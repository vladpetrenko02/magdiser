from sqlalchemy.orm import Session
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from db_service.models import BookFeature, Rating, BookSimilarity, UserRecommendation  # Враховуючи, що у вас є модель UserRating
from db_service.database import SessionLocal
import json
from sklearn.preprocessing import MinMaxScaler

def calculate_and_store_book_matrix_json(db: Session):
    # Завантаження характеристик книг із бази даних
    book_features = db.query(BookFeature).all()
    print('Характеристики завантажено')
    book_ids = [book.book_id for book in book_features]
    features_matrix = np.array([[book.feature_1, book.feature_2, book.feature_3] for book in book_features])

    # Обчислення cosine similarity між книгами
    similarity_matrix = cosine_similarity(features_matrix)
    print('схожість обрахована')
    # Видалення старих даних (опціонально)
    db.query(BookSimilarity).delete()
    print('старі записи видалено')
    count = 0
    # Збереження подібностей у форматі JSONB
    for i, book_id in enumerate(book_ids):
        similarities = {
            str(book_ids[j]): similarity_matrix[i][j]
            for j in range(len(book_ids)) if i != j  # Уникаємо self-similarity
        }
        similarity_entry = BookSimilarity(
            book_id=book_id,
            similarities=similarities
        )
        db.add(similarity_entry)
        count += 1
        print(count)
        db.commit()
        print('зміни зареєстровано')

    # Коміт змін

    print("Матриця подібності збережена у форматі JSONB")

# # Ініціалізація сесії бази даних
# db = SessionLocal()
#
# # Виклик функції для обчислення та збереження матриці
# calculate_and_store_book_matrix_json(db)
#
# # Закриття сесії
# db.close()

def calculate_recommendations_for_user(user_id: int, db: Session):
    """
    Розраховує рекомендації для конкретного користувача на основі оцінених ним книг.

    :param user_id: ID користувача
    :param db: Сесія бази даних
    """
    # Отримання оцінених книг користувачем
    user_ratings = db.query(Rating).filter(Rating.user_id == user_id).all()

    if not user_ratings:
        print(f"Користувач {user_id} не має оцінених книг.")
        return None

    # Отримуємо book_id та оцінки у форматі {book_id: rating}
    rated_books = {rating.book_id: rating.rating for rating in user_ratings}

    # Словник для зберігання коефіцієнтів рекомендацій
    recommendations = {}

    for rated_book_id, user_rating in rated_books.items():
        # Отримуємо подібності для оцінених книг із таблиці book_similarity
        book_similarity_entry = db.query(BookSimilarity).filter(BookSimilarity.book_id == rated_book_id).first()

        if not book_similarity_entry:
            continue

        # Завантаження подібностей у форматі JSON (якщо це не dict, то конвертуємо)
        if isinstance(book_similarity_entry.similarities, str):
            similar_books = json.loads(book_similarity_entry.similarities)
        else:
            similar_books = book_similarity_entry.similarities  # Уже dict

        for similar_book_id, similarity_score in similar_books.items():
            similar_book_id = int(similar_book_id)  # Перетворення на int
            if similar_book_id not in recommendations:
                recommendations[similar_book_id] = 0
            # Вносимо вклад до рекомендації, помноживши оцінку користувача на схожість
            recommendations[similar_book_id] += user_rating * similarity_score

    if recommendations:
        book_ids = list(recommendations.keys())
        scores = np.array(list(recommendations.values())).reshape(-1, 1)

        scaler = MinMaxScaler()
        normalized_scores = scaler.fit_transform(scores).flatten()

        # Створюємо нормалізований словник
        recommendations = {book_id: score for book_id, score in zip(book_ids, normalized_scores)}

        # Додавання шуму до значень, рівних 1.0
    for book_id in recommendations:
        if recommendations[book_id] == 1.0:
            noise = np.random.uniform(-0.02, -0.005)  # Шум у діапазоні [-0.02, -0.005]
            recommendations[book_id] = max(0, recommendations[book_id] + noise)  # Обмежуємо значення в [0, 1]

    # Вибір максимум 500 найкращих рекомендацій
    top_500_recommendations = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)[:8000]

    # Форматування у JSON для збереження
    recommendations_json = {str(book_id): score for book_id, score in top_500_recommendations}

    # Збереження результату в базу
    db.query(UserRecommendation).filter(UserRecommendation.user_id == user_id).delete()  # Видалення старих рекомендацій
    recommendation_entry = UserRecommendation(
        user_id=user_id,
        recommendations=recommendations_json
    )
    db.add(recommendation_entry)
    db.commit()

    print(f"Топ-8000 рекомендацій для користувача {user_id} успішно збережені.")
    return recommendations_json

# # Використання функції
# db = SessionLocal()
# user_id_to_calculate = 6  # ID користувача, для якого обчислюємо рекомендації
# recommendations = calculate_recommendations_for_user(user_id_to_calculate, db)
# db.close()

#print("Рекомендації:", recommendations)

# def get_user_ratings_from_db(db: Session):
#     # Завантаження всіх оцінок із таблиці user_ratings
#     user_ratings = db.query(Rating).all()
#     # Перетворення у словник формату {user_id: {book_id: rating}}
#     user_ratings_dict = {}
#     for rating in user_ratings:
#         if rating.user_id not in user_ratings_dict:
#             user_ratings_dict[rating.user_id] = {}
#         user_ratings_dict[rating.user_id][rating.book_id] = rating.rating
#     return user_ratings_dict
#
# def save_book_similarity_to_db(book_similarity, book_ids, db):
#     for i, book_id_1 in enumerate(book_ids):
#         for j, book_id_2 in enumerate(book_ids):
#             similarity = book_similarity[i][j]
#             similarity_entry = BookSimilarity(
#                 book_id_1=book_id_1,
#                 book_id_2=book_id_2,
#                 similarity=similarity
#             )
#             db.add(similarity_entry)
#     db.commit()
#
# def save_user_recommendations_to_db(user_ratings, book_similarity, book_ids, db):
#     for user_id, ratings in user_ratings.items():
#         user_ratings_vector = np.array([ratings.get(book_id, 0) for book_id in book_ids])
#         recommendations_raw = user_ratings_vector.dot(book_similarity)
#         recommendations = recommendations_raw / np.abs(book_similarity).sum(axis=1)
#
#         for book_id, score in zip(book_ids, recommendations):
#             recommendation_entry = UserRecommendation(
#                 user_id=user_id,
#                 book_id=book_id,
#                 recommendation_score=score
#             )
#             db.add(recommendation_entry)
#     db.commit()
#
#
# def get_book_features_from_db(db: Session):
#     # Завантаження характеристик із таблиці book_features
#     book_features = db.query(BookFeature).all()
#     # Створення словника {book_id: [feature_1, feature_2, ...]}
#     book_features_dict = {book.book_id: [book.feature_1, book.feature_2, book.feature_3] for book in book_features}
#     return book_features_dict
#
#
# def content_based_filtering(db: Session):
#     # Завантаження оцінок користувачів і характеристик книг із бази
#     user_ratings = get_user_ratings_from_db(db)
#     book_features = get_book_features_from_db(db)
#     print('Підтягнулось успішно')
#     # Підготовка даних для обчислення подібності
#     books = list(book_features.keys())
#     book_matrix = np.array([book_features[book] for book in books])
#     print('Підготувало дані книг')
#     # Обчислення cosine similarity між книгами
#     book_similarity = cosine_similarity(book_matrix)
#     content_recommendations = {}
#     print('Синус подібність пораховано')
#     for user, ratings in user_ratings.items():
#         print(f'Рахуємо для користувача {user}')
#         # Створення вектора оцінок користувача
#         user_ratings_vector = np.array([ratings.get(book, 0) for book in books])
#         print(f'Вектор оцінок {user_ratings_vector}')
#         # Обчислення рекомендацій для користувача на основі векторів подібності
#         recommendations = user_ratings_vector.dot(book_similarity) / np.array([np.abs(book_similarity).sum(axis=1)])
#         content_recommendations[user] = recommendations
#         print(content_recommendations)
#
#     return content_recommendations
#
# # Приклад виклику
# db = SessionLocal()
# recommendations = content_based_filtering(db)
# db.close()
#
# print(recommendations)
