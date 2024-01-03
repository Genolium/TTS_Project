from aiogram import types

#токен Telegram бота
API_TOKEN = ''

commands = [
    types.BotCommand(command="/start", description="Начать работу"),
    types.BotCommand(command="/change", description="Сменить голос"),
]

#максимальный размер файла в МБ (больше - отправляется через облако)
limit = 50

torch_num_threads: int = 4
