import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import warnings
import sys
warnings.filterwarnings("ignore")

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Input, LSTM, Dense, Dropout

print("TensorFlow Version:", tf.__version__)

df = pd.read_csv('c:/Users/AQI/aqi-vietnam/data/processed/pm25_training_data.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df_hn = df[df['city'] == 'Hà Nội'].sort_values('datetime').reset_index(drop=True)
FEATURES = ['pm25', 'temp', 'humidity', 'wind_speed', 'pressure', 'pm10']
TARGET_IDX = 0
df_lstm = df_hn[FEATURES].dropna()

scaler = MinMaxScaler()
data_scaled = scaler.fit_transform(df_lstm.values)

SEQ_LEN = 48
PRED_LEN = 24  # Dự đoán 24 tiếng tiếp theo

def create_sequences(data, seq_len, pred_len, target_idx=0):
    X, y = [], []
    for i in range(len(data) - seq_len - pred_len + 1):
        X.append(data[i : i + seq_len])
        y.append(data[i + seq_len : i + seq_len + pred_len, target_idx])
    return np.array(X), np.array(y)

X_all, y_all = create_sequences(data_scaled, SEQ_LEN, PRED_LEN)
train_split = int(len(X_all) * 0.70)
val_split   = int(len(X_all) * 0.85)
X_train, X_test = X_all[:train_split], X_all[val_split:]
y_train, y_test = y_all[:train_split], y_all[val_split:]
X_val = X_all[train_split:val_split]
y_val = y_all[train_split:val_split]

print("X_train shape:", X_train.shape)
print("y_train shape:", y_train.shape)

model_lstm = Sequential([
    Input(shape=(SEQ_LEN, len(FEATURES))),
    LSTM(64, return_sequences=True),
    Dropout(0.2),
    LSTM(32, return_sequences=False),
    Dropout(0.2),
    Dense(16, activation='relu'),
    Dense(PRED_LEN)  # Đầu ra 24 nơ-ron cho 24 tiếng
])
model_lstm.compile(optimizer='adam', loss='mse', metrics=['mae'])

# Train for just 1 epoch to see if it works
model_lstm.fit(X_train, y_train, epochs=1, batch_size=256, validation_data=(X_val, y_val), verbose=1)

y_pred_scaled = model_lstm.predict(X_test)
print("y_pred_scaled shape:", y_pred_scaled.shape)
print("y_test shape:", y_test.shape)

def inverse_pm25(scaled_values, scaler, target_idx, n_features):
    # scaled_values có dạng (N, pred_len)
    N, pred_len = scaled_values.shape
    dummy = np.zeros((N * pred_len, n_features))
    dummy[:, target_idx] = scaled_values.flatten()
    inv = scaler.inverse_transform(dummy)[:, target_idx]
    return inv.reshape(N, pred_len)

try:
    y_pred_actual = inverse_pm25(y_pred_scaled, scaler, TARGET_IDX, len(FEATURES))
    y_test_actual = inverse_pm25(y_test, scaler, TARGET_IDX, len(FEATURES))
    print("y_pred_actual shape:", y_pred_actual.shape)
    print("Success inverse transforming!")
except Exception as e:
    print("Error during inverse transform:")
    import traceback
    traceback.print_exc()

rmse = np.sqrt(mean_squared_error(y_test_actual, y_pred_actual))
mae  = mean_absolute_error(y_test_actual, y_pred_actual)
print(f"LSTM 24h-ahead -> RMSE: {rmse:.2f}, MAE: {mae:.2f}")


