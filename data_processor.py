"""
data_processor.py
Модуль предобработки данных с датчиков микроконтроллера.
Вычисляет целевой столбец 'traffic_load' (загруженность перекрестка) по формуле ЛР6.
"""

import os
import pandas as pd
import numpy as np

# Весовые коэффициенты формулы ЛР6
DEFAULT_WEIGHTS = {
    'w_cars': 0.45,       # Вес интенсивности потока машин
    'w_speed': 0.25,      # Вес снижения средней скорости
    'w_wait': 0.20,       # Вес времени ожидания красного сигнала
    'w_ped': 0.10,        # Вес пешеходного потока
}

DEFAULT_MAX_VALUES = {
    'max_cars': 120.0,    # Максимальная пропускная способность за такт
    'free_speed': 60.0,   # Свободная скорость движения (км/ч)
    'max_wait': 90.0,     # Максимальная задержка на светофоре (сек)
    'max_ped': 30.0,      # Максимальное число пешеходов
}


def calculate_traffic_load(df: pd.DataFrame, weights=None, max_vals=None) -> pd.DataFrame:
    """
    Вычисляет уровень загруженности перекрестка по формуле ЛР6:
    Load = w_cars * (N_total / max_cars) +
           w_speed * (1 - V_avg / free_speed) +
           w_wait * (T_wait / max_wait) +
           w_ped * (N_ped / max_ped)
    """
    w = weights or DEFAULT_WEIGHTS
    m = max_vals or DEFAULT_MAX_VALUES
    res = df.copy()

    total_cars = (
        res['cars_north'] + 
        res['cars_south'] + 
        res['cars_east'] + 
        res['cars_west']
    )
    res['total_cars'] = total_cars

    cars_term = np.clip(total_cars / m['max_cars'], 0.0, 1.0)
    speed_term = np.clip(1.0 - (res['avg_speed'] / m['free_speed']), 0.0, 1.0)
    wait_term = np.clip(res['red_light_wait_sec'] / m['max_wait'], 0.0, 1.0)
    ped_term = np.clip(res['pedestrians_count'] / m['max_ped'], 0.0, 1.0)

    load_score = (
        cars_term * w['w_cars'] +
        speed_term * w['w_speed'] +
        wait_term * w['w_wait'] +
        ped_term * w['w_ped']
    )
    res['traffic_load'] = np.round(np.clip(load_score, 0.0, 1.0), 3)

    conditions = [
        res['traffic_load'] < 0.38,
        (res['traffic_load'] >= 0.38) & (res['traffic_load'] < 0.70),
        res['traffic_load'] >= 0.70
    ]
    choices = ['Низкая', 'Средняя', 'Высокая']
    res['load_category'] = np.select(conditions, choices, default='Низкая')
    return res


def generate_sample_sensor_csv(filepath="sensor_data.csv"):
    """Создает пример файла с датчиков микроконтроллера, если его еще нет"""
    if os.path.exists(filepath):
        return filepath

    data = {
        'time': ['08:00', '08:15', '08:30', '08:45', '09:00', '11:30', '14:00', '17:30', '18:00', '19:00', '21:00', '23:00'],
        'cars_north': [28, 35, 42, 38, 24, 15, 20, 44, 46, 31, 12, 6],
        'cars_south': [26, 34, 40, 37, 22, 16, 18, 46, 48, 29, 14, 5],
        'cars_east': [14, 19, 28, 25, 15, 10, 12, 32, 35, 18, 8, 4],
        'cars_west': [12, 22, 30, 27, 14, 9, 14, 29, 34, 20, 6, 3],
        'avg_speed': [38.0, 24.0, 14.0, 18.0, 42.0, 52.0, 48.0, 11.0, 9.0, 29.0, 55.0, 58.0],
        'pedestrians_count': [8, 15, 22, 19, 12, 4, 6, 28, 26, 14, 3, 1],
        'red_light_wait_sec': [32, 54, 78, 68, 28, 18, 22, 85, 89, 45, 15, 10],
    }
    df = pd.DataFrame(data)
    df = calculate_traffic_load(df)
    df.to_csv(filepath, index=False, encoding='utf-8')
    return filepath