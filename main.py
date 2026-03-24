import telebot
import os
import re
from gigachat import GigaChat
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# --- Конфигурация ---
# Получаем токен Telegram-бота из переменной окружения или используем значение по умолчанию
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "ВСТАВИТЬ ТОКЕН")
# Получаем ключ API GigaChat из переменной окружения или используем значение по умолчанию
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY", "ВСТАВИТЬ КЛЮЧ").strip()

# --- Инициализация ---
# Инициализируем клиент GigaChat с учетными данными
# verify_ssl_certs=False отключает проверку SSL-сертификатов
client = GigaChat(credentials=GIGACHAT_API_KEY, verify_ssl_certs=False)
# Инициализируем Telegram-бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Временное хранилище для данных пользователей (в виде словаря)
user_data = {}

# --- Генерация идей ---
def generate_ideas(prompt):
    """
    Отправляет запрос к GigaChat для генерации идей подарка.
    """
    # Отправляем запрос к API GigaChat
    response = client.chat(
        payload={
            "model": "GigaChat-2",  # Явно указываем модель
            "messages": [
                # Задаем роль и поведение для модели
                {"role": "system", "content": "Ты — полезный ассистент, который помогает с идеями подарков. Отвечай обычным текстом, без использования Markdown-разметки."},
                # Передаем промпт от пользователя
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,  # Уровень креативности ответа
            "max_tokens": 300,   # Максимальное количество слов в ответе
        }
    )
    # Возвращаем текстовое содержимое ответа
    return response.choices[0].message.content.strip()

# --- Клавиатуры ---
def main_keyboard():
    """
    Создает и возвращает главную клавиатуру с кнопкой "Подобрать подарок".
    """
    markup = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(KeyboardButton("🎁 Подобрать подарок"))
    return markup

def gender_keyboard():
    """
    Создает и возвращает клавиатуру для выбора пола.
    """
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("Мужской"), KeyboardButton("Женский"))
    return markup

# --- Обработчики команд ---
@bot.message_handler(commands=['start', 'help'])
def start(message):
    """
    Обрабатывает команды /start и /help.
    """
    user_id = message.from_user.id
    user_data[user_id] = {}  # Очищаем данные о пользователе при старте
    bot.send_message(
        message.chat.id,
        "Привет! Я бот-помощник по выбору подарков. Нажми на кнопку ниже, чтобы начать.",
        reply_markup=main_keyboard()
    )

# --- Основной сценарий ---
@bot.message_handler(func=lambda msg: msg.text == "🎁 Подобрать подарок")
def start_process(message):
    """
    Начинает процесс сбора информации для подбора подарка.
    """
    user_id = message.from_user.id
    user_data[user_id] = {}
    msg = bot.send_message(message.chat.id, "Укажите возраст получателя (цифрой):", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_age)

def process_age(message):
    """
    Обрабатывает введенный возраст.
    """
    user_id = message.from_user.id

    # Проверка, что сообщение не пустое
    if not message.text:
        msg = bot.send_message(message.chat.id, "Ошибка: отправьте текстовое сообщение с возрастом.")
        bot.register_next_step_handler(msg, process_age)
        return

    # Ищем число в сообщении
    age_match = re.search(r'\d+', message.text)
    
    # Проверяем, что возраст является корректным числом
    if not age_match or not (0 < int(age_match.group(0)) < 120):
        msg = bot.send_message(message.chat.id, "Ошибка: введите реальный возраст (от 1 до 119).")
        bot.register_next_step_handler(msg, process_age)
        return

    user_data[user_id]['age'] = age_match.group(0)
    msg = bot.send_message(message.chat.id, "Выберите пол:", reply_markup=gender_keyboard())
    bot.register_next_step_handler(msg, process_gender)

def process_gender(message):
    """
    Обрабатывает выбранный пол.
    """
    user_id = message.from_user.id

    if not message.text or message.text.lower() not in ['мужской', 'женский']:
        msg = bot.send_message(message.chat.id, "Ошибка: выберите пол с помощью кнопок.")
        bot.register_next_step_handler(msg, process_gender)
        return

    user_data[user_id]['gender'] = message.text
    msg = bot.send_message(message.chat.id, "Перечислите интересы и увлечения:", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_interests)

def process_interests(message):
    """
    Обрабатывает введенные интересы.
    """
    user_id = message.from_user.id

    if not message.text:
        msg = bot.send_message(message.chat.id, "Ошибка: отправьте текстовое сообщение с интересами.")
        bot.register_next_step_handler(msg, process_interests)
        return

    user_data[user_id]['interests'] = message.text
    msg = bot.send_message(message.chat.id, "Какой повод? (например: 'День рождения', 'Новый год')")
    bot.register_next_step_handler(msg, process_occasion)

def process_occasion(message):
    """
    Обрабатывает повод, формирует промпт и отправляет запрос к GigaChat.
    """
    user_id = message.from_user.id

    if not message.text:
        msg = bot.send_message(message.chat.id, "Ошибка: отправьте текстовое сообщение с поводом.")
        bot.register_next_step_handler(msg, process_occasion)
        return

    user_data[user_id]['occasion'] = message.text
    bot.send_message(message.chat.id, "🤖 Генерирую идеи...")

    try:
        # Формируем итоговый промпт для модели
        prompt = (
            f"Подскажи 5 идей для подарка:\n"
            f"- Возраст: {user_data[user_id]['age']}\n"
            f"- Пол: {user_data[user_id]['gender']}\n"
            f"- Интересы: {user_data[user_id]['interests']}\n"
            f"- Повод: {user_data[user_id]['occasion']}\n\n"
            f"Представь идеи в виде нумерованного списка."
        )

        suggestions = generate_ideas(prompt)
        bot.send_message(message.chat.id, f"Вот несколько идей:\n\n{suggestions}", reply_markup=main_keyboard())
    
    except Exception as e:
        print(f"Ошибка: {e}")
        error_msg = str(e).lower()

        # Обработка распространенных ошибок API
        if "401" in error_msg or "unauthorized" in error_msg:
            bot.send_message(message.chat.id, "❌ Неверный API-ключ GigaChat. Проверьте ключ.", reply_markup=main_keyboard())
        elif "429" in error_msg or "rate" in error_msg:
            bot.send_message(message.chat.id, "⏰ Слишком много запросов. Подождите минуту и попробуйте снова.", reply_markup=main_keyboard())
        else:
            bot.send_message(message.chat.id, "❌ Ошибка при генерации идей. Попробуйте позже.", reply_markup=main_keyboard())
    
    finally:
        # Очищаем данные пользователя после завершения или ошибки
        if user_id in user_data:
            user_data[user_id] = {}

# --- Обработчик по умолчанию ---
@bot.message_handler(func=lambda msg: True)
def default_handler(message):
    """
    Отвечает на любые сообщения, которые не были обработаны ранее.
    """
    bot.send_message(
        message.chat.id,
        "Я не совсем понимаю. Нажмите /start, чтобы начать.",
        reply_markup=main_keyboard()
    )

if __name__ == '__main__':
    print("=" * 50)
    print("🤖 Бот-помощник по выбору подарков")
    print("AI: GigaChat")
    print("=" * 50)
    print("\nБот запущен и ожидает команд...")
    print("=" * 50 + "\n")

    # Запускаем бота в режиме бесконечного опроса
    bot.infinity_polling()
