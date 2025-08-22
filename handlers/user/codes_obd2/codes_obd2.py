from core.imports import wraps, telebot, types, os, json, re
from core.bot_instance import bot, BASE_DIR
from handlers.user.user_main_menu import return_to_menu
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# --------------------------------------------------- КОДЫ OBD2 ---------------------------------------------------------

FILES_FOR_OBD2_DIR = os.path.join(BASE_DIR, "files", "files_for_obd2")

def load_error_codes():
    error_codes = {}
    try:
        with open(os.path.join(FILES_FOR_OBD2_DIR, "codes_obd2.txt"), "r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(" ", 1)
                if len(parts) == 2:
                    code, description = parts
                    error_codes[code] = description
    except FileNotFoundError:
        pass
    return error_codes

error_codes = load_error_codes()

@bot.message_handler(func=lambda message: message.text == "Коды OBD2")
@check_function_state_decorator('Коды OBD2')
@track_usage('Коды OBD2')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def obd2_request(message, show_description=True):

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("В главное меню"))

    help_text = (
        "ℹ️ *Краткая справка по чтению кодов OBD2*\n\n"
        "📌 *Первая позиция:*\n"
        "*P* - код связан с работой двигателя и/или АКПП\n"
        "*B* - код связан с работой \"кузовных систем\" (подушки безопасности, центральный замок, электростеклоподъемники)\n"
        "*C* - код относится к системе шасси (ходовой части)\n"
        "*U* - код относится к системе взаимодействия между электронными блоками (например, к шине CAN)\n\n"
        "📌 *Вторая позиция:*\n"
        "*0* - общий для OBD2 код\n"
        "*1 и 2* - код производителя\n"
        "*3* - резерв\n\n"
        "📌 *Третья позиция* - тип неисправности:\n"
        "*1* - топливная система или воздухоподача\n"
        "*2* - топливная система или воздухоподача\n"
        "*3* - система зажигания\n"
        "*4* - вспомогательный контроль\n"
        "*5* - холостой ход\n"
        "*6* - ECU или его цепи\n"
        "*7* - трансмиссия\n"
        "*8* - трансмиссия\n\n"
        "📌 *Четвертая и пятая позиции* - порядковый *номер* ошибки\n\n"
    )

    if show_description:
        bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

    msg = bot.send_message(message.chat.id, "Введите коды ошибок OBD2:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_error_codes)

@text_only_handler
def process_error_codes(message):

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    codes = [code.strip().upper() for code in message.text.split(",")]
    response = ""

    code_pattern = re.compile(r'^[PBCU][0-3]\d{3}$')

    valid_codes = []
    invalid_codes = []

    for code in codes:
        if code_pattern.match(code):
            valid_codes.append(code)
        else:
            invalid_codes.append(code)

    for code in valid_codes:
        if code in error_codes:
            response += f"🔧 *Код ошибки*: `{code}`\n📋 *Описание*: {error_codes[code]}\n\n"
        else:
            response += f"🔧 *Код ошибки*: `{code}`\n❌ *Описание*: Не найдено\n\n"

    for code in invalid_codes:
        response += f"🔧 *Код ошибки*: `{code}`\n❌ *Описание*: Не найдено\n\n"

    bot.send_message(message.chat.id, response, parse_mode="Markdown")

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("В главное меню"))

    msg = bot.send_message(message.chat.id, "Введите другие коды ошибок OBD2 через запятую:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_error_codes)