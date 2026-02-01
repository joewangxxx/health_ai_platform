import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from PIL import Image
import os
import sys

# ================= 🔧 路径修正 =================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.append(PROJECT_ROOT)

from backend.config import FOOD_MODEL_PATH, DATA_WAREHOUSE_DIR

# ================= ⚙️ 配置区域 =================
# 路径 (假设数据在 data_warehouse 下，或者你可以自定义)
# 注意：原代码使用了 C:\Users\王彬桥\Desktop...，建议迁移至 data_warehouse
# 这里为了演示，我将指向 data_warehouse
BASE_DATA_DIR = os.path.join(DATA_WAREHOUSE_DIR, "processed_data")
INDEX_FILE = os.path.join(BASE_DATA_DIR, "food_image_labels.csv")
MODEL_SAVE_PATH = FOOD_MODEL_PATH

# 超参数
BATCH_SIZE = 32       # 如果显存不够，改小一点 (16 or 8)
LEARNING_RATE = 0.001
EPOCHS = 10           # 图像训练比较慢，先跑10轮看看效果
IMG_SIZE = 224        # ResNet 标准输入尺寸

# 设备
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"🔥 视觉模型训练使用设备: {device}")
# ===============================================

# 1. 定义数据集类
class FoodDataset(Dataset):
    def __init__(self, csv_file, transform=None):
        self.data = pd.read_csv(csv_file)
        
        # 🔥 关键清洗：去除没有碳水数值 (NaN) 或 碳水为0 的图片
        # 我们只学习有意义的食物
        initial_len = len(self.data)
        self.data = self.data.dropna(subset=['carbs'])
        self.data = self.data[self.data['carbs'] > 0]
        
        print(f"🧹 数据清洗: 原始 {initial_len} 张 -> 有效 {len(self.data)} 张")
        
        self.transform = transform

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        # 获取图片路径
        img_path = self.data.iloc[idx]['image_path']
        # 获取标签 (Carbs) -> 转为 float32
        label = float(self.data.iloc[idx]['carbs'])
        
        try:
            # 打开图片并转为 RGB (防止有 PNG 透明通道报错)
            image = Image.open(img_path).convert('RGB')
            
            if self.transform:
                image = self.transform(image)
                
            return image, torch.tensor(label, dtype=torch.float32)
            
        except Exception as e:
            print(f"⚠️ 无法读取图片: {img_path} ({e})")
            # 如果读图失败，返回一个全黑图片代替，防止崩溃
            dummy_img = torch.zeros((3, IMG_SIZE, IMG_SIZE))
            return dummy_img, torch.tensor(0.0, dtype=torch.float32)

def train_cv_model():
    print("1. 准备数据增强与加载器...")
    
    # 图像预处理 (标准化是必须的，为了匹配预训练模型)
    data_transforms = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.RandomHorizontalFlip(), # 数据增强：随机翻转
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]) # ImageNet 标准均值方差
    ])

    dataset = FoodDataset(INDEX_FILE, transform=data_transforms)
    
    # Windows 下 num_workers 建议设为 0，否则可能报错
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)

    print("2. 加载预训练 ResNet-18 模型...")
    # 使用 weights=ResNet18_Weights.DEFAULT 替代旧版 pretrained=True
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    
    # 🥶 冻结前面的层 (Feature Extractor)
    # 我们不想重头训练识别线条和颜色，只想训练最后一层
    for param in model.parameters():
        param.requires_grad = False
        
    # 🔧 修改最后的全连接层 (FC Layer)
    # 原本是输出 1000 个分类 (猫, 狗...)，改为输出 1 个数值 (Carbs)
    num_ftrs = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Linear(num_ftrs, 128),
        nn.ReLU(),
        nn.Linear(128, 1) # 回归任务，输出1维
    )
    
    model = model.to(device)

    # 定义损失函数和优化器
    criterion = nn.MSELoss() # 均方误差
    # 只优化我们刚才修改的 fc 层，前面的层不动
    optimizer = optim.Adam(model.fc.parameters(), lr=LEARNING_RATE)

    print("\n🚀 开始训练视觉模型 (这可能需要几分钟)...")
    print("-" * 30)

    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        
        for i, (inputs, labels) in enumerate(dataloader):
            inputs = inputs.to(device)
            labels = labels.to(device).unsqueeze(1) # 变成 [Batch, 1] 形状
            
            optimizer.zero_grad()
            
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
            if i % 10 == 0 and i > 0:
                print(f"   [Epoch {epoch+1}, Batch {i}] Current Loss: {loss.item():.4f}")

        epoch_loss = running_loss / len(dataloader)
        print(f"🏁 Epoch {epoch+1}/{EPOCHS} 完成 | Avg Loss: {epoch_loss:.4f}")

    # 保存
    torch.save(model.state_dict(), MODEL_SAVE_PATH)
    print("\n" + "="*40)
    print(f"✅ 食物识别模型训练完成！")
    print(f"💾 模型已保存至: {MODEL_SAVE_PATH}")
    print("="*40)

if __name__ == "__main__":
    train_cv_model()
