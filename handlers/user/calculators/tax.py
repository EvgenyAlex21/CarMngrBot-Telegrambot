from core.imports import wraps, telebot, types, os, json, re, requests, datetime, timedelta, ReplyKeyboardMarkup, ReplyKeyboardRemove, pd, load_workbook, Alignment, Border, Side, Font, PatternFill, openpyxl
from core.bot_instance import bot, BASE_DIR
from handlers.user.user_main_menu import return_to_menu
from handlers.user.calculators.calculators_main import return_to_calculators
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_НАЛОГ --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Налог")
@check_function_state_decorator('Налог')
@track_usage('Налог')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_nalog_calc(message, show_description=True):
    global stored_message
    stored_message = message

    description = (
        "ℹ️ *Краткая справка по расчету транспортного налога*\n\n"
        "📌 *Расчет налога:*\n"
        "Расчет ведется по следующим данным - *регион, тип ТС, мощность двигателя, количество месяцев владения, наличие льгот, стоимость ТС (для авто дороже 10 млн руб.)*\n\n"
        "_P.S. Если хотите узнать без калькулятора, следуйте по формуле:_\n"
        "_Сумма налога (руб.) = налоговая база (л.с.) × ставка (руб.) × (количество полных месяцев владения / 12 месяцев)_\n\n"
        "📌 *Просмотр налогов:*\n"
        "Вы можете посмотреть свои предыдущие расчеты с указанием всех параметров\n\n"
        "📌 *Удаление налогов:*\n"
        "Вы можете удалить свои расчеты, если они вам больше не нужны"
    )

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Рассчитать налог', 'Просмотр налогов', 'Удаление налогов')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')

    if show_description:
        bot.send_message(message.chat.id, description, parse_mode='Markdown')

    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

NALOG_JSON_PATH = os.path.join(BASE_DIR, 'files', 'files_for_calc', 'files_for_nalog', 'nalog.json')
USER_HISTORY_PATH_NALOG = os.path.join(BASE_DIR, 'data', 'user', 'calculators', 'nalog', 'nalog_users.json')
PERECHEN_AUTO_PATH = os.path.join(BASE_DIR, 'files', 'files_for_calc', 'files_for_nalog', 'auto_10mln_rub_2025.json')
TRANSPORT_TAX_BASE_PATH = os.path.join(BASE_DIR, 'files', 'files_for_calc', 'files_for_nalog', 'transport_tax_{year}.json')
NALOG_EXCEL_DIR = os.path.join(BASE_DIR, 'data', 'user', 'calculators', 'nalog', 'excel')

def ensure_path_and_file(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

ensure_path_and_file(NALOG_JSON_PATH)
ensure_path_and_file(USER_HISTORY_PATH_NALOG)
ensure_path_and_file(PERECHEN_AUTO_PATH)
ensure_path_and_file(TRANSPORT_TAX_BASE_PATH.format(year=2025))
os.makedirs(NALOG_EXCEL_DIR, exist_ok=True)

nalog_data = {}
user_history_nalog = {}
user_data = {}
expensive_cars = []
tax_rates = {}
available_years = [2021, 2022, 2023, 2024, 2025]

def load_nalog_data():
    global nalog_data
    try:
        with open(NALOG_JSON_PATH, 'r', encoding='utf-8') as file:
            nalog_data = json.load(file)
    except Exception as e:
        pass

def load_user_history_nalog():
    global user_history_nalog
    try:
        if os.path.exists(USER_HISTORY_PATH_NALOG):
            with open(USER_HISTORY_PATH_NALOG, 'r', encoding='utf-8') as db_file:
                user_history_nalog = json.load(db_file)
        else:
            user_history_nalog = {}
            save_user_history_nalog()
    except Exception as e:
        user_history_nalog = {}

def save_user_history_nalog():
    try:
        with open(USER_HISTORY_PATH_NALOG, 'w', encoding='utf-8') as db_file:
            json.dump(user_history_nalog, db_file, ensure_ascii=False, indent=2)
    except Exception as e:
        pass

def load_expensive_cars():
    global expensive_cars
    try:
        with open(PERECHEN_AUTO_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file) 
            car_data = []
            for section in data:
                cost_range = "10-15" if "10 миллионов до 15 миллионов рублей" in section['subtitle'] else "15+"
                for car in section['cars']:
                    car_data.append({
                        "brand": car['brand'],
                        "model": car['model'],
                        "engine_type": car['engine_type'],
                        "engine_volume": str(car['engine_displacement']) if car['engine_displacement'] is not None else "N/A",
                        "years_passed": car['age'],
                        "cost_range": cost_range
                    })
            expensive_cars = car_data
    except json.JSONDecodeError as e:
        pass
    except Exception as e:
        pass

def load_tax_rates(year):
    global tax_rates
    try:
        tax_file_path = TRANSPORT_TAX_BASE_PATH.format(year=year)
        if not os.path.exists(tax_file_path):
            raise FileNotFoundError(f"Файл {tax_file_path} не найден!")
        with open(tax_file_path, 'r', encoding='utf-8') as file:
            tax_rates = json.load(file)
    except Exception as e:
        tax_rates = {}

load_nalog_data()
load_user_history_nalog()
load_expensive_cars()
load_tax_rates(2025)

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_НАЛОГ (рассчитать налог) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Рассчитать налог")
@check_function_state_decorator('Рассчитать налог')
@track_usage('Рассчитать налог')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def start_tax_calculation(message):
    if not nalog_data:
        bot.send_message(message.chat.id, "❌ Данные для расчета не найдены!")
        return

    user_id = message.from_user.id
    user_data[user_id] = {'user_id': user_id, 'username': message.from_user.username or 'unknown'}

    markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    regions = list(tax_rates.keys())
    for i in range(0, len(regions), 2):
        if i + 1 < len(regions):
            markup.row(regions[i], regions[i + 1])
        else:
            markup.add(regions[i])
    markup.add("Вернуться в налог")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Выберите ваш регион:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_nalog_region_step)

@text_only_handler
def process_nalog_region_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в налог":
        view_nalog_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    region_name = message.text.strip()
    if region_name not in tax_rates:
        markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        regions = list(tax_rates.keys())
        for i in range(0, len(regions), 2):
            if i + 1 < len(regions):
                markup.row(regions[i], regions[i + 1])
            else:
                markup.add(regions[i])
        markup.add("Вернуться в налог")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный регион!\nВыберите регион из списка:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_nalog_region_step)
        return

    user_data[user_id]['region'] = region_name

    markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    years = [str(year) for year in available_years]
    for i in range(0, len(years), 2):
        if i + 1 < len(years):
            markup.row(years[i], years[i + 1])
        else:
            markup.add(years[i])
    markup.add("Вернуться в налог")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Выберите год для налога:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_year_step)

@text_only_handler
def process_year_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в налог":
        view_nalog_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        year = int(message.text)
        if year not in available_years:
            raise ValueError
        user_data[user_id]['year'] = year
        load_tax_rates(year)
        if not tax_rates:
            bot.send_message(message.chat.id, f"❌ Данные за `{year}` год отсутствуют!", parse_mode='Markdown')
            new_message_for_nalog = message
            new_message_for_nalog.text = "Налог"  
            view_nalog_calc(new_message_for_nalog, show_description=False)
            return
    except ValueError:
        markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        years = [str(year) for year in available_years]
        for i in range(0, len(years), 2):
            if i + 1 < len(years):
                markup.row(years[i], years[i + 1])
            else:
                markup.add(years[i])
        markup.add("Вернуться в налог")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, f"Некорректный год!\nВыберите год из списка: {', '.join(years)}", reply_markup=markup)
        bot.register_next_step_handler(msg, process_year_step)
        return

    markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    months = [str(i) for i in range(1, 13)]
    for i in range(0, len(months), 2):
        if i + 1 < len(months):
            markup.row(months[i], months[i + 1])
        else:
            markup.add(months[i])
    markup.add("Вернуться в налог")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Количество месяцев владения ТС:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_ownership_months_step)

@text_only_handler
def process_ownership_months_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в налог":
        view_nalog_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        months = int(message.text)
        if months < 1 or months > 12:
            raise ValueError
        user_data[user_id]['ownership_months'] = months
    except ValueError:
        markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        months = [str(i) for i in range(1, 13)]
        for i in range(0, len(months), 2):
            if i + 1 < len(months):
                markup.row(months[i], months[i + 1])
            else:
                markup.add(months[i])
        markup.add("Вернуться в налог")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число от 1 до 12", reply_markup=markup)
        bot.register_next_step_handler(msg, process_ownership_months_step)
        return

    markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    vehicle_types = list(tax_rates[user_data[user_id]['region']].keys())
    for i in range(0, len(vehicle_types), 2):
        if i + 1 < len(vehicle_types):
            markup.row(vehicle_types[i], vehicle_types[i + 1])
        else:
            markup.add(vehicle_types[i])
    markup.add("Вернуться в налог")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Вид транспортного средства:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_vehicle_type_nalog_step)

@text_only_handler
def process_vehicle_type_nalog_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в налог":
        view_nalog_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    vehicle_type = message.text.strip()
    if vehicle_type not in tax_rates[user_data[user_id]['region']]:
        markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        vehicle_types = list(tax_rates[user_data[user_id]['region']].keys())
        for i in range(0, len(vehicle_types), 2):
            if i + 1 < len(vehicle_types):
                markup.row(vehicle_types[i], vehicle_types[i + 1])
            else:
                markup.add(vehicle_types[i])
        markup.add("Вернуться в налог")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный тип ТС!\nВыберите тип из списка:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_vehicle_type_nalog_step)
        return

    user_data[user_id]['vehicle_type'] = vehicle_type
    user_data[user_id]['metric'] = "Мощность двигателя (л.с.)"

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Вернуться в налог")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, f"Введите мощность двигателя (л.с.):", reply_markup=markup)
    bot.register_next_step_handler(msg, process_metric_value_step)

@text_only_handler
def process_metric_value_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в налог":
        view_nalog_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        value = float(message.text.replace(',', '.'))
        user_data[user_id]['metric_value'] = value
    except ValueError:
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число")
        bot.register_next_step_handler(msg, process_metric_value_step)
        return

    if user_data[user_id]['vehicle_type'] == "Легковые автомобили":
        markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("Да", "Нет")
        markup.add("Вернуться в налог")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "ТС стоит больше 10 миллионов рублей?", reply_markup=markup)
        bot.register_next_step_handler(msg, process_expensive_car_step)
    else:
        proceed_to_benefits(message)

@text_only_handler
def process_expensive_car_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в налог":
        view_nalog_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    if message.text not in ["Да", "Нет"]:
        markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("Да", "Нет")
        markup.add("Вернуться в налог")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите да или нет", reply_markup=markup)
        bot.register_next_step_handler(msg, process_expensive_car_step)
        return

    user_data[user_id]['is_expensive'] = message.text == "Да"

    if user_data[user_id]['is_expensive']:
        brands = sorted(set(car['brand'] for car in expensive_cars))
        brand_list = "\n".join(f"📜 №{i+1}. {brand}" for i, brand in enumerate(brands))
        user_data[user_id]['brands'] = brands

        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в налог")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, f"*Марка ТС:*\n\n{brand_list}\n\nВведите номер марки:", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_brand_step)
    else:
        proceed_to_benefits(message)

@text_only_handler
def process_brand_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в налог":
        view_nalog_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        brand_idx = int(message.text) - 1
        brands = user_data[user_id]['brands']
        if brand_idx < 0 or brand_idx >= len(brands):
            raise ValueError
        selected_brand = brands[brand_idx]
        user_data[user_id]['selected_brand'] = selected_brand

        models = sorted(set(car['model'] for car in expensive_cars if car['brand'] == selected_brand))
        model_list = "\n".join(f"✨ №{i+1}. {model}" for i, model in enumerate(models))
        user_data[user_id]['models'] = models

        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в налог")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, f"*Модель ТС:*\n\n{model_list}\n\nВведите номер модели:", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_model_step)
    except ValueError:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в налог")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, f"Некорректный номер!\nВведите число от 1 до {len(user_data[user_id]['brands'])}", reply_markup=markup)
        bot.register_next_step_handler(msg, process_brand_step)

@text_only_handler
def process_model_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в налог":
        view_nalog_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        model_idx = int(message.text) - 1
        models = user_data[user_id]['models']
        if model_idx < 0 or model_idx >= len(models):
            raise ValueError
        selected_model = models[model_idx]
        user_data[user_id]['selected_model'] = selected_model

        selected_brand = user_data[user_id]['selected_brand']
        years_passed_list = sorted(set(car['years_passed'] for car in expensive_cars if car['brand'] == selected_brand and car['model'] == selected_model))
        years = []
        current_year = user_data[user_id]['year']
        for years_passed in years_passed_list:
            if "от" in years_passed and "до" in years_passed:
                match = re.search(r'от (\d+) до (\d+)', years_passed)
                if match:
                    start, end = map(int, match.groups())
                    for y in range(start, end + 1):
                        years.append(current_year - y)
            elif "до" in years_passed:
                match = re.search(r'до (\d+)', years_passed)
                if match:
                    end = int(match.group(1))
                    for y in range(0, end + 1):
                        years.append(current_year - y)
            else:
                match = re.search(r'(\d+)', years_passed)
                if match:
                    y = int(match.group(1))
                    years.append(current_year - y)
        years = sorted(set(years))
        user_data[user_id]['years'] = years
        year_list = "\n".join(f"📅 №{i+1}. {year}" for i, year in enumerate(years))

        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в налог")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, f"*Год выпуска:*\n\n{year_list}\n\nВведите номер года:", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_year_of_manufacture_step)
    except ValueError:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в налог")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, f"Некорректный номер!\nВведите число от 1 до {len(user_data[user_id]['models'])}", reply_markup=markup)
        bot.register_next_step_handler(msg, process_model_step)

@text_only_handler
def process_year_of_manufacture_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в налог":
        view_nalog_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return
    
    try:
        year_idx = int(message.text) - 1
        years = user_data[user_id]['years']
        if year_idx < 0 or year_idx >= len(years):
            raise ValueError
        selected_year = years[year_idx]
        user_data[user_id]['year_of_manufacture'] = selected_year
        proceed_to_benefits(message)
    except ValueError:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Вернуться в налог")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, f"Некорректный номер!\nВведите число от 1 до {len(user_data[user_id]['years'])}", reply_markup=markup)
        bot.register_next_step_handler(msg, process_year_of_manufacture_step)

@text_only_handler
def proceed_to_benefits(message):
    user_id = message.from_user.id
    markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    benefits = ["Нет", "Да"]
    markup.add(*benefits)
    markup.add("Вернуться в налог")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Имею ли я право на льготу?", reply_markup=markup)
    bot.register_next_step_handler(msg, process_benefits_step)

@text_only_handler
def process_benefits_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в налог":
        view_nalog_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    benefit_desc = message.text.strip()
    if benefit_desc not in ["Нет", "Да"]:
        markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        benefits = ["Нет", "Да"]
        markup.add(*benefits)
        markup.add("Вернуться в налог")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите да или нет", reply_markup=markup)
        bot.register_next_step_handler(msg, process_benefits_step)
        return

    user_data[user_id]['benefit'] = benefit_desc
    calculate_tax(message)

@text_only_handler
def calculate_tax(message):
    user_id_int = message.from_user.id  
    user_id_str = str(user_id_int)  
    data = user_data[user_id_int]

    tax_base = data['metric_value']
    region = data['region']
    vehicle_type = data['vehicle_type']
    rates = tax_rates[region][vehicle_type]

    rate = 0.0
    for condition, value in rates.items():
        if "до" in condition:
            limit = float(condition.split()[1])
            if tax_base <= limit:
                rate = value
                break
        elif "свыше" in condition:
            limit = float(condition.split()[1])
            if tax_base > limit:
                rate = value

    ownership_months = data['ownership_months']
    months_coefficient = ownership_months / 12
    benefit = data['benefit']
    benefit_coefficient = 1.0 if benefit == "Нет" else 0.0
    increasing_coefficient = 1.0
    expensive_details = "Нет"

    if data.get('is_expensive', False):
        years_passed = data['year'] - data['year_of_manufacture']
        if years_passed <= 3:
            increasing_coefficient = 3.0
            expensive_details = f"Да (коэффициент 3.0, до 3 лет с выпуска: {data['year_of_manufacture']})"
        elif years_passed <= 5:
            increasing_coefficient = 2.0
            expensive_details = f"Да (коэффициент 2.0, 3-5 лет с выпуска: {data['year_of_manufacture']})"
        elif years_passed <= 10:
            increasing_coefficient = 1.5
            expensive_details = f"Да (коэффициент 1.5, 5-10 лет с выпуска: {data['year_of_manufacture']})"

    tax = tax_base * rate * months_coefficient * increasing_coefficient * benefit_coefficient
    result_message = (
        f"*📊 Итоговый расчет транспортного налога*\n\n"
        f"*Ваши данные:*\n\n"
        f"🌍 *Регион:* {data['region']}\n"
        f"📅 *Год:* {data['year']}\n"
        f"🚗 *Тип ТС:* {data['vehicle_type']}\n"
        f"💪 *Мощность двигателя:* {tax_base} л.с.\n"
        f"⏳ *Месяцев владения:* {ownership_months}\n"
        f"💰 *ТС дороже 10 млн руб.:* {expensive_details}\n"
        f"⭐ *Льготы:* {benefit}\n\n"
        f"*Итоговый расчет:*\n\n"
        f"💰 *Сумма налога:* {tax:,.2f} руб.\n\n"
        f"*Параметры расчета:*\n\n"
        f"📏 *Налоговая база:* {tax_base} л.с.\n"
        f"💵 *Ставка:* {rate} руб./л.с.\n"
        f"⭐ *Коэффициент владения:* {months_coefficient:.2f} ({ownership_months}/12)\n"
        f"⭐ *Повышающий коэффициент:* {increasing_coefficient}\n"
        f"⭐ *Льготный коэффициент:* {benefit_coefficient}"
    )

    timestamp = datetime.now().strftime("%d.%m.%Y в %H:%M")
    calculation_data = {
        'region': data['region'],
        'year': data['year'],
        'vehicle_type': data['vehicle_type'],
        'engine_power': tax_base,
        'ownership_months': ownership_months,
        'is_expensive': data.get('is_expensive', False),
        'benefit': benefit,
        'tax': tax,
        'rate': rate,
        'months_coefficient': months_coefficient,
        'increasing_coefficient': increasing_coefficient,
        'benefit_coefficient': benefit_coefficient,
        'timestamp': timestamp
    }
    if data.get('is_expensive', False):
        calculation_data['year_of_manufacture'] = data['year_of_manufacture']
        calculation_data['selected_brand'] = data['selected_brand']
        calculation_data['selected_model'] = data['selected_model']

    if user_id_str not in user_history_nalog:
        user_history_nalog[user_id_str] = {
            'username': data.get('username', 'unknown'),
            'nalog_calculations': []
        }
    elif 'nalog_calculations' not in user_history_nalog[user_id_str]:
        user_history_nalog[user_id_str]['nalog_calculations'] = []

    user_history_nalog[user_id_str]['nalog_calculations'].append(calculation_data)
    
    if not USER_HISTORY_PATH_NALOG.endswith('nalog_users.json'):
        raise ValueError("Попытка сохранить данные налога в неверный файл!")
    
    save_user_history_nalog()
    save_nalog_to_excel(user_id_str, calculation_data)

    bot.send_message(message.chat.id, result_message, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
    
    del user_data[user_id_int]  
    new_message_for_nalog = message
    new_message_for_nalog.text = "Налог"  
    view_nalog_calc(new_message_for_nalog, show_description=False)

def save_nalog_to_excel(user_id, calculation):
    file_path = os.path.join(NALOG_EXCEL_DIR, f"{user_id}_nalog.xlsx")
    
    calculations = user_history_nalog.get(user_id, {}).get('nalog_calculations', [])
    
    columns = [
        "Дата расчета",
        "Регион",
        "Год",
        "Тип ТС",
        "Мощность двигателя (л.с.)",
        "Месяцев владения",
        "ТС дороже 10 млн руб.",
        "Марка ТС",
        "Модель ТС",
        "Год выпуска",
        "Льготы",
        "Сумма налога (руб.)",
        "Ставка (руб./л.с.)",
        "Коэффициент владения",
        "Повышающий коэффициент",
        "Льготный коэффициент"
    ]
    
    expensive_details = "Нет"
    if calculation['is_expensive']:
        years_passed = calculation['year'] - calculation['year_of_manufacture']
        if years_passed <= 3:
            expensive_details = f"Да (коэффициент 3.0, до 3 лет с выпуска: {calculation['year_of_manufacture']})"
        elif years_passed <= 5:
            expensive_details = f"Да (коэффициент 2.0, 3-5 лет с выпуска: {calculation['year_of_manufacture']})"
        elif years_passed <= 10:
            expensive_details = f"Да (коэффициент 1.5, 5-10 лет с выпуска: {calculation['year_of_manufacture']})"

    new_calc_data = {
        "Дата расчета": calculation['timestamp'],
        "Регион": calculation['region'],
        "Год": calculation['year'],
        "Тип ТС": calculation['vehicle_type'],
        "Мощность двигателя (л.с.)": calculation['engine_power'],
        "Месяцев владения": calculation['ownership_months'],
        "ТС дороже 10 млн руб.": expensive_details,
        "Марка ТС": calculation.get('selected_brand', ''),
        "Модель ТС": calculation.get('selected_model', ''),
        "Год выпуска": calculation.get('year_of_manufacture', ''),
        "Льготы": calculation['benefit'],
        "Сумма налога (руб.)": calculation['tax'],
        "Ставка (руб./л.с.)": calculation['rate'],
        "Коэффициент владения": calculation['months_coefficient'],
        "Повышающий коэффициент": calculation['increasing_coefficient'],
        "Льготный коэффициент": calculation['benefit_coefficient']
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

def update_nalog_excel_file(user_id):
    file_path = os.path.join(NALOG_EXCEL_DIR, f"{user_id}_nalog.xlsx")
    calculations = user_history_nalog.get(user_id, {}).get('nalog_calculations', [])

    if not calculations:
        columns = [
            "Дата расчета",
            "Регион",
            "Год",
            "Тип ТС",
            "Мощность двигателя (л.с.)",
            "Месяцев владения",
            "ТС дороже 10 млн руб.",
            "Марка ТС",
            "Модель ТС",
            "Год выпуска",
            "Льготы",
            "Сумма налога (руб.)",
            "Ставка (руб./л.с.)",
            "Коэффициент владения",
            "Повышающий коэффициент",
            "Льготный коэффициент"
        ]
        df = pd.DataFrame(columns=columns)
        df.to_excel(file_path, index=False)
        return

    columns = [
        "Дата расчета",
        "Регион",
        "Год",
        "Тип ТС",
        "Мощность двигателя (л.с.)",
        "Месяцев владения",
        "ТС дороже 10 млн руб.",
        "Марка ТС",
        "Модель ТС",
        "Год выпуска",
        "Льготы",
        "Сумма налога (руб.)",
        "Ставка (руб./л.с.)",
        "Коэффициент владения",
        "Повышающий коэффициент",
        "Льготный коэффициент"
    ]

    calc_records = []
    for calc in calculations:
        expensive_details = "Нет"
        if calc['is_expensive']:
            years_passed = calc['year'] - calc['year_of_manufacture']
            if years_passed <= 3:
                expensive_details = f"Да (коэффициент 3.0, до 3 лет с выпуска: {calc['year_of_manufacture']})"
            elif years_passed <= 5:
                expensive_details = f"Да (коэффициент 2.0, 3-5 лет с выпуска: {calc['year_of_manufacture']})"
            elif years_passed <= 10:
                expensive_details = f"Да (коэффициент 1.5, 5-10 лет с выпуска: {calc['year_of_manufacture']})"

        calc_data = {
            "Дата расчета": calc['timestamp'],
            "Регион": calc['region'],
            "Год": calc['year'],
            "Тип ТС": calc['vehicle_type'],
            "Мощность двигателя (л.с.)": calc['engine_power'],
            "Месяцев владения": calc['ownership_months'],
            "ТС дороже 10 млн руб.": expensive_details,
            "Марка ТС": calc.get('selected_brand', ''),
            "Модель ТС": calc.get('selected_model', ''),
            "Год выпуска": calc.get('year_of_manufacture', ''),
            "Льготы": calc['benefit'],
            "Сумма налога (руб.)": calc['tax'],
            "Ставка (руб./л.с.)": calc['rate'],
            "Коэффициент владения": calc['months_coefficient'],
            "Повышающий коэффициент": calc['increasing_coefficient'],
            "Льготный коэффициент": calc['benefit_coefficient']
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

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_НАЛОГ (просмотр налогов) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Просмотр налогов")
@check_function_state_decorator('Просмотр налогов')
@track_usage('Просмотр налогов')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_view_nalog(message):
    user_id = str(message.from_user.id)
    if user_id not in user_history_nalog or 'nalog_calculations' not in user_history_nalog[user_id] or not user_history_nalog[user_id]['nalog_calculations']:
        bot.send_message(message.chat.id, "❌ У вас нет сохраненных расчетов налога!")
        new_message_for_nalog = message
        new_message_for_nalog.text = "Налог"
        view_nalog_calc(new_message_for_nalog, show_description=False)
        return
    view_nalog_calculations(message)

@text_only_handler
def view_nalog_calculations(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if user_id not in user_history_nalog or 'nalog_calculations' not in user_history_nalog[user_id] or not user_history_nalog[user_id]['nalog_calculations']:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов налога!")
        new_message_for_nalog = message
        new_message_for_nalog.text = "Налог"
        view_nalog_calc(new_message_for_nalog, show_description=False)
        return

    calculations = user_history_nalog[user_id]['nalog_calculations']
    message_text = "*Список ваших расчетов налога:*\n\n"

    for i, calc in enumerate(calculations, 1):
        timestamp = calc['timestamp']
        message_text += f"🕒 *№{i}.* {timestamp}\n"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Налог в EXCEL')
    markup.add('Вернуться в налог')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    msg = bot.send_message(chat_id, message_text, parse_mode='Markdown')
    bot.send_message(chat_id, "Введите номера расчетов шин для просмотра:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_view_nalog_selection)

@text_only_handler
def process_view_nalog_selection(message):
    chat_id = message.chat.id 
    user_id = str(message.from_user.id)

    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в налог":
        new_message_for_nalog = message
        new_message_for_nalog.text = "Налог"
        view_nalog_calc(new_message_for_nalog, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return
    if message.text == "Налог в EXCEL":
        send_nalog_excel_file(message)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Налог в EXCEL')
        markup.add('Вернуться в налог')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Введите номера расчетов для просмотра:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_view_nalog_selection)
        return

    calculations = user_history_nalog.get(user_id, {}).get('nalog_calculations', [])
    if not calculations:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов налога!")
        new_message_for_nalog = message
        new_message_for_nalog.text = "Налог"
        view_nalog_calc(new_message_for_nalog, show_description=False)
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
            markup.add('Налог в EXCEL')
            markup.add('Вернуться в налог')
            markup.add('Вернуться в калькуляторы')
            markup.add('В главное меню')
            msg = bot.send_message(chat_id, "Некорректный ввод!\nВыберите существующие номера расчетов из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_view_nalog_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(chat_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        for index in valid_indices:
            calc = calculations[index]
            expensive_details = "Нет"
            if calc['is_expensive']:
                years_passed = calc['year'] - calc['year_of_manufacture']
                if years_passed <= 3:
                    expensive_details = f"Да (коэффициент 3.0, до 3 лет с выпуска: {calc['year_of_manufacture']})"
                elif years_passed <= 5:
                    expensive_details = f"Да (коэффициент 2.0, 3-5 лет с выпуска: {calc['year_of_manufacture']})"
                elif years_passed <= 10:
                    expensive_details = f"Да (коэффициент 1.5, 5-10 лет с выпуска: {calc['year_of_manufacture']})"

            result_message = (
                f"*📊 Итоговый расчет транспортного налога №{index + 1}*\n\n"
                f"*Ваши данные:*\n\n"
                f"🌍 *Регион:* {calc['region']}\n"
                f"📅 *Год:* {calc['year']}\n"
                f"🚗 *Тип ТС:* {calc['vehicle_type']}\n"
                f"💪 *Мощность двигателя:* {calc['engine_power']} л.с.\n"
                f"⏳ *Месяцев владения:* {calc['ownership_months']}\n"
                f"💰 *ТС дороже 10 млн руб.:* {expensive_details}\n"
                f"⭐ *Льготы:* {calc['benefit']}\n\n"
                f"*Итоговый расчет:*\n\n"
                f"💰 *Сумма налога:* {calc['tax']:,.2f} руб.\n\n"
                f"*Параметры расчета:*\n\n"
                f"📏 *Налоговая база:* {calc['engine_power']} л.с.\n"
                f"💵 *Ставка:* {calc['rate']} руб./л.с.\n"
                f"⭐ *Коэффициент владения:* {calc['months_coefficient']:.2f} ({calc['ownership_months']}/12)\n"
                f"⭐ *Повышающий коэффициент:* {calc['increasing_coefficient']}\n"
                f"⭐ *Льготный коэффициент:* {calc['benefit_coefficient']}\n\n"
                f"🕒 *Дата расчета:* {calc['timestamp']}"
            )
            bot.send_message(chat_id, result_message, parse_mode='Markdown')

        new_message_for_nalog = message
        new_message_for_nalog.text = "Налог"
        view_nalog_calc(new_message_for_nalog, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Налог в EXCEL')
        markup.add('Вернуться в налог')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Некорректный ввод!\nВведите числа через запятую", reply_markup=markup)
        bot.register_next_step_handler(msg, process_view_nalog_selection)

@bot.message_handler(func=lambda message: message.text == "Налог в EXCEL")
@check_function_state_decorator('Налог в EXCEL')
@track_usage('Налог в EXCEL')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_nalog_excel_file(message):
    user_id = str(message.from_user.id)
    excel_file_path = os.path.join(NALOG_EXCEL_DIR, f"{user_id}_nalog.xlsx")

    if os.path.exists(excel_file_path):
        with open(excel_file_path, 'rb') as excel_file:
            bot.send_document(message.chat.id, excel_file)
    else:
        bot.send_message(message.chat.id, "❌ Файл Excel не найден!\nУбедитесь, что у вас есть сохраненные расчеты налога")
    new_message_for_nalog = message
    new_message_for_nalog.text = "Налог"
    view_nalog_calc(new_message_for_nalog, show_description=False)

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_НАЛОГ (удаление налогов) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Удаление налогов")
@check_function_state_decorator('Удаление налогов')
@track_usage('Удаление налогов')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_delete_nalog(message):
    user_id = str(message.from_user.id)
    if user_id not in user_history_nalog or 'nalog_calculations' not in user_history_nalog[user_id] or not user_history_nalog[user_id]['nalog_calculations']:
        bot.send_message(message.chat.id, "❌ У вас нет сохраненных расчетов налога!")
        new_message_for_nalog = message
        new_message_for_nalog.text = "Налог"  
        view_nalog_calc(new_message_for_nalog, show_description=False)
        return
    delete_nalog_calculations(message)

@text_only_handler
def delete_nalog_calculations(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if user_id not in user_history_nalog or 'nalog_calculations' not in user_history_nalog[user_id] or not user_history_nalog[user_id]['nalog_calculations']:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов налога!")
        new_message_for_nalog = message
        new_message_for_nalog.text = "Налог"  
        view_nalog_calc(new_message_for_nalog, show_description=False)
        return

    calculations = user_history_nalog[user_id]['nalog_calculations']
    message_text = "*Список ваших расчетов налога:*\n\n"

    for i, calc in enumerate(calculations, 1):
        timestamp = calc['timestamp']
        message_text += f"🕒 *№{i}.* {timestamp}\n"

    msg = bot.send_message(chat_id, message_text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_delete_nalog_selection)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в налог')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    bot.send_message(chat_id, "Введите номера для удаления расчетов:", reply_markup=markup)

@text_only_handler
def process_delete_nalog_selection(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в налог":
        view_nalog_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    calculations = user_history_nalog.get(user_id, {}).get('nalog_calculations', [])
    if not calculations:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов налога!")
        new_message_for_nalog = message
        new_message_for_nalog.text = "Налог"  
        view_nalog_calc(new_message_for_nalog, show_description=False)
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
            markup.add('Вернуться в налог')
            markup.add('Вернуться в калькуляторы')
            markup.add('В главное меню')
            msg = bot.send_message(chat_id, "Некорректный ввод!\nВыберите существующие номера расчетов из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_delete_nalog_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(chat_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        valid_indices.sort(reverse=True)
        for index in valid_indices:
            del calculations[index]

        save_user_history_nalog()
        update_nalog_excel_file(user_id)
        bot.send_message(chat_id, "✅ Выбранные расчеты налога успешно удалены!")
        new_message_for_nalog = message
        new_message_for_nalog.text = "Налог"  
        view_nalog_calc(new_message_for_nalog, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в налог')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Некорректный ввод!\nВведите числа через запятую", reply_markup=markup)
        bot.register_next_step_handler(msg, process_delete_nalog_selection)