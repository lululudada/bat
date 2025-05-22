import os
from PIL import Image
import io
import math

def process_images():
    # 支持的图片扩展名
    supported_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')
    
    # 设置文件夹路径
    current_folder = os.getcwd()
    input_folder = os.path.join(current_folder, "待处理图片")
    output_folder = os.path.join(current_folder, "处理后图片")
    
    # 创建待处理图片文件夹（如果不存在）
    os.makedirs(input_folder, exist_ok=True)
    print(f"图片请放入: {input_folder}")
    
    # 创建输出文件夹
    os.makedirs(output_folder, exist_ok=True)
    
    # 检查待处理文件夹是否为空
    if not any(os.listdir(input_folder)):
        print("'待处理图片'文件夹为空，请放入图片后重新运行程序")
        return
    
    # 最小分辨率
    min_width, min_height = 1024, 1024
    
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
                    
                    # 检查并调整分辨率
                    width, height = img.size
                    if width < min_width or height < min_height:
                        # 计算等比例放大的尺寸
                        ratio = max(min_width / width, min_height / height)
                        new_width = math.ceil(width * ratio)
                        new_height = math.ceil(height * ratio)
                        img = img.resize((new_width, new_height), Image.LANCZOS)
                        print(f"调整分辨率: {os.path.join(relative_path, filename)} 从 {width}x{height} 放大到 {new_width}x{new_height}")
                    
                    # 确定输出文件名和路径
                    base_name = os.path.splitext(filename)[0]
                    output_filename = f"{base_name}.jpg"
                    output_path = os.path.join(output_root, output_filename)
                    
                    # 初始质量设置
                    quality = 95
                    
                    # 调整质量直到图片大小小于1.9MB
                    while quality >= 5:
                        # 使用BytesIO来获取图片大小而不保存到磁盘
                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=quality, optimize=True)
                        size_in_bytes = buffer.getbuffer().nbytes
                        size_in_mb = size_in_bytes / (1024 * 1024)
                        
                        if size_in_mb <= 1.9:
                            # 如果大小合适，保存图片
                            img.save(output_path, format='JPEG', quality=quality, optimize=True)
                            print(f"处理成功: {os.path.join(relative_path, filename)} -> {os.path.join(relative_path, output_filename)} (质量: {quality}%, 大小: {size_in_mb:.2f}MB, 分辨率: {img.size[0]}x{img.size[1]})")
                            processed_count += 1
                            break
                        else:
                            # 减少质量
                            quality -= 5
                    else:
                        print(f"无法将 {os.path.join(relative_path, filename)} 压缩到1.9MB以下而不损失过多质量")
                    
                except Exception as e:
                    print(f"处理 {os.path.join(relative_path, filename)} 时出错: {str(e)}")
    
    # 输出总结信息
    if processed_count > 0:
        print(f"\n处理完成！共成功处理 {processed_count} 张图片")
        print(f"处理后的图片已保存到: {output_folder}")
        print("注意：已保持原始文件夹结构")
    else:
        print("\n没有找到可处理的图片（支持的格式：.png, .jpg, .jpeg, .bmp, .gif, .tiff, .webp）")

if __name__ == "__main__":
    print("=== 图片处理程序 ===")
    print("将递归处理'待处理图片'文件夹及其所有子文件夹")
    process_images()
    input("\n按Enter键退出...")