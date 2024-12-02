import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from db_service.models import Book, BookFeature  # Імпорт моделей
from db_service.database import SessionLocal  # Імпорт сесії для підключення до бази

def create_book_features_from_db(db: Session):
    # Отримання всіх записів із таблиці books
    books = db.query(Book).all()

    # Перетворення записів на DataFrame для зручної обробки
    books_df = pd.DataFrame([{
        'book_id': book.book_id,
        'authors': book.authors,
        'genres': book.genres,
        'average_rating': book.average_rating
    } for book in books])

    # Перетворення авторів на числові значення з нормалізацією
    label_encoder = LabelEncoder()
    authors_encoded = label_encoder.fit_transform(books_df['authors'].fillna('Unknown'))
    authors_encoded = authors_encoded.reshape(-1, 1)  # Перетворення у 2D масив для нормалізації
    scaler = MinMaxScaler()
    authors_normalized = scaler.fit_transform(authors_encoded)

    # Обробка жанрів
    books_df['genres'] = books_df['genres'].fillna('')  # Заповнюємо пусті значення

    # Перетворення жанрів у векторний вигляд
    vectorizer = TfidfVectorizer(tokenizer=lambda x: x.split(';'))  # Розділяємо жанри за комою
    genres_matrix = vectorizer.fit_transform(books_df['genres'])

    # Середнє значення TF-IDF для кожної книги
    genres_average_tfidf = genres_matrix.mean(axis=1).A1  # Середнє значення TF-IDF для кожної книги

    # Нормалізація середнього TF-IDF
    scaler = MinMaxScaler()
    genres_normalized = scaler.fit_transform(genres_average_tfidf.reshape(-1, 1))

    # Використання середнього рейтингу як характеристики
    rating_scaler = MinMaxScaler()
    average_rating = rating_scaler.fit_transform(books_df[['average_rating']])

    # Комбінування характеристик у єдиний вектор
    book_features = np.hstack([authors_normalized, genres_normalized, average_rating])

    # Видаляємо старі записи з таблиці book_features, якщо потрібно оновлення
    db.query(BookFeature).delete()

    # Додаємо нові записи до таблиці book_features
    for book_id, feature_vector in zip(books_df['book_id'], book_features):
        book_feature = BookFeature(
            book_id=book_id,
            feature_1=float(feature_vector[0]),
            feature_2=float(feature_vector[1]),
            feature_3=float(feature_vector[2]),
            # Додайте більше полів, якщо у вас більше характеристик
        )
        db.add(book_feature)
    db.commit()
    return book_features


# Приклад використання функції для запису даних у таблицю
db = SessionLocal()
create_book_features_from_db(db)
db.close()