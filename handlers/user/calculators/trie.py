from core.imports import wraps, telebot, types, os, json, re, requests, datetime, timedelta, ReplyKeyboardMarkup, ReplyKeyboardRemove, pd, Workbook, load_workbook, Alignment, Border, Side, Font, PatternFill, openpyxl
from core.bot_instance import bot, BASE_DIR
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from handlers.user.user_main_menu import return_to_menu
from handlers.user.calculators.calculators_main import return_to_calculators
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_ШИНЫ --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Шины")
@check_function_state_decorator('Шины')
@track_usage('Шины')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_tire_calc(message, show_description=True):
    description = (
        "ℹ️ *Краткая справка по шинному калькулятору*\n\n"
        "📌 *Расчет шин и дисков:*\n"
        "Расчет выполняется на основе данных - *ширина, профиль и диаметр текущих шин, ширина обода и вылет текущих дисков, а также параметры новых шин и дисков*\n\n"
        "_P.S. Калькулятор предоставляет ориентировочные данные для сравнения. Совместимость зависит от конструкции автомобиля и может отличаться!_\n\n"
        "📌 *Просмотр расчетов:*\n"
        "Вы можете посмотреть свои предыдущие расчеты с указанием всех параметров\n\n"
        "📌 *Удаление расчетов:*\n"
        "Вы можете удалить свои расчеты, если они больше не нужны"
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Рассчитать шины', 'Просмотр шин', 'Удаление шин')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')

    if show_description:
        bot.send_message(message.chat.id, description, parse_mode='Markdown')

    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

TIRE_HISTORY_PATH = os.path.join('data', 'user', 'calculators', 'tires', 'tire_users.json')
TIRE_EXCEL_DIR = os.path.join('data', 'user', 'calculators', 'tires', 'excel')

user_data = {}
user_history_tire = {}

def ensure_path_and_file(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def load_user_history_tires():
    global user_history_tire
    try:
        if os.path.exists(TIRE_HISTORY_PATH):
            with open(TIRE_HISTORY_PATH, 'r', encoding='utf-8') as db_file:
                user_history_tire = json.load(db_file)
        else:
            user_history_tire = {}
    except Exception as e:
        user_history_tire = {}

def save_user_history_tires():
    try:
        with open(TIRE_HISTORY_PATH, 'w', encoding='utf-8') as db_file:
            json.dump(user_history_tire, db_file, ensure_ascii=False, indent=2)
    except Exception as e:
        pass

ensure_path_and_file(TIRE_HISTORY_PATH)
os.makedirs(TIRE_EXCEL_DIR, exist_ok=True)
load_user_history_tires()

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_ШИНЫ (рассчитать шины) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Рассчитать шины")
@check_function_state_decorator('Рассчитать шины')
@track_usage('Рассчитать шины')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def start_tire_calculation(message):
    user_id = message.from_user.id
    user_data[user_id] = {'user_id': user_id, 'username': message.from_user.username or 'unknown'}

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Вернуться в шины')
    markup.add('Вернуться в калькуляторы')
    markup.add("В главное меню")
    msg = bot.send_message(message.chat.id, "Введите ширину текущих шин (мм):\n\n_P.S. ввод от 135 до 405 с шагом 10_", reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_current_width_step)

@text_only_handler
def process_current_width_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в шины":
        view_tire_calc(message, show_description=False)
        return 
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        width = int(message.text)
        if width < 135 or width > 405 or (width - 135) % 10 != 0:
            raise ValueError
        user_data[user_id]['current_width'] = width
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Введите профиль текущих шин (%):\n\n_P.S. ввод от 30 до 80 с шагом 5_", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_current_profile_step)
    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число от 135 до 405 с шагом 10", reply_markup=markup)
        bot.register_next_step_handler(msg, process_current_width_step)

@text_only_handler
def process_current_profile_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в шины":
        view_tire_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        profile = int(message.text)
        if profile < 30 or profile > 80 or (profile - 30) % 5 != 0:
            raise ValueError
        user_data[user_id]['current_profile'] = profile
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Введите диаметр текущих шин (дюймы):\n\n_P.S. ввод от 12 до 24 с шагом 1_", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_current_diameter_step)
    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число от 30 до 80 с шагом 5", reply_markup=markup)
        bot.register_next_step_handler(msg, process_current_profile_step)

@text_only_handler
def process_current_diameter_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в шины":
        view_tire_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        diameter = int(message.text)
        if diameter < 12 or diameter > 24:
            raise ValueError
        user_data[user_id]['current_diameter'] = diameter
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Введите ширину обода текущих дисков (дюймы):\n\n_P.S. ввод от 4 до 13 с шагом 0.5_", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_current_rim_width_step)
    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число от 12 до 24", reply_markup=markup)
        bot.register_next_step_handler(msg, process_current_diameter_step)

@text_only_handler
def process_current_rim_width_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в шины":
        view_tire_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        rim_width = float(message.text.replace(',', '.'))
        if rim_width < 4 or rim_width > 13 or (rim_width * 2 % 1 != 0):
            raise ValueError
        user_data[user_id]['current_rim_width'] = rim_width
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Введите вылет текущих дисков (ET, мм):\n\n_P.S. ввод от -55 до 65 с шагом 1_", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_current_et_step)
    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число от 4 до 13 с шагом 0.5", reply_markup=markup)
        bot.register_next_step_handler(msg, process_current_rim_width_step)

@text_only_handler
def process_current_et_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в шины":
        view_tire_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        et = int(message.text)
        if et < -55 or et > 65:
            raise ValueError
        user_data[user_id]['current_et'] = et
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Введите ширину новых шин (мм):\n\n_P.S. ввод от 135 до 405 с шагом 10_", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_new_width_step)
    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число от -55 до 65", reply_markup=markup)
        bot.register_next_step_handler(msg, process_current_et_step)

@text_only_handler
def process_new_width_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в шины":
        view_tire_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        width = int(message.text)
        if width < 135 or width > 405 or (width - 135) % 10 != 0:
            raise ValueError
        user_data[user_id]['new_width'] = width
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Введите профиль новых шин (%):\n\n_P.S. ввод от 30 до 80 с шагом 5_", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_new_profile_step)
    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число от 135 до 405 с шагом 10", reply_markup=markup)
        bot.register_next_step_handler(msg, process_new_width_step)

@text_only_handler
def process_new_profile_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в шины":
        view_tire_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        profile = int(message.text)
        if profile < 30 or profile > 80 or (profile - 30) % 5 != 0:
            raise ValueError
        user_data[user_id]['new_profile'] = profile
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Введите диаметр новых шин (дюймы):\n\n_P.S. ввод от 12 до 24 с шагом 1_", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_new_diameter_step)
    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число от 30 до 80 с шагом 5", reply_markup=markup)
        bot.register_next_step_handler(msg, process_new_profile_step)

@text_only_handler
def process_new_diameter_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в шины":
        view_tire_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        diameter = int(message.text)
        if diameter < 12 or diameter > 24:
            raise ValueError
        user_data[user_id]['new_diameter'] = diameter
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Введите ширину обода новых дисков (дюймы):\n\n_P.S. ввод от 4 до 13 с шагом 0.5_", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_new_rim_width_step)
    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число от 12 до 24", reply_markup=markup)
        bot.register_next_step_handler(msg, process_new_diameter_step)

@text_only_handler
def process_new_rim_width_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в шины":
        view_tire_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        rim_width = float(message.text.replace(',', '.'))
        if rim_width < 4 or rim_width > 13 or (rim_width * 2 % 1 != 0):
            raise ValueError
        user_data[user_id]['new_rim_width'] = rim_width
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Введите вылет новых дисков (ET, мм):\n\n_P.S. ввод от -55 до 65 с шагом 1_", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_new_et_step)
    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число от 4 до 13 с шагом 0.5", reply_markup=markup)
        bot.register_next_step_handler(msg, process_new_rim_width_step)

@text_only_handler
def process_new_et_step(message):
    user_id = message.from_user.id
    if message.text == "Вернуться в шины":
        view_tire_calc(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    try:
        et = int(message.text)
        if et < -55 or et > 65:
            raise ValueError
        user_data[user_id]['new_et'] = et
        calculate_tire(message)
    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add("В главное меню")
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВведите число от -55 до 65", reply_markup=markup)
        bot.register_next_step_handler(msg, process_new_et_step)

@text_only_handler
def calculate_tire(message):
    user_id = message.from_user.id
    data = user_data[user_id]

    current_diameter_mm = data['current_diameter'] * 25.4
    new_diameter_mm = data['new_diameter'] * 25.4
    current_rim_width_mm = data['current_rim_width'] * 25.4
    new_rim_width_mm = data['new_rim_width'] * 25.4

    current_profile_height = data['current_width'] * (data['current_profile'] / 100)
    new_profile_height = data['new_width'] * (data['new_profile'] / 100)

    current_total_diameter = current_diameter_mm + 2 * current_profile_height
    new_total_diameter = new_diameter_mm + 2 * new_profile_height

    diameter_diff_mm = new_total_diameter - current_total_diameter
    diameter_diff_percent = (diameter_diff_mm / current_total_diameter) * 100

    clearance_diff = diameter_diff_mm / 2
    speed_diff_percent = -diameter_diff_percent
    rim_width_diff_mm = new_rim_width_mm - current_rim_width_mm

    recommendation = "✅ Подходит" if abs(diameter_diff_percent) <= 3 and abs(rim_width_diff_mm) <= 25.4 else "⚠️ Не рекомендуется (отклонение > 3% или ширина обода сильно отличается)"

    width_effects = ""
    if data['new_width'] > data['current_width']:
        width_effects = (
            "📈 *Увеличится ширина шины:*\n\n"
            "✅ Лучше внешний вид сзади\n"
            "✅ Улучшится сцепление и торможение (лето)\n"
            "✅ Увеличится срок службы шины\n"
            "❌ Незначительно увеличится расход топлива\n"
            "❌ Риск затирания подкрылков\n"
        )
    elif data['new_width'] < data['current_width']:
        width_effects = (
            "📉 *Уменьшится ширина шины:*\n\n"
            "✅ Улучшится сцепление на льду и снегу\n"
            "✅ Уменьшится расход топлива\n"
            "❌ Ухудшится сцепление (лето)\n"
            "❌ Сократится срок службы шины\n"
        )

    profile_effects = ""
    if new_profile_height > current_profile_height:
        profile_effects = (
            "📈 *Увеличится высота профиля:*\n\n"
            "✅ Машина станет мягче\n"
            "✅ Меньше риск повредить шину/диск\n"
            "❌ Хуже держит дорогу на скорости\n"
        )
    elif new_profile_height < current_profile_height:
        profile_effects = (
            "📉 *Уменьшится высота профиля:*\n\n"
            "✅ Улучшится управляемость\n"
            "❌ Машина станет жестче\n"
            "❌ Больше риск повредить диск/шину\n"
        )

    clearance_effects = ""
    if clearance_diff > 0:
        clearance_effects = (
            "📈 *Увеличится клиренс:*\n\n"
            "✅ Комфортнее на ямах и бездорожье\n"
            "❌ Ухудшится управляемость на скорости\n"
            "❌ Риск затирания подкрылков\n"
            f"❌ Спидометр занижает на {abs(speed_diff_percent):.1f}%\n"
        )
    elif clearance_diff < 0:
        clearance_effects = (
            "📉 *Уменьшится клиренс:*\n\n"
            "✅ Улучшится управляемость на скорости\n"
            "❌ Менее комфортно на ямах\n"
            f"❌ Спидометр завышает на {abs(speed_diff_percent):.1f}%\n"
        )

    current_tire = f"{data['current_width']}/{data['current_profile']} R{data['current_diameter']}"
    current_rim = f"{data['current_rim_width']}x{data['current_diameter']} ET {data['current_et']}"
    new_tire = f"{data['new_width']}/{data['new_profile']} R{data['new_diameter']}"
    new_rim = f"{data['new_rim_width']}x{data['new_diameter']} ET {data['new_et']}"

    result_message = (
        "*Результат расчета шин и дисков:*\n\n"
        "*Текущие параметры:*\n\n"
        f"📏 Шины: {current_tire}\n"
        f"🔍 Диски: {current_rim}\n"
        f"↔️ Ширина шины: {data['current_width']} мм\n"
        f"↕️ Высота профиля: {current_profile_height:.1f} мм\n"
        f"🔄 Диаметр: {current_total_diameter:.1f} мм\n"
        f"↔️ Ширина обода: {current_rim_width_mm:.1f} мм\n\n"
        "*Новые параметры:*\n\n"
        f"📏 Шины: {new_tire}\n"
        f"🔍 Диски: {new_rim}\n"
        f"↔️ Ширина шины: {data['new_width']} мм\n"
        f"↕️ Высота профиля: {new_profile_height:.1f} мм\n"
        f"🔄 Диаметр: {new_total_diameter:.1f} мм\n"
        f"↔️ Ширина обода: {new_rim_width_mm:.1f} мм\n\n"
        "*Сравнение:*\n\n"
        f"🔄 Разница в диаметре: {diameter_diff_mm:+.1f} мм ({diameter_diff_percent:+.1f}%)\n"
        f"🚗 Изменение клиренса: {clearance_diff:+.1f} мм\n"
        f"⏱ Отклонение спидометра: {speed_diff_percent:+.1f}%\n"
        f"↔️ Разница в ширине обода: {rim_width_diff_mm:+.1f} мм\n\n"
        f"{width_effects}\n\n"
        f"{profile_effects}\n\n"
        f"{clearance_effects}\n\n"
        f"*Рекомендация:*\n\n{recommendation}"
    )

    bot.send_message(message.chat.id, result_message, parse_mode='Markdown')
    
    save_tire_calculation_to_history(user_id, data, current_total_diameter, new_total_diameter, diameter_diff_mm, diameter_diff_percent)
    
    del user_data[user_id]
    view_tire_calc(message, show_description=False)

def save_tire_calculation_to_history(user_id, data, current_diameter, new_diameter, diff_mm, diff_percent):
    user_id_int = int(user_id)
    user_id_str = str(user_id)
    timestamp = datetime.now().strftime("%d.%m.%Y в %H:%M")
    
    current_profile_height = data['current_width'] * (data['current_profile'] / 100)
    new_profile_height = data['new_width'] * (data['new_profile'] / 100)
    current_rim_width_mm = data['current_rim_width'] * 25.4
    new_rim_width_mm = data['new_rim_width'] * 25.4
    diameter_diff_mm = new_diameter - current_diameter
    diameter_diff_percent = (diameter_diff_mm / current_diameter) * 100
    clearance_diff = diameter_diff_mm / 2
    speed_diff_percent = -diameter_diff_percent
    rim_width_diff_mm = new_rim_width_mm - current_rim_width_mm
    recommendation = "✅ Подходит" if abs(diameter_diff_percent) <= 3 and abs(rim_width_diff_mm) <= 25.4 else "⚠️ Не рекомендуется (отклонение > 3% или ширина обода сильно отличается)"

    calculation_data = {
        'current_tire': f"{data['current_width']}/{data['current_profile']} R{data['current_diameter']}",
        'current_rim': f"{data['current_rim_width']}x{data['current_diameter']} ET {data['current_et']}",
        'new_tire': f"{data['new_width']}/{data['new_profile']} R{data['new_diameter']}",
        'new_rim': f"{data['new_rim_width']}x{data['new_diameter']} ET {data['new_et']}",
        'current_width': data['current_width'],
        'current_profile': data['current_profile'],
        'current_profile_height': round(current_profile_height, 1),
        'current_diameter': round(current_diameter, 1),
        'current_rim_width_mm': round(current_rim_width_mm, 1),
        'current_et': data['current_et'],
        'new_width': data['new_width'],
        'new_profile': data['new_profile'],
        'new_profile_height': round(new_profile_height, 1),
        'new_diameter': round(new_diameter, 1),
        'new_rim_width_mm': round(new_rim_width_mm, 1),
        'new_et': data['new_et'],
        'diameter_diff_mm': round(diameter_diff_mm, 1),
        'diameter_diff_percent': round(diameter_diff_percent, 1),
        'clearance_diff': round(clearance_diff, 1),
        'speed_diff_percent': round(speed_diff_percent, 1),
        'rim_width_diff_mm': round(rim_width_diff_mm, 1),
        'recommendation': recommendation,
        'timestamp': timestamp
    }

    if user_id_str not in user_history_tire:
        user_history_tire[user_id_str] = {
            'username': data.get('username', 'unknown'),
            'tire_calculations': []
        }
    elif 'tire_calculations' not in user_history_tire[user_id_str]:
        user_history_tire[user_id_str]['tire_calculations'] = []

    user_history_tire[user_id_str]['tire_calculations'].append(calculation_data)
    
    if not TIRE_HISTORY_PATH.endswith('tire_users.json'):
        raise ValueError("Попытка сохранить данные шин в неверный файл!")
    
    save_user_history_tires()
    save_tire_to_excel(user_id_str, calculation_data)

def save_tire_to_excel(user_id, calculation):
    file_path = os.path.join(TIRE_EXCEL_DIR, f"{user_id}_tires.xlsx")
    
    calculations = user_history_tire.get(user_id, {}).get('tire_calculations', [])
    
    columns = [
        "Дата расчета",
        "Текущие шины", "Текущие диски", "Ширина текущих шин (мм)", "Профиль текущих шин (%)",
        "Высота профиля текущих шин (мм)", "Диаметр текущих шин (мм)", "Ширина обода текущих дисков (мм)", "Вылет текущих дисков (ET, мм)",
        "Новые шины", "Новые диски", "Ширина новых шин (мм)", "Профиль новых шин (%)",
        "Высота профиля новых шин (мм)", "Диаметр новых шин (мм)", "Ширина обода новых дисков (мм)", "Вылет новых дисков (ET, мм)",
        "Разница в диаметре (мм)", "Разница в диаметре (%)", "Изменение клиренса (мм)", "Отклонение спидометра (%)", "Разница в ширине обода (мм)",
        "Рекомендация"
    ]
    
    new_calc_data = {
        "Дата расчета": calculation['timestamp'],
        "Текущие шины": calculation['current_tire'],
        "Текущие диски": calculation['current_rim'],
        "Ширина текущих шин (мм)": calculation['current_width'],
        "Профиль текущих шин (%)": calculation['current_profile'],
        "Высота профиля текущих шин (мм)": calculation['current_profile_height'],
        "Диаметр текущих шин (мм)": calculation['current_diameter'],
        "Ширина обода текущих дисков (мм)": calculation['current_rim_width_mm'],
        "Вылет текущих дисков (ET, мм)": calculation['current_et'],
        "Новые шины": calculation['new_tire'],
        "Новые диски": calculation['new_rim'],
        "Ширина новых шин (мм)": calculation['new_width'],
        "Профиль новых шин (%)": calculation['new_profile'],
        "Высота профиля новых шин (мм)": calculation['new_profile_height'],
        "Диаметр новых шин (мм)": calculation['new_diameter'],
        "Ширина обода новых дисков (мм)": calculation['new_rim_width_mm'],
        "Вылет новых дисков (ET, мм)": calculation['new_et'],
        "Разница в диаметре (мм)": calculation['diameter_diff_mm'],
        "Разница в диаметре (%)": calculation['diameter_diff_percent'],
        "Изменение клиренса (мм)": calculation['clearance_diff'],
        "Отклонение спидометра (%)": calculation['speed_diff_percent'],
        "Разница в ширине обода (мм)": calculation['rim_width_diff_mm'],
        "Рекомендация": calculation['recommendation']
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

def update_tire_excel_file(user_id):
    file_path = os.path.join(TIRE_EXCEL_DIR, f"{user_id}_tires.xlsx")
    calculations = user_history_tire.get(user_id, {}).get('tire_calculations', [])

    if not calculations:
        columns = [
            "Дата расчета",
            "Текущие шины", "Текущие диски", "Ширина текущих шин (мм)", "Профиль текущих шин (%)",
            "Высота профиля текущих шин (мм)", "Диаметр текущих шин (мм)", "Ширина обода текущих дисков (мм)", "Вылет текущих дисков (ET, мм)",
            "Новые шины", "Новые диски", "Ширина новых шин (мм)", "Профиль новых шин (%)",
            "Высота профиля новых шин (мм)", "Диаметр новых шин (мм)", "Ширина обода новых дисков (мм)", "Вылет новых дисков (ET, мм)",
            "Разница в диаметре (мм)", "Разница в диаметре (%)", "Изменение клиренса (мм)", "Отклонение спидометра (%)", "Разница в ширине обода (мм)",
            "Рекомендация"
        ]
        df = pd.DataFrame(columns=columns)
        df.to_excel(file_path, index=False)
        return

    columns = [
        "Дата расчета",
        "Текущие шины", "Текущие диски", "Ширина текущих шин (мм)", "Профиль текущих шин (%)",
        "Высота профиля текущих шин (мм)", "Диаметр текущих шин (мм)", "Ширина обода текущих дисков (мм)", "Вылет текущих дисков (ET, мм)",
        "Новые шины", "Новые диски", "Ширина новых шин (мм)", "Профиль новых шин (%)",
        "Высота профиля новых шин (мм)", "Диаметр новых шин (мм)", "Ширина обода новых дисков (мм)", "Вылет новых дисков (ET, мм)",
        "Разница в диаметре (мм)", "Разница в диаметре (%)", "Изменение клиренса (мм)", "Отклонение спидометра (%)", "Разница в ширине обода (мм)",
        "Рекомендация"
    ]

    calc_records = []
    for calc in calculations:
        calc_data = {
            "Дата расчета": calc['timestamp'],
            "Текущие шины": calc['current_tire'],
            "Текущие диски": calc['current_rim'],
            "Ширина текущих шин (мм)": calc['current_width'],
            "Профиль текущих шин (%)": calc['current_profile'],
            "Высота профиля текущих шин (мм)": calc['current_profile_height'],
            "Диаметр текущих шин (мм)": calc['current_diameter'],
            "Ширина обода текущих дисков (мм)": calc['current_rim_width_mm'],
            "Вылет текущих дисков (ET, мм)": calc['current_et'],
            "Новые шины": calc['new_tire'],
            "Новые диски": calc['new_rim'],
            "Ширина новых шин (мм)": calc['new_width'],
            "Профиль новых шин (%)": calc['new_profile'],
            "Высота профиля новых шин (мм)": calc['new_profile_height'],
            "Диаметр новых шин (мм)": calc['new_diameter'],
            "Ширина обода новых дисков (мм)": calc['new_rim_width_mm'],
            "Вылет новых дисков (ET, мм)": calc['new_et'],
            "Разница в диаметре (мм)": calc['diameter_diff_mm'],
            "Разница в диаметре (%)": calc['diameter_diff_percent'],
            "Изменение клиренса (мм)": calc['clearance_diff'],
            "Отклонение спидометра (%)": calc['speed_diff_percent'],
            "Разница в ширине обода (мм)": calc['rim_width_diff_mm'],
            "Рекомендация": calc['recommendation']
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

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_ШИНЫ (просмотр шин) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Просмотр шин")
@check_function_state_decorator('Просмотр шин')
@track_usage('Просмотр шин')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_view_tire_calc(message):
    user_id = str(message.from_user.id)
    if user_id not in user_history_tire or 'tire_calculations' not in user_history_tire[user_id] or not user_history_tire[user_id]['tire_calculations']:
        bot.send_message(message.chat.id, "❌ У вас нет сохраненных расчетов шин!")
        view_tire_calc(message, show_description=False)
        return
    view_tire_calculations(message)

@text_only_handler
def view_tire_calculations(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if user_id not in user_history_tire or 'tire_calculations' not in user_history_tire[user_id] or not user_history_tire[user_id]['tire_calculations']:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов шин!")
        view_tire_calc(message, show_description=False)
        return

    calculations = user_history_tire[user_id]['tire_calculations']
    message_text = "*Список ваших расчетов шин:*\n\n"

    for i, calc in enumerate(calculations, 1):
        timestamp = calc['timestamp']
        message_text += f"🕒 *№{i}.* {timestamp}\n"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Шины в EXCEL')
    markup.add('Вернуться в шины')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    msg = bot.send_message(chat_id, message_text, parse_mode='Markdown')
    bot.send_message(chat_id, "Введите номера расчетов автокредита для просмотра:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_view_tire_selection)

@text_only_handler
def process_view_tire_selection(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в шины":
        view_tire_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return
    if message.text == "Шины в EXCEL":
        send_tire_excel_file(message)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Шины в EXCEL')
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Введите номера расчетов шин для просмотра:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_view_tire_selection)
        return

    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    calculations = user_history_tire.get(user_id, {}).get('tire_calculations', [])
    if not calculations:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов шин!")
        view_tire_calc(message, show_description=False)
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
            markup.add('Шины в EXCEL')
            markup.add('Вернуться в шины')
            markup.add('Вернуться в калькуляторы')
            markup.add('В главное меню')
            msg = bot.send_message(chat_id, "Некорректный ввод!\nВыберите существующие номера расчетов из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_view_tire_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(chat_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        for index in valid_indices:
            calc = calculations[index]
            required_keys = [
                'current_width', 'new_width', 'current_profile_height', 'new_profile_height',
                'current_diameter', 'new_diameter', 'current_rim_width_mm', 'new_rim_width_mm',
                'diameter_diff_mm', 'diameter_diff_percent', 'clearance_diff', 'speed_diff_percent',
                'rim_width_diff_mm', 'recommendation', 'current_tire', 'current_rim', 'new_tire', 'new_rim'
            ]
            for key in required_keys:
                if key not in calc:
                    bot.send_message(chat_id, f"❌ Данные расчета №{index + 1} устарели или повреждены! Выполните новый расчет!")
                    view_tire_calc(message, show_description=False)
                    return

            width_effects = ""
            if calc['new_width'] > calc['current_width']:
                width_effects = (
                    "📈 *Увеличится ширина шины:*\n\n"
                    "✅ Лучше внешний вид сзади\n"
                    "✅ Улучшится сцепление и торможение (лето)\n"
                    "✅ Увеличится срок службы шины\n"
                    "❌ Незначительно увеличится расход топлива\n"
                    "❌ Риск затирания подкрылков\n"
                )
            elif calc['new_width'] < calc['current_width']:
                width_effects = (
                    "📉 *Уменьшится ширина шины:*\n\n"
                    "✅ Улучшится сцепление на льду и снегу\n"
                    "✅ Уменьшится расход топлива\n"
                    "❌ Ухудшится сцепление (лето)\n"
                    "❌ Сократится срок службы шины\n"
                )

            profile_effects = ""
            if calc['new_profile_height'] > calc['current_profile_height']:
                profile_effects = (
                    "📈 *Увеличится высота профиля:*\n\n"
                    "✅ Машина станет мягче\n"
                    "✅ Меньше риск повредить шину/диск\n"
                    "❌ Хуже держит дорогу на скорости\n"
                )
            elif calc['new_profile_height'] < calc['current_profile_height']:
                profile_effects = (
                    "📉 *Уменьшится высота профиля:*\n\n"
                    "✅ Улучшится управляемость\n"
                    "❌ Машина станет жестче\n"
                    "❌ Больше риск повредить диск/шину\n"
                )

            clearance_effects = ""
            if calc['clearance_diff'] > 0:
                clearance_effects = (
                    "📈 *Увеличится клиренс:*\n\n"
                    "✅ Комфортнее на ямах и бездорожье\n"
                    "❌ Ухудшится управляемость на скорости\n"
                    "❌ Риск затирания подкрылков\n"
                    f"❌ Спидометр занижает на {abs(calc['speed_diff_percent']):.1f}%\n"
                )
            elif calc['clearance_diff'] < 0:
                clearance_effects = (
                    "📉 *Уменьшится клиренс:*\n\n"
                    "✅ Улучшится управляемость на скорости\n"
                    "❌ Менее комфортно на ямах\n"
                    f"❌ Спидометр завышает на {abs(calc['speed_diff_percent']):.1f}%\n"
                )

            result_message = (
                f"*📊 Результат расчета шин №{index + 1}:*\n\n"
                f"*Текущие параметры:*\n\n"
                f"📏 Шины: {calc['current_tire']}\n"
                f"🔍 Диски: {calc['current_rim']}\n"
                f"↔️ Ширина шины: {calc['current_width']} мм\n"
                f"↕️ Высота профиля: {calc['current_profile_height']:.1f} мм\n"
                f"🔄 Диаметр: {calc['current_diameter']:.1f} мм\n"
                f"↔️ Ширина обода: {calc['current_rim_width_mm']:.1f} мм\n\n"
                f"*Новые параметры:*\n\n"
                f"📏 Шины: {calc['new_tire']}\n"
                f"🔍 Диски: {calc['new_rim']}\n"
                f"↔️ Ширина шины: {calc['new_width']} мм\n"
                f"↕️ Высота профиля: {calc['new_profile_height']:.1f} мм\n"
                f"🔄 Диаметр: {calc['new_diameter']:.1f} мм\n"
                f"↔️ Ширина обода: {calc['new_rim_width_mm']:.1f} мм\n\n"
                f"*Сравнение:*\n\n"
                f"🔄 Разница в диаметре: {calc['diameter_diff_mm']:+.1f} мм ({calc['diameter_diff_percent']:+.1f}%)\n"
                f"🚗 Изменение клиренса: {calc['clearance_diff']:+.1f} мм\n"
                f"⏱ Отклонение спидометра: {calc['speed_diff_percent']:+.1f}%\n"
                f"↔️ Разница в ширине обода: {calc['rim_width_diff_mm']:+.1f} мм\n\n"
                f"{width_effects}\n\n"
                f"{profile_effects}\n\n"
                f"{clearance_effects}\n\n"
                f"*Рекомендация:*\n\n{calc['recommendation']}\n\n"
                f"🕒 *Дата расчета:* {calc['timestamp']}"
            )

            bot.send_message(chat_id, result_message, parse_mode='Markdown')

        view_tire_calc(message, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Шины в EXCEL')
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Некорректный ввод!\nВведите числа через запятую", reply_markup=markup)
        bot.register_next_step_handler(msg, process_view_tire_selection)

@bot.message_handler(func=lambda message: message.text == "Шины в EXCEL")
@check_function_state_decorator('Шины в EXCEL')
@track_usage('Шины в EXCEL')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_tire_excel_file(message):
    user_id = str(message.from_user.id)
    excel_file_path = os.path.join(TIRE_EXCEL_DIR, f"{user_id}_tires.xlsx")

    if os.path.exists(excel_file_path):
        with open(excel_file_path, 'rb') as excel_file:
            bot.send_document(message.chat.id, excel_file)
    else:
        bot.send_message(message.chat.id, "❌ Файл Excel не найден!\nУбедитесь, что у вас есть сохраненные расчеты шин")
    view_tire_calc(message, show_description=False)

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_ШИНЫ (удаление шин) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Удаление шин")
@check_function_state_decorator('Удаление шин')
@track_usage('Удаление шин')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_delete_tire_calc(message):
    user_id = str(message.from_user.id)
    if user_id not in user_history_tire or 'tire_calculations' not in user_history_tire[user_id] or not user_history_tire[user_id]['tire_calculations']:
        bot.send_message(message.chat.id, "❌ У вас нет сохраненных расчетов шин!")
        view_tire_calc(message, show_description=False)
        return
    delete_tire_calculations(message)

@text_only_handler
def delete_tire_calculations(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if user_id not in user_history_tire or 'tire_calculations' not in user_history_tire[user_id] or not user_history_tire[user_id]['tire_calculations']:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов шин!")
        view_tire_calc(message, show_description=False)
        return

    calculations = user_history_tire[user_id]['tire_calculations']
    message_text = "*Список ваших расчетов шин:*\n\n"

    for i, calc in enumerate(calculations, 1):
        timestamp = calc['timestamp']
        message_text += f"🕒 *№{i}.* {timestamp}\n"

    msg = bot.send_message(chat_id, message_text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_delete_tire_selection)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в шины')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    bot.send_message(chat_id, "Введите номера для удаления расчетов:", reply_markup=markup)

@text_only_handler
def process_delete_tire_selection(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в шины":
        view_tire_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    calculations = user_history_tire.get(user_id, {}).get('tire_calculations', [])
    if not calculations:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов шин!")
        view_tire_calc(message, show_description=False)
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
            markup.add('Вернуться в шины')
            markup.add('Вернуться в калькуляторы')
            markup.add('В главное меню')
            msg = bot.send_message(chat_id, "Некорректный ввод!\nВыберите существующие номера расчетов из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_delete_tire_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(chat_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        valid_indices.sort(reverse=True)
        for index in valid_indices:
            del calculations[index]

        save_user_history_tires()
        update_tire_excel_file(user_id)
        bot.send_message(chat_id, "✅ Выбранные расчеты шин успешно удалены!")
        view_tire_calc(message, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в шины')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Некорректный ввод!\nВведите числа через запятую", reply_markup=markup)
        bot.register_next_step_handler(msg, process_delete_tire_selection)