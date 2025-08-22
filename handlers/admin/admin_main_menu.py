from core.imports import wraps, telebot, types, os, json, re, hashlib, time
from core.bot_instance import bot, BASE_DIR
from core.config import ADMIN_USERNAME, ADMIN_PASSWORD
from decorators.blocked_user import load_blocked_users, save_blocked_users
from .utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

def return_to_menu(message):
    from handlers.user.user_main_menu import return_to_menu as _f
    return _f(message)

def handle_change_credentials(message):
    from handlers.admin.admin.admin import handle_change_credentials as _f
    return _f(message)

def is_valid_username(username):
    from handlers.admin.admin.admin import is_valid_username as _f
    return _f(username)

def generate_login_password_hash(username, password):
    from handlers.admin.admin.admin import generate_login_password_hash as _f
    return _f(username, password)

# ------------------------------------------------------ ВХОД В АДМИНКУ ------------------------------------------------------

ADMIN_SESSIONS_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')
credentials_changed = False
admin_sessions = []
admin_logout_times = {}
blocked_users = load_blocked_users()

def load_admin_data():
    if os.path.exists(ADMIN_SESSIONS_PATH):
        with open(ADMIN_SESSIONS_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return {
        "admin_sessions": data.get("admin_sessions", []),
                "admins_data": data.get("admins_data", {}),
        "removed_admins": {k: v for k, v in data.get("removed_admins", {}).items()},
                "login_password_hash": data.get("login_password_hash", "")
            }
    return {
    "admin_sessions": [],
        "admins_data": {},
        "removed_admins": {},
        "login_password_hash": ""
    }

def save_admin_data(admin_sessions, admins_data, login_password_hash, removed_admins=None):
    with open(ADMIN_SESSIONS_PATH, 'w', encoding='utf-8') as file:
        json.dump({
            "admin_sessions": list(admin_sessions),
            "admins_data": admins_data,
            "removed_admins": removed_admins or {},
            "login_password_hash": login_password_hash
        }, file, ensure_ascii=False, indent=4)

admin_sessions = []

data = load_admin_data()
admin_sessions = data["admin_sessions"]
admins_data = data["admins_data"]
removed_admins = data["removed_admins"]

login_password_hash = data["login_password_hash"]
login_password_hash = hashlib.sha256(f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}".encode()).hexdigest()

# -------------------------------------------------- ВХОД В АДМИНКУ (функции) ---------------------------------------------------

def get_login_password_hash():
    return hashlib.sha256(f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}".encode()).hexdigest()

def _normalize(text: str) -> str:
    return str(text or '').strip()

def get_root_admin_id():
    return next(iter(admins_data)) if admins_data else None

def is_root_admin(admin_id) -> bool:
    return str(admin_id) == str(get_root_admin_id())

def check_permission(admin_id, permission):

    if is_root_admin(admin_id):
        return True

    requested = _normalize(permission)
    current_permissions = admins_data.get(str(admin_id), {}).get("permissions", []) or []

    if requested in current_permissions:
        return True

    req_suffix = requested.split(':')[-1].strip()
    for perm in current_permissions:
        perm_norm = _normalize(perm)
        if perm_norm.split(':')[-1].strip() == req_suffix:
            return True

    for perm in current_permissions:
        if perm.startswith(f"{requested}:"):
            return True

    return False  

def get_user_data(message):
    user = message.from_user
    return {
        "user_id": user.id,
        "first_name": user.first_name if user.first_name else " ",
        "last_name": user.last_name if user.last_name else " ",
        "username": f"@{user.username}" if user.username else " ",
        "phone": user.phone_number if hasattr(user, 'phone_number') else " "
    }

def is_new_admin(admin_id):
    return admins_data.get(admin_id, {}).get("is_new", False)

def process_login_choice(message):
    global credentials_changed
    user_id = str(message.chat.id)

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text == "Быстрый вход":
        if user_id in admin_sessions and not credentials_changed:
            if is_new_admin(user_id):
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add('Смена данных входа')
                bot.send_message(message.chat.id, "⚠️ Вы новый администратор!\nПожалуйста, смените данные входа:", reply_markup=markup)
                bot.register_next_step_handler(message, handle_change_credentials)
            else:
                session_data = admins_data.get(user_id, {})
                bot.send_message(message.chat.id, f"Добро пожаловать в админ-панель, {session_data.get('username', 'админ')}!")
                show_admin_panel(message)
        else:
            bot.send_message(message.chat.id, "⚠️ Сессия недействительна!\nПожалуйста, авторизуйтесь заново...")
            handle_admin_login(message)
    elif message.text == "Ввести логин и пароль заново":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_main = types.KeyboardButton("В главное меню")
        markup.add(item_main)
        msg = bot.send_message(message.chat.id, "👤 Введите логин:", reply_markup=markup)
        bot.register_next_step_handler(msg, verify_username)
    else:
        bot.send_message(message.chat.id, "Неверный выбор! Попробуйте снова")
        handle_admin_login(message)

def verify_username(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    username = message.text
    is_valid, error_message = is_valid_username(username)
    if not is_valid:
        bot.send_message(message.chat.id, f"Ошибка: {error_message}! Попробуйте снова")
        bot.register_next_step_handler(message, verify_username)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_main)
    msg = bot.send_message(message.chat.id, "🔑 Введите пароль:", reply_markup=markup)
    bot.register_next_step_handler(msg, verify_password, username)
    bot.delete_message(message.chat.id, message.message_id)  

def verify_password(message, username):
    global credentials_changed

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    password = message.text
    admin_id = str(message.chat.id)

    if admin_id in removed_admins:
        bot.send_message(message.chat.id, "🚫 Ваш доступ был отключён! Обратитесь к корневому администратору!")
        return

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        if admin_id not in admin_sessions:
            admin_sessions.append(admin_id)
        save_admin_data(admin_sessions, admins_data, login_password_hash, removed_admins)

        user_data = get_user_data(message)
        update_admin_data(user_data)

        session_data = admins_data.get(admin_id, {})
        bot.send_message(message.chat.id, f"Добро пожаловать в админ-панель, {session_data.get('username', 'админ')}!")
        show_admin_panel(message)

        credentials_changed = False
        bot.delete_message(message.chat.id, message.message_id)   
        return

    admin_hash = admins_data.get(admin_id, {}).get("login_password_hash_for_user_id", "")
    if generate_login_password_hash(username, password) == admin_hash:
        if admin_id not in admin_sessions:
            admin_sessions.append(admin_id)
        save_admin_data(admin_sessions, admins_data, login_password_hash, removed_admins)

        user_data = get_user_data(message)
        update_admin_data(user_data)

        session_data = admins_data.get(admin_id, {})
        bot.send_message(message.chat.id, f"Добро пожаловать в админ-панель, {session_data.get('username', 'админ')}!")
        show_admin_panel(message)

        credentials_changed = False
    else:
        bot.send_message(message.chat.id, "❌ Неверные логин или пароль! Попробуйте снова...")
        handle_admin_login(message)

    bot.delete_message(message.chat.id, message.message_id) 

def update_admin_data(user_data):
    admin_id = str(user_data["user_id"])

    if admin_id in removed_admins:
        return

    if admin_id in admins_data:
        existing_data = admins_data[admin_id]
        if (existing_data.get("first_name") != user_data["first_name"] or
            existing_data.get("last_name") != user_data["last_name"] or
            existing_data.get("username") != user_data["username"] or
            existing_data.get("phone") != user_data["phone"]):
            admins_data[admin_id].update(user_data)
            save_admin_data(admin_sessions, admins_data, login_password_hash)
    else:
        admins_data[admin_id] = user_data
        save_admin_data(admin_sessions, admins_data, login_password_hash)

def update_login_password(chat_id, new_username=None, new_password=None):
    global admins_data, login_password_hash

    admin_id = str(chat_id)

    if admin_id not in admins_data:
        return f"Администратор с id {admin_id} не найден!"

    admin_data = admins_data[admin_id]
    current_username = admin_data["admins_username"]
    current_password_hash = admin_data["login_password_hash_for_user_id"]

    if new_username:
        old_username = current_username
        admin_data["admins_username"] = new_username
        if old_username != new_username:
            admin_data["login_password_hash_for_user_id"] = hashlib.sha256(f"{new_username}:{new_password or current_password_hash}".encode()).hexdigest()

    if new_password:
        new_hash = hashlib.sha256(f"{new_username or current_username}:{new_password}".encode()).hexdigest()
        admin_data["login_password_hash_for_user_id"] = new_hash
    else:
        admin_data["login_password_hash_for_user_id"] = current_password_hash

    login_password_hash = hashlib.sha256(f"{new_username or current_username}:{new_password or current_password_hash}".encode()).hexdigest()

    admins_data[admin_id] = admin_data

    save_admin_data(admin_sessions, admins_data, login_password_hash)

    if new_username and new_password:
        return f"Логин обновлён на {new_username}, пароль обновлён!"
    elif new_username:
        return f"Логин обновлён на {new_username}. Пароль остался прежним!"
    elif new_password:
        return "Пароль обновлён!"
    else:
        return "Изменений не было..."

def verify_login_password_hash():
    global login_password_hash
    current_hash = hashlib.sha256(f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}".encode()).hexdigest()

    if current_hash != login_password_hash:
        login_password_hash = current_hash
        save_admin_data(admin_sessions, admins_data, login_password_hash)

verify_login_password_hash()

def change_admin_credentials(new_username=None, new_password=None):
    global ADMIN_USERNAME, ADMIN_PASSWORD, login_password_hash

    current_username = ADMIN_USERNAME
    current_password = ADMIN_PASSWORD

    if new_username:
        ADMIN_USERNAME = new_username
        current_username = new_username
    if new_password:
        ADMIN_PASSWORD = new_password
        current_password = new_password

    login_password_hash = hashlib.sha256(f"{current_username}:{current_password}".encode()).hexdigest()

    save_admin_data(admin_sessions, admins_data, login_password_hash)

# -------------------------------------------------- ВХОД В АДМИНКУ (основная команда /admin) ------------------------------------------------

@bot.message_handler(commands=['admin'])
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_admin_login(message):
    global credentials_changed
    user_data = get_user_data(message)
    admin_id = str(user_data["user_id"])

    if admin_id in blocked_users:
        bot.send_message(admin_id, "⛔ Вы заблокировали бота! Пожалуйста, разблокируйте бота и попробуйте снова")
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    current_time = time.time()
    last_logout_time = admin_logout_times.get(admin_id)

    admin_sessions[:] = [
        session_id for session_id in admin_sessions
        if (current_time - admin_logout_times.get(session_id, 0)) <= 300
    ]

    if last_logout_time and (current_time - last_logout_time) <= 300:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        if not credentials_changed:
            markup.add('Быстрый вход')
        if credentials_changed:
            markup.add('Ввести логин и пароль заново')
        markup.add('В главное меню')
        bot.send_message(
            user_data["user_id"],
            "🛠️ Выберите способ входа:",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, process_login_choice)
    else:
        if admin_id not in admin_sessions:
            if is_new_admin(admin_id):
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add('Смена данных входа')
                bot.send_message(message.chat.id, "⚠️ Вы новый администратор!\nПожалуйста, смените данные входа:", reply_markup=markup)
                bot.register_next_step_handler(message, handle_change_credentials)
            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item_main = types.KeyboardButton("В главное меню")
                markup.add(item_main)
                msg = bot.send_message(message.chat.id, "👤 Введите логин:", reply_markup=markup)
                bot.register_next_step_handler(msg, verify_username)
        else:
            admin_logout_times[admin_id] = time.time()
            bot.send_message(message.chat.id, "✅ Вы уже вошли в систему... Добро пожаловать обратно!")
            show_admin_panel(message)

def show_admin_panel(message):
    admin_id = str(message.chat.id)
    if is_new_admin(admin_id):
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add('Смена данных входа')
        bot.send_message(message.chat.id, "⚠️ Вы новый администратор!\nПожалуйста, смените данные входа:", reply_markup=markup)
        bot.register_next_step_handler(message, handle_change_credentials)
    else:
        markup = types.ReplyKeyboardMarkup(row_width=3)
        markup.add('Управление системой')
        markup.add('Админ', 'Бан', 'Функции')
        markup.add('Статистика', 'Файлы', 'Резервная копия')
        markup.add('Общение', 'Реклама', 'Редакция')
        markup.add('Экстренная остановка')
        markup.add('Выход')
        bot.send_message(message.chat.id, "Выберите действие из админ-панели:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'В меню админ-панели')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_return_to_admin_panel(message):
    show_admin_panel(message)

# -------------------------------------------------- ВХОД В АДМИНКУ (выход) ------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Выход' and str(message.chat.id) in admin_sessions)
@restricted
@track_user_activity
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def admin_logout(message):
    admin_id = str(message.chat.id)

    if admin_id in blocked_users:
        bot.send_message(admin_id, "⛔ Вы заблокировали бота! Пожалуйста, разблокируйте бота и попробуйте снова")
        return

    admin_logout_times[admin_id] = time.time()
    bot.send_message(message.chat.id, "✅ Вы вышли из админ-панели!\n🔐 Быстрый вход доступен в течении 5 минут...")
    return_to_menu(message)