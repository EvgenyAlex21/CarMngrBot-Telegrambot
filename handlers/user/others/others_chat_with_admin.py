from core.imports import wraps, telebot, types, os, json, re, datetime, time, threading, ApiTelegramException, datetime, timedelta
from core.bot_instance import bot, BASE_DIR
from ..user_main_menu import start as main_start
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

def return_admin_to_menu(admin_id):
    try:
        from handlers.admin.communication.communication import return_admin_to_menu as _f
        return _f(admin_id)
    except Exception:
        pass

def load_user_data():
    try:
        from handlers.user.user_main_menu import load_users_data as _f
        return _f()
    except Exception:
        return {}

def load_blocked_users():
    try:
        from decorators.blocked_user import load_blocked_users as _f
        return _f()
    except Exception:
        return []

def save_blocked_users(data):
    try:
        from decorators.blocked_user import save_blocked_users as _f
        return _f(data)
    except Exception:
        pass

# -------------------------------------------------- ПРОЧЕЕ (чат с админом) ---------------------------------------------------

ACTIVE_CHATS_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'chats', 'active_chats.json')
CHAT_HISTORY_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'chats', 'chat_history.json')
USER_DB_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'users.json')
DB_PATH = USER_DB_PATH

def check_and_create_file():
    dir_path = os.path.dirname(DB_PATH)
    os.makedirs(dir_path, exist_ok=True)
    if not os.path.exists(DB_PATH):
        with open(DB_PATH, 'w', encoding='utf-8') as file:
            json.dump({}, file, ensure_ascii=False, indent=4)

ADMIN_SESSIONS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')
def load_admin_sessions():
    try:
        with open(ADMIN_SESSIONS_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return set(data.get('admin_sessions', []))
    except Exception:
        return set()

admin_sessions = load_admin_sessions()

active_chats = {}
user_requests_chat = {}
active_user_chats = {}
active_admin_chats = {}
current_dialogs = {}

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

def get_active_chats_fresh():
    if os.path.exists(ACTIVE_CHATS_PATH):
        try:
            with open(ACTIVE_CHATS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {int(k): v for k, v in data.get('active_chats', {}).items()}
        except Exception:
            pass
    return {}

def _is_admin_request_pending_for_user(message):
    uid = message.from_user.id
    ac = get_active_chats_fresh()
    data = ac.get(uid)
    return bool(data and data.get('status') == 'pending' and (data.get('awaiting_response', False) or 'admin_id' in data))

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

def escape_markdown(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def ensure_directories_and_file():
    directory = os.path.dirname(ACTIVE_CHATS_PATH)
    if not os.path.exists(directory):
        os.makedirs(directory)
    if not os.path.exists(ACTIVE_CHATS_PATH):
        with open(ACTIVE_CHATS_PATH, 'w', encoding='utf-8') as file:
            json.dump({"active_chats": {}, "user_requests_chat": {}}, file, ensure_ascii=False, indent=4)

def check_user_requests_chat_type(func_name):
    global user_requests_chat
    if not isinstance(user_requests_chat, dict):
        user_requests_chat = {}

def add_user_request(user_id, date, count):
    if user_id not in user_requests_chat:
        user_requests_chat[user_id] = {}

    today = datetime.now().date().isoformat()

    if today not in user_requests_chat[user_id]:
        user_requests_chat[user_id][today] = []

    if len(user_requests_chat[user_id][today]) >= 3:
        return False

    user_requests_chat[user_id][today].append(time.time())
    save_active_chats()
    return True

def load_chat_history():
    if os.path.exists(CHAT_HISTORY_PATH):
        with open(CHAT_HISTORY_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

def save_message_to_history(admin_id, user_id, message_content, message_type, caption=None):
    chat_history = load_chat_history()

    chat_key = f"{admin_id}_{user_id}"
    if chat_key not in chat_history:
        chat_history[chat_key] = []

    timestamp = datetime.now().strftime("%d.%m.%Y в %H:%M")

    if chat_key not in current_dialogs:
        current_dialogs[chat_key] = []

    current_dialogs[chat_key].append({
        "type": message_type,
        "content": message_content,
        "timestamp": timestamp,
        "caption": caption.lower() if caption else None
    })

    with open(CHAT_HISTORY_PATH, 'w', encoding='utf-8') as file:
        json.dump(chat_history, file, ensure_ascii=False, indent=4)

@bot.message_handler(func=lambda message: message.text and message.text.lower() in ["принять", "отклонить"] and _is_admin_request_pending_for_user(message))
@restricted
@track_user_activity
@check_chat_state
def handle_chat_response(message):
    user_id = message.from_user.id

    load_active_chats()

    if user_id in active_chats and active_chats[user_id]["status"] == "pending" and active_chats[user_id]["awaiting_response"]:
        admin_id = active_chats[user_id]["admin_id"]
        users_data = load_users()
        username = users_data.get(str(user_id), {}).get('username', 'Unknown')
        escaped_username = escape_markdown(username)

        if admin_id in active_admin_chats:
            bot.send_message(user_id, "❌ Администратор уже начал чат с другим пользователем! Попробуйте позже...", parse_mode="Markdown")
            start_menu(user_id)
            del active_chats[user_id]
            save_active_chats()
            return

        if message.text.lower() == "принять":
            with threading.Lock():
                if admin_id in active_admin_chats:
                    bot.send_message(user_id, "❌ Администратор уже начал чат с другим пользователем! Попробуйте позже...", parse_mode="Markdown")
                    start_menu(user_id)
                    del active_chats[user_id]
                    save_active_chats()
                    return

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add(types.KeyboardButton('Стоп'))
                bot.send_message(user_id, "✅ Вы на связи с администратором!", parse_mode="Markdown", reply_markup=markup)
                bot.send_message(admin_id, f"✅ Пользователь {escaped_username} - `{user_id}` принял запрос на чат!", parse_mode="Markdown", reply_markup=markup)
                active_chats[user_id]["status"] = "active"
                active_chats[user_id]["awaiting_response"] = False
                active_user_chats[user_id] = admin_id
                active_admin_chats[admin_id] = user_id
                save_active_chats()

        else:  
            bot.send_message(user_id, "✅ Вы отклонили запрос на чат!", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
            bot.send_message(admin_id, f"❌ Пользователь {escaped_username} - `{user_id}` отклонил запрос на чат!", parse_mode="Markdown")
            del active_chats[user_id]
            save_active_chats()
            return_to_menu(message)
            return_admin_to_menu(admin_id)
    else:
        return

@bot.message_handler(func=lambda message: message.text == "В главное меню")
@check_function_state_decorator('В главное меню')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@rate_limit_with_captcha
def return_to_menu(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id in active_chats and active_chats[user_id].get("status") == "waiting_for_topic":
        del active_chats[user_id]
        save_active_chats()

    try:
        from handlers.user.calculators.trip import temporary_trip_data as _tmp
        if user_id in _tmp:
            _tmp[user_id] = []
    except Exception:
        pass

    main_start(message)

def send_message_to_user(user_id, text, reply_markup=None, parse_mode=None):
    blocked_users = load_blocked_users()

    if user_id in blocked_users:
        return

    try:
        bot.send_message(user_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    except ApiTelegramException as e:
        if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
            if user_id not in blocked_users:
                blocked_users.append(user_id)
                save_blocked_users(blocked_users)
        else:
            raise e

@bot.message_handler(func=lambda message: message.text == 'Стоп' or message.text == '/stopchat')
@restricted
@track_user_activity
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@rate_limit_with_captcha
def stop_chat(message):
    user_id = message.from_user.id

    if user_id in active_user_chats:
        admin_id = active_user_chats[user_id]
        users_data = load_users()
        username = users_data.get(str(user_id), {}).get('username', 'Unknown')
        escaped_username = escape_markdown(username)

        bot.send_message(admin_id, f"✅ Пользователь {escaped_username} - `{user_id}` завершил чат!", parse_mode="Markdown")
        bot.send_message(user_id, "✅ Чат с администратором был завершен!", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
        del active_user_chats[user_id]
        del active_admin_chats[admin_id]
        if user_id in active_chats:
            del active_chats[user_id]
        save_active_chats()
        start_menu(user_id)

        chat_key = f"{admin_id}_{user_id}"
        if chat_key in current_dialogs:
            chat_history = load_chat_history()
            chat_history[chat_key].append(current_dialogs[chat_key])
            del current_dialogs[chat_key]
            with open(CHAT_HISTORY_PATH, 'w', encoding='utf-8') as file:
                json.dump(chat_history, file, ensure_ascii=False, indent=4)

        return_admin_to_menu(admin_id)

    elif user_id in active_admin_chats:
        target_user_id = active_admin_chats[user_id]
        bot.send_message(target_user_id, "✅ Администратор завершил чат!", parse_mode="Markdown")
        del active_admin_chats[user_id]
        del active_user_chats[target_user_id]
        if target_user_id in active_chats:
            del active_chats[target_user_id]
        save_active_chats()
        start_menu(target_user_id)

        chat_key = f"{user_id}_{target_user_id}"
        if chat_key in current_dialogs:
            chat_history = load_chat_history()
            chat_history[chat_key].append(current_dialogs[chat_key])
            del current_dialogs[chat_key]
            with open(CHAT_HISTORY_PATH, 'w', encoding='utf-8') as file:
                json.dump(chat_history, file, ensure_ascii=False, indent=4)

        return_admin_to_menu(user_id)

    else:
        bot.send_message(user_id, "❌ Нет активного чата для завершения!")

def start_menu(user_id):
    user_data = load_user_data()
    username = user_data.get(user_id, {}).get('username', 'неизвестный')

    if not username or username == 'неизвестный':
        users_data = load_users()
        username = users_data.get(str(user_id), {}).get('username', 'неизвестный')

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    itembuysub = types.KeyboardButton("Подписка на бота")
    item1 = types.KeyboardButton("Калькуляторы")
    item2 = types.KeyboardButton("Траты и ремонты")
    item3 = types.KeyboardButton("Найти транспорт")
    item4 = types.KeyboardButton("Поиск мест")
    item5 = types.KeyboardButton("Погода")
    item6 = types.KeyboardButton("Цены на топливо")
    item7 = types.KeyboardButton("Код региона")
    item8 = types.KeyboardButton("Коды OBD2")
    item9 = types.KeyboardButton("Напоминания")
    item10 = types.KeyboardButton("Антирадар")
    item11 = types.KeyboardButton("Прочее")

    markup.add(itembuysub)
    markup.add(item1, item2)
    markup.add(item3, item4)
    markup.add(item5, item6)
    markup.add(item7, item8)
    markup.add(item9, item10)
    markup.add(item11)

    welcome_message = f"Добро пожаловать, {escape_markdown(username)}!\nВыберите действие из меню:"
    send_message_to_user(user_id, welcome_message, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Чат с админом")
@check_function_state_decorator('Чат с админом')
@track_usage('Чат с админом')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def request_chat_with_admin(message, show_description=True):
    global active_chats, user_requests_chat
    check_user_requests_chat_type("request_chat_with_admin")
    if not isinstance(user_requests_chat, dict):
        user_requests_chat = {}
    if active_chats is None:
        active_chats = {}

    user_id = message.from_user.id
    today = datetime.now().date().isoformat()

    if any(chat_data.get("user_id") == user_id and chat_data.get("status") == "pending" for chat_data in active_chats.values()):
        bot.send_message(user_id, "⚠️ У вас уже есть запрос на чат к администратору! Ожидайте...")
        return

    user_requests_chat_today = len(user_requests_chat.get(user_id, {}).get(today, []))
    if user_requests_chat_today >= 3:
        bot.send_message(user_id, "❌ Вы исчерпали лимит запросов на сегодня! Попробуйте завтра...")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton('Вернуться в прочее'))
    markup.add(types.KeyboardButton('В главное меню'))

    description = (
        "ℹ️ *Краткая справка по чату*\n\n"
        "📌 *Чат:*\n"
        "Вы можете отправить запрос на чат с администратором (разработчиком), чтобы лично обсудить *вопросы, которые касаются бота* "
        "*(реклама, баги, что-то не работает и т.д.)*\n"
        "Запрос подается *1 раз*, если администратор (разработчик) не видят ее, т.е. она остается в статусе \"ожидание\", "
        "а если же чат завершился по какой-либо причине, то *у вас есть возможность* связаться еще *2 раза*, т.е. *3 раза в сутки.* "
        "Учитывайте, что администратор (разработчик) может *запретить вам общение навсегда*, если оно будет *не по теме*!\n\n"
        "📌 *Чат от администратора (разработчика):*\n"
        "Администратор (разработчик) может кинуть вам *запрос на чат неограниченное количество раз.* "
        "Вы в праве *принять* запрос или *отклонить*!",
    )

    if show_description:
        bot.send_message(user_id, description, parse_mode="Markdown")

    bot.send_message(user_id, "Пожалуйста, укажите тему для общения с администратором:", reply_markup=markup)
    active_chats[user_id] = {"user_id": user_id, "status": "waiting_for_topic", "awaiting_response": False}
    save_active_chats()

def _is_waiting_for_topic(message):
    uid = message.from_user.id
    ac = get_active_chats_fresh()
    data = ac.get(uid)
    return bool(data and data.get('status') == 'waiting_for_topic')

@bot.message_handler(func=_is_waiting_for_topic)
def handle_chat_topic_user(message):
    user_id = message.from_user.id
    topic = message.text
    today = datetime.now().date().isoformat()

    if user_id in active_chats and active_chats[user_id].get("status") == "waiting_for_topic":
        if add_user_request(user_id, today, 1):
            active_chats[user_id] = {
                "user_id": user_id,
                "status": "pending",
                "topic": topic,
                "awaiting_response": False
            }
            save_active_chats()
            bot.send_message(user_id, "✅ Запрос на чат был успешно передан администратору! Ожидаем ответа...")
            return_to_menu(message)
        else:
            bot.send_message(user_id, "❌ Вы исчерпали лимит запросов на сегодня! Попробуйте завтра...")
            del active_chats[user_id]
            save_active_chats()
            return_to_menu(message)
    else:
        bot.send_message(user_id, "⚠️ У вас уже есть запрос на чат к администратору! Ожидайте...")

def check_chat_activity():
    while True:
        current_time = time.time()
        for user_id, chat_data in list(active_chats.items()):
            if chat_data["status"] == "active":
                last_activity_time = chat_data.get("last_activity_time", current_time)
                if current_time - last_activity_time > 180:  
                    admin_id = chat_data.get("admin_id")
                    users_data = load_users()
                    username = users_data.get(str(user_id), {}).get('username', 'Unknown')
                    escaped_username = escape_markdown(username)

                    if admin_id:
                        bot.send_message(admin_id, f"✅ Чат с пользователем {escaped_username} - `{user_id}` был автоматически завершен из-за неактивности!", parse_mode="Markdown")
                        return_admin_to_menu(admin_id)

                    bot.send_message(user_id, "✅ Чат с администратором был автоматически завершен из-за неактивности!", parse_mode="Markdown")
                    start_menu(user_id)

                    chat_key = f"{admin_id}_{user_id}"
                    if chat_key in current_dialogs:
                        chat_history = load_chat_history()
                        chat_history[chat_key].append(current_dialogs[chat_key])
                        del current_dialogs[chat_key]
                        with open(CHAT_HISTORY_PATH, 'w', encoding='utf-8') as file:
                            json.dump(chat_history, file, ensure_ascii=False, indent=4)

                    del active_chats[user_id]
                    save_active_chats()
        time.sleep(15)

threading.Thread(target=check_chat_activity, daemon=True).start()

@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'animation', 'sticker', 'audio', 'contact', 'voice', 'video_note', 'gif'], func=lambda message: (message.from_user.id in active_user_chats or message.from_user.id in active_admin_chats))
@restricted
@track_user_activity
@check_user_blocked
def handle_chat_messages(message):
    user_id = message.from_user.id

    if message.text and message.text.startswith('/') and message.text not in ['/stopchat']:
        return
    if message.text == 'Стоп':
        return

    if user_id in active_chats:
        active_chats[user_id]["last_activity_time"] = time.time()
        save_active_chats()

    if user_id in active_admin_chats:
        target_user_id = active_admin_chats[user_id]
        try:
            if message.content_type == 'text':
                bot.send_message(target_user_id, f"{message.text}")
                save_message_to_history(user_id, target_user_id, message.text, 'admin')
            elif message.content_type == 'photo':
                media_group = []
                media_group.append(types.InputMediaPhoto(message.photo[-1].file_id, caption=message.caption))
                bot.send_media_group(target_user_id, media_group)
                save_message_to_history(user_id, target_user_id, f"photo: {message.photo[-1].file_id}", 'admin', caption=message.caption)
            elif message.content_type == 'video':
                media_group = []
                media_group.append(types.InputMediaVideo(message.video.file_id, caption=message.caption))
                bot.send_media_group(target_user_id, media_group)
                save_message_to_history(user_id, target_user_id, f"video: {message.video.file_id}", 'admin', caption=message.caption)
            elif message.content_type == 'document':
                media_group = []
                media_group.append(types.InputMediaDocument(message.document.file_id, caption=message.caption))
                bot.send_media_group(target_user_id, media_group)
                save_message_to_history(user_id, target_user_id, f"document: {message.document.file_id}", 'admin', caption=message.caption)
            elif message.content_type == 'animation':
                bot.send_animation(target_user_id, message.animation.file_id, caption=message.caption)
                save_message_to_history(user_id, target_user_id, f"animation: {message.animation.file_id}", 'admin', caption=message.caption)
            elif message.content_type == 'sticker':
                bot.send_sticker(target_user_id, message.sticker.file_id)
                save_message_to_history(user_id, target_user_id, f"sticker: {message.sticker.file_id}", 'admin')
            elif message.content_type == 'audio':
                bot.send_audio(target_user_id, message.audio.file_id, caption=message.caption)
                save_message_to_history(user_id, target_user_id, f"audio: {message.audio.file_id}", 'admin', caption=message.caption)
            elif message.content_type == 'contact':
                bot.send_contact(target_user_id, message.contact.phone_number, message.contact.first_name)
                save_message_to_history(user_id, target_user_id, f"contact: {message.contact.phone_number}", 'admin')
            elif message.content_type == 'voice':
                bot.send_voice(target_user_id, message.voice.file_id, caption=message.caption)
                save_message_to_history(user_id, target_user_id, f"voice: {message.voice.file_id}", 'admin', caption=message.caption)
            elif message.content_type == 'video_note':
                bot.send_video_note(target_user_id, message.video_note.file_id)
                save_message_to_history(user_id, target_user_id, f"video_note: {message.video_note.file_id}", 'admin')
            elif message.content_type == 'gif':
                bot.send_document(target_user_id, message.document.file_id, caption=message.caption)
                save_message_to_history(user_id, target_user_id, f"gif: {message.document.file_id}", 'admin', caption=message.caption)
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                blocked_users = load_blocked_users()
                if target_user_id not in blocked_users:
                    blocked_users.append(target_user_id)
                    save_blocked_users(blocked_users)
            else:
                raise e

    elif user_id in active_user_chats:
        target_admin_id = active_user_chats[user_id]
        try:
            if message.content_type == 'text':
                bot.send_message(target_admin_id, f"{message.text}")
                save_message_to_history(target_admin_id, user_id, message.text, 'user')
            elif message.content_type == 'photo':
                media_group = []
                media_group.append(types.InputMediaPhoto(message.photo[-1].file_id, caption=message.caption))
                bot.send_media_group(target_admin_id, media_group)
                save_message_to_history(target_admin_id, user_id, f"photo: {message.photo[-1].file_id}", 'user', caption=message.caption)
            elif message.content_type == 'video':
                media_group = []
                media_group.append(types.InputMediaVideo(message.video.file_id, caption=message.caption))
                bot.send_media_group(target_admin_id, media_group)
                save_message_to_history(target_admin_id, user_id, f"video: {message.video.file_id}", 'user', caption=message.caption)
            elif message.content_type == 'document':
                media_group = []
                media_group.append(types.InputMediaDocument(message.document.file_id, caption=message.caption))
                bot.send_media_group(target_admin_id, media_group)
                save_message_to_history(target_admin_id, user_id, f"document: {message.document.file_id}", 'user', caption=message.caption)
            elif message.content_type == 'animation':
                bot.send_animation(target_admin_id, message.animation.file_id, caption=message.caption)
                save_message_to_history(target_admin_id, user_id, f"animation: {message.animation.file_id}", 'user', caption=message.caption)
            elif message.content_type == 'sticker':
                bot.send_sticker(target_admin_id, message.sticker.file_id)
                save_message_to_history(target_admin_id, user_id, f"sticker: {message.sticker.file_id}", 'user')
            elif message.content_type == 'audio':
                bot.send_audio(target_admin_id, message.audio.file_id, caption=message.caption)
                save_message_to_history(target_admin_id, user_id, f"audio: {message.audio.file_id}", 'user', caption=message.caption)
            elif message.content_type == 'contact':
                bot.send_contact(target_admin_id, message.contact.phone_number, message.contact.first_name)
                save_message_to_history(target_admin_id, user_id, f"contact: {message.contact.phone_number}", 'user')
            elif message.content_type == 'voice':
                bot.send_voice(target_admin_id, message.voice.file_id, caption=message.caption)
                save_message_to_history(target_admin_id, user_id, f"voice: {message.voice.file_id}", 'user', caption=message.caption)
            elif message.content_type == 'video_note':
                bot.send_video_note(target_admin_id, message.video_note.file_id)
                save_message_to_history(target_admin_id, user_id, f"video_note: {message.video_note.file_id}", 'user')
            elif message.content_type == 'gif':
                bot.send_document(target_admin_id, message.document.file_id, caption=message.caption)
                save_message_to_history(target_admin_id, user_id, f"gif: {message.document.file_id}", 'user', caption=message.caption)
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                blocked_users = load_blocked_users()
                if user_id not in blocked_users:
                    blocked_users.append(user_id)
                    save_blocked_users(blocked_users)
            else:
                raise e

@bot.message_handler(func=lambda message: _is_waiting_for_topic(message) and str(message.from_user.id) not in admin_sessions)
def handle_chat_topic(message):
    user_id = message.from_user.id
    topic = message.text
    today = datetime.now().date().isoformat()

    if user_id in active_chats and active_chats[user_id].get("status") == "waiting_for_topic":
        if add_user_request(user_id, today, 1):
            active_chats[user_id] = {
                "user_id": user_id,
                "status": "pending",
                "topic": topic,
                "awaiting_response": False
            }
            save_active_chats()
            bot.send_message(user_id, "✅ Запрос на чат был успешно передан администратору! Ожидаем ответа...")
            return_to_menu(message)
        else:
            bot.send_message(user_id, "❌ Вы исчерпали лимит запросов на сегодня! Попробуйте завтра...")
            del active_chats[user_id]
            save_active_chats()
            return_to_menu(message)
    else:
        bot.send_message(user_id, "⚠️ У вас уже есть запрос на чат к администратору! Ожидайте...")