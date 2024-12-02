import pandas as pd
from sqlalchemy.orm import Session
from db_service.database import SessionLocal
from db_service.models import Rating, Book
from datetime import datetime, timedelta


# Обчислення дати "вчора" з конкретним часом


def import_ratings(file_path: str):
    """
    Імпортує рейтинги з CSV, перевіряючи наявність книги в таблиці books.

    :param file_path: Шлях до файлу CSV.
    """
    # Завантажуємо тільки перші 300 000 рядків
    ratings_df = pd.read_csv(file_path, nrows=300000)

    # Ініціалізація сесії бази даних
    db = SessionLocal()

    # Отримуємо всі існуючі book_id з таблиці books
    existing_book_ids = {book.book_id for book in db.query(Book.book_id).all()}

    for _, row in ratings_df.iterrows():
        book_id = int(row['book_id'])
        # Перевірка, чи існує book_id в таблиці books
        if book_id not in existing_book_ids:
            continue  # Пропускаємо, якщо книги немає в базі

        yesterday = datetime.now() - timedelta(days=1)
        yesterday = yesterday.replace(hour=22, minute=0, second=0, microsecond=0)

        # Додаємо рейтинг
        rating = Rating(
            user_id=int(row['user_id']),
            book_id=book_id,
            rating=int(row['rating']),
            created_at = yesterday
        )
        db.add(rating)
        print("рейт додано")

    # Коміт для збереження даних
    db.commit()
    db.close()

    print("Рейтинги імпортовано успішно, пропущено записи з неіснуючими book_id.")


# Виклик функції
import_ratings('ratings.csv')