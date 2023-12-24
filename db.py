import sqlite3

# Подключаемся к базе данных SQLite
conn = sqlite3.connect('user_preferences.db')
cursor = conn.cursor()

def start():
    # Создаем таблицу, если её нет
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER PRIMARY KEY,
            speaker TEXT
        )
    ''')
    conn.commit()

#Смена предпочитаемого голоса
def changeUserPreferenceVoice(user_id, voice):
    cursor.execute('''
        UPDATE user_preferences
        SET speaker = ?
        WHERE user_id = ?
    ''', (voice, user_id))
    conn.commit()

#Получение предпочитаемого голоса
def getUserPreferenceVoice(user_id):
    cursor.execute('SELECT * FROM user_preferences WHERE user_id = ?', (user_id,))
    user_record = cursor.fetchone()
    
    if not user_record:
        # Если пользователя нет в базе, добавляем его
        cursor.execute('INSERT INTO user_preferences (user_id, speaker) VALUES (?, ?)', (user_id, 'baya'))
        conn.commit()
        cursor.execute('SELECT * FROM user_preferences WHERE user_id = ?', (user_id,))
        user_record = cursor.fetchone()

    return user_record