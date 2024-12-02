from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Float, JSON
from .database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class UserToken(Base):
    __tablename__ = "user_tokens"

    token_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    token = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    expired_at = Column(TIMESTAMP, nullable=False)

class UserActivity(Base):
    __tablename__ = "user_activities"

    activity_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    activity_count = Column(Float, nullable=False)
    activity_recency = Column(Float, nullable=False)
    activity_interval = Column(Float, nullable=False)
    activity_intensity = Column(Float, nullable=False)

class PredictionResult(Base):
    __tablename__ = "prediction_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    collaborative_coefficient = Column(Float, nullable=False)
    content_coefficient = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Book(Base):
    __tablename__ = "books"

    book_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    authors = Column(String, nullable=False)
    average_rating = Column(Float, nullable=False)
    genres = Column(String, nullable=False)
    image_url = Column(String, nullable=True)  # Посилання на обкладинку у стандартному розмірі
    small_image_url = Column(String, nullable=True)  # Посилання на обкладинку у меншому розмірі

class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    book_id = Column(Integer, nullable=False)
    rating = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())  # Час створення запису

class BookFeature(Base):
    __tablename__ = "book_features"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, nullable=False)
    feature_1 = Column(Float, nullable=False)
    feature_2 = Column(Float, nullable=False)
    feature_3 = Column(Float, nullable=False)

class BookSimilarity(Base):
    __tablename__ = "book_similarity"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, unique=True, index=True)
    similarities = Column(JSON)  # Зберігаємо JSON об'єкт

class UserRecommendation(Base):
    __tablename__ = "user_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    recommendations = Column(JSON)  # JSON поле для зберігання результатів рекомендацій
    created_at = Column(TIMESTAMP, server_default=func.now())  # Час створення запису

class UserSimilarity(Base):
    __tablename__ = "user_similarity"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    similarities = Column(JSON)  # JSON-об'єкт зі схожостями

class UserRecommendationCollaborative(Base):
    __tablename__ = "user_recommendations_collaborative"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    recommendations = Column(JSON, nullable=False)  # Результати у форматі JSON

class UserHybridRecommendations(Base):
    __tablename__ = "user_hybrid_recommendations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    recommendations = Column(JSON)  # Зберігаємо результати у форматі JSON
