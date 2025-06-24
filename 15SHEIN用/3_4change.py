import os
from PIL import Image
import shutil
from io import BytesIO
import math

def process_images():
    input_dir = "待处理图片"
    output_dir = "已处理图片"
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 支持的图片格式
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    
    for filename in os.listdir(input_dir):
        filepath = os.path.join(input_dir, filename)
        
        # 检查是否为图片文件
        ext = os.path.splitext(filename)[1].lower()
        if not os.path.isfile(filepath) or ext not in image_extensions:
            continue
        
        try:
            with Image.open(filepath) as img:
                # 转换为RGB模式（移除透明度）
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                width, height = img.size
                target_ratio = 3/4
                current_ratio = width / height
                
                # 计算裁剪区域（3:4比例）
                if current_ratio > target_ratio:
                    # 图片太宽，裁剪左右
                    new_width = int(height * target_ratio)
                    left = (width - new_width) / 2
                    top = 0
                    right = left + new_width
                    bottom = height
                else:
                    # 图片太高，裁剪上下
                    new_height = int(width / target_ratio)
                    left = 0
                    top = (height - new_height) / 2
                    right = width
                    bottom = top + new_height
                
                # 执行裁剪
                img = img.crop((left, top, right, bottom))
                
                # 调整分辨率（最短边≥800，最长边≤4000）
                new_width, new_height = img.size
                if min(new_width, new_height) < 800:
                    # 按最短边=800等比例缩放
                    scale_factor = 900 / min(new_width, new_height)
                    new_size = (int(new_width * scale_factor), int(new_height * scale_factor))
                    img = img.resize(new_size, Image.LANCZOS)
                elif max(new_width, new_height) > 4000:
                    # 按最长边=4000等比例缩放
                    scale_factor = 2200 / max(new_width, new_height)
                    new_size = (int(new_width * scale_factor), int(new_height * scale_factor))
                    img = img.resize(new_size, Image.LANCZOS)
                
                # 准备输出路径
                #output_path = os.path.join(output_dir, f"processed_{filename}") 
                output_path = os.path.join(output_dir, f"{filename}")
                
                # 优化文件大小
                buffer = BytesIO()
                quality = 90  # 初始质量
                img_format = 'JPEG' if ext in ('.jpg', '.jpeg') else 'PNG'
                
                while quality >= 50:
                    buffer.seek(0)
                    buffer.truncate(0)
                    
                    save_args = {
                        'format': img_format,
                        'quality': quality
                    }
                    
                    if img_format == 'PNG':
                        save_args['compress_level'] = 6
                    
                    img.save(buffer, **save_args)
                    
                    # 检查文件大小
                    if buffer.tell() <= 1.9 * 1024 * 1024:  # 1.9MB
                        with open(output_path, 'wb') as f:
                            f.write(buffer.getvalue())
                        print(f"处理成功: {filename} -> 大小: {buffer.tell()/1024:.1f}KB 分辨率: {img.size}")
                        break
                    
                    # 未满足大小要求则降低质量
                    quality -= 10
                else:
                    # 如果质量降至50%仍不满足，强制保存并警告
                    with open(output_path, 'wb') as f:
                        img.save(output_path, format=img_format, quality=50)
                    print(f"警告: {filename} 文件大小可能超过1.9MB (实际: {buffer.tell()/1024/1024:.2f}MB)")

        except Exception as e:
            print(f"处理失败: {filename} - {str(e)}")

if __name__ == "__main__":
    process_images()
