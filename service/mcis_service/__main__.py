import uvicorn

from .config import Settings
from .main import create_app

if __name__ == "__main__":
    st = Settings()
    # 安全约束：只绑定回环地址
    uvicorn.run(create_app(st), host="127.0.0.1", port=st.port, log_level="info")
