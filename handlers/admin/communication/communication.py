from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, ApiTelegramException, ReplyKeyboardMarkup, KeyboardButton
from core.bot_instance import bot, BASE_DIR
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from handlers.user.others.others_chat_with_admin import check_and_create_file, DB_PATH, start_menu
from decorators.blocked_user import load_blocked_users
from handlers.admin.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha,
)

# -------------------------------------------------- ОБЩЕНИЕ ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Общение')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_communication_menu(message):
    if not check_admin_access(message):
        return
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Общение'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Чат', 'Запросы')
    markup.add('Оповещения', 'Диалоги')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите действие из общения:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Вернуться в общение' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_communication(message):
    show_communication_menu(message)

# -------------------------------------------------- ОБЩЕНИЕ_ЧАТ ---------------------------------------------------

ADMIN_SESSIONS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')
USER_DB_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'users.json')
ADMIN_DB_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')
ACTIVE_CHATS_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'chats', 'active_chats.json')
CHAT_HISTORY_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'chats', 'chat_history.json')
MAX_MESSAGE_LENGTH = 4096

active_chats = {}
user_requests_chat = {}
active_user_chats = {}
active_admin_chats = {}

def check_admin_access(message):
    admin_sessions = load_admin_sessions()
    if str(message.chat.id) in admin_sessions:
        return True
    else:
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return False

def load_admin_sessions():
    with open(ADMIN_SESSIONS_FILE, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data['admin_sessions']

def load_active_chats():
    global active_chats, user_requests_chat
    if os.path.exists(ACTIVE_CHATS_PATH):
        with open(ACTIVE_CHATS_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)
            active_chats = {int(k): v for k, v in data.get("active_chats", {}).items()}
            user_requests_chat_data = data.get("user_requests_chat", {})
            user_requests_chat = {
                int(k): v if isinstance(v, dict) else {}
                for k, v in user_requests_chat_data.items()
            }
    else:
        active_chats = {}
        user_requests_chat = {}

load_active_chats()

def save_active_chats():
    with open(ACTIVE_CHATS_PATH, 'w', encoding='utf-8') as file:
        data = {
            "active_chats": {str(k): v for k, v in active_chats.items()},
            "user_requests_chat": {str(k): v for k, v in user_requests_chat.items()}
        }
        json.dump(data, file, ensure_ascii=False, indent=4)

def load_users():
    check_and_create_file()
    try:
        with open(DB_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except UnicodeDecodeError as e:
        with open(DB_PATH, 'r', encoding='cp1251') as file:
            content = file.read()
            with open(DB_PATH, 'w', encoding='utf-8') as outfile:
                json.dump(json.loads(content), outfile, ensure_ascii=False, indent=4)
            return json.loads(content)
    except json.JSONDecodeError as e:
        return {}

def load_admins():
    if os.path.exists(ADMIN_DB_PATH):
        with open(ADMIN_DB_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    return []

def is_admin(user_id):
    admins = load_admins()
    return user_id in admins

def escape_markdown(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

@bot.message_handler(func=lambda message: message.text == 'Чат' and check_admin_access(message))
@bot.message_handler(commands=['chat'])
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def initiate_chat(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Чат'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if not check_admin_access(message):
        return

    if admin_id in active_admin_chats:
        existing_user_id = active_admin_chats[admin_id]
        bot.send_message(admin_id, f"⚠️ У вас уже есть запрос к пользователю `{existing_user_id}`!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в общение":
        return_to_communication(message)
        return

    command_parts = message.text.split()
    if len(command_parts) == 2:
        user_input = command_parts[1]
        users_data = load_users()
        blocked_users = load_blocked_users()

        if len(user_input) <= 5 and user_input.isdigit():
            try:
                user_number = int(user_input)
                if user_number < 1 or user_number > len(users_data):
                    bot.send_message(message.chat.id, f"❌ Неверный номер `{user_number}` пользователя!", parse_mode="Markdown")
                    return
                user_id = list(users_data.keys())[user_number - 1]
                username = users_data[user_id]['username']
                if user_id in blocked_users:
                    bot.send_message(message.chat.id, f"⚠️ Пользователь с номером `{user_number}` заблокирован!", parse_mode="Markdown")
                    return
            except ValueError:
                bot.send_message(message.chat.id, "Неверный формат номера пользователя!")
                return
        elif user_input.isdigit():
            user_id = int(user_input)
            if str(user_id) not in users_data:
                bot.send_message(message.chat.id, f"❌ Пользователь с таким id - `{user_id}` не найден!", parse_mode="Markdown")
                return
            if user_id in blocked_users:
                bot.send_message(message.chat.id, f"⚠️ Пользователь с таким id - `{user_id}` заблокирован!", parse_mode="Markdown")
                return
            username = users_data[str(user_id)]['username']
        elif user_input.startswith('@'):
            username = user_input
            user_id = None
            for uid, data in users_data.items():
                if data.get('username') == username:
                    user_id = int(uid)
                    break
            if user_id is None:
                bot.send_message(message.chat.id, f"❌ Пользователь с таким username - {escape_markdown(username)} не найден!", parse_mode="Markdown")
                return
            if user_id in blocked_users:
                bot.send_message(message.chat.id, f"⚠️ Пользователь с таким username - {escape_markdown(username)} заблокирован!", parse_mode="Markdown")
                return
        else:
            bot.send_message(message.chat.id, "Неверный формат ввода!")
            return

        if str(user_id) == admin_id:
            bot.send_message(message.chat.id, "⚠️ Вы не можете начать чат с самим собой!", parse_mode="Markdown")
            return

        if user_id in active_chats:
            if active_chats[user_id].get("admin_id") is None:
                active_chats[user_id]["admin_id"] = message.chat.id
                save_active_chats()
            else:
                bot.send_message(message.chat.id, "⚠️ Этот пользователь уже находится в активном чате с другим администратором!")
                return

        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add('Принять', 'Отклонить')
        markup.add('В главное меню')
        bot.send_message(user_id, "🚨 Администратор хочет связаться с вами!\n\nВыберите *ПРИНЯТЬ* для принятия или *ОТКЛОНИТЬ* для отклонения!", parse_mode="Markdown", reply_markup=markup)
        bot.send_message(message.chat.id, f"✅ Запрос отправлен пользователю {escape_markdown(username)} - `{user_id}`! Ожидаем ответа...", parse_mode="Markdown")

        active_chats[user_id] = {"admin_id": message.chat.id, "status": "pending", "awaiting_response": True}
        save_active_chats()

        def check_response_timeout(user_id):
            load_active_chats()
            chat = active_chats.get(user_id)
            if chat and chat.get("status") == "pending":
                admin_id = chat.get("admin_id")
                bot.send_message(admin_id, f"❌ Пользователь {escape_markdown(username)} - `{user_id}` не ответил на запрос! Чат завершен...", parse_mode="Markdown")
                bot.send_message(user_id, "❌ Время ожидания для принятие или отклонения чата истекло, он был завершен!")
                active_chats.pop(user_id, None)
                save_active_chats()
                start_menu(user_id)

        timer = threading.Timer(30.0, check_response_timeout, [user_id])
        timer.start()

    else:
        list_users_for_chat(message)

def list_users_for_chat(message):
    users_data = load_users()
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

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton('Вернуться в общение'))
    markup.add(types.KeyboardButton('В меню админ-панели'))

    bot.send_message(
        message.chat.id,
        "Пожалуйста, укажите один из следующих параметров для начала чата:\n\n"
        "1. Номер пользователя из списка в формате: `/chat 0`\n"
        "2. Id пользователя в формате: `/chat id`\n"
        "3. Username в формате: `/chat @username`\n",
        parse_mode="Markdown",
        reply_markup=markup
    )

# -------------------------------------------------- ОБЩЕНИЕ_ЗАПРОСЫ ---------------------------------------------------

admin_request_selection = {}

@bot.message_handler(func=lambda message: message.text == 'Запросы' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def list_chat_requests(message):
    admin_id = message.from_user.id

    load_active_chats()

    requests = [
        (user_id, data.get("topic", "Без темы"))
        for user_id, data in active_chats.items()
        if isinstance(data, dict) and data.get("status") == "pending"
    ]

    if not requests:
        bot.send_message(admin_id, "❌ Нет активных запросов на чат!", parse_mode="Markdown")
        return

    users_data = load_users()
    request_list = []
    for i, (user_id, topic) in enumerate(requests):
        username = users_data.get(str(user_id), {}).get('username', 'Unknown')
        escaped_username = escape_markdown(username)
        request_list.append(f"🔹 *№{i + 1}.* Запрос от пользователя:\n👤 {escaped_username} - `{user_id}`\n📨 *Тема*: {topic.lower()}")

    request_list_message = "*Список запросов на чат:*\n\n" + "\n\n".join(request_list) + "\n\nВведите номер запроса для начала диалога:\n\n_P.S. Если вы передумали выбирать запрос, то объязательно выйдите из режима выбора запросов!_"

    parts = [request_list_message[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(request_list_message), MAX_MESSAGE_LENGTH)]

    for part in parts:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton('Выйти из режима запросов'))
        markup.add(types.KeyboardButton('Вернуться в общение'))
        markup.add(types.KeyboardButton('В меню админ-панели'))

        bot.send_message(admin_id, part, parse_mode="Markdown", reply_markup=markup)

    admin_request_selection[admin_id] = True

@bot.message_handler(func=lambda message: admin_request_selection.get(message.from_user.id, False))
def handle_request_selection(message):
    admin_id = message.from_user.id

    load_active_chats()

    if message.text.lower() == 'выйти из режима запросов':
        del admin_request_selection[admin_id]
        bot.send_message(admin_id, "✅ Вы вышли из режима выбора запросов!")
        return_to_communication(message)
        return

    if not message.text.isdigit() or int(message.text) <= 0:
        bot.send_message(admin_id, "Пожалуйста, введите корректный номер запроса!")
        return

    requests = [
        (user_id, data.get("topic", "Без темы"))
        for user_id, data in active_chats.items()
        if isinstance(data, dict) and data.get("status") == "pending"
    ]

    if not requests:
        bot.send_message(admin_id, "❌ Нет активных запросов для выбора!")
        return

    try:
        selected_index = int(message.text) - 1

        if selected_index < 0 or selected_index >= len(requests):
            bot.send_message(admin_id, "Такого номера запроса не существует! Пожалуйста, введите корректный номер запроса")
            return

        selected_user_id, topic = requests[selected_index]
        users_data = load_users()
        username = users_data.get(str(selected_user_id), {}).get('username', 'Unknown')

        if selected_user_id in active_chats:
            if active_chats[selected_user_id].get("admin_id") is None:
                active_chats[selected_user_id]["admin_id"] = admin_id
                save_active_chats()
            else:
                admin_id_in_chat = active_chats[selected_user_id]["admin_id"]
                bot.send_message(admin_id, f"⚠️ Этот пользователь уже находится в активном чате с администратором `{admin_id_in_chat}`!", parse_mode="Markdown")
                show_communication_menu(message)
                return

        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add('Принять', 'Отклонить')
        markup.add('В главное меню')

        bot.send_message(selected_user_id, "🚨 Администратор хочет связаться с вами!\n\nВыберите *ПРИНЯТЬ* для принятия или *ОТКЛОНИТЬ* для отклонения!", parse_mode="Markdown", reply_markup=markup)
        bot.send_message(admin_id, f"✅ Запрос отправлен пользователю {escape_markdown(username)} - `{selected_user_id}`! Ожидаем ответа...", parse_mode="Markdown")

        active_chats[selected_user_id] = {"admin_id": admin_id, "status": "pending", "awaiting_response": True}
        save_active_chats()

        def check_response_timeout(user_id):
            load_active_chats()
            chat = active_chats.get(user_id)
            if chat and chat.get("status") == "pending":
                admin_id = chat.get("admin_id")
                bot.send_message(admin_id, f"❌ Пользователь {escape_markdown(username)} - `{user_id}` не ответил на запрос! Чат завершен...", parse_mode="Markdown")
                bot.send_message(user_id, "❌ Время ожидания для принятия или отклонения чата истекло, он был завершен!")
                active_chats.pop(user_id, None)
                save_active_chats()
                start_menu(user_id)

        timer = threading.Timer(30.0, check_response_timeout, [selected_user_id])
        timer.start()

        del admin_request_selection[admin_id]

    except ValueError:
        pass

def return_admin_to_menu(admin_id):
    bot.send_message(admin_id, "✅ Чат с пользователем был завершен!", parse_mode="Markdown")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Управление системой')
    markup.add('Админ', 'Бан', 'Функции')
    markup.add('Статистика', 'Файлы', 'Резервная копия')
    markup.add('Общение', 'Реклама', 'Редакция')
    markup.add('Экстренная остановка')
    markup.add('Выход')
    bot.send_message(admin_id, "Выберите действие из админ-панели:", reply_markup=markup)