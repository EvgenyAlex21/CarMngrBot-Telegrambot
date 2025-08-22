from core.imports import wraps, telebot, types, os, json, re, hashlib, time, ApiTelegramException
from core.bot_instance import bot, BASE_DIR
from decorators.blocked_user import load_blocked_users, save_blocked_users
from handlers.admin import admin_main_menu as _admin_main
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

admins_data = _admin_main.admins_data
admin_sessions = _admin_main.admin_sessions
removed_admins = _admin_main.removed_admins
save_admin_data = _admin_main.save_admin_data
login_password_hash = _admin_main.login_password_hash
show_admin_panel = _admin_main.show_admin_panel
return_to_menu = _admin_main.return_to_menu
check_permission = _admin_main.check_permission

def check_admin_access(message):
    return str(message.chat.id) in admin_sessions

def _all_permissions():
    from handlers.admin.functions.functions import ALL_PERMISSIONS as _P
    return _P

def _main_functions():
    from handlers.admin.functions.functions import MAIN_FUNCTIONS as _M
    return _M

# -------------------------------------------------- АДМИН ---------------------------------------------------

blocked_users = load_blocked_users()

def escape_markdown(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def get_root_admin_id():
    try:
        return _admin_main.get_root_admin_id()
    except Exception:
        return next(iter(admins_data)) if admins_data else None

def is_root_admin(admin_id):
    try:
        return _admin_main.is_root_admin(admin_id)
    except Exception:
        return str(admin_id) == str(get_root_admin_id())

def generate_login_password_hash(username, password):
    return hashlib.sha256(f"{username}:{password}".encode()).hexdigest()

users_db_path = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'users.json')

def ensure_directory_exists(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def load_users_data():
    ensure_directory_exists(users_db_path)

    if not os.path.exists(users_db_path):
        with open(users_db_path, 'w', encoding='utf-8') as file:
            json.dump({}, file)
        return {}

    with open(users_db_path, 'r', encoding='utf-8') as file:
        content = file.read().strip()
        if not content:
            return {}
        return json.loads(content)

users_data = load_users_data()

@bot.message_handler(func=lambda message: message.text == 'Админ' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_settings_menu(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Админ'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add('Смена данных входа')
    markup.add('Добавить админа', 'Удалить админа', 'Права доступа')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите настройку:", reply_markup=markup)

# -------------------------------------------------- АДМИН (смена данных входа) ---------------------------------------------------

def is_valid_username(username):
    if len(username) < 3:
        return False, "Логин должен содержать не менее 3 символов"
    if not re.search(r'[A-Z]', username):
        return False, "Логин должен содержать хотя бы одну заглавную букву"
    if not re.search(r'[a-z]', username):
        return False, "Логин должен содержать хотя бы одну строчную букву"
    if not re.search(r'[0-9]', username):
        return False, "Логин должен содержать хотя бы одну цифру"
    return True, ""

def is_valid_password(password):
    if len(password) < 8:
        return False, "Пароль должен содержать не менее 8 символов"
    if not re.search(r'[A-Z]', password):
        return False, "Пароль должен содержать хотя бы одну заглавную букву"
    if not re.search(r'[a-z]', password):
        return False, "Пароль должен содержать хотя бы одну строчную букву"
    if not re.search(r'[0-9]', password):
        return False, "Пароль должен содержать хотя бы одну цифру"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Пароль должен содержать хотя бы один специальный символ"
    return True, ""

@bot.message_handler(func=lambda message: message.text == 'Смена данных входа' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_change_credentials(message):
    global credentials_changed
    admin_id = str(message.chat.id)
    admin_data = admins_data.get(admin_id, {})

    if not check_permission(admin_id, 'Смена данных входа'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    has_credentials = admin_data.get("admins_username") and admin_data.get("login_password_hash_for_user_id")

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if has_credentials:
        markup.add('Сменить пароль')
    markup.add('Сменить логин и пароль')
    bot.send_message(message.chat.id, "Выберите, что хотите изменить:", reply_markup=markup)

# -------------------------------------------------- АДМИН (сменить пароль) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Сменить пароль' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_change_password(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Сменить пароль'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню админ-панели')
    password_requirements = (
        "🔒 Введите новый пароль\n\n"
        "Требования к паролю:\n"
        "- 🔢 Не менее 8 символов\n"
        "- 🔡 Хотя бы одна заглавная буква\n"
        "- 🔠 Хотя бы одна строчная буква\n"
        "- 🔢 Хотя бы одна цифра\n"
        "- 🔣 Хотя бы один специальный символ (например, !@#$%^&*(),.?\":{}|<>)"
    )
    msg = bot.send_message(message.chat.id, password_requirements, reply_markup=markup)
    bot.register_next_step_handler(msg, process_new_password)

@text_only_handler
def process_new_password(message):

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    new_password = message.text
    is_valid, error_message = is_valid_password(new_password)
    if not is_valid:
        bot.send_message(message.chat.id, f"Ошибка: {error_message}! Попробуйте снова")
        bot.register_next_step_handler(message, process_new_password)
        return

    if not is_password_unique(new_password):
        bot.send_message(message.chat.id, "⚠️ Этот пароль уже используется! Попробуйте другой...")
        bot.register_next_step_handler(message, process_new_password)
        return

    update_admin_login_credentials(message, message.chat.id, new_password=new_password)
    bot.delete_message(message.chat.id, message.message_id)   

# -------------------------------------------------- АДМИН (сменить логин и пароль) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Сменить логин и пароль' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_change_login_and_password(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Сменить логин и пароль'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню админ-панели')
    login_requirements = (
        "🔒 Введите новый логин\n\n"
        "Требования к логину:\n"
        "- 🔢 Не менее 3 символов\n"
        "- 🔡 Хотя бы одна заглавная буква\n"
        "- 🔠 Хотя бы одна строчная буква\n"
        "- 🔢 Хотя бы одна цифра"
    )
    msg = bot.send_message(message.chat.id, login_requirements, reply_markup=markup)
    bot.register_next_step_handler(msg, process_new_login_and_password_step1)

@text_only_handler
def process_new_login_and_password_step1(message):

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return
    new_login = message.text
    is_valid, error_message = is_valid_username(new_login)
    if not is_valid:
        bot.send_message(message.chat.id, f"Ошибка: {error_message}! Попробуйте снова")
        bot.register_next_step_handler(message, process_new_login_and_password_step1)
        return
    if any(admin.get("admins_username") == new_login for admin in admins_data.values()):
        bot.send_message(message.chat.id, "⚠️ Этот логин уже существует! Попробуйте другой...")
        bot.register_next_step_handler(message, process_new_login_and_password_step1)
        return
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню админ-панели')
    password_requirements = (
        "🔒 Введите новый пароль\n\n"
        "Требования к паролю:\n"
        "- 🔢 Не менее 8 символов\n"
        "- 🔡 Хотя бы одна заглавная буква\n"
        "- 🔠 Хотя бы одна строчная буква\n"
        "- 🔢 Хотя бы одна цифра\n"
        "- 🔣 Хотя бы один специальный символ (например, !@#$%^&*(),.?\":{}|<>)"
    )
    msg = bot.send_message(message.chat.id, password_requirements, reply_markup=markup)
    bot.register_next_step_handler(msg, process_new_login_and_password_step2, new_login)
    bot.delete_message(message.chat.id, message.message_id)  

@text_only_handler
def process_new_login_and_password_step2(message, new_login):

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    new_password = message.text
    is_valid, error_message = is_valid_password(new_password)
    if not is_valid:
        bot.send_message(message.chat.id, f"Ошибка: {error_message}! Попробуйте снова")
        bot.register_next_step_handler(message, process_new_login_and_password_step2, new_login)
        return

    if not is_password_unique(new_password):
        bot.send_message(message.chat.id, "⚠️ Этот пароль уже используется! Попробуйте другой...")
        bot.register_next_step_handler(message, process_new_login_and_password_step2, new_login)
        return

    update_admin_login_credentials(message, message.chat.id, new_username=new_login, new_password=new_password)
    bot.delete_message(message.chat.id, message.message_id)   

# -------------------------------------------------- АДМИН (сменить пароль и логин и пароль) ---------------------------------------------------

def is_password_unique(new_password):
    for admin_data in admins_data.values():
        current_password_hash = admin_data.get("login_password_hash_for_user_id", "")
        current_username = admin_data.get("admins_username", "")
        if generate_login_password_hash(current_username, new_password) == current_password_hash:
            return False
    return True

def update_admin_login_credentials(message, admin_id, new_username=None, new_password=None):
    global credentials_changed
    admin_id = str(admin_id)
    if admin_id not in admins_data:
        bot.send_message(admin_id, "❌ Администратор не найден!")
        return

    current_username = admins_data[admin_id].get("admins_username", "")
    current_password_hash = admins_data[admin_id].get("login_password_hash_for_user_id", "")

    if new_username:
        current_username = new_username

    if new_password:
        current_password_hash = generate_login_password_hash(current_username, new_password)

    admins_data[admin_id]["admins_username"] = current_username
    admins_data[admin_id]["login_password_hash_for_user_id"] = current_password_hash
    admins_data[admin_id]["is_new"] = False
    save_admin_data(admin_sessions, admins_data, login_password_hash)
    bot.send_message(admin_id, "✅ Данные входа успешно обновлены!")

    credentials_changed = True

    bot.send_message(admin_id, "⚠️ Данные входа изменены!\n\n🔒 Пожалуйста, авторизуйтесь заново, используя команду /admin")
    return_to_menu(message)

# -------------------------------------------------- АДМИН (добавить админа) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Добавить админа' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_add_admin(message):
    root_admin_id = get_root_admin_id()
    if str(message.chat.id) != root_admin_id:
        bot.send_message(message.chat.id, "⛔️ Недостаточно прав! Только корневой администратор может добавлять администраторов!")
        return

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Добавить админа'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    users_data = load_users_data()
    user_list = []
    for user_id, data in users_data.items():
        username = escape_markdown(data.get('username', 'неизвестный'))
        user_list.append(f"№{len(user_list) + 1}. {username} - `{user_id}`")

    if user_list:
        response_message = "📋 Список *пользователей*:\n\n" + "\n\n".join(user_list)
        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    if removed_admins:
        removed_admin_list = []
        for admin_id, data in removed_admins.items():
            username = escape_markdown(data['username'])
            removed_admin_list.append(f"№{len(removed_admin_list) + 1}. {username} - `{admin_id}`")

        response_message = "📋 Список *удалённых администраторов*:\n\n" + "\n".join(removed_admin_list)
        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('Вернуться в админ')
    markup.add('В меню админ-панели')
    bot.send_message(
        message.chat.id,
        "Введите *номера*, *id* или *username* пользователей или удалённых администраторов для добавления:",
        reply_markup=markup, parse_mode="Markdown"
    )
    bot.register_next_step_handler(message, process_add_admin, root_admin_id, message.chat.id)

def list_removed_admins(message):
    removed_admin_list = []
    for admin_id, data in removed_admins.items():
        username = escape_markdown(data['username'])
        removed_admin_list.append(f"№{len(removed_admin_list) + 1}. {username} - `{admin_id}`")

    if removed_admin_list:
        response_message = "📋 Список *удалённых* администраторов:\n\n" + "\n\n".join(removed_admin_list)
        if len(response_message) > 4096:
            bot.send_message(message.chat.id, "📜 Список удалённых администраторов слишком большой для отправки в одном сообщении!")
        else:
            bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('Вернуться в админ')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите *номера*, *id* или *username* администраторов для добавления:", reply_markup=markup)

def process_add_admin(message, root_admin_id, initiator_chat_id):
    if message.text == "Вернуться в админ":
        show_settings_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    input_data = message.text.strip()
    admin_ids = []

    parts = input_data.split(',')
    for part in parts:
        part = part.strip()
        if part.isdigit():
            if len(part) < 5:
                index = int(part) - 1
                if 0 <= index < len(users_data):
                    user_id = list(users_data.keys())[index]
                    admin_ids.append(user_id)
                else:
                    bot.send_message(message.chat.id, f"❌ Такого пользователя с *номером* `{part}` не существует! Попробуйте еще раз", parse_mode="Markdown")
                    bot.register_next_step_handler(message, process_add_admin, root_admin_id, initiator_chat_id)
                    return
            else:
                user_id = part
                if user_id not in users_data and user_id not in removed_admins:
                    bot.send_message(message.chat.id, f"❌ Такого пользователя с *id* `{user_id}` не существует! Попробуйте еще раз", parse_mode="Markdown")
                    bot.register_next_step_handler(message, process_add_admin, root_admin_id, initiator_chat_id)
                    return
                admin_ids.append(user_id)
        else:
            username = part
            user_id = next(
                (user_id for user_id, data in users_data.items() if data.get("username") == username),
                None
            )
            if not user_id:
                bot.send_message(message.chat.id, f"❌ Такого пользователя с *username* {escape_markdown(username)} не существует! Попробуйте еще раз", parse_mode="Markdown")
                bot.register_next_step_handler(message, process_add_admin, root_admin_id, initiator_chat_id)
                return
            admin_ids.append(user_id)

    for admin_id in admin_ids:
        if admin_id in admins_data:
            username = users_data.get(admin_id, {}).get("username", "неизвестный")
            bot.send_message(message.chat.id, f"❌ Администратор с {escape_markdown(username)} - `{admin_id}` уже существует!", parse_mode="Markdown")
            continue
        username = users_data[admin_id]["username"]
        add_admin(admin_id, username, permissions=["Админ", "Смена данных входа", "Сменить пароль", "Сменить логин и пароль", "Статистика", "Пользователи", "Использование функций", "Список ошибок", "Версия и аптайм"], initiator_chat_id=initiator_chat_id)
        if admin_id in removed_admins:
            del removed_admins[admin_id]

    save_admin_data(admin_sessions, admins_data, login_password_hash, removed_admins)
    show_settings_menu(message)

def add_admin(admin_id, username, permissions=None, initiator_chat_id=None):
    admin_id = str(admin_id)
    if permissions is None:
        permissions = ["Админ", "Смена данных входа", "Сменить пароль", "Сменить логин и пароль", "Статистика", "Пользователи", "Использование функций", "Список ошибок", "Версия и аптайм"]
    user_data = {
        "user_id": admin_id,
        "first_name": " ",
        "last_name": " ",
        "username": username,
        "phone": " ",
        "permissions": permissions,
        "is_new": True
    }
    admins_data[admin_id] = user_data
    admin_sessions.append(admin_id)
    save_admin_data(admin_sessions, admins_data, login_password_hash, removed_admins)

    try:
        bot.send_message(admin_id, "✅ Вы стали администратором! Быстрый вход по команде /admin доступен...")
        if initiator_chat_id:
            bot.send_message(initiator_chat_id, f"✅ Администратор {escape_markdown(username)} - `{admin_id}` успешно добавлен!", parse_mode="Markdown")
    except ApiTelegramException as e:
        if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
            if admin_id not in blocked_users:
                blocked_users.append(admin_id)
                save_blocked_users(blocked_users)
        else:
            raise e

# -------------------------------------------------- АДМИН (удалить админа) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Удалить админа' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_remove_admin(message):
    root_admin_id = get_root_admin_id()
    if str(message.chat.id) != root_admin_id:
        bot.send_message(message.chat.id, "⛔️ Недостаточно прав! Только корневой администратор может удалять администраторов!")
        return

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Удалить админа'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    list_admins_for_removal(message)
    bot.register_next_step_handler(message, process_remove_admin, root_admin_id, message.chat.id)

def list_admins_for_removal(message):
    admin_list = []
    for admin_id, data in admins_data.items():
        username = escape_markdown(data['username'])
        admin_list.append(f"№{len(admin_list) + 1}. {username} - `{admin_id}`")

    if admin_list:
        response_message = "📋 Список *всех* администраторов:\n\n" + "\n\n".join(admin_list)
        if len(response_message) > 4096:
            bot.send_message(message.chat.id, "📜 Список администраторов слишком большой для отправки в одном сообщении!")
        else:
            bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('Вернуться в админ')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите *номера*, *id* или *username* администраторов для удаления:", reply_markup=markup, parse_mode="Markdown")

admin_sessions_db_path = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')

def ensure_directory_exists(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def load_admin_sessions_data():
    ensure_directory_exists(admin_sessions_db_path)

    if not os.path.exists(admin_sessions_db_path):
        with open(admin_sessions_db_path, 'w', encoding='utf-8') as file:
            json.dump({}, file) 

    with open(admin_sessions_db_path, 'r', encoding='utf-8') as file:
        return json.load(file)

admin_sessions_data = load_admin_sessions_data()

def process_remove_admin(message, root_admin_id, initiator_chat_id):

    if message.text == "Вернуться в админ":
        show_settings_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    input_data = message.text.strip()
    admin_ids = []

    parts = input_data.split(',')
    for part in parts:
        part = part.strip()
        if part.isdigit() and len(part) < 5:
            index = int(part) - 1
            if 0 <= index < len(admins_data):
                admin_id = list(admins_data.keys())[index]
                admin_ids.append(admin_id)
            else:
                bot.send_message(message.chat.id, f"❌ Такого администратора с *номером* `{part}` не существует! Попробуйте еще раз", parse_mode="Markdown")
                bot.register_next_step_handler(message, process_remove_admin, root_admin_id, initiator_chat_id)
                return
        elif part.isdigit():
            admin_id = part
            if admin_id not in admins_data:
                bot.send_message(message.chat.id, f"❌ Такого администратора с *id* `{admin_id}` не существует! Попробуйте еще раз", parse_mode="Markdown")
                bot.register_next_step_handler(message, process_remove_admin, root_admin_id, initiator_chat_id)
                return
            admin_ids.append(admin_id)
        else:
            username = part
            admin_id = next(
                (user_id for user_id, data in admins_data.items() if data.get("username") == username),
                None
            )
            if not admin_id:
                bot.send_message(message.chat.id, f"❌ Такого администратора с *username* {escape_markdown(username)} не существует! Попробуйте еще раз", parse_mode="Markdown")
                bot.register_next_step_handler(message, process_remove_admin, root_admin_id, initiator_chat_id)
                return
            admin_ids.append(admin_id)

    for admin_id in admin_ids:
        if str(message.chat.id) == admin_id:
            bot.send_message(message.chat.id, "❌ Невозможно удалить самого себя!")
            continue
        if admin_id == root_admin_id:
            bot.send_message(message.chat.id, "❌ Невозможно удалить корневого администратора!")
            continue
        remove_admin(admin_id, initiator_chat_id)

    show_settings_menu(message)

def remove_admin(admin_id, initiator_chat_id):
    admin_id = str(admin_id)
    if admin_id in admins_data:
        admin_username = admins_data[admin_id]["username"]
        removed_admins[admin_id] = {"username": admin_username}

        del admins_data[admin_id]
        if admin_id in admin_sessions:
            admin_sessions.remove(admin_id)

        save_admin_data(admin_sessions, admins_data, login_password_hash, removed_admins)

        try:
            bot.send_message(admin_id, "🚫 Вас удалили из администраторов!")
            bot.send_message(initiator_chat_id, f"✅ Администратор {escape_markdown(admin_username)} - `{admin_id}` успешно удален!", parse_mode="Markdown")
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                if admin_id not in blocked_users:
                    blocked_users.append(admin_id)
                    save_blocked_users(blocked_users)
            else:
                raise e
    else:
        bot.send_message(initiator_chat_id, f"❌ Администратор с *id* `{admin_id}` не найден!", parse_mode="Markdown")

# -------------------------------------------------- АДМИН (права доступа) ---------------------------------------------------

def escape_markdown(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def format_permissions(permissions):
    formatted_permissions = []
    counter = 1

    for perm in permissions:
        formatted_permissions.append(f"⚙️ №{counter}. {perm}")
        counter += 1

    return "\n".join(formatted_permissions)

@bot.message_handler(func=lambda message: message.text == 'Права доступа' and str(message.chat.id) in admin_sessions)
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_permissions(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Права доступа'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    list_admins(message)

def list_admins(message):
    admin_list = []
    for admin_id, data in admins_data.items():
        username = data['username']
        escaped_username = escape_markdown(username)
        admin_list.append(f"№{len(admin_list) + 1}. {escaped_username} - `{admin_id}`")

    if admin_list:
        response_message = "📋 Список администраторов:\n\n" + "\n\n".join(admin_list)
        try:
            bot.send_message(message.chat.id, response_message, parse_mode="Markdown")
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                pass
                if message.chat.id not in blocked_users:
                    blocked_users.append(message.chat.id)
                    save_blocked_users(blocked_users)
            else:
                raise e

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('Вернуться в админ')
    markup.add('В меню админ-панели')
    try:
        bot.send_message(message.chat.id, "Введите *номер*, *id* или *username* администратора для просмотра его прав:", reply_markup=markup, parse_mode="Markdown")
    except ApiTelegramException as e:
        if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
            pass
            if message.chat.id not in blocked_users:
                blocked_users.append(message.chat.id)
                save_blocked_users(blocked_users)
        else:
            raise e
    bot.register_next_step_handler(message, process_admin_selection)

@text_only_handler
def process_admin_selection(message):
    if message.chat.id in blocked_users:
        return

    if message.text == "Вернуться в админ":
        show_settings_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    input_data = message.text.strip()

    try:
        if input_data.isdigit() and len(input_data) < 5:
            admin_number = int(input_data)
            if admin_number < 1 or admin_number > len(admins_data):
                raise ValueError
            admin_id = list(admins_data.keys())[admin_number - 1]
        elif input_data.isdigit():
            admin_id = input_data
            if admin_id not in admins_data:
                bot.send_message(message.chat.id, f"❌ Такого администратора с ID `{admin_id}` не существует! Попробуйте снова", parse_mode="Markdown")
                bot.register_next_step_handler(message, process_admin_selection)
                return
        else:
            admin_id = next((key for key, data in admins_data.items() if data.get('username') == input_data), None)
            if not admin_id:
                bot.send_message(message.chat.id, f"❌ Такого администратора с именем пользователя `{input_data}` не существует! Попробуйте снова", parse_mode="Markdown")
                bot.register_next_step_handler(message, process_admin_selection)
                return

        admin_data = admins_data[admin_id]
        permissions = admin_data.get("permissions", [])

        if is_root_admin(admin_id):
            bot.send_message(message.chat.id, "⚠️ *Корневой администратор обладает всеми правами!*", parse_mode="Markdown")
            show_settings_menu(message)
            return

        escaped_username = escape_markdown(admin_data['username'])
        permissions_list = format_permissions_with_headers(permissions)
        bot.send_message(message.chat.id, f"Текущие права администратора {escaped_username} - `{admin_id}`:\n\n{permissions_list}", parse_mode="Markdown")

        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add('Добавить права', 'Удалить права')
        markup.add('Вернуться в админ')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Выберите действие для прав:", reply_markup=markup)
        bot.register_next_step_handler(message, process_permission_action, admin_id)

    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Пожалуйста, введите *номер*, *id* или *username* администратора!", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_admin_selection)

def get_available_permissions(admin_id):
    current_permissions = admins_data.get(admin_id, {}).get("permissions", [])
    unique_permissions = set(perm.split(':')[-1].strip() for perm in current_permissions)
    available_permissions = [perm for perm in _all_permissions() if perm.split(':')[-1].strip() not in unique_permissions]
    return available_permissions

def format_permissions_with_headers(permissions):
    formatted_permissions = []
    counter = 1

    formatted_permissions.append("*Основные права:*")
    for main_func in _main_functions():
        if any(perm.split(':')[-1].strip() == main_func for perm in permissions):
            formatted_permissions.append(f"⚙️ №{counter}. {main_func}")
            counter += 1
    formatted_permissions.append("")

    for main_func in _main_functions():
        sub_permissions = [perm.split(':')[-1].strip() for perm in permissions if perm.startswith(main_func) and perm.split(':')[-1].strip() != main_func]
        if sub_permissions:
            formatted_permissions.append(f"*Права в \"{main_func}\":*")
            for perm in sub_permissions:
                formatted_permissions.append(f"⚙️ №{counter}. {perm}")
                counter += 1
            formatted_permissions.append("")

    other_permissions = [perm.split(':')[-1].strip() for perm in permissions if not any(perm.startswith(main_func) for main_func in _main_functions())]
    if other_permissions:
        formatted_permissions.append("*Другие права:*")
        for perm in other_permissions:
            formatted_permissions.append(f"⚙️ №{counter}. {perm}")
            counter += 1

    return "\n".join(formatted_permissions)

def format_permissions_as_list(permissions):
    formatted_permissions = []
    counter = 1

    for perm in permissions:
        formatted_permissions.append(f"⚙️ №{counter}. {perm}")
        counter += 1

    return "\n".join(formatted_permissions)

def process_permission_action(message, admin_id):
    if message.text == "Вернуться в админ":
        show_settings_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    if message.text == 'Добавить права':
        if not check_permission(str(message.chat.id), 'Добавить права'):
            bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
            return

        available_permissions = get_available_permissions(admin_id)
        permissions_list = format_permissions_with_headers(available_permissions)
        bot.send_message(message.chat.id, f"*Доступные права для добавления*:\n\n{permissions_list}", parse_mode="Markdown")

        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add('Вернуться в админ')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Введите номера прав через запятую для *добавления*:", parse_mode="Markdown", reply_markup=markup)
        bot.register_next_step_handler(message, process_add_permissions, admin_id, available_permissions)

    elif message.text == 'Удалить права':
        if not check_permission(str(message.chat.id), 'Удалить права'):
            bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
            return

        current_permissions = admins_data[admin_id].get("permissions", [])
        permissions_list = format_permissions_as_list(current_permissions)
        bot.send_message(message.chat.id, f"*Текущие права администратора:*\n\n{permissions_list}", parse_mode="Markdown")

        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add('Вернуться в админ')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Введите номера прав через запятую для *удаления*:", parse_mode="Markdown", reply_markup=markup)
        bot.register_next_step_handler(message, process_remove_permissions, admin_id, current_permissions)

def format_permissions_with_main_functions(permissions):
    formatted_permissions = []
    counter = 1

    formatted_permissions.append("*Основные функции:*")
    for main_func in _main_functions():
        formatted_permissions.append(f"⚙️ №{counter}. {main_func}")
        counter += 1
    formatted_permissions.append("")

    for main_func in _main_functions():
        sub_permissions = [perm for perm in permissions if perm.startswith(main_func) and perm != main_func]
        if sub_permissions:
            formatted_permissions.append(f"*{main_func}:*")
            for perm in sub_permissions:
                formatted_permissions.append(f"⚙️ №{counter}. {perm.split(': ')[1]}")
                counter += 1
            formatted_permissions.append("")

    return "\n".join(formatted_permissions)

@text_only_handler
def process_add_permissions(message, admin_id, available_permissions):
    if message.chat.id in blocked_users:
        return

    if message.text == "Вернуться в админ":
        show_settings_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        permission_numbers = [int(num.strip()) - 1 for num in message.text.split(',')]
        permissions_to_add = []
        invalid_permissions = []

        for num in permission_numbers:
            if 0 <= num < len(available_permissions):
                permission = available_permissions[num].split(':')[-1].strip()
                if permission in admins_data[admin_id].get("permissions", []):
                    bot.send_message(message.chat.id, f"❌ Право *{escape_markdown(permission)}* уже добавлено! Попробуйте снова", parse_mode="Markdown")
                    bot.register_next_step_handler(message, process_add_permissions, admin_id, available_permissions)
                    return
                permissions_to_add.append(permission)
            else:
                invalid_permissions.append(str(num + 1))

        if invalid_permissions:
            bot.send_message(message.chat.id, f"❌ Неверный номер права: *{', '.join(invalid_permissions)}*! Эти права были пропущены...", parse_mode="Markdown")

        if permissions_to_add:
            admins_data[admin_id].setdefault("permissions", []).extend(permissions_to_add)
            save_admin_data(admin_sessions, admins_data, login_password_hash, removed_admins)

            admin_data = admins_data[admin_id]
            escaped_username = escape_markdown(admin_data['username'])
            escaped_permissions_to_add = [escape_markdown(permission.lower()) for permission in permissions_to_add]

            bot.send_message(message.chat.id, f"✅ Права для админа {escaped_username} - `{admin_id}` обновлены!", parse_mode="Markdown")
            try:
                bot.send_message(admin_id, f"⚠️ Ваши права были *изменены*!\n\n✅ *Добавлены* новые права: _{', '.join(escaped_permissions_to_add)}_", parse_mode="Markdown")
            except ApiTelegramException as e:
                if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                    pass
                    if admin_id not in blocked_users:
                        blocked_users.append(admin_id)
                        save_blocked_users(blocked_users)
                else:
                    raise e
            show_settings_menu(message)
        else:
            bot.send_message(message.chat.id, "Неверные номера прав! Попробуйте снова")
            bot.register_next_step_handler(message, process_add_permissions, admin_id, available_permissions)

    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Неверные номера прав! Попробуйте снова")
        bot.register_next_step_handler(message, process_add_permissions, admin_id, available_permissions)

@text_only_handler
def process_remove_permissions(message, admin_id, current_permissions):
    if message.chat.id in blocked_users:
        return

    if message.text == "Вернуться в админ":
        show_settings_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        permission_numbers = [int(num.strip()) - 1 for num in message.text.split(',')]
        permissions_to_remove = []
        invalid_permissions = []

        for num in permission_numbers:
            if 0 <= num < len(current_permissions):
                permissions_to_remove.append(current_permissions[num])
            else:
                invalid_permissions.append(str(num + 1))

        if invalid_permissions:
            bot.send_message(message.chat.id, f"❌ Неверный номер права: *{', '.join(invalid_permissions)}*! Эти права были пропущены...", parse_mode="Markdown")

        if permissions_to_remove:
            updated_permissions = [perm for perm in current_permissions if perm not in permissions_to_remove]
            admins_data[admin_id]["permissions"] = updated_permissions
            save_admin_data(admin_sessions, admins_data, login_password_hash, removed_admins)

            escaped_username = escape_markdown(admins_data[admin_id]['username'])
            escaped_removed = ', '.join(escape_markdown(perm.lower()) for perm in permissions_to_remove)

            bot.send_message(message.chat.id, f"✅ Права для администратора {escaped_username} - `{admin_id}` обновлены!", parse_mode="Markdown")
            try:
                bot.send_message(admin_id, f"⚠️ Ваши права были *изменены*!\n\n❌ *Удалены* права: _{escaped_removed}_", parse_mode="Markdown")
            except ApiTelegramException as e:
                if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                    pass
                    if admin_id not in blocked_users:
                        blocked_users.append(admin_id)
                        save_blocked_users(blocked_users)
                else:
                    raise e

            show_settings_menu(message)
        else:
            bot.send_message(message.chat.id, "Введите номера прав через запятую!", parse_mode="Markdown")
            bot.register_next_step_handler(message, process_remove_permissions, admin_id, current_permissions)

    except ValueError:
        bot.send_message(message.chat.id, "Введите номера прав через запятую!", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_remove_permissions, admin_id, current_permissions)
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")