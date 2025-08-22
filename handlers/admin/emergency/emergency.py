from core.imports import wraps, telebot, types, os, sys, json, re, threading
from core.bot_instance import bot, BASE_DIR
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from handlers.admin.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha,
)

# -------------------------------------------------- ЭКСТРЕННАЯ ОСТАНОВКА ----------------------------------------------

ADMIN_SESSIONS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')

def load_admin_sessions():
    with open(ADMIN_SESSIONS_FILE, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data.get('admin_sessions', [])

def check_admin_access(message):
    admin_sessions = load_admin_sessions()
    if str(message.chat.id) in admin_sessions:
        return True
    else:
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return False

@bot.message_handler(func=lambda message: message.text == 'Экстренная остановка' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_emergency_stop(message):
    emergency_stop(message)

@log_user_actions
def emergency_stop(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Экстренная остановка'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Подтвердить остановку", "Отмена остановки")
    markup.add("В меню админ-панели")
    bot.send_message(message.chat.id, "Вы уверены, что хотите остановить бота?", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_emergency_stop)

def stop_bot_after_delay():
    threading.Timer(5.0, stop_bot).start()

def stop_bot():
    bot.stop_polling()
    os._exit(0) 
    
@log_user_actions
def confirm_emergency_stop(message):
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    if message.text == "Подтвердить остановку":
        bot.send_message(message.chat.id, "🛑 Бот будет остановлен через 5 секунд...")
        stop_bot_after_delay()
        show_admin_panel(message)
    elif message.text == "Отмена остановки":
        bot.send_message(message.chat.id, "✅ Остановка бота отменена!")
        show_admin_panel(message)
    else:
        bot.send_message(message.chat.id, "Неверная команда! Пожалуйста, выберите действие")
        bot.register_next_step_handler(message, confirm_emergency_stop)