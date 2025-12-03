import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

def choose_folder():
    folder = filedialog.askdirectory()
    folder_path.set(folder)

def preview_results():
    folder = folder_path.get()
    find_text = find_entry.get()
    repl_text = replace_entry.get()
    use_regex = regex_var.get()

    if not folder:
        messagebox.showerror("错误", "请先选择文件夹")
        return

    file_list.delete(*file_list.get_children())

    for filename in os.listdir(folder):
        old = filename
        name, ext = os.path.splitext(filename)

        if use_regex:
            new = re.sub(find_text, repl_text, name) + ext
        else:
            new = name.replace(find_text, repl_text) + ext

        if new != old:
            file_list.insert("", "end", values=(old, new))

def rename_files():
    folder = folder_path.get()
    find_text = find_entry.get()
    repl_text = replace_entry.get()
    use_regex = regex_var.get()

    if not folder:
        messagebox.showerror("错误", "请先选择文件夹")
        return

    changed = 0

    for filename in os.listdir(folder):
        old_path = os.path.join(folder, filename)
        if os.path.isdir(old_path):
            continue

        name, ext = os.path.splitext(filename)

        if use_regex:
            new_name = re.sub(find_text, repl_text, name) + ext
        else:
            new_name = name.replace(find_text, repl_text) + ext

        new_path = os.path.join(folder, new_name)

        if new_name != filename:
            if os.path.exists(new_path):
                continue
            os.rename(old_path, new_path)
            changed += 1

    messagebox.showinfo("完成", f"重命名完成，共修改 {changed} 个文件")
    preview_results()


# ---------------- UI ---------------- #

root = tk.Tk()
root.title("批量重命名工具（简洁版）")
root.geometry("600x500")

folder_path = tk.StringVar()
regex_var = tk.BooleanVar()

tk.Label(root, text="选择文件夹：").pack(anchor="w", padx=10, pady=5)
tk.Entry(root, textvariable=folder_path, width=50).pack(anchor="w", padx=10)
tk.Button(root, text="选择文件夹", command=choose_folder).pack(anchor="w", padx=10, pady=5)

tk.Label(root, text="查找内容（可正则）：").pack(anchor="w", padx=10, pady=5)
find_entry = tk.Entry(root, width=40)
find_entry.pack(anchor="w", padx=10)

tk.Label(root, text="替换为：").pack(anchor="w", padx=10, pady=5)
replace_entry = tk.Entry(root, width=40)
replace_entry.pack(anchor="w", padx=10)

tk.Checkbutton(root, text="使用正则表达式", variable=regex_var).pack(anchor="w", padx=10, pady=5)

tk.Button(root, text="预览结果", command=preview_results, bg="#e0e0e0").pack(anchor="w", padx=10, pady=5)
tk.Button(root, text="开始重命名", command=rename_files, bg="#d0ffd0").pack(anchor="w", padx=10, pady=5)

# 预览表格
columns = ("old", "new")
file_list = ttk.Treeview(root, columns=columns, show="headings", height=10)
file_list.heading("old", text="原文件名")
file_list.heading("new", text="新文件名")
file_list.pack(fill="both", expand=True, padx=10, pady=10)

root.mainloop()
