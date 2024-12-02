from sqlalchemy.orm import Session
import numpy as np
import json
from db_service.models import UserRecommendation, Rating, UserSimilarity, BookSimilarity, UserRecommendationCollaborative  # Враховуючи, що у вас є модель UserRating
from db_service.database import SessionLocal
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

def calculate_similarity_for_user_with_limited_ratings(user_id: int, db: Session, top_n=50, max_ratings=60):
    """
    Обчислює подібність користувача з іншими на основі обмеженої кількості оцінок.

    :param user_id: ID користувача.
    :param db: Сесія бази даних.
    :param top_n: Кількість найбільш схожих користувачів.
    :param max_ratings: Максимальна кількість оцінок для врахування.
    """
    # Завантаження всіх оцінок користувача
    user_ratings = db.query(Rating).filter(Rating.user_id == user_id).order_by(Rating.book_id).limit(max_ratings).all()

    if not user_ratings:
        print(f"Користувач {user_id} не має достатньо оцінок.")
        return

    # Формуємо матрицю оцінок з урахуванням обмеження
    ratings = db.query(Rating).all()
    user_ratings_dict = {}
    for rating in ratings:
        if rating.user_id not in user_ratings_dict:
            user_ratings_dict[rating.user_id] = {}
        user_ratings_dict[rating.user_id][rating.book_id] = rating.rating

    user_ids = list(user_ratings_dict.keys())
    book_ids = list({rating.book_id for rating in ratings})

    # Створення матриці
    rating_matrix = np.zeros((len(user_ids), len(book_ids)))
    for i, uid in enumerate(user_ids):
        for j, book_id in enumerate(book_ids):
            rating_matrix[i, j] = user_ratings_dict[uid].get(book_id, 0)

    # Знаходимо індекс користувача
    user_index = user_ids.index(user_id)

    # Обчислення подібності
    user_similarity_scores = cosine_similarity(
        rating_matrix[user_index].reshape(1, -1), rating_matrix
    )[0]

    # Отримання топ-N схожих користувачів
    top_similar_indices = user_similarity_scores.argsort()[-top_n - 1:-1][::-1]
    top_similar_users = {str(user_ids[j]): float(user_similarity_scores[j]) for j in top_similar_indices}

    # Оновлення в базі
    db.query(UserSimilarity).filter(UserSimilarity.user_id == user_id).delete(synchronize_session=False)
    similarity_entry = UserSimilarity(
        user_id=user_id,
        similarities=top_similar_users
    )
    db.add(similarity_entry)
    db.commit()

    print(f"Подібність для користувача {user_id} успішно оновлена на основі перших {max_ratings} оцінок.")

def calculate_recommendations_for_user_with_test_set(user_id: int, db: Session, test_books: list):
    """
    Розраховує рекомендації для користувача з обмеженим тестовим набором книг.

    :param user_id: ID користувача.
    :param db: Сесія бази даних.
    :param test_books: Список ID книг для тестування.
    """
    user_similarity_entry = db.query(UserSimilarity).filter(UserSimilarity.user_id == user_id).first()
    if not user_similarity_entry:
        return {"error": "Подібність для користувача не знайдена."}

    similar_users = user_similarity_entry.similarities
    similar_users_ids = list(map(int, similar_users.keys()))
    similar_users_ratings = db.query(Rating).filter(
        Rating.user_id.in_(similar_users_ids),
        Rating.book_id.in_(test_books)
    ).all()

    # Організація оцінок
    book_ratings = {}
    for rating in similar_users_ratings:
        if rating.book_id not in book_ratings:
            book_ratings[rating.book_id] = []
        book_ratings[rating.book_id].append(rating.rating * similar_users[str(rating.user_id)])

    # Розрахунок рекомендацій
    recommendations = {
        book_id: np.mean(ratings) for book_id, ratings in book_ratings.items()
    }

    # Нормалізація
    if recommendations:
        book_ids = list(recommendations.keys())
        scores = np.array(list(recommendations.values())).reshape(-1, 1)
        scaler = MinMaxScaler()
        normalized_scores = scaler.fit_transform(scores).flatten()
        recommendations = {book_id: score for book_id, score in zip(book_ids, normalized_scores)}

    # Сортування
    sorted_recommendations = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)

    # Форматування результатів у JSON
    recommendations_json = {str(book_id): score for book_id, score in sorted_recommendations}

    db.query(UserRecommendationCollaborative).filter(UserRecommendationCollaborative.user_id == user_id).delete()
    recommendation_entry = UserRecommendationCollaborative(
        user_id=user_id,
        recommendations=recommendations_json
    )
    db.add(recommendation_entry)
    db.commit()

    print("Тестові коеціцієнти для книг розраховано")
    return sorted_recommendations

def calculate_content_recommendations_for_test_set(user_id: int, db: Session, test_books: list, max_ratings=60):
    """
    Розраховує контентні рекомендації для заданого користувача лише для тестових книг.

    :param user_id: ID користувача.
    :param db: Сесія бази даних.
    :param test_books: Список ID книг для тестування.
    """
    # Отримання оцінених книг користувачем
    user_ratings = db.query(Rating).filter(Rating.user_id == user_id).order_by(Rating.book_id).limit(max_ratings).all()

    if not user_ratings:
        print(f"Користувач {user_id} не має оцінених книг.")
        return None

    # Формуємо словник оцінок користувача
    rated_books = {rating.book_id: rating.rating for rating in user_ratings}

    # Ініціалізація словника для зберігання коефіцієнтів рекомендацій
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
            similar_book_id = int(similar_book_id)
            # Перевірка, чи книга входить до тестового набору
            if similar_book_id not in test_books:
                continue

            similar_book_id = int(similar_book_id)  # Перетворення на int
            if similar_book_id not in recommendations:
                recommendations[similar_book_id] = 0
            # Додаємо вклад до рекомендації, помноживши оцінку користувача на схожість
            recommendations[similar_book_id] += user_rating * similarity_score
    print(f"{recommendations}")
    # Нормалізація результатів
    if recommendations:
        book_ids = list(recommendations.keys())
        scores = np.array(list(recommendations.values())).reshape(-1, 1)

        scaler = MinMaxScaler()
        normalized_scores = scaler.fit_transform(scores).flatten()

        # Створення нормалізованого словника
        recommendations = {book_id: score for book_id, score in zip(book_ids, normalized_scores)}

        if not recommendations:
            print(f"{recommendations} він порожній")
            return None

        # Додаємо шум до значень, рівних 1.0
        for book_id in recommendations:
            if recommendations[book_id] == 1.0:
                noise = np.random.uniform(-0.02, -0.005)  # Шум у діапазоні [-0.02, -0.005]
                recommendations[book_id] = max(0, recommendations[book_id] + noise)  # Обмежуємо значення в [0, 1]
        print(f"{recommendations}")

    # Сортування за зменшенням рейтингу
    sorted_recommendations = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)

    # Форматування результатів у JSON
    recommendations_json = {str(book_id): score for book_id, score in sorted_recommendations}

    # Збереження рекомендацій для користувача в базу
    db.query(UserRecommendation).filter(UserRecommendation.user_id == user_id).delete()
    recommendation_entry = UserRecommendation(
        user_id=user_id,
        recommendations=recommendations_json
    )
    db.add(recommendation_entry)
    db.commit()

    print(f"Контентні рекомендації для тестового набору книг користувача {user_id} успішно розраховані та збережені.")
    return recommendations_json

# test_books_set = [1655, 1733, 1748, 1817, 2074, 2546, 2568, 2745, 3011, 3108, 3119, 3162, 3223, 3680, 4009, 4095, 4390, 4797, 5007]
# userId = 1677
# db = SessionLocal()
# calculate_similarity_for_user_with_limited_ratings(user_id = userId, db = db, top_n=50, max_ratings=60)
# calculate_recommendations_for_user_with_test_set(userId, db, test_books_set)
# calculate_content_recommendations_for_test_set(userId, db, test_books_set, 60)
# db.close()


