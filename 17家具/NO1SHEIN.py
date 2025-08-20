import os
from PIL import Image
import io
import math

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
    output_folder = os.path.join(current_folder, "处理后图片")
    
    # 创建待处理图片文件夹（如果不存在）
    os.makedirs(input_folder, exist_ok=True)
    print(f"\n图片请放入: {input_folder}")
    
    # 创建输出文件夹
    os.makedirs(output_folder, exist_ok=True)
    
    # 检查待处理文件夹是否为空
    if not any(os.listdir(input_folder)):
        print("'待处理图片'文件夹为空，请放入图片后重新运行程序")
        return
    
    # 参数设置
    min_width, min_height = 1500, 1500
    max_side_limit = 3000  # 新增：最大边长限制
    target_ratio = 1/1  # 3:4比例

    # 获取起始编号
    start_number = get_start_number()
    current_number = start_number

    # 处理图片
    processed_count = 0
    
    # 遍历待处理文件夹及其所有子文件夹
    for root, dirs, files in os.walk(input_folder):
        # 计算相对路径，用于在输出文件夹中保持相同结构
        relative_path = os.path.relpath(root, input_folder)
        output_root = os.path.join(output_folder, relative_path)
        
        # 创建对应的输出子文件夹
        os.makedirs(output_root, exist_ok=True)
        
        for filename in files:
            # 检查文件是否是支持的图片格式
            if filename.lower().endswith(supported_extensions):
                try:
                    # 打开图片
                    img_path = os.path.join(root, filename)
                    img = Image.open(img_path)
                    
                    # 如果图片有透明通道，转换为RGB
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')

                    # 生成新文件名
                    new_filename = f"JBY{current_number:05d}.jpg"
                    current_number += 1
                    
                    # 初始尺寸信息
                    orig_width, orig_height = img.size
                    print(f"\n处理文件: {os.path.join(relative_path, filename)}")
                    print(f"新文件名: {new_filename}")
                    print(f"原始尺寸: {orig_width}x{orig_height}")

                    # 第一步：智能尺寸调整（同时满足最小1350px和最大3000px要求）
                    min_side = min(orig_width, orig_height)
                    max_side = max(orig_width, orig_height)
                    
                    # 计算满足最小尺寸和最大尺寸的缩放比例
                    ratio_min = min_width / min_side if min_side < min_width else 1
                    ratio_max = max_side_limit / max_side if max_side > max_side_limit else 1
                    
                    # 确定最终缩放比例
                    if min_side < min_width and max_side > max_side_limit:
                        # 需要同时放大和缩小的情况
                        if min_side * ratio_max >= min_width:
                            scale_ratio = ratio_max  # 优先满足最大边限制
                            reason = f"同时满足最小边{min_width}px和最大边{max_side_limit}px要求"
                        else:
                            scale_ratio = ratio_min  # 优先满足最小边要求
                            reason = f"优先满足最小边{min_width}px要求（无法同时满足最大边限制）"
                    elif min_side < min_width:
                        scale_ratio = ratio_min
                        reason = f"满足最小边{min_width}px要求"
                    elif max_side > max_side_limit:
                        scale_ratio = ratio_max
                        reason = f"满足最大边{max_side_limit}px要求"
                    else:
                        scale_ratio = 1
                        reason = "尺寸已满足要求"
                    
                    # 执行缩放（当比例不等于1时）
                    if abs(scale_ratio - 1) > 1e-5:
                        new_width = round(orig_width * scale_ratio)
                        new_height = round(orig_height * scale_ratio)
                        img = img.resize((new_width, new_height), Image.LANCZOS)
                        print(f"智能调整: {orig_width}x{orig_height} → {new_width}x{new_height} | 原因: {reason}")
                    else:
                        new_width, new_height = orig_width, orig_height
                        print(f"智能调整: 保持原始尺寸 | 原因: {reason}")

                    # 第二步：3:4比例裁切
                    current_ratio = new_width / new_height
                    
                    # 计算裁切区域
                    if current_ratio > target_ratio:  # 原图更宽
                        crop_height = new_height
                        crop_width = int(crop_height * target_ratio)
                        left = (new_width - crop_width) // 2
                        top = 0
                    else:  # 原图更高
                        crop_width = new_width
                        crop_height = int(crop_width / target_ratio)
                        left = 0
                        top = (new_height - crop_height) // 2
                    
                    # 执行裁切
                    img = img.crop((left, top, left + crop_width, top + crop_height))
                    print(f"比例裁切: → {img.size[0]}x{img.size[1]} (3:4)")

                    # 第三步：最终分辨率验证
                    final_width, final_height = img.size
                    if final_width < min_width or final_height < min_height:
                        # 裁切后尺寸不足，需要放大（但不超过最大限制）
                        ratio = max(min_width/final_width, min_height/final_height)
                        # 应用放大但不超过最大限制
                        if max(final_width * ratio, final_height * ratio) > max_side_limit:
                            ratio = min(ratio, max_side_limit / max(final_width, final_height))
                        
                        final_width = math.ceil(final_width * ratio)
                        final_height = math.ceil(final_height * ratio)
                        img = img.resize((final_width, final_height), Image.LANCZOS)
                        print(f"最终调整: → {final_width}x{final_height} (保证最小边要求)")

                    # 确定输出路径
                    output_path = os.path.join(output_root, new_filename)
                    
                    # 质量压缩流程
                    quality = 95
                    while quality >= 5:
                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=quality, optimize=True)
                        size_mb = buffer.getbuffer().nbytes / (1024 * 1024)
                        
                        if size_mb <= 1.9:
                            img.save(output_path, format='JPEG', quality=quality, optimize=True)
                            print(f"保存结果: {new_filename} | 质量: {quality}% | 大小: {size_mb:.2f}MB")
                            processed_count += 1
                            break
                        quality -= 5
                    else:
                        print("! 无法压缩到1.9MB以下")
                    
                except Exception as e:
                    print(f"处理出错: {str(e)}")

    # 输出总结信息
    if processed_count > 0:
        print(f"\n处理完成！共成功处理 {processed_count} 张图片")
        print(f"起始编号: JBY{start_number:05d}")
        print(f"结束编号: JBY{(current_number-1):05d}")
        print(f"处理后图片路径: {output_folder}")
        print("文件结构已保持原始目录")
    else:
        print("\n没有找到可处理的图片")

if __name__ == "__main__":
    print("=== 图片处理程序 ===")
    print("功能说明:")
    print("- 自动处理'待处理图片'及其子文件夹")
    print("- 输出到'处理后图片'保持相同结构")
    print("- 自动连续编号（格式：JBY00001）")
    print("- 自动裁切到3:4比例")
    print("- 保证分辨率≥1350x1350")
    print("- 限制最大边长≤3000px")  # 新增功能说明
    print("- 文件大小≤1.9MB\n")
    process_images()
    input("\n按Enter键退出...")