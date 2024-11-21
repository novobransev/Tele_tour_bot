import sqlite3

def create_connection():
    """Создает соединение с базой данных SQLite."""
    conn = sqlite3.connect('tour_bot.db')
    return conn


def create_tables():
    """Создает таблицы Questions, Tours и Users.

        1. Таблица Questions:
           - id: INTEGER, PRIMARY KEY, AUTO INCREMENT
           - question: TEXT - текст вопроса
           - answer: TEXT - текст ответа

        2. Таблица Tours:
           - id: INTEGER, PRIMARY KEY, AUTO INCREMENT
           - departure_city: TEXT - город отправления
           - arrival_city: TEXT - город назначения
           - price: REAL - цена поездки
           - departure_time: TEXT - время отправления
           - trip_date: TEXT - дата поездки
           - description: TEXT - описание поездки (дополнительная информация)
           - photo: TEXT - ссылка на фотографию
           - status: TEXT - состояние поездки (текущее, будущее, прошлое)

        3. Таблица Users:
           - id: INTEGER, PRIMARY KEY, AUTO INCREMENT
           - telegram_id: INTEGER - id  телеграмма
           - name: TEXT - имя пользователя
           - phone_number: TEXT - номер телефона
           - trips: TEXT - список поездок (можно использовать JSON или просто перечисление ID поездок)
           - photo: TEXT - ссылка на фотографию пользователя"""

    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Tours (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        departure_city TEXT NOT NULL,
        arrival_city TEXT NOT NULL,
        price REAL NOT NULL,
        departure_time TEXT NOT NULL,
        trip_date TEXT NOT NULL,
        description TEXT,
        photo TEXT,
        status TEXT NOT NULL,  -- состояние поездки
        published BOOLEAN DEFAULT 0  -- добавляем поле
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        name TEXT NULL,
        phone_number TEXT NOT NULL,
        trips TEXT,  -- можно использовать JSON или перечисление ID поездок
        photo TEXT  -- ссылка на фотографию пользователя
    )
    ''')

    conn.commit()
    conn.close()


def insert_question(question, answer):
    """Добавляет запись для таблицы Questions"""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Questions (question, answer) VALUES (?, ?)", (question, answer))
    conn.commit()
    conn.close()


def delete_question_from_db(question_id):
    connection = sqlite3.connect('tour_bot.db')
    cursor = connection.cursor()
    cursor.execute("DELETE FROM Questions WHERE id = ?", (question_id,))
    connection.commit()
    connection.close()


def insert_tour(departure_city, arrival_city, price, departure_time, trip_date, description, photo, status):
    """Добавляет запись для таблицы Tours"""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Tours (departure_city, arrival_city, price, departure_time, trip_date, description, photo, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (departure_city, arrival_city, price, departure_time, trip_date, description, photo, status))
    conn.commit()
    conn.close()


def insert_user(name, phone_number, trips, photo, telegram_id):
    """Добавляет запись для таблицы Users"""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Users (name, phone_number, trips, photo, telegram_id) VALUES (?, ?, ?, ?, ?)", (name, phone_number, trips, photo, telegram_id))
    conn.commit()
    conn.close()


def get_questions():
    """Извлекает все вопросы и ответы."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Questions")
    questions = cursor.fetchall()
    conn.close()
    return questions


def get_tours():
    """Извлекает все поездки."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT departure_city, arrival_city, price, departure_time, trip_date, description, photo, status FROM Tours")
    tours = cursor.fetchall()
    conn.close()
    return tours


def get_users():
    """Извлекает всех пользователей."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users")
    users = cursor.fetchall()
    conn.close()
    return users


def get_user_by_telegram_id(telegram_id):
    """Извлекает пользователя по его ID Telegram."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()  # Получаем одну запись
    conn.close()
    return user  # Возвращаем данные пользователя или None, если не найден


def update_user(telegram_id, name=None, phone_number=None, photo=None):
    """Обновляет информацию о пользователе в базе данных."""
    conn = create_connection()
    cursor = conn.cursor()

    if name:
        cursor.execute("UPDATE Users SET name = ? WHERE telegram_id = ?", (name, telegram_id))

    if phone_number:
        cursor.execute("UPDATE Users SET phone_number = ? WHERE telegram_id = ?", (phone_number, telegram_id))

    if photo:
        cursor.execute("UPDATE Users SET photo = ? WHERE telegram_id = ?", (photo, telegram_id))

    conn.commit()
    conn.close()


def update_question_in_db(question_id, new_question_text):
    connection = sqlite3.connect('tour_bot.db')
    cursor = connection.cursor()
    cursor.execute("UPDATE Questions SET question = ? WHERE id = ?", (new_question_text, question_id))
    connection.commit()
    connection.close()


def update_answer_in_db(question_id, new_answer_text):
    connection = sqlite3.connect('tour_bot.db')
    cursor = connection.cursor()
    cursor.execute("UPDATE Questions SET answer = ? WHERE id = ?", (new_answer_text, question_id))
    connection.commit()
    connection.close()


def get_current_question(question_id):
    connection = sqlite3.connect('tour_bot.db')
    cursor = connection.cursor()
    cursor.execute("SELECT question FROM Questions WHERE id = ?", (question_id,))
    record = cursor.fetchone()
    connection.close()
    return record


if __name__ == '__main__':
    create_tables()
