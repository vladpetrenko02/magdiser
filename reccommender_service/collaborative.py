from sqlalchemy.orm import Session
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from db_service.models import Rating, UserSimilarity, UserRecommendationCollaborative # Враховуючи, що у вас є модель UserRating
from db_service.database import SessionLocal
import json

from sklearn.preprocessing import MinMaxScaler

def calculate_similarity_for_user(user_id: int, db: Session, top_n=50):
    """
    Обчислює подібність заданого користувача з іншими користувачами.

    :param user_id: ID користувача, для якого обчислюється подібність.
    :param db: Сесія бази даних.
    :param top_n: Кількість найбільш схожих користувачів, які потрібно зберегти.
    """
    # Завантаження оцінок з бази
    ratings = db.query(Rating).all()

    # Формування матриці оцінок
    user_ratings_dict = {}
    for rating in ratings:
        if rating.user_id not in user_ratings_dict:
            user_ratings_dict[rating.user_id] = {}
        user_ratings_dict[rating.user_id][rating.book_id] = rating.rating

    # Перевірка, чи заданий користувач має оцінки
    if user_id not in user_ratings_dict:
        print(f"Користувач {user_id} не має оцінок.")
        return

    user_ids = list(user_ratings_dict.keys())
    book_ids = list({rating.book_id for rating in ratings})

    # Створення матриці
    rating_matrix = np.zeros((len(user_ids), len(book_ids)))
    for i, uid in enumerate(user_ids):
        for j, book_id in enumerate(book_ids):
            rating_matrix[i, j] = user_ratings_dict[uid].get(book_id, 0)

    # Знаходимо індекс користувача
    user_index = user_ids.index(user_id)

    # Обчислення подібності заданого користувача з іншими
    user_similarity_scores = cosine_similarity(
        rating_matrix[user_index].reshape(1, -1), rating_matrix
    )[0]

    # Отримання індексів і значень топ-N найбільш схожих користувачів
    top_similar_indices = user_similarity_scores.argsort()[-top_n-1:-1][::-1]  # -1 для виключення self-similarity
    top_similar_users = {str(user_ids[j]): float(user_similarity_scores[j]) for j in top_similar_indices}

    # Видалення старих записів для користувача
    db.query(UserSimilarity).filter(UserSimilarity.user_id == user_id).delete(synchronize_session=False)

    # Збереження нових подібностей
    similarity_entry = UserSimilarity(
        user_id=user_id,
        similarities=top_similar_users
    )
    db.add(similarity_entry)
    db.commit()

    print(f"Подібність для користувача {user_id} успішно збережена (user_similarity).")

def calculate_user_similarity_top_n(db: Session, top_n=50):
    # Завантаження оцінок з бази
    ratings = db.query(Rating).all()
    print('Оцінки завантажено')
    # Формування матриці оцінок
    user_ratings_dict = {}
    for rating in ratings:
        if rating.user_id not in user_ratings_dict:
            user_ratings_dict[rating.user_id] = {}
        user_ratings_dict[rating.user_id][rating.book_id] = rating.rating

    user_ids = list(user_ratings_dict.keys())
    book_ids = list({rating.book_id for rating in ratings})

    # Створення матриці
    rating_matrix = np.zeros((len(user_ids), len(book_ids)))
    for i, user_id in enumerate(user_ids):
        for j, book_id in enumerate(book_ids):
            rating_matrix[i, j] = user_ratings_dict[user_id].get(book_id, 0)
    print('матриця оцінок створена')
    # Обчислення cosine similarity між користувачами
    user_similarity_matrix = cosine_similarity(rating_matrix)
    print('подібність обрахована')
    # Збереження 50 найбільш схожих користувачів у базу
    db.query(UserSimilarity).delete()  # Видалення старих даних
    count = 0
    for i, user_id in enumerate(user_ids):
        # Отримання індексів і значень топ-N найбільш схожих користувачів
        similarity_scores = user_similarity_matrix[i]
        top_similar_indices = similarity_scores.argsort()[-top_n-1:-1][::-1]  # -1 для виключення self-similarity
        top_similar_users = {str(user_ids[j]): float(similarity_scores[j]) for j in top_similar_indices}

        # Створення запису для користувача
        similarity_entry = UserSimilarity(
            user_id=user_id,
            similarities=top_similar_users
        )
        count +=1
        db.add(similarity_entry)

        print(f"Користувач {user_id} оброблений і доданий - крок {count}")
    db.commit()

# # Приклад використання
# db = SessionLocal()
# calculate_user_similarity_top_n(db, top_n=50)
# db.close()

def calculate_recommendations_for_user(user_id: int, db: Session):
    # Отримання схожих користувачів для заданого користувача
    user_similarity_entry = db.query(UserSimilarity).filter(UserSimilarity.user_id == user_id).first()
    if not user_similarity_entry:
        return {"error": "User similarity not found for this user."}

    similar_users = user_similarity_entry.similarities  # Це буде словник {user_id: similarity_score}

    # Завантаження оцінок схожих користувачів
    similar_users_ids = list(map(int, similar_users.keys()))
    similar_users_ratings = db.query(Rating).filter(Rating.user_id.in_(similar_users_ids)).all()

    # Організація оцінок схожих користувачів
    book_ratings = {}  # {book_id: [rating1, rating2, ...]}
    for rating in similar_users_ratings:
        if rating.book_id not in book_ratings:
            book_ratings[rating.book_id] = []
        book_ratings[rating.book_id].append(rating.rating * similar_users[str(rating.user_id)])  # Зважуємо рейтинг

    # Розрахунок середньозважених рекомендацій
    recommendations = {
        book_id: np.mean(ratings) for book_id, ratings in book_ratings.items()
    }

    if recommendations:
        book_ids = list(recommendations.keys())
        scores = np.array(list(recommendations.values())).reshape(-1, 1)

        scaler = MinMaxScaler()
        normalized_scores = scaler.fit_transform(scores).flatten()

        # Створюємо нормалізований словник
        recommendations = {book_id: score for book_id, score in zip(book_ids, normalized_scores)}

    for book_id in recommendations:
        if recommendations[book_id] == 1.0:
            noise = np.random.uniform(-0.02, -0.005)  # Шум у діапазоні [-0.02, -0.005]
            recommendations[book_id] = max(0, recommendations[book_id] + noise)  # Обмежуємо значення в [0, 1]

    # Сортування за зменшенням рекомендаційного скору
    sorted_recommendations = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)

    # Вибір максимум 50 найкращих рекомендацій
    top_50_recommendations = sorted_recommendations[:50]

    # Підготовка рекомендацій у форматі JSON
    recommendations_json = {str(book_id): score for book_id, score in top_50_recommendations}

    # Збереження рекомендацій у таблицю UserRecommendationCollaborative
    db.query(UserRecommendationCollaborative).filter(UserRecommendationCollaborative.user_id == user_id).delete()
    recommendation_entry = UserRecommendationCollaborative(
        user_id=user_id,
        recommendations=recommendations_json
    )
    db.add(recommendation_entry)
    db.commit()

    print(f"Топ-50 рекомендацій для користувача {user_id} збережено.")
    return recommendations_json


# # Приклад виклику
# db = SessionLocal()
# user_id_to_calculate = 6  # Вкажіть ID користувача
# recommendations = calculate_recommendations_for_user(user_id_to_calculate, db)
# db.close()

#print(recommendations)