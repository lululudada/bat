import os
from PIL import Image
import shutil
from io import BytesIO

def process_images():
    input_dir = "待处理图片"
    output_dir = "处理后图片1比1"
    
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
                
                # 计算裁剪区域
                width, height = img.size
                size = min(width, height)
                left = (width - size) / 2
                top = (height - size) / 2
                right = left + size
                bottom = top + size
                
                # 裁剪为正方形
                img = img.crop((left, top, right, bottom))
                
                # 调整分辨率（不超过2200x2200）
                if size > 2200:
                    img = img.resize((2200, 2200), Image.LANCZOS)
                
                # 准备输出路径
                #output_path = os.path.join(output_dir, f"processed_{filename}")
                output_path = os.path.join(output_dir, f"{filename}")
                
                # 优化文件大小
                buffer = BytesIO()
                quality = 95  # 初始质量
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
                    if buffer.tell() <= 1.9 * 1024 * 1024:  # 19MB
                        with open(output_path, 'wb') as f:
                            f.write(buffer.getvalue())
                        print(f"处理成功: {filename} -> 大小: {buffer.tell()//1024}KB")
                        break
                    
                    # 未满足大小要求则降低质量
                    quality -= 10
                else:
                    # 如果质量降至50%仍不满足，强制保存并警告
                    with open(output_path, 'wb') as f:
                        img.save(output_path, format=img_format, quality=50)
                    print(f"警告: {filename} 文件大小可能超过1.9MB")

        except Exception as e:
            print(f"处理失败: {filename} - {str(e)}")

if __name__ == "__main__":
    process_images()