import logging, asyncio, nltk, os, config
from pydub import AudioSegment
from tts import va_speak
from db import *
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

bot = Bot(token=config.API_TOKEN)
dp = Dispatcher(bot)

#Команда start
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    voice = getUserPreferenceVoice(message.chat.id)
    await message.reply("Привет! Я эхо-бот. Просто отправь мне сообщение, и я отправлю озвучку этого сообщения.")

#Команда смены голоса
@dp.message_handler(commands=['change'])
async def send_welcome(message: types.Message):
    voice = getUserPreferenceVoice(message.chat.id)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        KeyboardButton("Aidar"),
        KeyboardButton("Baya"),
        KeyboardButton("Kseniya"),
        KeyboardButton("Xenia"),
    ]
    keyboard.add(*buttons)
    await message.reply("Выберите новый голос", reply_markup=keyboard)

#Обработчик выбранного голоса
@dp.message_handler(lambda message: message.text.lower() in ["aidar", "baya", "kseniya", "xenia"])
async def universal_button_handler(message: types.Message):
    changeUserPreferenceVoice(message.chat.id, message.text.lower())
    await message.answer(f"Вы выбрали новый голос", reply_markup=ReplyKeyboardRemove())

#Обработчик для получения и обработки .txt файла
@dp.message_handler(content_types=['document'])
async def handle_txt_file(message: types.Message):
    if message.document.mime_type == 'text/plain' and message.document.file_name.endswith('.txt'):
        file_id = message.document.file_id
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path
        txt_content = await bot.download_file(file_path)
        txt_content_str = txt_content.read().decode('utf-8')
        voice = getUserPreferenceVoice(message.chat.id)
        wav = str(message.chat.id) + str(message.message_id) + ".wav"
        mp3 = str(message.chat.id) + str(message.message_id) + ".mp3"
        await message.reply("Обрабатываем ваш файл")
        await va_speak(txt_content_str, wav, voice[1])
        sound = AudioSegment.from_wav(wav)
        sound.export(mp3, format="wav")
        with open(mp3, 'rb') as audio_file:
            await bot.send_audio(message.chat.id, audio_file, caption="Вот ваш аудиофайл:")
        os.remove(mp3)
        os.remove(wav)

#Обработчик всех остальных сообщений
@dp.message_handler()
async def echo(message: types.Message):
    await message.reply("Обрабатываем ваше сообщение")
    voice = getUserPreferenceVoice(message.chat.id)
    wav = str(message.chat.id) + str(message.message_id) + ".wav"
    mp3 = str(message.chat.id) + str(message.message_id) + ".mp3"
    await va_speak(message.text, wav, voice[1])
    sound = AudioSegment.from_wav(wav)
    sound.export(mp3, format="wav")
    with open(mp3, 'rb') as audio_file:
        await bot.send_audio(message.chat.id, audio_file, caption="Вот ваш аудиофайл:")
    os.remove(mp3)
    os.remove(wav)

#Действия, выполняемые при запуске программы
async def on_startup(dp):
    logging.basicConfig(level=logging.INFO)
    nltk.download('punkt')
    start() 
    await dp.bot.set_my_commands(config.commands)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(executor.start_polling(dp, skip_updates=True, on_startup=on_startup))
    loop.run_forever()