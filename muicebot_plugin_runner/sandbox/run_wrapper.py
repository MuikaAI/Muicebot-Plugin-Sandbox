import subprocess
from pathlib import Path
import sys
import os

def main():
    print("[runner] Starting execution...")
    
    # 切换到工作目录
    os.chdir("/workspace")
    print(f"[runner] Working directory: {os.getcwd()}")
    print(f"[runner] Files in workspace: {list(Path('.').iterdir())}")
    
    # 安装依赖
    requirements = Path("requirements.txt")
    if requirements.exists():
        print("[runner] Installing dependencies...")
        try:
            result = subprocess.run(
                ["python", "-m", "pip", "install", "-r", "requirements.txt"], 
                capture_output=True, 
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                print("[runner] Dependencies installed successfully")
            else:
                print(f"[runner] Failed to install dependencies:")
                print(f"[runner] stdout: {result.stdout}")
                print(f"[runner] stderr: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("[runner] Dependency installation timed out")
        except Exception as e:
            print(f"[runner] Error installing dependencies: {e}")
    else:
        print("[runner] No requirements.txt found")

    # 检查输入文件
    input_file = Path("input_code.py")
    if not input_file.exists():
        print("[runner] Error: input_code.py not found!")
        print(f"[runner] Available files: {list(Path('.').iterdir())}")
        return

    print(f"[runner] Found input_code.py, size: {input_file.stat().st_size} bytes")

    print("[runner] Running script...")
    try:
        result = subprocess.run(
            ["python", "input_code.py"], 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        print(f"[runner] Script execution completed with return code: {result.returncode}")
        
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print(result.stderr, file=sys.stderr)
            
    except subprocess.TimeoutExpired:
        print("[runner] Script execution timed out")
    except Exception as e:
        print(f"[runner] Unexpected error during script execution: {e}")

    print("[runner] Execution finished")

if __name__ == "__main__":
    main()