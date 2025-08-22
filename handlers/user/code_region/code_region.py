from core.imports import wraps, telebot, types, os, json, re
from core.bot_instance import bot, BASE_DIR
from handlers.user.user_main_menu import return_to_menu
from handlers.user.placesearch.placesearch import shorten_url
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# --------------------------------------------------- КОД РЕГИОНА ---------------------------------------------------------

FILES_DIR = os.path.join(BASE_DIR, "files")
FILES_FOR_REGIONS_DIR = os.path.join(FILES_DIR, "files_for_regions")
REGIONS_FILE_PATH = os.path.join(FILES_FOR_REGIONS_DIR, "regions.txt")

ALLOWED_LETTERS = "АВЕКМНОРСТУХABEKMHOPCTYX"

def is_valid_car_number(car_number):
    pattern = rf"^[{ALLOWED_LETTERS}]\d{{3}}[{ALLOWED_LETTERS}]{{2}}\d{{2,3}}$"
    return bool(re.match(pattern, car_number))

regions = {}
try:
    with open(REGIONS_FILE_PATH, 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split(' — ')
            if len(parts) == 2:
                code, name = parts
                regions[code.strip()] = name.strip()
except FileNotFoundError:
    pass
except Exception as e:
    pass

@bot.message_handler(func=lambda message: message.text == "Код региона")
@check_function_state_decorator('Код региона')
@track_usage('Код региона')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def regioncode(message, show_description=True):
    description = (
        "ℹ️ *Краткая справка по поиску кода региона и госномера авто*\n\n"
        "📌 *Код региона:*\n"
        "Вводится в формате цифр *(2-3 цифры)* - *21* или *121*\n\n"
        "📌 *Госномер:*\n"
        "Вводится в формате РФ *(8-9 символов)* - *A121АА21* или *А121АА121*"
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("В главное меню")
    markup.add(item1)

    if show_description:
        bot.send_message(message.chat.id, description, parse_mode="Markdown")

    bot.send_message(message.chat.id, "Введите коды регионов или госномера автомобилей:", reply_markup=markup)
    bot.register_next_step_handler(message, process_input)

@text_only_handler
def process_input(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    text = message.text.strip()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("В главное меню")
    markup.add(item1)

    inputs = [i.strip() for i in text.split(',')]
    responses = []

    for input_item in inputs:
        if input_item.isdigit() and (2 <= len(input_item) <= 3):
            region_code = input_item
            if region_code in regions:
                region_name = regions[region_code]
                response = f"🔍 *Регион для кода {region_code}:*\n{region_name}\n\n"
            else:
                response = f"❌ Не удалось определить регион для кода: *{region_code}*\n\n"

        elif 8 <= len(input_item) <= 9 and is_valid_car_number(input_item.upper()):
            car_number = input_item.upper()
            region_code = car_number[-3:] if len(car_number) == 9 else car_number[-2:]

            if region_code in regions:
                region_name = regions[region_code]
                avtocod_url = f"https://avtocod.ru/proverkaavto/{car_number}?rd=GRZ"
                short_url = shorten_url(avtocod_url)

                response = (
                    f"🔍 Регион для номера `{car_number}`: {region_name}\n"
                    f"🔗 [Ссылка на AvtoCod с поиском]({short_url})\n\n"
                )
            else:
                response = f"❌ Не удалось определить регион для номера: `{car_number}`\n\n"

        else:
            response = f"❌ Неверный формат для `{input_item}`!\nПожалуйста, введите правильный госномер или код региона\n\n"

        responses.append(response)

    final_response = "".join(responses)
    bot.send_message(message.chat.id, final_response, reply_markup=markup, parse_mode="Markdown")
    bot.send_message(message.chat.id, "Введите другие коды регионов или госномера автомобилей через запятую:")
    bot.register_next_step_handler(message, process_input)