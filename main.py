import logging
import os
import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor
from bd import insert_user, get_users, get_user_by_telegram_id, update_user, \
    insert_question, get_questions, delete_question_from_db, \
    update_question_in_db, update_answer_in_db, get_current_question  # Убедитесь, что эти функции корректны.
from states import Form, Questions, Tours

API_TOKEN = '7430055967:AAE_ptETbGQV1CT2RoeqTTFDV1N6flWzquY'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

DEFAULT_PHOTO = 'https://cs1e5a.4pda.ws/15550621.png'  # URL фото по умолчанию
PHOTO_STORAGE_DIR = 'photos'  # Директория для хранения изображений
ADMIN_ID = 868918195

# Проверяем, существует ли директория для хранения фотографий, если нет - создаем
if not os.path.exists(PHOTO_STORAGE_DIR):
    os.makedirs(PHOTO_STORAGE_DIR)


@dp.message_handler(commands=['start'], state='*')
async def start_command(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id

    # Проверяем, есть ли пользователь в базе данных
    users = get_users()  # Получаем всех пользователей

    if not any(user[1] == user_id for user in users):  # Проверяем по telegram_id
        # Добавляем нового пользователя. Номер телефона "не записан".
        insert_user(message.from_user.full_name, "не записан", "", None, telegram_id=user_id)
        await message.answer("Ваши данные записаны в систему.")

    # Показываем профиль пользователя
    await show_user_profile(message, telegram_id=user_id)


async def show_user_profile(message: types.Message, edit_mode=False, telegram_id=None):
    user_info = get_user_by_telegram_id(telegram_id)
    # Формируем текст для подписей
    profile_text = (
        f"Имя: {user_info[2]}\n"
        f"Номер телефона: {user_info[3]}"
    )

    # Создаем инлайн-кнопки
    inline_markup = types.InlineKeyboardMarkup()

    if not edit_mode:  # Если не в режиме редактирования
        inline_markup.row(
            types.InlineKeyboardButton("✈️ Мои поездки", callback_data="my_trips"),
            types.InlineKeyboardButton("✍️ Редактировать профиль", callback_data="edit_profile")
        )
        if telegram_id == ADMIN_ID:
            inline_markup.add(types.InlineKeyboardButton("👑 Админка", callback_data="admin"))
    else:  # В режиме редактирования
        inline_markup.row(
            types.InlineKeyboardButton("✏️ Имя", callback_data="edit_name"),
            types.InlineKeyboardButton("📞 Номер телефона", callback_data="edit_phone"),
            types.InlineKeyboardButton("🖼️ Фото профиля", callback_data="edit_photo")
        )
        inline_markup.add(types.InlineKeyboardButton("🗑️ Удалить фото профиля", callback_data="delete_photo")) \
            if user_info[5] is not None and user_info[5] != "Nophoto" else print()
        inline_markup.add(types.InlineKeyboardButton("↩️ Назад", callback_data="back_to_profile"))

    # Отправляем сообщение с фото и подписью
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=open(user_info[5], 'rb') if user_info[5] and user_info[5] != "Nophoto" else DEFAULT_PHOTO,  # Открываем файл в бинарном режиме
        caption=profile_text,
        reply_markup=inline_markup
    )


async def check_admin_id_message(message: types.Message):
    return message.from_user.id == ADMIN_ID


async def check_admin_id_callback_query(callback_query: types.CallbackQuery):
    return callback_query.from_user.id == ADMIN_ID


@dp.callback_query_handler(lambda c: c.data == "back_to_profile")
async def back_to_profile(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    await callback_query.message.delete()
    # Вернемся к показыванию профиля без режима редактирования
    await show_user_profile(callback_query.message, edit_mode=False, telegram_id=user_id)


@dp.callback_query_handler(lambda c: c.data == "edit_profile")
async def process_edit_profile(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    # Удаляем предыдущее сообщение
    await callback_query.message.delete()

    # Показываем новый профиль в режиме редактирования
    await show_user_profile(callback_query.message, edit_mode=True, telegram_id=callback_query.from_user.id)


@dp.callback_query_handler(lambda c: c.data == "my_trips")
async def process_my_trips(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer("Здесь будут ваши поездки.")  # Вы можете добавить логику для показа поездок.


# Обработчики для редактирования
@dp.callback_query_handler(lambda c: c.data == "edit_name")
async def edit_name(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await Form.waiting_for_new_name.set()  # Устанавливаем новое состояние
    await callback_query.message.delete()
    await callback_query.message.answer("Введите ваше новое имя:")


@dp.message_handler(state=Form.waiting_for_new_name)
async def process_new_name(message: types.Message, state: FSMContext):
    new_name = message.text
    user_id = message.from_user.id

    # Сохраним новое имя в БД
    update_user(user_id, name=new_name)

    await state.finish()  # Завершить текущее состояние
    await show_user_profile(message, telegram_id=message.from_user.id, edit_mode=True)  # Показываем профиль с обновленным именем


@dp.callback_query_handler(lambda c: c.data == "edit_phone")
async def edit_phone(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await Form.waiting_for_new_phone.set()  # Устанавливаем новое состояние
    await callback_query.message.delete()
    await callback_query.message.answer("Введите новый номер телефона:")


@dp.message_handler(state=Form.waiting_for_new_phone)
async def process_new_phone(message: types.Message, state: FSMContext):
    new_phone = message.text
    user_id = message.from_user.id

    # Сохраним новый номер телефона в БД
    update_user(user_id, phone_number=new_phone)

    await state.finish()  # Завершить текущее состояние
    await show_user_profile(message, telegram_id=message.from_user.id, edit_mode=True)  # Показываем профиль с обновленным номером


@dp.callback_query_handler(lambda c: c.data == "edit_photo")
async def edit_photo(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await Form.waiting_for_new_photo.set()  # Устанавливаем новое состояние
    await callback_query.message.delete()
    await callback_query.message.answer("Отправьте новое фото:")


@dp.message_handler(state=Form.waiting_for_new_photo, content_types=types.ContentTypes.PHOTO)
async def process_new_photo(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id  # Получаем файл
    photo_file = await bot.get_file(photo_id)  # Получаем объект файла
    new_photo_path = os.path.join(PHOTO_STORAGE_DIR, f'{user_id}_photo.png')  # Имя файла для сохранения

    # Скачиваем фото
    await bot.download_file(photo_file.file_path, new_photo_path)

    # Сохраним путь к новому фото в БД
    update_user(user_id, photo=new_photo_path)

    await state.finish()  # Завершить текущее состояние
    await show_user_profile(message, telegram_id=message.from_user.id, edit_mode=True)  # Показываем профиль с обновленным фото


@dp.callback_query_handler(lambda c: c.data == "delete_photo")
async def delete_photo(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id

    # Получаем информацию о пользователе из базы данных
    user_info = get_user_by_telegram_id(user_id)

    if user_info and user_info[5]:  # Если есть фотография
        photo_path = user_info[5]  # Получаем путь к фотографии

        # Удаляем фото из базы данных
        update_user(user_id, photo="Nophoto")  # Обновляем запись в БД
        if os.path.exists(photo_path):
            os.remove(photo_path)  # Удаляем файл фото
        await callback_query.message.delete()
        await callback_query.message.answer("Фотография удалена.")

        await show_user_profile(callback_query.message, telegram_id=callback_query.from_user.id, edit_mode=True)  # Показываем профиль без фото
    else:
        await callback_query.message.answer("Фотография не найдена.")


# ADMIN - ОБЩИЙ ИНТЕРФЕЙС
@dp.callback_query_handler(lambda c: c.data == "admin")
async def process_admin(callback_query: types.CallbackQuery):
    if check_admin_id_callback_query(callback_query):
        await bot.answer_callback_query(callback_query.id)  # Уведомляем о нажатии кнопки

        # Создаем новое меню для администраторов
        admin_markup = types.InlineKeyboardMarkup()
        admin_markup.add(types.InlineKeyboardButton("📊 Статистика", callback_data="admin_statistics"))
        admin_markup.add(types.InlineKeyboardButton("❓ Вопросы-Ответы", callback_data="admin_faq"))
        admin_markup.add(types.InlineKeyboardButton("✈️ Поездки", callback_data="admin_trips"))
        admin_markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile"))

        await bot.send_message(callback_query.from_user.id, "Добро пожаловать в админку! Выберите действие:", reply_markup=admin_markup)


# ADMIN - ЛОГИКА ДОБАВЛЕНИЯ ВОПРОСЫ-ОТВЕТЫ
async def admin_faq_2(callback_query_or_message):
    # Проверяем, является ли контекст сообщением или обратным вызовом
    if isinstance(callback_query_or_message, types.CallbackQuery):
        await bot.answer_callback_query(callback_query_or_message.id)
        user_id = callback_query_or_message.from_user.id
    else:  # В случае, если это обычное сообщение, используем его идентификатор
        user_id = callback_query_or_message.from_user.id

    questions = get_questions()

    # Создаем инлайн-кнопки для каждого вопроса
    faq_markup = types.InlineKeyboardMarkup()

    for record in questions:
        question_id, question, answer = record
        faq_markup.add(
            types.InlineKeyboardButton(f"✏️ {question[:10]} - {answer}", callback_data=f"edit_questions_{question_id}"),
            types.InlineKeyboardButton("❌ Удалить", callback_data=f"delete_question_{question_id}")
        )

    faq_markup.add(types.InlineKeyboardButton("➕ Добавить новый вопрос", callback_data="add_question"))
    faq_markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))

    await bot.send_message(user_id, "Вопросы и ответы:", reply_markup=faq_markup)


@dp.callback_query_handler(lambda c: c.data == "admin_faq")
async def admin_faq(callback_query_or_message):
    # Проверяем, является ли контекст сообщением или обратным вызовом
    if isinstance(callback_query_or_message, types.CallbackQuery):
        await bot.answer_callback_query(callback_query_or_message.id)
        user_id = callback_query_or_message.from_user.id
    else:  # В случае, если это обычное сообщение, используем его идентификатор
        user_id = callback_query_or_message.from_user.id

    questions = get_questions()

    # Создаем инлайн-кнопки для каждого вопроса
    faq_markup = types.InlineKeyboardMarkup()
    for record in questions:
        question_id, question, answer = record
        faq_markup.add(
            types.InlineKeyboardButton(f"✏️ {question[:10]} - {answer}", callback_data=f"edit_questions_{question_id}"),
            types.InlineKeyboardButton("❌ Удалить", callback_data=f"delete_question_{question_id}")
        )

    faq_markup.add(types.InlineKeyboardButton("➕ Добавить новый вопрос", callback_data="add_question"))
    faq_markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))

    await bot.send_message(user_id, "Вопросы и ответы:", reply_markup=faq_markup)


@dp.callback_query_handler(lambda c: c.data == "back_to_admin", state="*")
async def back_to_admin(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await bot.answer_callback_query(callback_query.id)
    # Здесь вы можете вернуть пользователя в основное админ меню
    await process_admin(callback_query)


@dp.callback_query_handler(lambda c: c.data == "add_question")
async def add_question(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Введите вопрос:")
    await dp.current_state(user=callback_query.from_user.id).set_data({"action": "add"})


@dp.message_handler(state="*")
async def handle_new_question(message: types.Message, state: FSMContext):
    user_data = await state.get_data()

    print(user_data)

    if "action" in user_data and user_data["action"] == "add":
        question_text = message.text
        await bot.send_message(message.from_user.id, "Введите ответ:")
        await state.update_data({"question": question_text, "action": "add_answer"})
    elif "action" in user_data and user_data["action"] == "add_answer":
        answer_text = message.text
        insert_question(user_data["question"], answer_text)
        await bot.send_message(message.from_user.id, "Вопрос добавлен!")
        await admin_faq_2(message)
        await state.finish()  # Сброс состояния

    elif "action" in user_data and user_data["action"] == "edit_question_text_":
        question_id = user_data["question_id"]
        new_question_text = message.text
        update_question_in_db(question_id, new_question_text)  # Ваша функция обновления
        await bot.send_message(message.from_user.id, "Вопрос обновлен!")

        await admin_faq(message)  # Вернем к вопросам и ответам
        await state.finish()

    elif "action" in user_data and user_data["action"] == "edit_answer_text_":
        question_id = user_data["question_id"]
        new_answer_text = message.text
        update_answer_in_db(question_id, new_answer_text)  # Ваша функция обновления
        await bot.send_message(message.from_user.id, "Ответ обновлен!")

        await admin_faq(message)  # Вернем к вопросам и ответам
        await state.finish()


@dp.callback_query_handler(lambda c: c.data.startswith("edit_questions_"))
async def edit_question(callback_query: types.CallbackQuery):
    question_id = int(callback_query.data.split("_")[-1])

    # Получаем текущий вопрос и ответ из базы данных
    connection = sqlite3.connect('tour_bot.db')
    cursor = connection.cursor()
    cursor.execute("SELECT question, answer FROM Questions WHERE id = ?", (question_id,))
    record = cursor.fetchone()
    connection.close()

    if record:
        current_question, current_answer = record

        # Отправляем сообщение с выбором
        edit_markup = types.InlineKeyboardMarkup()
        edit_markup.add(
            types.InlineKeyboardButton("📝 Редактировать вопрос", callback_data=f"edit_question_text_{question_id}"),
            types.InlineKeyboardButton("💬 Редактировать ответ", callback_data=f"edit_answer_text_{question_id}"),

        )
        edit_markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_questions"))  # Кнопка назад

        await bot.send_message(callback_query.from_user.id, "Что редактируем? 😊", reply_markup=edit_markup)
    else:
        await bot.send_message(callback_query.from_user.id, "Вопрос не найден.")


@dp.callback_query_handler(lambda c: c.data.startswith("edit_question_text_"))
async def edit_question_text(callback_query: types.CallbackQuery):
    question_id = int(callback_query.data.split("_")[-1])

    # Получаем текущий вопрос из базы данных
    question = get_current_question(question_id)

    if question:
        current_question = question[0]
        await bot.send_message(callback_query.from_user.id, f"Введите новый текст для вопроса:\n{current_question}")
        await dp.current_state(user=callback_query.from_user.id).set_data(
            {"action": "edit_question_text_", "question_id": question_id})
        print("Состояние установлено на Questions.question")  # Отладка
    else:
        await bot.send_message(callback_query.from_user.id, "Вопрос не найден.")


@dp.callback_query_handler(lambda c: c.data.startswith("edit_answer_text_"))
async def edit_answersss_text(callback_query: types.CallbackQuery):
    question_id = int(callback_query.data.split("_")[-1])

    # Получаем текущий ответ из базы данных
    connection = sqlite3.connect('tour_bot.db')
    cursor = connection.cursor()
    cursor.execute("SELECT answer FROM Questions WHERE id = ?", (question_id,))
    record = cursor.fetchone()
    connection.close()

    if record:
        current_answer = record[0]
        await bot.send_message(callback_query.from_user.id, f"Введите новый текст для ответа:\n{current_answer}")
        await dp.current_state(user=callback_query.from_user.id).set_data(
            {"action": "edit_answer_text_", "question_id": question_id})
    else:
        await bot.send_message(callback_query.from_user.id, "Ответ не найден.")


# Обработчик для кнопки "Назад"
@dp.callback_query_handler(lambda c: c.data == "back_to_questions")
async def back_to_questions(callback_query: types.CallbackQuery):
    await admin_faq(callback_query)  # Предполагаем, что admin_faq — это функция, которая показывает все вопросы


@dp.callback_query_handler(lambda c: c.data.startswith("delete_question_"))
async def delete_question(callback_query: types.CallbackQuery):
    question_id = int(callback_query.data.split("_")[-1])
    delete_question_from_db(question_id)
    await admin_faq_2(callback_query)


# ADMIN - ЛОГИКА ДОБАВЛЕНИЯ ПОЕЗДОК
@dp.callback_query_handler(lambda c: c.data == "admin_trips")
async def view_tours(callback_query: types.CallbackQuery):
    # Получаем данные о поездках из базы данных
    connection = sqlite3.connect('tour_bot.db')
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, departure_city, arrival_city, price, departure_time, trip_date, description, photo, published FROM Tours")
    records = cursor.fetchall()
    connection.close()

    if records:
        for record in records:
            tour_id, departure_city, arrival_city, price, departure_time, trip_date, description, photo, published = record

            # Формируем карточку поездки
            published_text = "✅ Опубликовано" if published else "❌ Не опубликовано"
            card = f"""
            🚌 Поездка #
            **Город отправления:** {departure_city}
            **Город назначения:** {arrival_city}
            **Цена:** {price}$
            **Время отправления:** {departure_time}
            **Дата поездки:** {trip_date}
            **Описание:** {description}
            {published_text}
            [![Фото]({photo})]({photo})
            """
            await bot.send_message(callback_query.from_user.id, card, parse_mode='Markdown')

    else:
        await bot.send_message(callback_query.from_user.id, "Нет доступных поездок.")

    # Кнопки для добавления поездки и возврат
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"),
        types.InlineKeyboardButton("➕ Добавить поездку", callback_data="add_tour")
    )

    await bot.send_message(callback_query.from_user.id, "Выберите действие:", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == "add_tour")
async def add_tour(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id,
                           "Пожалуйста, введите информацию о новой поездке в следующем формате:\n"
                           "Город отправления, Город назначения, Цена, Время отправления, "
                           "Дата поездки, Описание, Ссылка на фото, Опубликовано (да/нет)")

    await Tours.waiting_for_tour_info.set()  # Устанавливаем состояние для получения данных о поездке


@dp.message_handler(state=Tours.waiting_for_tour_info)
async def process_add_tour(message: types.Message, state: FSMContext):
    data = message.text.split(", ")

    if len(data) != 8:
        await message.reply("Неверный формат! Пожалуйста, убедитесь, что все поля указаны корректно.")
        return

    departure_city, arrival_city, price, departure_time, trip_date, description, photo, published = data
    published = 1 if published.lower() == "да" else 0  # Преобразуем строку в boolean

    # Сохраняем данные в базу данных
    connection = sqlite3.connect('tour_bot.db')
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO Tours (departure_city, arrival_city, price, departure_time, trip_date, description, photo, published) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (departure_city, arrival_city, float(price), departure_time, trip_date, description, photo, published))
    connection.commit()
    connection.close()

    await message.reply("Поездка успешно добавлена!")

    # Вернёмся к списку поездок
    await view_tours(message)
    await state.finish()  # Сброс состояния


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
