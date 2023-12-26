from aiogram import types

#токен Telegram бота
API_TOKEN = ''

commands = [
    types.BotCommand(command="/start", description="Начать работу"),
    types.BotCommand(command="/change", description="Сменить голос"),
]
