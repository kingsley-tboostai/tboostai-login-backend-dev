import uvicorn
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent))

if __name__ == "__main__":
    # 根据命令行参数选择要运行的服务
    if len(sys.argv) > 1:
        service = sys.argv[1]
        port = int(sys.argv[2]) if len(sys.argv) > 2 else None
        
        if service == "auth":
            port = port or 8004
            uvicorn.run("auth.auth:app", host="0.0.0.0", port=port, reload=True)
        elif service == "user":
            port = port or 8003
            uvicorn.run("user_api.user_backend:app", host="0.0.0.0", port=port, reload=True)
        elif service == "chat":
            port = port or 8001
            uvicorn.run("agent_chat.chat_backend:app", host="0.0.0.0", port=port, reload=True)
        else:
            print("Invalid service. Use: auth, user, or chat")
    else:
        print("Please specify which service to run: auth, user, or chat") 