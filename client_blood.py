# -*- coding: utf-8 -*-
"""bloodmnist.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/15Gn6cZEWv0b7TepR_w9pYR6yijbzOA4S
"""

!pip install medmnist

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import transforms
import medmnist
from medmnist import INFO
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
import seaborn as sns
from PIL import Image

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# 1. Load BloodMNIST dataset
data_flag = 'bloodmnist'
info = INFO[data_flag]
n_classes = len(info['label'])
DataClass = getattr(medmnist, info['python_class'])

# Data transformations with augmentation
train_transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.RandomRotation(10),
    transforms.RandomHorizontalFlip(),
    transforms.Normalize(mean=[0.5], std=[0.5])
])

test_transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5], std=[0.5])
])

# Load datasets
train_dataset = DataClass(split='train', transform=train_transform, download=True)
val_dataset = DataClass(split='val', transform=test_transform, download=True)
test_dataset = DataClass(split='test', transform=test_transform, download=True)

# Data loaders
batch_size = 128
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

# 2. Define model for BloodMNIST
class BloodCellClassifier(nn.Module):
    def __init__(self, num_classes=n_classes):
        super(BloodCellClassifier, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)
        )
        self.classifier = nn.Sequential(
            nn.Linear(128 * 3 * 3, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x

model = BloodCellClassifier().to(device)

# 3. Training setup
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', patience=3)

# 4. Training function with history tracking
def train_model(model, train_loader, val_loader, criterion, optimizer, num_epochs=25):
    history = {'train_loss': [], 'train_acc': [], 'val_loss': [], 'val_acc': []}

    for epoch in range(num_epochs):
        model.train()
        running_loss, running_correct, total = 0.0, 0, 0

        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.squeeze().long().to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, preds = torch.max(outputs, 1)
            running_correct += (preds == targets).sum().item()
            total += targets.size(0)

        train_loss = running_loss / len(train_loader)
        train_acc = running_correct / total

        # Validation
        val_loss, val_acc = evaluate_model(model, val_loader, criterion)
        scheduler.step(val_loss)

        # Update history
        history['train_loss'].append(train_loss)
        history['train_acc'].append(train_acc)
        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)

        print(f'Epoch {epoch+1}/{num_epochs}: '
              f'Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}, '
              f'Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}')

    return history

# 5. Evaluation function
def evaluate_model(model, data_loader, criterion):
    model.eval()
    running_loss, running_correct, total = 0.0, 0, 0

    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs, targets = inputs.to(device), targets.squeeze().long().to(device)

            outputs = model(inputs)
            loss = criterion(outputs, targets)

            running_loss += loss.item()
            _, preds = torch.max(outputs, 1)
            running_correct += (preds == targets).sum().item()
            total += targets.size(0)

    return running_loss / len(data_loader), running_correct / total

# 6. Train the model
history = train_model(model, train_loader, val_loader, criterion, optimizer)

# 7. Plot training history
plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(history['train_loss'], label='Train Loss')
plt.plot(history['val_loss'], label='Validation Loss')
plt.title('Training and Validation Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(history['train_acc'], label='Train Accuracy')
plt.plot(history['val_acc'], label='Validation Accuracy')
plt.title('Training and Validation Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()
plt.tight_layout()
plt.show()

# 8. Confusion Matrix
def plot_confusion_matrix(model, data_loader):
    model.eval()
    all_preds = []
    all_targets = []
    class_names = ['basophil', 'eosinophil', 'erythroblast',
                  'immature granulocytes', 'lymphocyte',
                  'monocyte', 'neutrophil', 'platelet']

    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs, targets = inputs.to(device), targets.squeeze().long().to(device)
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(targets.cpu().numpy())

    cm = confusion_matrix(all_targets, all_preds)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=class_names, yticklabels=class_names)
    plt.title('Confusion Matrix for Blood Cell Classification')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.xticks(rotation=45)
    plt.yticks(rotation=0)
    plt.show()

plot_confusion_matrix(model, test_loader)

# 9. Predict and visualize single image
def predict_and_visualize(model, dataset, index=0):
    model.eval()
    image, label = dataset[index]
    image = image.to(device).unsqueeze(0)

    with torch.no_grad():
        output = model(image)
        _, pred = torch.max(output, 1)
        probs = torch.softmax(output, dim=1)[0] * 100

    # Convert image for display
    img = image.squeeze().permute(1, 2, 0).cpu().numpy()
    img = (img - img.min()) / (img.max() - img.min())

    # Get class names
    class_names = ['basophil', 'eosinophil', 'erythroblast',
                  'immature granulocytes', 'lymphocyte',
                  'monocyte', 'neutrophil', 'platelet']

    plt.figure(figsize=(8, 6))
    plt.imshow(img)
    plt.title(f'Actual: {class_names[label.item()]}\n'
              f'Predicted: {class_names[pred.item()]}\n'
              f'Confidence: {probs[pred.item()]:.2f}%')
    plt.axis('off')

    # Show probability distribution
    plt.figure(figsize=(10, 4))
    plt.bar(class_names, probs.cpu().numpy())
    plt.title('Prediction Probabilities')
    plt.xlabel('Blood Cell Types')
    plt.ylabel('Probability (%)')
    plt.xticks(rotation=45)
    plt.ylim(0, 100)
    plt.show()

    return pred.item()

# Example prediction
sample_idx = 42  # Try different indices
prediction = predict_and_visualize(model, test_dataset, sample_idx)
print(f"Predicted class index: {prediction}")

