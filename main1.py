from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
API_TOKEN = '7430055967:AAE_ptETbGQV1CT2RoeqTTFDV1N6flWzquY'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler()
async def echo_message(message: types.Message):
    await message.answer(message.text)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)