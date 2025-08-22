from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, timedelta
from core.bot_instance import bot
from handlers.admin.statistics.statistics import check_admin_access, escape_markdown, check_permission
from handlers.admin.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

# -------------------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Управление системой' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def manage_system(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Управление системой'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Управление подписками', 'Управление магазином')
    markup.add('Управление баллами', 'Управление обменами')
    markup.add('Управление скидками', 'Управление подарками')
    markup.add('Статистика системы')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите действие для управления системой:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Вернуться в управление системой' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_subs(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Вернуться в управление системой'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return
    manage_system(message)