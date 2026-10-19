"""
neural_net.py
Нейронная сеть для предсказания загруженности перекрестка.
Пошаговое обучение (1 клик = 1 эпоха), расчет потерь и точности, сохранение чекпоинта.
Встроена защита от сбоев DLL Windows с автоматическим переключением на чистый NumPy.
"""

import os
import json
from datetime import datetime
import pandas as pd
import numpy as np

# Защита от WinError 1114
USE_TORCH = False
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    USE_TORCH = True
except (ImportError, OSError, Exception):
    USE_TORCH = False


class NumpyMLP:
    """Полносвязная нейросеть на чистом NumPy (работает всегда без DLL)"""
    def __init__(self, in_features=7, hidden1=16, hidden2=8, out_features=1, lr=0.03):
        np.random.seed(42)
        self.lr = lr
        self.W1 = np.random.randn(in_features, hidden1) * np.sqrt(2.0 / in_features)
        self.b1 = np.zeros((1, hidden1))
        self.W2 = np.random.randn(hidden1, hidden2) * np.sqrt(2.0 / hidden1)
        self.b2 = np.zeros((1, hidden2))
        self.W3 = np.random.randn(hidden2, out_features) * np.sqrt(2.0 / hidden2)
        self.b3 = np.zeros((1, out_features))

    def sigmoid(self, x):
        return 1.0 / (1.0 + np.exp(-np.clip(x, -25.0, 25.0)))

    def relu(self, x):
        return np.maximum(0, x)

    def forward(self, X):
        self.X = X
        self.z1 = np.dot(X, self.W1) + self.b1
        self.a1 = self.relu(self.z1)
        self.z2 = np.dot(self.a1, self.W2) + self.b2
        self.a2 = self.relu(self.z2)
        self.z3 = np.dot(self.a2, self.W3) + self.b3
        self.y_pred = self.sigmoid(self.z3)
        return self.y_pred

    def backward(self, y_true):
        m = self.X.shape[0]
        d_out = (self.y_pred - y_true) * (self.y_pred * (1.0 - self.y_pred))
        
        dW3 = np.dot(self.a2.T, d_out) / m
        db3 = np.sum(d_out, axis=0, keepdims=True) / m
        
        da2 = np.dot(d_out, self.W3.T)
        dz2 = da2 * (self.z2 > 0)
        dW2 = np.dot(self.a1.T, dz2) / m
        db2 = np.sum(dz2, axis=0, keepdims=True) / m
        
        da1 = np.dot(dz2, self.W2.T)
        dz1 = da1 * (self.z1 > 0)
        dW1 = np.dot(self.X.T, dz1) / m
        db1 = np.sum(dz1, axis=0, keepdims=True) / m
        
        self.W3 -= self.lr * dW3
        self.b3 -= self.lr * db3
        self.W2 -= self.lr * dW2
        self.b2 -= self.lr * db2
        self.W1 -= self.lr * dW1
        self.b1 -= self.lr * db1

    def save_weights(self, filepath):
        weights = {
            'W1': self.W1.tolist(), 'b1': self.b1.tolist(),
            'W2': self.W2.tolist(), 'b2': self.b2.tolist(),
            'W3': self.W3.tolist(), 'b3': self.b3.tolist(),
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(weights, f, indent=2)


class TrafficTrainer:
    """Управляет пошаговым обучением нейросети (1 эпоха за клик)"""
    def __init__(self, csv_path="sensor_data.csv", lr=0.03):
        self.use_torch = USE_TORCH
        self.current_epoch = 0
        self.weights_dir = "weights"
        os.makedirs(self.weights_dir, exist_ok=True)
        
        self.prepare_data(csv_path)

        if self.use_torch:
            try:
                class TorchTrafficNet(nn.Module):
                    def __init__(self):
                        super().__init__()
                        self.net = nn.Sequential(
                            nn.Linear(7, 16), nn.ReLU(),
                            nn.Linear(16, 8), nn.ReLU(),
                            nn.Linear(8, 1), nn.Sigmoid()
                        )
                    def forward(self, x): return self.net(x)
                
                self.torch_model = TorchTrafficNet()
                self.criterion = nn.MSELoss()
                self.optimizer = optim.Adam(self.torch_model.parameters(), lr=lr)
                self.X_tensor = torch.tensor(self.x_norm, dtype=torch.float32)
                self.Y_tensor = torch.tensor(self.y_raw, dtype=torch.float32)
            except Exception:
                self.use_torch = False
                self.numpy_model = NumpyMLP(lr=lr)
        else:
            self.numpy_model = NumpyMLP(lr=lr)

    def prepare_data(self, csv_path):
        df = pd.read_csv(csv_path)
        feature_cols = [
            'cars_north', 'cars_south', 'cars_east', 'cars_west',
            'avg_speed', 'pedestrians_count', 'red_light_wait_sec'
        ]
        x_raw = df[feature_cols].values.astype(np.float32)
        self.x_mean = x_raw.mean(axis=0)
        self.x_std = x_raw.std(axis=0) + 1e-6
        self.x_norm = (x_raw - self.x_mean) / self.x_std
        self.y_raw = df['traffic_load'].values.astype(np.float32).reshape(-1, 1)

    def train_one_epoch(self):
        """1 нажатие кнопки = обучение 1 эпохи, расчет потерь, точности и сохранение весов"""
        start_time = datetime.now()
        self.current_epoch += 1

        if self.use_torch:
            self.torch_model.train()
            self.optimizer.zero_grad()
            preds = self.torch_model(self.X_tensor)
            loss_t = self.criterion(preds, self.Y_tensor)
            loss_t.backward()
            self.optimizer.step()
            loss_val = float(loss_t.item())
            
            with torch.no_grad():
                diff = torch.abs(preds - self.Y_tensor)
                accuracy = float((diff < 0.10).float().mean().item() * 100.0)
            save_path = os.path.join(self.weights_dir, f"model_epoch_{self.current_epoch}.pth")
            torch.save(self.torch_model.state_dict(), save_path)
        else:
            preds = self.numpy_model.forward(self.x_norm)
            loss_val = float(np.mean((preds - self.y_raw) ** 2))
            self.numpy_model.backward(self.y_raw)
            diff = np.abs(preds - self.y_raw)
            accuracy = float(np.mean(diff < 0.10) * 100.0)
            save_path = os.path.join(self.weights_dir, f"model_epoch_{self.current_epoch}.json")
            self.numpy_model.save_weights(save_path)

        return {
            'epoch': self.current_epoch,
            'start_time': start_time.strftime("%H:%M:%S"),
            'loss': round(loss_val, 4),
            'accuracy': round(accuracy, 2),
            'saved_model': save_path,
            'status': 'Сохранено успешно'
        }