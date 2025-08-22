from core.imports import wraps, telebot, types, os, json, re
from core.bot_instance import bot
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# -------------------------------------------------- ПРОЧЕЕ (бланки) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Бланки")
@check_function_state_decorator('Бланки')
@track_usage('Бланки')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def blank_forms(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('ДКП', 'Европротокол', 'Доверенность') 
    markup.add('Вернуться в прочее')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите действие из бланков:", reply_markup=markup)

from core.bot_instance import BASE_DIR as PROJECT_BASE_DIR
BLANK_FORMS_DIR = os.path.join(PROJECT_BASE_DIR, 'files', 'files_for_blank_forms')
os.makedirs(BLANK_FORMS_DIR, exist_ok=True)

# -------------------------------------------------- ПРОЧЕЕ (ДКП) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "ДКП")
@check_function_state_decorator('ДКП')
@track_usage('ДКП')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_dkp_form(message):
    file_path = os.path.join(BLANK_FORMS_DIR, 'dkp.pdf')
    
    if os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            bot.send_document(message.chat.id, file, caption="📄 Пустой бланк договора купли-продажи")
    else:
        bot.send_message(message.chat.id, "❌ Бланк ДКП временно не доступен!")

# -------------------------------------------------- ПРОЧЕЕ (Европротокол) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Европротокол")
@check_function_state_decorator('Европротокол')
@track_usage('Европротокол')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_evroprotokol_form(message):
    file_path = os.path.join(BLANK_FORMS_DIR, 'evroprotokol.pdf')
    
    if os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            bot.send_document(message.chat.id, file, caption="📄 Пустой бланк для заполнения европротокола")
    else:
        bot.send_message(message.chat.id, "❌ Бланк Европротокола временно не доступен!")

# -------------------------------------------------- ПРОЧЕЕ (Доверенность) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Доверенность")
@check_function_state_decorator('Доверенность')
@track_usage('Доверенность')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_doverennost_form(message):
    file_path = os.path.join(BLANK_FORMS_DIR, 'doverennosti.pdf')
    
    if os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            bot.send_document(message.chat.id, file, caption="📄 Пустой бланк для заполнения доверенности")
    else:
        bot.send_message(message.chat.id, "❌ Бланк Доверенности временно не доступен!")