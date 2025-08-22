from core.imports import wraps, telebot, types, os, json, re, datetime, timedelta, ReplyKeyboardMarkup, ReplyKeyboardRemove, openpyxl, Workbook, load_workbook, Alignment, Border, Side, Font, PatternFill
from core.bot_instance import bot
from .calculators_main import return_to_calculators
from handlers.user.user_main_menu import return_to_menu
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_АВТОКРЕДИТ --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Автокредит")
@check_function_state_decorator('Автокредит')
@track_usage('Автокредит')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_autokredit_calc(message, show_description=True):
    description = (
        "ℹ️ *Краткая справка по расчету автокредита*\n\n"
        "📌 *Расчет автокредита:*\n"
        "Расчет ведется по следующим данным - *дата, стоимость авто, первый платеж, срок кредита, процентная ставка, схема оплаты, дополнительные погашения*\n\n"
        "_P.S. калькулятор предоставляет ориентировочные данные на основе введенных параметров. Точные суммы зависят от условий банка и могут отличаться!_\n\n"
        "📌 *Просмотр автокредитов:*\n"
        "Вы можете посмотреть свои предыдущие расчеты с указанием всех параметров\n\n"
        "📌 *Удаление автокредитов:*\n"
        "Вы можете удалить свои расчеты, если они вам больше не нужны"
    )

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Рассчитать автокредит', 'Просмотр автокредитов', 'Удаление автокредитов')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')

    if show_description:
        bot.send_message(message.chat.id, description, parse_mode='Markdown')

    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

KREDIT_USERS_PATH = os.path.join('data', 'user', 'calculators', 'kredit', 'kredit_users.json')
EXCEL_PATH_TEMPLATE = os.path.join('data', 'user', 'calculators', 'kredit', 'excel', '{user_id}', '{user_id}_{timestamp}_autokredit.xlsx')

user_data = {}
user_history_kredit = {}

loan_terms = {
    "1 месяц": 1, "3 месяца": 3, "6 месяцев": 6, "1 год": 12, "1,5 года": 18,
    "2 года": 24, "3 года": 36, "4 года": 48, "5 лет": 60, "6 лет": 72,
    "7 лет": 84, "8 лет": 96, "9 лет": 108, "10 лет": 120, "15 лет": 180, "20 лет": 240
}

def ensure_path_and_file(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def load_user_history_kredit():
    global user_history_kredit
    try:
        if os.path.exists(KREDIT_USERS_PATH):
            with open(KREDIT_USERS_PATH, 'r', encoding='utf-8') as db_file:
                user_history_kredit = json.load(db_file)
        else:
            user_history_kredit = {}
    except Exception as e:
        user_history_kredit = {}

def save_user_history_kredit():
    try:
        with open(KREDIT_USERS_PATH, 'w', encoding='utf-8') as db_file:
            json.dump(user_history_kredit, db_file, ensure_ascii=False, indent=2)
    except Exception as e:
        pass

ensure_path_and_file(KREDIT_USERS_PATH)
load_user_history_kredit()

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_АВТОКРЕДИТ (рассчитать автокредит) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Рассчитать автокредит")
@check_function_state_decorator('Рассчитать автокредит')
@track_usage('Рассчитать автокредит')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def start_car_loan_calculation(message):
    user_id = message.from_user.id
    user_data[user_id] = {'user_id': user_id, 'username': message.from_user.username}
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в автокредит')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, "Введите дату выдачи автокредита в формате ДД.ММ.ГГГГ:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_loan_date_step)

@text_only_handler
def process_loan_date_step(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    try:
        loan_date = datetime.strptime(message.text, "%d.%m.%Y")
        current_date = datetime.now()
        if loan_date < current_date.replace(hour=0, minute=0, second=0, microsecond=0):
            raise ValueError("Дата не может быть раньше текущей")
        user_data[user_id]['loan_date'] = loan_date
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, "Введите стоимость авто в рублях:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_car_price_step)
    except ValueError as e:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, str(e) if str(e) else "Некорректный формат даты!\nИспользуйте ДД.ММ.ГГГГ", reply_markup=markup)
        bot.register_next_step_handler(msg, process_loan_date_step)

@text_only_handler
def process_car_price_step(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    try:
        car_price = float(message.text.replace(',', '.'))
        if car_price <= 0:
            raise ValueError("Стоимость авто должна быть положительным числом!")
        user_data[user_id]['car_price'] = car_price
        
        markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("В ₽", "В %")
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, "Как вы хотите внести первый платеж?", reply_markup=markup)
        bot.register_next_step_handler(msg, process_down_payment_type_step)
    except ValueError as e:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, str(e) if str(e) else "Некорректный ввод!\nВведите положительное число", reply_markup=markup)
        bot.register_next_step_handler(msg, process_car_price_step)

@text_only_handler
def process_down_payment_type_step(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    down_payment_type = message.text.strip()
    if down_payment_type not in ["В ₽", "В %"]:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите в ₽ или в %", reply_markup=markup)
        bot.register_next_step_handler(msg, process_down_payment_type_step)
        return
    
    user_data[user_id]['down_payment_type'] = down_payment_type
    unit = "₽" if down_payment_type == "В ₽" else "%"
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в автокредит')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, f"Введите сумму первого платежа в *{unit}*:", reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_down_payment_amount_step)

@text_only_handler
def process_down_payment_amount_step(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    try:
        amount = float(message.text.replace(',', '.'))
        if amount < 0:
            raise ValueError("Сумма первого платежа не может быть отрицательной!")
        
        if user_data[user_id]['down_payment_type'] == "В ₽":
            if amount >= user_data[user_id]['car_price']:
                raise ValueError("Первый платеж не может быть больше или равен стоимости авто!")
            user_data[user_id]['down_payment'] = amount
        else:  
            if amount > 100:
                raise ValueError("Процент не может быть больше 100!")
            user_data[user_id]['down_payment'] = user_data[user_id]['car_price'] * (amount / 100)
        
        markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        terms = list(loan_terms.keys())
        for i in range(0, len(terms), 2):
            if i + 1 < len(terms):
                markup.row(terms[i], terms[i + 1])
            else:
                markup.add(terms[i])
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, "Выберите срок выдачи автокредита:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_loan_term_step)
    except ValueError as e:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, str(e) if str(e) else "Некорректный ввод!\nВведите положительное число", reply_markup=markup)
        bot.register_next_step_handler(msg, process_down_payment_amount_step)

@text_only_handler
def process_loan_term_step(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    term = message.text.strip()
    if term not in loan_terms:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите срок из предложенных вариантов", reply_markup=markup)
        bot.register_next_step_handler(msg, process_loan_term_step)
        return
    
    user_data[user_id]['loan_term'] = loan_terms[term]
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в автокредит')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, "Введите процентную ставку автокредита в процентах:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_interest_rate_step)

@text_only_handler
def process_interest_rate_step(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    try:
        rate = float(message.text.replace(',', '.'))
        if rate <= 0:
            raise ValueError("Процентная ставка должна быть положительным числом!")
        user_data[user_id]['interest_rate'] = rate / 100
        
        markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("Равными долями", "Дифференцированные платежи")
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, "Выберите схему оплаты:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_payment_scheme_step)
    except ValueError as e:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, str(e) if str(e) else "Некорректный ввод!\nВведите положительное число", reply_markup=markup)
        bot.register_next_step_handler(msg, process_interest_rate_step)

@text_only_handler
def process_payment_scheme_step(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    scheme = message.text.strip()
    if scheme not in ["Равными долями", "Дифференцированные платежи"]:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите равными долями или дифференцированные платежи", reply_markup=markup)
        bot.register_next_step_handler(msg, process_payment_scheme_step)
        return
    
    user_data[user_id]['payment_scheme'] = scheme
    markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    markup.add("Да", "Нет")
    markup.add('Вернуться в автокредит')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, "Есть ли у вас дополнительные погашения?", reply_markup=markup)
    bot.register_next_step_handler(msg, process_extra_payments_step)

@text_only_handler
def process_extra_payments_step(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    answer = message.text.strip()
    if answer not in ["Да", "Нет"]:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите да или нет", reply_markup=markup)
        bot.register_next_step_handler(msg, process_extra_payments_step)
        return
    
    user_data[user_id]['has_extra_payments'] = answer == "Да"
    if answer == "Нет":
        calculate_loan(message)
    else:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, "Введите количество дополнительных погашений:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_extra_payments_count_step)

@text_only_handler
def process_extra_payments_count_step(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError("Количество погашений должно быть положительным числом!")
        user_data[user_id]['extra_payments_count'] = count
        user_data[user_id]['extra_payments'] = []
        process_extra_payment_info(message, 1)
    except ValueError as e:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, str(e) if str(e) else "Некорректный ввод!\nВведите положительное число", reply_markup=markup)
        bot.register_next_step_handler(msg, process_extra_payments_count_step)

@text_only_handler
def process_extra_payment_info(message, payment_num):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    if payment_num > user_data[user_id]['extra_payments_count']:
        calculate_loan(message)
        return
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в автокредит')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, f"*Погашение №{payment_num}*\nВведите дату платежа в формате ДД.ММ.ГГГГ:", reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler(msg, lambda m: process_extra_payment_date_step(m, payment_num))

@text_only_handler
def process_extra_payment_date_step(message, payment_num):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    try:
        payment_date = datetime.strptime(message.text, "%d.%m.%Y")
        if payment_date < user_data[user_id]['loan_date']:
            raise ValueError("Дата не может быть раньше даты выдачи кредита")
        user_data[user_id]['extra_payments'].append({'date': payment_date})
        
        markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
        markup.add("Единоразово", "Ежемесячно", "Ежегодно")
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, f"*Погашение №{payment_num}*\nВыберите периодичность:", reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(msg, lambda m: process_extra_payment_frequency_step(m, payment_num))
    except ValueError as e:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, str(e) if str(e) else "Некорректный формат даты!\nИспользуйте формат ДД.ММ.ГГГГ", reply_markup=markup)
        bot.register_next_step_handler(msg, lambda m: process_extra_payment_date_step(m, payment_num))

@text_only_handler
def process_extra_payment_frequency_step(message, payment_num):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    frequency = message.text.strip()
    if frequency not in ["Единоразово", "Ежемесячно", "Ежегодно"]:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите единоразово, ежемесячно или ежегодно", reply_markup=markup)
        bot.register_next_step_handler(msg, lambda m: process_extra_payment_frequency_step(m, payment_num))
        return
    
    user_data[user_id]['extra_payments'][payment_num-1]['frequency'] = frequency
    markup = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True, resize_keyboard=True)
    markup.add("Срок", "Сумма")
    markup.add('Вернуться в автокредит')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, f"*Погашение №{payment_num}*\nЧто уменьшать?", reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler(msg, lambda m: process_extra_payment_target_step(m, payment_num))

@text_only_handler
def process_extra_payment_target_step(message, payment_num):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    target = message.text.strip()
    if target not in ["Срок", "Сумма"]:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, "Некорректный ввод!\nВыберите срок или сумма", reply_markup=markup)
        bot.register_next_step_handler(msg, lambda m: process_extra_payment_target_step(m, payment_num))
        return
    
    user_data[user_id]['extra_payments'][payment_num-1]['target'] = target
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в автокредит')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, f"*Погашение №{payment_num}*\nВведите сумму погашения в рублях:", reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler(msg, lambda m: process_extra_payment_amount_step(m, payment_num))

@text_only_handler
def process_extra_payment_amount_step(message, payment_num):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    user_id = message.from_user.id
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError("Сумма погашения должна быть положительным числом!")
        user_data[user_id]['extra_payments'][payment_num-1]['amount'] = amount
        process_extra_payment_info(message, payment_num + 1)
    except ValueError as e:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(message.chat.id, str(e) if str(e) else "Некорректный ввод!\nВведите положительное число", reply_markup=markup)
        bot.register_next_step_handler(msg, lambda m: process_extra_payment_amount_step(m, payment_num))

@text_only_handler
def calculate_loan(message):
    user_id = message.from_user.id
    data = user_data[user_id]
    
    principal = data['car_price'] - data['down_payment']
    months = data['loan_term']
    monthly_rate = data['interest_rate'] / 12 / 100  
    
    payment_schedule = []
    total_interest = 0
    total_payment = 0
    monthly_payment = 0
    
    extra_payments = []
    if data.get('has_extra_payments', False):
        for extra in data['extra_payments']:
            payment_date = extra['date']
            amount = extra['amount']
            frequency = extra['frequency']
            target = extra['target']
            
            if frequency == "Единоразово":
                extra_payments.append({'date': payment_date, 'amount': amount, 'target': target})
            elif frequency == "Ежемесячно":
                current_date = payment_date
                end_date = data['loan_date'] + timedelta(days=30 * months)
                while current_date <= end_date:
                    extra_payments.append({'date': current_date, 'amount': amount, 'target': target})
                    current_date += timedelta(days=30)
            elif frequency == "Ежегодно":
                current_date = payment_date
                end_date = data['loan_date'] + timedelta(days=30 * months)
                while current_date <= end_date:
                    extra_payments.append({'date': current_date, 'amount': amount, 'target': target})
                    current_date += timedelta(days=365)
        extra_payments.sort(key=lambda x: x['date'])

    remaining_principal = principal
    start_date = data['loan_date']
    current_month = 0
    extra_payment_index = 0
    
    if data['payment_scheme'] == "Равными долями":
        monthly_payment = (principal * monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
        
        while remaining_principal > 0 and current_month < months:
            payment_date = start_date + timedelta(days=30 * current_month)
            
            extra_amount = 0
            extra_target = None
            while (extra_payment_index < len(extra_payments) and 
                   extra_payments[extra_payment_index]['date'].date() <= payment_date.date()):
                extra_amount += extra_payments[extra_payment_index]['amount']
                extra_target = extra_payments[extra_payment_index]['target']
                extra_payment_index += 1
            
            interest_payment = remaining_principal * monthly_rate
            principal_payment = monthly_payment - interest_payment
            
            if extra_amount > 0:
                if extra_target == "Сумма":
                    adjusted_payment = monthly_payment - extra_amount
                    if adjusted_payment < 0:
                        extra_amount = monthly_payment
                        adjusted_payment = 0
                    principal_payment += extra_amount
                else:  
                    remaining_principal -= extra_amount
                    remaining_months = months - current_month - 1
                    if remaining_months > 0 and remaining_principal > 0:
                        monthly_payment = (remaining_principal * monthly_rate * (1 + monthly_rate) ** remaining_months) / ((1 + monthly_rate) ** remaining_months - 1)
                    else:
                        monthly_payment = 0
            
            total_monthly_payment = monthly_payment
            if total_monthly_payment > remaining_principal + interest_payment:
                total_monthly_payment = remaining_principal + interest_payment
                principal_payment = remaining_principal
            
            remaining_principal -= principal_payment
            if remaining_principal < 0:
                remaining_principal = 0
            
            total_interest += interest_payment
            total_payment += total_monthly_payment
            
            payment_schedule.append({
                'date': payment_date.strftime("%d.%m.%Y"),
                'remaining_principal': remaining_principal,
                'interest_payment': interest_payment,
                'principal_payment': principal_payment,
                'total_payment': total_monthly_payment
            })
            
            current_month += 1
            if monthly_payment == 0:
                break
    
    else: 
        monthly_principal = principal / months
        
        while remaining_principal > 0 and current_month < months:
            payment_date = start_date + timedelta(days=30 * current_month)
            
            extra_amount = 0
            extra_target = None
            while (extra_payment_index < len(extra_payments) and 
                   extra_payments[extra_payment_index]['date'].date() <= payment_date.date()):
                extra_amount += extra_payments[extra_payment_index]['amount']
                extra_target = extra_payments[extra_payment_index]['target']
                extra_payment_index += 1
            
            interest_payment = remaining_principal * monthly_rate
            principal_payment = monthly_principal
            
            if extra_amount > 0:
                if extra_target == "Сумма":
                    principal_payment += extra_amount
                else:  
                    remaining_principal -= extra_amount
                    remaining_months = months - current_month - 1
                    if remaining_months > 0 and remaining_principal > 0:
                        monthly_principal = remaining_principal / remaining_months
                    else:
                        monthly_principal = 0
                    principal_payment = monthly_principal
            
            total_monthly_payment = principal_payment + interest_payment
            remaining_principal -= principal_payment
            if remaining_principal < 0:
                remaining_principal = 0
            
            total_interest += interest_payment
            total_payment += total_monthly_payment
            
            payment_schedule.append({
                'date': payment_date.strftime("%d.%m.%Y"),
                'remaining_principal': remaining_principal,
                'interest_payment': interest_payment,
                'principal_payment': principal_payment,
                'total_payment': total_monthly_payment
            })
            
            current_month += 1
            if monthly_principal == 0:
                break

    timestamp_display = datetime.now().strftime("%d.%m.%Y в %H:%M")
    result_message = (
        f"*Итоговый расчет по автокредиту на {timestamp_display}*\n\n"
        f"✨ *Ежемесячный платеж:*\n"
        f"{monthly_payment if data['payment_scheme'] == 'Равными долями' else payment_schedule[0]['total_payment']:,.2f} ₽\n\n"
        f"🏛️ *Сумма кредита:*\n"
        f"{principal:,.2f} ₽\n\n"
        f"💸 *Сумма процентов:*\n"
        f"{total_interest:,.2f} ₽\n\n"
        f"💰 *Общая выплата:*\n"
        f"{total_payment:,.2f} ₽\n\n"
        f"Ожидайте файл с календарем выплат по кредиту..."
    )
    
    bot.send_message(message.chat.id, result_message, parse_mode='Markdown')
    
    timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M")
    excel_path = EXCEL_PATH_TEMPLATE.format(user_id=user_id, timestamp=timestamp)
    
    os.makedirs(os.path.dirname(excel_path), exist_ok=True)
    save_to_excel(user_id, principal, total_interest, total_payment, payment_schedule, excel_path, timestamp_display)
    
    save_credit_calculation_to_history(user_id, principal, total_interest, total_payment, payment_schedule, timestamp_display)
    
    with open(excel_path, 'rb') as file:
        bot.send_document(message.chat.id, file, caption="📅 Календарь выплат по кредиту")
    
    del user_data[user_id]
    view_autokredit_calc(message, show_description=False)

def save_to_excel(user_id, principal, total_interest, total_payment, payment_schedule, excel_path, timestamp_display):
    user_id_int = int(user_id)  
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    
    sheet['A1'] = f"Календарный расчет выплат по автокредиту на дату {timestamp_display}"
    sheet['A1'].font = Font(bold=True)
    sheet['A1'].alignment = Alignment(horizontal='center', vertical='center')
    sheet.merge_cells('A1:E1')
    
    sheet['A3'] = "Сумма"
    sheet['B3'] = "Срок"
    sheet['C3'] = "Процентная ставка"
    sheet['D3'] = "Стоимость кредита"
    for col in ['A3', 'B3', 'C3', 'D3']:
        sheet[col].font = Font(bold=True)
        sheet[col].alignment = Alignment(horizontal='center', vertical='center')
    
    sheet['A4'] = f"{user_data[user_id_int]['car_price']:,.2f} руб.".replace(',', ' ')
    sheet['B4'] = f"{user_data[user_id_int]['loan_term']} мес"
    sheet['C4'] = f"{user_data[user_id_int]['interest_rate'] * 100:.2f}%"
    sheet['D4'] = f"{total_interest:,.2f} руб.".replace(',', ' ')
    for col in ['A4', 'B4', 'C4', 'D4']:
        sheet[col].alignment = Alignment(horizontal='center', vertical='center')
    
    thin_border = Border(
        left=Side(style='thin', color='000000'),
        right=Side(style='thin', color='000000'),
        top=Side(style='thin', color='000000'),
        bottom=Side(style='thin', color='000000')
    )
    light_green_fill = PatternFill(start_color='CCFFCC', end_color='CCFFCC', fill_type='solid')
    yellow_fill = PatternFill(start_color='FFFF99', end_color='FFFF99', fill_type='solid')
    
    headers = ["Дата платежа", "Остаток долга", "Начисление %", "Платеж в основной долг", "Сумма платежа"]
    for col, header in enumerate(headers, 1):
        cell = sheet.cell(row=5, column=col)
        cell.value = header
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border
    
    for row, payment in enumerate(payment_schedule, 6):
        sheet.cell(row=row, column=1).value = payment['date']
        sheet.cell(row=row, column=2).value = f"{payment['remaining_principal']:,.2f}".replace(',', ' ')
        sheet.cell(row=row, column=3).value = f"{payment['interest_payment']:,.2f}".replace(',', ' ')
        sheet.cell(row=row, column=4).value = f"{payment['principal_payment']:,.2f}".replace(',', ' ')
        sheet.cell(row=row, column=5).value = f"{payment['total_payment']:,.2f}".replace(',', ' ')
        
        for col in range(1, 6):
            cell = sheet.cell(row=row, column=col)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.fill = light_green_fill
            cell.border = thin_border
    
    row = len(payment_schedule) + 7
    sheet.cell(row=row, column=1).value = "Итого:"
    sheet.cell(row=row, column=3).value = f"{total_interest:,.2f}".replace(',', ' ')
    sheet.cell(row=row, column=5).value = f"{total_payment:,.2f}".replace(',', ' ')
    for col in [1, 3, 5]:
        cell = sheet.cell(row=row, column=col)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.fill = yellow_fill
        cell.border = thin_border
    
    for col_idx in range(1, 6):
        column_letter = openpyxl.utils.get_column_letter(col_idx)
        max_length = 0
        for row in range(1, sheet.max_row + 1):
            cell = sheet.cell(row=row, column=col_idx)
            if isinstance(cell, openpyxl.cell.cell.MergedCell):
                continue
            try:
                cell_value = str(cell.value)
                if len(cell_value) > max_length:
                    max_length = len(cell_value)
            except:
                pass
        adjusted_width = (max_length + 2) * 1.2
        sheet.column_dimensions[column_letter].width = adjusted_width
    
    workbook.save(excel_path)

def save_credit_calculation_to_history(user_id, principal, total_interest, total_payment, payment_schedule, timestamp_display):
    user_id_int = int(user_id) 
    user_id_str = str(user_id)  
    username = user_data[user_id_int].get('username', 'unknown')
    
    calculation_data = {
        'car_price': user_data[user_id_int]['car_price'],
        'down_payment': user_data[user_id_int]['down_payment'],
        'loan_term': user_data[user_id_int]['loan_term'],
        'interest_rate': user_data[user_id_int]['interest_rate'] * 100,
        'payment_scheme': user_data[user_id_int]['payment_scheme'],
        'has_extra_payments': user_data[user_id_int]['has_extra_payments'],
        'loan_date': user_data[user_id_int]['loan_date'].strftime("%d.%m.%Y"),
        'principal': principal,
        'total_interest': total_interest,
        'total_payment': total_payment,
        'timestamp': timestamp_display
    }
    
    if user_data[user_id_int]['has_extra_payments']:
        calculation_data['extra_payments'] = [
            {**ep, 'date': ep['date'].strftime("%d.%m.%Y")} 
            for ep in user_data[user_id_int]['extra_payments']
        ]
    
    if user_id_str not in user_history_kredit:
        user_history_kredit[user_id_str] = {
            'username': username,
            'autokredit_calculations': []
        }
    elif 'autokredit_calculations' not in user_history_kredit[user_id_str]:
        user_history_kredit[user_id_str]['autokredit_calculations'] = []
    
    user_history_kredit[user_id_str]['autokredit_calculations'].append(calculation_data)
    
    if not KREDIT_USERS_PATH.endswith('kredit_users.json'):
        raise ValueError("Попытка сохранить данные автокредита в неверный файл!")
    
    save_user_history_kredit()

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_АВТОКРЕДИТ (просмотр автокредитов) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Просмотр автокредитов")
@check_function_state_decorator('Просмотр автокредитов')
@track_usage('Просмотр автокредитов')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_view_autokredit(message):
    user_id = str(message.from_user.id)
    if user_id not in user_history_kredit or 'autokredit_calculations' not in user_history_kredit[user_id] or not user_history_kredit[user_id]['autokredit_calculations']:
        bot.send_message(message.chat.id, "❌ У вас нет сохраненных расчетов автокредитов!")
        view_autokredit_calc(message, show_description=False)
        return
    view_autokredit_calculations(message)

@text_only_handler
def view_autokredit_calculations(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if user_id not in user_history_kredit or 'autokredit_calculations' not in user_history_kredit[user_id] or not user_history_kredit[user_id]['autokredit_calculations']:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов автокредитов!")
        view_autokredit_calc(message, show_description=False)
        return

    calculations = user_history_kredit[user_id]['autokredit_calculations']
    message_text = "*Список ваших расчетов автокредитов:*\n\n"

    for i, calc in enumerate(calculations, 1):
        timestamp = calc['timestamp']
        message_text += f"🕒 *№{i}.* {timestamp}\n"

    msg = bot.send_message(chat_id, message_text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_view_autokredit_selection)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в автокредит')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    bot.send_message(chat_id, "Введите номера расчетов автокредита для просмотра:", reply_markup=markup)

@text_only_handler
def process_view_autokredit_selection(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    calculations = user_history_kredit.get(user_id, {}).get('autokredit_calculations', [])
    if not calculations:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов автокредитов!")
        view_autokredit_calc(message, show_description=False)
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
            markup.add('Вернуться в автокредит')
            markup.add('Вернуться в калькуляторы')
            markup.add('В главное меню')
            msg = bot.send_message(chat_id, "Некорректный ввод!\nВыберите существующие номера расчетов из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_view_autokredit_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(chat_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        for index in valid_indices:
            calc = calculations[index]
            result_message = (
                f"*📊 Итоговый расчет по автокредиту №{index + 1}:*\n\n"
                f"*Ваши данные:*\n\n"
                f"📅 *Дата выдачи:* {calc['loan_date']}\n"
                f"🚗 *Стоимость авто:* {calc['car_price']:,.2f} ₽\n"
                f"💰 *Первый платеж:* {calc['down_payment']:,.2f} ₽\n"
                f"⏳ *Срок кредита:* {calc['loan_term']} мес.\n"
                f"📈 *Процентная ставка:* {calc['interest_rate']:.2f}%\n"
                f"📋 *Схема оплаты:* {calc['payment_scheme']}\n"
                f"💸 *Дополнительные погашения:* {'Да' if calc['has_extra_payments'] else 'Нет'}\n"
            )

            if calc['has_extra_payments']:
                result_message += "\n*Дополнительные погашения:*\n"
                for i, extra in enumerate(calc['extra_payments'], 1):
                    result_message += (
                        f"\n*Погашение №{i}:*\n"
                        f"📅 *Дата:* {extra['date']}\n"
                        f"💰 *Сумма:* {extra['amount']:,.2f} ₽\n"
                        f"🔄 *Периодичность:* {extra['frequency']}\n"
                        f"🎯 *Цель:* {extra['target']}\n"
                    )

            result_message += (
                f"\n*Итоговый расчет:*\n\n"
                f"🏛️ *Сумма кредита:* {calc['principal']:,.2f} ₽\n"
                f"💸 *Сумма процентов:* {calc['total_interest']:,.2f} ₽\n"
                f"💰 *Общая выплата:* {calc['total_payment']:,.2f} ₽\n"
                f"🕒 *Дата расчета:* {calc['timestamp']}"
            )

            bot.send_message(chat_id, result_message, parse_mode='Markdown')

            timestamp = calc['timestamp'].replace(' в ', '_').replace('.', '_').replace(':', '_')
            excel_path = EXCEL_PATH_TEMPLATE.format(user_id=user_id, timestamp=timestamp)
            if os.path.exists(excel_path):
                with open(excel_path, 'rb') as file:
                    bot.send_document(chat_id, file, caption=f"📅 Календарь выплат для расчета №{index + 1}")
            else:
                bot.send_message(chat_id, "❌ Excel-файл для этого расчета не найден!")

        view_autokredit_calc(message, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Некорректный ввод!\nВведите числа через запятую", reply_markup=markup)
        bot.register_next_step_handler(msg, process_view_autokredit_selection)

# ------------------------------------------- КАЛЬКУЛЯТОРЫ_АВТОКРЕДИТ (удаление автокредитов) --------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Удаление автокредитов")
@check_function_state_decorator('Удаление автокредитов')
@track_usage('Удаление автокредитов')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_delete_autokredit(message):
    user_id = str(message.from_user.id)
    if user_id not in user_history_kredit or 'autokredit_calculations' not in user_history_kredit[user_id] or not user_history_kredit[user_id]['autokredit_calculations']:
        bot.send_message(message.chat.id, "❌ У вас нет сохраненных расчетов автокредитов!")
        view_autokredit_calc(message, show_description=False)
        return
    delete_autokredit_calculations(message)

@text_only_handler
def delete_autokredit_calculations(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    if user_id not in user_history_kredit or 'autokredit_calculations' not in user_history_kredit[user_id] or not user_history_kredit[user_id]['autokredit_calculations']:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов автокредитов!")
        view_autokredit_calc(message, show_description=False)
        return

    calculations = user_history_kredit[user_id]['autokredit_calculations']
    message_text = "*Список ваших расчетов автокредитов:*\n\n"

    for i, calc in enumerate(calculations, 1):
        timestamp = calc['timestamp']
        message_text += f"🕒 *№{i}.* {timestamp}\n"

    msg = bot.send_message(chat_id, message_text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_delete_autokredit_selection)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в автокредит')
    markup.add('Вернуться в калькуляторы')
    markup.add('В главное меню')
    bot.send_message(chat_id, "Введите номера для удаления расчетов:", reply_markup=markup)

@text_only_handler
def process_delete_autokredit_selection(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в автокредит":
        view_autokredit_calc(message, show_description=False)
        return
    if message.text == "Вернуться в калькуляторы":
        return_to_calculators(message)
        return

    chat_id = message.chat.id
    user_id = str(message.from_user.id)

    calculations = user_history_kredit.get(user_id, {}).get('autokredit_calculations', [])
    if not calculations:
        bot.send_message(chat_id, "❌ У вас нет сохраненных расчетов автокредитов!")
        view_autokredit_calc(message, show_description=False)
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
            markup.add('Вернуться в автокредит')
            markup.add('Вернуться в калькуляторы')
            markup.add('В главное меню')
            msg = bot.send_message(chat_id, "Некорректный ввод!\nВыберите существующие номера расчетов из списка", reply_markup=markup)
            bot.register_next_step_handler(msg, process_delete_autokredit_selection)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(chat_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        valid_indices.sort(reverse=True)
        for index in valid_indices:
            calc = calculations[index]
            timestamp = calc['timestamp'].replace(' в ', '_').replace('.', '_').replace(':', '_')
            excel_path = EXCEL_PATH_TEMPLATE.format(user_id=user_id, timestamp=timestamp)
            if os.path.exists(excel_path):
                os.remove(excel_path)
            del calculations[index]

        save_user_history_kredit()
        bot.send_message(chat_id, "✅ Выбранные расчеты автокредитов успешно удалены!")
        view_autokredit_calc(message, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в автокредит')
        markup.add('Вернуться в калькуляторы')
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "Некорректный ввод!\nВведите числа через запятую", reply_markup=markup)
        bot.register_next_step_handler(msg, process_delete_autokredit_selection)