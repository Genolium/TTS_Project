import logging, asyncio, nltk, PyPDF2, os, config, requests
from pydub import AudioSegment
from tts import va_speak
from db import *
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

bot = Bot(token=config.API_TOKEN)
dp = Dispatcher(bot)

#максимальный размер файла в МБ (больше - отправляется через облако)
limit = 50

#Команда start
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    voice = await getUserPreferenceVoice(message.chat.id)
    await message.reply("Привет! Я эхо-бот. Просто отправь мне сообщение, и я отправлю озвучку этого сообщения.")

#Команда смены голоса
@dp.message_handler(commands=['change'])
async def send_welcome(message: types.Message):
    voice = await getUserPreferenceVoice(message.chat.id)
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
    await changeUserPreferenceVoice(message.chat.id, message.text.lower())
    await message.answer(f"Вы выбрали новый голос", reply_markup=ReplyKeyboardRemove())

#Обработчик для получения и обработки .txt и .pdf файла
@dp.message_handler(content_types=['document'])
async def handle_txt_file(message: types.Message):
    #txt
    if message.document.mime_type == 'text/plain' and message.document.file_name.endswith('.txt'):
        await message.reply("Обрабатываем ваш файл")
        file_id = message.document.file_id
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path
        txt_content = await bot.download_file(file_path)
        txt_content_str = txt_content.read().decode('utf-8')
        voice = await getUserPreferenceVoice(message.chat.id)
        wav = str(message.chat.id) + str(message.message_id) + ".wav"
        mp3 = str(message.chat.id) + str(message.message_id) + ".mp3"
        await va_speak(txt_content_str, wav, voice[1])
        sound = AudioSegment.from_wav(wav)
        sound.export(mp3, format="wav")

        #если размер меньше 50Мб
        if (os.path.getsize(mp3) < limit * 1024 * 1024):
            with open(mp3, 'rb') as audio_file:
                await message.reply_audio(audio=audio_file, caption="Вот ваш аудиофайл:")
        else:
            url = "https://file.io"
            with open(mp3, "rb") as file:
                files = {"file": file}
                response = requests.post(url, files=files)
                if response.status_code == 200:
                    file_url = response.json()["link"]
                    await message.reply(f"Ваш файл больше 50 МБ. Ссылка на облако: {file_url}")

        os.remove(mp3)
        os.remove(wav)

    #pdf
    elif message.document.mime_type == 'application/pdf':
        await message.reply("Обрабатываем ваш файл")
        file_info = await bot.get_file(message.document.file_id)
        file_object = await bot.download_file(file_info.file_path)
        pdf = str(message.chat.id) + str(message.message_id) +".pdf"
        with open(pdf, "wb") as pdf_file:
            pdf_file.write(file_object.read())
        text = ""
        with open(pdf, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()

        voice = await getUserPreferenceVoice(message.chat.id)
        wav = str(message.chat.id) + str(message.message_id) + ".wav"
        mp3 = str(message.chat.id) + str(message.message_id) + ".mp3"
        await va_speak(text, wav, voice[1])
        sound = AudioSegment.from_wav(wav)
        sound.export(mp3, format="wav")

        #если размер меньше 50Мб
        if (os.path.getsize(mp3) < limit * 1024 * 1024):
            with open(mp3, 'rb') as audio_file:
                await message.reply_audio(audio=audio_file, caption="Вот ваш аудиофайл:")
        else:
            url = "https://file.io"
            with open(mp3, "rb") as file:
                files = {"file": file}
                response = requests.post(url, files=files)
                if response.status_code == 200:
                    file_url = response.json()["link"]
                    await message.reply(f"Ваш файл больше 50 МБ. Ссылка на облако: {file_url}")

        os.remove(pdf)
        os.remove(mp3)
        os.remove(wav)

#Обработчик всех остальных сообщений
@dp.message_handler()
async def echo(message: types.Message):
    await message.reply("Обрабатываем ваше сообщение")
    try:
        voice = await getUserPreferenceVoice(message.chat.id)
        wav = str(message.chat.id) + str(message.message_id) + ".wav"
        mp3 = str(message.chat.id) + str(message.message_id) + ".mp3"
        await va_speak(message.text, wav, voice[1])
        sound = AudioSegment.from_wav(wav)
        sound.export(mp3, format="wav")
        with open(mp3, 'rb') as audio_file:
            await message.reply_audio(audio=audio_file, caption="Вот ваш аудиофайл:")
        os.remove(mp3)
        os.remove(wav)
    except:
        await message.reply("Произошла неизвестная ошибка, попробуйте отправить сообщение снова.")


#Действия, выполняемые при запуске программы
async def on_startup(dp):
    logging.basicConfig(level=logging.INFO)
    nltk.download('punkt')
    await start() 
    await dp.bot.set_my_commands(config.commands)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)