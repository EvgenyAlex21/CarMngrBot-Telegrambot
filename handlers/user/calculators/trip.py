from core.imports import wraps, telebot, types, os, json, re, requests, datetime, timedelta, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, pd, Workbook, load_workbook, Alignment, Border, Side, Font, PatternFill, openpyxl, Nominatim, GeocoderUnavailable, geodesic, BeautifulSoup
from core.bot_instance import bot, BASE_DIR
from handlers.user.user_main_menu import return_to_menu
from handlers.user.calculators.calculators_main import return_to_calculators
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ---------------------------------------------------- КАЛЬКУЛЯТОРЫ_РАСХОД ТОПЛИВА -------------------------------------------------------

TRIP_DIR = os.path.join(BASE_DIR, 'data', 'user', 'calculators', 'trip')
geolocator = Nominatim(user_agent="fuel_expense_bot")

def ensure_trip_directory():
    os.makedirs(TRIP_DIR, exist_ok=True)

ensure_trip_directory()

user_trip_data = {}

def save_data(user_id):
    if user_id in user_trip_data:
        file_path = os.path.join(TRIP_DIR, f"{user_id}_trip_data.json")
        with open(file_path, "w", encoding='utf-8') as json_file:
            json.dump({
                "user_id": str(user_id),
                "trips": user_trip_data[user_id]
            }, json_file, ensure_ascii=False, indent=4)

def add_trip(user_id, trip):
    if user_id not in user_trip_data:
        user_trip_data[user_id] = []
    user_trip_data[user_id].append(trip)

def save_trip_data(user_id):
    file_path = os.path.join(TRIP_DIR, f"{user_id}_trip_data.json")
    with open(file_path, "w", encoding='utf-8') as json_file:
        json.dump({
            "user_id": str(user_id),
            "trips": user_trip_data.get(user_id, [])
        }, json_file, ensure_ascii=False, indent=4)

def load_trip_data(user_id):
    file_path = os.path.join(TRIP_DIR, f"{user_id}_trip_data.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding='utf-8') as json_file:
                data = json.load(json_file)
                if isinstance(data, dict) and "trips" in data:
                    return data["trips"]
                else:
                    with open(file_path, "w", encoding='utf-8') as json_file:
                        json.dump({
                            "user_id": str(user_id),
                            "trips": data
                        }, json_file, ensure_ascii=False, indent=4)
                    return data
        except UnicodeDecodeError:
            with open(file_path, "r", encoding='windows-1251') as json_file:
                data = json.load(json_file)
            with open(file_path, "w", encoding='utf-8') as json_file:
                if isinstance(data, dict) and "trips" in data:
                    json.dump(data, json_file, ensure_ascii=False, indent=4)
                    return data["trips"]
                else:
                    json.dump({
                        "user_id": str(user_id),
                        "trips": data
                    }, json_file, ensure_ascii=False, indent=4)
                    return data
    else:
        return []

def load_all_user_data():
    for filename in os.listdir(TRIP_DIR):
        if filename.endswith("_trip_data.json"):
            user_id = filename.split("_")[0]
            user_trip_data[user_id] = load_trip_data(user_id)

def save_all_trip_data():
    for user_id in user_trip_data:
        save_trip_data(user_id)

load_all_user_data()

user_trip_data = {}
trip_data = {}
temporary_trip_data = {}
fuel_types = ["АИ-92", "АИ-95", "АИ-98", "АИ-100", "ДТ", "ГАЗ"]
date_pattern = r"^\d{2}.\d{2}.\d{4}$"

@bot.message_handler(func=lambda message: message.text == "Расход топлива")
@check_function_state_decorator('Расход топлива')
@track_usage('Расход топлива')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_fuel_expense(message, show_description=True):
    description = (
        "ℹ️ *Краткая справка по расчету топлива*\n\n"
        "📌 *Расчет топлива:*\n"
        "Расчет ведется по следующим данным - *несколько точек маршрута, дата, расстояние, тип топлива, цена за литр, расход топлива, количество пассажиров*\n\n"
        "📌 *Просмотр поездок:*\n"
        "Вы можете посмотреть свои расчеты\n\n"
        "📌 *Удаление поездок:*\n"
        "Вы можете удалить свои расчеты, если они вам не нужны"
    )

    user_id = message.from_user.id

    if user_id not in user_trip_data:
        user_trip_data[user_id] = load_trip_data(user_id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Рассчитать расход")
    item2 = types.KeyboardButton("Посмотреть поездки")
    item3 = types.KeyboardButton("Удалить поездки")
    item4 = types.KeyboardButton("Вернуться в калькуляторы")
    item5 = types.KeyboardButton("В главное меню")

    markup.add(item1, item2, item3)
    markup.add(item4)
    markup.add(item5)

    bot.clear_step_handler_by_chat_id(user_id)

    if show_description:
        bot.send_message(user_id, description, parse_mode="Markdown")

    bot.send_message(user_id, "Выберите действия из расхода топлива:", reply_markup=markup)

def reset_and_start_over(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Рассчитать расход")
    item2 = types.KeyboardButton("Посмотреть поездки")
    item3 = types.KeyboardButton("Удалить поездки")
    item4 = types.KeyboardButton("Вернуться в калькуляторы")
    item5 = types.KeyboardButton("В главное меню")

    markup.add(item1, item2, item3)
    markup.add(item4)
    markup.add(item5)

    bot.send_message(chat_id, "Выберите действия из расхода топлива:", reply_markup=markup)

save_all_trip_data()

def reset_user_data(user_id):
    if user_id not in user_trip_data:
        user_trip_data[user_id] = load_trip_data(user_id)
    bot.clear_step_handler_by_chat_id(user_id)

# --------------------------------------------- КАЛЬКУЛЯТОРЫ_РАСХОД ТОПЛИВА (рассчитать расход) ---------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Рассчитать расход")
@check_function_state_decorator('Рассчитать расход')
@track_usage('Рассчитать расход')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def calculate_fuel_cost_handler(message):
    chat_id = message.chat.id

    bot.clear_step_handler_by_chat_id(chat_id)

    trip_data[chat_id] = {"locations": []}

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Отправить геолокацию", request_location=True)
    item2 = types.KeyboardButton("Вернуться в расход топлива")
    item3 = types.KeyboardButton("Вернуться в калькуляторы")
    item4 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)
    markup.add(item3)
    markup.add(item4)
    sent = bot.send_message(chat_id, "Введите 1 местоположение или отправьте геолокацию:", reply_markup=markup)
    reset_user_data(chat_id)

    bot.register_next_step_handler(sent, process_location_step, location_number=1)

@text_only_handler
def process_location_step(message, location_number):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Отправить геолокацию", request_location=True)
    item2 = types.KeyboardButton("Вернуться в расход топлива")
    item3 = types.KeyboardButton("Вернуться в калькуляторы")
    item4 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)
    markup.add(item3)
    markup.add(item4)

    if message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return		
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    location_data = {}
    if message.location:
        location = message.location
        try:
            address = geolocator.reverse((location.latitude, location.longitude), timeout=10).address
            location_data = {
                "address": address,
                "latitude": location.latitude,
                "longitude": location.longitude
            }
            bot.send_message(chat_id, f"Ваше {location_number} местоположение:\n\n{address}")
        except GeocoderUnavailable:
            bot.send_message(chat_id, "Сервис геолокации временно недоступен!\nПопробуйте позже")
            return
    else:
        address = message.text
        try:
            location = geolocator.geocode(address, timeout=10)
            if location:
                location_data = {
                    "address": address,
                    "latitude": location.latitude,
                    "longitude": location.longitude
                }
                bot.send_message(chat_id, f"Ваше {location_number} местоположение:\n\n{address}")
            else:
                sent = bot.send_message(chat_id, "Не удалось найти местоположение!\nПожалуйста, введите корректный адрес")
                bot.register_next_step_handler(sent, process_location_step, location_number)
                return
        except GeocoderUnavailable:
            bot.send_message(chat_id, "Сервис геолокации временно недоступен!\nПопробуйте позже")
            return

    trip_data[chat_id]["locations"].append(location_data)

    if location_number == 1:
        sent = bot.send_message(chat_id, "Введите 2 местоположение или отправьте геолокацию:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_location_step, location_number=2)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Да")
        item2 = types.KeyboardButton("Нет")
        item3 = types.KeyboardButton("Вернуться в расход топлива")
        item4 = types.KeyboardButton("Вернуться в калькуляторы")
        item5 = types.KeyboardButton("В главное меню")
        markup.add(item1, item2)
        markup.add(item3)
        markup.add(item4)
        markup.add(item5)
        sent = bot.send_message(chat_id, "Хотите добавить еще местоположение для расчета?", reply_markup=markup)
        bot.register_next_step_handler(sent, process_add_more_locations, location_number + 1)

@text_only_handler
def process_add_more_locations(message, next_location_number):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Да")
    item2 = types.KeyboardButton("Нет")
    item3 = types.KeyboardButton("Вернуться в расход топлива")
    item4 = types.KeyboardButton("Вернуться в калькуляторы")
    item5 = types.KeyboardButton("В главное меню")
    markup.add(item1, item2)
    markup.add(item3)
    markup.add(item4)
    markup.add(item5)

    if message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return		
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text == "Да":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Отправить геолокацию", request_location=True)
        item2 = types.KeyboardButton("Вернуться в расход топлива")
        item3 = types.KeyboardButton("Вернуться в калькуляторы")
        item4 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2)
        markup.add(item3)
        markup.add(item4)
        sent = bot.send_message(chat_id, f"Введите {next_location_number} местоположение или отправьте геолокацию:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_location_step, next_location_number)
    elif message.text == "Нет":
        calculate_total_distance(chat_id)
    else:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите да или нет!", reply_markup=markup)
        bot.register_next_step_handler(sent, process_add_more_locations, next_location_number)

def calculate_total_distance(chat_id):
    locations = trip_data[chat_id]["locations"]
    total_distance = 0.0
    for i in range(len(locations) - 1):
        start_coords = (locations[i]["latitude"], locations[i]["longitude"])
        end_coords = (locations[i + 1]["latitude"], locations[i + 1]["longitude"])
        total_distance += geodesic(start_coords, end_coords).kilometers

    trip_data[chat_id]["distance"] = total_distance

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_auto = types.KeyboardButton("Автоматическое")
    item_input = types.KeyboardButton("Ввод вручную")
    item1 = types.KeyboardButton("Вернуться в расход топлива")
    item2 = types.KeyboardButton("Вернуться в калькуляторы")
    item3 = types.KeyboardButton("В главное меню")

    markup.add(item_auto, item_input)
    markup.add(item1)
    markup.add(item2)
    markup.add(item3)

    sent = bot.send_message(chat_id, f"Выберите вариант ввода расстояния:", reply_markup=markup)
    bot.register_next_step_handler(sent, process_distance_choice_step, total_distance)

@text_only_handler
def process_custom_distance_step(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Вернуться в расход топлива")
    item2 = types.KeyboardButton("Вернуться в калькуляторы")
    item3 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)
    markup.add(item3)

    if message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return		
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    try:
        custom_distance = float(message.text.replace(',', '.'))
        if custom_distance <= 0:
            raise ValueError
        bot.send_message(chat_id, f"Вы ввели свое расстояние: {custom_distance:.2f} км.", reply_markup=markup)

        trip_data[chat_id]["distance"] = custom_distance

        markup_date = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_manual = types.KeyboardButton("Ввести дату вручную")
        item_skip = types.KeyboardButton("Пропустить ввод даты")
        markup_date.add(item_manual, item_skip)
        markup_date.add(item1)
        markup_date.add(item2)

        sent = bot.send_message(chat_id, "Выберите способ ввода даты:", reply_markup=markup_date)
        bot.register_next_step_handler(sent, process_date_step, custom_distance)
    except ValueError:
        sent = bot.send_message(chat_id, "Пожалуйста, введите корректное число для расстояния!", reply_markup=markup)
        bot.register_next_step_handler(sent, process_custom_distance_step)

@text_only_handler
def process_distance_choice_step(message, distance_km):
    chat_id = message.chat.id
    trip_data[chat_id]["distance"] = distance_km

    if message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return		
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_auto = types.KeyboardButton("Автоматическое")
    item_input = types.KeyboardButton("Ввод вручную")
    item1 = types.KeyboardButton("Вернуться в расход топлива")
    item2 = types.KeyboardButton("Вернуться в калькуляторы")
    item3 = types.KeyboardButton("В главное меню")

    markup.add(item_auto, item_input)
    markup.add(item1)
    markup.add(item2)
    markup.add(item3)

    if message.text == "Автоматическое":
        bot.send_message(chat_id, f"Расстояние между точками: {distance_km:.2f} км.")
        process_date_step(message, distance_km)
    elif message.text == "Ввод вручную":
        custom_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в расход топлива")
        item2 = types.KeyboardButton("Вернуться в калькуляторы")
        item3 = types.KeyboardButton("В главное меню")
        custom_markup.add(item1)
        custom_markup.add(item2)
        custom_markup.add(item3)

        sent = bot.send_message(chat_id, "Введите ваше расстояние (км.):", reply_markup=custom_markup)
        bot.register_next_step_handler(sent, process_custom_distance_step)
    else:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите один из вариантов!", reply_markup=markup)
        bot.register_next_step_handler(sent, process_distance_choice_step, distance_km)

@text_only_handler
def process_date_step(message, distance):
    chat_id = message.chat.id

    if message.text == "Пропустить ввод даты":
        selected_date = "Без даты"
        process_selected_date(message, selected_date)
        return

    if message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return		
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text == "Ввести дату вручную":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в расход топлива")
        item2 = types.KeyboardButton("Вернуться в калькуляторы")
        item3 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2)
        markup.add(item3)
        sent = bot.send_message(chat_id, "Введите дату поездки в формате ДД.ММ.ГГГГ:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_manual_date_step, distance)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_manual = types.KeyboardButton("Ввести дату вручную")
        item_skip = types.KeyboardButton("Пропустить ввод даты")
        item1 = types.KeyboardButton("Вернуться в расход топлива")
        item2 = types.KeyboardButton("Вернуться в калькуляторы")
        item3 = types.KeyboardButton("В главное меню")
        markup.add(item_manual, item_skip)
        markup.add(item1)
        markup.add(item2)
        markup.add(item3)

        sent = bot.send_message(chat_id, "Выберите способ ввода даты:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_date_step, distance)

@text_only_handler
def process_date_input_step(message, distance):
    chat_id = message.chat.id
    date_input = message.text.strip()

    date_pattern = r"^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.\d{4}$"
    if re.match(date_pattern, date_input):
        selected_date = date_input
        process_selected_date(message, selected_date)
    else:
        bot.send_message(chat_id, "Неверный формат даты!\nПожалуйста, введите дату в формате ДД.ММ.ГГГГ")
        bot.register_next_step_handler(message, process_date_input_step, distance)

@text_only_handler
def handle_date_selection(message, distance):
    chat_id = message.chat.id

    if message.text == "Пропустить ввод даты":
        selected_date = "Без даты"
        process_selected_date(message, selected_date)
        return

    if message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return		
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text == "Ввести дату вручную":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в расход топлива")
        item2 = types.KeyboardButton("Вернуться в калькуляторы")
        item3 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2)
        markup.add(item3)

        sent = bot.send_message(chat_id, "Введите дату поездки в формате ДД.ММ.ГГГГ:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_manual_date_step, distance)
    else:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите корректный вариант!")
        bot.register_next_step_handler(sent, handle_date_selection, distance)

@text_only_handler
def process_selected_date(message, selected_date):
    chat_id = message.chat.id
    distance_km = trip_data[chat_id].get("distance")

    if distance_km is None:
        bot.send_message(chat_id, "Расстояние не было задано!\nПожалуйста, попробуйте снова")
        return

    show_fuel_types(chat_id, selected_date, distance_km)

@text_only_handler
def process_manual_date_step(message, distance):
    chat_id = message.chat.id
    date_pattern = r"\d{2}\.\d{2}\.\d{4}"

    if message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return		
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Вернуться в расход топлива")
    item2 = types.KeyboardButton("Вернуться в калькуляторы")
    item3 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)
    markup.add(item3)

    if re.match(date_pattern, message.text):
        day, month, year = map(int, message.text.split('.'))
        if 2000 <= year <= 3000:
            try:
                datetime(year, month, day)
                bot.send_message(chat_id, f"Вы выбрали дату: {message.text}", reply_markup=markup)
                show_fuel_types(chat_id, message.text, distance)
            except ValueError:
                sent = bot.send_message(chat_id, "Неправильная дата!\nПожалуйста, введите корректную дату", reply_markup=markup)
                bot.register_next_step_handler(sent, process_manual_date_step, distance)
        else:
            sent = bot.send_message(chat_id, "Год должен быть в диапазоне от 2000 г. до 3000 г.", reply_markup=markup)
            bot.register_next_step_handler(sent, process_manual_date_step, distance)
    else:
        sent = bot.send_message(chat_id, "Неправильный формат даты!\nПожалуйста, введите дату в формате ДД.ММ.ГГГГ", reply_markup=markup)
        bot.register_next_step_handler(sent, process_manual_date_step, distance)

def show_fuel_types(chat_id, date, distance):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    row1 = [KeyboardButton(fuel_type) for fuel_type in fuel_types[:3]]
    row2 = [KeyboardButton(fuel_type) for fuel_type in fuel_types[3:]]
    row3 = [KeyboardButton("Вернуться в расход топлива")]
    row4 = [KeyboardButton("Вернуться в калькуляторы")]
    row5 = [KeyboardButton("В главное меню")]

    markup.add(*row1, *row2, *row3)
    markup.add(*row4)
    markup.add(*row5)

    sent = bot.send_message(chat_id, "Выберите тип топлива:", reply_markup=markup)
    bot.register_next_step_handler(sent, process_fuel_type, date, distance)

def clean_price(price):
    cleaned_price = re.sub(r'[^\d.]', '', price)
    if cleaned_price.count('.') > 1:
        cleaned_price = cleaned_price[:cleaned_price.find('.') + 1] + cleaned_price[cleaned_price.find('.') + 1:].replace('.', '')
    return cleaned_price

fuel_type_mapping = {
    "аи-92": "Аи-92",
    "аи-95": "Аи-95",
    "аи-98": "Аи-98",
    "аи-100": "Аи-100",
    "дт": "ДТ",
    "газ": "Газ СПБТ",
}

def get_average_fuel_price_from_files(fuel_type, directory=None):
    if directory is None:
        directory = os.path.join(BASE_DIR, 'data', 'user', 'azs')
    fuel_prices = []

    fuel_type = fuel_type.lower()

    if not os.path.exists(directory):
        os.makedirs(directory)

    file_path = os.path.join(directory, "cheboksary_table_azs_data.json")

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            for entry in data:
                if len(entry) >= 3:  
                    company, fuel, price = entry
                    if fuel.lower() == fuel_type:
                        try:
                            price = float(price)
                            fuel_prices.append(price)
                        except ValueError:
                            continue

    if not fuel_prices:
        fuel_data = get_fuel_prices_from_website()
        if fuel_data:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(fuel_data, file, ensure_ascii=False, indent=4)

            for entry in fuel_data:
                company, fuel, price = entry
                if fuel.lower() == fuel_type:
                    try:
                        price = float(price)
                        fuel_prices.append(price)
                    except ValueError:
                        continue

    if fuel_prices:
        average_price = sum(fuel_prices) / len(fuel_prices)
        return average_price
    else:
        return None

def get_fuel_prices_from_website(city_code='cheboksary'):
    url = f'https://fuelprice.ru/t-{city_code}'

    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.find('table')
        if not table:
            raise ValueError("Не найдена таблица с ценами")

        fuel_data = []
        rows = table.find_all('tr')

        for row in rows[1:]:
            columns = row.find_all('td')
            if len(columns) < 5:
                continue

            company = columns[1].text.strip()
            fuel = columns[2].text.strip()
            today_price = clean_price(columns[3].text.strip())

            if today_price:
                fuel_data.append([company, fuel, f"{float(today_price):.2f}"])

        return fuel_data

    except (requests.RequestException, ValueError) as e:
        return None

@text_only_handler
def process_fuel_type(message, date, distance):
    if message is None:
        return

    chat_id = message.chat.id

    if message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return		
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    fuel_type = message.text.strip().lower() if message.text else ""

    fuel_type_mapping = {
        "аи-92": "аи-92",
        "аи-95": "аи-95",
        "аи-98": "аи-98",
        "аи-100": "аи-100",
        "дт": "дт",
        "газ": "газ спбт",
    }

    if fuel_type not in fuel_type_mapping:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите тип топлива только из предложенных вариантов!")
        bot.register_next_step_handler(sent, process_fuel_type, date, distance)
        return

    actual_fuel_type = fuel_type_mapping[fuel_type]

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Актуальная цена")
    item2 = types.KeyboardButton("Ввести свою")
    item3 = types.KeyboardButton("Вернуться в расход топлива")
    item4 = types.KeyboardButton("Вернуться в калькуляторы")
    item5 = types.KeyboardButton("В главное меню")
    markup.add(item1, item2)
    markup.add(item3)
    markup.add(item4)
    markup.add(item5)

    sent = bot.send_message(chat_id, "Выберите вариант ввода цены топлива:", reply_markup=markup)
    bot.register_next_step_handler(sent, handle_price_input_choice, date, distance, actual_fuel_type)

@text_only_handler
def handle_price_input_choice(message, date, distance, fuel_type):
    chat_id = message.chat.id

    if message.text == "Ввести свою":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в расход топлива")
        item2 = types.KeyboardButton("Вернуться в калькуляторы")
        item3 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2)
        markup.add(item3)

        sent = bot.send_message(chat_id, "Введите цену за литр топлива:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_price_per_liter_step, date, distance, fuel_type)
    elif message.text == "Актуальная цена":
        price_from_files = get_average_fuel_price_from_files(
            fuel_type, directory=os.path.join(BASE_DIR, 'data', 'user', 'azs')
        )
        if price_from_files:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton("Вернуться в расход топлива")
            item2 = types.KeyboardButton("Вернуться в калькуляторы")
            item3 = types.KeyboardButton("В главное меню")
            markup.add(item1)
            markup.add(item2)
            markup.add(item3)
            bot.send_message(chat_id, f"Актуальная средняя цена на {fuel_type.upper()} по РФ: {price_from_files:.2f} руб./л.", reply_markup=markup)
            sent = bot.send_message(chat_id, "Введите расход топлива на 100 км:", reply_markup=markup)
            bot.register_next_step_handler(sent, process_fuel_consumption_step, date, distance, fuel_type, price_from_files)
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton("Вернуться в расход топлива")
            item2 = types.KeyboardButton("Вернуться в калькуляторы")
            item3 = types.KeyboardButton("В главное меню")
            markup.add(item1)
            markup.add(item2)
            markup.add(item3)
            sent = bot.send_message(chat_id, f"Для выбранного топлива '{fuel_type}' данных нет!\nПожалуйста, введите цену", reply_markup=markup)
            bot.register_next_step_handler(sent, process_price_per_liter_step, date, distance, fuel_type)
    elif message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
    elif message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
    elif message.text == "В главное меню":
        return_to_menu(message)
    else:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите один из предложенных вариантов!")
        bot.register_next_step_handler(sent, handle_price_input_choice, date, distance, fuel_type)

@text_only_handler
def process_price_per_liter_step(message, date, distance, fuel_type):
    chat_id = message.chat.id
    if message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return		
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    input_text = message.text.replace(',', '.')
    try:
        price_per_liter = float(input_text)
        if price_per_liter <= 0:
            raise ValueError
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в расход топлива")
        item2 = types.KeyboardButton("Вернуться в калькуляторы")
        item3 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2)
        markup.add(item3)
        sent = bot.send_message(chat_id, "Введите расход топлива на 100 км:", reply_markup=markup)
        bot.clear_step_handler_by_chat_id(chat_id)
        bot.register_next_step_handler(sent, process_fuel_consumption_step, date, distance, fuel_type, price_per_liter)
    except ValueError:
        sent = bot.send_message(chat_id, "Пожалуйста, введите положительное число для цены топлива за литр!")
        bot.register_next_step_handler(sent, process_price_per_liter_step, date, distance, fuel_type)

@text_only_handler
def process_fuel_consumption_step(message, date, distance, fuel_type, price_per_liter):
    chat_id = message.chat.id
    if message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return		
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    input_text = message.text.replace(',', '.')
    try:
        fuel_consumption = float(input_text)
        if fuel_consumption <= 0:
            raise ValueError
        sent = bot.send_message(chat_id, "Введите количество пассажиров в машине:")
        bot.clear_step_handler_by_chat_id(chat_id)
        bot.register_next_step_handler(sent, process_passengers_step, date, distance, fuel_type, price_per_liter, fuel_consumption)
    except ValueError:
        sent = bot.send_message(chat_id, "Пожалуйста, введите положительное число для расхода топлива на 100 км!")
        bot.register_next_step_handler(sent, process_fuel_consumption_step, date, distance, fuel_type, price_per_liter)

@text_only_handler
def process_passengers_step(message, date, distance, fuel_type, price_per_liter, fuel_consumption):
    chat_id = message.chat.id
    if message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return		
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    try:
        passengers = int(message.text)
        if passengers <= 0:
            raise ValueError
        fuel_cost = (distance / 100) * fuel_consumption * price_per_liter
        fuel_cost_per_person = fuel_cost / passengers
        locations = trip_data[chat_id]['locations']
        coords = [f"{loc['latitude']},{loc['longitude']}" for loc in locations]
        yandex_maps_url = f"https://yandex.ru/maps/?rtext={'~'.join(coords)}&rtt=auto"
        try:
            response = requests.get(f'https://clck.ru/--?url={yandex_maps_url}')
            short_url = response.text
        except Exception as e:
            bot.send_message(chat_id, f"Не удалось сократить ссылку: {str(e)}")
            short_url = yandex_maps_url
        calculation_timestamp = datetime.now().strftime("%d.%m.%Y в %H:%M")
        if chat_id not in temporary_trip_data:
            temporary_trip_data[chat_id] = []
        temporary_trip_data[chat_id].append({
            "locations": locations,
            "date": date,
            "distance": distance,
            "fuel_type": fuel_type,
            "price_per_liter": price_per_liter,
            "fuel_consumption": fuel_consumption,
            "passengers": passengers,
            "fuel_spent": (distance / 100) * fuel_consumption,
            "fuel_cost": fuel_cost,
            "fuel_cost_per_person": fuel_cost_per_person,
            "route_link": short_url,
            "calculation_timestamp": calculation_timestamp  
        })
        display_summary(chat_id, fuel_cost, fuel_cost_per_person, fuel_type, date, distance, price_per_liter, fuel_consumption, passengers)
    except ValueError:
        sent = bot.send_message(chat_id, "Пожалуйста, введите положительное целое число для количества пассажиров!")
        bot.register_next_step_handler(sent, process_passengers_step, date, distance, fuel_type, price_per_liter, fuel_consumption)

def display_summary(chat_id, fuel_cost, fuel_cost_per_person, fuel_type, date, distance, price_per_liter, fuel_consumption, passengers):
    fuel_spent = (distance / 100) * fuel_consumption
    locations = trip_data[chat_id]['locations']
    coords = [f"{loc['latitude']},{loc['longitude']}" for loc in locations]
    yandex_maps_url = f"https://yandex.ru/maps/?rtext={'~'.join(coords)}&rtt=auto"
    try:
        response = requests.get(f'https://clck.ru/--?url={yandex_maps_url}')
        short_url = response.text
    except Exception as e:
        bot.send_message(chat_id, f"Не удалось сократить ссылку: {str(e)}")
        short_url = yandex_maps_url
    summary_message = "🚗 *ИНФОРМАЦИЯ О ПОЕЗДКЕ*\n"
    summary_message += "-------------------------------------------------------------\n"
    for i, loc in enumerate(locations, 1):
        summary_message += f"📍 *Местоположение {i}:*\n{loc['address']}\n"
    summary_message += f"🗓️ *Дата поездки:* {date}\n"
    summary_message += f"📏 *Расстояние:* {distance:.2f} км.\n"
    summary_message += f"⛽ *Тип топлива:* {fuel_type}\n"
    summary_message += f"💵 *Цена топлива за литр:* {price_per_liter:.2f} руб.\n"
    summary_message += f"⚙️ *Расход топлива на 100 км:* {fuel_consumption} л.\n"
    summary_message += f"👥 *Количество пассажиров:* {passengers} чел.\n"
    summary_message += "-------------------------------------------------------------\n"
    summary_message += f"🛢️ *ПОТРАЧЕНО ЛИТРОВ ТОПЛИВА:* {fuel_spent:.2f} л.\n"
    summary_message += f"💰 *СТОИМОСТЬ ТОПЛИВА ДЛЯ ПОЕЗДКИ:* {fuel_cost:.2f} руб.\n"
    summary_message += f"👤 *СТОИМОСТЬ ТОПЛИВА НА ЧЕЛОВЕКА:* {fuel_cost_per_person:.2f} руб.\n"
    summary_message += f"[ССЫЛКА НА МАРШРУТ]({short_url})\n"
    summary_message = summary_message.replace('\n', '\n\n')
    bot.clear_step_handler_by_chat_id(chat_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Вернуться в расход топлива")
    item2 = types.KeyboardButton("Вернуться в калькуляторы")
    item3 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)
    markup.add(item3)
    bot.send_message(chat_id, summary_message, reply_markup=markup, parse_mode="Markdown")
    if chat_id in temporary_trip_data and temporary_trip_data[chat_id]:
        if chat_id not in user_trip_data:
            user_trip_data[chat_id] = []
        user_trip_data[chat_id].extend(temporary_trip_data[chat_id])
        last_trip = user_trip_data[chat_id][-1]
        save_trip_data(chat_id)
        save_trip_to_excel(chat_id, last_trip)
        temporary_trip_data[chat_id] = []
    reset_and_start_over(chat_id)

def update_excel_file(user_id):
    folder_path = os.path.join(BASE_DIR, "data", "user", "calculators", "trip", "excel")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    file_path = os.path.join(folder_path, f"{user_id}_trips.xlsx")

    trips = user_trip_data.get(user_id, [])

    if not trips:
        columns = ["Дата", "Дата расчета"]
        columns.extend([
            "Расстояние (км)", "Тип топлива", "Цена топлива (руб/л)",
            "Расход топлива (л/100 км)", "Количество пассажиров",
            "Потрачено литров", "Стоимость топлива (руб)",
            "Стоимость на человека (руб)", "Ссылка на маршрут"
        ])
        df = pd.DataFrame(columns=columns)
        df.to_excel(file_path, index=False)
        return

    max_locations = max(len(trip["locations"]) for trip in trips)

    columns = ["Дата", "Дата расчета"]
    location_columns = [f"Местоположение {i+1}" for i in range(max_locations)]
    columns.extend(location_columns)
    columns.extend([
        "Расстояние (км)", "Тип топлива", "Цена топлива (руб/л)",
        "Расход топлива (л/100 км)", "Количество пассажиров",
        "Потрачено литров", "Стоимость топлива (руб)",
        "Стоимость на человека (руб)", "Ссылка на маршрут"
    ])

    trip_records = []
    for trip in trips:
        trip_data = {
            "Дата": trip['date'],
            "Дата расчета": trip.get('calculation_timestamp', "Неизвестно"),
            "Расстояние (км)": round(trip.get('distance', None), 2),
            "Тип топлива": trip.get('fuel_type', None),
            "Цена топлива (руб/л)": round(trip.get('price_per_liter', None), 2),
            "Расход топлива (л/100 км)": round(trip.get('fuel_consumption', None), 2),
            "Количество пассажиров": trip.get('passengers', None),
            "Потрачено литров": round(trip.get('fuel_spent', None), 2),
            "Стоимость топлива (руб)": round(trip.get('fuel_cost', None), 2),
            "Стоимость на человека (руб)": round(trip.get('fuel_cost_per_person', None), 2),
            "Ссылка на маршрут": trip.get('route_link', "Нет ссылки")
        }
        for i in range(max_locations):
            key = f"Местоположение {i+1}"
            trip_data[key] = trip['locations'][i]['address'] if i < len(trip['locations']) else None
        trip_records.append(trip_data)

    df = pd.DataFrame(trip_records, columns=columns)
    df.to_excel(file_path, index=False)

    workbook = load_workbook(file_path)
    worksheet = workbook.active
    for column in worksheet.columns:
        max_length = max(len(str(cell.value)) for cell in column if cell.value) + 2
        worksheet.column_dimensions[column[0].column_letter].width = max_length
    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(horizontal='center', vertical='center')
    thick_border = Border(left=Side(style='thick'), right=Side(style='thick'),
                          top=Side(style='thick'), bottom=Side(style='thick'))
    for row in worksheet.iter_rows(min_row=2, min_col=len(columns)-3, max_col=len(columns)):
        for cell in row:
            cell.border = thick_border
    workbook.save(file_path)

def save_trip_to_excel(user_id, trip):
    directory = os.path.join(BASE_DIR, "data", "user", "calculators", "trip", "excel")
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, f"{user_id}_trips.xlsx")
    
    trips = user_trip_data.get(user_id, [])
    max_locations = max(len(t["locations"]) for t in trips) if trips else len(trip["locations"])
    
    columns = ["Дата", "Дата расчета"]
    location_columns = [f"Местоположение {i+1}" for i in range(max_locations)]
    columns.extend(location_columns)
    columns.extend([
        "Расстояние (км)", "Тип топлива", "Цена топлива (руб/л)",
        "Расход топлива (л/100 км)", "Количество пассажиров",
        "Потрачено литров", "Стоимость топлива (руб)",
        "Стоимость на человека (руб)", "Ссылка на маршрут"
    ])
    
    new_trip_data = {
        "Дата": trip['date'],
        "Дата расчета": trip.get('calculation_timestamp', "Неизвестно"),
        "Расстояние (км)": round(trip.get('distance', None), 2),
        "Тип топлива": trip.get('fuel_type', None),
        "Цена топлива (руб/л)": round(trip.get('price_per_liter', None), 2),
        "Расход топлива (л/100 км)": round(trip.get('fuel_consumption', None), 2),
        "Количество пассажиров": trip.get('passengers', None),
        "Потрачено литров": round(trip.get('fuel_spent', None), 2),
        "Стоимость топлива (руб)": round(trip.get('fuel_cost', None), 2),
        "Стоимость на человека (руб)": round(trip.get('fuel_cost_per_person', None), 2),
        "Ссылка на маршрут": trip.get('route_link', None)
    }
    
    for i in range(max_locations):
        key = f"Местоположение {i+1}"
        new_trip_data[key] = trip['locations'][i]['address'] if i < len(trip['locations']) else None

    new_trip_df = pd.DataFrame([new_trip_data], columns=columns)
    
    if os.path.exists(file_path):
        existing_data = pd.read_excel(file_path).dropna(axis=1, how='all')
        existing_data = existing_data.reindex(columns=columns, fill_value=None)
        updated_data = pd.concat([existing_data, new_trip_df], ignore_index=True)
    else:
        updated_data = new_trip_df
    
    updated_data.to_excel(file_path, index=False)
    
    workbook = load_workbook(file_path)
    worksheet = workbook.active
    for column in worksheet.columns:
        max_length = max(len(str(cell.value)) for cell in column if cell.value) + 2
        worksheet.column_dimensions[column[0].column_letter].width = max_length
    for row in worksheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(horizontal="center", vertical="center")
    thick_border = Border(left=Side(style='thick'), right=Side(style='thick'),
                          top=Side(style='thick'), bottom=Side(style='thick'))
    for row in worksheet.iter_rows(min_col=worksheet.max_column-3, max_col=worksheet.max_column):
        for cell in row:
            cell.border = thick_border
    workbook.save(file_path)

# --------------------------------------------- КАЛЬКУЛЯТОРЫ_РАСХОД ТОПЛИВА (посмотреть поездки) ---------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Посмотреть поездки")
@check_function_state_decorator('Посмотреть поездки')
@track_usage('Посмотреть поездки')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_trips(message):
    user_id = message.chat.id
    trips = user_trip_data.get(user_id, [])

    if trips:
        message_text = "*Список ваших поездок:*\n\n"
        for i, trip in enumerate(trips, 1):
            calc_time = trip.get('calculation_timestamp', "дата расчета неизвестна")
            message_text += f"🕒 №{i}. {calc_time}\n"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Поездки в EXCEL")
        markup.add("Вернуться в расход топлива")
        markup.add("Вернуться в калькуляторы")
        markup.add("В главное меню")

        msg = bot.send_message(user_id, message_text, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_view_trip_selection)

        bot.send_message(user_id, "Введите номера поездок для просмотра:", reply_markup=markup)
    else:
        bot.send_message(user_id, "❌ У вас нет сохраненных поездок!")
        handle_fuel_expense(message, show_description=False)

@text_only_handler
def process_view_trip_selection(message):
    if message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return		
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Поездки в EXCEL":
        send_excel_file(message)
        return

    chat_id = message.chat.id
    user_id = message.chat.id
    trips = user_trip_data.get(user_id, [])

    if not trips:
        bot.send_message(chat_id, "❌ У вас нет сохраненных поездок!")
        handle_fuel_expense(message, show_description=False)
        return

    try:
        indices = [int(num.strip()) - 1 for num in message.text.split(',')]
        valid_indices = []
        invalid_indices = []

        for index in indices:
            if 0 <= index < len(trips):
                valid_indices.append(index)
            else:
                invalid_indices.append(index + 1)

        if not valid_indices and invalid_indices:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Поездки в EXCEL")
            markup.add("Вернуться в расход топлива")
            markup.add("Вернуться в калькуляторы")
            markup.add("В главное меню")
            msg = bot.send_message(chat_id, "Некорректный номер!\nПожалуйста, выберите существующие поездки из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_view_trip_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(chat_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        for index in valid_indices:
            trip = trips[index]
            date = trip['date'] if trip['date'] != "Без даты" else "Без даты"
            summary_message = f"🚗 *ИТОГОВЫЕ ДАННЫЕ ПОЕЗДКИ* *№{index + 1}* \n\n"
            summary_message += "-------------------------------------------------------------\n\n"
            for i, loc in enumerate(trip['locations'], 1):
                summary_message += f"📍 *Местоположение {i}:*\n\n{loc['address']}\n\n"
            summary_message += f"🗓️ *Дата поездки:* {date}\n\n"
            summary_message += f"📏 *Расстояние:* {trip['distance']:.2f} км.\n\n"
            summary_message += f"⛽ *Тип топлива:* {trip['fuel_type']}\n\n"
            summary_message += f"💵 *Цена топлива за литр:* {trip['price_per_liter']:.2f} руб.\n\n"
            summary_message += f"⚙️ *Расход топлива на 100 км:* {trip['fuel_consumption']} л.\n\n"
            summary_message += f"👥 *Количество пассажиров:* {trip['passengers']}\n\n"
            summary_message += "-------------------------------------------------------------\n\n"
            summary_message += f"🛢️ *ПОТРАЧЕНО ЛИТРОВ ТОПЛИВА:* {trip['fuel_spent']:.2f} л.\n\n"
            summary_message += f"💰 *СТОИМОСТЬ ТОПЛИВА ДЛЯ ПОЕЗДКИ:* {trip['fuel_cost']:.2f} руб.\n\n"
            summary_message += f"👤 *СТОИМОСТЬ ТОПЛИВА НА ЧЕЛОВЕКА:* {trip['fuel_cost_per_person']:.2f} руб.\n\n"
            if 'route_link' in trip:
                summary_message += f"[ССЫЛКА НА МАРШРУТ]({trip['route_link']})\n\n"
            else:
                summary_message += "Ссылка на маршрут недоступна!\n\n"
            bot.send_message(chat_id, summary_message, parse_mode="Markdown")

        handle_fuel_expense(message, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Поездки в EXCEL")
        markup.add("Вернуться в расход топлива")
        markup.add("Вернуться в калькуляторы")
        markup.add("В главное меню")
        msg = bot.send_message(chat_id, "Некорректный ввод!\nПожалуйста, введите номера поездок", reply_markup=markup)
        bot.register_next_step_handler(msg, process_view_trip_selection)

# --------------------------------------------- КАЛЬКУЛЯТОРЫ_РАСХОД ТОПЛИВА (поездки в excel) ---------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Поездки в EXCEL")
@check_function_state_decorator('Поездки в EXCEL')
@track_usage('Поездки в EXCEL')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_excel_file(message):
    user_id = message.chat.id
    excel_file_path = os.path.join(BASE_DIR, 'data', 'user', 'calculators', 'trip', 'excel', f"{user_id}_trips.xlsx")

    if os.path.exists(excel_file_path):
        with open(excel_file_path, 'rb') as excel_file:
            bot.send_document(user_id, excel_file)
    else:
        bot.send_message(user_id, "❌ Файл Excel не найден!\nУбедитесь, что у вас есть сохраненные поездки")
    handle_fuel_expense(message, show_description=False)

# --------------------------------------------- КАЛЬКУЛЯТОРЫ_РАСХОД ТОПЛИВА (удалить поездки) ---------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Удалить поездки")
@check_function_state_decorator('Удалить поездки')
@track_usage('Удалить поездки')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def ask_for_trip_to_delete(message):
    user_id = message.chat.id
    trips = user_trip_data.get(user_id, [])

    if not trips:
        bot.send_message(user_id, "❌ У вас нет сохраненных поездок!")
        handle_fuel_expense(message, show_description=False)
        return

    message_text = "*Список ваших поездок:*\n\n"
    for i, trip in enumerate(trips, 1):
        calc_time = trip.get('calculation_timestamp', "дата расчета неизвестна")
        message_text += f"🕒 №{i}. {calc_time}\n"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в расход топлива")
    markup.add("Вернуться в калькуляторы")
    markup.add("В главное меню")

    msg = bot.send_message(user_id, message_text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_delete_trip_selection)
    bot.send_message(user_id, "Введите номера для удаления поездок:", reply_markup=markup)

@text_only_handler
def process_delete_trip_selection(message):
    user_id = message.chat.id
    trips = user_trip_data.get(user_id, [])

    if not trips:
        bot.send_message(user_id, "❌ У вас нет сохраненных поездок!")
        handle_fuel_expense(message, show_description=False)
        return

    if message.text == "Вернуться в расход топлива":
        handle_fuel_expense(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    try:
        indices = [int(num.strip()) - 1 for num in message.text.split(',')]
        valid_indices = []
        invalid_indices = []

        for index in indices:
            if 0 <= index < len(trips):
                valid_indices.append(index)
            else:
                invalid_indices.append(index + 1)

        if not valid_indices and invalid_indices:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Вернуться в расход топлива")
            markup.add("Вернуться в калькуляторы")
            markup.add("В главное меню")
            msg = bot.send_message(user_id, "Некорректный номер!\nПожалуйста, выберите существующие поездки из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_delete_trip_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(user_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        valid_indices.sort(reverse=True)
        for index in valid_indices:
            del trips[index]

        user_trip_data[user_id] = trips
        save_trip_data(user_id)
        update_excel_file(user_id) 
        bot.send_message(user_id, "✅ Выбранные поездки успешно удалены!")

        handle_fuel_expense(message, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в расход топлива")
        markup.add("Вернуться в калькуляторы")
        markup.add("В главное меню")
        msg = bot.send_message(user_id, "Некорректный ввод!\nПожалуйста, введите номера поездок", reply_markup=markup)
        bot.register_next_step_handler(msg, process_delete_trip_selection)