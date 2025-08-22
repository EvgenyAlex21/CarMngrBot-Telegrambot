from core.imports import wraps, telebot, types, os, json, re
from core.bot_instance import bot
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ----------------------------------------------------- ПРОЧЕЕ ----------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Прочее")
@check_function_state_decorator('Прочее')
@track_usage('Прочее')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_others(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Новости', 'Курсы валют', 'Уведомления') 
    markup.add('Бланки', 'Для рекламы', 'Чат с админом') 
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите действие из прочего:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Вернуться в прочее")
@check_function_state_decorator('Вернуться в прочее')
@track_usage('Вернуться в прочее')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_other(message):
    view_others(message)