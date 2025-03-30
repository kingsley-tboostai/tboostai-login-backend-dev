import subprocess
import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent))

def run_service(service_name, port):
    """运行单个服务"""
    cmd = [sys.executable, "run.py", service_name, str(port)]
    return subprocess.Popen(cmd)

def main():
    # 定义服务配置
    services = [
        ("auth", 8004),
        ("user", 8003),
        ("chat", 8001)
    ]
    
    # 启动所有服务
    processes = []
    for service, port in services:
        print(f"Starting {service} service on port {port}...")
        process = run_service(service, port)
        processes.append(process)
        time.sleep(2)  # 等待服务启动
    
    try:
        # 等待所有进程
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("\nShutting down all services...")
        # 终止所有进程
        for process in processes:
            process.terminate()
        print("All services stopped")

if __name__ == "__main__":
    main() 