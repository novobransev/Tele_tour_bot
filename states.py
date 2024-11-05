from aiogram.dispatcher.filters.state import State, StatesGroup


class Questions(StatesGroup):
    question = State()
    answer = State()


class Trip(StatesGroup):
    departure_city = State()
    arrival_city = State()
    price = State()
    departure_time = State()
    trip_date = State()
    description = State()