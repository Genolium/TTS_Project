from aiogram import types

#токен Telegram бота
API_TOKEN = '6039661155:AAGaebqmeYT8ztLqU7O7IrhjFD9cWSdq2uI'

commands = [
    types.BotCommand(command="/start", description="Начать работу"),
    types.BotCommand(command="/change", description="Сменить голос"),
]