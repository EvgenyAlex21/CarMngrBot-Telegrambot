from core.imports import telebot, os, pytz, datetime
from core.config import BOT_TOKEN

# ------------------------------------------------------ ТОКЕН ДЛЯ БОТА ИЗ BOTFATHER ------------------------------------------------------

bot = telebot.TeleBot(BOT_TOKEN)

# ------------------------------------------------------ ЧАСОВОЙ ПОЯС ------------------------------------------------------

moscow_tz = pytz.timezone('Europe/Moscow')
current_time = datetime.now(moscow_tz)
formatted_time = current_time.strftime('%d.%m.%Y в %H:%M:%S')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))