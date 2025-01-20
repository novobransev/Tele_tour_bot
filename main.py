import logging
import os
import sqlite3
import time
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext, filters
from aiogram.utils import executor
from bd import insert_user, get_users, get_user_by_telegram_id, update_user, \
    insert_question, get_questions, delete_question_from_db, \
    update_question_in_db, update_answer_in_db, get_current_question, \
    insert_message_id, get_all_message_ids, delete_message_id  # Убедитесь, что эти функции корректны.
from states import Form, Questions, Tours, TourStates
from aiogram_timepicker.panel import FullTimePicker, full_timep_callback, full_timep_default
from aiogram_datepicker import Datepicker, DatepickerSettings
full_timep_default(
    # default labels
    label_up='⇪', label_down='⇓',
    hour_format='{0:02}h', minute_format='{0:02}m', second_format='{0:02}s'
)


async def delete_all_message(chat_id, user_id):
    for mes in get_all_message_ids(user_id):
        await bot.delete_message(chat_id, mes)


def clear_bd_message(user_id):
    for mes in get_all_message_ids(user_id):
        delete_message_id(mes)

API_TOKEN = '7430055967:AAE_ptETbGQV1CT2RoeqTTFDV1N6flWzquY'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

DEFAULT_PHOTO = 'https://cs1e5a.4pda.ws/15550621.png'  # URL фото по умолчанию
PHOTO_STORAGE_DIR = 'photos'  # Директория для хранения изображений
ADMIN_ID = 305636069
PHOTO_DIR = 'tour_photo'

# Проверяем, существует ли директория для хранения фотографий, если нет - создаем
if not os.path.exists(PHOTO_STORAGE_DIR):
    os.makedirs(PHOTO_STORAGE_DIR)

# Убедитесь, что папка существует
if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR)


@dp.message_handler(commands=['start'], state='*')
async def start_command(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id

    # Проверяем, есть ли пользователь в базе данных
    users = get_users()  # Получаем всех пользователей

    if not any(user[1] == user_id for user in users):  # Проверяем по telegram_id
        # Добавляем нового пользователя. Номер телефона "не записан".
        insert_user(message.from_user.full_name, "не записан", "", None, telegram_id=user_id)

    # Показываем профиль пользователя
    await show_user_profile(message, telegram_id=user_id)


async def show_user_profile(message: types.Message, edit_mode=False, telegram_id=None):
    await delete_all_message(message.chat.id, message.from_user.id)
    clear_bd_message(message.from_user.id)
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
            types.InlineKeyboardButton("✈️ Поездки", callback_data="my_trips"),
            types.InlineKeyboardButton(text="❓ Частые вопросы", callback_data="faq_questions")
        )
        inline_markup.add(types.InlineKeyboardButton("✍️ Редактировать профиль", callback_data="edit_profile"))
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


@dp.callback_query_handler(lambda c: c.data == "faq_questions")
async def faq_questions(callback_query: types.CallbackQuery):
    # Подключаемся к базе данных
    connection = sqlite3.connect('tour_bot.db')
    cursor = connection.cursor()

    # Извлекаем все вопросы и ответы
    cursor.execute("SELECT question, answer FROM Questions")
    records = cursor.fetchall()
    inline_markup = types.InlineKeyboardMarkup()
    inline_markup.add(types.InlineKeyboardButton("↩️ Назад", callback_data="back_to_profile"))

    # Форматируем текст для отправки
    if records:
        faq_text = ""
        for index, (question, answer) in enumerate(records, start=1):
            faq_text += f"📝 *Вопрос {index}:* {question}\n🗨️ *Ответ:* {answer}\n\n"

        # Отправляем сообщение с вопросами и ответами
        await bot.send_message(
            chat_id=callback_query.from_user.id,
            text=faq_text,
            parse_mode="Markdown",  # Используем Markdown форматирование
            reply_markup=inline_markup
        )
    else:
        await bot.send_message(
            chat_id=callback_query.from_user.id,
            text="🚫 Нет доступных вопросов."
        )

    # Закрываем соединение с базой данных
    connection.close()


async def check_admin_id_message(message: types.Message):
    return message.from_user.id == ADMIN_ID


async def check_admin_id_callback_query(callback_query: types.CallbackQuery):
    return callback_query.from_user.id == ADMIN_ID


@dp.callback_query_handler(lambda c: c.data == "back_to_profile")
async def back_to_profile(callback_query: types.CallbackQuery):
    await delete_all_message(callback_query.message.chat.id, callback_query.from_user.id)
    clear_bd_message(callback_query.from_user.id)
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
    print("Выполняю")
    await bot.answer_callback_query(callback_query.id)
    # Получаем данные о поездках из базы данных
    connection = sqlite3.connect('tour_bot.db')
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, departure_city, arrival_city, price, departure_time, trip_date, description, photo, published FROM Tours WHERE published = 1")
    records = cursor.fetchall()
    connection.close()

    if records:
        for record in records:
            tour_id, departure_city, arrival_city, price, departure_time, trip_date, description, photo, published = record

            # Создаем инлайн-кнопку "Записаться"
            register_button = types.InlineKeyboardButton(text='📝 Записаться', callback_data=f'register_for_trip_{tour_id}')

            # Создаем клавиатуру с кнопками
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(register_button)

            # Формируем карточку поездки
            published_text = "✅ Опубликовано" if published else "❌ Не опубликовано"
            caption = (
                f"\n№ поездки: {tour_id}\n\n"
                f"\n✈️ Город отправления: {departure_city if departure_city else 'Не заполнено'}\n\n"
                f"🌍 Город назначения: {arrival_city if arrival_city else 'Не заполнено'}\n\n"
                f"💰 Цена: {price if price else 'Не заполнено'}\n\n"
                f"🕒 Время отправления: {departure_time if departure_time else 'Не заполнено'}\n\n"
                f"📅 Дата поездки: {trip_date if trip_date else 'Не заполнено'}\n\n"
                f"📝 Описание: {description if description else 'Не заполнено'}\n\n"
            )

            mes = await bot.send_photo(
                chat_id=callback_query.from_user.id,
                photo=open(photo,
                           'rb') if photo else "https://steamuserimages-a.akamaihd.net/ugc/950726000575702194/E9862E658BDABDC2B3AD40338ADB7DA100C56004/?imw=512&imh=320&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=true",
                caption=caption,
                reply_markup=keyboard
            )
            insert_message_id(mes.message_id, callback_query.from_user.id)
        # После всех поездок отправляем сообщение с кнопкой "Назад"
        back_keyboard = types.InlineKeyboardMarkup()
        back_button = types.InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_profile')
        back_keyboard.add(back_button)



        mes = await bot.send_message(
            chat_id=callback_query.from_user.id,
            text="Это все поездки.",
            reply_markup=back_keyboard  # Добавляем инлайн-кнопку "Назад"
        )
        insert_message_id(mes.message_id, callback_query.from_user.id)
    else:
        mes = await bot.send_message(callback_query.from_user.id, "Нет доступных поездок.")
        insert_message_id(mes.message_id, callback_query.from_user.id)


@dp.callback_query_handler(lambda c: c.data.startswith("register_for_trip_"))
async def register_for_trip(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    # Здесь можно получить id тура из callback_data
    tour_id = callback_query.data.split('_')[-1]  # Извлекаем tour_id

    # Подключаемся к базе данных
    conn = sqlite3.connect('tour_bot.db')
    cursor = conn.cursor()

    # Запрос для извлечения departure_city и arrival_city
    cursor.execute('''
        SELECT departure_city, arrival_city FROM Tours WHERE id = ?;
    ''', (tour_id,))

    # Извлекаем результаты
    result = cursor.fetchone()

    departure_city = result[0]  # Город отправления
    arrival_city = result[1]  # Город назначения

    print(departure_city, arrival_city)
    conn.close()

    # Отправляем сообщение с информацией о записи
    message = (
        f"Хотите записаться на тур №{tour_id}\n"
        f"{departure_city} - {arrival_city}?\n\n"
        "Вы можете записаться двумя способами:\n"
        "1️⃣ Позвонить нашему менеджеру по номеру: <номер телефона>\n"
        "2️⃣ Записаться через бота, нажав кнопку ниже."
    )

    # Создаем инлайн-кнопку "Записаться через бота"
    register_via_bot_button = types.InlineKeyboardButton(text='🤖 Записаться через бота', callback_data=f'register_via_bot_{tour_id}')
    register_keyboard = types.InlineKeyboardMarkup()
    register_keyboard.add(register_via_bot_button)

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=message,
        reply_markup=register_keyboard
    )


@dp.callback_query_handler(lambda c: c.data.startswith("register_via_bot_"))
async def register_via_bot(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    user_id = callback_query.from_user.id

    # Проверяем, есть ли зарегистрированный номер телефона
    connection = sqlite3.connect('tour_bot.db')
    cursor = connection.cursor()
    cursor.execute("SELECT phone_number FROM Users WHERE telegram_id = ?", (user_id,))
    result = cursor.fetchone()
    connection.close()
    print(result)
    if result and result[0] and result[0] != 'не записан':
        # Если номер телефона уже есть
        phone_number = result[0]
        await bot.send_message(callback_query.from_user.id,
                               f"Вы записаны на поездку. Ваш номер: {phone_number}. Мы свяжемся с вами для подтверждения!")
        await bot.send_message(ADMIN_ID, f"К вам Записался человек его номер телефона {phone_number}")
    else:
        # Если номер телефона не зарегистрирован
        # Предлагаем ввести номер телефона
        enter_phone_button = types.InlineKeyboardButton(text='📞 Ввести номер телефона',
                                                        callback_data='enter_phone_number')
        keyboard = types.InlineKeyboardMarkup().add(enter_phone_button)

        mes = await bot.send_message(callback_query.from_user.id, "У вас еще нет зарегистрированного номера телефона.\n" + "Пожалуйста, введите свой номер телефона:",
                               reply_markup=keyboard)
        insert_message_id(mes.message_id, callback_query.from_user.id)


@dp.callback_query_handler(lambda c: c.data == 'enter_phone_number')
async def enter_phone_number(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    # Запрашиваем номер телефона
    mes = await bot.send_message(callback_query.from_user.id,
                           "Пожалуйста, отправьте свой номер телефона в формате: +7XXXXXXXXXX")
    insert_message_id(mes.message_id, callback_query.from_user.id)


@dp.message_handler(lambda message: message.text.startswith('+7') or message.text.startswith('8') and len(message.text) == 12)
async def save_phone_number(message: types.Message):
    phone_number = message.text
    user_id = message.from_user.id

    # Сохраняем номер телефона в базу данных
    connection = sqlite3.connect('tour_bot.db')
    cursor = connection.cursor()
    cursor.execute("INSERT OR REPLACE INTO Users (telegram_id, phone_number) VALUES (?, ?)", (user_id, phone_number))
    connection.commit()
    connection.close()

    mes = await bot.send_message(message.chat.id,
                           "Ваш номер телефона успешно записан. Теперь вы можете записаться на поездку через бота!")
    time.sleep(1)
    insert_message_id(mes.message_id, message.from_user.id)
    insert_message_id(message.message_id, message.from_user.id)

    await delete_all_message(message.chat.id, message.from_user.id)
    clear_bd_message(message.from_user.id)





# Обработчики для редактирования
@dp.callback_query_handler(lambda c: c.data == "edit_name")
async def edit_name(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await Form.waiting_for_new_name.set()  # Устанавливаем новое состояние
    await callback_query.message.delete()
    mes = await callback_query.message.answer("Введите ваше новое имя:")
    insert_message_id(mes.message_id, callback_query.from_user.id)


@dp.message_handler(state=Form.waiting_for_new_name)
async def process_new_name(message: types.Message, state: FSMContext):
    new_name = message.text
    user_id = message.from_user.id

    insert_message_id(message.message_id, message.from_user.id)

    # Сохраним новое имя в БД
    update_user(user_id, name=new_name)

    await state.finish()  # Завершить текущее состояние
    await show_user_profile(message, telegram_id=message.from_user.id, edit_mode=True)  # Показываем профиль с обновленным именем


@dp.callback_query_handler(lambda c: c.data == "edit_phone")
async def edit_phone(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await Form.waiting_for_new_phone.set()  # Устанавливаем новое состояние
    await callback_query.message.delete()
    mes = await callback_query.message.answer("Введите новый номер телефона:")
    insert_message_id(mes.message_id, callback_query.from_user.id)


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
    mes = await callback_query.message.answer("Отправьте новое фото:")
    insert_message_id(mes.message_id, callback_query.from_user.id)


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

    mes = await bot.send_message(user_id, "Вопросы и ответы:", reply_markup=faq_markup)
    insert_message_id(mes.message_id, callback_query_or_message.from_user.id)


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

    mes = await bot.send_message(user_id, "Вопросы и ответы:", reply_markup=faq_markup)
    insert_message_id(mes.message_id, callback_query_or_message.from_user.id)


@dp.callback_query_handler(lambda c: c.data == "back_to_admin", state="*")
async def back_to_admin(callback_query: types.CallbackQuery, state: FSMContext):
    print("Кнопка назад")

    await state.finish()
    await delete_all_message(callback_query.message.chat.id, callback_query.from_user.id)
    clear_bd_message(callback_query.from_user.id)

    await bot.answer_callback_query(callback_query.id)
    # Здесь вы можете вернуть пользователя в основное админ меню



    await process_admin(callback_query)




@dp.callback_query_handler(lambda c: c.data == "add_question")
async def add_question(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    mes = await bot.send_message(callback_query.from_user.id, "Введите вопрос:")
    insert_message_id(mes.message_id, callback_query.from_user.id)
    await dp.current_state(user=callback_query.from_user.id).set_data({"action": "add"})


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

        mes = await bot.send_message(callback_query.from_user.id, "Что редактируем? 😊", reply_markup=edit_markup)
        insert_message_id(mes.message_id, callback_query.from_user.id)
    else:
        mes = await bot.send_message(callback_query.from_user.id, "Вопрос не найден.")
        insert_message_id(mes.message_id, callback_query.from_user.id)


@dp.callback_query_handler(lambda c: c.data.startswith("edit_question_text_"))
async def edit_question_text(callback_query: types.CallbackQuery):
    question_id = int(callback_query.data.split("_")[-1])

    # Получаем текущий вопрос из базы данных
    question = get_current_question(question_id)

    if question:
        current_question = question[0]
        mes = await bot.send_message(callback_query.from_user.id, f"Введите новый текст для вопроса:\n{current_question}")
        insert_message_id(mes.message_id, callback_query.from_user.id)
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
        mes = await bot.send_message(callback_query.from_user.id, f"Введите новый текст для ответа:\n{current_answer}")
        insert_message_id(mes.message_id, callback_query.from_user.id)
        await dp.current_state(user=callback_query.from_user.id).set_data(
            {"action": "edit_answer_text_", "question_id": question_id})
    else:
        await bot.send_message(callback_query.from_user.id, "Ответ не найден.")


# Обработчик для кнопки "Назад"
@dp.callback_query_handler(lambda c: c.data == "back_to_questions")
async def back_to_questions(callback_query: types.CallbackQuery):
    await delete_all_message(callback_query.message.chat.id, callback_query.from_user.id)
    clear_bd_message(callback_query.from_user.id)
    await admin_faq(callback_query)  # Предполагаем, что admin_faq — это функция, которая показывает все вопросы


@dp.callback_query_handler(lambda c: c.data.startswith("delete_question_"))
async def delete_question(callback_query: types.CallbackQuery):
    insert_message_id(callback_query.message.message_id, callback_query.from_user.id)
    await delete_all_message(callback_query.message.chat.id, callback_query.from_user.id)
    clear_bd_message(callback_query.from_user.id)
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
            caption = (
                f"\n✈️ Город отправления: {departure_city if departure_city else 'Не заполнено'}\n\n"
                f"🌍 Город назначения: {arrival_city if arrival_city else 'Не заполнено'}\n\n"
                f"💰 Цена: {price if price else 'Не заполнено'}\n\n"
                f"🕒 Время отправления: {departure_time if departure_time else 'Не заполнено'}\n\n"
                f"📅 Дата поездки: {trip_date if trip_date else 'Не заполнено'}\n\n"
                f"📝 Описание: {description if description else 'Не заполнено'}\n\n"
                f"📢 Опубликовано: {'Да ✅' if published else 'Нет ❌'}"
            )

            # Создаем инлайн-кнопки
            keyboard = types.InlineKeyboardMarkup()
            edit_button = types.InlineKeyboardButton(text='✏️ Редактировать', callback_data=f'edit_tour_{tour_id}')
            delete_button = types.InlineKeyboardButton(text='🗑️ Удалить', callback_data=f'delete_tour_{tour_id}')
            keyboard.add(edit_button, delete_button)

            mes = await bot.send_photo(
                chat_id=callback_query.from_user.id,
                photo=open(photo, 'rb') if photo else "https://steamuserimages-a.akamaihd.net/ugc/950726000575702194/E9862E658BDABDC2B3AD40338ADB7DA100C56004/?imw=512&imh=320&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=true",
                caption=caption,
                reply_markup=keyboard  # Добавляем инлайн-кнопки
            )
            insert_message_id(mes.message_id, callback_query.from_user.id)

    else:
        await bot.send_message(callback_query.from_user.id, "Нет доступных поездок.")

    # Кнопки для добавления поездки и возврат
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"),
        types.InlineKeyboardButton("➕ Добавить поездку", callback_data="add_tour")
    )

    mes = await bot.send_message(callback_query.from_user.id, "Выберите действие:", reply_markup=markup)
    insert_message_id(mes.message_id, callback_query.from_user.id)


@dp.callback_query_handler(lambda c: c.data.startswith('edit_tour_'))
async def edit_tour(callback_query: types.CallbackQuery):
    await delete_all_message(callback_query.message.chat.id, callback_query.from_user.id)
    clear_bd_message(callback_query.from_user.id)
    tour_id = callback_query.data.split('_')[-1]  # Получаем tour_id

    conn = sqlite3.connect('tour_bot.db')

    # Получаем обновленную информацию о поездке
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tours WHERE id = ?", (tour_id,))
    tour_info = cursor.fetchone()
    conn.close()

    # Формируем новое caption
    caption = create_caption(tour_info)
    photo_path = os.path.join(PHOTO_DIR, f'tour_{tour_id}.jpg')  # Формируем имя файла

    if not os.path.isfile(photo_path):
        photo_path = False

    mes = await bot.send_photo(
        chat_id=callback_query.from_user.id,
        photo=open(photo_path,
                   'rb') if photo_path else "https://steamuserimages-a.akamaihd.net/ugc/950726000575702194/E9862E658BDABDC2B3AD40338ADB7DA100C56004/?imw=512&imh=320&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=true",
        caption=caption,
        reply_markup=generate_inline_keyboard(tour_id)
    )

    insert_message_id(mes.message_id, callback_query.from_user.id)


@dp.callback_query_handler(lambda c: c.data.startswith('delete_tour_'))
async def delete_tour(callback_query: types.CallbackQuery):
    # Получаем tour_id из callback_data
    tour_id = callback_query.data.split('_')[-1]

    # Создаем соединение с базой данных
    connection = sqlite3.connect('tour_bot.db')
    cursor = connection.cursor()

    # Удаляем запись о поездке по заданному tour_id
    cursor.execute("DELETE FROM Tours WHERE id = ?", (tour_id,))
    connection.commit()
    connection.close()

    # Отправляем сообщение о том, что поездка была удалена
    await view_tours(callback_query)


# Ваш обработчик для нажатия кнопки "Добавить поездку"
@dp.callback_query_handler(lambda c: c.data == "add_tour")
async def add_tour(callback_query: types.CallbackQuery):
    await delete_all_message(callback_query.message.chat.id, callback_query.from_user.id)
    clear_bd_message(callback_query.from_user.id)
    conn = sqlite3.connect('tour_bot.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO Tours (departure_city, arrival_city, price, departure_time, trip_date, description, photo, status, published) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', ("", "", 0.0, "", "", "", "", "", False))

    new_tour_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT * FROM Tours WHERE id = ?", (new_tour_id,))
    tour_info = cursor.fetchone()
    conn.close()

    caption = create_caption(tour_info)

    mes = await bot.send_photo(
        chat_id=callback_query.from_user.id,
        photo="https://steamuserimages-a.akamaihd.net/ugc/950726000575702194/E9862E658BDABDC2B3AD40338ADB7DA100C56004/?imw=512&imh=320&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=true",
        caption=caption,
        reply_markup=generate_inline_keyboard(new_tour_id)
    )

    insert_message_id(mes.message_id, callback_query.from_user.id)


def create_caption(tour_info):
    if tour_info:
        departure_city, arrival_city, price, departure_time, trip_date, description, photo, status, published = tour_info[1:]  # Пропускаем ID
        caption = (
            f"\n✈️ Город отправления: {departure_city if departure_city else 'Не заполнено'}\n\n"
            f"🌍 Город назначения: {arrival_city if arrival_city else 'Не заполнено'}\n\n"
            f"💰 Цена: {price if price else 'Не заполнено'}\n\n"
            f"🕒 Время отправления: {departure_time if departure_time else 'Не заполнено'}\n\n"
            f"📅 Дата поездки: {trip_date if trip_date else 'Не заполнено'}\n\n"
            f"📝 Описание: {description if description else 'Не заполнено'}\n\n"
            f"📢 Опубликовано: {'Да ✅' if published else 'Нет ❌'}"
        )

        return caption
    return "Нет информации."


def generate_inline_keyboard(tour_id):
    keyboard = types.InlineKeyboardMarkup()

    # Получаем информацию о туре, чтобы проверить заполненность полей
    conn = sqlite3.connect('tour_bot.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT departure_city, arrival_city, price, departure_time, trip_date, description, photo, published FROM Tours WHERE id = ?",
        (tour_id,))
    tour_info = cursor.fetchone()
    conn.close()

    fields = [
        ("Город отправления", tour_info[0]),
        ("Город назначения", tour_info[1]),
        ("Цена", tour_info[2]),
        ("Время отправления", tour_info[3]),
        ("Дата поездки", tour_info[4]),
        ("Описание", tour_info[5]),
        ("Ссылка на фото", tour_info[6]),
        ("Опубликовано", 'Да' if tour_info[7] else 'Нет')
    ]

    call_data = [
        'departure-city',
        'arrival-city',
        'price',
        'departure-time',
        'trip-date',
        'description',
        'photo',
        'published'
    ]

    count = 0
    for field_name, field_value in fields:
        emoji = '✅' if field_value and field_value != "Нет" else '❌'
        button_text = f"{emoji} {field_name}"
        button = types.InlineKeyboardButton(text=button_text,
                                            callback_data=f"edit_field_{call_data[count]}_{tour_id}")
        keyboard.add(button)
        count += 1
        print(field_name, field_value)
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))
    return keyboard

# full timepicker usage
@dp.callback_query_handler(full_timep_callback.filter())
async def process_full_timepicker(callback_query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    user_data = await state.get_data()
    tour_id = user_data.get('tour_id')
    r = await FullTimePicker().process_selection(callback_query, callback_data)
    if r.selected:
        await callback_query.message.delete_reply_markup()

        conn = sqlite3.connect('tour_bot.db')
        cursor = conn.cursor()

        cursor.execute(f"UPDATE Tours SET {'departure_time'} = ? WHERE id = ?", (r.time.strftime("%H:%M"), tour_id))
        conn.commit()

        # Получаем обновленную информацию о поездке
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Tours WHERE id = ?", (tour_id,))
        tour_info = cursor.fetchone()
        conn.close()

        # Формируем новое caption
        caption = create_caption(tour_info)
        photo_path = os.path.join(PHOTO_DIR, f'tour_{tour_id}.jpg')  # Формируем имя файла

        if not os.path.isfile(photo_path):
            photo_path = False

        # Отправляем обновленное сообщение с фотографией
        await bot.send_photo(
            chat_id=callback_query.from_user.id,
            photo=open(photo_path, 'rb') if photo_path else "https://steamuserimages-a.akamaihd.net/ugc/950726000575702194/E9862E658BDABDC2B3AD40338ADB7DA100C56004/?imw=512&imh=320&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=true",
            caption=caption,
            reply_markup=generate_inline_keyboard(tour_id)
        )

        await state.finish()  # Завершаем текущее состояние



@dp.callback_query_handler(lambda c: c.data.startswith("edit_field_"))
async def edit_field(callback_query: types.CallbackQuery, state: FSMContext):    # Получаем tour_id и поле, которое пользователь хочет редактировать из callback_data
    field, tour_id = callback_query.data.split('_')[-2], callback_query.data.split('_')[-1]

    # Сохраняем tour_id в состояние
    await state.update_data(tour_id=tour_id)

    if field == 'departure-city':
        mes = await callback_query.message.answer("Введите город отправления:")
        insert_message_id(mes.message_id, callback_query.from_user.id)
        await TourStates.waiting_for_field_value.set()
        await state.update_data(field_name='departure_city')

    elif field == 'arrival-city':
        mes = await callback_query.message.answer("Введите город назначения:")
        insert_message_id(mes.message_id, callback_query.from_user.id)
        await TourStates.waiting_for_field_value.set()
        await state.update_data(field_name='arrival_city')

    elif field == 'price':
        mes = await callback_query.message.answer("Введите цену:")
        insert_message_id(mes.message_id, callback_query.from_user.id)
        await TourStates.waiting_for_field_value.set()
        await state.update_data(field_name='price')

    elif field == 'departure-time':
        mes = await callback_query.message.answer(
            "Выберите время начала поездки: ",
            reply_markup=await FullTimePicker().start_picker()
        )
        insert_message_id(mes.message_id, callback_query.from_user.id)

    elif field == 'trip-date':
        mes = await callback_query.message.answer("Введите дату поездки:")
        insert_message_id(mes.message_id, callback_query.from_user.id)
        datepicker = Datepicker(_get_datepicker_settings())

        markup = datepicker.start_calendar()
        mes = await callback_query.message.answer('Select a date: ', reply_markup=markup)
        insert_message_id(mes.message_id, callback_query.from_user.id)
        await state.update_data(field_name='trip_date')

    elif field == 'description':
        mes = await callback_query.message.answer("Введите описание:")
        insert_message_id(mes.message_id, callback_query.from_user.id)
        await TourStates.waiting_for_field_value.set()
        await state.update_data(field_name='description')

    elif field == 'photo':
        mes = await callback_query.message.answer("Введите ссылку на фото:")
        insert_message_id(mes.message_id, callback_query.from_user.id)
        await TourStates.waiting_for_photo.set()
        await state.update_data(field_name='photo')

    elif field == 'published':
        photo_path = os.path.join(PHOTO_DIR, f'tour_{tour_id}.jpg')  # Формируем имя файла

        if not os.path.isfile(photo_path):
            photo_path = False
        conn = sqlite3.connect('tour_bot.db')

        # Получаем обновленную информацию о поездке
        cursor = conn.cursor()
        cursor.execute("SELECT published FROM Tours WHERE id = ?", (tour_id,))

        is_published = cursor.fetchone()[0]
        print(is_published)

        if is_published:
            cursor.execute(f"UPDATE Tours SET published = ? WHERE id = ?", (0, tour_id))
            conn.commit()
        else:
            cursor.execute(f"UPDATE Tours SET published = ? WHERE id = ?", (1, tour_id))
            conn.commit()

        cursor.execute("SELECT * FROM Tours WHERE id = ?", (tour_id,))
        tour_info = cursor.fetchone()
        conn.close()

        # Формируем новое caption
        caption = create_caption(tour_info)

        # Отправляем обновленное сообщение с фотографией
        mes = await bot.send_photo(
            chat_id=callback_query.from_user.id,
            photo=open(photo_path, 'rb') if photo_path else "https://steamuserimages-a.akamaihd.net/ugc/950726000575702194/E9862E658BDABDC2B3AD40338ADB7DA100C56004/?imw=512&imh=320&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=true",
            caption=caption,
            reply_markup=generate_inline_keyboard(tour_id)
        )
        insert_message_id(mes.message_id, callback_query.from_user.id)


DatepickerSettings(
    initial_view='day',  #available views -> day, month, year
    initial_date=datetime.now().date(),  #default date
    views={
        'day': {
            'show_weekdays': True,
            'weekdays_labels': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
            'header': ['prev-year', 'days-title',  'next-year'],
            'footer': ['prev-month', 'select', 'next-month'], #if you don't need select action, you can remove it and the date will return automatically without waiting for the button select
            #available actions -> prev-year, days-title, next-year, prev-month, select, next-month, ignore
        },
        'month': {
            'months_labels': ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
            'header': [
                        ['prev-year', 'year', 'next-year'], #you can separate buttons into groups
                       ],
            'footer': ['select'],
            #available actions -> prev-year, year, next-year, select, ignore
        },
        'year': {
            'header': [],
            'footer': ['prev-years', 'next-years'],
            #available actions -> prev-years, ignore, next-years
        }
    },
    labels={
        'prev-year': '<<',
        'next-year': '>>',
        'prev-years': '<<',
        'next-years': '>>',
        'days-title': '{month} {year}',
        'selected-day': '{day} *',
        'selected-month': '{month} *',
        'present-day': '• {day} •',
        'prev-month': '<',
        'select': 'Выбрать',
        'next-month': '>',
        'ignore': ''
    },
    custom_actions=[] #some custom actions

)

def _get_datepicker_settings():
    return DatepickerSettings() #some settings


@dp.callback_query_handler(Datepicker.datepicker_callback.filter())
async def _process_datepicker(callback_query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    datepicker = Datepicker(_get_datepicker_settings())
    date = await datepicker.process(callback_query, callback_data)
    if date:
        user_data = await state.get_data()
        field_name = user_data.get('field_name')
        tour_id = user_data.get('tour_id')
        photo_path = os.path.join(PHOTO_DIR, f'tour_{tour_id}.jpg')  # Формируем имя файла

        if not os.path.isfile(photo_path):
            photo_path = False

        # Обновляем значение в БД
        conn = sqlite3.connect('tour_bot.db')
        cursor = conn.cursor()

        cursor.execute(f"UPDATE Tours SET {field_name} = ? WHERE id = ?", (date.strftime('%d.%m.%Y'), tour_id))
        conn.commit()

        # Получаем обновленную информацию о поездке
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Tours WHERE id = ?", (tour_id,))
        tour_info = cursor.fetchone()
        conn.close()

        # Формируем новое caption
        caption = create_caption(tour_info)

        # Отправляем обновленное сообщение с фотографией
        mes = await bot.send_photo(
            chat_id=callback_query.from_user.id,
            photo=open(photo_path, 'rb') if photo_path else "https://steamuserimages-a.akamaihd.net/ugc/950726000575702194/E9862E658BDABDC2B3AD40338ADB7DA100C56004/?imw=512&imh=320&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=true",
            caption=caption,
            reply_markup=generate_inline_keyboard(tour_id)
        )
        insert_message_id(mes.message_id, callback_query.from_user.id)

        await state.finish()  # Завершаем текущее состояние

    await callback_query.answer()


@dp.message_handler(state=TourStates.waiting_for_field_value)
async def process_field_value(message: types.Message, state: FSMContext):
    insert_message_id(message.message_id, message.from_user.id)
    await delete_all_message(message.chat.id, message.from_user.id)
    clear_bd_message(message.from_user.id)
    user_data = await state.get_data()
    field_name = user_data.get('field_name')
    tour_id = user_data.get('tour_id')

    # Обновляем значение в БД
    conn = sqlite3.connect('tour_bot.db')
    cursor = conn.cursor()

    # Проверка, нужно ли конвертировать значение в boolean
    if field_name == 'published':
        value = message.text.strip().lower() == 'да'
    else:
        value = message.text.strip()

    cursor.execute(f"UPDATE Tours SET {field_name} = ? WHERE id = ?", (value, tour_id))
    conn.commit()

    # Получаем обновленную информацию о поездке
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tours WHERE id = ?", (tour_id,))
    tour_info = cursor.fetchone()
    conn.close()

    # Формируем новое caption
    caption = create_caption(tour_info)

    photo_path = os.path.join(PHOTO_DIR, f'tour_{tour_id}.jpg')  # Формируем имя файла

    if not os.path.isfile(photo_path):
        photo_path = False

    # Отправляем обновленное сообщение с фотографией
    mes = await bot.send_photo(
        chat_id=message.from_user.id,
        photo=open(photo_path, 'rb') if photo_path else "https://steamuserimages-a.akamaihd.net/ugc/950726000575702194/E9862E658BDABDC2B3AD40338ADB7DA100C56004/?imw=512&imh=320&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=true",
        caption=caption,
        reply_markup=generate_inline_keyboard(tour_id)
    )
    insert_message_id(mes.message_id, message.from_user.id)

    await state.finish()  # Завершаем текущее состояние


@dp.message_handler(content_types=types.ContentType.PHOTO, state=TourStates.waiting_for_photo)
async def process_photo(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    field_name = user_data.get('field_name')
    tour_id = user_data.get('tour_id')
    # Получаем ID фотографии
    file_id = message.photo[-1].file_id  # Получаем наилучшее качество фото

    # Загружаем фотографию
    photo = await bot.get_file(file_id)
    photo_file = await bot.download_file(photo.file_path)

    # Сохраняем фотографию в папку tour_photo
    photo_path = os.path.join(PHOTO_DIR, f'tour_{tour_id}.jpg')  # Формируем имя файла
    with open(photo_path, 'wb') as new_file:
        new_file.write(photo_file.getvalue())

    # Обновляем значение в БД
    conn = sqlite3.connect('tour_bot.db')
    cursor = conn.cursor()

    cursor.execute("UPDATE Tours SET photo = ? WHERE id = ?", (photo_path, tour_id))
    conn.commit()

    # Получаем обновленную информацию о поездке
    cursor.execute("SELECT * FROM Tours WHERE id = ?", (tour_id,))
    tour_info = cursor.fetchone()
    conn.close()

    # Формируем новое caption
    caption = create_caption(tour_info)

    # Отправляем обновленное сообщение с фотографией
    mes = await bot.send_photo(
        chat_id=message.from_user.id,
        photo=open(photo_path, 'rb'),  # Открываем фото для отправки
        caption=caption,
        reply_markup=generate_inline_keyboard(tour_id)
    )
    insert_message_id(mes.message_id, message.from_user.id)

    await state.finish()  # Завершаем текущее состояние


@dp.message_handler(state="*")
async def handle_new_question(message: types.Message, state: FSMContext):
    user_data = await state.get_data()

    print(user_data)

    if "action" in user_data and user_data["action"] == "add":
        question_text = message.text
        mes = await bot.send_message(message.from_user.id, "Введите ответ:")
        insert_message_id(mes.message_id, message.from_user.id)
        insert_message_id(message.message_id, message.from_user.id)
        await state.update_data({"question": question_text, "action": "add_answer"})
    elif "action" in user_data and user_data["action"] == "add_answer":
        answer_text = message.text
        insert_question(user_data["question"], answer_text)
        mes = await bot.send_message(message.from_user.id, "Вопрос добавлен!")
        insert_message_id(mes.message_id, message.from_user.id)
        insert_message_id(message.message_id, message.from_user.id)
        await delete_all_message(message.chat.id, message.from_user.id)
        clear_bd_message(message.from_user.id)
        await admin_faq_2(message)
        await state.finish()  # Сброс состояния

    elif "action" in user_data and user_data["action"] == "edit_question_text_":
        question_id = user_data["question_id"]
        new_question_text = message.text
        update_question_in_db(question_id, new_question_text)  # Ваша функция обновления
        mes = await bot.send_message(message.from_user.id, "Вопрос обновлен!")
        insert_message_id(mes.message_id, message.from_user.id)
        insert_message_id(message.message_id, message.from_user.id)
        await delete_all_message(message.chat.id, message.from_user.id)
        clear_bd_message(message.from_user.id)

        await admin_faq(message)  # Вернем к вопросам и ответам
        await state.finish()

    elif "action" in user_data and user_data["action"] == "edit_answer_text_":
        question_id = user_data["question_id"]
        new_answer_text = message.text
        update_answer_in_db(question_id, new_answer_text)  # Ваша функция обновления
        mes = await bot.send_message(message.from_user.id, "Ответ обновлен!")
        insert_message_id(mes.message_id, message.from_user.id)
        insert_message_id(message.message_id, message.from_user.id)
        await delete_all_message(message.chat.id, message.from_user.id)
        clear_bd_message(message.from_user.id)

        await admin_faq(message)  # Вернем к вопросам и ответам
        await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
