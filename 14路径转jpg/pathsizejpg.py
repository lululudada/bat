import os
import sys
from PIL import Image
import io
import math

def process_images(input_folder):
    # 支持的图片扩展名
    supported_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp', '.jfif')
    
    # 创建输出文件夹
    output_folder = os.path.join(input_folder, "处理后图片")
    os.makedirs(output_folder, exist_ok=True)
    
    # 检查输入文件夹是否存在
    if not os.path.exists(input_folder):
        print(f"错误：文件夹不存在 - {input_folder}")
        return False
    
    # 检查输入文件夹是否包含支持的图片
    has_images = False
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(supported_extensions):
            has_images = True
            break
    
    if not has_images:
        print("未找到支持的图片文件（支持的格式：.png, .jpg, .jpeg, .bmp, .gif, .tiff, .webp）")
        return False
    
    # 最小分辨率
    min_width, min_height = 1024, 1024
    
    # 处理图片
    processed_count = 0
    skipped_count = 0
    
    print("\n开始处理图片...")
    print("=" * 60)
    
    # 遍历输入文件夹
    for filename in os.listdir(input_folder):
        # 检查文件是否是支持的图片格式
        if not filename.lower().endswith(supported_extensions):
            continue
            
        try:
            # 打开图片
            img_path = os.path.join(input_folder, filename)
            img = Image.open(img_path)
            original_mode = img.mode
            
            # 处理透明通道
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
                print(f"已移除透明通道: {filename}")
            
            # 检查并调整分辨率
            width, height = img.size
            resolution_changed = False
            if width < min_width or height < min_height:
                # 计算等比例放大的尺寸
                ratio = max(min_width / width, min_height / height)
                new_width = math.ceil(width * ratio)
                new_height = math.ceil(height * ratio)
                img = img.resize((new_width, new_height), Image.LANCZOS)
                resolution_changed = True
            
            # 确定输出格式和文件名
            base_name = os.path.splitext(filename)[0]
            output_ext = ".jpg"
            output_filename = f"{base_name}{output_ext}"
            output_path = os.path.join(output_folder, output_filename)
            
            # 初始质量设置
            quality = 95
            
            # 调整质量直到图片大小小于1.9MB
            success = False
            while quality >= 5:
                buffer = io.BytesIO()
                
                # 保存参数
                save_params = {'optimize': True, 'quality': quality}
                
                # 保存到buffer以检查大小
                img.save(buffer, format='JPEG', **save_params)
                size_in_bytes = buffer.getbuffer().nbytes
                size_in_mb = size_in_bytes / (1024 * 1024)
                
                if size_in_mb <= 1.9:
                    img.save(output_path, format='JPEG', **save_params)
                    success = True
                    
                    # 打印处理信息
                    status = []
                    if resolution_changed:
                        status.append(f"分辨率: {width}x{height}→{new_width}x{new_height}")
                    if original_mode != img.mode:
                        status.append(f"模式: {original_mode}→{img.mode}")
                    status.append(f"大小: {size_in_mb:.2f}MB")
                    status.append(f"质量: {quality}%")
                    
                    print(f"✓ {filename} → {output_filename} ({', '.join(status)})")
                    processed_count += 1
                    break
                    
                quality -= 5
                
            if not success:
                # 以最低质量保存
                save_params['quality'] = 5
                img.save(output_path, format='JPEG', **save_params)
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', **save_params)
                size_in_mb = buffer.getbuffer().nbytes / (1024 * 1024)
                print(f"⚠ {filename} → {output_filename} (质量: 5%, 大小: {size_in_mb:.2f}MB - 达到最低质量)")
                processed_count += 1
                    
        except Exception as e:
            print(f"✗ 处理 {filename} 时出错: {str(e)}")
            skipped_count += 1
    
    # 输出总结信息
    print("=" * 60)
    if processed_count > 0:
        print(f"\n处理完成！成功处理 {processed_count} 张图片")
        if skipped_count > 0:
            print(f"跳过 {skipped_count} 张无法处理的图片")
        print(f"处理后的图片已保存到: {output_folder}")
        return True
    else:
        print("\n没有图片被处理")
        return False

if __name__ == "__main__":
    print("=== 图片处理工具 ===")
    print("功能说明:")
    print("1. 自动调整分辨率至最小1024x1024")
    print("2. 自动转换为JPG格式")
    print("3. 优化文件大小至1.9MB以下")
    print("=" * 40)
    
    # 检查是否通过拖拽传递了文件夹路径
    if len(sys.argv) > 1:
        # 获取拖拽的文件夹路径
        input_folder = sys.argv[1]
        print(f"使用拖拽的文件夹: {input_folder}")
        process_images(input_folder)
    else:
        # 提示用户输入文件夹路径
        input_folder = input("请将文件夹拖拽到本程序上，或输入文件夹路径: ").strip('"').strip()
        if not input_folder:
            print("未提供文件夹路径，程序退出")
        else:
            process_images(input_folder)
    
    input("\n按Enter键退出...")