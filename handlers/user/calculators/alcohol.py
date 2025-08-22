from core.imports import wraps, telebot, types, os, json, re, datetime, timedelta, pd, openpyxl, Workbook, load_workbook, Alignment, Border, Side, Font, PatternFill
from core.bot_instance import bot, BASE_DIR
from .calculators_main import return_to_calculators
from handlers.user.user_main_menu import return_to_menu
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ----------------------------------------------- КАЛЬКУЛЯТОРЫ_АЛКОГОЛЬ --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Алкоголь")
@check_function_state_decorator('Алкоголь')
@track_usage('Алкоголь')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_alc_calc(message, show_description=True):
    global stored_message
    stored_message = message

    description = (
        "ℹ️ *Краткая справка по расчету алкоголя в крови*\n\n"
        "📌 *Расчет алкоголя:*\n"
        "Расчет ведется по следующим данным - *пол, вес, что пили, сколько, как быстро выпили, как давно закончили, еда*\n\n"
        "_P.S. калькулятор не сможет дать 100% точный результат! Если вы выпили, то НИ в коем случае нельзя садиться за руль после алкоголя как минимум в течение суток!!!_"
        "\n\n"
        "📌 *Просмотр алкоголя:*\n"
        "Вы можете посмотреть свои расчеты и вспомнить, что вы пили и сколько\n\n"
        "📌 *Удаление алкоголя:*\n"
        "Вы можете удалить свои расчеты, если они вам не нужны"
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Рассчитать алкоголь', 'Просмотр алкоголя', 'Удаление алкоголя')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')

    if show_description:
        bot.send_message(message.chat.id, description, parse_mode='Markdown')

    bot.send_message(message.chat.id, "Выберите действия из алкоголя:", reply_markup=markup)

ALKO_JSON_PATH = os.path.join(BASE_DIR, 'files', 'files_for_calc', 'files_for_alko', 'alko.json')
USER_HISTORY_PATH_ALKO = os.path.join(BASE_DIR, 'data', 'user', 'calculators', 'alcohol', 'alko_users.json')
ALKO_EXCEL_DIR = os.path.join(BASE_DIR, 'data', 'user', 'calculators', 'alcohol', 'excel')
os.makedirs(os.path.dirname(ALKO_JSON_PATH), exist_ok=True)
os.makedirs(os.path.dirname(USER_HISTORY_PATH_ALKO), exist_ok=True)
os.makedirs(ALKO_EXCEL_DIR, exist_ok=True)

if not os.path.exists(ALKO_JSON_PATH):
    with open(ALKO_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump({}, f, ensure_ascii=False, indent=2)
if not os.path.exists(USER_HISTORY_PATH_ALKO):
    with open(USER_HISTORY_PATH_ALKO, 'w', encoding='utf-8') as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

alko_data = {}
user_history_alko = {}
user_data = {}

def ensure_path_and_file(file_path):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        pass

def load_alko_data():
    global alko_data
    try:
        with open(ALKO_JSON_PATH, 'r', encoding='utf-8') as file:
            alko_data = json.load(file)
        if 'drinks' in alko_data:
            alko_data['drinks'] = sorted(alko_data['drinks'], key=lambda x: x['strength'])
        else:
            pass
        if 'food' not in alko_data:
            pass
        else:
            pass
    except Exception as e:
        alko_data = {}

def load_user_history_alko():
    global user_history_alko
    try:
        if os.path.exists(USER_HISTORY_PATH_ALKO):
            with open(USER_HISTORY_PATH_ALKO, 'r', encoding='utf-8') as db_file:
                user_history_alko = json.load(db_file)
        else:
            user_history_alko = {}
    except Exception as e:
        user_history_alko = {}

def save_user_history_alko():
    try:
        with open(USER_HISTORY_PATH_ALKO, 'w', encoding='utf-8') as db_file:
            json.dump(user_history_alko, db_file, ensure_ascii=False, indent=2)
    except Exception as e:
        pass

ensure_path_and_file(ALKO_JSON_PATH)
ensure_path_and_file(USER_HISTORY_PATH_ALKO)
load_alko_data()
load_user_history_alko()

# ----------------------------------------------- КАЛЬКУЛЯТОРЫ_АЛКОГОЛЬ (рассчитать алкоголь) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Рассчитать алкоголь")
@check_function_state_decorator('Рассчитать алкоголь')
@track_usage('Рассчитать алкоголь')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def start_alcohol_calculation(message):
    if not alko_data.get('drinks'):
        bot.send_message(message.chat.id, "❌ Данные для расчета не найдены!")
        return

    user_id = message.from_user.id
    user_data[user_id] = {'user_id': user_id, 'username': message.from_user.username}

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("Мужской", "Женский")
    markup.add("Вернуться в алкоголь")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Укажите ваш пол:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_gender)

@text_only_handler
def process_gender(message):
    user_id = message.from_user.id
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в алкоголь":
        view_alc_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        gender = message.text.strip().lower()

        if gender not in ['мужской', 'женский']:
            raise ValueError

        user_data[user_id]['gender'] = gender

        markup = types.ReplyKeyboardMarkup(one_time_keyboard=False, resize_keyboard=True)
        markup.add("Вернуться в алкоголь")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")

        msg = bot.send_message(message.chat.id, "Укажите ваш вес в килограммах:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_weight)

    except:
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("Мужской", "Женский")
        markup.add("Вернуться в алкоголь")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nПожалуйста, выберите пол", reply_markup=markup)
        bot.register_next_step_handler(msg, process_gender)

@text_only_handler
def process_weight(message):
    user_id = message.from_user.id
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в алкоголь":
        view_alc_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        weight_str = message.text.strip().replace(',', '.')
        weight = float(weight_str)

        if weight <= 0 or weight > 300:
            raise ValueError

        user_data[user_id]['weight'] = weight

        show_drinks_menu(message)  

    except:
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=False, resize_keyboard=True)
        markup.add("Вернуться в алкоголь")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nПожалуйста, укажите ваш вес в килограммах", reply_markup=markup)
        bot.register_next_step_handler(msg, process_weight)

@text_only_handler
def show_drinks_menu(message):
    chat_id = message.chat.id  
    if not alko_data.get('drinks'):
        bot.send_message(chat_id, "❌ Данные для расчета не найдены!")
        return

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)

    if 'selected_drinks' in user_data[chat_id] and user_data[chat_id]['selected_drinks']:
        markup.row("Убрать последний", "Готово", "Убрать все")
    else:
        markup.row("Готово")

    markup.row("Вернуться в алкоголь")
    markup.add('Вернуться в калькуляторы')
    markup.row("В главное меню")

    drinks_buttons = [drink['name'] for drink in alko_data['drinks']]
    for i in range(0, len(drinks_buttons), 3):
        markup.row(*drinks_buttons[i:i+3])

    if 'selected_drinks' in user_data[chat_id] and user_data[chat_id]['selected_drinks']:
        selected = ", ".join([f"*{drink['name'].lower()}*" for drink in user_data[chat_id]['selected_drinks']])
        msg_text = f"✅ Выбрано: {selected}\n\nПродолжайте выбирать напитки или нажмите *ГОТОВО* для продолжения:"
    else:
        msg_text = "Что вы пили?\nВыбирайте напитки из кнопок:"

    msg = bot.send_message(chat_id, msg_text, reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_drinks_selection)

@text_only_handler
def process_drinks_selection(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в алкоголь":
        view_alc_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    if message.text == "Готово":
        if 'selected_drinks' not in user_data[user_id] or not user_data[user_id]['selected_drinks']:
            bot.send_message(chat_id, "❌ Вы не выбрали ни одного напитка!\nПожалуйста, выберите хотя бы один")
            bot.register_next_step_handler(message, process_drinks_selection)
            return

        process_next_drink_volume(message) 
        return

    elif message.text == "Убрать последний":
        if 'selected_drinks' in user_data[user_id] and user_data[user_id]['selected_drinks']:
            removed_drink = user_data[user_id]['selected_drinks'].pop()
            bot.send_message(chat_id, f"✅ Удален напиток: *{removed_drink['name'].lower()}*!", parse_mode='Markdown')
        show_drinks_menu(message) 
        return

    elif message.text == "Убрать все":
        if 'selected_drinks' in user_data[user_id] and user_data[user_id]['selected_drinks']:
            user_data[user_id]['selected_drinks'] = []
            bot.send_message(chat_id, "✅ Все напитки удалены!")
        show_drinks_menu(message)  
        return

    try:
        drink_name = message.text.strip()
        selected_drink = next((drink for drink in alko_data['drinks'] if drink['name'] == drink_name), None)

        if not selected_drink:
            raise ValueError

        if 'selected_drinks' not in user_data[user_id]:
            user_data[user_id]['selected_drinks'] = []

        if selected_drink not in user_data[user_id]['selected_drinks']:
            user_data[user_id]['selected_drinks'].append(selected_drink)
            bot.send_message(chat_id, f"✅ Добавлен напиток: *{selected_drink['name'].lower()}*!", parse_mode='Markdown')

        show_drinks_menu(message) 

    except ValueError:
        bot.send_message(chat_id, "Некорректный ввод!\nПожалуйста, выбирайте напитки из списка")
        bot.register_next_step_handler(message, process_drinks_selection)

@text_only_handler
def process_next_drink_volume(message):
    chat_id = message.chat.id
    user_id = user_data[chat_id]['user_id']
    if 'current_drink_index' not in user_data[user_id]:
        user_data[user_id]['current_drink_index'] = 0
        user_data[user_id]['drinks_volumes'] = {}

    current_index = user_data[user_id]['current_drink_index']
    if current_index >= len(user_data[user_id]['selected_drinks']):
        show_drinking_speed_menu(message) 
        return

    current_drink = user_data[user_id]['selected_drinks'][current_index]

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)

    liters_buttons = [f"{vol} л" for vol in alko_data['volume_liters'] if vol <= 2.0]
    for i in range(0, len(liters_buttons), 3):
        markup.row(*liters_buttons[i:i+3])

    for cont in alko_data['volume_containers']:
        markup.add(f"{cont['name']} ({cont['volume']} мл)")

    markup.add("Вернуться в алкоголь")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")

    msg = bot.send_message(chat_id, f"Выберите объем для *{current_drink['name'].lower()}*:",
                         reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_volume_selection)

@text_only_handler
def process_volume_selection(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в алкоголь":
        view_alc_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        volume_text = message.text.strip()
        current_index = user_data[user_id]['current_drink_index']
        current_drink = user_data[user_id]['selected_drinks'][current_index]

        if volume_text.endswith(' л'):
            volume_liters = float(volume_text.split(' ')[0])
        elif '(' in volume_text and 'мл' in volume_text:
            volume_ml = int(volume_text.split('(')[1].split(' ')[0])
            volume_liters = volume_ml / 1000
        else:
            raise ValueError

        user_data[user_id]['drinks_volumes'][current_drink['id']] = volume_liters

        user_data[user_id]['current_drink_index'] += 1
        process_next_drink_volume(message)  

    except ValueError:
        current_index = user_data[user_id]['current_drink_index']
        current_drink = user_data[user_id]['selected_drinks'][current_index]
        bot.send_message(chat_id, f"Некорректный ввод!\nПожалуйста, выберите объем для *{current_drink['name'].lower()}*", parse_mode='Markdown')
        bot.register_next_step_handler(message, process_volume_selection)

@text_only_handler
def show_drinking_speed_menu(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(alko_data['drinking_speed'][0]['name'])

    speed_buttons = [speed['name'] for speed in alko_data['drinking_speed'][1:]]
    for i in range(0, len(speed_buttons), 3):
        markup.row(*speed_buttons[i:i+3])

    markup.add("Вернуться в алкоголь")
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")

    msg = bot.send_message(chat_id, "Как быстро выпили?", reply_markup=markup)
    bot.register_next_step_handler(msg, process_drinking_speed)

@text_only_handler
def process_drinking_speed(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в алкоголь":
        view_alc_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        speed_name = message.text.strip()
        speed = next((s for s in alko_data['drinking_speed'] if s['name'] == speed_name), None)

        if not speed:
            raise ValueError

        user_data[user_id]['drinking_speed'] = speed['id']

        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add(alko_data['time_since_last_drink'][0]['name'])
        time_buttons = [time['name'] for time in alko_data['time_since_last_drink'][1:]]
        markup.row(*time_buttons)
        markup.add("Вернуться в алкоголь")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")

        msg = bot.send_message(chat_id, "Как давно закончили пить?", reply_markup=markup)
        bot.register_next_step_handler(msg, process_time_since_last_drink)

    except ValueError:
        bot.send_message(chat_id, "Некорректный ввод!\nПожалуйста, выберите за какое время выпили")
        bot.register_next_step_handler(message, process_drinking_speed)

@text_only_handler
def process_time_since_last_drink(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в алкоголь":
        view_alc_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        time_name = message.text.strip()
        time = next((t for t in alko_data['time_since_last_drink'] if t['name'] == time_name), None)

        if not time:
            raise ValueError

        user_data[user_id]['time_since_last_drink'] = time['id']

        if time['id'] == 0:
            user_data[user_id]['time_since_value'] = 0

            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            food_buttons = [food['name'] for food in alko_data['food']]
            markup.row(*food_buttons)
            markup.add("Вернуться в алкоголь")
            markup.add('Вернуться в калькуляторы')
            markup.add("В главное меню")

            msg = bot.send_message(chat_id, "Что-нибудь ели?", reply_markup=markup)
            bot.register_next_step_handler(msg, process_food)
        else:
            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add("Вернуться в алкоголь")
            markup.add('Вернуться в калькуляторы')
            markup.add("В главное меню")

            time_type = "мин." if time['id'] == 2 else "ч."
            msg = bot.send_message(
                chat_id,
                f"Укажите сколько {time_type} :",
                reply_markup=markup
            )
            bot.register_next_step_handler(msg, process_time_since_value)

    except:
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add(alko_data['time_since_last_drink'][0]['name'])

        time_buttons = [time['name'] for time in alko_data['time_since_last_drink'][1:]]
        markup.row(*time_buttons)

        markup.add("Вернуться в алкоголь")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")

        msg = bot.send_message(chat_id, "Некорректный ввод!\nПожалуйста, выберите вариант", reply_markup=markup)
        bot.register_next_step_handler(msg, process_time_since_last_drink)

@text_only_handler
def process_time_since_value(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в алкоголь":
        view_alc_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        time_value = float(message.text.strip().replace(',', '.'))
        user_data[user_id]['time_since_value'] = time_value

        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        food_buttons = [food['name'] for food in alko_data['food']]
        markup.row(*food_buttons)
        markup.add("Вернуться в алкоголь")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")

        msg = bot.send_message(chat_id, "Что-нибудь ели?", reply_markup=markup)
        bot.register_next_step_handler(msg, process_food)

    except:
        time_id = user_data[user_id]['time_since_last_drink']
        time_type = next((time['name'] for time in alko_data['time_since_last_drink'] if time['id'] == time_id), "")

        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("Вернуться в алкоголь")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")

        msg = bot.send_message(chat_id, f"Некорректный ввод!\nУкажите сколько {time_type}", reply_markup=markup)
        bot.register_next_step_handler(msg, process_time_since_value)

@text_only_handler
def process_food(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в алкоголь":
        view_alc_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        food_name = message.text.strip()
        food_name_normalized = food_name.lower()

        available_foods = [f['name'].lower() for f in alko_data.get('food', [])]

        food = next((f for f in alko_data['food'] if f['name'].lower() == food_name_normalized), None)

        if not food:
            raise ValueError(f"Еда '{food_name}' не найдена в списке. Доступные варианты: {available_foods}")

        if user_id not in user_data:
            raise ValueError(f"Данные пользователя {user_id} не найдены в user_data")

        user_data[user_id]['food'] = food['id']

        calculate_and_show_result(message)

    except Exception as e:
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        food_buttons = [food['name'] for food in alko_data.get('food', [])]
        markup.row(*food_buttons)
        markup.add("Вернуться в алкоголь")
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(chat_id, f"Некорректный ввод или ошибка данных!\nПожалуйста, выберите вариант", reply_markup=markup)
        bot.register_next_step_handler(msg, process_food)

@text_only_handler
def calculate_and_show_result(message):
    chat_id = message.chat.id
    user_id = user_data[chat_id]['user_id']
    data = user_data[user_id]

    r = 0.70 if data['gender'] == 'мужской' else 0.60
    total_alcohol_grams = 0
    for drink in data['selected_drinks']:
        drink_id = drink['id']
        volume_liters = data['drinks_volumes'][drink_id]
        strength = drink['strength'] / 100

        alcohol_grams = volume_liters * 1000 * strength * 0.79
        total_alcohol_grams += alcohol_grams

    c = total_alcohol_grams / (data['weight'] * r)

    drinking_speed = data['drinking_speed']
    if drinking_speed > 1:
        hours_drinking = drinking_speed - 1
        c = c * 0.8

    food_id = data['food']
    if food_id == 2:
        c = c * 0.9
    elif food_id == 3:
        c = c * 0.7

    time_id = data['time_since_last_drink']
    if time_id != 0:
        time_value = data['time_since_value']
        if time_id == 1:
            hours_passed = time_value
        else:
            hours_passed = time_value / 60

        elimination_rate = 0.15 if data['gender'] == 'мужской' else 0.10
        c = max(0, c - (hours_passed * elimination_rate))

    c = round(c, 2)

    if c > 0:
        elimination_rate = 0.15 if data['gender'] == 'мужской' else 0.10
        hours_to_sober = c / elimination_rate
        sober_time = datetime.now() + timedelta(hours=hours_to_sober)
        sober_time_str = sober_time.strftime("%d.%m.%Y в %H:%M")

        recommendations = get_recommendations(c, data['gender'])

        result = (
            f"📊 *Итоговый расчёт*\n\n"
            f"🔹 Сейчас в вашей крови примерно: *{c}%*\n"
            f"🔹 Вы будете трезвы примерно через *{int(hours_to_sober)} ч. {int((hours_to_sober % 1) * 60)} мин.*\n"
            f"🔹 Алкоголь выведется из крови примерно *{sober_time_str}*\n\n"
            f"📌 *Рекомендации:*\n{recommendations}"
        )
    else:
        result = "📊 *Итоговый расчёт*\n\n✅ Вы уже трезвы или алкоголь ещё не поступил в кровь!"

    save_alcohol_calculation_to_history(message, c)
    user_data[user_id] = data
    bot.send_message(chat_id, result, parse_mode='Markdown')
    new_message_for_alko = message
    new_message_for_alko.text = "Алкоголь"  
    view_alc_calc(new_message_for_alko, show_description=False)

def get_recommendations(promille, gender):
    if promille <= 0:
        return "✅ Вы трезвы! Можете управлять транспортным средством!"

    recommendations = []

    if promille > 0.3:
        recommendations.append("⚠️ Внимание! Превышена допустимая норма алкоголя в крови (0.3%). Управление транспортным средством запрещено!")
        recommendations.append("🚫 В таком состоянии вы можете представлять опасность для себя и окружающих!")
    elif promille > 0.16:
        recommendations.append("⚠️ Будьте осторожны! Вы близки к превышению допустимой нормы алкоголя в крови...")
        recommendations.append("🚦 Лучше воздержаться от управления транспортным средством!")
    else:
        recommendations.append("✅ Уровень алкоголя в пределах допустимой нормы, но будьте осторожны!")
        recommendations.append("🔄 Алкоголь еще продолжает всасываться в кровь")

    if promille < 0.3:
        recommendations.append("\n😊 Легкая степень опьянения:")
        recommendations.append("- Вы можете чувствовать расслабленность и улучшение настроения")
        recommendations.append("- Незначительное снижение концентрации внимания")
        recommendations.append("- Минимальное влияние на координацию движений")
    elif promille < 0.6:
        recommendations.append("\n🍷 Умеренное опьянение:")
        recommendations.append("- Нарушения координации становятся заметными")
        recommendations.append("- Снижается скорость реакции")
        recommendations.append("- Может появиться излишняя разговорчивость")
    elif promille < 1.0:
        recommendations.append("\n🚨 Заметное опьянение:")
        recommendations.append("- Явные нарушения координации движений")
        recommendations.append("- Замедленная реакция на внешние раздражители")
        recommendations.append("- Эмоциональная нестабильность")
        recommendations.append("- Ухудшение оценки расстояний и скорости")
    elif promille < 1.5:
        recommendations.append("\n⚠️ Сильное опьянение:")
        recommendations.append("- Серьезные нарушения моторики и мышления")
        recommendations.append("- Несвязная речь")
        recommendations.append("- Проблемы с равновесием")
        recommendations.append("- Высокий риск потери сознания")
    elif promille < 2.0:
        recommendations.append("\n❌ Опасное опьянение:")
        recommendations.append("- Высокий риск для здоровья")
        recommendations.append("- Возможна тошнота и рвота")
        recommendations.append("- Сильное головокружение")
        recommendations.append("- Проблемы с передвижением без помощи")
    else:
        recommendations.append("\n🆘 Критическое опьянение!")
        recommendations.append("- Немедленно прекратите употребление алкоголя")
        recommendations.append("- Обеспечьте постоянное наблюдение")
        recommendations.append("- При ухудшении состояния вызовите врача")
        recommendations.append("- Риск алкогольного отравления")

    recommendations.append("\n💡 Советы по восстановлению:")
    recommendations.append("- Пейте больше воды (1 стакан каждые 30 минут)")
    recommendations.append("- Примите активированный уголь (1 таблетка на 10 кг веса)")
    recommendations.append("- Выпейте крепкий сладкий чай с лимоном")
    recommendations.append("- Примите прохладный душ (не холодный!)")
    recommendations.append("- Съешьте что-то жирное (молоко, сыр, орехи)")
    recommendations.append("- Избегайте кофеина - он усиливает обезвоживание")
    recommendations.append("- Не принимайте лекарства без консультации врача")

    if gender == 'женский':
        recommendations.append("\n♀️ Для женщин:")
        recommendations.append("- Алкоголь выводится медленнее на 15-20%")
        recommendations.append("- Будьте особенно осторожны с дозировками")

    if promille > 0.5:
        recommendations.append("\n🚑 При сильном опьянении:")
        recommendations.append("- Лягте на бок, чтобы избежать аспирации при возможной рвоте")
        recommendations.append("- Не оставляйте человека одного")
        recommendations.append("- Контролируйте дыхание и пульс")
        recommendations.append("- При потере сознания немедленно вызывайте скорую")

    return "\n".join(recommendations)

def format_timestamp(timestamp):
    dt = datetime.strptime(timestamp, "%d.%m.%Y в %H:%M")
    return dt.strftime("%d.%m.%Y в %H:%M")

def save_alcohol_calculation_to_history(message, promille):
    chat_id = message.chat.id
    user_id = str(user_data[chat_id]['user_id'])  
    username = user_data[chat_id].get('username', 'unknown')

    sober_time = datetime.now() + timedelta(hours=promille / 0.15)
    sober_time_str = sober_time.strftime("%d.%m.%Y в %H:%M")

    calculation_data = {
        'timestamp': datetime.now().strftime("%d.%m.%Y в %H:%M"),
        'promille': promille,
        'sober_time': sober_time_str,
        'drinks': [
            {
                'name': drink['name'],
                'volume': user_data[int(user_id)]['drinks_volumes'][drink['id']], 
                'strength': drink['strength']
            } for drink in user_data[int(user_id)]['selected_drinks']
        ],
        'weight': user_data[int(user_id)]['weight'],
        'gender': user_data[int(user_id)]['gender']
    }

    if user_id not in user_history_alko:
        user_history_alko[user_id] = {
            'username': username,
            'alcohol_calculations': []
        }
    elif 'alcohol_calculations' not in user_history_alko[user_id]:
        user_history_alko[user_id]['alcohol_calculations'] = []

    user_history_alko[user_id]['alcohol_calculations'].append(calculation_data)
    
    if not USER_HISTORY_PATH_ALKO.endswith('alko_users.json'):
        raise ValueError("Попытка сохранить данные алкоголя в неверный файл!")
    
    save_user_history_alko()
    save_alcohol_to_excel(user_id, calculation_data)

def save_alcohol_to_excel(user_id, calculation):
    file_path = os.path.join(ALKO_EXCEL_DIR, f"{user_id}_alcohol.xlsx")
    
    calculations = user_history_alko.get(user_id, {}).get('alcohol_calculations', [])
    max_drinks = max(len(calc['drinks']) for calc in calculations) if calculations else len(calculation['drinks'])
    
    columns = ["Дата расчета", "Пол", "Вес (кг)", "Уровень алкоголя (%)", "Время вытрезвления"]
    drink_columns = [f"Напиток {i+1}" for i in range(max_drinks)]
    volume_columns = [f"Объем {i+1} (л)" for i in range(max_drinks)]
    strength_columns = [f"Крепость {i+1} (%)" for i in range(max_drinks)]
    columns.extend(drink_columns + volume_columns + strength_columns)
    
    new_calc_data = {
        "Дата расчета": calculation['timestamp'],
        "Пол": calculation['gender'].capitalize(),
        "Вес (кг)": calculation['weight'],
        "Уровень алкоголя (%)": calculation['promille'],
        "Время вытрезвления": calculation['sober_time']
    }
    
    for i in range(max_drinks):
        drink_key = f"Напиток {i+1}"
        volume_key = f"Объем {i+1} (л)"
        strength_key = f"Крепость {i+1} (%)"
        if i < len(calculation['drinks']):
            new_calc_data[drink_key] = calculation['drinks'][i]['name']
            new_calc_data[volume_key] = calculation['drinks'][i]['volume']
            new_calc_data[strength_key] = calculation['drinks'][i]['strength']
        else:
            new_calc_data[drink_key] = None
            new_calc_data[volume_key] = None
            new_calc_data[strength_key] = None

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
    for row in worksheet.iter_rows(min_col=worksheet.max_column-3*max_drinks+1, max_col=worksheet.max_column):
        for cell in row:
            cell.border = thick_border
    workbook.save(file_path)

def update_alcohol_excel_file(user_id):
    file_path = os.path.join(ALKO_EXCEL_DIR, f"{user_id}_alcohol.xlsx")
    calculations = user_history_alko.get(user_id, {}).get('alcohol_calculations', [])

    if not calculations:
        columns = ["Дата расчета", "Пол", "Вес (кг)", "Уровень алкоголя (%)", "Время вытрезвления"]
        df = pd.DataFrame(columns=columns)
        df.to_excel(file_path, index=False)
        return

    max_drinks = max(len(calc['drinks']) for calc in calculations)

    columns = ["Дата расчета", "Пол", "Вес (кг)", "Уровень алкоголя (%)", "Время вытрезвления"]
    drink_columns = [f"Напиток {i+1}" for i in range(max_drinks)]
    volume_columns = [f"Объем {i+1} (л)" for i in range(max_drinks)]
    strength_columns = [f"Крепость {i+1} (%)" for i in range(max_drinks)]
    columns.extend(drink_columns + volume_columns + strength_columns)

    calc_records = []
    for calc in calculations:
        calc_data = {
            "Дата расчета": calc['timestamp'],
            "Пол": calc['gender'].capitalize(),
            "Вес (кг)": calc['weight'],
            "Уровень алкоголя (%)": calc['promille'],
            "Время вытрезвления": calc['sober_time']
        }
        for i in range(max_drinks):
            drink_key = f"Напиток {i+1}"
            volume_key = f"Объем {i+1} (л)"
            strength_key = f"Крепость {i+1} (%)"
            if i < len(calc['drinks']):
                calc_data[drink_key] = calc['drinks'][i]['name']
                calc_data[volume_key] = calc['drinks'][i]['volume']
                calc_data[strength_key] = calc['drinks'][i]['strength']
            else:
                calc_data[drink_key] = None
                calc_data[volume_key] = None
                calc_data[strength_key] = None
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
    for row in worksheet.iter_rows(min_row=2, min_col=len(columns)-3*max_drinks+1, max_col=len(columns)):
        for cell in row:
            cell.border = thick_border
    workbook.save(file_path)

# ----------------------------------------------- КАЛЬКУЛЯТОРЫ_АЛКОГОЛЬ (просмотр алкоголя) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Просмотр алкоголя")
@check_function_state_decorator('Просмотр алкоголя')
@track_usage('Просмотр алкоголя')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_view_alcohol(message):
    user_id = str(message.from_user.id)  
    if user_id not in user_history_alko or 'alcohol_calculations' not in user_history_alko[user_id] or not user_history_alko[user_id]['alcohol_calculations']:
        bot.send_message(message.chat.id, "❌ У вас нет сохраненных расчетов алкоголя!")
        view_alc_calc(message, show_description=False)
        return
    view_alcohol_calculations(message)

@text_only_handler
def view_alcohol_calculations(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if user_id not in user_history_alko or 'alcohol_calculations' not in user_history_alko[user_id] or not user_history_alko[user_id]['alcohol_calculations']:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов алкоголя!")
        view_alc_calc(message, show_description=False)
        return

    calculations = user_history_alko[user_id]['alcohol_calculations']
    message_text = "*Список ваших расчетов алкоголя:*\n\n"

    for i, calc in enumerate(calculations, 1):
        timestamp = calc['timestamp']
        message_text += f"🕒 №{i}. {timestamp}\n"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Алкоголь в EXCEL")
    markup.add('Вернуться в алкоголь')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    msg = bot.send_message(chat_id, message_text, parse_mode='Markdown')
    bot.send_message(chat_id, "Введите номера расчетов алкоголя для просмотра:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_view_alcohol_selection)

@text_only_handler
def process_view_alcohol_selection(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в алкоголь":
        view_alc_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return
    if message.text == "Алкоголь в EXCEL":
        send_alcohol_excel_file(message)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Алкоголь в EXCEL")
        markup.add('Вернуться в алкоголь')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, "Введите номера расчетов алкоголя для просмотра:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_view_alcohol_selection)
        return

    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    calculations = user_history_alko.get(user_id, {}).get('alcohol_calculations', [])
    if not calculations:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов алкоголя!")
        new_message_for_alko = message
        new_message_for_alko.text = "Алкоголь"  
        view_alc_calc(new_message_for_alko, show_description=False)        
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
            markup.add("Алкоголь в EXCEL")
            markup.add('Вернуться в алкоголь')
            markup.add('Вернуться в калькуляторы')
            markup.add('В главное меню')
            msg = bot.send_message(chat_id, "Некорректный номер!\nПожалуйста, выберите существующие расчеты из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_view_alcohol_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(chat_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        for index in valid_indices:
            calc = calculations[index]
            timestamp = calc['timestamp']
            drinks = "\n".join([f"{i+1}. {drink['name']} ({drink['strength']}%) - {drink['volume']} л." for i, drink in enumerate(calc['drinks'])])
            result = (
                f"📊 *Расчет от {timestamp}*\n\n"
                f"🚹 Ваш пол - {calc['gender']}\n"
                f"🏋️ Ваш вес - {calc['weight']} кг\n\n"
                f"🍷 Вы пили:\n{drinks}\n\n"
                f"🔍 *Итоговый расчет:*\n\n"
                f"🔹 Сейчас в вашей крови примерно: *{calc['promille']}%*\n"
                f"🔹 Вы будете трезвы примерно через *{int(calc['promille'] / 0.15)} ч. {int((calc['promille'] / 0.15 % 1) * 60)} мин.*\n"
                f"🔹 Алкоголь выведется из крови примерно *{calc['sober_time']}*"
            )
            bot.send_message(chat_id, result, parse_mode='Markdown')

        new_message_for_alko = message
        new_message_for_alko.text = "Алкоголь"  
        view_alc_calc(new_message_for_alko, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Алкоголь в EXCEL")
        markup.add('Вернуться в алкоголь')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Некорректный ввод!\nПожалуйста, введите номера расчетов", reply_markup=markup)
        bot.register_next_step_handler(msg, process_view_alcohol_selection)

@bot.message_handler(func=lambda message: message.text == "Алкоголь в EXCEL")
@check_function_state_decorator('Алкоголь в EXCEL')
@track_usage('Алкоголь в EXCEL')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_alcohol_excel_file(message):
    user_id = str(message.from_user.id)
    excel_file_path = os.path.join(ALKO_EXCEL_DIR, f"{user_id}_alcohol.xlsx")

    if os.path.exists(excel_file_path):
        with open(excel_file_path, 'rb') as excel_file:
            bot.send_document(message.chat.id, excel_file)
    else:
        bot.send_message(message.chat.id, "❌ Файл Excel не найден!\nУбедитесь, что у вас есть сохраненные расчеты алкоголя")
    new_message_for_alko = message
    new_message_for_alko.text = "Алкоголь"  
    view_alc_calc(new_message_for_alko, show_description=False)

# ----------------------------------------------- КАЛЬКУЛЯТОРЫ_АЛКОГОЛЬ (удаление алкоголя) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Удаление алкоголя")
@check_function_state_decorator('Удаление алкоголя')
@track_usage('Удаление алкоголя')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_delete_alcohol(message):
    user_id = str(message.from_user.id)  
    if user_id not in user_history_alko or 'alcohol_calculations' not in user_history_alko[user_id] or not user_history_alko[user_id]['alcohol_calculations']:
        bot.send_message(message.chat.id, "❌ У вас нет сохраненных расчетов алкоголя!")
        new_message_for_alko = message
        new_message_for_alko.text = "Алкоголь"  
        view_alc_calc(new_message_for_alko, show_description=False)
        return
    delete_alcohol_calculations(message)

@text_only_handler
def delete_alcohol_calculations(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if user_id not in user_history_alko or 'alcohol_calculations' not in user_history_alko[user_id] or not user_history_alko[user_id]['alcohol_calculations']:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов алкоголя!")
        new_message_for_alko = message
        new_message_for_alko.text = "Алкоголь"  
        view_alc_calc(new_message_for_alko, show_description=False)
        return

    calculations = user_history_alko[user_id]['alcohol_calculations']
    message_text = "*Список ваших расчетов алкоголя:*\n\n"

    for i, calc in enumerate(calculations, 1):
        timestamp = calc['timestamp']
        message_text += f"🕒 №{i}. {timestamp}\n"

    msg = bot.send_message(chat_id, message_text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_delete_alcohol_selection)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в алкоголь')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    bot.send_message(chat_id, "Введите номера для удаления расчетов:", reply_markup=markup)

@text_only_handler
def process_delete_alcohol_selection(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в алкоголь":
        view_alc_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    calculations = user_history_alko.get(user_id, {}).get('alcohol_calculations', [])
    if not calculations:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов алкоголя!")
        new_message_for_alko = message
        new_message_for_alko.text = "Алкоголь"  
        view_alc_calc(new_message_for_alko, show_description=False)
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
            markup.add('Вернуться в алкоголь')
            markup.add('Вернуться в калькуляторы')
            markup.add('В главное меню')
            msg = bot.send_message(chat_id, "Некорректный номер!\nПожалуйста, выберите существующие расчеты из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_delete_alcohol_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(chat_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        valid_indices.sort(reverse=True)
        for index in valid_indices:
            del calculations[index]

        save_user_history_alko()
        update_alcohol_excel_file(user_id)
        bot.send_message(chat_id, "✅ Выбранные расчеты алкоголя успешно удалены!")

        new_message_for_alko = message
        new_message_for_alko.text = "Алкоголь"  
        view_alc_calc(new_message_for_alko, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в алкоголь')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Некорректный ввод!\nПожалуйста, введите номера расчетов", reply_markup=markup)
        bot.register_next_step_handler(msg, process_delete_alcohol_selection)