import requests
import time
import random
import math

# 后端地址 (注意端口 8001)
API_URL = "http://127.0.0.1:8001/api/device/upload"

def simulate_watch():
    print("⌚ 智能穿戴设备模拟器已启动...")
    print(f"📡 目标服务器: {API_URL}")
    print("------------------------------------------------")
    
    t = 0
    while True:
        # 1. 模拟心率波动 (正弦波 + 随机噪音)
        # 模拟一个人在平静和轻微活动之间切换
        base_hr = 75 + 15 * math.sin(t * 0.1) 
        current_hr = int(base_hr + random.randint(-5, 5))
        
        # 2. 模拟连续血糖 (CGM)
        # 缓慢变化
        current_glucose = 100 + 10 * math.cos(t * 0.05) + random.uniform(-2, 2)
        
        # 3. 构造数据包
        payload = {
            "hr": current_hr,
            "glucose": round(current_glucose, 1),
            "steps": random.randint(0, 100) # 步数增量
        }
        
        try:
            # 发送 POST 请求
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                print(f"✅ [发送成功] HR: {current_hr} bpm | Glucose: {payload['glucose']} | Steps: {payload['steps']}")
            else:
                print(f"❌ 服务器报错: {response.status_code}")
        except Exception as e:
            print(f"❌ 连接失败: 请确保 main.py 正在运行! ({e})")
            
        time.sleep(2) # 每2秒发一次
        t += 1

if __name__ == "__main__":
    simulate_watch()