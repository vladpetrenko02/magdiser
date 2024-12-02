from sqlalchemy.orm import Session
from . import models, schemas

def create_user_activity(db: Session, activity: schemas.UserActivityCreate):
    db_activity = models.UserActivity(
        user_id=activity.user_id,
        activity_count=activity.activity_count,
        activity_recency=activity.activity_recency,
        activity_interval=activity.activity_interval,
        activity_intensity=activity.activity_intensity
    )
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    return db_activity

def save_prediction_result(db: Session, user_id: int, collaborative_coefficient: float, content_coefficient: float):
    db_result = models.PredictionResult(
        user_id=user_id,
        collaborative_coefficient=collaborative_coefficient,
        content_coefficient=content_coefficient
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

def get_user_activity(db: Session, user_id: str):
    return db.query(models.UserActivity).filter(models.UserActivity.user_id == user_id).all()

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.user_id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()