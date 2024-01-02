from aiogram import types

#токен Telegram бота
API_TOKEN = '6736801084:AAEOeS5vrhFXU_i_zP837E4_eyIOs8SeIFM'

commands = [
    types.BotCommand(command="/start", description="Начать работу"),
    types.BotCommand(command="/change", description="Сменить голос"),
]

#максимальный размер файла в МБ (больше - отправляется через облако)
limit = 50

torch_num_threads: int = 4