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
    photo = State()


class Form(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_phone = State()
    waiting_for_new_photo = State()


class Tours(StatesGroup):
    waiting_for_tour_info = State()  # Ожидание информации о новой поездке


class TourStates(StatesGroup):
    waiting_for_field_value = State()
    waiting_for_photo = State()