import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import threading
import io

class ImageProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("批量图片处理工具")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        
        # 创建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 输入路径选择
        ttk.Label(main_frame, text="输入文件夹:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.input_path = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.input_path, width=50).grid(row=0, column=1, pady=5, padx=5)
        ttk.Button(main_frame, text="浏览", command=self.browse_input).grid(row=0, column=2, pady=5)
        
        # 输出路径选择
        ttk.Label(main_frame, text="输出文件夹:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_path = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.output_path, width=50).grid(row=1, column=1, pady=5, padx=5)
        ttk.Button(main_frame, text="浏览", command=self.browse_output).grid(row=1, column=2, pady=5)
        
        # 分辨率设置
        resolution_frame = ttk.LabelFrame(main_frame, text="分辨率设置", padding="5")
        resolution_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(resolution_frame, text="宽度:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.width_var = tk.StringVar()
        ttk.Entry(resolution_frame, textvariable=self.width_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(resolution_frame, text="高度:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.height_var = tk.StringVar()
        ttk.Entry(resolution_frame, textvariable=self.height_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(resolution_frame, text="或按比例缩放:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.scale_var = tk.StringVar(value="1.0")
        scale_combo = ttk.Combobox(resolution_frame, textvariable=self.scale_var, values=["0.1", "0.25", "0.5", "0.75", "1.0", "1.5", "2.0", "3.0"])
        scale_combo.grid(row=1, column=1, padx=5, pady=5)
        
        # 强制压缩选项
        self.force_resize = tk.BooleanVar(value=False)
        ttk.Checkbutton(resolution_frame, text="强制压缩到目标分辨率(不保持宽高比)", variable=self.force_resize).grid(row=1, column=2, columnspan=2, sticky=tk.W, padx=5)
        
        # 转换选项
        options_frame = ttk.LabelFrame(main_frame, text="转换选项", padding="5")
        options_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.convert_to_jpg = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="转换为JPG格式", variable=self.convert_to_jpg).grid(row=0, column=0, sticky=tk.W, padx=5)
        
        ttk.Label(options_frame, text="JPG质量 (1-100):").grid(row=0, column=1, sticky=tk.W, padx=20)
        self.quality_var = tk.StringVar(value="95")
        ttk.Entry(options_frame, textvariable=self.quality_var, width=10).grid(row=0, column=2, padx=5)
        
        # 文件大小限制
        ttk.Label(options_frame, text="最大文件大小:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.max_size_var = tk.StringVar()
        max_size_combo = ttk.Combobox(options_frame, textvariable=self.max_size_var, 
                                     values=["无限制", "100KB", "500KB", "1MB", "2MB", "5MB"])
        max_size_combo.grid(row=1, column=1, padx=5, pady=5)
        max_size_combo.set("无限制")
        
        # 处理速度选项
        ttk.Label(options_frame, text="处理速度:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.speed_var = tk.StringVar(value="平衡")
        speed_combo = ttk.Combobox(options_frame, textvariable=self.speed_var, values=["最快", "平衡", "最佳质量"])
        speed_combo.grid(row=2, column=1, padx=5, pady=5)
        
        # 进度条
        ttk.Label(main_frame, text="进度:").grid(row=4, column=0, sticky=tk.W, pady=10)
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=500, mode='determinate')
        self.progress.grid(row=4, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=10, padx=5)
        
        # 日志框
        ttk.Label(main_frame, text="处理日志:").grid(row=5, column=0, sticky=tk.W, pady=(10, 0))
        
        # 添加滚动条到日志框
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=6, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_text = tk.Text(log_frame, height=12, width=70)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="开始处理", command=self.start_processing).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="退出", command=root.quit).pack(side=tk.LEFT, padx=5)
        
        # 配置网格权重
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        self.log("程序已启动，请选择输入和输出文件夹。")
        self.log("提示: 可以自定义宽度和高度，或使用比例缩放。")
    
    def browse_input(self):
        folder = filedialog.askdirectory()
        if folder:
            self.input_path.set(folder)
    
    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_path.set(folder)
    
    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
    
    def start_processing(self):
        if not self.input_path.get():
            messagebox.showerror("错误", "请选择输入文件夹")
            return
        
        if not self.output_path.get():
            messagebox.showerror("错误", "请选择输出文件夹")
            return
        
        # 检查输出目录是否存在，不存在则创建
        if not os.path.exists(self.output_path.get()):
            os.makedirs(self.output_path.get())
        
        # 在新线程中处理图片，避免UI冻结
        thread = threading.Thread(target=self.process_images)
        thread.daemon = True
        thread.start()
    
    def get_resize_method(self):
        speed_setting = self.speed_var.get()
        if speed_setting == "最快":
            return Image.Resampling.NEAREST
        elif speed_setting == "平衡":
            return Image.Resampling.BILINEAR
        else:  # 最佳质量
            return Image.Resampling.LANCZOS
    
    def get_max_size_bytes(self):
        """将最大文件大小字符串转换为字节数"""
        max_size_str = self.max_size_var.get()
        if max_size_str == "无限制":
            return None
        
        if "KB" in max_size_str:
            return int(float(max_size_str.replace("KB", "")) * 1024)
        elif "MB" in max_size_str:
            return int(float(max_size_str.replace("MB", "")) * 1024 * 1024)
        
        return None
    
    def optimize_jpg_quality(self, img, target_size_bytes, initial_quality=95):
        """优化JPG质量以满足目标文件大小"""
        # 如果不需要限制大小，直接返回初始质量
        if target_size_bytes is None:
            return initial_quality
        
        # 检查当前质量是否已经满足要求
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=initial_quality, optimize=True)
        current_size = buffer.getbuffer().nbytes
        
        if current_size <= target_size_bytes:
            return initial_quality
        
        # 使用二分查找找到满足要求的最高质量
        low, high = 10, initial_quality
        best_quality = low
        
        while low <= high:
            mid = (low + high) // 2
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=mid, optimize=True)
            current_size = buffer.getbuffer().nbytes
            
            if current_size <= target_size_bytes:
                best_quality = mid
                low = mid + 1
            else:
                high = mid - 1
        
        return best_quality
    
    def optimize_png_size(self, img, target_size_bytes):
        """优化PNG文件大小"""
        # 如果不需要限制大小，直接返回原图
        if target_size_bytes is None:
            return img
        
        # 尝试不同的优化级别
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        current_size = buffer.getbuffer().nbytes
        
        if current_size <= target_size_bytes:
            return img
        
        # 如果优化后仍然太大，尝试减少颜色深度
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            # 转换为RGB模式（去除透明度）
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        
        # 再次尝试保存
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        
        return img
    
    def process_images(self):
        input_dir = self.input_path.get()
        output_dir = self.output_path.get()
        
        # 获取所有PNG文件
        png_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.png')]
        
        if not png_files:
            self.log("在输入文件夹中未找到PNG文件。")
            return
        
        total_files = len(png_files)
        self.log(f"找到 {total_files} 个PNG文件，开始处理...")
        
        # 设置进度条
        self.progress['maximum'] = total_files
        self.progress['value'] = 0
        
        # 处理参数
        width_str = self.width_var.get().strip()
        height_str = self.height_var.get().strip()
        scale = float(self.scale_var.get())
        convert_to_jpg = self.convert_to_jpg.get()
        initial_quality = int(self.quality_var.get())
        force_resize = self.force_resize.get()
        resize_method = self.get_resize_method()
        max_size_bytes = self.get_max_size_bytes()
        
        # 解析宽度和高度
        width = None
        height = None
        
        if width_str:
            try:
                width = int(width_str)
            except ValueError:
                self.log(f"错误: 宽度 '{width_str}' 不是有效的数字")
                return
        
        if height_str:
            try:
                height = int(height_str)
            except ValueError:
                self.log(f"错误: 高度 '{height_str}' 不是有效的数字")
                return
        
        # 处理每个文件
        for i, filename in enumerate(png_files):
            try:
                input_path = os.path.join(input_dir, filename)
                
                # 打开图片
                with Image.open(input_path) as img:
                    original_width, original_height = img.size
                    
                    # 计算目标尺寸
                    if width is not None and height is not None and force_resize:
                        # 强制压缩到指定分辨率
                        target_size = (width, height)
                    elif width is not None and height is not None:
                        # 保持宽高比，计算最佳匹配尺寸
                        img_ratio = original_width / original_height
                        target_ratio = width / height
                        
                        if img_ratio >= target_ratio:
                            # 图片更宽，以宽度为准
                            new_width = width
                            new_height = int(width / img_ratio)
                        else:
                            # 图片更高，以高度为准
                            new_height = height
                            new_width = int(height * img_ratio)
                        
                        target_size = (new_width, new_height)
                    elif width is not None:
                        # 保持宽高比，根据宽度计算高度
                        new_width = width
                        new_height = int(original_height * (width / original_width))
                        target_size = (new_width, new_height)
                    elif height is not None:
                        # 保持宽高比，根据高度计算宽度
                        new_height = height
                        new_width = int(original_width * (height / original_height))
                        target_size = (new_width, new_height)
                    else:
                        # 按比例缩放
                        target_size = (int(original_width * scale), int(original_height * scale))
                    
                    # 调整大小
                    if target_size != img.size:
                        resized_img = img.resize(target_size, resize_method)
                    else:
                        resized_img = img
                    
                    # 确定输出文件名和格式
                    if convert_to_jpg:
                        output_filename = os.path.splitext(filename)[0] + '.jpg'
                        output_format = 'JPEG'
                        
                        # 如果原始图片有透明通道，转换为RGB
                        if resized_img.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', resized_img.size, (255, 255, 255))
                            background.paste(resized_img, mask=resized_img.split()[-1])
                            resized_img = background
                        
                        # 优化JPG质量以满足文件大小限制
                        final_quality = self.optimize_jpg_quality(resized_img, max_size_bytes, initial_quality)
                        
                        # 保存图片
                        output_path = os.path.join(output_dir, output_filename)
                        resized_img.save(output_path, format=output_format, quality=final_quality, optimize=True)
                        
                        # 获取最终文件大小
                        final_size = os.path.getsize(output_path)
                        size_info = f" 质量: {final_quality}, 大小: {self.format_file_size(final_size)}"
                    else:
                        output_filename = filename
                        output_format = 'PNG'
                        
                        # 优化PNG文件大小
                        if max_size_bytes:
                            resized_img = self.optimize_png_size(resized_img, max_size_bytes)
                        
                        # 保存图片
                        output_path = os.path.join(output_dir, output_filename)
                        resized_img.save(output_path, format=output_format, optimize=True)
                        
                        # 获取最终文件大小
                        final_size = os.path.getsize(output_path)
                        size_info = f" 大小: {self.format_file_size(final_size)}"
                
                self.log(f"成功处理: {filename} ({original_width}x{original_height} -> {target_size[0]}x{target_size[1]}){size_info}")
                
            except Exception as e:
                self.log(f"处理失败: {filename} - 错误: {str(e)}")
            
            # 更新进度条
            self.progress['value'] = i + 1
            self.root.update_idletasks()
        
        self.log("所有文件处理完成！")
    
    def format_file_size(self, size_bytes):
        """格式化文件大小显示"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.2f} KB"
        else:
            return f"{size_bytes/(1024*1024):.2f} MB"

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessor(root)
    root.mainloop()