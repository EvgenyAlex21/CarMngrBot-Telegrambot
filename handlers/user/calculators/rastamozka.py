from core.imports import wraps, telebot, types, os, json, re, requests, datetime, timedelta, pd, load_workbook, openpyxl, Alignment, Border, Side
from core.bot_instance import bot, BASE_DIR
from handlers.user.user_main_menu import return_to_menu
from handlers.user.calculators.calculators_main import return_to_calculators
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ----------------------------------------------- КАЛЬКУЛЯТОРЫ_РАСТАМОЖКА --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Растаможка")
@check_function_state_decorator('Растаможка')
@track_usage('Растаможка')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_rastamozka_calc(message, show_description=True):
    global stored_message
    stored_message = message

    description = (
        "ℹ️ *Краткая справка по расчету таможенных платежей*\n\n"
        "📌 *Расчет растаможки:*\n"
        "Расчет ведется по следующим данным - *кто ввозит, возраст авто, тип двигателя, мощность, объем двигателя, стоимость*\n\n"
        "_P.S. калькулятор предоставляет ориентировочные данные на основе актуальных ставок. Точные суммы зависят от законодательства и могут отличаться!_\n\n"
        "📌 *Просмотр растаможек:*\n"
        "Вы можете посмотреть свои предыдущие расчеты с указанием всех параметров\n\n"
        "📌 *Удаление растаможек:*\n"
        "Вы можете удалить свои расчеты, если они вам больше не нужны"
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Рассчитать растаможку', 'Просмотр растаможек', 'Удаление растаможек')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')

    if show_description:
        bot.send_message(message.chat.id, description, parse_mode='Markdown')

    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

RASTAMOZKA_JSON_PATH = os.path.join(BASE_DIR, 'files', 'files_for_calc', 'files_for_rastamozka', 'rastamozka.json')
USER_HISTORY_PATH_RASTAMOZKA = os.path.join(BASE_DIR, 'data', 'user', 'calculators', 'rastamozka', 'rastamozka_users.json')
RASTAMOZKA_EXCEL_DIR = os.path.join(BASE_DIR, 'data', 'user', 'calculators', 'rastamozka', 'excel')

rastamozka_data = {}
user_history_rastamozka = {}
user_data = {}

def fetch_exchange_rates_cbr():
    url = 'https://www.cbr-xml-daily.ru/daily_json.js'
    try:
        response = requests.get(url)
        data = response.json()
        rates = data['Valute']
        return {
            'USD': rates['USD']['Value'],  
            'EUR': rates['EUR']['Value'],  
            'BYN': rates['BYN']['Value'],  
            'CNY': rates['CNY']['Value'] / 10,  
            'JPY': rates['JPY']['Value'] / 100,  
            'KRW': rates['KRW']['Value'] / 1000, 
            'RUB': 1 
        }
    except Exception as e:
        return get_default_rates()

def get_default_rates():
    return {
        'USD': 83.6813,
        'EUR': 89.6553,
        'BYN': 27.34,
        'CNY': 11.46,
        'JPY': 0.55,
        'KRW': 0.05705,
        'RUB': 1
    }

EXCHANGE_RATES = fetch_exchange_rates_cbr()

def ensure_path_and_file(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def load_rastamozka_data():
    global rastamozka_data
    try:
        with open(RASTAMOZKA_JSON_PATH, 'r', encoding='utf-8') as file:
            rastamozka_data = json.load(file)
    except Exception as e:
        pass

def load_user_history_rastamozka():
    global user_history_rastamozka
    try:
        if os.path.exists(USER_HISTORY_PATH_RASTAMOZKA):
            with open(USER_HISTORY_PATH_RASTAMOZKA, 'r', encoding='utf-8') as db_file:
                user_history_rastamozka = json.load(db_file)
        else:
            user_history_rastamozka = {}
    except Exception as e:
        user_history_rastamozka = {}

def save_user_history_rastamozka():
    try:
        with open(USER_HISTORY_PATH_RASTAMOZKA, 'w', encoding='utf-8') as db_file:
            json.dump(user_history_rastamozka, db_file, ensure_ascii=False, indent=2)
    except Exception as e:
        pass

ensure_path_and_file(RASTAMOZKA_JSON_PATH)
ensure_path_and_file(USER_HISTORY_PATH_RASTAMOZKA)
os.makedirs(RASTAMOZKA_EXCEL_DIR, exist_ok=True)
load_rastamozka_data()
load_user_history_rastamozka()

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_РАСТАМОЖКА (рассчитать растаможку) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Рассчитать растаможку")
@check_function_state_decorator('Рассчитать растаможку')
@track_usage('Рассчитать растаможку')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def start_customs_calculation(message):
    if not rastamozka_data:
        bot.send_message(message.chat.id, "❌ Данные для расчета не найдены!")
        return

    user_id = message.from_user.id
    user_data[user_id] = {'user_id': user_id, 'username': message.from_user.username or 'unknown'}

    global EXCHANGE_RATES
    EXCHANGE_RATES = fetch_exchange_rates_cbr()

    markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    markup.add("Физическое лицо (для себя)", "Физическое лицо (для перепродажи)")
    markup.add("Юридическое лицо")
    markup.add("Вернуться в растаможку")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Кто ввозит автомобиль?", reply_markup=markup)
    bot.register_next_step_handler(msg, process_car_importer_step)

@text_only_handler
def process_car_importer_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в растаможку":
        view_rastamozka_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        car_importer = message.text.strip()
        if car_importer not in rastamozka_data['the_car_is_importing'].values():
            raise ValueError

        user_data[user_id]['car_importer'] = car_importer

        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("До 3 лет", "От 3 до 5 лет")
        markup.add("От 5 до 7 лет", "Более 7 лет")
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        
        msg = bot.send_message(message.chat.id, "Какой возраст у автомобиля?", reply_markup=markup)
        bot.register_next_step_handler(msg, process_car_age_step)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("Физическое лицо (для себя)", "Физическое лицо (для перепродажи)")
        markup.add("Юридическое лицо")
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nПожалуйста, выберите верный вариант", reply_markup=markup)
        bot.register_next_step_handler(msg, process_car_importer_step)

@text_only_handler
def process_car_age_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в растаможку":
        view_rastamozka_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        car_age = message.text.strip()
        if car_age not in rastamozka_data['age_of_the_car'].values():
            raise ValueError

        user_data[user_id]['car_age'] = car_age

        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("Бензиновый", "Дизельный")
        markup.add("Гибридный", "Электрический")
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")

        msg = bot.send_message(message.chat.id, "Какой тип двигателя у автомобиля?", reply_markup=markup)
        bot.register_next_step_handler(msg, process_engine_type_step)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("До 3 лет", "От 3 до 5 лет")
        markup.add("От 5 до 7 лет", "Более 7 лет")
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nПожалуйста, выберите верный вариант", reply_markup=markup)
        bot.register_next_step_handler(msg, process_car_age_step)

@text_only_handler
def process_engine_type_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в растаможку":
        view_rastamozka_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return
    
    try:
        engine_type = message.text.strip()
        if engine_type not in rastamozka_data['engine_type'].values():
            raise ValueError

        user_data[user_id]['engine_type'] = engine_type

        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("ЛС", "кВТ")
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")

        msg = bot.send_message(message.chat.id, "Выберите измерения мощности двигателя:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_engine_type_rastamozka_step)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("Бензиновый", "Дизельный")
        markup.add("Гибридный", "Электрический")
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nПожалуйста, выберите верный вариант", reply_markup=markup)
        bot.register_next_step_handler(msg, process_engine_type_step)

@text_only_handler
def process_engine_type_rastamozka_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в растаможку":
        view_rastamozka_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        engine_power = message.text.strip()
        if engine_power not in ["ЛС", "кВТ"]:
            raise ValueError

        user_data[user_id]['engine_power'] = engine_power

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        
        if engine_power == "кВТ":
            msg = bot.send_message(message.chat.id, 
                                 "Введите мощность двигателя:\n*Подсказка:* _1 кВТ = 1.36 л.с._", 
                                 reply_markup=markup, parse_mode='Markdown')
        else:
            msg = bot.send_message(message.chat.id, 
                                 "Введите мощность двигателя:", 
                                 reply_markup=markup)
        bot.register_next_step_handler(msg, process_engine_power_value_step)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("ЛС", "кВТ")
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nПожалуйста, выберите верный вариант", reply_markup=markup)
        bot.register_next_step_handler(msg, process_engine_type_rastamozka_step)  

@text_only_handler
def process_engine_power_value_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в растаможку":
        view_rastamozka_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        power_value = float(message.text.strip().replace(',', '.'))
        if user_data[user_id]['engine_power'] == "кВТ":
            power_value *= 1.36

        user_data[user_id]['engine_power_value'] = power_value

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        
        msg = bot.send_message(message.chat.id, 
                             "Введите объем двигателя:\n*Подсказка:* _1 л. = 1000 см³_", 
                             reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_engine_volume_step)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nПожалуйста, введите число", reply_markup=markup)
        bot.register_next_step_handler(msg, process_engine_power_value_step)

@text_only_handler
def process_engine_volume_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в растаможку":
        view_rastamozka_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        volume_value = float(message.text.strip().replace(',', '.'))
        user_data[user_id]['engine_volume'] = volume_value

        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("Российский рубль", "Белорусский рубль")
        markup.add("Доллар США", "Евро")
        markup.add("Китайский юань", "Японская йена")
        markup.add("Корейская вона")
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")

        msg = bot.send_message(message.chat.id, "Выберите валюту для покупки:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_car_cost_step)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nПожалуйста, введите число", reply_markup=markup)
        bot.register_next_step_handler(msg, process_engine_volume_step)

@text_only_handler
def process_car_cost_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в растаможку":
        view_rastamozka_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        car_cost_currency = message.text.strip()
        if car_cost_currency not in rastamozka_data['car_cost'].values():
            raise ValueError

        currency_key = {
            "Российский рубль": "RUB",
            "Белорусский рубль": "BYN",
            "Доллар США": "USD",
            "Евро": "EUR",
            "Китайский юань": "CNY",
            "Японская йена": "JPY",
            "Корейская вона": "KRW"
        }.get(car_cost_currency)

        user_data[user_id]['car_cost_currency'] = currency_key

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        
        msg = bot.send_message(message.chat.id, 
                             "Введите стоимость автомобиля:", 
                             reply_markup=markup)
        bot.register_next_step_handler(msg, process_car_cost_value_step)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("Российский рубль", "Белорусский рубль")
        markup.add("Доллар США", "Евро")
        markup.add("Китайский юань", "Японская йена")
        markup.add("Корейская вона")
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nПожалуйста, выберите верный вариант", reply_markup=markup)
        bot.register_next_step_handler(msg, process_car_cost_step)

@text_only_handler
def process_car_cost_value_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в растаможку":
        view_rastamozka_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        car_cost_value = float(message.text.strip().replace(",", "."))
        user_data[user_id]['car_cost_value'] = car_cost_value
        calculate_customs(message)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в растаможку")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nПожалуйста, введите число", reply_markup=markup)
        bot.register_next_step_handler(msg, process_car_cost_value_step)

@text_only_handler
def calculate_customs(message):
    try:
        user_id_int = message.from_user.id 
        user_id_str = str(user_id_int) 
        data = user_data[user_id_int]

        car_cost_rub = data['car_cost_value'] * EXCHANGE_RATES.get(data['car_cost_currency'], 1)

        customs_fee = calculate_customs_fee(car_cost_rub)
        customs_duty = calculate_customs_duty(car_cost_rub, data['engine_volume'], data['car_age'], data['engine_type'], data['car_importer'])
        utilization_fee = calculate_utilization_fee(data['engine_volume'], data['engine_type'], data['car_age'], data['car_importer'])
        excise = calculate_excise(data['engine_power_value'], data['engine_type'], data['car_importer'])
        nds = calculate_nds(car_cost_rub, customs_duty, excise, data['car_importer'])
        total_customs = customs_fee + customs_duty + utilization_fee + excise + nds
        total_cost = car_cost_rub + total_customs

        result_message = (
            "*Итоговый расчет по растаможке:*\n\n"
            "*Ваши данные:*\n\n"
            f"🚗 Импортер: {data['car_importer']}\n"
            f"📅 Возраст авто: {data['car_age']}\n"
            f"🔧 Тип двигателя: {data['engine_type']}\n"
            f"💪 Мощность: {data['engine_power_value']:.1f} ЛС\n"
            f"📏 Объем двигателя: {data['engine_volume']:.1f} см³\n"
            f"💰 Стоимость: {data['car_cost_value']:,.2f} {data['car_cost_currency']}\n\n"
            "*Расчет:*\n\n"
            f"🛃 Таможенный сбор: {customs_fee:,.2f} ₽\n"
            f"🏦 Таможенная пошлина: {customs_duty:,.2f} ₽\n"
            f"♻️ Утилизационный сбор: {utilization_fee:,.2f} ₽\n"
            f"📈 Акциз: {excise:,.2f} ₽\n"
            f"🫰 НДС: {nds:,.2f} ₽\n"
            f"💵 Итого: {total_customs:,.2f} ₽\n"
            f"💰 Стоимость автомобиля + растаможка: {total_cost:,.2f} ₽"
        )

        username = data.get('username', 'unknown')
        timestamp = datetime.now().strftime("%d.%m.%Y в %H:%M")

        calculation_data = {
            'car_importer': data['car_importer'],
            'car_age': data['car_age'],
            'engine_type': data['engine_type'],
            'engine_power': data['engine_power'],
            'engine_power_value': round(data['engine_power_value'], 1),
            'engine_volume': round(data['engine_volume'], 1),
            'car_cost_currency': data['car_cost_currency'],
            'car_cost_value': round(data['car_cost_value'], 2),
            'car_cost_rub': round(car_cost_rub, 2),
            'customs_fee': round(customs_fee, 2),
            'customs_duty': round(customs_duty, 2),
            'utilization_fee': round(utilization_fee, 2),
            'excise': round(excise, 2),
            'nds': round(nds, 2),
            'total_customs': round(total_customs, 2),
            'total_cost': round(total_cost, 2),
            'timestamp': timestamp
        }

        if user_id_str not in user_history_rastamozka:
            user_history_rastamozka[user_id_str] = {
                'username': username,
                'rastamozka_calculations': []
            }
        elif 'rastamozka_calculations' not in user_history_rastamozka[user_id_str]:
            user_history_rastamozka[user_id_str]['rastamozka_calculations'] = []

        user_history_rastamozka[user_id_str]['rastamozka_calculations'].append(calculation_data)

        if not USER_HISTORY_PATH_RASTAMOZKA.endswith('rastamozka_users.json'):
            raise ValueError("Попытка сохранить данные растаможки в неверный файл!")

        save_user_history_rastamozka()
        save_rastamozka_to_excel(user_id_str, calculation_data)

        bot.send_message(message.chat.id, result_message, parse_mode='Markdown', reply_markup=types.ReplyKeyboardRemove())
        del user_data[user_id_int]  
        view_rastamozka_calc(message, show_description=False)

    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при расчете!\nПожалуйста, попробуйте снова")
        view_rastamozka_calc(message, show_description=False)

def calculate_customs_fee(car_cost_rub):
    if car_cost_rub <= 200000:
        return 1067
    elif car_cost_rub <= 450000:
        return 2134
    elif car_cost_rub <= 1200000:
        return 4269
    elif car_cost_rub <= 2700000:
        return 11746
    elif car_cost_rub <= 4200000:
        return 16524
    elif car_cost_rub <= 5500000:
        return 21344
    elif car_cost_rub <= 7000000:
        return 27540
    else:
        return 30000

def calculate_customs_duty(car_cost_rub, engine_volume, car_age, engine_type, car_importer):
    if car_age == "До 3 лет":
        age_category = "до 3 лет"
    elif car_age == "От 3 до 5 лет":
        age_category = "от 3 до 5 лет"
    elif car_age == "От 5 до 7 лет":
        age_category = "от 5 до 7 лет"
    elif car_age == "Более 7 лет":
        age_category = "старше 7 лет"
    else:
        raise ValueError("Некорректный формат возраста автомобиля!")

    if engine_type == "Электрический":
        return car_cost_rub * 0.15

    if car_importer == "Юридическое лицо":
        if engine_type == "Бензиновый":
            if age_category == "до 3 лет":
                if engine_volume <= 3000:
                    return car_cost_rub * 0.15
                else:
                    return car_cost_rub * 0.125
            elif age_category == "от 3 до 5 лет":
                if engine_volume <= 1000:
                    return max(car_cost_rub * 0.2, (0.36 * engine_volume) * EXCHANGE_RATES['EUR'])
                elif engine_volume <= 1500:
                    return max(car_cost_rub * 0.2, (0.4 * engine_volume) * EXCHANGE_RATES['EUR'])
                elif engine_volume <= 1800:
                    return max(car_cost_rub * 0.2, (0.36 * engine_volume) * EXCHANGE_RATES['EUR'])
                elif engine_volume <= 2300:
                    return max(car_cost_rub * 0.2, (0.44 * engine_volume) * EXCHANGE_RATES['EUR'])
                elif engine_volume <= 2800:
                    return max(car_cost_rub * 0.2, (0.44 * engine_volume) * EXCHANGE_RATES['EUR'])
                elif engine_volume <= 3000:
                    return max(car_cost_rub * 0.2, (0.44 * engine_volume) * EXCHANGE_RATES['EUR'])
                else:
                    return max(car_cost_rub * 0.2, (0.8 * engine_volume) * EXCHANGE_RATES['EUR'])
            elif age_category == "от 5 до 7 лет":
                if engine_volume <= 1000:
                    return max(car_cost_rub * 0.2, (0.36 * engine_volume) * EXCHANGE_RATES['EUR'])
                elif engine_volume <= 1500:
                    return max(car_cost_rub * 0.2, (0.4 * engine_volume) * EXCHANGE_RATES['EUR'])
                elif engine_volume <= 1800:
                    return max(car_cost_rub * 0.2, (0.36 * engine_volume) * EXCHANGE_RATES['EUR'])
                elif engine_volume <= 2300:
                    return max(car_cost_rub * 0.2, (0.44 * engine_volume) * EXCHANGE_RATES['EUR'])
                elif engine_volume <= 2800:
                    return max(car_cost_rub * 0.2, (0.44 * engine_volume) * EXCHANGE_RATES['EUR'])
                elif engine_volume <= 3000:
                    return max(car_cost_rub * 0.2, (0.44 * engine_volume) * EXCHANGE_RATES['EUR'])
                else:
                    return max(car_cost_rub * 0.2, (0.8 * engine_volume) * EXCHANGE_RATES['EUR'])
            else:  
                if engine_volume <= 1000:
                    return (1.4 * engine_volume) * EXCHANGE_RATES['EUR']
                elif engine_volume <= 1500:
                    return (1.5 * engine_volume) * EXCHANGE_RATES['EUR']
                elif engine_volume <= 1800:
                    return (1.6 * engine_volume) * EXCHANGE_RATES['EUR']
                elif engine_volume <= 2300:
                    return (2.2 * engine_volume) * EXCHANGE_RATES['EUR']
                elif engine_volume <= 2800:
                    return (2.2 * engine_volume) * EXCHANGE_RATES['EUR']
                elif engine_volume <= 3000:
                    return (2.2 * engine_volume) * EXCHANGE_RATES['EUR']
                else:
                    return (3.2 * engine_volume) * EXCHANGE_RATES['EUR']
        elif engine_type == "Дизельный":
            if age_category == "до 3 лет":
                return car_cost_rub * 0.15
            elif age_category == "от 3 до 5 лет":
                if engine_volume <= 1500:
                    return max(car_cost_rub * 0.2, (0.32 * engine_volume) * EXCHANGE_RATES['EUR'])
                elif engine_volume <= 2500:
                    return max(car_cost_rub * 0.2, (0.4 * engine_volume) * EXCHANGE_RATES['EUR'])
                else:
                    return max(car_cost_rub * 0.2, (0.8 * engine_volume) * EXCHANGE_RATES['EUR'])
            elif age_category == "от 5 до 7 лет":
                if engine_volume <= 1500:
                    return max(car_cost_rub * 0.2, (0.32 * engine_volume) * EXCHANGE_RATES['EUR'])
                elif engine_volume <= 2500:
                    return max(car_cost_rub * 0.2, (0.4 * engine_volume) * EXCHANGE_RATES['EUR'])
                else:
                    return max(car_cost_rub * 0.2, (0.8 * engine_volume) * EXCHANGE_RATES['EUR'])
            else:  
                if engine_volume <= 1500:
                    return (1.5 * engine_volume) * EXCHANGE_RATES['EUR']
                elif engine_volume <= 2500:
                    return (2.2 * engine_volume) * EXCHANGE_RATES['EUR']
                else:
                    return (3.2 * engine_volume) * EXCHANGE_RATES['EUR']
    else:
        if age_category == "до 3 лет":
            car_cost_eur = car_cost_rub / EXCHANGE_RATES['EUR']
            if car_cost_eur <= 8500:
                return max(0.54 * car_cost_rub, (2.5 * engine_volume) * EXCHANGE_RATES['EUR'])
            elif car_cost_eur <= 16700:
                return max(0.48 * car_cost_rub, (3.5 * engine_volume) * EXCHANGE_RATES['EUR'])
            elif car_cost_eur <= 42300:
                return max(0.48 * car_cost_rub, (5.5 * engine_volume) * EXCHANGE_RATES['EUR'])
            elif car_cost_eur <= 84500:
                return max(0.48 * car_cost_rub, (7.5 * engine_volume) * EXCHANGE_RATES['EUR'])
            elif car_cost_eur <= 169000:
                return max(0.48 * car_cost_rub, (15 * engine_volume) * EXCHANGE_RATES['EUR'])
            else:
                return max(0.48 * car_cost_rub, (20 * engine_volume) * EXCHANGE_RATES['EUR'])
        elif age_category == "от 3 до 5 лет":
            if engine_volume <= 1000:
                return (1.5 * engine_volume) * EXCHANGE_RATES['EUR']
            elif engine_volume <= 1500:
                return (1.7 * engine_volume) * EXCHANGE_RATES['EUR']
            elif engine_volume <= 1800:
                return (2.5 * engine_volume) * EXCHANGE_RATES['EUR']
            elif engine_volume <= 2300:
                return (2.7 * engine_volume) * EXCHANGE_RATES['EUR']
            elif engine_volume <= 3000:
                return (3.0 * engine_volume) * EXCHANGE_RATES['EUR']
            else:
                return (3.6 * engine_volume) * EXCHANGE_RATES['EUR']
        else:  
            if engine_volume <= 1000:
                return (3.0 * engine_volume) * EXCHANGE_RATES['EUR']
            elif engine_volume <= 1500:
                return (3.2 * engine_volume) * EXCHANGE_RATES['EUR']
            elif engine_volume <= 1800:
                return (3.5 * engine_volume) * EXCHANGE_RATES['EUR']
            elif engine_volume <= 2300:
                return (4.8 * engine_volume) * EXCHANGE_RATES['EUR']
            elif engine_volume <= 3000:
                return (5.0 * engine_volume) * EXCHANGE_RATES['EUR']
            else:
                return (5.7 * engine_volume) * EXCHANGE_RATES['EUR']

def calculate_utilization_fee(engine_volume, engine_type, car_age, car_importer):
    base_rate = 20000 if engine_type != "Электрический" else 0
    coefficient = get_utilization_coefficient(engine_volume, engine_type, car_age, car_importer)
    return base_rate * coefficient

def get_utilization_coefficient(engine_volume, engine_type, car_age, car_importer):
    if car_age == "До 3 лет":
        age_category = "до 3 лет"
    elif car_age == "От 3 до 5 лет":
        age_category = "от 3 до 5 лет"
    elif car_age == "От 5 до 7 лет":
        age_category = "от 5 до 7 лет"
    elif car_age == "Более 7 лет":
        age_category = "старше 7 лет"
    else:
        raise ValueError("Некорректный формат возраста автомобиля!")

    if engine_type == "Электрический":
        if car_importer == "Юридическое лицо":
            return 33.37 if age_category == "до 3 лет" else 58.7
        return 0.17 if age_category == "до 3 лет" else 0.26

    if car_importer == "Юридическое лицо":
        if age_category == "до 3 лет":
            if engine_volume <= 1000:
                return 9.01
            elif engine_volume <= 2000:
                return 33.37
            elif engine_volume <= 3000:
                return 93.77
            elif engine_volume <= 3500:
                return 107.67
            else:
                return 137.11
        elif age_category == "от 3 до 5 лет":
            if engine_volume <= 1000:
                return 23.0
            elif engine_volume <= 2000:
                return 58.7
            elif engine_volume <= 3000:
                return 141.97
            elif engine_volume <= 3500:
                return 165.84
            else:
                return 180.24
        elif age_category == "от 5 до 7 лет":
            if engine_volume <= 1000:
                return 25.0  
            elif engine_volume <= 2000:
                return 60.0  
            elif engine_volume <= 3000:
                return 145.0  
            elif engine_volume <= 3500:
                return 170.0 
            else:
                return 185.0  
        else: 
            if engine_volume <= 1000:
                return 27.0  
            elif engine_volume <= 2000:
                return 62.0  
            elif engine_volume <= 3000:
                return 150.0  
            elif engine_volume <= 3500:
                return 175.0  
            else:
                return 190.0  
    else: 
        if age_category == "до 3 лет":
            if engine_volume <= 1000:
                return 0.17
            elif engine_volume <= 2000:
                return 0.17
            elif engine_volume <= 3000:
                return 0.17
            elif engine_volume <= 3500:
                return 107.67
            else:
                return 137.11
        else:  
            if engine_volume <= 1000:
                return 0.26
            elif engine_volume <= 2000:
                return 0.26
            elif engine_volume <= 3000:
                return 0.26
            elif engine_volume <= 3500:
                return 165.84
            else:
                return 180.24

def calculate_excise(engine_power, engine_type, car_importer):
    if car_importer == "Физическое лицо (для себя)":
        return 0

    if engine_type == "Электрический":
        return 0

    if engine_power <= 90:
        return 0
    elif engine_power <= 150:
        return 61 * engine_power
    elif engine_power <= 200:
        return 583 * engine_power
    elif engine_power <= 300:
        return 955 * engine_power
    elif engine_power <= 400:
        return 1628 * engine_power
    elif engine_power <= 500:
        return 1685 * engine_power
    else:
        return 1740 * engine_power

def calculate_nds(car_cost_rub, customs_duty, excise, car_importer):
    if car_importer in ["Физическое лицо (для себя)", "Физическое лицо (для перепродажи)"]:
        return 0
    return (car_cost_rub + customs_duty + excise) * 0.2

def save_rastamozka_to_excel(user_id, calculation):
    file_path = os.path.join(RASTAMOZKA_EXCEL_DIR, f"{user_id}_rastamozka.xlsx")
    
    calculations = user_history_rastamozka.get(user_id, {}).get('rastamozka_calculations', [])
    
    columns = [
        "Дата расчета",
        "Импортер",
        "Возраст авто",
        "Тип двигателя",
        "Мощность (ЛС)",
        "Объем двигателя (см³)",
        "Стоимость автомобиля",
        "Валюта",
        "Стоимость в рублях",
        "Таможенный сбор (₽)",
        "Таможенная пошлина (₽)",
        "Утилизационный сбор (₽)",
        "Акциз (₽)",
        "НДС (₽)",
        "Итого растаможка (₽)",
        "Итоговая стоимость (₽)"
    ]
    
    new_calc_data = {
        "Дата расчета": calculation['timestamp'],
        "Импортер": calculation['car_importer'],
        "Возраст авто": calculation['car_age'],
        "Тип двигателя": calculation['engine_type'],
        "Мощность (ЛС)": calculation['engine_power_value'],
        "Объем двигателя (см³)": calculation['engine_volume'],
        "Стоимость автомобиля": calculation['car_cost_value'],
        "Валюта": calculation['car_cost_currency'],
        "Стоимость в рублях": calculation['car_cost_rub'],
        "Таможенный сбор (₽)": calculation['customs_fee'],
        "Таможенная пошлина (₽)": calculation['customs_duty'],
        "Утилизационный сбор (₽)": calculation['utilization_fee'],
        "Акциз (₽)": calculation['excise'],
        "НДС (₽)": calculation['nds'],
        "Итого растаможка (₽)": calculation['total_customs'],
        "Итоговая стоимость (₽)": calculation['total_cost']
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
    for row in worksheet.iter_rows(min_col=worksheet.max_column-4, max_col=worksheet.max_column):
        for cell in row:
            cell.border = thick_border
    workbook.save(file_path)

def update_rastamozka_excel_file(user_id):
    file_path = os.path.join(RASTAMOZKA_EXCEL_DIR, f"{user_id}_rastamozka.xlsx")
    calculations = user_history_rastamozka.get(user_id, {}).get('rastamozka_calculations', [])

    if not calculations:
        columns = [
            "Дата расчета",
            "Импортер",
            "Возраст авто",
            "Тип двигателя",
            "Мощность (ЛС)",
            "Объем двигателя (см³)",
            "Стоимость автомобиля",
            "Валюта",
            "Стоимость в рублях",
            "Таможенный сбор (₽)",
            "Таможенная пошлина (₽)",
            "Утилизационный сбор (₽)",
            "Акциз (₽)",
            "НДС (₽)",
            "Итого растаможка (₽)",
            "Итоговая стоимость (₽)"
        ]
        df = pd.DataFrame(columns=columns)
        df.to_excel(file_path, index=False)
        return

    columns = [
        "Дата расчета",
        "Импортер",
        "Возраст авто",
        "Тип двигателя",
        "Мощность (ЛС)",
        "Объем двигателя (см³)",
        "Стоимость автомобиля",
        "Валюта",
        "Стоимость в рублях",
        "Таможенный сбор (₽)",
        "Таможенная пошлина (₽)",
        "Утилизационный сбор (₽)",
        "Акциз (₽)",
        "НДС (₽)",
        "Итого растаможка (₽)",
        "Итоговая стоимость (₽)"
    ]

    calc_records = []
    for calc in calculations:
        calc_data = {
            "Дата расчета": calc['timestamp'],
            "Импортер": calc['car_importer'],
            "Возраст авто": calc['car_age'],
            "Тип двигателя": calc['engine_type'],
            "Мощность (ЛС)": calc['engine_power_value'],
            "Объем двигателя (см³)": calc['engine_volume'],
            "Стоимость автомобиля": calc['car_cost_value'],
            "Валюта": calc['car_cost_currency'],
            "Стоимость в рублях": calc['car_cost_rub'],
            "Таможенный сбор (₽)": calc['customs_fee'],
            "Таможенная пошлина (₽)": calc['customs_duty'],
            "Утилизационный сбор (₽)": calc['utilization_fee'],
            "Акциз (₽)": calc['excise'],
            "НДС (₽)": calc['nds'],
            "Итого растаможка (₽)": calc['total_customs'],
            "Итоговая стоимость (₽)": calc['total_cost']
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
    for row in worksheet.iter_rows(min_row=2, min_col=len(columns)-4, max_col=len(columns)):
        for cell in row:
            cell.border = thick_border
    workbook.save(file_path)

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_РАСТАМОЖКА (просмотр растаможек) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Просмотр растаможек")
@check_function_state_decorator('Просмотр растаможек')
@track_usage('Просмотр растаможек')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_view_rastamozka(message):
    user_id = str(message.from_user.id)
    if user_id not in user_history_rastamozka or 'rastamozka_calculations' not in user_history_rastamozka[user_id] or not user_history_rastamozka[user_id]['rastamozka_calculations']:
        bot.send_message(message.chat.id, "❌ У вас нет сохраненных расчетов растаможки!")
        view_rastamozka_calc(message, show_description=False)
        return
    view_rastamozka_calculations(message)

@text_only_handler
def view_rastamozka_calculations(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if user_id not in user_history_rastamozka or 'rastamozka_calculations' not in user_history_rastamozka[user_id] or not user_history_rastamozka[user_id]['rastamozka_calculations']:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов растаможки!")
        view_rastamozka_calc(message, show_description=False)
        return

    calculations = user_history_rastamozka[user_id]['rastamozka_calculations']
    message_text = "*Список ваших расчетов растаможки:*\n\n"

    for i, calc in enumerate(calculations, 1):
        timestamp = calc['timestamp']
        message_text += f"🕒 *№{i}.* {timestamp}\n"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Растаможка в EXCEL')
    markup.add('Вернуться в растаможку')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    msg = bot.send_message(chat_id, message_text, parse_mode='Markdown')
    bot.send_message(chat_id, "Введите номера расчетов растаможки для просмотра:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_view_rastamozka_selection)

@text_only_handler
def process_view_rastamozka_selection(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в растаможку":
        view_rastamozka_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return
    if message.text == "Растаможка в EXCEL":
        send_rastamozka_excel_file(message)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Растаможка в EXCEL')
        markup.add('Вернуться в растаможку')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, "Введите номера расчетов растаможки для просмотра:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_view_rastamozka_selection)
        return

    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    calculations = user_history_rastamozka.get(user_id, {}).get('rastamozka_calculations', [])
    if not calculations:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов растаможки!")
        view_rastamozka_calc(message, show_description=False)
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
            markup.add('Растаможка в EXCEL')
            markup.add('Вернуться в растаможку')
            markup.add('Вернуться в калькуляторы')
            markup.add('В главное меню')
            msg = bot.send_message(
                chat_id,
                "Некорректный номер!\nПожалуйста, выберите существующие расчеты из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_view_rastamozka_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(chat_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        for index in valid_indices:
            calc = calculations[index]
            required_keys = [
                'car_importer', 'car_age', 'engine_type', 'engine_power_value',
                'engine_volume', 'car_cost_value', 'car_cost_currency', 'customs_fee',
                'customs_duty', 'utilization_fee', 'excise', 'nds', 'total_customs', 'total_cost'
            ]
            for key in required_keys:
                if key not in calc:
                    bot.send_message(chat_id, f"❌ Данные расчета №{index + 1} устарели или повреждены! Выполните новый расчет!")
                    view_rastamozka_calc(message, show_description=False)
                    return

            result = (
                f"📊 *Расчет растаможки №{index + 1}. {calc['timestamp']}*\n\n"
                f"*Ваши данные:*\n\n"
                f"🚗 Импортер: {calc['car_importer']}\n"
                f"📅 Возраст авто: {calc['car_age']}\n"
                f"🔧 Тип двигателя: {calc['engine_type']}\n"
                f"💪 Мощность: {calc['engine_power_value']:.1f} ЛС\n"
                f"📏 Объем двигателя: {calc['engine_volume']:.1f} см³\n"
                f"💰 Стоимость: {calc['car_cost_value']:,.2f} {calc['car_cost_currency']}\n\n"
                f"*Расчет:*\n\n"
                f"🛃 Таможенный сбор: {calc['customs_fee']:,.2f} ₽\n"
                f"🏦 Таможенная пошлина: {calc['customs_duty']:,.2f} ₽\n"
                f"♻️ Утилизационный сбор: {calc['utilization_fee']:,.2f} ₽\n"
                f"📈 Акциз: {calc['excise']:,.2f} ₽\n"
                f"🫰 НДС: {calc['nds']:,.2f} ₽\n"
                f"💵 Итого: {calc['total_customs']:,.2f} ₽\n"
                f"💰 Стоимость автомобиля + растаможка: {calc['total_cost']:,.2f} ₽"
            )
            bot.send_message(chat_id, result, parse_mode='Markdown')

        view_rastamozka_calc(message, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Растаможка в EXCEL')
        markup.add('Вернуться в растаможку')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Некорректный ввод!\nВведите числа через запятую", reply_markup=markup)
        bot.register_next_step_handler(msg, process_view_rastamozka_selection)

@bot.message_handler(func=lambda message: message.text == "Растаможка в EXCEL")
@check_function_state_decorator('Растаможка в EXCEL')
@track_usage('Растаможка в EXCEL')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_rastamozka_excel_file(message):
    user_id = str(message.from_user.id)
    excel_file_path = os.path.join(RASTAMOZKA_EXCEL_DIR, f"{user_id}_rastamozka.xlsx")

    if os.path.exists(excel_file_path):
        with open(excel_file_path, 'rb') as excel_file:
            bot.send_document(message.chat.id, excel_file)
    else:
        bot.send_message(message.chat.id, "❌ Файл Excel не найден!\nУбедитесь, что у вас есть сохраненные расчеты растаможки")
    view_rastamozka_calc(message, show_description=False)

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_РАСТАМОЖКА (удаление растаможек) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Удаление растаможек")
@check_function_state_decorator('Удаление растаможек')
@track_usage('Удаление растаможек')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_delete_rastamozka(message):
    user_id = str(message.from_user.id)
    if user_id not in user_history_rastamozka or 'rastamozka_calculations' not in user_history_rastamozka[user_id] or not user_history_rastamozka[user_id]['rastamozka_calculations']:
        bot.send_message(message.chat.id, "❌ У вас нет сохраненных расчетов растаможки!")
        view_rastamozka_calc(message, show_description=False)
        return
    delete_rastamozka_calculations(message)

@text_only_handler
def delete_rastamozka_calculations(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if user_id not in user_history_rastamozka or 'rastamozka_calculations' not in user_history_rastamozka[user_id] or not user_history_rastamozka[user_id]['rastamozka_calculations']:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов растаможки!")
        view_rastamozka_calc(message, show_description=False)
        return

    calculations = user_history_rastamozka[user_id]['rastamozka_calculations']
    message_text = "*Список ваших расчетов растаможки:*\n\n"

    for i, calc in enumerate(calculations, 1):
        timestamp = calc['timestamp']
        message_text += f"🕒 *№{i}.* {timestamp}\n"

    msg = bot.send_message(chat_id, message_text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_delete_rastamozka_selection)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в растаможку')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    bot.send_message(chat_id, "Введите номера для удаления расчетов:", reply_markup=markup)

@text_only_handler
def process_delete_rastamozka_selection(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в растаможку":
        view_rastamozka_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    calculations = user_history_rastamozka.get(user_id, {}).get('rastamozka_calculations', [])
    if not calculations:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов растаможки!")
        view_rastamozka_calc(message, show_description=False)
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
            markup.add('Вернуться в растаможку')
            markup.add('Вернуться в калькуляторы')
            markup.add('В главное меню')
            msg = bot.send_message(chat_id, "Некорректный номер!\nПожалуйста, выберите существующие расчеты из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_delete_rastamozka_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(chat_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        valid_indices.sort(reverse=True)
        for index in valid_indices:
            del calculations[index]

        save_user_history_rastamozka()
        update_rastamozka_excel_file(user_id)
        bot.send_message(chat_id, "✅ Выбранные расчеты растаможки успешно удалены!")
        view_rastamozka_calc(message, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в растаможку')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Некорректный ввод!\nВведите числа через запятую", reply_markup=markup)
        bot.register_next_step_handler(msg, process_delete_rastamozka_selection)