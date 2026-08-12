# -*- coding: utf-8 -*-
"""
图片侵权/违规内容 AI 分类筛选工具
根据用户提供的关键词规则，调用多模态AI接口识别本地图片，
自动分类为：正常可用 / 谨慎使用 / 违规侵权 三类，并分别复制到对应文件夹。
识别结果同时会导出为一份 Excel 表格，保存在输出文件夹根目录下。
"""

import concurrent.futures
import requests
import base64
import threading
import io
import json
import re
import shutil
import time
from pathlib import Path
from PIL import Image
import openpyxl
import tkinter as tk
from tkinter import filedialog, messagebox
import queue

# ================= 文件路径 =================
CACHE_FILE = Path("config_cache.json")
RESULT_FILE = Path("classify_results.json")  # 断点续跑记录
RESULT_XLSX_NAME = "识别结果.xlsx"  # 导出到输出文件夹下的表格文件名

stop_event = threading.Event()
log_queue = queue.Queue()
LOCK = threading.Lock()

# 支持的图片后缀
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# 分类文件夹名
CAT_NORMAL = "1_正常可用"
CAT_CAUTION = "2_谨慎使用"
CAT_BANNED = "3_违规侵权"

# ================= 默认配置 =================
DEFAULT_CONFIG = {
    "api_key": "模型API密钥",
    "base_url": "",
    "model": "gpt-4o-mini",
    "workers": 8,
    "source_folder": "",
    "output_folder": "",
    "prompt": (
        "你是一名电商图片合规审核员。请根据以下规则判断图片是否存在侵权或违规风险：\n"
        "【在这里填写你的判断关键词/规则，例如：是否包含知名品牌LOGO、卡通形象、"
        "明星肖像、他人版权作品、违禁词图案等】\n\n"
        "请只输出如下JSON格式，不要输出任何其他文字：\n"
        '{"category": "正常/谨慎/违规", "reason": "详细说明理由（不超过30字）"}'
    ),
}

# ================= JSON配置系统 =================
def load_config():
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT_CONFIG, **data}
        except Exception:
            return dict(DEFAULT_CONFIG)
    else:
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

def save_config(data):
    CACHE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

config = load_config()

# ================= 结果缓存（支持断点续跑） =================
def load_results():
    if RESULT_FILE.exists():
        try:
            return json.loads(RESULT_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_results(results):
    with LOCK:
        RESULT_FILE.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

results_cache = load_results()

# ================= 日志 =================
def log(msg):
    print(msg)
    log_queue.put(msg)

# ================= 图片压缩 =================
def compress_image(img_path):
    try:
        img = Image.open(img_path)

        max_size = 512
        w, h = img.size

        if w > h:
            nw = max_size
            nh = int(h * max_size / w) if h else max_size
        else:
            nh = max_size
            nw = int(w * max_size / h) if w else max_size

        nw = max(nw, 1)
        nh = max(nh, 1)

        img = img.resize((nw, nh), Image.LANCZOS)

        if img.mode != "RGB":
            img = img.convert("RGB")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)

        return buf.getvalue()

    except Exception as e:
        log(f"压缩失败：{img_path} | {e}")
        return None

# ================= API：分类判断 =================
def classify_image(base64_image, max_retries=3):
    """
    调用多模态模型，根据config['prompt']中的规则判断图片类别。
    返回 (category, reason)，category 取值："正常" / "谨慎" / "违规" / None(失败)
    失败时 reason 会带上接口返回的真实错误内容，方便排查。
    """
    headers = {
        "Authorization": f"Bearer {config['api_key']}"
    }

    payload = {
        "model": config["model"],
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": config["prompt"]},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }}
            ]
        }],
        "max_tokens": 200,
        "temperature": 0
    }

    last_reason = "UNKNOWN"

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(
                f"{config['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
        except requests.exceptions.Timeout:
            last_reason = f"TIMEOUT(第{attempt}次)"
            continue
        except requests.exceptions.RequestException as e:
            last_reason = f"REQUEST_ERROR(第{attempt}次): {e}"
            continue

        # 限流/服务器繁忙，等一下再重试
        if r.status_code == 429 or r.status_code >= 500:
            body_text = r.text[:300]

            removed_param = _try_strip_unsupported_param(payload, body_text)
            if removed_param:
                last_reason = f"已自动移除不支持的参数 '{removed_param}' 并重试: {body_text}"
                continue

            last_reason = f"HTTP_{r.status_code}(第{attempt}次): {body_text}"
            time.sleep(2 * attempt)
            continue

        if r.status_code != 200:
            body_text = r.text[:300]
            removed_param = _try_strip_unsupported_param(payload, body_text)
            if removed_param and attempt < max_retries:
                last_reason = f"已自动移除不支持的参数 '{removed_param}' 并重试: {body_text}"
                continue
            return None, f"HTTP_{r.status_code}: {body_text}"

        try:
            data = r.json()
        except Exception:
            return None, f"响应不是合法JSON: {r.text[:300]}"

        if "choices" not in data:
            err_detail = data.get("error", data)
            return None, f"NO_CHOICES: {str(err_detail)[:300]}"

        try:
            content = data['choices'][0]['message']['content'].strip()
        except (KeyError, IndexError, TypeError) as e:
            return None, f"响应结构异常({e}): {str(data)[:300]}"

        return parse_classification(content)

    return None, f"重试{max_retries}次后仍失败: {last_reason}"

def _try_strip_unsupported_param(payload, error_text):
    """
    如果错误信息里提到某个参数"不支持/已弃用/deprecated/not supported"，
    就把它从 payload 里删掉，返回被删除的参数名；否则返回 None。
    """
    candidates = ["temperature", "max_tokens", "top_p", "presence_penalty",
                  "frequency_penalty", "logprobs", "stop"]

    text_lower = error_text.lower()
    if "deprecated" not in text_lower and "not supported" not in text_lower \
            and "unsupported" not in text_lower and "unrecognized" not in text_lower:
        return None

    for key in candidates:
        if key in payload and key.lower() in text_lower:
            del payload[key]
            return key

    return None

def parse_classification(content):
    """
    优先按JSON解析AI返回结果；解析失败时用关键词兜底匹配。
    """
    match = re.search(r"\{.*\}", content, re.S)
    if match:
        try:
            data = json.loads(match.group(0))
            cat_raw = str(data.get("category", "")).strip()
            reason = str(data.get("reason", "")).strip()
            cat = normalize_category(cat_raw)
            if cat:
                return cat, reason
        except Exception:
            pass

    cat = normalize_category(content)
    if cat:
        return cat, content[:60]

    return None, f"UNPARSEABLE: {content[:60]}"

def normalize_category(text):
    if not text:
        return None
    if "违规" in text or "侵权" in text or "禁" in text:
        return "违规"
    if "谨慎" in text or "不建议" in text or "risk" in text.lower():
        return "谨慎"
    if "正常" in text or "可用" in text or "safe" in text.lower():
        return "正常"
    return None

# ================= 单张图片处理 =================
def process_image(img_path: Path, source_root: Path):
    try:
        if not img_path.exists():
            return {"path": str(img_path), "status": "fail", "category": None, "reason": "FILE_NOT_FOUND"}

        img_bytes = compress_image(img_path)
        if not img_bytes:
            return {"path": str(img_path), "status": "fail", "category": None, "reason": "COMPRESS_FAIL"}

        base64_img = base64.b64encode(img_bytes).decode()
        category, reason = classify_image(base64_img)

        if not category:
            return {"path": str(img_path), "status": "fail", "category": None, "reason": reason}

        return {"path": str(img_path), "status": "success", "category": category, "reason": reason}

    except Exception as e:
        return {"path": str(img_path), "status": "fail", "category": None, "reason": str(e)}

# ================= 复制到分类目录 =================
def copy_to_category(img_path: Path, source_root: Path, output_root: Path, category: str):
    folder_map = {
        "正常": CAT_NORMAL,
        "谨慎": CAT_CAUTION,
        "违规": CAT_BANNED,
    }
    sub = folder_map.get(category)
    if not sub:
        return

    try:
        rel = img_path.relative_to(source_root)
    except ValueError:
        rel = img_path.name

    dest = output_root / sub / rel
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copy2(img_path, dest)
    except Exception as e:
        log(f"复制失败：{img_path} -> {dest} | {e}")

# ================= 扫描图片 =================
def scan_images(source_root: Path):
    files = []
    for p in source_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            files.append(p)
    return files

# ================= 结果表格（Excel） =================
RESULT_HEADERS = ["序号", "文件名", "完整路径", "分类结果", "原因/错误信息", "状态"]

def init_result_excel(output_root: Path):
    """
    在输出文件夹下创建（或复用已有的）识别结果表格，返回工作簿路径。
    """
    xlsx_path = output_root / RESULT_XLSX_NAME

    if xlsx_path.exists():
        return xlsx_path

    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "识别结果"
    sheet.append(RESULT_HEADERS)
    wb.save(xlsx_path)
    return xlsx_path

def append_result_row(xlsx_path: Path, row_index, img_path: Path, category, reason, status):
    """
    追加一行识别结果到表格并保存。多线程环境下用 LOCK 保护，避免并发写文件冲突。
    """
    status_cn = "成功" if status == "success" else "失败"
    with LOCK:
        try:
            wb = openpyxl.load_workbook(xlsx_path)
            sheet = wb.active
            sheet.append([
                row_index,
                img_path.name,
                str(img_path),
                category or "",
                reason or "",
                status_cn
            ])
            wb.save(xlsx_path)
        except Exception as e:
            log(f"写入结果表格失败：{e}")

# ================= 主任务 =================
def run_task():
    source_root = Path(config["source_folder"])
    output_root = Path(config["output_folder"])

    if not source_root.exists():
        log("❌ 源文件夹不存在")
        return

    for sub in (CAT_NORMAL, CAT_CAUTION, CAT_BANNED):
        (output_root / sub).mkdir(parents=True, exist_ok=True)

    xlsx_path = init_result_excel(output_root)

    all_images = scan_images(source_root)
    total = len(all_images)
    done = 0

    log(f"📂 共扫描到 {total} 张图片，开始识别...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=config["workers"]) as executor:

        futures = {}

        for img_path in all_images:
            if stop_event.is_set():
                break

            key = str(img_path)

            cached = results_cache.get(key)
            if cached and cached.get("status") == "success":
                copy_to_category(img_path, source_root, output_root, cached["category"])
                done += 1
                append_result_row(xlsx_path, done, img_path, cached["category"], cached.get("reason", ""), "success")
                log(f"[跳过-已识别] {done}/{total} {img_path.name} -> {cached['category']}")
                continue

            futures[executor.submit(process_image, img_path, source_root)] = img_path

        for f in concurrent.futures.as_completed(futures):
            if stop_event.is_set():
                break

            res = f.result()
            img_path = Path(res["path"])
            status = res["status"]

            if status == "success":
                category = res["category"]
                copy_to_category(img_path, source_root, output_root, category)

                with LOCK:
                    results_cache[str(img_path)] = res
                save_results(results_cache)

                done += 1
                append_result_row(xlsx_path, done, img_path, category, res["reason"], "success")
                log(f"[成功] {done}/{total} {img_path.name} -> {category} | {res['reason'][:30]}")

            else:
                with LOCK:
                    results_cache[str(img_path)] = res
                save_results(results_cache)

                done += 1
                append_result_row(xlsx_path, done, img_path, None, res["reason"], "fail")
                log(f"[失败] {done}/{total} {img_path.name} | {res['reason']}")

    log(f"🎉 全部完成，结果表格已保存到：{xlsx_path}")

# ================= UI 回调 =================
def start():
    config["api_key"] = api_key_var.get().strip()
    config["base_url"] = base_url_var.get().strip()
    config["model"] = model_var.get().strip()
    try:
        config["workers"] = int(workers_var.get())
    except ValueError:
        messagebox.showerror("错误", "线程数必须为整数")
        return
    config["prompt"] = prompt_text.get("1.0", tk.END).strip()
    config["source_folder"] = source_var.get().strip()
    config["output_folder"] = output_var.get().strip()

    if not config["source_folder"] or not config["output_folder"]:
        messagebox.showerror("错误", "请填写/选择源文件夹和输出文件夹")
        return

    if not config["api_key"] or not config["base_url"]:
        messagebox.showerror("错误", "请填写API KEY和BASE URL")
        return

    save_config(config)
    log("💾 已自动保存配置文件")

    try:
        status_var.set("🚀 识别中...")
    except NameError:
        pass

    stop_event.clear()
    threading.Thread(target=run_task, daemon=True).start()

def stop():
    stop_event.set()
    log("⛔ 已停止")

def choose_source_folder():
    path = filedialog.askdirectory()
    if path:
        source_var.set(path)

def choose_output_folder():
    path = filedialog.askdirectory()
    if path:
        output_var.set(path)

def clear_cache():
    global results_cache
    if messagebox.askyesno("确认", "确定要清空识别记录吗？（清空后所有图片将重新识别）"):
        results_cache = {}
        save_results(results_cache)
        log("🧹 已清空识别记录")

# ================= 右键/双击 复制粘贴菜单 =================
def attach_copy_paste_menu(widget):
    """
    给输入框/文本框绑定右键和双击菜单，支持 剪切/复制/粘贴/全选。
    """
    menu = tk.Menu(widget, tearoff=0)

    def cut():
        widget.event_generate("<<Cut>>")

    def copy():
        widget.event_generate("<<Copy>>")

    def paste():
        widget.event_generate("<<Paste>>")

    def select_all():
        if isinstance(widget, tk.Text):
            widget.tag_add("sel", "1.0", "end")
        else:
            widget.select_range(0, tk.END)

    menu.add_command(label="剪切", command=cut)
    menu.add_command(label="复制", command=copy)
    menu.add_command(label="粘贴", command=paste)
    menu.add_separator()
    menu.add_command(label="全选", command=select_all)

    def show_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

    widget.bind("<Button-3>", show_menu)       # 右键
    widget.bind("<Double-Button-1>", show_menu)  # 双击
    return menu

# ================= UI =================
root = tk.Tk()
root.title("图片侵权/违规内容识别分类系统")
root.geometry("900x820")

api_key_var = tk.StringVar(value=config["api_key"])
base_url_var = tk.StringVar(value=config["base_url"])
model_var = tk.StringVar(value=config["model"])
workers_var = tk.StringVar(value=str(config["workers"]))
source_var = tk.StringVar(value=config["source_folder"])
output_var = tk.StringVar(value=config["output_folder"])

tk.Label(root, text="API KEY").pack()
e_api_key = tk.Entry(root, textvariable=api_key_var, width=90)
e_api_key.pack()
attach_copy_paste_menu(e_api_key)

tk.Label(root, text="BASE URL").pack()
e_base_url = tk.Entry(root, textvariable=base_url_var, width=90)
e_base_url.pack()
attach_copy_paste_menu(e_base_url)

tk.Label(root, text="MODEL").pack()
e_model = tk.Entry(root, textvariable=model_var, width=90)
e_model.pack()
attach_copy_paste_menu(e_model)

tk.Label(root, text="线程数（如频繁失败请调低，如5-10）").pack()
e_workers = tk.Entry(root, textvariable=workers_var)
e_workers.pack()
attach_copy_paste_menu(e_workers)

# 源文件夹：支持直接粘贴路径 + 浏览按钮
tk.Label(root, text="源图片文件夹（可直接粘贴路径，或点击右侧按钮选择）").pack()
source_frame = tk.Frame(root)
source_frame.pack(fill="x", padx=10)
e_source = tk.Entry(source_frame, textvariable=source_var)
e_source.pack(side="left", fill="x", expand=True)
attach_copy_paste_menu(e_source)
tk.Button(source_frame, text="浏览...", command=choose_source_folder).pack(side="left", padx=5)

# 输出文件夹：支持直接粘贴路径 + 浏览按钮
tk.Label(root, text="输出文件夹（自动生成三个分类子文件夹 + 识别结果表格）").pack()
output_frame = tk.Frame(root)
output_frame.pack(fill="x", padx=10)
e_output = tk.Entry(output_frame, textvariable=output_var)
e_output.pack(side="left", fill="x", expand=True)
attach_copy_paste_menu(e_output)
tk.Button(output_frame, text="浏览...", command=choose_output_folder).pack(side="left", padx=5)

tk.Label(root, text="判断规则/关键词提示词（要求AI输出JSON分类结果，右键/双击可复制粘贴）").pack()
prompt_text = tk.Text(root, height=10)
prompt_text.insert(tk.END, config["prompt"])
prompt_text.pack(fill="x", padx=10)
attach_copy_paste_menu(prompt_text)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=5)
tk.Button(btn_frame, text="🚀 开始识别", bg="green", fg="white", command=start).pack(side="left", padx=5)
tk.Button(btn_frame, text="⛔ 停止", bg="red", fg="white", command=stop).pack(side="left", padx=5)
tk.Button(btn_frame, text="🧹 清空识别记录", bg="orange", fg="white", command=clear_cache).pack(side="left", padx=5)

tk.Label(root, text="识别记录（实时日志）").pack()
log_box = tk.Text(root, height=16)
log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
attach_copy_paste_menu(log_box)

def update_log():
    while not log_queue.empty():
        log_box.insert(tk.END, log_queue.get() + "\n")
        log_box.see(tk.END)
    root.after(200, update_log)

root.after(200, update_log)
root.mainloop()
