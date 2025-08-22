from core.imports import wraps, telebot, types, os, json, re, datetime, timedelta, ReplyKeyboardMarkup, ReplyKeyboardRemove, pd, Workbook, load_workbook, Alignment, Border, Side, Font, PatternFill, openpyxl
from core.bot_instance import bot, BASE_DIR
from .calculators_main import return_to_calculators
from handlers.user.user_main_menu import return_to_menu
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_ОСАГО --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "ОСАГО")
@check_function_state_decorator('ОСАГО')
@track_usage('ОСАГО')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_osago_calc(message, show_description=True):
    global stored_message
    stored_message = message

    description = (
        "ℹ️ *Краткая справка по расчету ОСАГО*\n\n"
        "📌 *Расчет ОСАГО:*\n"
        "Расчет ведется по следующим данным - *регион, мощность авто, возраст и стаж водителей, количество аварий, тип полиса (ограниченный/неограниченный), период использования*\n\n"
        "_P.S. калькулятор предоставляет ориентировочные данные на основе актуальных коэффициентов. Точные суммы зависят от страховой компании и могут отличаться!_\n\n"
        "📌 *Просмотр ОСАГО:*\n"
        "Вы можете посмотреть свои предыдущие расчеты с указанием всех параметров\n\n"
        "📌 *Удаление ОСАГО:*\n"
        "Вы можете удалить свои расчеты, если они вам больше не нужны"
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Рассчитать ОСАГО', 'Просмотр ОСАГО', 'Удаление ОСАГО')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')

    if show_description:
        bot.send_message(message.chat.id, description, parse_mode='Markdown')

    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

OSAGO_JSON_PATH = os.path.join(BASE_DIR, 'files', 'files_for_calc', 'files_for_osago', 'osago.json')
USER_HISTORY_PATH_OSAGO = os.path.join(BASE_DIR, 'data', 'user', 'calculators', 'osago', 'osago_users.json')
OSAGO_EXCEL_DIR = os.path.join(BASE_DIR, 'data', 'user', 'calculators', 'osago', 'excel')

osago_data = {}
user_history_osago = {}
user_data = {}

def ensure_path_and_file(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def load_osago_data():
    global osago_data
    try:
        with open(OSAGO_JSON_PATH, 'r', encoding='utf-8') as file:
            osago_data = json.load(file)
    except Exception as e:
        pass

def load_user_history_osago():
    global user_history_osago
    try:
        if os.path.exists(USER_HISTORY_PATH_OSAGO):
            with open(USER_HISTORY_PATH_OSAGO, 'r', encoding='utf-8') as db_file:
                user_history_osago = json.load(db_file)
        else:
            user_history_osago = {}
    except Exception as e:
        user_history_osago = {}

def save_user_history_osago():
    try:
        with open(USER_HISTORY_PATH_OSAGO, 'w', encoding='utf-8') as db_file:
            json.dump(user_history_osago, db_file, ensure_ascii=False, indent=2)
    except Exception as e:
        pass

ensure_path_and_file(OSAGO_JSON_PATH)
ensure_path_and_file(USER_HISTORY_PATH_OSAGO)
os.makedirs(OSAGO_EXCEL_DIR, exist_ok=True)
load_osago_data()
load_user_history_osago()

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_ОСАГО (рассчитать осаго) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Рассчитать ОСАГО")
@check_function_state_decorator('Рассчитать ОСАГО')
@track_usage('Рассчитать ОСАГО')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def start_osago_calculation(message):
    if not osago_data:
        bot.send_message(message.chat.id, "❌ Данные для расчета не найдены!")
        return

    user_id = message.from_user.id
    user_data[user_id] = {'user_id': user_id, 'username': message.from_user.username or 'unknown'}

    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    owner_types = [owner['name'] for owner in osago_data['owner_types']]
    for i in range(0, len(owner_types), 2):
        if i + 1 < len(owner_types):
            markup.row(owner_types[i], owner_types[i + 1])
        else:
            markup.add(owner_types[i])
    markup.add("Вернуться в ОСАГО")   
    markup.add('Вернуться в калькуляторы')     
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Кто владелец ТС?", reply_markup=markup)
    bot.register_next_step_handler(msg, process_owner_type_step)

@text_only_handler
def process_owner_type_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    owner_type = message.text.strip()
    if owner_type not in [owner['name'] for owner in osago_data['owner_types']]:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите верный вариант")
        bot.register_next_step_handler(msg, process_owner_type_step)
        return

    user_data[user_id]['owner_type'] = owner_type

    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    vehicle_types = [vt['name'] for vt in osago_data['vehicle_types']]
    for i in range(0, len(vehicle_types), 2):
        if i + 1 < len(vehicle_types):
            markup.row(vehicle_types[i], vehicle_types[i + 1])
        else:
            markup.add(vehicle_types[i])
    markup.add("Вернуться в ОСАГО")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Выберите тип ТС:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_vehicle_type_step)

@text_only_handler
def process_vehicle_type_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    vehicle_type = message.text.strip()
    vehicle = next((vt for vt in osago_data['vehicle_types'] if vt['name'] == vehicle_type), None)
    if not vehicle:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите верный вариант")
        bot.register_next_step_handler(msg, process_vehicle_type_step)
        return

    user_data[user_id]['vehicle_type'] = vehicle_type
    user_data[user_id]['vehicle_id'] = vehicle['id']

    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    regions = [region['name'] for region in osago_data['regions']]
    for i in range(0, len(regions), 2):
        if i + 1 < len(regions):
            markup.row(regions[i], regions[i + 1])
        else:
            markup.add(regions[i])
    markup.add("Вернуться в ОСАГО")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Выберите регион:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_osago_region_step)

@text_only_handler
def process_osago_region_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    region_name = message.text.strip()
    region = next((r for r in osago_data['regions'] if r['name'] == region_name), None)
    if not region:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите верный вариант")
        bot.register_next_step_handler(msg, process_osago_region_step)
        return

    user_data[user_id]['region'] = region_name
    user_data[user_id]['region_data'] = region

    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    if 'cities' in region and region['cities']:
        cities = list(region['cities'].keys())
        for i in range(0, len(cities), 2):
            if i + 1 < len(cities):
                markup.row(cities[i], cities[i + 1])
            else:
                markup.add(cities[i])
    else:
        markup.add("Единственный регион")
    markup.add("Вернуться в ОСАГО")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Выберите город:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_city_step)

@text_only_handler
def process_city_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    city_name = message.text.strip()
    region = user_data[user_id]['region_data']
    if city_name != "Единственный регион" and ('cities' not in region or city_name not in region['cities']):
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите верный вариант")
        bot.register_next_step_handler(msg, process_city_step)
        return

    user_data[user_id]['city'] = city_name
    if city_name == "Единственный регион":
        user_data[user_id]['kt'] = float(region['kt']) if region['kt'] else 1.0
    else:
        user_data[user_id]['kt'] = region['cities'].get(city_name, 1.0)

    vehicle_id = user_data[user_id]['vehicle_id']
    if vehicle_id >= 5 and vehicle_id <= 12: 
        user_data[user_id]['km'] = 1.0  
        proceed_to_usage_period(message)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в ОСАГО")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Введите мощность двигателя (л.с.):", reply_markup=markup)
        bot.register_next_step_handler(msg, process_engine_power_step)

@text_only_handler
def process_engine_power_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        power = float(message.text.replace(',', '.'))
        user_data[user_id]['engine_power'] = power
        km = calculate_km(power)
        user_data[user_id]['km'] = km
        proceed_to_usage_period(message)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число")
        bot.register_next_step_handler(msg, process_engine_power_step)

@text_only_handler
def proceed_to_usage_period(message):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    periods = [period['name'] for period in osago_data['usage_periods']]
    for i in range(0, len(periods), 2):
        if i + 1 < len(periods):
            markup.row(periods[i], periods[i + 1])
        else:
            markup.add(periods[i])
    markup.add("Вернуться в ОСАГО")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Выберите период использования ТС:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_usage_period_step)

@text_only_handler
def process_usage_period_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    period_name = message.text.strip()
    if period_name not in [p['name'] for p in osago_data['usage_periods']]:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите верный вариант")
        bot.register_next_step_handler(msg, process_usage_period_step)
        return

    user_data[user_id]['usage_period'] = period_name
    ks = calculate_ks(period_name)
    user_data[user_id]['ks'] = ks

    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    markup.add("Без ограничений по водителям", "С ограничениями")
    markup.add("Вернуться в ОСАГО")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Лица, допущенные к управлению:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_driver_restriction_step)

@text_only_handler
def process_driver_restriction_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    restriction = message.text.strip()
    if restriction not in ["Без ограничений по водителям", "С ограничениями"]:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите верный вариант")
        bot.register_next_step_handler(msg, process_driver_restriction_step)
        return

    user_data[user_id]['driver_restriction'] = restriction
    user_data[user_id]['ko'] = 2.27 if restriction == "Без ограничений по водителям" else 1.0  

    if restriction == "Без ограничений по водителям":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в ОСАГО")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Введите возраст и стаж страхователя (например: 18, 0):", reply_markup=markup)
        bot.register_next_step_handler(msg, process_unrestricted_age_experience_step)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в ОСАГО")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Сколько человек допущено к управлению?", reply_markup=markup)
        bot.register_next_step_handler(msg, process_restricted_driver_count_step)

@text_only_handler
def process_unrestricted_age_experience_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        age, experience = map(int, message.text.split(','))
        if age < 18:
            msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВозраст водителя должен быть не менее 18 лет")
            bot.register_next_step_handler(msg, process_unrestricted_age_experience_step)
            return
        if experience < 0:
            msg = bot.send_message(message.chat.id, "Некорректный ввод!\nСтаж не может быть отрицательным")
            bot.register_next_step_handler(msg, process_unrestricted_age_experience_step)
            return
        user_data[user_id]['insurer_age'] = age
        user_data[user_id]['insurer_experience'] = experience

        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("Да", "Нет")
        markup.add("Вернуться в ОСАГО")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Были ли аварии (по его вине)?", reply_markup=markup)
        bot.register_next_step_handler(msg, process_unrestricted_accidents_step)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите возраст и стаж через запятую (например: 18, 0)")
        bot.register_next_step_handler(msg, process_unrestricted_age_experience_step)

@text_only_handler
def process_unrestricted_accidents_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    accidents = message.text.strip()
    if accidents not in ["Да", "Нет"]:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите да или нет")
        bot.register_next_step_handler(msg, process_unrestricted_accidents_step)
        return

    if accidents == "Нет":
        kbm = calculate_kbm(user_data[user_id]['insurer_age'], user_data[user_id]['insurer_experience'], 0)
        user_data[user_id]['kbm'] = kbm
        calculate_osago(message)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в ОСАГО")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Сколько было аварий (по его вине)?", reply_markup=markup)
        bot.register_next_step_handler(msg, process_unrestricted_accident_count_step)

@text_only_handler
def process_unrestricted_accident_count_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        accident_count = int(message.text)
        kbm = calculate_kbm(user_data[user_id]['insurer_age'], user_data[user_id]['insurer_experience'], accident_count)
        user_data[user_id]['kbm'] = kbm
        calculate_osago(message)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число")
        bot.register_next_step_handler(msg, process_unrestricted_accident_count_step)

@text_only_handler
def process_restricted_driver_count_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        driver_count = int(message.text)
        user_data[user_id]['driver_count'] = driver_count
        user_data[user_id]['drivers'] = []
        process_driver_info(message, 1)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число")
        bot.register_next_step_handler(msg, process_restricted_driver_count_step)

@text_only_handler
def process_driver_info(message, driver_num):
    user_id = message.from_user.id
    if driver_num > user_data[user_id]['driver_count']:
        calculate_restricted_kbm(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Вернуться в ОСАГО")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, f"Введите возраст и стаж для *водителя №{driver_num}* (например: 18, 0):", reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler(msg, lambda m: process_driver_age_experience_step(m, driver_num))

@text_only_handler
def process_driver_age_experience_step(message, driver_num):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        age, experience = map(int, message.text.split(','))
        if age < 18:
            msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВозраст водителя должен быть не менее 18 лет")
            bot.register_next_step_handler(msg, lambda m: process_driver_age_experience_step(m, driver_num))
            return
        if experience < 0:
            msg = bot.send_message(message.chat.id, "Некорректный ввод!\nСтаж не может быть отрицательным")
            bot.register_next_step_handler(msg, lambda m: process_driver_age_experience_step(m, driver_num))
            return
        driver_data = {'age': age, 'experience': experience}
        user_data[user_id]['drivers'].append(driver_data)

        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("Да", "Нет")
        markup.add("Вернуться в ОСАГО")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, f"Были ли аварии у *водителя №{driver_num}* (по его вине)?", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, lambda m: process_driver_accidents_step(m, driver_num))
    except ValueError:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите возраст и стаж (например: 18, 0)")
        bot.register_next_step_handler(msg, lambda m: process_driver_age_experience_step(m, driver_num))

@text_only_handler
def process_driver_accidents_step(message, driver_num):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    accidents = message.text.strip()
    if accidents not in ["Да", "Нет"]:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите да или нет")
        bot.register_next_step_handler(msg, lambda m: process_driver_accidents_step(m, driver_num))
        return

    if accidents == "Нет":
        user_data[user_id]['drivers'][driver_num-1]['accidents'] = 0
        process_driver_info(message, driver_num + 1)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в ОСАГО")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, f"Сколько было аварий у *водителя №{driver_num}* (по его вине)?", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, lambda m: process_driver_accident_count_step(m, driver_num))

@text_only_handler
def process_driver_accident_count_step(message, driver_num):
    user_id = message.from_user.id
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        accident_count = int(message.text)
        user_data[user_id]['drivers'][driver_num-1]['accidents'] = accident_count
        process_driver_info(message, driver_num + 1)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число")
        bot.register_next_step_handler(msg, lambda m: process_driver_accident_count_step(m, driver_num))

def calculate_km(power):
    if power <= 50: return 0.6
    elif power <= 70: return 0.8
    elif power <= 100: return 1.0
    elif power <= 120: return 1.2
    elif power <= 150: return 1.4
    else: return 1.6

def calculate_ks(period_name):
    period_map = {
        "3 месяца": 0.5,
        "4 месяца": 0.6,
        "5 месяцев": 0.65,
        "6 месяцев": 0.7,
        "7 месяцев": 0.8,
        "8 месяцев": 0.9,
        "9 месяцев": 0.95,
        "10–12 месяцев": 1.0
    }
    return period_map.get(period_name, 1.0)

def calculate_kvs(age, experience):
    if age < 18 or experience < 0:
        raise ValueError("Возраст должен быть >= 18, стаж >= 0")
    if age <= 22 and experience <= 3: return 2.27  
    elif age <= 22 and experience > 3: return 1.93
    elif age > 22 and experience <= 3: return 1.87
    else: return 1.0

def calculate_kbm(age, experience, accidents):
    if age < 18 or experience < 0:
        raise ValueError("Возраст должен быть >= 18, стаж >= 0")
    
    if accidents > 0:
        if accidents == 1: return 1.55
        elif accidents == 2: return 2.25
        elif accidents == 3: return 2.45
        else: return 3.92
    
    base_class = 3
    final_class = base_class + min(experience, 10)
    
    for kmb_class in osago_data['kmb_classes']:
        if kmb_class['name'] == f"Класс {final_class}":
            return kmb_class['kbm']
    return 0.46

def get_base_tariff(vehicle_id):
    tariffs = {
        1: (1548, 5552),  
        2: (2471, 5431),  
        3: (2089, 6603),  
        4: (2966, 7396),  
        5: (2089, 6603),  
        6: (2966, 7396), 
        7: (2089, 6603),  
        8: (2966, 7396), 
        9: (4449, 8875),  
        10: (2966, 7396),
        11: (1483, 3698), 
        12: (1125, 3374)  
    }
    return tariffs.get(vehicle_id, (2471, 5431)) 

def calculate_restricted_kbm(message):
    user_id = message.from_user.id
    kvs_list = []
    kbm_list = []
    driver_results = []
    
    for i, driver in enumerate(user_data[user_id]['drivers'], 1):
        kvs = calculate_kvs(driver['age'], driver['experience'])
        kbm = calculate_kbm(driver['age'], driver['experience'], driver['accidents'])
        kvs_list.append(kvs)
        kbm_list.append(kbm)
        
        base_tariff_min, base_tariff_max = 1646, 7535
        kt = user_data[user_id]['kt']
        km = user_data[user_id]['km']
        ks = user_data[user_id]['ks']
        ko = user_data[user_id]['ko']
        
        min_cost = base_tariff_min * kt * km * kvs * ko * ks * kbm
        max_cost = base_tariff_max * kt * km * kvs * ko * ks * kbm
        
        driver_results.append({
            'driver_num': i,
            'kvs': kvs,
            'kbm': kbm,
            'min_cost': min_cost,
            'max_cost': max_cost
        })
    
    user_data[user_id]['kvs'] = max(kvs_list)  
    user_data[user_id]['kbm'] = max(kbm_list) 
    user_data[user_id]['driver_results'] = driver_results
    calculate_osago(message)

@text_only_handler
def calculate_osago(message):
    user_id_int = message.from_user.id  
    user_id_str = str(user_id_int)  
    data = user_data[user_id_int]

    base_tariff_min, base_tariff_max = get_base_tariff(data['vehicle_id'])
    kt = data['kt']
    km = data['km']
    ks = data['ks']
    ko = data['ko']

    if data['driver_restriction'] == "Без ограничений по водителям":
        kvs = calculate_kvs(data['insurer_age'], data['insurer_experience'])
        kbm = data['kbm']
        min_cost = base_tariff_min * kt * km * kvs * ko * ks * kbm
        max_cost = base_tariff_max * kt * km * kvs * ko * ks * kbm
        
        result_message = (
            "*Итоговый расчет по ОСАГО (без ограничений):*\n\n"
            "*Ваши данные:*\n\n"
            f"👤 *Владелец ТС:* {data['owner_type']}\n"
            f"🚗 *Тип ТС:* {data['vehicle_type']}\n"
            f"🌍 *Регион:* {data['region']}\n"
            f"🏙 *Город:* {data['city']}\n"
            f"💪 *Мощность двигателя:* {data.get('engine_power', 'Не требуется')} л.с.\n"
            f"📅 *Период использования:* {data['usage_period']}\n"
            f"🚗 *Лица, допущенные к управлению:* {data['driver_restriction']}\n"
            f"🎂 *Возраст страхователя:* {data['insurer_age']}\n"
            f"⏳ *Стаж страхователя:* {data['insurer_experience']}\n"
            "\n*Итоговый расчет:*\n\n"
            f"💰 *Диапазон цены:* {min_cost:,.0f} … {max_cost:,.0f} руб.\n"
            f"\n*Тариф и коэффициенты:*\n\n"
            f"💵 *Базовый тариф* – от {base_tariff_min} до {base_tariff_max} руб.\n"
            f"⭐ *КТ (коэффициент территории):* {kt}\n"
            f"⭐ *КМ (коэффициент мощности):* {km}\n"
            f"⭐ *КВС (коэффициент возраст-стаж):* {kvs}\n"
            f"⭐ *КО (коэффициент ограничения):* {ko}\n"
            f"⭐ *КС (коэффициент сезонности):* {ks}\n"
            f"⭐ *КБМ (коэффициент бонус-малус):* {kbm}\n"
        )
    else:
        result_message = (
            "*Итоговый расчет по ОСАГО (с ограничениями):*\n\n"
            "*Ваши данные:*\n\n"
            f"👤 *Владелец ТС:* {data['owner_type']}\n"
            f"🚗 *Тип ТС:* {data['vehicle_type']}\n"
            f"🌍 *Регион:* {data['region']}\n"
            f"🏙 *Город:* {data['city']}\n"
            f"💪 *Мощность двигателя:* {data.get('engine_power', 'Не требуется')} л.с.\n"
            f"📅 *Период использования:* {data['usage_period']}\n"
            f"🚗 *Лица, допущенные к управлению:* {data['driver_restriction']}\n"
            "\n*Данные водителей:*\n"
        )
        
        for i, driver in enumerate(data['drivers'], 1):
            result_message += (
                f"\n👤 *Водитель №{i}:*\n"
                f"🎂 *Возраст:* {driver['age']}\n"
                f"⏳ *Стаж:* {driver['experience']}\n"
                f"💥 *Аварии:* {driver['accidents']}\n"
            )
        
        result_message += "\n*Индивидуальные расчеты по водителям:*\n"
        for result in data['driver_results']:
            result_message += (
                f"\n👤 *Водитель №{result['driver_num']}:*\n"
                f"💰 *Диапазон цены:* {result['min_cost']:,.0f} … {result['max_cost']:,.0f} руб.\n"
                f"⭐ *КВС:* {result['kvs']}\n"
                f"⭐ *КБМ:* {result['kbm']}\n"
            )
        
        kvs = data['kvs']
        kbm = data['kbm']
        min_cost = base_tariff_min * kt * km * kvs * ko * ks * kbm
        max_cost = base_tariff_max * kt * km * kvs * ko * ks * kbm
        
        result_message += (
            "\n*Итоговый расчет (с учетом всех водителей):*\n\n"
            f"💰 *Диапазон цены:* {min_cost:,.0f} … {max_cost:,.0f} руб.\n"
            f"\n*Тариф и коэффициенты:*\n\n"
            f"💵 *Базовый тариф* – от {base_tariff_min} до {base_tariff_max} руб.\n"
            f"⭐ *КТ (коэффициент территории):* {kt}\n"
            f"⭐ *КМ (коэффициент мощности):* {km}\n"
            f"⭐ *КВС (коэффициент возраст-стаж):* {kvs}\n"
            f"⭐ *КО (коэффициент ограничения):* {ko}\n"
            f"⭐ *КС (коэффициент сезонности):* {ks}\n"
            f"⭐ *КБМ (коэффициент бонус-малус):* {kbm}\n"
        )

    username = data.get('username', 'unknown')
    timestamp = datetime.now().strftime("%d.%m.%Y в %H:%M")
    
    calculation_data = {
        'owner_type': data['owner_type'],
        'vehicle_type': data['vehicle_type'],
        'region': data['region'],
        'city': data['city'],
        'engine_power': data.get('engine_power', 'не требуется'),
        'usage_period': data['usage_period'],
        'driver_restriction': data['driver_restriction'],
        'kt': kt,
        'km': km,
        'ks': ks,
        'ko': ko,
        'min_cost': round(min_cost, 0),
        'max_cost': round(max_cost, 0),
        'timestamp': timestamp
    }

    if 'insurer_age' in data:
        calculation_data['insurer_age'] = data['insurer_age']
        calculation_data['insurer_experience'] = data['insurer_experience']
        calculation_data['kvs'] = calculate_kvs(data['insurer_age'], data['insurer_experience'])
        calculation_data['kbm'] = data['kbm']

    if 'drivers' in data:
        calculation_data['drivers'] = data['drivers']
        calculation_data['driver_results'] = data['driver_results']
        calculation_data['kvs'] = data['kvs']
        calculation_data['kbm'] = data['kbm']

    if user_id_str not in user_history_osago:
        user_history_osago[user_id_str] = {
            'username': username,
            'osago_calculations': []
        }
    elif 'osago_calculations' not in user_history_osago[user_id_str]:
        user_history_osago[user_id_str]['osago_calculations'] = []

    user_history_osago[user_id_str]['osago_calculations'].append(calculation_data)

    if not USER_HISTORY_PATH_OSAGO.endswith('osago_users.json'):
        raise ValueError("Попытка сохранить данные ОСАГО в неверный файл!")

    save_user_history_osago()
    save_osago_to_excel(user_id_str, calculation_data)

    bot.send_message(message.chat.id, result_message, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
    del user_data[user_id_int]  
    view_osago_calc(message, show_description=False)

def save_osago_to_excel(user_id, calculation):
    file_path = os.path.join(OSAGO_EXCEL_DIR, f"{user_id}_osago.xlsx")
    
    calculations = user_history_osago.get(user_id, {}).get('osago_calculations', [])
    
    columns = [
        "Дата расчета",
        "Владелец ТС",
        "Тип ТС",
        "Регион",
        "Город",
        "Мощность двигателя (л.с.)",
        "Период использования",
        "Лица, допущенные к управлению",
        "Возраст страхователя",
        "Стаж страхователя",
        "КТ",
        "КМ",
        "КВС",
        "КО",
        "КС",
        "КБМ",
        "Минимальная стоимость (руб.)",
        "Максимальная стоимость (руб.)"
    ]
    
    new_calc_data = {
        "Дата расчета": calculation['timestamp'],
        "Владелец ТС": calculation['owner_type'],
        "Тип ТС": calculation['vehicle_type'],
        "Регион": calculation['region'],
        "Город": calculation['city'],
        "Мощность двигателя (л.с.)": calculation['engine_power'],
        "Период использования": calculation['usage_period'],
        "Лица, допущенные к управлению": calculation['driver_restriction'],
        "Возраст страхователя": calculation.get('insurer_age', ''),
        "Стаж страхователя": calculation.get('insurer_experience', ''),
        "КТ": calculation['kt'],
        "КМ": calculation['km'],
        "КВС": calculation.get('kvs', ''),
        "КО": calculation['ko'],
        "КС": calculation['ks'],
        "КБМ": calculation.get('kbm', ''),
        "Минимальная стоимость (руб.)": calculation['min_cost'],
        "Максимальная стоимость (руб.)": calculation['max_cost']
    }

    new_calc_df = pd.DataFrame([new_calc_data], columns=columns)
    
    if os.path.exists(file_path):
        existing_data = pd.read_excel(file_path).dropna(axis=1, how='all')
        existing_data = existing_data.reindex(columns=columns, fill_value=None)
        updated_data = pd.concat([existing_data, new_calc_df], ignore_index=True)
    else:
        updated_data = new_calc_df
    
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
    for row in worksheet.iter_rows(min_col=worksheet.max_column-1, max_col=worksheet.max_column):
        for cell in row:
            cell.border = thick_border
    workbook.save(file_path)

def update_osago_excel_file(user_id):
    file_path = os.path.join(OSAGO_EXCEL_DIR, f"{user_id}_osago.xlsx")
    calculations = user_history_osago.get(user_id, {}).get('osago_calculations', [])

    if not calculations:
        columns = [
            "Дата расчета",
            "Владелец ТС",
            "Тип ТС",
            "Регион",
            "Город",
            "Мощность двигателя (л.с.)",
            "Период использования",
            "Лица, допущенные к управлению",
            "Возраст страхователя",
            "Стаж страхователя",
            "КТ",
            "КМ",
            "КВС",
            "КО",
            "КС",
            "КБМ",
            "Минимальная стоимость (руб.)",
            "Максимальная стоимость (руб.)"
        ]
        df = pd.DataFrame(columns=columns)
        df.to_excel(file_path, index=False)
        return

    columns = [
        "Дата расчета",
        "Владелец ТС",
        "Тип ТС",
        "Регион",
        "Город",
        "Мощность двигателя (л.с.)",
        "Период использования",
        "Лица, допущенные к управлению",
        "Возраст страхователя",
        "Стаж страхователя",
        "КТ",
        "КМ",
        "КВС",
        "КО",
        "КС",
        "КБМ",
        "Минимальная стоимость (руб.)",
        "Максимальная стоимость (руб.)"
    ]

    calc_records = []
    for calc in calculations:
        calc_data = {
            "Дата расчета": calc['timestamp'],
            "Владелец ТС": calc['owner_type'],
            "Тип ТС": calc['vehicle_type'],
            "Регион": calc['region'],
            "Город": calc['city'],
            "Мощность двигателя (л.с.)": calc['engine_power'],
            "Период использования": calc['usage_period'],
            "Лица, допущенные к управлению": calc['driver_restriction'],
            "Возраст страхователя": calc.get('insurer_age', ''),
            "Стаж страхователя": calc.get('insurer_experience', ''),
            "КТ": calc['kt'],
            "КМ": calc['km'],
            "КВС": calc.get('kvs', ''),
            "КО": calc['ko'],
            "КС": calc['ks'],
            "КБМ": calc.get('kbm', ''),
            "Минимальная стоимость (руб.)": calc['min_cost'],
            "Максимальная стоимость (руб.)": calc['max_cost']
        }
        calc_records.append(calc_data)

    df = pd.DataFrame(calc_records, columns=columns)
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
    for row in worksheet.iter_rows(min_row=2, min_col=len(columns)-1, max_col=len(columns)):
        for cell in row:
            cell.border = thick_border
    workbook.save(file_path)

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_ОСАГО (просмотр осаго) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Просмотр ОСАГО")
@check_function_state_decorator('Просмотр ОСАГО')
@track_usage('Просмотр ОСАГО')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_view_osago(message):
    user_id = str(message.from_user.id)
    if user_id not in user_history_osago or 'osago_calculations' not in user_history_osago[user_id] or not user_history_osago[user_id]['osago_calculations']:
        bot.send_message(message.chat.id, "❌ У вас нет сохраненных расчетов ОСАГО!")
        view_osago_calc(message, show_description=False)
        return
    view_osago_calculations(message)

@text_only_handler
def view_osago_calculations(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if user_id not in user_history_osago or 'osago_calculations' not in user_history_osago[user_id] or not user_history_osago[user_id]['osago_calculations']:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов ОСАГО!")
        view_osago_calc(message, show_description=False)
        return

    calculations = user_history_osago[user_id]['osago_calculations']
    message_text = "*Список ваших расчетов ОСАГО:*\n\n"

    for i, calc in enumerate(calculations, 1):
        timestamp = calc['timestamp']
        message_text += f"🕒 *№{i}.* {timestamp}\n"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('ОСАГО в EXCEL')
    markup.add('Вернуться в ОСАГО')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    msg = bot.send_message(chat_id, message_text, parse_mode='Markdown')
    bot.send_message(chat_id, "Введите номера расчетов ОСАГО для просмотра:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_view_osago_selection)

@text_only_handler
def process_view_osago_selection(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return
    if message.text == "ОСАГО в EXCEL":
        send_osago_excel_file(message)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('ОСАГО в EXCEL')
        markup.add('Вернуться в ОСАГО')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(
            chat_id,
            "Введите номера расчетов ОСАГО для просмотра:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_view_osago_selection)
        return

    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    calculations = user_history_osago.get(user_id, {}).get('osago_calculations', [])
    if not calculations:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов ОСАГО!")
        view_osago_calc(message, show_description=False)
        return

    try:
        indices = [int(num.strip()) - 1 for num in message.text.split(',')]
        valid_indices = []
        invalid_indices = []

        for index in indices:
            if 0 <= index < len(calculations):
                valid_indices.append(index)
            else:
                invalid_indices.append(index + 1)

        if not valid_indices and invalid_indices:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add('ОСАГО в EXCEL')
            markup.add('Вернуться в ОСАГО')
            markup.add('Вернуться в калькуляторы')
            markup.add('В главное меню')
            msg = bot.send_message(
                chat_id,
                "Некорректный номер!\nПожалуйста, выберите существующие расчеты из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_view_osago_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(chat_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        for index in valid_indices:
            calc = calculations[index]
            vehicle = next((vt for vt in osago_data['vehicle_types'] if vt['name'] == calc['vehicle_type']), None)
            vehicle_id = vehicle['id'] if vehicle else 2
            base_tariff_min, base_tariff_max = get_base_tariff(vehicle_id)

            required_keys = [
                'owner_type', 'vehicle_type', 'region', 'city', 'engine_power',
                'usage_period', 'driver_restriction', 'kt', 'km', 'ks', 'ko', 'min_cost', 'max_cost'
            ]
            for key in required_keys:
                if key not in calc:
                    bot.send_message(chat_id, f"❌ Данные расчета №{index + 1} устарели или повреждены! Выполните новый расчет!")
                    view_osago_calc(message, show_description=False)
                    return

            if calc['driver_restriction'] == "Без ограничений по водителям":
                result_message = (
                    f"*📊 Итоговый расчет по ОСАГО №{index + 1} (без ограничений):*\n\n"
                    f"*Ваши данные:*\n\n"
                    f"👤 *Владелец ТС:* {calc['owner_type']}\n"
                    f"🚗 *Тип ТС:* {calc['vehicle_type']}\n"
                    f"🌍 *Регион:* {calc['region']}\n"
                    f"🏙 *Город:* {calc['city']}\n"
                    f"💪 *Мощность двигателя:* {calc['engine_power']}\n"
                    f"📅 *Период использования:* {calc['usage_period']}\n"
                    f"🚗 *Лица, допущенные к управлению:* {calc['driver_restriction']}\n"
                    f"🎂 *Возраст страхователя:* {calc.get('insurer_age', 'Не указан')}\n"
                    f"⏳ *Стаж страхователя:* {calc.get('insurer_experience', 'Не указан')}\n"
                    f"\n*Итоговый расчет:*\n\n"
                    f"💰 *Диапазон цены:* {calc['min_cost']:,.0f} … {calc['max_cost']:,.0f} руб.\n"
                    f"\n*Тариф и коэффициенты:*\n\n"
                    f"💵 *Базовый тариф* – от {base_tariff_min} до {base_tariff_max} руб.\n"
                    f"⭐ *КТ (коэффициент территории):* {calc['kt']}\n"
                    f"⭐ *КМ (коэффициент мощности):* {calc['km']}\n"
                    f"⭐ *КВС (коэффициент возраст-стаж):* {calc.get('kvs', 'Не указан')}\n"
                    f"⭐ *КО (коэффициент ограничения):* {calc['ko']}\n"
                    f"⭐ *КС (коэффициент сезонности):* {calc['ks']}\n"
                    f"⭐ *КБМ (коэффициент бонус-малус):* {calc.get('kbm', 'Не указан')}\n"
                    f"\n🕒 *Дата расчета:* {calc['timestamp']}"
                )
            else:
                result_message = (
                    f"*📊 Итоговый расчет по ОСАГО №{index + 1} (с ограничениями):*\n\n"
                    f"*Ваши данные:*\n\n"
                    f"👤 *Владелец ТС:* {calc['owner_type']}\n"
                    f"🚗 *Тип ТС:* {calc['vehicle_type']}\n"
                    f"🌍 *Регион:* {calc['region']}\n"
                    f"🏙 *Город:* {calc['city']}\n"
                    f"💪 *Мощность двигателя:* {calc['engine_power']}\n"
                    f"📅 *Период использования:* {calc['usage_period']}\n"
                    f"🚗 *Лица, допущенные к управлению:* {calc['driver_restriction']}\n"
                    "\n*Данные водителей:*\n"
                )

                for i, driver in enumerate(calc.get('drivers', []), 1):
                    result_message += (
                        f"\n👤 *Водитель №{i}:*\n"
                        f"🎂 *Возраст:* {driver['age']}\n"
                        f"⏳ *Стаж:* {driver['experience']}\n"
                        f"💥 *Аварии:* {driver.get('accidents', 0)}\n"
                    )

                result_message += "\n*Индивидуальные расчеты по водителям:*\n"
                for result in calc.get('driver_results', []):
                    result_message += (
                        f"\n👤 *Водитель №{result['driver_num']}:*\n"
                        f"💰 *Диапазон цены:* {result['min_cost']:,.0f} … {result['max_cost']:,.0f} руб.\n"
                        f"⭐ *КВС:* {result['kvs']}\n"
                        f"⭐ *КБМ:* {result['kbm']}\n"
                    )

                result_message += (
                    f"\n*Итоговый расчет (с учетом всех водителей):*\n\n"
                    f"💰 *Диапазон цены:* {calc['min_cost']:,.0f} … {calc['max_cost']:,.0f} руб.\n"
                    f"\n*Тариф и коэффициенты:*\n\n"
                    f"💵 *Базовый тариф* – от {base_tariff_min} до {base_tariff_max} руб.\n"
                    f"⭐ *КТ (коэффициент территории):* {calc['kt']}\n"
                    f"⭐ *КМ (коэффициент мощности):* {calc['km']}\n"
                    f"⭐ *КВС (коэффициент возраст-стаж):* {calc.get('kvs', 'Не указан')}\n"
                    f"⭐ *КО (коэффициент ограничения):* {calc['ko']}\n"
                    f"⭐ *КС (коэффициент сезонности):* {calc['ks']}\n"
                    f"⭐ *КБМ (коэффициент бонус-малус):* {calc.get('kbm', 'Не указан')}\n"
                    f"\n🕒 *Дата расчета:* {calc['timestamp']}"
                )

            bot.send_message(chat_id, result_message, parse_mode='Markdown')

        view_osago_calc(message, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('ОСАГО в EXCEL')
        markup.add('Вернуться в ОСАГО')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Некорректный ввод!\nВведите числа через запятую", reply_markup=markup)
        bot.register_next_step_handler(msg, process_view_osago_selection)

@bot.message_handler(func=lambda message: message.text == "ОСАГО в EXCEL")
@check_function_state_decorator('ОСАГО в EXCEL')
@track_usage('ОСАГО в EXCEL')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_osago_excel_file(message):
    user_id = str(message.from_user.id)
    excel_file_path = os.path.join(OSAGO_EXCEL_DIR, f"{user_id}_osago.xlsx")

    if os.path.exists(excel_file_path):
        with open(excel_file_path, 'rb') as excel_file:
            bot.send_document(message.chat.id, excel_file)
    else:
        bot.send_message(message.chat.id, "❌ Файл Excel не найден!\nУбедитесь, что у вас есть сохраненные расчеты ОСАГО")
    view_osago_calc(message, show_description=False)

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_ОСАГО (удаление осаго) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Удаление ОСАГО")
@check_function_state_decorator('Удаление ОСАГО')
@track_usage('Удаление ОСАГО')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_delete_osago(message):
    user_id = str(message.from_user.id)
    if user_id not in user_history_osago or 'osago_calculations' not in user_history_osago[user_id] or not user_history_osago[user_id]['osago_calculations']:
        bot.send_message(message.chat.id, "❌ У вас нет сохраненных расчетов ОСАГО!")
        view_osago_calc(message, show_description=False)
        return
    delete_osago_calculations(message)

@text_only_handler
def delete_osago_calculations(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if user_id not in user_history_osago or 'osago_calculations' not in user_history_osago[user_id] or not user_history_osago[user_id]['osago_calculations']:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов ОСАГО!")
        view_osago_calc(message, show_description=False)
        return

    calculations = user_history_osago[user_id]['osago_calculations']
    message_text = "*Список ваших расчетов ОСАГО:*\n\n"

    for i, calc in enumerate(calculations, 1):
        timestamp = calc['timestamp']
        message_text += f"🕒 *№{i}.* {timestamp}\n"

    msg = bot.send_message(chat_id, message_text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_delete_osago_selection)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в ОСАГО')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    bot.send_message(chat_id, "Введите номера для удаления расчетов:", reply_markup=markup)

@text_only_handler
def process_delete_osago_selection(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в ОСАГО":
        view_osago_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    calculations = user_history_osago.get(user_id, {}).get('osago_calculations', [])
    if not calculations:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов ОСАГО!")
        view_osago_calc(message, show_description=False)
        return

    try:
        indices = [int(num.strip()) - 1 for num in message.text.split(',')]
        valid_indices = []
        invalid_indices = []

        for index in indices:
            if 0 <= index < len(calculations):
                valid_indices.append(index)
            else:
                invalid_indices.append(index + 1)

        if not valid_indices and invalid_indices:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add('Вернуться в ОСАГО')
            markup.add('Вернуться в калькуляторы')
            markup.add('В главное меню')
            msg = bot.send_message(chat_id, "Некорректный номер!\nПожалуйста, выберите существующие расчеты из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_delete_osago_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(chat_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        valid_indices.sort(reverse=True)
        for index in valid_indices:
            del calculations[index]

        save_user_history_osago()
        update_osago_excel_file(user_id)
        bot.send_message(chat_id, "✅ Выбранные расчеты ОСАГО успешно удалены!")
        view_osago_calc(message, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в ОСАГО')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Некорректный ввод!\nВведите числа через запятую", reply_markup=markup)
        bot.register_next_step_handler(msg, process_delete_osago_selection)