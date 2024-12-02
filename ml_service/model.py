import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Input
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler
import joblib
import matplotlib.pyplot as plt
from tensorflow.keras.callbacks import EarlyStopping

# Шляхи до файлів
USER_ACTIVITIES_FILE = "C:/Users/Asus/PycharmProjects/HybridReccomenderServer/ml_service/data/user_activities_logical.csv"
COEFFICIENTS_FILE = "C:/Users/Asus/PycharmProjects/HybridReccomenderServer/ml_service/data/coefficients_logical.csv"
MODEL_FILE = "C:/Users/Asus/PycharmProjects/HybridReccomenderServer/ml_service/data/trained_model.keras"
CALER_X_FILE = "C:/Users/Asus/PycharmProjects/HybridReccomenderServer/ml_service/data/scaler_X.pkl"


def plot_loss(history):
  """
  Функція для побудови графіка втрат.

  Args:
    history: Історія навчання моделі, що повертається методом fit().
  """
  plt.plot(history.history['loss'])
  plt.plot(history.history['val_loss'])
  plt.title('Графік втрат')
  plt.ylabel('Втрати')
  plt.xlabel('Епоха')
  plt.legend(['Тренувальні', 'Валідаційні'], loc='upper right')
  plt.show()



def train_and_save_model():
    # Завантаження даних
    user_activities_df = pd.read_csv(USER_ACTIVITIES_FILE)
    coefficients_df = pd.read_csv(COEFFICIENTS_FILE)

    # Підготовка даних
    X = user_activities_df[["activity_count", "activity_recency", "activity_interval", "activity_intensity"]].values
    y = coefficients_df[["collaborative_coefficient", "content_coefficient"]].values

    # Нормалізація даних
    scaler_X = MinMaxScaler()
    X_scaled = scaler_X.fit_transform(X)

    # Розподіл на навчальну та тестову вибірки
    X_train, X_test = X_scaled[:1000], X_scaled[1000:]
    y_train, y_test = y[:1000], y[1000:]

    model = Sequential([
        Input(shape=(X_train.shape[1],)),  # Визначення форми вхідних даних
        Dense(16, activation="relu"),
        Dropout(0.2),  # Випадкове вимкнення 20% нейронів
        Dense(8, activation="relu"),
        Dense(2, activation="linear")
    ])

    # model = Sequential([
    #     Input(shape=(X_train.shape[1],)),  # Визначення форми вхідних даних
    #     Dense(64, activation="relu"),
    #     Dense(16, activation="relu"),
    #     Dense(2, activation="linear")
    # ])

    # Компіляція моделі
    model.compile(optimizer=Adam(learning_rate=0.01), loss="mse", metrics=["mse"])

    # # Навчання моделі
    early_stopping = EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True)
    history = model.fit(X_train, y_train, validation_split=0.2, batch_size=32, epochs=100, callbacks=[early_stopping])
    # history = model.fit(X_train, y_train, validation_split=0.2, batch_size=32, epochs=100)

    # Оцінка моделі на тестовій вибірці
    y_pred = model.predict(X_test)
    test_mse = mean_squared_error(y_test, y_pred)
    print(f"Середня квадратична помилка (MSE) на тестовій вибірці: {test_mse}")

    plot_loss(history)
    # Збереження моделі та нормалізаторів
    model.save(MODEL_FILE)
    joblib.dump(scaler_X, "C:/Users/Asus/PycharmProjects/HybridReccomenderServer/ml_service/data/scaler_X.pkl")
    print(f"Модель збережена у файл {MODEL_FILE}.")

# Виклик функції для навчання і збереження моделі
train_and_save_model()
