import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.utils import executor

from aiogram_datepicker import Datepicker, DatepickerSettings

logging.basicConfig(level=logging.INFO)
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

API_TOKEN = '7430055967:AAE_ptETbGQV1CT2RoeqTTFDV1N6flWzquY'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, run_tasks_by_default=True)


def _get_datepicker_settings():
    return DatepickerSettings() #some settings


@dp.message_handler(state='*')
async def _main(message: Message):
    datepicker = Datepicker(_get_datepicker_settings())

    markup = datepicker.start_calendar()
    await message.answer('Select a date: ', reply_markup=markup)


@dp.callback_query_handler(Datepicker.datepicker_callback.filter())
async def _process_datepicker(callback_query: CallbackQuery, callback_data: dict):
    datepicker = Datepicker(_get_datepicker_settings())
    date = await datepicker.process(callback_query, callback_data)
    if date:
        await callback_query.message.answer(date.strftime('%d/%m/%Y'))

    await callback_query.answer()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)