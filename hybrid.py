from sqlalchemy.orm import Session
import numpy as np
import json
from db_service.models import UserRecommendation,UserRecommendationCollaborative, UserHybridRecommendations  # Враховуючи, що у вас є модель UserRating
from db_service.database import SessionLocal
from reccommender_service.content_based import calculate_recommendations_for_user as calc_content
from reccommender_service.collaborative import calculate_recommendations_for_user as calc_coll
from sklearn.preprocessing import MinMaxScaler

def hybrid_recommendations_dynamic(user_id, db: Session, collaborative_weight, content_weight):
    """
    Генерація гібридних рекомендацій для користувача з динамічним вибором книг.

    Параметри:
    - user_id: ID користувача.
    - db: Сесія бази даних.
    - collaborative_weight: Вага колаборативної фільтрації.
    - content_weight: Вага контентної фільтрації.

    Повертає:
    - Словник із рекомендаціями у форматі {user_id: recommendations}.
    """

    # Отримання рекомендацій із контентної фільтрації
    content_entry = db.query(UserRecommendation).filter(
        UserRecommendation.user_id == user_id
    ).first()
    if not content_entry:
        calc_content(user_id, db)
        print(f'Для користувавча {user_id} ще немає контентних рекомендацій, прораховано додатково')
        content_entry = db.query(UserRecommendation).filter(
            UserRecommendation.user_id == user_id
        ).first()

    # Якщо вже dict, то використовуємо його без змін
    content_recommendations = (
        content_entry.recommendations
        if isinstance(content_entry.recommendations, dict)
        else json.loads(content_entry.recommendations)
    )

    # Отримання рекомендацій із колаборативної фільтрації
    collaborative_entry = db.query(UserRecommendationCollaborative).filter(
        UserRecommendationCollaborative.user_id == user_id
    ).first()
    if not collaborative_entry:
        calc_coll(user_id, db)
        print(f'Для користувавча {user_id} ще немає колаборативних рекомендацій, прораховано додатково')
        collaborative_entry = db.query(UserRecommendationCollaborative).filter(
            UserRecommendationCollaborative.user_id == user_id
        ).first()

    # Якщо вже dict, то використовуємо його без змін
    collaborative_recommendations = (
        collaborative_entry.recommendations
        if isinstance(collaborative_entry.recommendations, dict)
        else json.loads(collaborative_entry.recommendations)
    )

    # Вибір методу комбінування залежно від ваги контентної фільтрації
    hybrid_results = {}
    if content_weight > 0.6:
        # Використовуємо всі книги з обох систем
        all_books = set(content_recommendations.keys()).union(collaborative_recommendations.keys())
        for book_id in all_books:
            content_score = content_recommendations.get(book_id, 0)
            collaborative_score = collaborative_recommendations.get(book_id, 0)
            hybrid_score = (content_weight * content_score) + (collaborative_weight * collaborative_score)
            hybrid_results[book_id] = hybrid_score
    else:
        # Використовуємо тільки спільні книги
        common_books = set(content_recommendations.keys()).intersection(collaborative_recommendations.keys())
        for book_id in common_books:
            content_score = content_recommendations.get(book_id, 0)
            collaborative_score = collaborative_recommendations.get(book_id, 0)
            hybrid_score = (content_weight * content_score) + (collaborative_weight * collaborative_score)
            hybrid_results[book_id] = hybrid_score

    # Сортування результатів
    sorted_hybrid_results = sorted(hybrid_results.items(), key=lambda x: x[1], reverse=True)

    # Збереження тільки топ-20 книг
    top_20_recommendations = sorted_hybrid_results[:20]

    # Видалення старих записів для цього користувача
    db.query(UserHybridRecommendations).filter(UserHybridRecommendations.user_id == user_id).delete()

    # Додавання нових рекомендацій у базу
    hybrid_entry = UserHybridRecommendations(
        user_id=user_id,
        recommendations={book_id: score for book_id, score in top_20_recommendations}
    )
    db.add(hybrid_entry)
    db.commit()

    # Повернення результату
    return {"user_id": user_id, "recommendations": top_20_recommendations}

# db = SessionLocal()
# user_id = 1677  # ID користувача
# content_weight = 0.7
# collaborative_weight = 0.3
#
# content_weight_ = 0.4
# collaborative_weight_ = 0.6
#
# hybrid_results_dynamic = hybrid_recommendations_dynamic(user_id, db, collaborative_weight_, content_weight_)
# hybrid_results_static = hybrid_recommendations_dynamic(user_id, db, collaborative_weight, content_weight)
# db.close()
#
# # Виведення результатів
# print(f'Результат динамічної: {hybrid_results_dynamic}')
# print(f'Результат статичної: {hybrid_results_static}')
#
# actual_ratings = [4, 3, 3, 5, 5, 4, 4, 5, 4, 4, 3, 3, 4, 4, 3, 4, 4, 3, 3]  # Останні 6 рейтингів з таблиці ratings
#
# # Масштабування прогнозованих оцінок до діапазону [1, 5]
# def scale_predictions(predictions, target_min=1, target_max=5):
#     predicted_min = min(predictions)
#     predicted_max = max(predictions)
#     return [
#         target_min + (p - predicted_min) * (target_max - target_min) / (predicted_max - predicted_min)
#         for p in predictions
#     ]
#
# # Отримання передбачених значень з hybrid_results_dynamic та hybrid_results_static
# predicted_dynamic = [score for _, score in hybrid_results_dynamic['recommendations']]
# predicted_static = [score for _, score in hybrid_results_static['recommendations']]
#
# # Перевірка
# print("Передбачені оцінки з динамічного підходу:", predicted_dynamic)
# print("Передбачені оцінки зі статичного підходу:", predicted_static)
#
# # Масштабовані передбачення
# scaled_dynamic = scale_predictions(predicted_dynamic)
# print(scaled_dynamic)
# scaled_static = scale_predictions(predicted_static)
#
# def calculate_rmse(actual, predicted):
#     return np.sqrt(np.mean((np.array(actual) - np.array(predicted)) ** 2))
#
# def calculate_mse(actual, predicted):
#     return np.mean((np.array(actual) - np.array(predicted)) ** 2)
#
# # Розрахунок RMSE та MSE для масштабованих оцінок
# rmse_dynamic = calculate_rmse(actual_ratings, scaled_dynamic)
# mse_dynamic = calculate_mse(actual_ratings, scaled_dynamic)
#
# rmse_static = calculate_rmse(actual_ratings, scaled_static)
# mse_static = calculate_mse(actual_ratings, scaled_static)
#
# # Виведення результатів
# print("Динамічний підхід (після масштабування):")
# print(f"RMSE: {rmse_dynamic}")
# print(f"MSE: {mse_dynamic}")
#
# print("\nСтатичний підхід (після масштабування):")
# print(f"RMSE: {rmse_static}")
# print(f"MSE: {mse_static}")
