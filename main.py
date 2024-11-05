import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher import filters
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from states import Questions, Trip
from bd import insert_question, insert_tour, get_questions

API_TOKEN = ''

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


# Главное меню
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Частые вопросы", "Планируемые поездки"]
    markup.add(*buttons)
    await message.answer("Добро пожаловать! Выберите опцию:", reply_markup=markup)


@dp.message_handler(filters.Text(equals="Частые вопросы"))
async def show_questions(message: types.Message):
    questions = get_questions()

    if not questions:
        await message.answer("Нет доступных вопросов.")
        return

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    for question, _ in questions:
        markup.add(question)

    # Добавляем кнопку "Назад" для возврата в главное меню
    markup.add(KeyboardButton("Назад в главное меню"))

    await message.answer("Выберите вопрос:", reply_markup=markup)


@dp.message_handler(lambda message: message.text in [q[0] for q in get_questions()])
async def answer_question(message: types.Message):
    question = message.text
    answer = None

    # Получаем ответ из базы данных
    for q, a in get_questions():
        if q == question:
            answer = a
            break

    if answer:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("Назад"))

        await message.answer(answer, reply_markup=markup)
    else:
        await message.answer("Извините, я не нашел ответ на этот вопрос.")


@dp.message_handler(text="Назад")
async def back_to_questions(message: types.Message):
    await show_questions(message)


@dp.message_handler(text="Назад в главное меню")
async def back_to_main_menu(message: types.Message):
    await start_command(message)


# ADMIN - ДОБАВЛЕНИЕ ВОПРОСА-ОТВЕТА
@dp.message_handler(commands=['add_question'])
async def add_question(message: types.Message, state: FSMContext):
    await message.answer("Введите новый вопрос:")
    await state.set_state(Questions.question)


@dp.message_handler(state=Questions.question)
async def process_new_question(message: types.Message, state: FSMContext):
    await state.update_data(question=message.text)
    await message.answer("Вопрос добавлен успешно!")
    await state.set_state(Questions.answer)
    await message.answer("Введите ответ на этот вопрос:")


@dp.message_handler(state=Questions.answer)
async def process_new_question(message: types.Message, state: FSMContext):
    await state.update_data(answer=message.text)
    await message.answer("Ответ добавлен успешно!")

    data = await state.get_data()

    insert_question(data.get("question"), data.get("answer"))
    await state.finish()


# ADMIN - ДОБАВЛЕНИЕ ПОЕЗДКИ
@dp.message_handler(commands=['add_trip'])
async def add_trip(message: types.Message):
    await message.answer("Введите город отправления:")
    await Trip.departure_city.set()


@dp.message_handler(state=Trip.departure_city)
async def process_departure_city(message: types.Message, state: FSMContext):
    await state.update_data(departure_city=message.text)
    await message.answer("Введите город назначения:")
    await Trip.arrival_city.set()


@dp.message_handler(state=Trip.arrival_city)
async def process_arrival_city(message: types.Message, state: FSMContext):
    await state.update_data(arrival_city=message.text)
    await message.answer("Введите цену поездки:")
    await Trip.price.set()


@dp.message_handler(state=Trip.price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Введите время отправления:")
    await Trip.departure_time.set()


@dp.message_handler(state=Trip.departure_time)
async def process_departure_time(message: types.Message, state: FSMContext):
    await state.update_data(departure_time=message.text)
    await message.answer("Введите дату поездки (YYYY-MM-DD):")
    await Trip.trip_date.set()


@dp.message_handler(state=Trip.trip_date)
async def process_trip_date(message: types.Message, state: FSMContext):
    await state.update_data(trip_date=message.text)
    await message.answer("Введите описание поездки:")
    await Trip.description.set()


@dp.message_handler(state=Trip.description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)

    data = await state.get_data()

    # Вывод данных о поездке
    await message.answer("Поездка добавлена успешно:\n"
                         f"Город отправления: {data['departure_city']}\n"
                         f"Город назначения: {data['arrival_city']}\n"
                         f"Цена: {data['price']}₽\n"
                         f"Время отправления: {data['departure_time']}\n"
                         f"Дата поездки: {data['trip_date']}\n"
                         f"Описание: {data['description']}")

    # Сохранение в базу данных
    insert_tour(
        data['departure_city'],
        data['arrival_city'],
        data['price'],
        data['departure_time'],
        data['trip_date'],
        data['description']
    )

    await state.finish()


@dp.message_handler(commands=['admin'])
async def admin_area(message: types.Message):
    if message.from_user.id == 868918195:  # Замените на ID вашего администратора
        await message.answer("Добро пожаловать в админ-панель!\n\n"
                             "Используйте /add_question для добавления вопроса-ответа\n"
                             "Используйте /add_tour для добавления поездки")
    else:
        await message.answer("У вас недостаточно прав для доступа к этой команде.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
