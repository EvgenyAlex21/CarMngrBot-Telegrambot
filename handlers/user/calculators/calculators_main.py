from core.imports import wraps, telebot, types, os, json, re
from core.bot_instance import bot
from handlers.user.user_main_menu import return_to_menu
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# --------------------------------------------------------- КАЛЬКУЛЯТОРЫ -------------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Калькуляторы")
@check_function_state_decorator('Калькуляторы')
@track_usage('Калькуляторы')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_calculators(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Расход топлива') 
    markup.add('Алкоголь', 'Автокредит', 'Налог') 
    markup.add('Растаможка', 'ОСАГО', 'Шины') 
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите калькулятор для рассчетов:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Вернуться в калькуляторы")
@check_function_state_decorator('Вернуться в калькуляторы')
@track_usage('Вернуться в калькуляторы')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_calculators(message):
    view_calculators(message)