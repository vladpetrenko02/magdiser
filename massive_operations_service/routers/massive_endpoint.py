from db_service.models import User,UserRecommendation,UserRecommendationCollaborative,UserHybridRecommendations, PredictionResult
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
from reccommender_service import collaborative, hybrid
from activity_collection_service import collect_all_activity_metrics

router = APIRouter()

@router.delete("/clear_all_recommendations")
def clear_all_recommendations(db: Session = Depends(get_db)):
    """
    Видаляє всі рекомендації для всіх користувачів.
    """
    db.query(UserRecommendation).delete(synchronize_session=False)
    db.query(UserRecommendationCollaborative).delete(synchronize_session=False)
    db.query(UserHybridRecommendations).delete(synchronize_session=False)
    db.commit()
    return {"message": "All recommendations cleared successfully."}

@router.post("/recalculate_recommendations_for_all")
def recalculate_recommendations_for_all(db: Session = Depends(get_db)):
    """
    Перерахунок рекомендацій для всіх користувачів.
    """
    users = db.query(User).all()
    for user in users:
        try:
            # Collaborative filtering
            collaborative.calculate_similarity_for_user(user.id, db, top_n=50)
            print(f"Collaborative similarity for user {user.id} calculated.")

            # Отримання коефіцієнтів
            prediction = (
                db.query(PredictionResult)
                .filter(PredictionResult.user_id == user.id)
                .order_by(PredictionResult.created_at.desc())
                .first()
            )
            collaborative_coefficient = prediction.collaborative_coefficient
            content_coefficient = prediction.content_coefficient

            # Hybrid recommendations
            hybrid.hybrid_recommendations_dynamic(
                user.id, db, collaborative_coefficient, content_coefficient
            )
            print(f"Hybrid recommendations for user {user.id} calculated.")
        except Exception as e:
            print(f"Error during recalculation for user {user.id}: {e}")
            continue
    return {"message": "Recommendations recalculated for all users."}

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

@router.post("/predict_for_all")
def predict_coefficients_for_all(db: Session = Depends(get_db)):
    """
    Прогнозує коефіцієнти для всіх користувачів.
    """
    if model is None or scaler_X is None:
        raise HTTPException(status_code=500, detail="Модель або нормалізатор не завантажено")

    users = db.query(models.UserActivity).all()
    for user_activity in users:
        X_new = np.array([[
            user_activity.activity_count,
            user_activity.activity_recency,
            user_activity.activity_interval,
            user_activity.activity_intensity
        ]])
        X_new_normalized = scaler_X.transform(X_new)
        prediction = model.predict(X_new_normalized)
        collaborative_coefficient = float(prediction[0][0])
        content_coefficient = float(prediction[0][1])

        try:
            crud.save_prediction_result(
                db=db,
                user_id=user_activity.user_id,
                collaborative_coefficient=collaborative_coefficient,
                content_coefficient=content_coefficient
            )
        except Exception as e:
            print(f"Error saving prediction for user {user_activity.user_id}: {e}")
    return {"message": "Coefficients predicted for all users."}

@router.post("/collect/activity_metrics")
def collect_all_activity_metrics_endpoint(db: Session = Depends(get_db)):
    collect_all_activity_metrics(db)
    return {"message": "All activity metrics collected successfully"}