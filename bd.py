import sqlite3


def create_connection():
    """Создает соединение с базой данных SQLite."""
    conn = sqlite3.connect('tour_bot.db')
    return conn


def create_tables():
    """Создает таблицы Questions и Tours.

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
           - description: TEXT - описание поездки (дополнительная информация)"""

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
        description TEXT
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


def insert_tour(departure_city, arrival_city, price, departure_time, trip_date, description):
    """Добавляет запись для таблицы Tours"""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Tours (departure_city, "
        "arrival_city, price, departure_time, trip_date, description) VALUES (?, ?, ?, ?, ?, ?)",
        (departure_city, arrival_city, price, departure_time, trip_date, description))
    conn.commit()
    conn.close()


def get_questions():
    """Извлекает все вопросы и ответы."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT question, answer FROM Questions")
    questions = cursor.fetchall()
    conn.close()
    return questions



if __name__ == '__main__':
    create_tables()
