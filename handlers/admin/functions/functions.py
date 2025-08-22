from core.imports import wraps, telebot, types, os, json, re, threading, datetime, timedelta, ApiTelegramException
from core.bot_instance import bot, BASE_DIR
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from decorators.blocked_user import load_blocked_users, save_blocked_users
from handlers.admin.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha,
)

# -------------------------------------------------- ФУНКЦИИ ---------------------------------------------------

ADMIN_SESSIONS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')
FUNCTIONS_STATE_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'functions', 'functions_state.json')

def check_admin_access(message):
    admin_sessions = load_admin_sessions()
    if str(message.chat.id) in admin_sessions:
        return True
    else:
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return False

def load_admin_sessions():
    try:
        with open(ADMIN_SESSIONS_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data['admin_sessions']
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def load_function_states():
    if os.path.exists(FUNCTIONS_STATE_PATH):
        try:
            with open(FUNCTIONS_STATE_PATH, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if data:
                    return data
        except json.JSONDecodeError:
            pass
    save_function_states({})
    return {}

def save_function_states(states):
    os.makedirs(os.path.dirname(FUNCTIONS_STATE_PATH), exist_ok=True)
    with open(FUNCTIONS_STATE_PATH, 'w', encoding='utf-8') as file:
        json.dump(states, file, ensure_ascii=False, indent=4)

function_states = load_function_states()

def load_functions_and_permissions():
    json_dir = os.path.join(BASE_DIR, 'files', 'files_for_bot')
    json_path = os.path.join(json_dir, 'functions_and_permissions.json')
    
    os.makedirs(json_dir, exist_ok=True)
    
    if not os.path.exists(json_path):
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({"new_functions": {}, "all_permissions": [], "main_functions": []}, f, ensure_ascii=False, indent=4)
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('new_functions', {}), data.get('all_permissions', []), data.get('main_functions', [])
    except json.JSONDecodeError:
        return {}, [], []
    
NEW_FUNCTIONS, ALL_PERMISSIONS, MAIN_FUNCTIONS = load_functions_and_permissions()

def update_function_states():
    global function_states
    updated = False
    for category, functions in NEW_FUNCTIONS.items():
        for function_name in functions:
            if function_name not in function_states:
                function_states[function_name] = {"state": True, "deactivation_time": None}
                updated = True
    if updated:
        save_function_states(function_states)

update_function_states()

def activate_function(function_name):
    return set_function_state(function_name, True)

def activate_function_later(function_name, delay):
    threading.Timer(delay.total_seconds(), lambda: notify_admin_and_activate(function_name)).start()

def deactivate_function(function_name, deactivation_time):
    return set_function_state(function_name, False, deactivation_time)

def set_function_state(function_name, state, deactivation_time=None):
    if function_name in function_states:
        function_states[function_name]['state'] = state
        function_states[function_name]['deactivation_time'] = deactivation_time
        save_function_states(function_states)
        return f"✅ Функция *{function_name}* успешно {'активирована' if state else 'деактивирована'}!"
    else:
        return "❌ Функция не найдена!"

@bot.message_handler(func=lambda message: message.text == 'Функции' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def toggle_functions(message):
    admin_id = str(message.chat.id)
    blocked_users = load_blocked_users()

    if admin_id in blocked_users:
        return

    if not check_permission(admin_id, 'Функции'):
        try:
            bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                pass
                if admin_id not in blocked_users:
                    blocked_users.append(admin_id)
                    save_blocked_users(blocked_users)
            else:
                raise e
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton('Включение'), types.KeyboardButton('Выключение'))
    markup.add(types.KeyboardButton('В меню админ-панели'))
    try:
        bot.send_message(message.chat.id, "Выберите действие для функций:", reply_markup=markup)
    except ApiTelegramException as e:
        if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
            pass
            if admin_id not in blocked_users:
                blocked_users.append(admin_id)
                save_blocked_users(blocked_users)
        else:
            raise e

# -------------------------------------------------- ФУНКЦИИ (включение) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Включение' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def enable_function(message):
    admin_id = str(message.chat.id)
    blocked_users = load_blocked_users()

    if admin_id in blocked_users:
        return

    if not check_permission(admin_id, 'Включение'):
        try:
            bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                pass
                if admin_id not in blocked_users:
                    blocked_users.append(admin_id)
                    save_blocked_users(blocked_users)
            else:
                raise e
        return

    disabled_functions = [(name, data['deactivation_time']) for name, data in function_states.items() if not data['state']]
    if disabled_functions:
        response = "*Выключенные функции:*\n\n"
        index = 1
        function_index_map = {}
        messages_to_send = []
        current_message = response

        for category, functions in NEW_FUNCTIONS.items():
            for function in functions:
                if function in [name for name, _ in disabled_functions]:
                    deactivation_time = next((data for name, data in disabled_functions if name == function), None)
                    if deactivation_time:
                        date_part, time_part = deactivation_time.split('; ')
                        line = f"❌ {index}. {function} (до {date_part} в {time_part})\n"
                    else:
                        line = f"❌ {index}. {function}\n"
                    if len(current_message) + len(line) > 4000:
                        messages_to_send.append(current_message)
                        current_message = ""
                    current_message += line
                    function_index_map[index] = function
                    index += 1

        if current_message:
            messages_to_send.append(current_message)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('Вернуться в функции'))
        markup.add(types.KeyboardButton('В меню админ-панели'))

        for msg in messages_to_send:
            try:
                bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup if msg == messages_to_send[-1] else None)
            except ApiTelegramException as e:
                if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                    pass
                    if admin_id not in blocked_users:
                        blocked_users.append(admin_id)
                        save_blocked_users(blocked_users)
                else:
                    raise e

        bot.send_message(message.chat.id, "Введите номера функций для включения:")
        bot.register_next_step_handler(message, process_enable_function_step, function_index_map)
    else:
        try:
            bot.send_message(message.chat.id, "✅ Все функции уже *включены*!", parse_mode="Markdown")
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                pass
                if admin_id not in blocked_users:
                    blocked_users.append(admin_id)
                    save_blocked_users(blocked_users)
            else:
                raise e
        toggle_functions(message)

@text_only_handler
def process_enable_function_step(message, function_index_map):
    if message.text == "Вернуться в функции":
        toggle_functions(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        function_indices = [int(index.strip()) for index in message.text.split(',')]
        function_names = []
        invalid_numbers = []

        for i in function_indices:
            if i in function_index_map:
                function_names.append(function_index_map[i])
            else:
                invalid_numbers.append(i)

        if invalid_numbers:
            bot.send_message(message.chat.id, f"❌ Неверные номера функций: *{', '.join(map(str, invalid_numbers))}*! Они будут пропущены...", parse_mode="Markdown")

        if function_names:
            for function_name in function_names:
                activate_function(function_name)
            bot.send_message(message.chat.id, f"✅ Функции *{', '.join(function_names).lower()}* успешно *активированы*!", parse_mode="Markdown")
            toggle_functions(message)
        else:
            bot.send_message(message.chat.id, "❌ Неверные номера функций!")
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат! Введите номера функций через запятую")

def notify_admin_and_activate(function_name):
    deactivation_time = function_states[function_name]['deactivation_time']
    if deactivation_time is None:
        date_part = "не установлено"
        time_part = "не установлено"
    else:
        date_part, time_part = deactivation_time.split('; ')

    admin_sessions = load_admin_sessions()
    blocked_users = load_blocked_users()

    activated_functions = [fn for fn, data in function_states.items() if not data['state']]

    for admin_id in admin_sessions:
        if admin_id in blocked_users:
            continue

        try:
            if len(activated_functions) == 1:
                bot.send_message(admin_id, f"✅ Функция *{function_name.lower()}* была *включена* по истечению времени (до {date_part} в {time_part})!", parse_mode="Markdown")
            else:
                bot.send_message(admin_id, f"✅ Функции *{', '.join(activated_functions).lower()}* были *включены* по истечению времени (до {date_part} в {time_part})!", parse_mode="Markdown")
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                pass
                if admin_id not in blocked_users:
                    blocked_users.append(admin_id)
                    save_blocked_users(blocked_users)
            else:
                raise e

    activate_function(function_name)

# -------------------------------------------------- ФУНКЦИИ (выключение) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Выключение' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def disable_function(message):
    admin_id = str(message.chat.id)
    blocked_users = load_blocked_users()

    if admin_id in blocked_users:
        return

    if not check_permission(admin_id, 'Выключение'):
        try:
            bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                pass
                if admin_id not in blocked_users:
                    blocked_users.append(admin_id)
                    save_blocked_users(blocked_users)
            else:
                raise e
        return

    enabled_functions = [name for name, data in function_states.items() if data['state']]
    if enabled_functions:
        response = "*Включенные функции:*\n\n"
        index = 1
        function_index_map = {}
        messages_to_send = []
        current_message = response

        for category, functions in NEW_FUNCTIONS.items():
            for function in functions:
                if function in enabled_functions:
                    line = f"✅ {index}. {function}\n"
                    if len(current_message) + len(line) > 4000: 
                        messages_to_send.append(current_message)
                        current_message = ""  
                    current_message += line
                    function_index_map[index] = function
                    index += 1

        if current_message:
            messages_to_send.append(current_message)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('Вернуться в функции'))
        markup.add(types.KeyboardButton('В меню админ-панели'))

        for msg in messages_to_send:
            try:
                bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=markup if msg == messages_to_send[-1] else None)
            except ApiTelegramException as e:
                if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                    pass
                    if admin_id not in blocked_users:
                        blocked_users.append(admin_id)
                        save_blocked_users(blocked_users)
                else:
                    raise e

        bot.send_message(message.chat.id, "Введите номера функций для выключения:")
        bot.register_next_step_handler(message, process_disable_function_step, function_index_map)
    else:
        try:
            bot.send_message(message.chat.id, "✅ Все функции уже *выключены*!", parse_mode="Markdown")
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                pass
                if admin_id not in blocked_users:
                    blocked_users.append(admin_id)
                    save_blocked_users(blocked_users)
            else:
                raise e
        toggle_functions(message)

@text_only_handler
def process_disable_function_step(message, function_index_map):
    if message.text == "Вернуться в функции":
        toggle_functions(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        function_indices = [int(index.strip()) for index in message.text.split(',')]
        function_names = []
        invalid_numbers = []

        for i in function_indices:
            if i in function_index_map:
                function_names.append(function_index_map[i])
            else:
                invalid_numbers.append(i)

        if invalid_numbers:
            bot.send_message(message.chat.id, f"❌ Неверные номера функций: *{', '.join(map(str, invalid_numbers))}*! Они будут пропущены...", parse_mode="Markdown")

        if function_names:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton('Вернуться в функции'))
            markup.add(types.KeyboardButton('В меню админ-панели'))
            bot.send_message(message.chat.id, "Введите дату в формате ДД.ММ.ГГГГ для выключения:", reply_markup=markup)
            bot.register_next_step_handler(message, process_disable_function_date_step, function_names)
        else:
            bot.send_message(message.chat.id, "❌ Неверные номера функций!")
            bot.register_next_step_handler(message, process_disable_function_step, function_index_map)
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат! Введите номера функций через запятую")
        bot.register_next_step_handler(message, process_disable_function_step, function_index_map)

@text_only_handler
def process_disable_function_date_step(message, function_names):
    admin_id = str(message.chat.id)
    blocked_users = load_blocked_users()

    if admin_id in blocked_users:
        return

    if message.text == "Вернуться в функции":
        toggle_functions(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    date_str = message.text
    if is_valid_date_time(date_str, "00:00"):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('Вернуться в функции'))
        markup.add(types.KeyboardButton('В меню админ-панели'))
        try:
            bot.send_message(message.chat.id, "Введите время в формате ЧЧ:ММ для выключения:", reply_markup=markup)
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                if admin_id not in blocked_users:
                    blocked_users.append(admin_id)
                    save_blocked_users(blocked_users)
            else:
                raise e
        bot.register_next_step_handler(message, process_disable_function_time_step, function_names, date_str, message)
    else:
        try:
            bot.send_message(message.chat.id, "Неверный формат даты! Попробуйте снова")
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                if admin_id not in blocked_users:
                    blocked_users.append(admin_id)
                    save_blocked_users(blocked_users)
            else:
                raise e
        bot.register_next_step_handler(message, process_disable_function_date_step, function_names)

def is_valid_date_time(date_str, time_str):
    try:
        date = datetime.strptime(date_str, "%d.%m.%Y")
        time = datetime.strptime(time_str, "%H:%M")
        if 2000 <= date.year <= 3000 and 1 <= date.month <= 12 and 1 <= date.day <= 31:
            if 0 <= time.hour <= 23 and 0 <= time.minute <= 59:
                return True
        return False
    except ValueError:
        return False

@text_only_handler
def process_disable_function_time_step(message, function_names, date_str, original_message):
    admin_id = str(message.chat.id)
    blocked_users = load_blocked_users()

    if admin_id in blocked_users:
        return

    if message.text == "Вернуться в функции":
        toggle_functions(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    time_str = message.text
    if is_valid_date_time(date_str, time_str):
        time_spec = f"{date_str}; {time_str}"
        handle_time_deactivation(time_spec, function_names, original_message)
    else:
        try:
            bot.send_message(message.chat.id, "Неверный формат времени! Попробуйте снова")
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                if admin_id not in blocked_users:
                    blocked_users.append(admin_id)
                    save_blocked_users(blocked_users)
            else:
                raise e
        bot.register_next_step_handler(message, process_disable_function_time_step, function_names, date_str, original_message)

def handle_time_deactivation(time_spec, function_names, message):
    try:
        end_time = datetime.strptime(time_spec, "%d.%m.%Y; %H:%M")
        now = datetime.now()

        if end_time > now:
            for function_name in function_names:
                deactivate_function(function_name, time_spec)
                delay = end_time - now
                activate_function_later(function_name, delay)
            date_part, time_part = time_spec.split('; ')

            blocked_users = load_blocked_users()

            if message.chat.id in blocked_users:
                return

            try:
                if len(function_names) == 1:
                    bot.send_message(message.chat.id, f"✅ Функция *{', '.join(function_names).lower()}* *отключена* до {date_part} в {time_part}!", parse_mode="Markdown")
                else:
                    bot.send_message(message.chat.id, f"✅ Функции *{', '.join(function_names).lower()}* *отключены* до {date_part} в {time_part}!", parse_mode="Markdown")
            except ApiTelegramException as e:
                if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                    pass
                    if message.chat.id not in blocked_users:
                        blocked_users.append(message.chat.id)
                        save_blocked_users(blocked_users)
                else:
                    raise e

            toggle_functions(message)
        else:
            bot.send_message(message.chat.id, "Указанное время уже прошло! Пожалуйста, введите дату и время снова")
            bot.register_next_step_handler(message, process_disable_function_date_step, function_names)
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат! Попробуйте снова")
        bot.register_next_step_handler(message, process_disable_function_date_step, function_names)