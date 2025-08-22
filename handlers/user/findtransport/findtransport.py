from core.imports import wraps, telebot, types, os, json, re
from core.bot_instance import bot, BASE_DIR
from handlers.user.user_main_menu import return_to_menu
from handlers.user.placesearch.placesearch import shorten_url
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ----------------------------------------------- НАЙТИ ТРАНСПОРТ ---------------------------------------------------

LATITUDE_KEY = 'latitude'
LONGITUDE_KEY = 'longitude'

FIND_TRANSPORT_DIR = os.path.join(BASE_DIR, "data", "user", "findtransport")

def ensure_directories():
    os.makedirs(FIND_TRANSPORT_DIR, exist_ok=True)

ensure_directories()

def save_location_data(location_data):
    ensure_directories() 

    file_path = os.path.join(FIND_TRANSPORT_DIR, "location_data.json")
    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(location_data, json_file, indent=4, ensure_ascii=False)

def load_location_data():
    ensure_directories()  

    file_path = os.path.join(FIND_TRANSPORT_DIR, "location_data.json")
    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, ValueError):
        return {}

location_data = load_location_data()

@bot.message_handler(func=lambda message: message.text == "Найти транспорт")
@check_function_state_decorator('Найти транспорт')
@track_usage('Найти транспорт')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def start_transport_search(message, show_description=True):
    global location_data
    user_id = str(message.from_user.id)

    if user_id in location_data and location_data[user_id].get('start_location') is not None and location_data[user_id].get('end_location') is None:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Продолжить")
        item2 = types.KeyboardButton("Начать заново")
        item3 = types.KeyboardButton("В главное меню")
        markup.add(item1, item2)
        markup.add(item3)
        bot.send_message(message.chat.id, "Хотите продолжить с того места, где остановились?", reply_markup=markup)
        bot.register_next_step_handler(message, continue_or_restart)
    else:
        start_new_transport_search(message, show_description=show_description)

@text_only_handler
def start_new_transport_search(message, show_description=True):
    global location_data
    user_id = str(message.from_user.id)
    location_data[user_id] = {'start_location': None, 'end_location': None}
    save_location_data(location_data)
    request_transport_location(message, show_description=show_description)

@text_only_handler
def request_transport_location(message, show_description=True):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Отправить геопозицию", request_location=True)
    item2 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)

    help_message = (
        "ℹ️ *Краткая справка по поиску транспорта*\n\n"
        "📌 *Отправка геопозиций:*\n"
        "Отправляется две геопозиции, *транспорта* и *ваша*\n\n"
        "📌 *Поиск:*\n"
        "Вывод *ссылки с маршрутом* от точки А до B"
    )

    if show_description:
        bot.send_message(message.chat.id, help_message, parse_mode="Markdown")

    bot.send_message(message.chat.id, "Отправьте геопозицию транспорта:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_car_location)

@text_only_handler
def continue_or_restart(message):
    if message.text == "Продолжить":
        request_user_location(message)
    elif message.text == "Начать заново":
        start_new_transport_search(message)
    else:
        return_to_menu(message)

@text_only_handler
def request_user_location(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Отправить геопозицию", request_location=True)
    item2 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)

    bot.send_message(message.chat.id, "Теперь отправьте свою геопозицию:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_car_location)

def _is_findtransport_active(m):
    try:
        uid = str(m.from_user.id)
        st = location_data.get(uid)
        return bool(st) and (st.get('start_location') is None or st.get('end_location') is None)
    except Exception:
        return False

@bot.message_handler(content_types=['location'], func=_is_findtransport_active)
@check_function_state_decorator('Функция для обработки локации')
@track_usage('Функция для обработки локации')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@check_subscription_chanal
@rate_limit_with_captcha
def handle_car_location(message):
    global location_data
    user_id = str(message.from_user.id)

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if user_id not in location_data:
        location_data[user_id] = {'start_location': None, 'end_location': None}

    if location_data[user_id]['start_location'] is None:
        if message.location is not None:
            location_data[user_id]['start_location'] = {
                LATITUDE_KEY: message.location.latitude,
                LONGITUDE_KEY: message.location.longitude
            }

            location_data[user_id]['process'] = 'in_progress'
            save_location_data(location_data)

            request_user_location(message)
        else:
            handle_location_error(message)

    elif location_data[user_id]['end_location'] is None:
        if message.location is not None:
            location_data[user_id]['end_location'] = {
                LATITUDE_KEY: message.location.latitude,
                LONGITUDE_KEY: message.location.longitude
            }

            location_data[user_id]['process'] = 'completed'
            save_location_data(location_data)

            send_map_link(message.chat.id, location_data[user_id]['start_location'], location_data[user_id]['end_location'])
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton("Найти транспорт")
            item2 = types.KeyboardButton("В главное меню")
            markup.add(item1)
            markup.add(item2)
            bot.send_message(message.chat.id, "✅ Отлично, транспорт найден!\nВы можете повторить поиск:", reply_markup=markup)
        else:
            handle_location_error(message)

@text_only_handler
def handle_location_error(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    bot.send_message(message.chat.id, "Извините, не удалось получить геопозицию!\nПопробуйте еще раз")
    bot.register_next_step_handler(message, handle_car_location)

def send_map_link(chat_id, start_location, end_location):
    map_url = f"https://yandex.ru/maps/?rtext={end_location['latitude']},{end_location['longitude']}~{start_location['latitude']},{start_location['longitude']}&rtt=pd"
    short_url = shorten_url(map_url)
    bot.send_message(chat_id, f"📍 *Маршрут для поиска:* [ссылка]({short_url})", parse_mode="Markdown")