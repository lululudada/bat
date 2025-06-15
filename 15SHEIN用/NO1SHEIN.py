import os
from PIL import Image
import io
import math
import threading
from queue import Queue
import time
import concurrent.futures

def get_start_number():
    """获取用户输入的起始编号"""
    while True:
        try:
            start_num = int(input("请输入起始编号（例如输入1生成JBY00001）：").strip())
            if start_num < 1:
                raise ValueError
            return start_num
        except ValueError:
            print("错误：请输入一个正整数！")

def process_images():
    # 支持的图片扩展名
    supported_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')
    
    # 设置文件夹路径
    current_folder = os.getcwd()
    input_folder = os.path.join(current_folder, "待处理图片")
    output_folder_3to4 = os.path.join(current_folder, "处理后图片")
    output_folder_1to1 = os.path.join(current_folder, "处理后图片1比1")
    
    # 创建待处理图片文件夹（如果不存在）
    os.makedirs(input_folder, exist_ok=True)
    print(f"\n图片请放入: {input_folder}")
    
    # 创建输出文件夹
    os.makedirs(output_folder_3to4, exist_ok=True)
    os.makedirs(output_folder_1to1, exist_ok=True)
    
    # 检查待处理文件夹是否为空
    if not any(os.listdir(input_folder)):
        print("'待处理图片'文件夹为空，请放入图片后重新运行程序")
        return
    
    # 参数设置
    min_width, min_height = 1350, 1350
    target_ratio_3to4 = 3/4
    target_ratio_1to1 = 1/1

    # 获取起始编号
    start_number = get_start_number()
    
    # 创建线程安全的计数器
    current_number = start_number
    number_lock = threading.Lock()
    
    # 创建处理统计
    processed_count = 0
    error_count = 0
    count_lock = threading.Lock()
    
    # 创建打印锁，确保输出不混乱
    print_lock = threading.Lock()
    
    # 创建任务队列
    task_queue = Queue()
    
    # 收集所有需要处理的文件路径
    all_files = []
    for root, dirs, files in os.walk(input_folder):
        for filename in files:
            if filename.lower().endswith(supported_extensions):
                all_files.append((root, filename))
    
    total_files = len(all_files)
    if total_files == 0:
        print("\n没有找到可处理的图片")
        return
    
    print(f"\n找到 {total_files} 张待处理图片")
    
    # 线程处理函数
    def worker():
        nonlocal processed_count, error_count, current_number
        while True:
            try:
                # 从队列获取任务
                root, filename = task_queue.get(timeout=3)
            except:
                # 队列为空，退出线程
                break
                
            try:
                # 打开图片
                img_path = os.path.join(root, filename)
                img = Image.open(img_path)
                
                # 如果图片有透明通道，转换为RGB
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # 获取唯一编号
                with number_lock:
                    file_number = current_number
                    current_number += 1
                
                # 生成新文件名
                new_filename = f"JBY{file_number:05d}.jpg"
                
                # 计算相对路径
                relative_path = os.path.relpath(root, input_folder)
                
                # 初始尺寸信息
                orig_width, orig_height = img.size
                
                with print_lock:
                    print(f"\n处理文件: {os.path.join(relative_path, filename)}")
                    print(f"新文件名: {new_filename}")
                    print(f"原始尺寸: {orig_width}x{orig_height}")

                # 第一步：调整基础分辨率
                if orig_width < min_width or orig_height < min_height:
                    ratio = max(min_width/orig_width, min_height/orig_height)
                    new_width = math.ceil(orig_width * ratio)
                    new_height = math.ceil(orig_height * ratio)
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    with print_lock:
                        print(f"基础放大: {orig_width}x{orig_height} → {new_width}x{new_height}")
                else:
                    new_width, new_height = orig_width, orig_height

                # 保存基础调整后的图片用于两种裁切
                img_base = img.copy()
                
                # 第二步：3:4比例裁切
                img_3to4 = process_ratio(img_base, target_ratio_3to4, min_width, min_height, "3:4", new_filename)
                
                # 第三步：1:1比例裁切
                img_1to1 = process_ratio(img_base, target_ratio_1to1, min_width, min_height, "1:1", new_filename)

                # 创建输出文件夹
                output_root_3to4 = os.path.join(output_folder_3to4, relative_path)
                output_root_1to1 = os.path.join(output_folder_1to1, relative_path)
                os.makedirs(output_root_3to4, exist_ok=True)
                os.makedirs(output_root_1to1, exist_ok=True)
                
                # 保存3:4比例图片
                output_path_3to4 = os.path.join(output_root_3to4, new_filename)
                save_result_3to4 = save_image_with_quality(img_3to4, output_path_3to4)
                
                # 保存1:1比例图片
                output_path_1to1 = os.path.join(output_root_1to1, new_filename)
                save_result_1to1 = save_image_with_quality(img_1to1, output_path_1to1)
                
                # 更新计数
                with count_lock:
                    if save_result_3to4 and save_result_1to1:
                        processed_count += 1
                    else:
                        error_count += 1
                
                # 标记任务完成
                task_queue.task_done()
                
            except Exception as e:
                with print_lock:
                    print(f"处理出错: {str(e)}")
                with count_lock:
                    error_count += 1
                task_queue.task_done()
    
    # 将任务添加到队列
    for file_info in all_files:
        task_queue.put(file_info)
    
    # 确定线程数量（根据CPU核心数，但不超过文件数量）
    num_threads = min(os.cpu_count() * 2, total_files, 32)  # 最多32个线程
    num_threads = max(num_threads, 1)  # 至少1个线程
    #num_threads = 32   # 手动设置线程
    
    print(f"启动 {num_threads} 个线程处理图片...")
    start_time = time.time()
    
    # 创建并启动线程池
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        # 提交任务
        futures = [executor.submit(worker) for _ in range(num_threads)]
        
        # 等待所有任务完成
        task_queue.join()
    
    # 计算处理时间
    elapsed_time = time.time() - start_time
    
    # 输出总结信息
    if processed_count > 0:
        print(f"\n处理完成！共处理 {total_files} 张图片")
        print(f"成功处理: {processed_count} 张（两种比例）")
        print(f"失败处理: {error_count} 张")
        print(f"起始编号: JBY{start_number:05d}")
        print(f"结束编号: JBY{(current_number-1):05d}")
        print(f"总耗时: {elapsed_time:.2f}秒")
        print(f"平均速度: {total_files/elapsed_time:.2f} 图片/秒")
        print(f"3:4比例图片路径: {output_folder_3to4}")
        print(f"1:1比例图片路径: {output_folder_1to1}")
        print("文件结构已保持原始目录")
    else:
        print("\n没有成功处理的图片")

def process_ratio(img, target_ratio, min_width, min_height, ratio_name, filename):
    """处理特定比例的裁切和调整"""
    width, height = img.size
    
    # 计算裁切区域
    current_ratio = width / height
    
    if current_ratio > target_ratio:  # 原图更宽
        crop_height = height
        crop_width = int(crop_height * target_ratio)
        left = (width - crop_width) // 2
        top = 0
    else:  # 原图更高
        crop_width = width
        crop_height = int(crop_width / target_ratio)
        left = 0
        top = (height - crop_height) // 2
    
    # 执行裁切
    img_cropped = img.crop((left, top, left + crop_width, top + crop_height))
    
    # 最终分辨率验证
    final_width, final_height = img_cropped.size
    if final_width < min_width or final_height < min_height:
        ratio = max(min_width/final_width, min_height/final_height)
        final_width = math.ceil(final_width * ratio)
        final_height = math.ceil(final_height * ratio)
        img_cropped = img_cropped.resize((final_width, final_height), Image.LANCZOS)
    
    return img_cropped

def save_image_with_quality(img, output_path):
    """保存图片并进行质量压缩"""
    quality = 95
    while quality >= 5:
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        size_mb = buffer.getbuffer().nbytes / (1024 * 1024)
        
        if size_mb <= 1.9:
            img.save(output_path, format='JPEG', quality=quality, optimize=True)
            return True
        quality -= 5
    
    return False

if __name__ == "__main__":
    print("=== 图片处理程序 ===")
    print("功能说明:")
    print("- 自动处理'待处理图片'及其子文件夹")
    print("- 输出到两个文件夹：'处理后图片_3比4'和'处理后图片_1比1'")
    print("- 自动连续编号（格式：JBY00001）")
    print("- 自动裁切到3:4和1:1两种比例")
    print("- 保证分辨率≥1350x1350")
    print("- 文件大小≤1.9MB")
    print("- 使用多线程加速处理\n")
    process_images()
    input("\n按Enter键退出...")