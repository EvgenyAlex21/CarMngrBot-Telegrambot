from core.imports import *
from core.bot_instance import bot
from handlers.user.user_main_menu import return_to_menu
from ..utils import (
    restricted, track_user_activity, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage
)

@bot.message_handler(func=lambda message: message.text == "Сайт")
@bot.message_handler(commands=['website'])
@check_function_state_decorator('Сайт')
@track_usage('Сайт')
@restricted
@track_user_activity
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_website_file(message):
    bot.send_message(message.chat.id, "[Сайт CAR MANAGER](carmngrbot.com.swtest.ru)", parse_mode="Markdown")