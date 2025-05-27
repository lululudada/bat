import os
import shutil
import sys

def wait_for_key_press(prompt="按任意键继续..."):
    """跨平台的等待按键函数"""
    print(prompt)
    if sys.platform == 'win32':
        import msvcrt
        msvcrt.getch()
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def clear_folders():
    """清空图片处理文件夹"""
    print("=== 文件夹清理程序 ===")
    print("将清空以下文件夹内容：")
    
    # 定义文件夹路径
    current_folder = os.getcwd()
    folders_to_clear = [
        os.path.join(current_folder, "待处理图片"),
        os.path.join(current_folder, "处理后图片")
    ]
    

    
    # 执行清理
    deleted_count = 0
    print("\n开始清理...")
    
    for folder in folders_to_clear:
        if not os.path.exists(folder):
            print(f"[跳过] 文件夹不存在: {folder}")
            continue
        
        try:
            # 遍历文件夹内容
            for item in os.listdir(folder):
                item_path = os.path.join(folder, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.remove(item_path)
                        deleted_count += 1
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        deleted_count += 1
                except Exception as e:
                    print(f"[错误] 删除失败: {item_path} - {str(e)}")
            
            print(f"[完成] 已清空: {folder}")
        except Exception as e:
            print(f"[错误] 清理文件夹时出错: {folder} - {str(e)}")
    
    
    # 显示结果
    print("\n" + "="*40)
    print(f"清理完成！共删除 {deleted_count} 个项目")
    print("="*40)

if __name__ == "__main__":
    clear_folders()
    wait_for_key_press("\n按任意键退出程序...")