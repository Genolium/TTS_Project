import logging, asyncio, nltk, PyPDF2, os, config, requests, time, multiprocessing, colorama
from pydub import AudioSegment
from pydub.effects import normalize, low_pass_filter, high_pass_filter
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ChatActions, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from transliterate import translit
from colorama import Fore, Back, Style
from tts import *
from local_mode import *
from config import *
from db import *

colorama.init()
bot = Bot(token=config.API_TOKEN)
dp = Dispatcher(bot)

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

        start_time = time.time()
        file_id = message.document.file_id
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f'https://api.telegram.org/file/bot{config.API_TOKEN}/{file_path}'
        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        with open(file_path, 'r', encoding='utf-8') as file:
            txt_content_str = file.read().decode('utf-8')
        end_time = time.time()
        print(f"Файл {message.message_id} размером {os.path.getsize(pdf)/1024/1024}Мб скачался за: {end_time - start_time:.2f} с.")

        voice = await getUserPreferenceVoice(message.chat.id)
        wav = str(message.chat.id) + str(message.message_id) + ".wav"
        mp3 = str(message.chat.id) + str(message.message_id) + ".mp3"
        
        start_time = time.time()
        await va_speak(txt_content_str, wav, voice[1])
        end_time = time.time()
        print(f"Файл {message.message_id} длиной в {len(txt_content_str)} символ(-ов) обработан в звук за: {end_time - start_time:.2f} с.")

        sound = AudioSegment.from_wav(wav)
        sound.export(mp3, format="wav")

        start_time = time.time()
        #если размер меньше 50Мб
        if (os.path.getsize(mp3) < limit * 1024 * 1024):
            with open(mp3, 'rb') as audio_file:
                await bot.send_chat_action(message.chat.id, ChatActions.UPLOAD_DOCUMENT)
                await message.reply_audio(audio=audio_file, caption="Вот ваш аудиофайл:")  
        else:
            url = "https://file.io"
            with open(mp3, "rb") as file:
                files = {"file": file}
                response = requests.post(url, files=files)
                if response.status_code == 200:
                    file_url = response.json()["link"]
                    await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
                    await message.reply(f"Ваш файл больше 50 МБ. Ссылка на облако: {file_url}") 
        end_time = time.time()
        print(f"Файл {mp3} размером {os.path.getsize(mp3)/1024/1024}Мб отправлен за: {end_time - start_time:.2f} с.")

        os.remove(mp3)
        os.remove(wav)

    #pdf
    elif message.document.mime_type == 'application/pdf':
        await message.reply("Обрабатываем ваш файл")
        
        start_time = time.time()
        pdf = str(message.chat.id) + str(message.message_id) +".pdf"
        file_id = message.document.file_id
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f'https://api.telegram.org/file/bot{config.API_TOKEN}/{file_path}'
        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            with open(pdf, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        text = ""
        with open(pdf, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
        end_time = time.time()
        print(f"Файл {message.message_id} размером {os.path.getsize(pdf)/1024/1024}Мб скачался за: {end_time - start_time:.2f} с.")

        voice = await getUserPreferenceVoice(message.chat.id)
        wav = str(message.chat.id) + str(message.message_id) + ".wav"
        mp3 = str(message.chat.id) + str(message.message_id) + ".mp3"

        start_time = time.time()
        await va_speak(text, wav, voice[1])
        end_time = time.time()
        print(f"Файл {message.message_id} длиной в {len(text)} символ(-ов) обработан в звук за: {end_time - start_time:.2f} с.")

        sound = AudioSegment.from_wav(wav)
        sound.export(mp3, format="wav")

        start_time = time.time()
        #если размер меньше 50Мб
        if (os.path.getsize(mp3) < limit * 1024 * 1024):
            with open(mp3, 'rb') as audio_file:
                await bot.send_chat_action(message.chat.id, ChatActions.UPLOAD_DOCUMENT)
                await message.reply_audio(audio=audio_file, caption="Вот ваш аудиофайл:")
        else:
            url = "https://file.io"
            with open(mp3, "rb") as file:
                files = {"file": file}
                response = requests.post(url, files=files)
                if response.status_code == 200:
                    file_url = response.json()["link"]
                    await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
                    await message.reply(f"Ваш файл больше 50 МБ. Ссылка на облако: {file_url}")   
        end_time = time.time()
        print(f"Файл {mp3} размером {os.path.getsize(mp3)/1024/1024}Мб отправлен за: {end_time - start_time:.2f} с.")

        os.remove(pdf)
        os.remove(mp3)
        os.remove(wav)

#Обработчик всех остальных сообщений
@dp.message_handler()
async def echo(message: types.Message):
        await message.reply("Обрабатываем ваше сообщение")
        
        start_time = time.time()
        voice = await getUserPreferenceVoice(message.chat.id)
        wav = str(message.chat.id) + str(message.message_id) + ".wav"
        mp3 = str(message.chat.id) + str(message.message_id) + ".mp3"
        await va_speak(message.text, wav, voice[1])
        end_time = time.time()
        print(f"Сообщение от {message.from_user.id} длиной в {len(message.text)} символ(-ов) обработано в звук за: {end_time - start_time:.2f} с.")
        
        sound = AudioSegment.from_wav(wav)
        sound.export(mp3, format="wav")

        start_time = time.time()
        with open(mp3, 'rb') as audio_file:
            await bot.send_chat_action(message.chat.id, ChatActions.UPLOAD_DOCUMENT)
            await message.reply_audio(audio=audio_file, caption="Вот ваш аудиофайл:")

        end_time = time.time()
        print(f"Файл размером {os.path.getsize(mp3)/1024/1024}Мб отправлен {message.from_user.id} за: {end_time - start_time:.2f} с.")

        os.remove(mp3)
        os.remove(wav)


#Действия, выполняемые при запуске программы
async def on_startup(dp):
    logging.basicConfig(level=logging.INFO)
    await start() 
    await dp.bot.set_my_commands(config.commands)

if __name__ == '__main__':
    threads_count = multiprocessing.cpu_count()
    if threads_count>4:
        torch_num_threads = int(threads_count/2)
    elif threads_count>2:
        torch_num_threads = 2
    else: torch_num_threads = 1
    print(f"Используются {torch_num_threads} ядер из {threads_count}")
    nltk.download('punkt')
    print(Fore.YELLOW + 'Выберите режим работы программы: как бот (введите 1) или в локальном режиме (введите 2)')
    choice = input()
    while choice not in ['1','2']:
        print('Введите еще раз')
        choice = input()
    print(Style.RESET_ALL)
    if choice=='1':
        loop = asyncio.get_event_loop()
        loop.create_task(executor.start_polling(dp, skip_updates=True, on_startup=on_startup))
        loop.run_forever()
    if choice=='2':
        loop = asyncio.get_event_loop()
        loop.create_task(local_main())
        loop.run_forever()
