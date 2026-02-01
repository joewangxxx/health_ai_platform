import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from PIL import Image
import os
import time

# ================= ⚙️ 配置区域 =================
BASE_DIR = r"F:\health_ai_platform_2.0"
DATA_FILE = os.path.join(BASE_DIR, "data_warehouse", "processed_data", "food_nutrition_labels.csv")
MODEL_SAVE_PATH = os.path.join(BASE_DIR, "models", "nutrition_efficientnet.pth")

# 训练参数
BATCH_SIZE = 16       # 显存不够可调小至 8
LEARNING_RATE = 1e-4  # 学习率
EPOCHS = 15           # 训练轮数
IMG_SIZE = 224        # EfficientNet 标准输入

# 检测 GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ================= 📦 1. 定义数据集 =================
class NutritionDataset(Dataset):
    def __init__(self, csv_file, transform=None):
        self.data = pd.read_csv(csv_file)
        self.transform = transform

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        row = self.data.iloc[idx]
        img_path = row['image_path']
        
        # 🔥 核心：同时预测 4 个指标
        # 顺序：[Calories, Carbs, Protein, Fat]
        labels = torch.tensor([
            float(row['calories']), 
            float(row['carbs']), 
            float(row['protein']), 
            float(row['fat'])
        ], dtype=torch.float32)

        try:
            image = Image.open(img_path).convert('RGB')
            if self.transform:
                image = self.transform(image)
            return image, labels
        except Exception as e:
            # 如果某张图坏了，返回全黑图防止崩坏
            print(f"⚠️ 坏图跳过: {img_path}")
            return torch.zeros((3, IMG_SIZE, IMG_SIZE)), labels

# ================= 🏗️ 2. 定义训练流程 =================
def train_model():
    print(f"=== 🚀 启动 AI 营养师训练 (Device: {device}) ===")
    
    if not os.path.exists(DATA_FILE):
        print(f"❌ 找不到数据文件: {DATA_FILE}")
        return

    # 图像预处理与增强
    train_transforms = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15), # 随机旋转，增加鲁棒性
        transforms.ColorJitter(brightness=0.2, contrast=0.2), # 模拟不同光照
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # 加载数据
    dataset = NutritionDataset(DATA_FILE, transform=train_transforms)
    # 划分 90% 训练，10% 验证
    train_size = int(0.9 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0) # Win下num_workers设0更稳
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    print(f"📊 训练集: {len(train_dataset)} 张 | 验证集: {len(val_dataset)} 张")

    # 🔥 加载 EfficientNet-B0 (比 ResNet 更适合移动端/Web端，精度更高)
    print("🏗️ 加载 EfficientNet-B0 预训练模型...")
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    
    # 修改输出层
    # 原始 EfficientNet 输出是 1000 类，我们要改成 4 个回归值
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, 4)
    
    model = model.to(device)
    
    # 损失函数：L1 Loss (MAE) 对回归任务更友好，抗异常值干扰
    criterion = nn.L1Loss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    # 开始循环
    start_time = time.time()
    
    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        
        for i, (imgs, labels) in enumerate(train_loader):
            imgs, labels = imgs.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(imgs)
            
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
            if i % 50 == 0:
                print(f"   [Epoch {epoch+1}] Batch {i}/{len(train_loader)} Loss: {loss.item():.2f}")
        
        # 验证集测试
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                outputs = model(imgs)
                val_loss += criterion(outputs, labels).item()
        
        avg_train_loss = running_loss / len(train_loader)
        avg_val_loss = val_loss / len(val_loader)
        
        print(f"🏁 Epoch {epoch+1}/{EPOCHS} | Train Loss: {avg_train_loss:.2f} | Val Loss: {avg_val_loss:.2f}")

    total_time = (time.time() - start_time) / 60
    print(f"\n✅ 训练完成！耗时: {total_time:.1f} 分钟")
    
    # 保存模型
    torch.save(model.state_dict(), MODEL_SAVE_PATH)
    print(f"💾 模型已保存至: {MODEL_SAVE_PATH}")

if __name__ == "__main__":
    train_model()