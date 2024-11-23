import os
from dotenv import load_dotenv
import telebot
from telebot import types
import random
import datetime


class BotConfig:
    """Клас для зберігання конфігурацій бота."""
    ENV_PATH = 'C:/Users/User/Documents/Lwallet_store_bot/bot_token.env'
    USER_IDS_FILE_PATH = 'C:/Users/User/Documents/Lwallet_store_bot/user_ids.txt'
    CHAT_LOG_FILE_PATH = 'C:/Users/User/Documents/Lwallet_store_bot/chat_log.txt'
    ADMIN_ID = 501887724


class UserManager:
    """Клас для роботи з користувачами."""
    @staticmethod
    def load_user_ids():
        """Завантаження ID користувачів із файлу."""
        try:
            with open(BotConfig.USER_IDS_FILE_PATH, "r", encoding="utf-8") as file:
                return {line.strip().split(': ')[1] for line in file if line.startswith("User ID")}
        except FileNotFoundError:
            return set()

    @staticmethod
    def save_user_data(user_id, username=None, first_name=None, last_name=None, phone_number=None):
        """Збереження даних користувача у файл."""
        user_ids = UserManager.load_user_ids()
        if user_id not in user_ids:
            with open(BotConfig.USER_IDS_FILE_PATH, "a", encoding="utf-8") as file:
                file.write(f"User ID: {user_id}\n")
                if username:
                    file.write(f"Nickname: @{username}\n")
                if first_name:
                    file.write(f"First Name: {first_name}\n")
                if last_name:
                    file.write(f"Last Name: {last_name}\n")
                if phone_number:
                    file.write(f"Phone Number: {phone_number}\n")
                file.write("\n")  # Порожній рядок між користувачами


class ChatLogger:
    """Клас для логування повідомлень."""
    @staticmethod
    def log_message(user_id, username, message_text):
        with open(BotConfig.CHAT_LOG_FILE_PATH, 'a', encoding='utf-8') as file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"[{timestamp}] User ID: {user_id}, Username: @{username}, Message: {message_text}\n")


class Bot:
    """Основний клас бота."""
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)

    def is_admin(self, user_id):
        """Перевірка, чи є користувач адміністратором."""
        return user_id == BotConfig.ADMIN_ID

    def start(self):
        """Запуск опитування бота."""
        self.bot.infinity_polling()

    def setup_handlers(self):
        """Налаштування всіх обробників команд."""
        bot = self.bot

        @bot.message_handler(commands=['start'])
        def send_welcome(message):
            user_id = message.chat.id
            username = message.chat.username
            first_name = message.chat.first_name
            last_name = message.chat.last_name
            phone_number = message.contact.phone_number if message.contact else None

            UserManager.save_user_data(user_id, username, first_name, last_name, phone_number)
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton("Всі команди"))
            bot.send_message(user_id, "Добридень, друже!", reply_markup=markup)
            
            ChatLogger.log_message(user_id, username, "Добридень, друже!")

        @bot.message_handler(commands=['help'])
        def send_help(message):
            help_text = (
                "Список доступних команд:\n"
                "/start - Початок роботи\n"
                "/random - Згенерувати випадкове число\n"
                "/help - Показати увесь список команд"
            )
            if self.is_admin(message.chat.id):
                help_text += "\n/broadcast - Надіслати повідомлення всім користувачам"
            bot.reply_to(message, help_text)
            ChatLogger.log_message(message.chat.id, message.chat.username, help_text)

        @bot.message_handler(commands=['random'])
        def send_random_number(message):
            random_number = random.randint(1, 10000)
            response = f"Ваше випадкове число: {random_number}"
            bot.reply_to(message, response)
            ChatLogger.log_message(message.chat.id, message.chat.username, response)

        @bot.message_handler(func=lambda message: message.text == "Всі команди")
        def show_all_commands(message):
            commands = (
                "/start - Початок роботи\n"
                "/random - Згенерувати випадкове число\n"
                "/help - Показати увесь список команд"
            )
            if self.is_admin(message.chat.id):
                commands += "\n/broadcast - Надіслати повідомлення всім користувачам"
            bot.reply_to(message, commands)
            ChatLogger.log_message(message.chat.id, message.chat.username, commands)

        @bot.message_handler(commands=['broadcast'])
        def broadcast_command(message):
            if self.is_admin(message.chat.id):
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Розпочати розсилку", callback_data="start_broadcast"))
                bot.send_message(message.chat.id, "Натисніть кнопку нижче, щоб розпочати розсилку", reply_markup=markup)
            else:
                bot.reply_to(message, "Ця команда доступна лише адміністраторам")

        @bot.callback_query_handler(func=lambda call: call.data == "start_broadcast")
        def handle_broadcast_button(call):
            if self.is_admin(call.message.chat.id):
                bot.delete_message(call.message.chat.id, call.message.message_id)
                bot.send_message(call.message.chat.id, "Будь ласка, введіть повідомлення для розсилки")
                bot.register_next_step_handler(call.message, self.send_broadcast_message)
            else:
                bot.answer_callback_query(call.id, "Ця функція доступна лише адміністраторам")

        @bot.message_handler(func=lambda message: True)
        def handle_message(message):
            ChatLogger.log_message(message.chat.id, message.chat.username, message.text)

    def send_broadcast_message(self, message):
        """Розсилка повідомлень усім користувачам."""
        if self.is_admin(message.chat.id):
            broadcast_text = message.text
            user_ids = UserManager.load_user_ids()
            for user_id in user_ids:
                try:
                    self.bot.send_message(user_id, broadcast_text)
                except telebot.apihelper.ApiException as e:
                    print(f"Не вдалося надіслати повідомлення користувачу {user_id}: {e}")
            self.bot.reply_to(message, "Повідомлення надіслано всім користувачам")
        else:
            self.bot.reply_to(message, "Ви не маєте права використовувати цю функцію")


# Завантаження конфігурації
load_dotenv(BotConfig.ENV_PATH)
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Токен не знайдено!")

# Запуск бота
bot_instance = Bot(TOKEN)
bot_instance.setup_handlers()
bot_instance.start()
