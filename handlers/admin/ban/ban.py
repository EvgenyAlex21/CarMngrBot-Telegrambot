from core.imports import wraps, telebot, types, os, json, re
from core.bot_instance import bot, BASE_DIR
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from decorators.blocked_user import load_blocked_users
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

# -------------------------------------------------- БАН ---------------------------------------------------

TELEGRAM_MESSAGE_LIMIT = 4096
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
FILES_PATH = os.path.join(BASE_DIR, 'data')
ADDITIONAL_FILES_PATH = os.path.join(BASE_DIR, 'files')
ADMIN_SESSIONS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')
USER_DATA_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'users.json')

def load_admin_sessions():
    with open(ADMIN_SESSIONS_FILE, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data['admin_sessions']

def check_admin_access(message):
    admin_sessions = load_admin_sessions()
    if str(message.chat.id) in admin_sessions:
        return True
    else:
        bot.send_message(message.chat.id, "⚠️ У вас нет *прав доступа* для выполнения этой операции!", parse_mode="Markdown")
        return False

def save_user_data(user_data):
    with open(USER_DATA_PATH, 'w', encoding='utf-8') as file:
        json.dump(user_data, file, ensure_ascii=False, indent=4)

def load_user_data():
    if os.path.exists(USER_DATA_PATH):
        with open(USER_DATA_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

def is_user_blocked(user_id):
    users_data = load_user_data()
    return users_data.get(str(user_id), {}).get('blocked', False)

def block_user(user_id):
    users_data = load_user_data()
    root_admin_id = get_root_admin()
    if str(user_id) == root_admin_id:
        return None, None, False  
    if str(user_id) in users_data:
        if users_data[str(user_id)].get('blocked'):
            return None, None, True  
        users_data[str(user_id)]['blocked'] = True
        save_user_data(users_data)
        return users_data[str(user_id)]['username'], user_id, False
    return None, None, False

def unblock_user(user_id):
    users_data = load_user_data()
    root_admin_id = get_root_admin()
    if str(user_id) == root_admin_id:
        return None, None, False  
    if str(user_id) in users_data:
        if not users_data[str(user_id)].get('blocked'):
            return None, None, True  
        users_data[str(user_id)]['blocked'] = False
        save_user_data(users_data)
        return users_data[str(user_id)]['username'], user_id, False
    return None, None, False

def get_user_id_by_username(username):
    users_data = load_user_data()
    username_to_check = username.lstrip('@')
    for user_id, data in users_data.items():
        if 'username' in data and data['username'].lstrip('@') == username_to_check:
            return int(user_id)
    return None

def escape_markdown(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def get_root_admin():
    with open(ADMIN_SESSIONS_FILE, 'r', encoding='utf-8') as file:
        data = json.load(file)
    root_admin_id = data['admin_sessions'][0]
    return root_admin_id

@bot.message_handler(func=lambda message: message.text == 'Бан' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def ban_user_prompt(message):
    blocked_users = load_blocked_users()
    if message.chat.id in blocked_users:
        return

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Бан'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    list_users_for_ban(message)

def list_users_for_ban(message):
    users_data = load_user_data()
    user_list = []
    for user_id, data in users_data.items():
        username = escape_markdown(data['username'])
        status = " - *заблокирован* 🚫" if data.get('blocked', False) else " - *разблокирован* ✅"
        user_list.append(f"№{len(user_list) + 1}. {username} - `{user_id}`{status}")

    response_message = "📋 Список *всех* пользователей:\n\n" + "\n\n".join(user_list)
    if len(response_message) > 4096:
        bot.send_message(message.chat.id, "📜 Список пользователей слишком большой для отправки в одном сообщении!")
    else:
        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Заблокировать", "Разблокировать")
    markup.add("Удалить данные")
    markup.add("В меню админ-панели")
    bot.send_message(message.chat.id, "Выберите действие для пользователя:", reply_markup=markup)
    bot.register_next_step_handler(message, choose_ban_action)

@check_user_blocked
@log_user_actions
def choose_ban_action(message):
    if message.text and message.text.strip() not in ["Заблокировать", "Разблокировать", "Удалить данные", "В меню админ-панели"]:
        pending_input = message.text.strip()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Заблокировать", "Разблокировать")
        markup.add("Удалить данные")
        markup.add("В меню админ-панели")
        bot.send_message(message.chat.id, "Сначала выберите действие: что сделать с указанными пользователями?", reply_markup=markup)
        def _dispatch_after_choice(msg):
            msg.text = msg.text  
            if msg.text == "Заблокировать":
                msg.text = pending_input
                process_block_user(msg)
            elif msg.text == "Разблокировать":
                msg.text = pending_input
                process_unblock_user(msg)
            elif msg.text == "Удалить данные":
                msg.text = pending_input
                process_delete_user_data(msg)
            elif msg.text == "В меню админ-панели":
                show_admin_panel(msg)
            else:
                bot.send_message(msg.chat.id, "Неверное действие! Пожалуйста, выберите действие и повторите ввод")
                bot.register_next_step_handler(msg, choose_ban_action)
        bot.register_next_step_handler(message, _dispatch_after_choice)
        return

    if message.text == "Заблокировать":
        admin_id = str(message.chat.id)
        if not check_permission(admin_id, 'Заблокировать'):
            bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
            return

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в бан")
        markup.add("В меню админ-панели")
        bot.send_message(message.chat.id, "Введите *номер*, *id* или *username* пользователей для *блокировки* через запятую:", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_block_user)

    elif message.text == "Разблокировать":
        admin_id = str(message.chat.id)
        if not check_permission(admin_id, 'Разблокировать'):
            bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
            return

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в бан")
        markup.add("В меню админ-панели")
        bot.send_message(message.chat.id, "Введите *номер*, *id* или *username* пользователей для *разблокировки* через запятую:", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_unblock_user)

    elif message.text == "Удалить данные":
        admin_id = str(message.chat.id)
        if not check_permission(admin_id, 'Удалить данные'):
            bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
            return
        delete_user_data(message)

    elif message.text == "В меню админ-панели":
        show_admin_panel(message)

# -------------------------------------------------- БАН (заблокировать) ---------------------------------------------------

def process_block_user(message):
    if message.text == "Вернуться в бан":
        ban_user_prompt(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    user_inputs = message.text.strip().split(',')
    users_data = load_user_data()
    admin_id = str(message.chat.id)
    root_admin_id = get_root_admin()

    for user_input in user_inputs:
        user_input = user_input.strip()
        user_id = None

        if user_input.isdigit():
            if int(user_input) <= len(users_data):
                user_id = list(users_data.keys())[int(user_input) - 1]
            else:
                user_id = int(user_input)
        elif user_input.startswith('@'):
            user_id = get_user_id_by_username(user_input[1:])
        else:
            for uid, data in users_data.items():
                if data['username'] == f"@{user_input}":
                    user_id = uid
                    break

        if user_id and str(user_id) in users_data:
            if str(user_id) == root_admin_id:
                bot.send_message(message.chat.id, "⚠️ Нельзя *заблокировать* корневого администратора!", parse_mode="Markdown")
                continue
            if str(user_id) == admin_id:
                bot.send_message(message.chat.id, "⚠️ Нельзя *заблокировать* самого себя!", parse_mode="Markdown")
                continue

            username = users_data[str(user_id)]['username']
            _, _, already_blocked = block_user(user_id)
            if already_blocked:
                bot.send_message(message.chat.id, f"🚫 Пользователь {escape_markdown(username)} - `{user_id}` уже заблокирован!", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, f"🚫 Пользователь {escape_markdown(username)} - `{user_id}` заблокирован!", parse_mode="Markdown")
                bot.send_message(user_id, "🚫 Ваш аккаунт был заблокирован администратором!", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"⚠️ Пользователь *{escape_markdown(user_input)}* не найден!", parse_mode="Markdown")

    ban_user_prompt(message)

# -------------------------------------------------- БАН (разблокировать) ---------------------------------------------------

def process_unblock_user(message):
    if message.text == "Вернуться в бан":
        ban_user_prompt(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    user_inputs = message.text.strip().split(',')
    users_data = load_user_data()
    admin_id = str(message.chat.id)
    root_admin_id = get_root_admin()

    for user_input in user_inputs:
        user_input = user_input.strip()
        user_id = None

        if user_input.isdigit():
            if int(user_input) <= len(users_data):
                user_id = list(users_data.keys())[int(user_input) - 1]
            else:
                user_id = int(user_input)
        elif user_input.startswith('@'):
            user_id = get_user_id_by_username(user_input[1:])
        else:
            for uid, data in users_data.items():
                if data['username'] == f"@{user_input}":
                    user_id = uid
                    break

        if user_id and str(user_id) in users_data:
            if str(user_id) == root_admin_id:
                bot.send_message(message.chat.id, "⚠️ Нельзя *разблокировать* корневого администратора!", parse_mode="Markdown")
                continue
            if str(user_id) == admin_id:
                bot.send_message(message.chat.id, "⚠️ Нельзя *разблокировать* самого себя!", parse_mode="Markdown")
                continue

            username = users_data[str(user_id)]['username']
            _, _, already_unblocked = unblock_user(user_id)
            if already_unblocked:
                bot.send_message(message.chat.id, f"✅ Пользователь {escape_markdown(username)} - `{user_id}` уже разблокирован!", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, f"✅ Пользователь {escape_markdown(username)} - `{user_id}` разблокирован!", parse_mode="Markdown")
                bot.send_message(user_id, "✅ Ваш аккаунт был разблокирован администратором!", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"⚠️ Пользователь *{escape_markdown(user_input)}* не найден!", parse_mode="Markdown")

    ban_user_prompt(message)

# -------------------------------------------------- БАН (удалить данные) ---------------------------------------------------

def delete_user_data(message):
    blocked_users = load_blocked_users()
    if message.chat.id in blocked_users:
        return
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add("Вернуться в бан")
    markup.add("В меню админ-панели")
    bot.send_message(message.chat.id, "Введите *номер*, *username* или *id* пользователя для удаления данных:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_delete_user_data)

def process_delete_user_data(message):

    if message.text == "Вернуться в бан":
        ban_user_prompt(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    user_inputs = message.text.strip().split(',')
    users_data = load_user_data()
    admin_id = str(message.chat.id)
    root_admin_id = get_root_admin()

    for user_input in user_inputs:
        user_input = user_input.strip()
        user_id = None

        if user_input.isdigit():
            if int(user_input) <= len(users_data):
                user_id = list(users_data.keys())[int(user_input) - 1]
            else:
                user_id = int(user_input)
        elif user_input.startswith('@'):
            user_id = get_user_id_by_username(user_input[1:])
        else:
            for uid, data in users_data.items():
                if data['username'] == f"@{user_input}":
                    user_id = uid
                    break

        if user_id is None:
            bot.send_message(message.chat.id, f"❌ Пользователь с таким *username* или *id* не найден: {user_input}!", parse_mode="Markdown")
            continue

        if str(user_id) == root_admin_id:
            bot.send_message(message.chat.id, f"⚠️ Нельзя удалить данные корневого администратора {escape_markdown(user_input)} - `{user_id}`!", parse_mode="Markdown")
            continue

        if str(user_id) == admin_id:
            bot.send_message(message.chat.id, f"⚠️ Нельзя удалить данные самого себя {escape_markdown(user_input)} - `{user_id}`!", parse_mode="Markdown")
            continue

        delete_user_data_recursively(user_id, BASE_DIR)
        username = users_data[str(user_id)]['username']
        users_data.pop(str(user_id), None)
        save_user_data(users_data)

        bot.send_message(message.chat.id, f"✅ Данные пользователя {escape_markdown(username)} - `{user_id}` успешно удалены!", parse_mode="Markdown")

    ban_user_prompt(message)

def delete_user_data_recursively(user_id, current_dir):
    for root, dirs, files in os.walk(current_dir):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    try:
                        with open(file_path, 'r', encoding='windows-1251') as f:
                            data = json.load(f)
                    except Exception:
                        continue

                def remove_user_data(obj):
                    if isinstance(obj, dict):
                        keys_to_delete = [key for key in obj if key == str(user_id)]
                        for key in keys_to_delete:
                            del obj[key]
                        for value in obj.values():
                            remove_user_data(value)
                    elif isinstance(obj, list):
                        obj[:] = [item for item in obj if item != str(user_id)]
                        for item in obj:
                            remove_user_data(item)

                remove_user_data(data)

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)

def delete_user_from_users_db(message, user_id=None, username=None):
    if not os.path.exists(USER_DATA_PATH):
        bot.send_message(message.chat.id, "⚠️ База данных пользователей не существует!")
        return

    try:
        with open(USER_DATA_PATH, 'r', encoding='utf-8') as file:
            users_data = json.load(file)
    except json.JSONDecodeError:
        bot.send_message(message.chat.id, f"Файл {USER_DATA_PATH} содержит некорректные данные!")
        return
    except UnicodeDecodeError:
        try:
            with open(USER_DATA_PATH, 'r', encoding='windows-1251') as file:
                users_data = json.load(file)
        except json.JSONDecodeError:
            bot.send_message(message.chat.id, f"Файл {USER_DATA_PATH} содержит некорректные данные!")
            return
        except UnicodeDecodeError:
            bot.send_message(message.chat.id, f"Файл {USER_DATA_PATH} содержит некорректную кодировку!")
            return

    if user_id:
        if str(user_id) not in users_data:
            bot.send_message(message.chat.id, f"❌ Пользователь с *id* `{user_id}` не найден!", parse_mode="Markdown")
            return
        users_data.pop(str(user_id), None)
    elif username:
        username = username.lstrip('@')
        found = False
        for user_id, data in users_data.items():
            if data.get('username') == f"@{username}":
                users_data.pop(user_id, None)
                found = True
                break
        if not found:
            bot.send_message(message.chat.id, f"❌ Пользователь с *username* @{username} не найден!", parse_mode="Markdown")
            return

    with open(USER_DATA_PATH, 'w', encoding='utf-8') as file:
        json.dump(users_data, file, ensure_ascii=False, indent=4)

def delete_user_data_by_id(message, user_id):
    if not os.path.exists(USER_DATA_PATH):
        bot.send_message(message.chat.id, "⚠️ База данных пользователей не существует!")
        return

    users_data = load_user_data()
    if str(user_id) not in users_data:
        bot.send_message(message.chat.id, f"Пользователь с *id* `{user_id}` не найден!", parse_mode="Markdown")
        return

    root_admin_id = get_root_admin()
    admin_id = str(message.chat.id)

    if str(user_id) == root_admin_id:
        bot.send_message(message.chat.id, f"⚠️ Ошибка при удалении данных пользователя с *id* `{user_id}` - нельзя удалить данные корневого администратора!", parse_mode="Markdown")
        return

    if str(user_id) == admin_id:
        bot.send_message(message.chat.id, f"⚠️ Ошибка при удалении данных пользователя с *id* `{user_id}` - нельзя удалить данные самого себя!", parse_mode="Markdown")
        return

    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)

                if str(user_id) in file:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    except json.JSONDecodeError:
                        continue
                    except UnicodeDecodeError:
                        try:
                            with open(file_path, 'r', encoding='windows-1251') as f:
                                data = json.load(f)
                        except json.JSONDecodeError:
                            continue
                        except UnicodeDecodeError:
                            continue

                    if isinstance(data, list):
                        updated_data = [item for item in data if item != str(user_id)]
                        if len(updated_data) < len(data):
                            data = updated_data
                    elif isinstance(data, dict):
                        if 'admin_sessions' in data and str(user_id) in data['admin_sessions']:
                            data['admin_sessions'].remove(str(user_id))
                        if 'admins_data' in data and str(user_id) in data['admins_data']:
                            data['admins_data'].pop(str(user_id))
                    else:
                        continue

                else:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    except json.JSONDecodeError:
                        continue
                    except UnicodeDecodeError:
                        try:
                            with open(file_path, 'r', encoding='windows-1251') as f:
                                data = json.load(f)
                        except json.JSONDecodeError:
                            continue
                        except UnicodeDecodeError:
                            continue

                    if isinstance(data, dict):
                        if str(user_id) in data:
                            data.pop(str(user_id), None)
                        else:
                            continue
                    elif isinstance(data, list):
                        updated_data = []
                        for item in data:
                            if isinstance(item, dict) and item.get('user_id') == user_id:
                                continue
                            else:
                                updated_data.append(item)
                        data = updated_data
                    else:
                        continue

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)

    users_data.pop(str(user_id), None)
    save_user_data(users_data)