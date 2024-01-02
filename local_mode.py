import PyPDF2, os, time, pathlib
from datetime import datetime
from pydub import AudioSegment
from pydub.effects import normalize, low_pass_filter, high_pass_filter
from colorama import Fore, Back, Style
from tts import *
from config import *

voices = {
    1: 'baya',
    2: 'aidar',
    3: 'kseniya',
    4: 'xenia'
}

async def local_main():
    while True:
        print("\nВведите нужный полный путь к нужному вам файлу")
        print("Пример: C:\\Users\\User\\Downloads\\text.pdf")
        f = input()
        print("Введите номер голоса (baya - 1, aidar - 2, kseniya - 3, xenia - 4)")
        v = int(input())
        if(os.path.exists(f) and pathlib.Path(f).suffix in ['.txt','.pdf'] and v in range(1,5)):
            name = str(datetime.now().timestamp())
            if not os.path.exists('output'):
                os.mkdir('output')
            wav = "output\\" + name + ".wav"
            mp3 = "output\\" + name + ".mp3"
            voice = voices[v]
            if pathlib.Path(f).suffix == '.txt':
                start_time = time.time()
                with open(f, 'r', encoding='utf-8') as file:
                    txt_content_str = file.read()
                await va_speak(txt_content_str, wav, voice)
                end_time = time.time()
                print(Fore.YELLOW + f"Файл {f} длиной в {len(txt_content_str)} символ(-ов) (сохранен в {mp3}) обработан в звук за: {end_time - start_time:.2f} с.")
                sound = AudioSegment.from_wav(wav)
                sound.export(mp3, format="wav")
            else:
                start_time = time.time()
                text = ""
                with open(f, "rb") as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    num_pages = len(pdf_reader.pages)
                    for page_num in range(num_pages):
                        page = pdf_reader.pages[page_num]
                        text += page.extract_text()
                await va_speak(text, wav, voice)
                end_time = time.time()
                print(Fore.YELLOW + f"Файл {f} длиной в {len(text)} символ(-ов) (сохранен в {mp3}) обработан в звук за: {end_time - start_time:.2f} с.")
                sound = AudioSegment.from_wav(wav)
                sound.export(mp3, format="wav")
            os.remove(wav)
            print(Style.RESET_ALL)
        else:
            print("Ошибка в одном из введенных значений. Попробуйте снова")
