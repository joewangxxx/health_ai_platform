import uvicorn
import os
import sys

# 强制设置标准输出为 UTF-8，避免 Windows 控制台下打印 Emoji 报错
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to sys.path explicitly to be safe
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    reload_enabled = os.getenv("HEALTHAI_RELOAD", "0") == "1"
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=reload_enabled)
