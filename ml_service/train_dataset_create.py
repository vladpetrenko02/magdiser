import numpy as np
import pandas as pd

# Параметри для генерації даних
user_ids = range(1, 2001)
activity_count = np.random.randint(0, 21, 2000)  # Цілочисельна кількість активностей за день
activity_recency = np.random.uniform(1, 20, 2000)  # Чим більше число, тим менша давність
activity_interval = np.random.uniform(0, 20, 2000)
activity_intensity = activity_count  # Інтенсивність дорівнює кількості

# Розрахунок Activity_Total
activity_total = (
    0.6 * activity_count +
    0.2 * activity_recency +  # Велике activity_recency = менше часу з останньої активності
    0.15 * activity_interval +
    0.05 * activity_intensity
)

# Генерація коефіцієнтів на основі Activity_Total
collaborative_coefficient = np.clip(activity_total / activity_total.max(), 0, 1)
content_coefficient = np.clip(1 - collaborative_coefficient, 0, 1)

# Конвертація activity_count та activity_intensity у float для запису у файл
activity_count_float = activity_count.astype(float)
activity_intensity_float = activity_intensity.astype(float)

# Створення DataFrames
user_activities_logical_df = pd.DataFrame({
    "user_id": user_ids,
    "activity_count": activity_count_float,  # Записуємо у файл як float
    "activity_recency": activity_recency,   # Float
    "activity_interval": activity_interval, # Float
    "activity_intensity": activity_intensity_float,  # Записуємо у файл як float
})

coefficients_logical_df = pd.DataFrame({
    "user_id": user_ids,
    "collaborative_coefficient": collaborative_coefficient,
    "content_coefficient": content_coefficient,
})

# Збереження у CSV
user_activities_logical_df.to_csv("C:/Users/Asus/PycharmProjects/HybridReccomenderServer/ml_service/data/user_activities_logical.csv", index=False)
coefficients_logical_df.to_csv("C:/Users/Asus/PycharmProjects/HybridReccomenderServer/ml_service/data/coefficients_logical.csv", index=False)

print("Файли успішно створені: user_activities_logical.csv та coefficients_logical.csv")
