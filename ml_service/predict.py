from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import numpy as np
import os
from tensorflow.keras.models import load_model
import joblib
from sklearn.preprocessing import MinMaxScaler
from db_service import models
from db_service.routers.users import get_db
from db_service import crud

router = APIRouter()

MODEL_FILE = "C:/Users/Asus/PycharmProjects/HybridReccomenderServer/ml_service/data/trained_model.keras"
SCALER_X_FILE = "C:/Users/Asus/PycharmProjects/HybridReccomenderServer/ml_service/data/scaler_X.pkl"

# Завантаження моделі
if os.path.exists(MODEL_FILE):
    model = load_model(MODEL_FILE)
    print("Модель успішно завантажена.")
else:
    model = None
    print("Модель не знайдена. Переконайтесь, що модель навчена і збережена.")

# Завантаження нормалізатора
if os.path.exists(SCALER_X_FILE):
    scaler_X = joblib.load(SCALER_X_FILE)
    if not isinstance(scaler_X, MinMaxScaler):
        raise ValueError("Нормалізатор має неправильний тип. Очікується MinMaxScaler.")
    print("Нормалізатор успішно завантажено.")
else:
    scaler_X = None
    print("Нормалізатор не знайдено. Переконайтесь, що нормалізатор збережений.")

@router.post("/predict/{user_id}")
def predict_coefficients(user_id: int, db: Session = Depends(get_db)):
    # Перевірка активностей користувача
    user_activity = db.query(models.UserActivity).filter(models.UserActivity.user_id == user_id).first()
    if user_activity is None:
        raise HTTPException(status_code=404, detail=f"Активності для користувача з ID {user_id} не знайдено")

    # Перевірка, чи модель і нормалізатор завантажені
    if model is None:
        raise HTTPException(status_code=500, detail="Модель не завантажена")
    if scaler_X is None:
        raise HTTPException(status_code=500, detail="Нормалізатор не завантажено")

    # Підготовка даних
    X_new = np.array([[
        user_activity.activity_count,
        user_activity.activity_recency,
        user_activity.activity_interval,
        user_activity.activity_intensity
    ]])
    X_new_normalized = scaler_X.transform(X_new)

    # Прогнозування
    prediction = model.predict(X_new_normalized)
    collaborative_coefficient = float(prediction[0][0])
    content_coefficient = float(prediction[0][1])

    # Збереження результатів
    try:
        crud.save_prediction_result(
            db=db,
            user_id=user_id,
            collaborative_coefficient=collaborative_coefficient,
            content_coefficient=content_coefficient
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка при збереженні результатів: {str(e)}")

    # Повернення результатів
    return {
        "user_id": user_id,
        "collaborative_coefficient": collaborative_coefficient,
        "content_coefficient": content_coefficient
    }
