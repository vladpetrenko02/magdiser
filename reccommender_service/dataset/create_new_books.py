import pandas as pd

# Завантаження файлів
books_csv_path = 'C:/Users/Asus/PycharmProjects\HybridReccomenderServer/reccommender_service/dataset/books.csv'  # Ваш оригінальний файл
new_data_csv_path = 'C:/Users/Asus/PycharmProjects\HybridReccomenderServer/reccommender_service/dataset/path_genres.csv'  # Файл із жанрами
output_csv_path = 'C:/Users/Asus/PycharmProjects\HybridReccomenderServer/reccommender_service/dataset/books_with_genres.csv'  # Файл для збереження результату

# Завантаження даних
books_df = pd.read_csv(books_csv_path)
new_data_df = pd.read_csv(new_data_csv_path)

# Попередня обробка
# Додати нуль до ISBN у books.csv
books_df['isbn'] = books_df['isbn'].apply(lambda x: f"0{x}" if pd.notna(x) and not x.startswith('0') else x)

# Перетворення isbn13 у нормальний формат
def normalize_isbn13(isbn13):
    try:
        return str(int(float(isbn13)))
    except (ValueError, TypeError):
        return None

books_df['isbn13'] = books_df['isbn13'].apply(normalize_isbn13)

# Створення словників для швидкого пошуку
isbn_to_genres = dict(zip(new_data_df['isbn'], new_data_df['genres']))
isbn13_to_genres = dict(zip(new_data_df['isbn13'].astype(str), new_data_df['genres']))

# Додавання жанрів
def get_genres(row):
    genres = isbn_to_genres.get(row['isbn'])
    if not genres:
        genres = isbn13_to_genres.get(row['isbn13'])
    return genres

books_df['genres'] = books_df.apply(get_genres, axis=1)

total_books = len(books_df)
books_with_genres = books_df['genres'].notna().sum()
print(f"Загальна кількість книг: {total_books}")
print(f"Кількість книг з жанрами: {books_with_genres}")
print(f"Кількість книг без жанрів: {total_books - books_with_genres}")

# Видалення книг без жанрів
books_with_genres_df = books_df.dropna(subset=['genres'])

# Збереження результату
books_with_genres_df.to_csv(output_csv_path, index=False)

print(f"Файл із жанрами збережено: {output_csv_path}")
# import pandas as pd
# import requests
# import json
#
# # Функція для конвертації ISBN13 із наукового формату в нормальний
# def convert_isbn13(isbn13):
#     try:
#         return str(int(float(isbn13)))
#     except ValueError:
#         return None
#
# # Функція для отримання жанрів із Google Books API
# def fetch_genres(isbn):
#     api_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key=AIzaSyA5RkCb-2BXQ1hlHkkBJfTVupURwkfMUJM"
#     response = requests.get(api_url)
#     if response.status_code == 200:
#         data = response.json()
#         if data.get("totalItems", 0) > 0:
#             categories = data["items"][0]["volumeInfo"].get("categories", [])
#             return categories
#     return None
#
#
#
# # Основна функція
# def add_genres_to_books(input_file, output_file):
#     # Завантаження CSV
#     books_df = pd.read_csv(input_file)
#
#     # Додавання стовпця для жанрів
#     books_df["genres"] = None
#     count = 0
#     updated_rows = []
#
#     # Обробка кожного рядка
#     for _, row in books_df.iterrows():
#         isbn = str(row["isbn"]) if pd.notnull(row["isbn"]) else None
#         isbn13 = convert_isbn13(row["isbn13"]) if pd.notnull(row["isbn13"]) else None
#
#         genres = None
#
#         # Спроба отримати жанри за ISBN
#         if isbn:
#             genres = fetch_genres(isbn)
#
#         # Спроба отримати жанри за ISBN13, якщо за ISBN не знайдено
#         if not genres and isbn13:
#             genres = fetch_genres(isbn13)
#
#         if genres:
#             row["genres"] = ", ".join(genres)
#             updated_rows.append(row)
#         else:
#             print(f"No genres found for book ID {row['book_id']}, removing...")
#             count = count + 1
#             print(count)
#
#     # Збереження оновленого CSV
#     updated_df = pd.DataFrame(updated_rows)
#     updated_df.to_csv(output_file, index=False)
#     print(f"Updated CSV saved to {output_file}")
#
# # Виклик функції
# add_genres_to_books("C:/Users/Asus/PycharmProjects/HybridReccomenderServer/reccommender_service/dataset/books.csv", "C:/Users/Asus/PycharmProjects/HybridReccomenderServer/reccommender_service/dataset/books_with_genres.csv")