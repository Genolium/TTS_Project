import torch, torchaudio, os, re, wave, timeit
from pydub import AudioSegment
from nltk.tokenize import sent_tokenize
from transliterate import translit
from datetime import datetime, timedelta
from num2words import num2words
from omegaconf import OmegaConf
from config import torch_num_threads

language = 'ru'
model_id = 'ru_v3'
sample_rate = 48000 # 48000
put_accent = True
put_yo = True
device = torch.device('cpu') # cpu или cuda

line_length_limits: dict = {
    'aidar': 870,
    'baya': 860,
    'eugene': 1000,
    'kseniya': 870,
    'xenia': 957,
    'random': 355,
}
wave_file_size_limit: int = 512 * 1024 * 1024 

wave_channels: int = 1  # Mono
wave_header_size: int = 44  # Bytes
wave_sample_width: int = int(16 / 8)  # 16 bits == 2 bytes


def init_model(device: str, threads_count: int) -> torch.nn.Module:
    print("Initialising model")
    t0 = timeit.default_timer()

    # https://github.com/snakers4/silero-models/issues/183
    torch._C._jit_set_profiling_mode(False) # Fixes initial delay

    if not torch.cuda.is_available() and device == "auto":
        device = 'cpu'
    if torch.cuda.is_available() and device == "auto" or device == "cuda":
        # torch.backends.cudnn.deterministic = True
        torch_dev: torch.device = torch.device("cuda", 0)
        gpus_count = torch.cuda.device_count()  # 1
        print("Using {} GPU(s)...".format(gpus_count))
    else:
        torch_dev: torch.device = torch.device(device)
    torch.set_num_threads(threads_count)
    tts_model, tts_sample_text = torch.hub.load(repo_or_dir='snakers4/silero-models',
                                                model='silero_tts',
                                                language=language,
                                                speaker=model_id)
    print("Setup takes {:.2f}".format(timeit.default_timer() - t0))

    print("Загружаем модель")
    t1 = timeit.default_timer()
    tts_model.to(torch_dev)  # gpu or cpu
    print("Model to device takes {:.2f}".format(timeit.default_timer() - t1))

    if torch.cuda.is_available() and device == "auto" or device == "cuda":
        print("Synchronizing CUDA")
        t2 = timeit.default_timer()
        torch.cuda.synchronize()
        print("Cuda Synch takes {:.2f}".format(timeit.default_timer() - t2))
    print("Модель загружена")
    return tts_model

torch.hub.download_url_to_file('https://raw.githubusercontent.com/snakers4/silero-models/master/models.yml',
                                   'latest_silero_models.yml',
                                   progress=False)
tts_model: torch.nn.Module = init_model(device, torch_num_threads)
#model, _ = torch.hub.load(repo_or_dir='snakers4/silero-models',
#                         model='silero_tts',
#                          language=language,
#                          speaker=model_id)
#model.to(device)

# Функция для разбиения текста на чанки
async def chunk_text(text, max_chars=500):
    chunks = []
    current_chunk = ""
    
    sentences = sent_tokenize(text)
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_chars:
            current_chunk += sentence + " .  "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + " .  "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


async def find_char_positions(string: str, char: str) -> list:
    pos: list = []  # list to store positions for each 'char' in 'string'
    for n in range(len(string)):
        if string[n] == char:
            pos.append(n)
    return pos


async def find_max_char_position(positions: list, limit: int) -> int:
    max_position: int = 0
    for pos in positions:
        if pos < limit:
            max_position = pos
        else:
            break
    return max_position


async def find_split_position(line: str, old_position: int, char: str, limit: int) -> int:
    positions: list = await find_char_positions(line, char)
    new_position: int = await find_max_char_position(positions, limit)
    position: int = max(new_position, old_position)
    return position


async def spell_digits(line) -> str:
    digits: list = re.findall(r'\d+', line)
    # Sort digits from largest to smallest - else "1 11" will be "один один один" but not "один одиннадцать"
    digits = sorted(digits, key=len, reverse=True)
    for digit in digits:
        line = line.replace(digit, num2words(int(digit[:12]), lang='ru'))
    return line


async def preprocess_text(lines: list, length_limit: int) -> (list, int):
    print(f"Preprocessing text with line length limit={length_limit}")

    if length_limit > 3:
        length_limit = length_limit - 2  # Keep a room for trailing char and '\n' char
    else:
        print(F"ERROR: line length limit must be >= 3, got {length_limit}")
        exit(1)

    preprocessed_text_len: int = 0
    preprocessed_lines: list = []
    for line in lines:
        line = line.strip()  # Remove leading/trailing spaces
        if line == '\n' or line == '':
            line = "..."

        # Replace chars not supported by model
        line = line.replace("…", "...")  # Model does not handle "…"
        line = line.replace("*", " звёздочка ")
        line = re.sub(r'(\d+)[\.|,](\d+)', r'\1 и \2', line) # to make more clear stuff like 2.75%
        line = line.replace("%", " процентов ")
        line = line.replace(" г.", " году")
        line = line.replace(" гг.", " годах")
        line = re.sub("д.\s*н.\s*э.", " до нашей эры", line)
        line = re.sub("н.\s*э.", " нашей эры", line)
        line = await spell_digits(line)

        # print("Processing line: " + line)
        while len(line) > 0:
            # v3_1_ru model does not handle long lines (over 990 chars)
            if len(line) < length_limit:
                # print("adding line: " + line)
                line = line + "\n"
                preprocessed_lines.append(line)
                preprocessed_text_len += len(line)
                break
            # Find position to split line between sentences
            split_position: int = 0
            split_position = await find_split_position(line, split_position, ".", length_limit)
            split_position = await find_split_position(line, split_position, "!", length_limit)
            split_position = await find_split_position(line, split_position, "?", length_limit)

            # If no punctuation found - try to split on space
            if split_position == 0:
                split_position = await find_split_position(line, split_position, " ", length_limit)

            # If no punctuation found - force split at limit
            if split_position == 0:
                split_position = length_limit

            # Keep trailing char, add newline
            part: str = line[0:split_position + 1] + "\n"
            # print(F'Line too long - splitting at position {split_position}:  {line}')
            preprocessed_lines.append(part)
            preprocessed_text_len += len(part)
            # Skip trailing char from previous part
            line = line[split_position + 1:]
            # print ("Rest of line: " + line)
    return preprocessed_lines, preprocessed_text_len

async def init_wave_file(name: str, channels: int, sample_width: int, rate: int):
    print(f'Initialising wave file {name} with {channels} channels {sample_width} sample width {rate} sample rate')
    wf = wave.open(name, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(sample_width)
    wf.setframerate(rate)
    return wf

async def write_wave_chunk(wf, audio, audio_size: int, filename: str, wave_data_limit: int, wave_file_number: int):
    next_chunk_size = int(audio.size()[0] * wave_sample_width)
    if audio_size + next_chunk_size > wave_data_limit:
        print(F"Wave written {audio_size} limit={wave_data_limit} - creating new wave!")
        wf.close()
        wave_file_number += 1
        audio_size = wave_header_size + next_chunk_size
        wf = await init_wave_file(F'{filename}_{wave_file_number}.wav',
                            wave_channels, wave_sample_width, sample_rate)
    else:
        audio_size += next_chunk_size
        wf.writeframes((audio * 32767).numpy().astype('int16'))
    return wf, audio_size, wave_file_number

#Обработка текста и перевод его в файл
async def va_speak(what: str, file: str, voice: str):
    what = translit(what, 'ru')
    current_line: int = 0
    audio_size: int = wave_header_size
    wave_file_number: int = 0
    next_chunk_size: int

    line_length_limit: int = line_length_limits[voice]  # Max text length for speaker
    origin_lines = await chunk_text(what, line_length_limit)
    preprocessed_lines, preprocessed_text_len = await preprocess_text(origin_lines, line_length_limit)    
    
    wf = await init_wave_file(file, wave_channels, wave_sample_width, sample_rate)
    for line in preprocessed_lines:
        try:
            audio = tts_model.apply_tts(line,
                                        speaker=voice,
                                        sample_rate=sample_rate,
                                        put_accent=put_accent,
                                        put_yo=put_yo)
            next_chunk_size = int(audio.size()[0] * wave_sample_width)
            wf, audio_size, wave_file_number = await write_wave_chunk(wf, audio, audio_size, file,
                                                                wave_file_size_limit, wave_file_number)
        except ValueError:
            print("Произошла ошибка в обработке голоса, продолжаем обработку файла")

        current_line += 1