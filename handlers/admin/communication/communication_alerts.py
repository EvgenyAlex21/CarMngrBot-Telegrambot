from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, ApiTelegramException, ReplyKeyboardMarkup, KeyboardButton
from core.bot_instance import bot, BASE_DIR
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from handlers.admin.advertisement.advertisement import validate_time_format
from handlers.admin.admin.admin import escape_markdown
from handlers.admin.communication.communication import show_communication_menu
from handlers.user.others.others_chat_with_admin import check_and_create_file, DB_PATH
from decorators.blocked_user import load_blocked_users, save_blocked_users
from handlers.admin.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha,
)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ ---------------------------------------------------

DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'chats', 'alerts.json')
ADMIN_SESSIONS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')
USER_DATA_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'users.json')
alerts = {"sent_messages": {}, "notifications": {}}
blocked_users = load_blocked_users()
admin_sessions = []

def load_admin_sessions():
    if os.path.exists(ADMIN_SESSIONS_FILE):
        with open(ADMIN_SESSIONS_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data.get('admin_sessions', [])
    return []

admin_sessions = load_admin_sessions()

def check_admin_access(message):
    if str(message.chat.id) in admin_sessions:
        return True
    else:
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return False

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

def save_database():
    for key, value in alerts['notifications'].items():
        if 'time' in value and isinstance(value['time'], datetime):
            value['time'] = value['time'].strftime("%d.%m.%Y в %H:%M")
    for key, value in alerts['sent_messages'].items():
        if 'time' in value and isinstance(value['time'], datetime):
            value['time'] = value['time'].strftime("%d.%m.%Y в %H:%M")

    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    try:
        with open(DATABASE_PATH, 'w', encoding='utf-8') as file:
            json.dump(alerts, file, ensure_ascii=False, indent=4)
    except Exception as e:
        pass

    for key, value in alerts['notifications'].items():
        if 'time' in value and isinstance(value['time'], str):
            value['time'] = datetime.strptime(value['time'], "%d.%m.%Y в %H:%M")
    for key, value in alerts['sent_messages'].items():
        if 'time' in value and isinstance(value['time'], str):
            value['time'] = datetime.strptime(value['time'], "%d.%m.%Y в %H:%M")

def load_database():
    if os.path.exists(DATABASE_PATH):
        try:
            with open(DATABASE_PATH, 'r', encoding='utf-8') as file:
                data = json.load(file)

            for key, value in data['notifications'].items():
                if 'time' in value and value['time']:
                    value['time'] = datetime.strptime(value['time'], "%d.%m.%Y в %H:%M")

            if isinstance(data['sent_messages'], list):
                sent_messages_dict = {}
                for i, msg in enumerate(data['sent_messages']):
                    msg_id = str(i + 1)
                    sent_messages_dict[msg_id] = msg
                    if 'time' in msg and msg['time']:
                        msg['time'] = datetime.strptime(msg['time'], "%d.%m.%Y в %H:%M")
                data['sent_messages'] = sent_messages_dict
            else:
                for key, value in data['sent_messages'].items():
                    if 'time' in value and value['time']:
                        value['time'] = datetime.strptime(value['time'], "%d.%m.%Y в %H:%M")

            return data
        except Exception:
            pass

    return {"sent_messages": {}, "notifications": {}}

alerts = load_database()

def check_notifications():
    while True:
        now = datetime.now()
        for key, n in alerts['notifications'].items():
            if n['status'] == 'active' and 'time' in n and n['time'] <= now:
                user_id = n.get('user_id')
                if user_id:
                    user_ids = [user_id]
                else:
                    user_ids = load_users().keys()

                for user_id in user_ids:
                    if user_id in blocked_users:
                        continue

                    if n.get('text'):
                        try:
                            bot.send_message(user_id, n['text'])
                        except ApiTelegramException as e:
                            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                                pass
                                if user_id not in blocked_users:
                                    blocked_users.append(user_id)
                                    save_blocked_users(blocked_users)  
                            else:
                                raise e
                    else:
                        for file in n.get('files', []):
                            try:
                                if file['type'] == 'photo':
                                    bot.send_photo(user_id, file['file_id'], caption=file.get('caption'))
                                elif file['type'] == 'video':
                                    bot.send_video(user_id, file['file_id'], caption=file.get('caption'))
                                elif file['type'] == 'document':
                                    bot.send_document(user_id, file['file_id'], caption=file.get('caption'))
                                elif file['type'] == 'animation':
                                    bot.send_animation(user_id, file['file_id'], caption=file.get('caption'))
                                elif file['type'] == 'sticker':
                                    bot.send_sticker(user_id, file['file_id'])
                                elif file['type'] == 'audio':
                                    bot.send_audio(user_id, file['file_id'], caption=file.get('caption'))
                                elif file['type'] == 'voice':
                                    bot.send_voice(user_id, file['file_id'], caption=file.get('caption'))
                                elif file['type'] == 'video_note':
                                    bot.send_video_note(user_id, file['file_id'])
                            except ApiTelegramException as e:
                                if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                                    pass
                                    if user_id not in blocked_users:
                                        blocked_users.append(user_id)
                                        save_blocked_users(blocked_users)  
                                else:
                                    raise e
                n['status'] = 'sent'
        save_database()
        time.sleep(60)

threading.Thread(target=check_notifications, daemon=True).start()

@bot.message_handler(func=lambda message: message.text == 'Оповещения' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_notifications_menu(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Оповещения'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    markup = telebot.types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add('Всем', 'По времени', 'Отдельно')
    markup.add("Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите тип оповещения:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Вернуться в оповещения' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_notifications_menu(message):
    show_notifications_menu(message)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (по времени) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'По времени' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_time_notifications(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'По времени'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Отправить по времени')
    markup.add('Просмотр (по времени)', 'Удалить (по времени)')
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Управление оповещениями по времени:", reply_markup=markup)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (отправить по времени) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Отправить по времени' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def schedule_notification(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Отправить по времени'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Отправить всем', 'Отправить отдельно')
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите действие для отправки по времени:", reply_markup=markup)
    bot.register_next_step_handler(message, choose_send_action)

@text_only_handler
def choose_send_action(message):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return

    if message.text == 'Отправить всем':
        markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("Вернуться в оповещения", "Вернуться в общение")
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Введите тему оповещения:", reply_markup=markup)
        bot.register_next_step_handler(message, set_theme_for_notification)
    elif message.text == 'Отправить отдельно':
        list_users_for_time_notification(message)

@text_only_handler
def set_theme_for_notification(message):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    notification_theme = message.text
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите текст оповещения или отправьте мультимедийный файл:", reply_markup=markup)
    bot.register_next_step_handler(message, set_time_for_notification, notification_theme)

def set_time_for_notification(message, notification_theme):
    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    notification_text = message.text or message.caption
    content_type = message.content_type
    file_id = None
    caption = message.caption

    if content_type == 'photo':
        file_id = message.photo[-1].file_id
    elif content_type == 'video':
        file_id = message.video.file_id
    elif content_type == 'document':
        file_id = message.document.file_id
    elif content_type == 'animation':
        file_id = message.animation.file_id
    elif content_type == 'sticker':
        file_id = message.sticker.file_id
    elif content_type == 'audio':
        file_id = message.audio.file_id
    elif content_type == 'voice':
        file_id = message.voice.file_id
    elif content_type == 'video_note':
        file_id = message.video_note.file_id

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите дату оповещения в формате ДД.ММ.ГГГГ:", reply_markup=markup)
    bot.register_next_step_handler(message, process_notification_date, notification_theme, notification_text, content_type, file_id, caption)

@text_only_handler
def process_notification_date(message, notification_theme, notification_text, content_type, file_id, caption):

    date_str = message.text

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    if not validate_date_format(date_str):
        bot.send_message(message.chat.id, "Неверный формат даты! Введите дату в формате ДД.ММ.ГГГГ")
        bot.register_next_step_handler(message, process_notification_date, notification_theme, notification_text, content_type, file_id, caption)
        return

    try:
        notification_date = datetime.strptime(date_str, "%d.%m.%Y")
        if notification_date.date() < datetime.now().date():
            bot.send_message(message.chat.id, "Введенная дата уже прошла! Пожалуйста, введите корректную дату")
            bot.register_next_step_handler(message, process_notification_date, notification_theme, notification_text, content_type, file_id, caption)
            return
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат даты! Введите дату в формате ДД.ММ.ГГГГ")
        bot.register_next_step_handler(message, process_notification_date, notification_theme, notification_text, content_type, file_id, caption)
        return

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите время оповещения в формате ЧЧ:ММ:", reply_markup=markup)
    bot.register_next_step_handler(message, process_notification_time, notification_theme, notification_text, date_str, content_type, file_id, caption)

def validate_date_format(date_str):
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False

@text_only_handler
def process_notification_time(message, notification_theme, notification_text, date_str, content_type, file_id, caption):

    time_str = message.text

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    if not validate_time_format(time_str):
        bot.send_message(message.chat.id, "Неверный формат времени! Введите время в формате ЧЧ:ММ")
        bot.register_next_step_handler(message, process_notification_time, notification_theme, notification_text, date_str, content_type, file_id, caption)
        return

    try:
        notification_time = datetime.strptime(f"{date_str}, {time_str}", "%d.%m.%Y, %H:%M")
        if notification_time < datetime.now():
            bot.send_message(message.chat.id, "Введенное время уже прошло! Пожалуйста, введите корректное время")
            bot.register_next_step_handler(message, process_notification_time, notification_theme, notification_text, date_str, content_type, file_id, caption)
            return
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат времени! Введите время в формате ЧЧ:ММ")
        bot.register_next_step_handler(message, process_notification_time, notification_theme, notification_text, date_str, content_type, file_id, caption)
        return

    notification_id = str(len(alerts['notifications']) + 1)
    alerts['notifications'][notification_id] = {
        'theme': notification_theme,
        'text': notification_text if content_type == 'text' else None,
        'time': notification_time,
        'status': 'active',
        'category': 'time',
        'user_id': None,
        'files': [
            {
                'type': content_type,
                'file_id': file_id,
                'caption': caption if content_type != 'text' else None
            }
        ],
        'content_type': content_type
    }
    save_database()
    bot.send_message(message.chat.id, f"✅ Оповещение *{notification_theme.lower()}* запланировано на {notification_time.strftime('%d.%m.%Y в %H:%M')}!", parse_mode="Markdown")
    show_notifications_menu(message)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (просмотр по времени) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Просмотр (по времени)' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_view_notifications(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Просмотр (по времени)'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Активные (по времени)', 'Остановленные (по времени)')
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите тип просмотра оповещений:", reply_markup=markup)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (активные по времени) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Активные (по времени)' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_active_notifications(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Активные (по времени)'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    if alerts['notifications']:
        active_notifications = [
            f"⭐ №{i + 1} ⭐\n\n📝 *Тема*: {n['theme'].lower() if n['theme'] else 'без темы'}\n📅 *Дата*: {n['time'].strftime('%d.%m.%Y')}\n🕒 *Время*: {n['time'].strftime('%H:%M')}\n🔄 *Статус*: {'отправлено' if n['status'] == 'sent' else 'отложено'}\n"
            for i, n in enumerate([n for n in alerts['notifications'].values() if n['status'] == 'active' and n['category'] == 'time'])
        ]
        if active_notifications:
            bot.send_message(message.chat.id, "*Список активных оповещений (по времени)*:\n\n" + "\n\n".join(active_notifications), parse_mode="Markdown")

            markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.add("Вернуться в оповещения", "Вернуться в общение")
            markup.add('В меню админ-панели')

            bot.send_message(message.chat.id, "Введите номера оповещений для просмотра через запятую:", reply_markup=markup)
            bot.register_next_step_handler(message, show_notification_details, 'active')
        else:
            bot.send_message(message.chat.id, "❌ Нет активных оповещений!")
    else:
        bot.send_message(message.chat.id, "❌ Нет активных оповещений!")

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (остановленне по времени) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Остановленные (по времени)' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_stopped_notifications(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Остановленные (по времени)'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    stopped_notifications = [
        f"⭐ №{i + 1} ⭐\n\n📝 *Тема*: {n['theme'].lower() if n['theme'] else 'без темы'}\n📅 *Дата*: {n['time'].strftime('%d.%m.%Y')}\n🕒 *Время*: {n['time'].strftime('%H:%M')}\n🔄 *Статус*: {'отправлено' if n['status'] == 'sent' else 'отложено'}\n"
        for i, n in enumerate([n for n in alerts['notifications'].values() if n['status'] == 'sent' and n['category'] == 'time'])
    ]
    if stopped_notifications:
        bot.send_message(message.chat.id, "*Список остановленных оповещений (по времени)*:\n\n" + "\n\n".join(stopped_notifications), parse_mode="Markdown")

        markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("Вернуться в оповещения", "Вернуться в общение")
        markup.add('В меню админ-панели')

        bot.send_message(message.chat.id, "Введите номера оповещений для просмотра через запятую:", reply_markup=markup)
        bot.register_next_step_handler(message, show_notification_details, 'sent')
    else:
        bot.send_message(message.chat.id, "❌ Нет остановленных оповещений!")

@text_only_handler
def show_notification_details(message, status):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        indices = [int(index.strip()) - 1 for index in message.text.split(',')]
        notifications = [n for n in alerts['notifications'].values() if n['status'] == status and n['category'] == 'time']
        valid_indices = [index for index in indices if 0 <= index < len(notifications)]

        if len(valid_indices) != len(indices):
            invalid_numbers = [str(index + 1) for index in indices if index not in valid_indices]
            bot.send_message(message.chat.id, f"❌ Неверные номера для просмотра: `{','.join(invalid_numbers)}`! Они будут пропущены...", parse_mode="Markdown")
            if len(valid_indices) == 0:
                bot.register_next_step_handler(message, show_notification_details, status)
                return

        for index in valid_indices:
            notification = notifications[index]
            theme = notification['theme'].lower() if notification['theme'] else 'без темы'
            content_type = notification.get('content_type', 'текст')
            status_text = 'отправлено' if notification['status'] == 'sent' else 'активно'

            notification_details = (
                f"*Основная информация*:\n\n"
                f"📝 *Тема*: {theme}\n"
                f"📁 *Тип контента*: {content_type}\n"
                f"📅 *Дата*: {notification['time'].strftime('%d.%m.%Y')}\n"
                f"🕒 *Время*: {notification['time'].strftime('%H:%M')}\n"
                f"🔄 *Статус*: {status_text}\n"
            )

            if content_type == 'text':
                notification_details += f"\n*Текст сообщения*:\n\n{notification['text']}\n"

            bot.send_message(message.chat.id, notification_details, parse_mode="Markdown")

            if content_type != 'text':
                for file in notification.get('files', []):
                    if file['type'] == 'photo':
                        bot.send_photo(message.chat.id, file['file_id'], caption=file.get('caption'))
                    elif file['type'] == 'video':
                        bot.send_video(message.chat.id, file['file_id'], caption=file.get('caption'))
                    elif file['type'] == 'document':
                        bot.send_document(message.chat.id, file['file_id'], caption=file.get('caption'))
                    elif file['type'] == 'animation':
                        bot.send_animation(message.chat.id, file['file_id'], caption=file.get('caption'))
                    elif file['type'] == 'sticker':
                        bot.send_sticker(message.chat.id, file['file_id'])
                    elif file['type'] == 'audio':
                        bot.send_audio(message.chat.id, file['file_id'], caption=file.get('caption'))
                    elif file['type'] == 'voice':
                        bot.send_voice(message.chat.id, file['file_id'], caption=file.get('caption'))
                    elif file['type'] == 'video_note':
                        bot.send_video_note(message.chat.id, file['file_id'])

        show_notifications_menu(message)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер оповещения!")
        bot.register_next_step_handler(message, show_notification_details, status)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (удалить по времени) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Удалить (по времени)' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_notification(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Удалить (по времени)'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    notifications_list = [
        f"⭐ *№{i + 1}* ⭐\n\n📝 *Тема*: {n['theme'].lower() if n['theme'] else 'без темы'}\n📅 *Дата*: {n['time'].strftime('%d.%m.%Y')}\n🕒 *Время*: {n['time'].strftime('%H:%M')}\n🔄 *Статус*: {'отправлено' if n['status'] == 'sent' else 'активно'}"
        for i, n in enumerate([n for n in alerts['notifications'].values() if n['category'] == 'time'])
    ]
    if notifications_list:
        bot.send_message(message.chat.id, "*Список для удаления (по времени)*:\n\n" + "\n\n".join(notifications_list), parse_mode="Markdown")

        markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("Вернуться в оповещения", "Вернуться в общение")
        markup.add('В меню админ-панели')

        bot.send_message(message.chat.id, "Введите номера оповещений для удаления через запятую:", reply_markup=markup)
        bot.register_next_step_handler(message, process_delete_notification)
    else:
        bot.send_message(message.chat.id, "❌ Нет оповещений по времени для удаления!")

@text_only_handler
def process_delete_notification(message):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        indices = [int(index.strip()) - 1 for index in message.text.split(',')]
        notifications = list(alerts['notifications'].values())
        valid_indices = [index for index in indices if 0 <= index < len(notifications)]

        if len(valid_indices) != len(indices):
            invalid_numbers = [str(index + 1) for index in indices if index not in valid_indices]
            bot.send_message(message.chat.id, f"❌ Неверные номера для удаления: `{','.join(invalid_numbers)}`! Они будут пропущены...", parse_mode="Markdown")
            if len(valid_indices) == 0:
                bot.register_next_step_handler(message, process_delete_notification)
                return

        deleted_notifications = []
        for index in sorted(valid_indices, reverse=True):
            notification_id = list(alerts['notifications'].keys())[index]
            deleted_notification = alerts['notifications'].pop(notification_id)
            deleted_notifications.append(deleted_notification)

        new_notifications = {}
        for i, (notification_id, notification) in enumerate(alerts['notifications'].items(), start=1):
            new_notifications[str(i)] = notification

        alerts['notifications'] = new_notifications
        save_database()

        deleted_themes = ", ".join([f"*{msg['theme'].lower()}*" for msg in deleted_notifications])
        bot.send_message(message.chat.id, f"✅ Оповещения по темам *{deleted_themes}* были удалены!", parse_mode="Markdown")

        show_notifications_menu(message)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер оповещения!")
        bot.register_next_step_handler(message, process_delete_notification)

@text_only_handler
def list_users_for_time_notification(message):
    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

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

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер пользователя для отправки оповещения:", reply_markup=markup)
    bot.register_next_step_handler(message, choose_user_for_time_notification)

@text_only_handler
def choose_user_for_time_notification(message):
    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return

    try:
        index = int(message.text) - 1
        users_data = load_users()
        user_list = list(users_data.keys())
        if 0 <= index < len(user_list):
            user_id = user_list[index]
            bot.send_message(message.chat.id, "Введите тему оповещения:")
            bot.register_next_step_handler(message, set_theme_for_time_notification, user_id)
        else:
            bot.send_message(message.chat.id, "Неверный номер пользователя! Попробуйте снова")
            bot.register_next_step_handler(message, choose_user_for_time_notification)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер пользователя!")
        bot.register_next_step_handler(message, choose_user_for_time_notification)

@text_only_handler
def set_theme_for_time_notification(message, user_id):
    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    individual_theme = message.text
    bot.send_message(message.chat.id, "Введите текст оповещения или отправьте мультимедийный файл:")
    bot.register_next_step_handler(message, set_time_for_time_notification, user_id, individual_theme)

def set_time_for_time_notification(message, user_id, individual_theme):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    notification_text = message.text or message.caption
    content_type = message.content_type
    file_id = None
    caption = message.caption

    if content_type == 'photo':
        file_id = message.photo[-1].file_id
    elif content_type == 'video':
        file_id = message.video.file_id
    elif content_type == 'document':
        file_id = message.document.file_id
    elif content_type == 'animation':
        file_id = message.animation.file_id
    elif content_type == 'sticker':
        file_id = message.sticker.file_id
    elif content_type == 'audio':
        file_id = message.audio.file_id
    elif content_type == 'voice':
        file_id = message.voice.file_id
    elif content_type == 'video_note':
        file_id = message.video_note.file_id

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите дату оповещения в формате ДД.ММ.ГГГГ:", reply_markup=markup)
    bot.register_next_step_handler(message, process_time_notification_date, user_id, individual_theme, notification_text, content_type, file_id, caption)

@text_only_handler
def process_time_notification_date(message, user_id, individual_theme, notification_text, content_type, file_id, caption):
    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    date_str = message.text
    if not validate_date_format(date_str):
        bot.send_message(message.chat.id, "Неверный формат даты! Введите дату в формате ДД.ММ.ГГГГ")
        bot.register_next_step_handler(message, process_time_notification_date, user_id, individual_theme, notification_text, content_type, file_id, caption)
        return

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите время оповещения в формате ЧЧ:ММ:", reply_markup=markup)
    bot.register_next_step_handler(message, process_time_notification_time, user_id, individual_theme, notification_text, date_str, content_type, file_id, caption)

@text_only_handler
def process_time_notification_time(message, user_id, individual_theme, notification_text, date_str, content_type, file_id, caption):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    time_str = message.text
    if not validate_time_format(time_str):
        bot.send_message(message.chat.id, "Неверный формат времени! Введите время в формате ЧЧ:ММ")
        bot.register_next_step_handler(message, process_time_notification_time, user_id, individual_theme, notification_text, date_str, content_type, file_id, caption)
        return

    try:
        notification_time = datetime.strptime(f"{date_str}, {time_str}", "%d.%m.%Y, %H:%M")
        if notification_time < datetime.now():
            bot.send_message(message.chat.id, "Введенное время уже прошло! Пожалуйста, введите корректное время")
            bot.register_next_step_handler(message, process_time_notification_time, user_id, individual_theme, notification_text, date_str, content_type, file_id, caption)
            return
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат времени! Введите время в формате ЧЧ:ММ")
        bot.register_next_step_handler(message, process_time_notification_time, user_id, individual_theme, notification_text, date_str, content_type, file_id, caption)
        return

    notification_id = str(len(alerts['notifications']) + 1)
    alerts['notifications'][notification_id] = {
        'theme': individual_theme,
        'text': notification_text if content_type == 'text' else None,
        'time': notification_time,
        'status': 'active',
        'category': 'time',
        'user_id': user_id,
        'files': [
            {
                'type': content_type,
                'file_id': file_id,
                'caption': caption if content_type != 'text' else None
            }
        ],
        'content_type': content_type
    }
    save_database()

    users_data = load_users()
    username = escape_markdown(users_data.get(user_id, {}).get('username', 'неизвестный'))

    theme = individual_theme.lower()
    formatted_time = notification_time.strftime("%d.%m.%Y в %H:%M")
    bot.send_message(message.chat.id, f"✅ Оповещение *{theme.lower()}* запланировано на {formatted_time} для пользователя {username} - `{user_id}`!", parse_mode="Markdown")
    show_notifications_menu(message)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (всем) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Всем' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_broadcast_notifications(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Всем'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Отправить сообщение')
    markup.add('Отправленные', 'Удалить отправленные')
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Управление оповещения для всех:", reply_markup=markup)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (отправить сообщение) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Отправить сообщение' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_message_to_all(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Отправить сообщение'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите тему для оповещения:", reply_markup=markup)
    bot.register_next_step_handler(message, set_theme_for_broadcast)

@text_only_handler
def set_theme_for_broadcast(message):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    broadcast_theme = message.text
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите текст оповещения или отправьте мультимедийный файл:", reply_markup=markup)
    bot.register_next_step_handler(message, process_broadcast_message, broadcast_theme)

def process_broadcast_message(message, broadcast_theme):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    broadcast_text = message.text or message.caption
    content_type = message.content_type
    file_id = None
    caption = message.caption

    if content_type == 'photo':
        file_id = message.photo[-1].file_id
    elif content_type == 'video':
        file_id = message.video.file_id
    elif content_type == 'document':
        file_id = message.document.file_id
    elif content_type == 'animation':
        file_id = message.animation.file_id
    elif content_type == 'sticker':
        file_id = message.sticker.file_id
    elif content_type == 'audio':
        file_id = message.audio.file_id
    elif content_type == 'voice':
        file_id = message.voice.file_id
    elif content_type == 'video_note':
        file_id = message.video_note.file_id

    users = load_users()
    user_ids = []

    for user_id in users.keys():
        if user_id in blocked_users:
            continue

        try:
            if content_type == 'text':
                bot.send_message(user_id, broadcast_text)
            elif content_type == 'photo':
                bot.send_photo(user_id, file_id, caption=caption)
            elif content_type == 'video':
                bot.send_video(user_id, file_id, caption=caption)
            elif content_type == 'document':
                bot.send_document(user_id, file_id, caption=caption)
            elif content_type == 'animation':
                bot.send_animation(user_id, file_id, caption=caption)
            elif content_type == 'sticker':
                bot.send_sticker(user_id, file_id)
            elif content_type == 'audio':
                bot.send_audio(user_id, file_id, caption=caption)
            elif content_type == 'voice':
                bot.send_voice(user_id, file_id, caption=caption)
            elif content_type == 'video_note':
                bot.send_video_note(user_id, file_id)

            user_ids.append(user_id)

        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                pass
                if user_id not in blocked_users:
                    blocked_users.append(user_id)
                    save_blocked_users(blocked_users)
            else:
                raise e

    notification_id = str(len(alerts['sent_messages']) + 1)
    alerts['sent_messages'][notification_id] = {
        'theme': broadcast_theme,
        'text': broadcast_text if content_type == 'text' else None,
        'time': datetime.now().strftime("%d.%m.%Y в %H:%M"),
        'status': 'sent',
        'category': 'all',
        'user_ids': user_ids,
        'files': [
            {
                'type': content_type,
                'file_id': file_id,
                'caption': caption if content_type != 'text' else None
            }
        ]
    }
    save_database()
    bot.send_message(message.chat.id, "✅ Оповещение отправлено всем пользователям!")
    show_notifications_menu(message)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (отправленные) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Отправленные' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_sent_messages(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Отправленные'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    if alerts['sent_messages']:
        sent_messages_list = [
            f"⭐ *№{i + 1}* ⭐\n\n📝 *Тема*: {msg['theme'].lower()}\n👤 *Пользователи*: {', '.join(msg.get('user_ids', []))}\n📅 *Дата*: {msg['time'].strftime('%d.%m.%Y')}\n🕒 *Время*: {msg['time'].strftime('%H:%M')}\n"
            for i, msg in enumerate(alerts['sent_messages'].values()) if msg['category'] == 'all'
        ]

        header = "*Список отправленных оповещений:*\n\n"
        max_length = 4096
        message_text = header

        for sent_message in sent_messages_list:
            if len(message_text) + len(sent_message) > max_length:
                bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                message_text = sent_message
            else:
                message_text += sent_message + "\n\n"

        if message_text:
            bot.send_message(message.chat.id, message_text, parse_mode="Markdown")

        markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("Вернуться в оповещения", "Вернуться в общение")
        markup.add('В меню админ-панели')

        bot.send_message(message.chat.id, "Введите номер оповещения для просмотра:", reply_markup=markup)
        bot.register_next_step_handler(message, show_sent_message_details)
    else:
        bot.send_message(message.chat.id, "❌ Нет отправленных оповещений для просмотра!")

@text_only_handler
def show_sent_message_details(message):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        indices = [int(index.strip()) - 1 for index in message.text.split(',')]
        sent_messages = list(alerts['sent_messages'].values())
        valid_indices = [index for index in indices if 0 <= index < len(sent_messages)]

        if len(valid_indices) != len(indices):
            invalid_numbers = [str(index + 1) for index in indices if index not in valid_indices]
            bot.send_message(message.chat.id, f"❌ Неверные номера оповещений: `{','.join(invalid_numbers)}`! Они будут пропущены...", parse_mode="Markdown")
            if len(valid_indices) == 0:
                bot.register_next_step_handler(message, show_sent_message_details)
                return

        for index in valid_indices:
            sent_message = sent_messages[index]
            theme = sent_message['theme'].lower() if sent_message['theme'] else 'без темы'
            content_type = sent_message.get('content_type', 'текст')
            status_text = 'отправлено'

            formatted_time = sent_message['time'].strftime("%d.%m.%Y в %H:%M")

            message_text = sent_message.get('text', '')

            sent_message_details = (
                f"*Основная информация*:\n\n"
                f"📝 *Тема*: {theme}\n"
                f"📁 *Тип контента*: {content_type}\n"
                f"📅 *Дата*: {formatted_time}\n"
                f"🔄 *Статус*: {status_text}\n"
            )

            if message_text:
                sent_message_details += f"\n*Текст сообщения*:\n\n{message_text}\n"

            bot.send_message(message.chat.id, sent_message_details, parse_mode="Markdown")

            for file in sent_message.get('files', []):
                if file['type'] == 'photo':
                    bot.send_photo(message.chat.id, file['file_id'], caption=file.get('caption'))
                elif file['type'] == 'video':
                    bot.send_video(message.chat.id, file['file_id'], caption=file.get('caption'))
                elif file['type'] == 'document':
                    bot.send_document(message.chat.id, file['file_id'], caption=file.get('caption'))
                elif file['type'] == 'animation':
                    bot.send_animation(message.chat.id, file['file_id'], caption=file.get('caption'))
                elif file['type'] == 'sticker':
                    bot.send_sticker(message.chat.id, file['file_id'])
                elif file['type'] == 'audio':
                    bot.send_audio(message.chat.id, file['file_id'], caption=file.get('caption'))
                elif file['type'] == 'voice':
                    bot.send_voice(message.chat.id, file['file_id'], caption=file.get('caption'))
                elif file['type'] == 'video_note':
                    bot.send_video_note(message.chat.id, file['file_id'])

        show_notifications_menu(message)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректные номера оповещений через запятую!")
        bot.register_next_step_handler(message, show_sent_message_details)
    except IndexError:
        bot.send_message(message.chat.id, "Неверные номера оповещений! Попробуйте снова")
        bot.register_next_step_handler(message, show_sent_message_details)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (удалить отправленные) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Удалить отправленные' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_sent_messages(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Удалить отправленные'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    if alerts['sent_messages']:
        sent_messages_list = [
            f"⭐ *№{i + 1}* ⭐\n\n📝 *Тема*: {msg['theme'].lower()}\n👤 *Пользователи*: {', '.join(msg.get('user_ids', []))}\n📅 *Дата*: {msg['time'].strftime('%d.%m.%Y')}\n🕒 *Время*: {msg['time'].strftime('%H:%M')}\n"
            for i, msg in enumerate(alerts['sent_messages'].values()) if msg['category'] == 'all'
        ]

        header = "*Список отправленных оповещений:*\n\n"
        max_length = 4096
        message_text = header

        for sent_message in sent_messages_list:
            if len(message_text) + len(sent_message) > max_length:
                bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                message_text = sent_message
            else:
                message_text += sent_message + "\n\n"

        if message_text:
            bot.send_message(message.chat.id, message_text, parse_mode="Markdown")

        markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("Вернуться в оповещения", "Вернуться в общение")
        markup.add('В меню админ-панели')

        bot.send_message(message.chat.id, "Введите номер оповещения для удаления:", reply_markup=markup)
        bot.register_next_step_handler(message, process_delete_sent_message)
    else:
        bot.send_message(message.chat.id, "❌ Нет отправленных оповещений для удаления!")

@text_only_handler
def process_delete_sent_message(message):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        indices = [int(index.strip()) - 1 for index in message.text.split(',')]
        sent_messages = list(alerts['sent_messages'].values())
        valid_indices = [index for index in indices if 0 <= index < len(sent_messages)]

        if len(valid_indices) != len(indices):
            invalid_numbers = [str(index + 1) for index in indices if index not in valid_indices]
            bot.send_message(message.chat.id, f"❌ Неверные номера оповещений: `{','.join(invalid_numbers)}`! Они будут пропущены...", parse_mode="Markdown")
            if len(valid_indices) == 0:
                bot.register_next_step_handler(message, process_delete_sent_message)
                return

        deleted_messages = []
        for index in sorted(valid_indices, reverse=True):
            notification_id = list(alerts['sent_messages'].keys())[index]
            deleted_message = alerts['sent_messages'].pop(notification_id)
            deleted_messages.append(deleted_message)

        new_sent_messages = {}
        for i, (key, value) in enumerate(alerts['sent_messages'].items(), start=1):
            new_sent_messages[str(i)] = value
        alerts['sent_messages'] = new_sent_messages

        save_database()

        deleted_themes = ", ".join([f"*{msg['theme'].lower()}*" for msg in deleted_messages])
        bot.send_message(message.chat.id, f"✅ Оповещения (всем) по темам *{deleted_themes}* были удалены!", parse_mode="Markdown")

        show_notifications_menu(message)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректные номера оповещений через запятую!")
        bot.register_next_step_handler(message, process_delete_sent_message)
    except IndexError:
        bot.send_message(message.chat.id, "Неверные номера оповещений! Попробуйте снова")
        bot.register_next_step_handler(message, process_delete_sent_message)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (отдельно) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Отдельно' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_individual_notifications(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Отдельно'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Отправить отдельно')
    markup.add('Посмотреть отдельно', 'Удалить отдельно')
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Управление оповещениями для отдельных пользователей:", reply_markup=markup)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (отправить отдельно) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Отправить отдельно' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_message_to_individual(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Отправить отдельно'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    list_users(message)

def list_users(message):
    users_data = load_users()
    user_list = []
    for user_id, data in users_data.items():
        username = escape_markdown(data['username'])
        status = " - *разблокирован* ✅" if not data.get('blocked', False) else " - *заблокирован* 🚫"
        user_list.append(f"№{len(user_list) + 1}. {username} - `{user_id}`{status}")

    response_message = "📋 Список *всех* пользователей:\n\n" + "\n\n".join(user_list)
    if len(response_message) > 4096:
        bot.send_message(message.chat.id, "📜 Список пользователей слишком большой для отправки в одном сообщении!")
    else:
        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер пользователя для отправки сообщения:", reply_markup=markup)
    bot.register_next_step_handler(message, choose_user_for_send)

@text_only_handler
def choose_user_for_send(message):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        index = int(message.text) - 1
        users_data = load_users()
        user_list = list(users_data.keys())
        if 0 <= index < len(user_list):
            user_id = user_list[index]
            send_individual_message(message, user_id)
        else:
            bot.send_message(message.chat.id, "Неверный номер пользователя! Попробуйте снова")
            bot.register_next_step_handler(message, choose_user_for_send)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер пользователя!")
        bot.register_next_step_handler(message, choose_user_for_send)

def send_individual_message(message, user_id):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    bot.send_message(message.chat.id, "Введите тему для оповещения:")
    bot.register_next_step_handler(message, set_theme_for_individual_broadcast, user_id)

@text_only_handler
def set_theme_for_individual_broadcast(message, user_id):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    broadcast_theme = message.text
    bot.send_message(message.chat.id, "Введите текст оповещения или отправьте мультимедийный файл:")
    bot.register_next_step_handler(message, process_individual_broadcast_message, user_id, broadcast_theme)

def process_individual_broadcast_message(message, user_id, broadcast_theme):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    broadcast_text = message.text or message.caption
    content_type = message.content_type
    file_id = None
    caption = message.caption

    if content_type == 'photo':
        file_id = message.photo[-1].file_id
    elif content_type == 'video':
        file_id = message.video.file_id
    elif content_type == 'document':
        file_id = message.document.file_id
    elif content_type == 'animation':
        file_id = message.animation.file_id
    elif content_type == 'sticker':
        file_id = message.sticker.file_id
    elif content_type == 'audio':
        file_id = message.audio.file_id
    elif content_type == 'voice':
        file_id = message.voice.file_id
    elif content_type == 'video_note':
        file_id = message.video_note.file_id

    try:
        if content_type == 'text':
            bot.send_message(user_id, broadcast_text)
        elif content_type == 'photo':
            bot.send_photo(user_id, file_id, caption=caption)
        elif content_type == 'video':
            bot.send_video(user_id, file_id, caption=caption)
        elif content_type == 'document':
            bot.send_document(user_id, file_id, caption=caption)
        elif content_type == 'animation':
            bot.send_animation(user_id, file_id, caption=caption)
        elif content_type == 'sticker':
            bot.send_sticker(user_id, file_id)
        elif content_type == 'audio':
            bot.send_audio(user_id, file_id, caption=caption)
        elif content_type == 'voice':
            bot.send_voice(user_id, file_id, caption=caption)
        elif content_type == 'video_note':
            bot.send_video_note(user_id, file_id)

    except ApiTelegramException as e:
        if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
            pass
            if user_id not in blocked_users:
                blocked_users.append(user_id)
                save_blocked_users(blocked_users)
        else:
            raise e

    notification_id = str(len(alerts['sent_messages']) + 1)
    alerts['sent_messages'][notification_id] = {
        'theme': broadcast_theme,
        'text': broadcast_text if content_type == 'text' else None,
        'time': datetime.now().strftime("%d.%m.%Y в %H:%M"),
        'status': 'sent',
        'category': 'individual',
        'user_id': [user_id],
        'files': [
            {
                'type': content_type,
                'file_id': file_id,
                'caption': caption if content_type != 'text' else None
            }
        ]
    }
    save_database()

    users_data = load_users()
    username = escape_markdown(users_data.get(user_id, {}).get('username', 'неизвестный'))

    bot.send_message(message.chat.id, f"✅ Оповещение отправлено пользователю {username} - `{user_id}`!", parse_mode="Markdown")
    show_notifications_menu(message)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (посмотреть отдельно) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Посмотреть отдельно' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_individual_messages(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Посмотреть отдельно'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    users_data = load_users()
    user_list = []
    for user_id, data in users_data.items():
        username = escape_markdown(data['username'])
        status = " - *разблокирован* ✅" if not data.get('blocked', False) else " - *заблокирован* 🚫"
        user_list.append(f"№{len(user_list) + 1}. {username} - `{user_id}`{status}")

    response_message = "📋 Список *всех* пользователей:\n\n" + "\n\n".join(user_list)
    if len(response_message) > 4096:
        bot.send_message(message.chat.id, "📜 Список пользователей слишком большой для отправки в одном сообщении!")
    else:
        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер пользователя для просмотра:", reply_markup=markup)
    bot.register_next_step_handler(message, choose_user_for_view)

@text_only_handler
def choose_user_for_view(message):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        indices = [int(index.strip()) - 1 for index in message.text.split(',')]
        users_data = load_users()
        user_list = list(users_data.keys())
        valid_indices = [index for index in indices if 0 <= index < len(user_list)]

        if len(valid_indices) != len(indices):
            bot.send_message(message.chat.id, "Неверный номер пользователя! Попробуйте снова")
            bot.register_next_step_handler(message, choose_user_for_view)
            return

        for index in valid_indices:
            user_id = user_list[index]
            view_individual_messages_for_user(message, user_id)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер пользователя!")
        bot.register_next_step_handler(message, choose_user_for_view)

def view_individual_messages_for_user(message, user_id):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    sent_messages = [msg for msg in alerts['sent_messages'].values() if msg['category'] == 'individual' and user_id in msg.get('user_id', [])]
    if sent_messages:
        sent_messages_list = [
            f"⭐ №{i + 1} ⭐\n\n📝 *Тема*: {msg['theme'].lower()}\n👤 *Пользователи*: {', '.join(msg.get('user_id', []))}\n📅 *Дата*: {msg['time'].strftime('%d.%m.%Y')}\n🕒 *Время*: {msg['time'].strftime('%H:%M')}\n"
            for i, msg in enumerate(sent_messages)
        ]

        header = "*Список отправленных оповещений:*\n\n"
        max_length = 4096
        message_text = header

        for sent_message in sent_messages_list:
            if len(message_text) + len(sent_message) > max_length:
                bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                message_text = sent_message
            else:
                message_text += sent_message + "\n\n"

        if message_text:
            bot.send_message(message.chat.id, message_text, parse_mode="Markdown")

        markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("Вернуться в оповещения", "Вернуться в общение")
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Введите номер оповещения для просмотра:", reply_markup=markup)
        bot.register_next_step_handler(message, show_individual_message_details, user_id)
    else:
        bot.send_message(message.chat.id, "❌ Нет отправленных оповещений для простмотра по этому пользователю!")
        show_notifications_menu(message)

@text_only_handler
def show_individual_message_details(message, user_id):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        indices = [int(index.strip()) - 1 for index in message.text.split(',')]
        sent_messages = [msg for msg in alerts['sent_messages'].values() if msg['category'] == 'individual' and user_id in msg.get('user_id', [])]
        valid_indices = [index for index in indices if 0 <= index < len(sent_messages)]

        if len(valid_indices) != len(indices):
            invalid_numbers = [str(index + 1) for index in indices if index not in valid_indices]
            bot.send_message(message.chat.id, f"❌ Неверные номера оповещений: `{','.join(invalid_numbers)}`! Они будут пропущены...", parse_mode="Markdown")
            if len(valid_indices) == 0:
                bot.register_next_step_handler(message, show_individual_message_details, user_id)
                return

        for index in valid_indices:
            sent_message = sent_messages[index]
            theme = sent_message['theme'].lower() if sent_message['theme'] else 'без темы'
            content_type = sent_message.get('content_type', 'текст')
            status_text = 'отправлено' if sent_message.get('status') == 'sent' else 'активно'

            formatted_time = sent_message['time'].strftime("%d.%m.%Y в %H:%M")

            message_text = sent_message.get('text', '')

            sent_message_details = (
                f"*Основная информация*:\n\n"
                f"📝 *Тема*: {theme}\n"
                f"📁 *Тип контента*: {content_type}\n"
                f"📅 *Дата*: {formatted_time}\n"
                f"🔄 *Статус*: {status_text}\n"
            )

            if message_text:
                sent_message_details += f"\n*Текст сообщения*:\n\n{message_text}\n"

            bot.send_message(message.chat.id, sent_message_details, parse_mode="Markdown")

            for file in sent_message.get('files', []):
                if file['type'] == 'photo':
                    bot.send_photo(message.chat.id, file['file_id'], caption=file.get('caption'))
                elif file['type'] == 'video':
                    bot.send_video(message.chat.id, file['file_id'], caption=file.get('caption'))
                elif file['type'] == 'document':
                    bot.send_document(message.chat.id, file['file_id'], caption=file.get('caption'))
                elif file['type'] == 'animation':
                    bot.send_animation(message.chat.id, file['file_id'], caption=file.get('caption'))
                elif file['type'] == 'sticker':
                    bot.send_sticker(message.chat.id, file['file_id'])
                elif file['type'] == 'audio':
                    bot.send_audio(message.chat.id, file['file_id'], caption=file.get('caption'))
                elif file['type'] == 'voice':
                    bot.send_voice(message.chat.id, file['file_id'], caption=file.get('caption'))
                elif file['type'] == 'video_note':
                    bot.send_video_note(message.chat.id, file['file_id'])

        show_notifications_menu(message)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер оповещения!")
        bot.register_next_step_handler(message, show_individual_message_details, user_id)

# -------------------------------------------------- ОБЩЕНИЕ_ОПОВЕЩЕНИЯ (удалить отдельно) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Удалить отдельно' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_individual_messages(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Удалить отдельно'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    users_data = load_users()
    user_list = []
    for user_id, data in users_data.items():
        username = escape_markdown(data['username'])
        status = " - *разблокирован* ✅" if not data.get('blocked', False) else " - *заблокирован* 🚫"
        user_list.append(f"№{len(user_list) + 1}. {username} - `{user_id}`{status}")

    response_message = "📋 Список *всех* пользователей:\n\n" + "\n\n".join(user_list)
    if len(response_message) > 4096:
        bot.send_message(message.chat.id, "📜 Список пользователей слишком большой для отправки в одном сообщении!")
    else:
        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("Вернуться в оповещения", "Вернуться в общение")
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер пользователя для удаления:", reply_markup=markup)
    bot.register_next_step_handler(message, choose_user_for_delete)

@text_only_handler
def choose_user_for_delete(message):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        index = int(message.text) - 1
        users_data = load_users()
        user_list = list(users_data.keys())
        if 0 <= index < len(user_list):
            user_id = user_list[index]
            delete_individual_messages_for_user(message, user_id)
        else:
            bot.send_message(message.chat.id, "Неверный номер пользователя! Попробуйте снова")
            bot.register_next_step_handler(message, choose_user_for_delete)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер пользователя!")
        bot.register_next_step_handler(message, choose_user_for_delete)

def delete_individual_messages_for_user(message, user_id):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    sent_messages = [msg for msg in alerts['sent_messages'].values() if msg['category'] == 'individual' and user_id in msg.get('user_id', [])]
    if sent_messages:
        sent_messages_list = [
            f"⭐ №{i + 1} ⭐\n\n📝 *Тема*: {msg['theme'].lower()}\n👤 *Пользователи*: {', '.join(msg.get('user_id', []))}\n📅 *Дата*: {msg['time'].strftime('%d.%m.%Y')}\n🕒 *Время*: {msg['time'].strftime('%H:%M')}\n"
            for i, msg in enumerate(sent_messages)
        ]

        header = "*Список отправленных оповещений:*\n\n"
        max_length = 4096
        message_text = header

        for sent_message in sent_messages_list:
            if len(message_text) + len(sent_message) > max_length:
                bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                message_text = sent_message
            else:
                message_text += sent_message + "\n\n"

        if message_text:
            bot.send_message(message.chat.id, message_text, parse_mode="Markdown")

        bot.send_message(message.chat.id, "Введите номер оповещения для удаления:")
        bot.register_next_step_handler(message, process_delete_individual_message, user_id)
    else:
        bot.send_message(message.chat.id, "❌ Нет отправленных оповещений для удаления по этому пользователю!")
        show_notifications_menu(message)

@text_only_handler
def process_delete_individual_message(message, user_id):

    if message.text == "Вернуться в оповещения":
        show_notifications_menu(message)
        return

    if message.text == "Вернуться в общение":
        show_communication_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        indices = [int(index.strip()) - 1 for index in message.text.split(',')]
        sent_messages = [msg for msg in alerts['sent_messages'].values() if msg['category'] == 'individual' and user_id in msg.get('user_id', [])]
        valid_indices = [index for index in indices if 0 <= index < len(sent_messages)]

        if len(valid_indices) != len(indices):
            invalid_numbers = [str(index + 1) for index in indices if index not in valid_indices]
            bot.send_message(message.chat.id, f"❌ Неверные номера оповещений: `{','.join(invalid_numbers)}`! Они будут пропущены...", parse_mode="Markdown")
            if len(valid_indices) == 0:
                bot.register_next_step_handler(message, process_delete_individual_message, user_id)
                return

        deleted_messages = []
        for index in sorted(valid_indices, reverse=True):
            notification_id = list(alerts['sent_messages'].keys())[index]
            deleted_message = alerts['sent_messages'].pop(notification_id)
            deleted_messages.append(deleted_message)

        new_sent_messages = {}
        for i, (key, value) in enumerate(alerts['sent_messages'].items(), start=1):
            new_sent_messages[str(i)] = value
        alerts['sent_messages'] = new_sent_messages

        save_database()

        deleted_themes = ", ".join([f"*{msg['theme'].lower()}*" for msg in deleted_messages])
        bot.send_message(message.chat.id, f"✅ Оповещения (отдельно) по темам *{deleted_themes}* были удалены!", parse_mode="Markdown")

        show_notifications_menu(message)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер оповещения!")
        bot.register_next_step_handler(message, process_delete_individual_message, user_id)
    except IndexError:
        bot.send_message(message.chat.id, "Неверные номера оповещений! Попробуйте снова")
        bot.register_next_step_handler(message, process_delete_individual_message, user_id)