import pandas as pd
from sqlalchemy.orm import Session
from db_service.database import SessionLocal
from db_service.models import Book  # Модель таблиці Book має бути визначена в models.py

# Завантаження даних з books.csv
books_df = pd.read_csv('books_with_genres.csv')

# Імпорт вибраних полів у базу даних
def import_selected_book_fields():
    db = SessionLocal()
    for _, row in books_df.iterrows():
        book = Book(
            book_id=row['book_id'],
            title=row['title'],
            authors=row['authors'],
            average_rating=row['average_rating'],
            genres = row['genres'],
            image_url=row['image_url'],
            small_image_url=row['small_image_url']
        )
        db.add(book)
        print('книгу додано')
    db.commit()
    db.close()

# Виклик функції для імпорту
import_selected_book_fields()