from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, ApiTelegramException, ReplyKeyboardMarkup, KeyboardButton
from core.bot_instance import bot, BASE_DIR
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from handlers.admin.communication.communication import show_communication_menu, return_to_communication
from handlers.user.others.others_chat_with_admin import check_and_create_file, DB_PATH
from decorators.blocked_user import load_blocked_users, save_blocked_users
from handlers.admin.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha,
)

# -------------------------------------------------- ОБЩЕНИЕ_ДИАЛОГИ ---------------------------------------------------

ADMIN_SESSIONS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')
USER_DB_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'users.json')
CHAT_HISTORY_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'chats', 'chat_history.json')

dialog_states = {}

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

def load_chat_history():
    if os.path.exists(CHAT_HISTORY_PATH):
        with open(CHAT_HISTORY_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

def save_dialog_states():
    path = os.path.join(BASE_DIR, 'data', 'admin', 'chats', 'dialog_states.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(dialog_states, file, ensure_ascii=False, indent=4)

@bot.message_handler(func=lambda message: message.text == 'Диалоги' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_dialogs_menu(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Диалоги'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.chat.id in dialog_states:
        dialog_states.pop(message.chat.id, None)
        save_dialog_states()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Просмотр диалогов", "Удалить диалоги")
    markup.add("Вернуться в общение")
    markup.add("В меню админ-панели")

    bot.send_message(message.chat.id, "Выберите действие для диалогов:", reply_markup=markup)

# -------------------------------------------------- ОБЩЕНИЕ_ДИАЛОГИ (просмотр диалогов) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Просмотр диалогов' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_user_dialogs(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Просмотр диалогов'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в общение":
        return_to_communication(message)
        return

    chat_history = load_chat_history()
    users = load_users()

    user_ids = [user_id.split('_')[1] for user_id in chat_history.keys()]
    user_ids = list(set(user_ids))

    user_list = "\n\n".join(
        f"№{i + 1}. {escape_markdown(users.get(user_id, {}).get('username', 'N/A'))} - `{user_id}`"
        for i, user_id in enumerate(user_ids)
    )

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton("Вернуться в общение"))
    keyboard.add(KeyboardButton("В меню админ-панели"))

    try:
        bot.send_message(
            message.chat.id,
            f"*Список пользователей для просмотра диалогов:*\n\n{user_list}\n\nВведите номер пользователя:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except ApiTelegramException as e:
        if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
            pass
            blocked_users = load_blocked_users()
            if message.chat.id not in blocked_users:
                blocked_users.append(message.chat.id)
                save_blocked_users(blocked_users)
        else:
            raise e

    dialog_states[message.chat.id] = {"state": "select_user", "user_ids": user_ids}
    save_dialog_states()

@bot.message_handler(func=lambda message: message.chat.id in dialog_states and dialog_states[message.chat.id].get("state") == "select_user")
@check_user_blocked
def handle_user_selection(message):
    if message.text == "В меню админ-панели":
        dialog_states.pop(message.chat.id, None)
        save_dialog_states()
        return show_admin_panel(message)

    if message.text == "Вернуться в общение":
        return_to_communication(message)
        return

    if message.text == "Удалить все диалоги":
        dialog_states.pop(message.chat.id, None)
        save_dialog_states()
        return delete_all_dialogs(message)

    if message.text == "Удалить диалоги":
        dialog_states.pop(message.chat.id, None)
        save_dialog_states()
        show_delete_dialogs_menu(message)
        return

    user_ids = dialog_states[message.chat.id]["user_ids"]
    users = load_users()

    try:
        selected_index = int(message.text) - 1
        if selected_index < 0 or selected_index >= len(user_ids):
            raise IndexError

        selected_user_id = user_ids[selected_index]
        selected_username = users.get(selected_user_id, {}).get("username", "N/A")

        chat_key = f"{message.chat.id}_{selected_user_id}"
        chat_history = load_chat_history().get(chat_key, [])

        if not chat_history:
            bot.send_message(message.chat.id, "❌ История переписки с этим пользователем пуста! Пожалуйста, выберите другого пользователя или вернитесь в меню.", parse_mode="Markdown")
            return

        dialog_list = []
        for i, dialog in enumerate(chat_history):
            if dialog:
                timestamps = [entry['timestamp'] for entry in dialog]
                start_time = timestamps[0].split(" в ")[1]
                end_time = timestamps[-1].split(" в ")[1]
                date = timestamps[0].split(" в ")[0]
                dialog_list.append(f"№{i + 1}. *{date}* (с {start_time} до {end_time})")
            else:
                dialog_list.append(f"№{i + 1}. (Пустой диалог)")

        dialog_text = "\n".join(dialog_list)
        try:
            bot.send_message(
                message.chat.id,
                f"Выберите диалог с пользователем {escape_markdown(selected_username)} - `{selected_user_id}`:\n\n{dialog_text}\n\nВведите номер диалога:",
                parse_mode="Markdown"
            )
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                blocked_users = load_blocked_users()
                if message.chat.id not in blocked_users:
                    blocked_users.append(message.chat.id)
                    save_blocked_users(blocked_users)
            else:
                raise e

        dialog_states[message.chat.id] = {
            "state": "select_dialog",
            "selected_user_id": selected_user_id,
            "chat_history": chat_history,
        }
        save_dialog_states()

    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Неверный ввод! Пожалуйста, введите номер пользователя")

@bot.message_handler(func=lambda message: message.chat.id in dialog_states and dialog_states[message.chat.id].get("state") == "select_dialog")
@check_user_blocked
def handle_dialog_selection(message):
    selected_user_id = dialog_states[message.chat.id]["selected_user_id"]
    chat_key = f"{message.chat.id}_{selected_user_id}"
    chat_history = load_chat_history().get(chat_key, [])

    if not chat_history:
        bot.send_message(message.chat.id, "❌ История переписки с этим пользователем пуста!", parse_mode="Markdown")
        show_communication_menu(message)
        return

    if message.text == "Вернуться в общение":
        return_to_communication(message)
        return

    if message.text == "Удалить все диалоги":
        dialog_states.pop(message.chat.id, None)
        save_dialog_states()
        return delete_all_dialogs(message)

    try:
        selected_dialog_index = int(message.text) - 1
        if selected_dialog_index < 0 or selected_dialog_index >= len(chat_history):
            raise IndexError

        selected_dialog = chat_history[selected_dialog_index]

        if not selected_dialog:
            bot.send_message(message.chat.id, "❌ Выбранный диалог пуст!")
            show_communication_menu(message)
            return

        for entry in selected_dialog:
            timestamp = entry['timestamp']
            sender = entry['type']
            content = entry['content']
            caption = entry.get('caption')

            if caption is not None:
                caption = caption.lower()

            if content.startswith("photo:"):
                photo_id = content.replace("photo:", "").strip()
                message_text = f"👤 *{sender.upper()}* - [Фотография]"
                if caption:
                    message_text += f"\n✍ Подпись - {caption}"
                message_text += f"\n📅 *Дата и время*: _{timestamp}_"
                try:
                    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                    bot.send_photo(message.chat.id, photo_id)
                except ApiTelegramException as e:
                    if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                        pass
                        blocked_users = load_blocked_users()
                        if message.chat.id not in blocked_users:
                            blocked_users.append(message.chat.id)
                            save_blocked_users(blocked_users)
                    else:
                        raise e

            elif content.startswith("sticker:"):
                sticker_id = content.replace("sticker:", "").strip()
                message_text = f"👤 *{sender.upper()}* - [Стикер]"
                message_text += f"\n📅 *Дата и время*: _{timestamp}_"
                try:
                    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                    bot.send_sticker(message.chat.id, sticker_id)
                except ApiTelegramException as e:
                    if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                        pass
                        blocked_users = load_blocked_users()
                        if message.chat.id not in blocked_users:
                            blocked_users.append(message.chat.id)
                            save_blocked_users(blocked_users)
                    else:
                        raise e

            elif content.startswith("voice:"):
                voice_id = content.replace("voice:", "").strip()
                message_text = f"👤 *{sender.upper()}* - [Голосовое сообщение]"
                message_text += f"\n📅 *Дата и время*: _{timestamp}_"
                try:
                    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                    bot.send_voice(message.chat.id, voice_id)
                except ApiTelegramException as e:
                    if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                        pass
                        blocked_users = load_blocked_users()
                        if message.chat.id not in blocked_users:
                            blocked_users.append(message.chat.id)
                            save_blocked_users(blocked_users)
                    else:
                        raise e

            elif content.startswith("video:"):
                video_id = content.replace("video:", "").strip()
                message_text = f"👤 *{sender.upper()}* - [Видео]"
                if caption:
                    message_text += f"\n✍ Подпись - {caption}"
                message_text += f"\n📅 *Дата и время*: _{timestamp}_"
                try:
                    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                    bot.send_video(message.chat.id, video_id)
                except ApiTelegramException as e:
                    if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                        pass
                        blocked_users = load_blocked_users()
                        if message.chat.id not in blocked_users:
                            blocked_users.append(message.chat.id)
                            save_blocked_users(blocked_users)
                    else:
                        raise e

            elif content.startswith("document:"):
                document_id = content.replace("document:", "").strip()
                message_text = f"👤 *{sender.upper()}* - [Документ]"
                if caption:
                    message_text += f"\n✍ Подпись - {caption}"
                message_text += f"\n📅 *Дата и время*: _{timestamp}_"
                try:
                    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                    bot.send_document(message.chat.id, document_id)
                except ApiTelegramException as e:
                    if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                        pass
                        blocked_users = load_blocked_users()
                        if message.chat.id not in blocked_users:
                            blocked_users.append(message.chat.id)
                            save_blocked_users(blocked_users)
                    else:
                        raise e

            elif content.startswith("animation:"):
                animation_id = content.replace("animation:", "").strip()
                message_text = f"👤 *{sender.upper()}* - [Анимация]"
                if caption:
                    message_text += f"\n✍ Подпись - {escape_markdown(caption)}"
                message_text += f"\n📅 *Дата и время*: _{timestamp}_"
                try:
                    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                    bot.send_animation(message.chat.id, animation_id)
                except ApiTelegramException as e:
                    if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                        pass
                        blocked_users = load_blocked_users()
                        if message.chat.id not in blocked_users:
                            blocked_users.append(message.chat.id)
                            save_blocked_users(blocked_users)
                    else:
                        raise e

            elif content.startswith("audio:"):
                audio_id = content.replace("audio:", "").strip()
                message_text = f"👤 *{sender.upper()}* - [Аудио]"
                if caption:
                    message_text += f"\n✍ Подпись - {caption}"
                message_text += f"\n📅 *Дата и время*: _{timestamp}_"
                try:
                    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                    bot.send_audio(message.chat.id, audio_id)
                except ApiTelegramException as e:
                    if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                        pass
                        blocked_users = load_blocked_users()
                        if message.chat.id not in blocked_users:
                            blocked_users.append(message.chat.id)
                            save_blocked_users(blocked_users)
                    else:
                        raise e

            elif content.startswith("location:"):
                location_data = content.replace("location:", "").strip()
                lat, lon = map(float, location_data.split(","))
                message_text = f"👤 *{sender.upper()}* - [Локация]"
                message_text += f"\n📅 *Дата и время*: _{timestamp}_"
                try:
                    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                    bot.send_location(message.chat.id, latitude=lat, longitude=lon)
                except ApiTelegramException as e:
                    if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                        pass
                        blocked_users = load_blocked_users()
                        if message.chat.id not in blocked_users:
                            blocked_users.append(message.chat.id)
                            save_blocked_users(blocked_users)
                    else:
                        raise e

            elif content.startswith("contact:"):
                contact_data = content.replace("contact:", "").strip()
                phone, first_name, last_name = contact_data.split(",", maxsplit=2)
                message_text = f"👤 *{sender.upper()}* - [Контакт]"
                message_text += f"\n📅 *Дата и время*: _{timestamp}_"
                try:
                    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                    bot.send_contact(message.chat.id, phone_number=phone, first_name=first_name, last_name=last_name)
                except ApiTelegramException as e:
                    if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                        pass
                        blocked_users = load_blocked_users()
                        if message.chat.id not in blocked_users:
                            blocked_users.append(message.chat.id)
                            save_blocked_users(blocked_users)
                    else:
                        raise e

            elif content.startswith("gif:"):
                gif_id = content.replace("gif:", "").strip()
                message_text = f"👤 *{sender.upper()}* - [GIF]"
                if caption:
                    message_text += f"\n✍ Подпись - {caption}"
                message_text += f"\n📅 *Дата и время*: _{timestamp}_"
                try:
                    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                    bot.send_document(message.chat.id, gif_id)
                except ApiTelegramException as e:
                    if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                        pass
                        blocked_users = load_blocked_users()
                        if message.chat.id not in blocked_users:
                            blocked_users.append(message.chat.id)
                            save_blocked_users(blocked_users)
                    else:
                        raise e

            else:
                message_text = f"👤 *{sender.upper()}* - [Текст]\n📝 Текст - {content}\n📅 *Дата и время*: _{timestamp}_"
                try:
                    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
                except ApiTelegramException as e:
                    if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                        pass
                        blocked_users = load_blocked_users()
                        if message.chat.id not in blocked_users:
                            blocked_users.append(message.chat.id)
                            save_blocked_users(blocked_users)
                    else:
                        raise e

        del dialog_states[message.chat.id]
        save_dialog_states()

        show_communication_menu(message)

    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Неверный ввод! Пожалуйста, введите номер диалога")

# -------------------------------------------------- ОБЩЕНИЕ_ДИАЛОГИ (удалить диалоги) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Удалить диалоги' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_delete_dialogs_menu(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Удалить диалоги'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    # Очистим состояние, чтобы перейти в режим удаления без конфликтов
    if message.chat.id in dialog_states:
        dialog_states.pop(message.chat.id, None)
        save_dialog_states()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Удалить диалог", "Удалить все диалоги")
    markup.add("Вернуться в общение")
    markup.add("В меню админ-панели")

    try:
        bot.send_message(message.chat.id, "Выберите действие для удаления диалогов:", reply_markup=markup)
    except ApiTelegramException as e:
        if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
            pass
            blocked_users = load_blocked_users()
            if message.chat.id not in blocked_users:
                blocked_users.append(message.chat.id)
                save_blocked_users(blocked_users)
        else:
            raise e

# -------------------------------------------------- ОБЩЕНИЕ_ДИАЛОГИ (удалить диалог) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Удалить диалог' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_dialog(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Удалить диалог'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в общение":
        return_to_communication(message)
        return

    chat_history = load_chat_history()
    users = load_users()

    user_ids = [user_id.split('_')[1] for user_id in chat_history.keys()]
    user_ids = list(set(user_ids))

    user_list = "\n\n".join(
        f"№{i + 1}. {escape_markdown(users.get(user_id, {}).get('username', 'N/A'))} - `{user_id}`"
        for i, user_id in enumerate(user_ids)
    )

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton("Вернуться в общение"))
    keyboard.add(KeyboardButton("В меню админ-панели"))

    bot.send_message(
        message.chat.id,
        f"*Список пользователей для удаления диалогов:*\n\n{user_list}\n\nВведите номер пользователя:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    dialog_states[message.chat.id] = {"state": "delete_dialog_select_user", "user_ids": user_ids}
    save_dialog_states()

@bot.message_handler(func=lambda message: message.chat.id in dialog_states and dialog_states[message.chat.id].get("state") == "delete_dialog_select_user")
@check_user_blocked
def handle_delete_dialog_user_selection(message):
    if message.text == "Вернуться в общение":
        return_to_communication(message)
        return

    if message.text == "В меню админ-панели":
        dialog_states.pop(message.chat.id, None)
        save_dialog_states()
        return show_admin_panel(message)

    if message.text == "Удалить все диалоги":
        dialog_states.pop(message.chat.id, None)
        save_dialog_states()
        return delete_all_dialogs(message)

    user_ids = dialog_states[message.chat.id]["user_ids"]
    users = load_users()

    try:
        selected_index = int(message.text) - 1
        if selected_index < 0 or selected_index >= len(user_ids):
            raise IndexError

        selected_user_id = user_ids[selected_index]
        selected_username = users.get(selected_user_id, {}).get("username", "N/A")

        chat_key = f"{message.chat.id}_{selected_user_id}"
        chat_history = load_chat_history().get(chat_key, [])

        if not chat_history:
            bot.send_message(message.chat.id, "❌ История переписки с этим пользователем пуста! Пожалуйста, выберите другого пользователя или вернитесь в меню.", parse_mode="Markdown")
            return

        dialog_list = []
        for i, dialog in enumerate(chat_history):
            if dialog:
                timestamps = [entry['timestamp'] for entry in dialog]
                start_time = timestamps[0].split(" в ")[1]
                end_time = timestamps[-1].split(" в ")[1]
                date = timestamps[0].split(" в ")[0]
                dialog_list.append(f"№{i + 1}. *{date}* (с {start_time} до {end_time})")
            else:
                dialog_list.append(f"№{i + 1}. (Пустой диалог)")

        dialog_text = "\n".join(dialog_list)
        try:
            bot.send_message(
                message.chat.id,
                f"Выберите диалог для удаления с пользователем {escape_markdown(selected_username)} - `{selected_user_id}`:\n\n{dialog_text}\n\nВведите номер диалога:",
                parse_mode="Markdown"
            )
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                blocked_users = load_blocked_users()
                if message.chat.id not in blocked_users:
                    blocked_users.append(message.chat.id)
                    save_blocked_users(blocked_users)
            else:
                raise e

        dialog_states[message.chat.id] = {
            "state": "delete_dialog_select_dialog",
            "selected_user_id": selected_user_id,
            "chat_history": chat_history,
        }
        save_dialog_states()

    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Неверный ввод! Пожалуйста, введите номер пользователя")

@bot.message_handler(func=lambda message: message.chat.id in dialog_states and dialog_states[message.chat.id].get("state") == "delete_dialog_select_dialog")
@check_user_blocked
def handle_delete_dialog_selection(message):
    selected_user_id = dialog_states[message.chat.id]["selected_user_id"]
    chat_key = f"{message.chat.id}_{selected_user_id}"
    chat_history = load_chat_history().get(chat_key, [])

    if not chat_history:
        bot.send_message(message.chat.id, "❌ История переписки с этим пользователем пуста!", parse_mode="Markdown")
        return show_communication_menu(message)

    if message.text == "Вернуться в общение":
        return_to_communication(message)
        return

    try:
        selected_dialog_index = int(message.text) - 1
        if selected_dialog_index < 0 or selected_dialog_index >= len(chat_history):
            raise IndexError

        del chat_history[selected_dialog_index]

        chat_history_data = load_chat_history()
        chat_history_data[chat_key] = chat_history

        with open(CHAT_HISTORY_PATH, 'w', encoding='utf-8') as file:
            json.dump(chat_history_data, file, ensure_ascii=False, indent=4)

        bot.send_message(message.chat.id, "✅ Диалог успешно удален!", parse_mode="Markdown")
        return show_communication_menu(message)

    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Неверный ввод! Пожалуйста, введите номер диалога")

# -------------------------------------------------- ОБЩЕНИЕ_ДИАЛОГИ (удалить все диалоги) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Удалить все диалоги' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_all_dialogs(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Удалить все диалоги'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    # Сбросим возможные предыдущие состояния
    if message.chat.id in dialog_states:
        dialog_states.pop(message.chat.id, None)
        save_dialog_states()

    chat_history = load_chat_history()
    users = load_users()

    user_ids = [user_id.split('_')[1] for user_id in chat_history.keys()]
    user_ids = list(set(user_ids))

    user_list = "\n\n".join(
        f"№{i + 1}. {escape_markdown(users.get(user_id, {}).get('username', 'N/A'))} - `{user_id}`"
        for i, user_id in enumerate(user_ids)
    )

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton("Вернуться в общение"))
    keyboard.add(KeyboardButton("В меню админ-панели"))

    try:
        bot.send_message(
            message.chat.id,
            f"*Список пользователей для удаления всех диалогов:*\n\n{user_list}\n\nВведите номер пользователя:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except ApiTelegramException as e:
        if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
            pass
            blocked_users = load_blocked_users()
            if message.chat.id not in blocked_users:
                blocked_users.append(message.chat.id)
                save_blocked_users(blocked_users)
        else:
            raise e

    dialog_states[message.chat.id] = {"state": "delete_all_dialogs_select_user", "user_ids": user_ids}
    save_dialog_states()

@bot.message_handler(func=lambda message: message.chat.id in dialog_states and dialog_states[message.chat.id].get("state") == "delete_all_dialogs_select_user")
@check_user_blocked
def handle_delete_all_dialogs_user_selection(message):
    if message.text == "Вернуться в общение":
        return_to_communication(message)
        return

    if message.text == "В меню админ-панели":
        dialog_states.pop(message.chat.id, None)
        save_dialog_states()
        return show_admin_panel(message)

    user_ids = dialog_states[message.chat.id]["user_ids"]
    users = load_users()

    try:
        selected_index = int(message.text) - 1
        if selected_index < 0 or selected_index >= len(user_ids):
            raise IndexError

        selected_user_id = user_ids[selected_index]
        selected_username = users.get(selected_user_id, {}).get("username", "N/A")

        chat_key = f"{message.chat.id}_{selected_user_id}"
        chat_history = load_chat_history().get(chat_key, [])

        if not chat_history:
            bot.send_message(message.chat.id, "❌ История переписки с этим пользователем пуста! Пожалуйста, выберите другого пользователя или вернитесь в меню.", parse_mode="Markdown")
            return

        try:
            bot.send_message(
                message.chat.id,
                f"⚠️ Вы уверены, что хотите удалить все диалоги с пользователем {escape_markdown(selected_username)} - `{selected_user_id}`?\n\nВведите *да* для принятия или *нет* для отклонения:",
                parse_mode="Markdown"
            )
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                blocked_users = load_blocked_users()
                if message.chat.id not in blocked_users:
                    blocked_users.append(message.chat.id)
                    save_blocked_users(blocked_users)
            else:
                raise e

        dialog_states[message.chat.id] = {
            "state": "confirm_delete_all_dialogs",
            "selected_user_id": selected_user_id,
        }
        save_dialog_states()

    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Неверный ввод! Пожалуйста, введите номер пользователя")

@bot.message_handler(func=lambda message: message.chat.id in dialog_states and dialog_states[message.chat.id].get("state") == "confirm_delete_all_dialogs")
@check_user_blocked
def handle_confirm_delete_all_dialogs(message):
    if message.text.lower() not in ["да", "нет"]:
        bot.send_message(message.chat.id, "Неверный ввод! Пожалуйста, введите *да* для удаления или *нет* для отмены", parse_mode="Markdown")
        return

    if message.text.lower() == "да":
        selected_user_id = dialog_states[message.chat.id]["selected_user_id"]
        chat_key = f"{message.chat.id}_{selected_user_id}"

        chat_history_data = load_chat_history()
        if chat_key in chat_history_data:
            del chat_history_data[chat_key]

        with open(CHAT_HISTORY_PATH, 'w', encoding='utf-8') as file:
            json.dump(chat_history_data, file, ensure_ascii=False, indent=4)

        bot.send_message(message.chat.id, "✅ Все диалоги с пользователем успешно удалены!", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ Удаление всех диалогов с пользователем отменено!", parse_mode="Markdown")

    return show_communication_menu(message)