from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import crud, models, schemas
from db_service.models import Book,Rating, UserHybridRecommendations, UserActivity, UserRecommendation, UserRecommendationCollaborative, PredictionResult
from db_service.schemas import GenreRequest
from reccommender_service import content_based, collaborative, hybrid
from jose import jwt
import json
from datetime import datetime, timedelta

from datetime import datetime, timedelta


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = "your_secret_key"  # Замініть на ваш реальний секретний ключ
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_user_token(db: Session, user_id: int, token: str, expire: datetime):
    user_token = models.UserToken(
        user_id=user_id,
        token=token,
        expired_at=expire
    )
    db.add(user_token)
    db.commit()
    db.refresh(user_token)
    return user_token

def create_access_token(data: dict):
    """
    Створює JWT токен з даними користувача.

    Parameters:
    - data (dict): С

    Returns:ловник із даними для кодування (наприклад, user_id).
    - str: Згенерований JWT токен.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from collections import Counter


@router.get("/genres")
def get_top_genres(db: Session = Depends(get_db)):
    """
    Отримує 20 найпопулярніших жанрів, видаляючи складні комбінації жанрів.
    """
    genres = db.query(Book.genres).distinct().all()

    # Розбиття і очищення жанрів
    cleaned_genres = [
        genre.split(",")[0].strip()  # Беремо тільки перший жанр до коми
        for row in genres for genre in row[0].split(";") if genre.strip()
    ]

    # Підрахунок кількості згадувань кожного жанру
    genre_counter = Counter(cleaned_genres)

    # Вибір топ-20 жанрів
    top_genres = [genre for genre, _ in genre_counter.most_common(20)]

    return {"genres": sorted(top_genres)}

from sqlalchemy import or_

@router.post("/books_by_genres")
def get_books_by_genres(request: GenreRequest, db: Session = Depends(get_db)):
    genres = request.genres
    if len(genres) < 4:
        raise HTTPException(status_code=400, detail="Select at least 4 genres")

    books = db.query(Book).filter(
        or_(*[Book.genres.like(f"%{genre}%") for genre in genres])
    ).order_by(Book.average_rating.desc()).limit(20).all()

    return {
        "books": [
            {
                "book_id": book.book_id,
                "image_url": book.image_url,
                "title": book.title,
                "authors": book.authors,
                "average_rating": book.average_rating,
            }
            for book in books
        ]
    }

@router.get("/check_user_ratings/{user_id}")
def check_user_ratings(user_id: int, db: Session = Depends(get_db)):
    has_ratings = db.query(Rating).filter(Rating.user_id == user_id).first() is not None
    return {"has_ratings": has_ratings}

@router.post("/rate_book")
def rate_book(rating_data: dict, db: Session = Depends(get_db)):
    user_id = rating_data.get("user_id")
    book_id = rating_data.get("book_id")
    rating_value = rating_data.get("rating")
    print(rating_value)
    print(user_id)
    print(book_id)

    rating_value = int(rating_value)
    if not (1 <= rating_value <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Додавання або оновлення рейтингу
    rating_entry = db.query(Rating).filter(
        Rating.user_id == user_id, Rating.book_id == book_id
    ).first()

    if rating_entry:
        rating_entry.rating = rating_value
    else:
        new_rating = Rating(user_id=user_id, book_id=book_id, rating=rating_value)
        db.add(new_rating)

    db.commit()
    return {"message": "Rating saved successfully"}

@router.get("/users/{user_id}")
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    try:
        # Перевірка та декодування JWT токена
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_user_id = payload.get("user_id")
        if token_user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token: user_id missing")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token is invalid")

    # Дозволяємо доступ лише до даних авторизованого користувача
    if token_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Отримання даних користувача з бази даних
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user.user_id, "username": user.username}

@router.post("/users/", response_model=schemas.UserWithToken)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Перевірка, чи вже існує користувач з таким ім'ям
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Хешуємо пароль і створюємо користувача
    hashed_password = pwd_context.hash(user.password)
    new_user = models.User(
        username=user.username,
        password_hash=hashed_password,
        email=user.email
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Генеруємо JWT токен
    access_token = create_access_token(data={"user_id": new_user.user_id})
    expire_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Зберігаємо токен у базі
    create_user_token(db, user_id=new_user.user_id, token=access_token, expire=expire_at)

    # Повертаємо дані користувача разом із токеном
    return {
        "user": new_user,
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.delete("/clear_user_recommendations/{user_id}")
def clear_user_recommendations(user_id: int, db: Session = Depends(get_db)):
    """
    Видалення всіх рекомендацій для вказаного користувача.
    """

    recommendations = db.query(UserRecommendation).filter(UserRecommendation.user_id == user_id)
    if recommendations.count() != 0:
        recommendations.delete(synchronize_session=False)

    recommendations = db.query(UserRecommendationCollaborative).filter(UserRecommendationCollaborative.user_id == user_id)
    if recommendations.count() != 0:
        recommendations.delete(synchronize_session=False)

    recommendations = db.query(UserHybridRecommendations).filter(UserHybridRecommendations.user_id == user_id)
    if recommendations.count() != 0:
        recommendations.delete(synchronize_session=False)

    db.commit()
    return {"message": "Recommendations cleared successfully."}


@router.post("/recalculate_recommendations/{user_id}")
def recalculate_recommendations(user_id: int, db: Session = Depends(get_db)):
    """
    Викликає розрахунок рекомендацій для конкретного користувача.

    :param user_id: ID користувача
    :param db: Сесія бази даних
    """
    try:
        # Collaborative filtering
        collaborative.calculate_similarity_for_user(user_id, db, top_n=50)
        print(f"Collaborative similarity for user {user_id} calculated.")

        prediction = (
            db.query(PredictionResult)
            .filter(PredictionResult.user_id == user_id)
            .order_by(PredictionResult.created_at.desc())
            .first()
        )

        collaborative_coefficient = prediction.collaborative_coefficient  # Замініть на фактичну назву поля
        content_coefficient = prediction.content_coefficient  # Замініть на фактичну назву поля
        print(f"Вага колаборативної є - {collaborative_coefficient}")
        print(f"Вага контеної є - {content_coefficient}")

        # Hybrid recommendations
        hybrid.hybrid_recommendations_dynamic(user_id, db, collaborative_coefficient, content_coefficient)
        print(f"Hybrid recommendations for user {user_id} calculated.")

        return {"detail": f"Recommendations successfully recalculated for user {user_id}"}
    except Exception as e:
        print(f"Error during recalculation for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error during recommendation recalculation: {str(e)}")

@router.get("/recommendations/{type}/{user_id}")
def get_recommendations(type: str, user_id: int, db: Session = Depends(get_db)):
    """
    Отримати рекомендації для користувача.
    Тип може бути: 'content', 'collaborative', 'hybrid'.
    """
    if type == "content":
        entry = db.query(UserRecommendation).filter(UserRecommendation.user_id == user_id).first()
    elif type == "collaborative":
        entry = db.query(UserRecommendationCollaborative).filter(UserRecommendationCollaborative.user_id == user_id).first()
    elif type == "hybrid":
        entry = db.query(UserHybridRecommendations).filter(UserHybridRecommendations.user_id == user_id).first()
    else:
        raise HTTPException(status_code=400, detail="Invalid recommendation type")

    if not entry:
        raise HTTPException(status_code=404, detail=f"{type.capitalize()} recommendations not found")

    if isinstance(entry.recommendations, dict):
        recommendations = entry.recommendations
    else:
        recommendations = json.loads(entry.recommendations)  # Розпакувати JSON, якщо це str

    book_ids = list(recommendations.keys())[:20]  # Взяти максимум 20 книг

    # Підтягнути інформацію про книги
    books = db.query(Book).filter(Book.book_id.in_(book_ids)).all()

    # Відформатувати книги
    return {
        "books": [
            {
                "book_id": book.book_id,
                "title": book.title,
                "authors": book.authors,
                "average_rating": book.average_rating,
                "image_url": book.image_url,
            }
            for book in books
        ]
    }

@router.get("/books")
def get_books(
    title: str = None,
    author: str = None,
    genre: str = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    # Запит до таблиці Book
    query = db.query(Book)

    # Фільтрація за частиною назви
    if title:
        query = query.filter(Book.title.ilike(f"%{title}%"))

    # Фільтрація за авторами (пошук у текстовому полі)
    if author:
        query = query.filter(Book.authors.ilike(f"%{author}%"))

    # Фільтрація за жанрами (пошук у текстовому полі)
    if genre:
        query = query.filter(Book.genres.ilike(f"%{genre}%"))  # genres - текстове поле з комами

    # Підрахунок книг
    total_books = query.count()
    total_pages = (total_books + limit - 1) // limit

    # Пагінація
    books = query.offset((page - 1) * limit).limit(limit).all()

    # Серіалізація результатів
    serialized_books = [
        {
            "book_id": book.book_id,
            "title": book.title,
            "authors": book.authors,
            "genres": book.genres.split(", "),  # Перетворюємо текстове поле у список
            "image_url": book.image_url
        }
        for book in books
    ]

    return {
        "books": serialized_books,
        "total_pages": total_pages,
        "current_page": page
    }

@router.post("/add_activity")
def add_activity(
    user_id: int = Body(...),
    activity_count: int = Body(...),
    activity_recency: float = Body(...),
    activity_interval: float = Body(...),
    activity_intensity: int = Body(...),
    db: Session = Depends(get_db)
):
    """
    Додає або оновлює активність для вказаного користувача.

    :param user_id: ID користувача
    :param activity_count: Кількість активностей
    :param activity_recency: Свіжість активностей
    :param activity_interval: Інтервал активностей
    :param activity_intensity: Інтенсивність активностей
    :param db: Сесія бази даних
    :return: Повідомлення про успішне додавання
    """
    try:
        # Перевіряємо, чи існує активність для цього користувача
        user_activity = db.query(UserActivity).filter(UserActivity.user_id == user_id).first()

        if user_activity:
            # Оновлюємо наявну активність
            user_activity.activity_count = activity_count
            user_activity.activity_recency = activity_recency
            user_activity.activity_interval = activity_interval
            user_activity.activity_intensity = activity_intensity
        else:
            # Створюємо нову активність
            user_activity = UserActivity(
                user_id=user_id,
                activity_count=activity_count,
                activity_recency=activity_recency,
                activity_interval=activity_interval,
                activity_intensity=activity_intensity,
            )
            db.add(user_activity)

        db.commit()
        return {"message": "Activity successfully added or updated."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

