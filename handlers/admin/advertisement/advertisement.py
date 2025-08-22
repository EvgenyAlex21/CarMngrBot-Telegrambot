from core.imports import wraps, telebot, types, os, time, threading, json, re, ApiTelegramException, datetime
from core.bot_instance import bot, BASE_DIR
from decorators.blocked_user import load_blocked_users, save_blocked_users
from handlers.admin.statistics.statistics import check_admin_access
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

# -------------------------------------------------- РЕКЛАМА ---------------------------------------------------

ADVERTISEMENT_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'chats', 'advertisement.json')

advertisements = {}
temp_advertisement = {
    'text': None,
    'caption': None,
    'files': [],
    'chat_id': None
}

def save_advertisements():
    with open(ADVERTISEMENT_PATH, 'w', encoding='utf-8') as file:
        json.dump(advertisements, file, ensure_ascii=False, indent=4)

def load_advertisements():
    if os.path.exists(ADVERTISEMENT_PATH):
        with open(ADVERTISEMENT_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)
            for adv in data['advertisements'].values():
                if 'expected_date' in adv and 'expected_time' in adv:
                    adv['expected_date'] = datetime.strptime(adv['expected_date'], "%d.%m.%Y").strftime("%d.%m.%Y")
                    adv['expected_time'] = datetime.strptime(adv['expected_time'], "%H:%M").strftime("%H:%M")
                if 'end_date' in adv and 'end_time' in adv:
                    adv['end_date'] = datetime.strptime(adv['end_date'], "%d.%m.%Y").strftime("%d.%m.%Y")
                    adv['end_time'] = datetime.strptime(adv['end_time'], "%H:%M").strftime("%H:%M")
            return data
    return {"advertisements": {}}

advertisements = load_advertisements()
blocked_users = load_blocked_users()

@bot.message_handler(func=lambda message: message.text == 'Реклама' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_advertisement_menu(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Реклама'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    handle_admin_advertisement_requests(message)

def handle_admin_advertisement_requests(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Запросы на рекламу', 'Удалить рекламу')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите действие для рекламы:", reply_markup=markup)

# -------------------------------------------------- РЕКЛАМА (запросы на рекламу) ---------------------------------------------------

def validate_date_format(date_str):
    if date_str is None:
        return False
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False

def validate_future_date(date_str):
    today = datetime.now().date()
    input_date = datetime.strptime(date_str, "%d.%m.%Y").date()
    return input_date >= today

def validate_time_format(time_str):
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

def validate_future_time(date_str, time_str):
    now = datetime.now()
    input_datetime = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
    return input_datetime >= now

def validate_duration(duration_str):
    try:
        duration = int(duration_str)
        return 1 <= duration <= 7
    except ValueError:
        return False

@bot.message_handler(func=lambda message: message.text == 'Запросы на рекламу' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_advertisement_requests(message):
    if message.text == "Вернуться в рекламу":
        show_advertisement_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Запросы на рекламу'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    pending_advertisements = [adv for adv in advertisements['advertisements'].values() if adv['status'] == 'pending']
    current_time = datetime.now()

    for adv in pending_advertisements:
        end_datetime = datetime.strptime(f"{adv['end_date']} {adv['end_time']}", "%d.%m.%Y %H:%M")
        if current_time >= end_datetime:
            advertisement_id = next(key for key, value in advertisements['advertisements'].items() if value == adv)
            user_id = adv['user_id']
            theme = adv['theme']
            del advertisements['advertisements'][advertisement_id]
            save_advertisements()
            bot.send_message(user_id, f"❌ Ваша заявка по теме *{theme.lower()}* была отклонена, так как срок истек!", parse_mode="Markdown")

    pending_advertisements = [adv for adv in advertisements['advertisements'].values() if adv['status'] == 'pending']
    if pending_advertisements:
        advertisement_list = [
            f"⭐ *№{i + 1}*\n\n"
            f"👤 *Пользователь*: `{adv['user_id']}`\n"
            f"📝 *Тема*: {adv['theme'].lower()}\n"
            f"📅 *Начало*: {adv['expected_date']} в {adv['expected_time']}\n"
            f"⌛ *Конец*: {adv.get('end_date', 'N/A')} в {adv.get('end_time', 'N/A')}\n\n"
            for i, adv in enumerate(pending_advertisements)
        ]
        full_message = "*Список запросов* на рекламу:\n\n" + "\n\n".join(advertisement_list)

        max_length = 4096
        if len(full_message) > max_length:
            parts = [full_message[i:i + max_length] for i in range(0, len(full_message), max_length)]
            for part in parts:
                bot.send_message(message.chat.id, part, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, full_message, parse_mode="Markdown")

        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add('Вернуться в рекламу')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Введите номер запроса для просмотра:", reply_markup=markup)
        bot.register_next_step_handler(message, show_advertisement_request_details)
    else:
        bot.send_message(message.chat.id, "❌ Активных запросов на рекламу нет!", parse_mode="Markdown")

def show_advertisement_request_details(message):
    if message.text == "Вернуться в рекламу":
        show_advertisement_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    status_translation = {
        'pending': 'Ожидает',
        'accepted': 'Запланирована',
        'sent': 'Отправлена'
    }

    try:
        index = int(message.text) - 1
        advertisement_list = list(advertisements['advertisements'].values())
        if 0 <= index < len(advertisement_list):
            advertisement = advertisement_list[index]
            text = advertisement['text']

            info_message = (
                f"⭐ *Основная информация о рекламе*:\n\n"
                f"📝 *Тема*: {advertisement['theme'].lower()}\n"
                f"📅 *Начало*: {advertisement['expected_date']} в {advertisement['expected_time']}\n"
                f"⌛ *Конец*: {advertisement.get('end_date', 'N/A')} в {advertisement.get('end_time', 'N/A')}\n"
                f"📍 *Статус*: {status_translation.get(advertisement['status'], 'Неизвестен')}\n\n"
            )

            bot.send_message(message.chat.id, info_message, parse_mode="Markdown")

            if text and text != 'None':
                message_text = f"📝 Текст рекламы 📝\n\n{text}"
            else:
                message_text = ""

            if 'files' in advertisement and advertisement['files']:
                media_group = []
                first_file = True
                for file in advertisement['files']:
                    if first_file:
                        caption = message_text
                    else:
                        caption = None
                    if file['type'] == 'photo':
                        media_group.append(telebot.types.InputMediaPhoto(file['file_id'], caption=caption))
                    elif file['type'] == 'video':
                        media_group.append(telebot.types.InputMediaVideo(file['file_id'], caption=caption))
                    elif file['type'] == 'document':
                        media_group.append(telebot.types.InputMediaDocument(file['file_id'], caption=caption))
                    elif file['type'] == 'animation':
                        media_group.append(telebot.types.InputMediaAnimation(file['file_id'], caption=caption))
                    elif file['type'] == 'sticker':
                        bot.send_sticker(message.chat.id, file['file_id'])
                    elif file['type'] == 'audio':
                        media_group.append(telebot.types.InputMediaAudio(file['file_id'], caption=caption))
                    elif file['type'] == 'voice':
                        media_group.append(telebot.types.InputMediaAudio(file['file_id'], caption=caption))
                    elif file['type'] == 'video_note':
                        bot.send_video_note(message.chat.id, file['file_id'])
                    first_file = False

                if media_group:
                    bot.send_media_group(message.chat.id, media_group)
            else:
                if message_text:
                    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")

            markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.add('Принять рекламу', 'Отклонить рекламу')
            markup.add('Вернуться в рекламу')
            markup.add('В меню админ-панели')
            bot.send_message(message.chat.id, "Выберите действие для рекламы:", reply_markup=markup)
            bot.register_next_step_handler(message, handle_advertisement_request_action, index)
        else:
            bot.send_message(message.chat.id, "Неверный номер запроса! Попробуйте снова")
            bot.register_next_step_handler(message, show_advertisement_request_details)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер запроса!")
        bot.register_next_step_handler(message, show_advertisement_request_details)

def handle_advertisement_request_action(message, index):
    if message.text == "Вернуться в рекламу":
        show_advertisement_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    advertisement_id = list(advertisements['advertisements'].keys())[index]
    if advertisement_id not in advertisements['advertisements']:
        bot.send_message(message.chat.id, "❌ Ошибка: Реклама не найдена!")
        show_advertisement_menu(message)
        return

    advertisement = advertisements['advertisements'][advertisement_id]

    if message.text == 'Принять рекламу':
        advertisements['advertisements'][advertisement_id]['status'] = 'accepted'
        save_advertisements()
        bot.send_message(message.chat.id, "✅ Реклама была принята!\nВыберите действия для отправки:")
        choose_send_advertisement_action(message, advertisement_id)

    elif message.text == 'Отклонить рекламу':
        user_id = advertisement['user_id']
        theme = advertisement['theme']
        del advertisements['advertisements'][advertisement_id]
        save_advertisements()
        bot.send_message(message.chat.id, "❌ Реклама была отклонена!")
        bot.send_message(user_id, f"❌ Ваша заявка по теме *{theme.lower()}* была отклонена администратором!", parse_mode="Markdown")
        show_advertisement_menu(message)

    else:
        bot.send_message(message.chat.id, "Неверное действие! Попробуйте снова")
        show_advertisement_request_details(message)

def handle_user_withdraw_advertisement(message):
    user_id = message.chat.id
    for adv_id, adv in advertisements['advertisements'].items():
        if adv['user_id'] == user_id and adv['status'] == 'pending':
            del advertisements['advertisements'][adv_id]
            save_advertisements()
            bot.send_message(message.chat.id, "✅ Ваша заявка на рекламу была успешно отозвана!")
            return

    bot.send_message(message.chat.id, "❌ Вы не можете отозвать рекламу, так как она уже запланирована, отправлена или не существует!")

def schedule_advertisement(message, advertisement_id):
    if message.text == "Вернуться в рекламу":
        show_advertisement_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    advertisement = advertisements['advertisements'][advertisement_id]
    bot.send_message(message.chat.id, f"Тема: {advertisement['theme']}")

    if advertisement['text'] and advertisement['text'] != 'None':
        message_text = f"📝 Текст рекламы 📝\n\n{advertisement['text']}"
    else:
        message_text = ""

    if 'files' in advertisement and advertisement['files']:
        media_group = []
        first_file = True
        for file in advertisement['files']:
            if first_file:
                caption = message_text
            else:
                caption = None
            if file['type'] == 'photo':
                media_group.append(telebot.types.InputMediaPhoto(file['file_id'], caption=caption))
            elif file['type'] == 'video':
                media_group.append(telebot.types.InputMediaVideo(file['file_id'], caption=caption))
            elif file['type'] == 'document':
                media_group.append(telebot.types.InputMediaDocument(file['file_id'], caption=caption))
            elif file['type'] == 'animation':
                media_group.append(telebot.types.InputMediaAnimation(file['file_id'], caption=caption))
            elif file['type'] == 'sticker':
                bot.send_sticker(message.chat.id, file['file_id'])
            elif file['type'] == 'audio':
                media_group.append(telebot.types.InputMediaAudio(file['file_id'], caption=caption))
            elif file['type'] == 'voice':
                media_group.append(telebot.types.InputMediaAudio(file['file_id'], caption=caption))
            elif file['type'] == 'video_note':
                bot.send_video_note(message.chat.id, file['file_id'])
            first_file = False

        if media_group:
            bot.send_media_group(message.chat.id, media_group)
    else:
        if message_text:
            bot.send_message(message.chat.id, message_text, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Отправить по времени', 'Отправить всем')
    markup.add('Вернуться в рекламу')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите действие для рекламы:", reply_markup=markup)
    bot.register_next_step_handler(message, choose_send_advertisement_action, advertisement_id)

def choose_send_advertisement_action(message, advertisement_id):
    if message.text == "Вернуться в рекламу":
        show_advertisement_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Отправить по времени', 'Отправить всем')
    markup.add('Вернуться в рекламу')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите действие для рекламы:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_send_advertisement_action, advertisement_id)

def handle_send_advertisement_action(message, advertisement_id):
    if message.text == "Вернуться в рекламу":
        show_advertisement_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    if message.text == 'Отправить по времени':
        schedule_notification(message, advertisement_id)
    elif message.text == 'Отправить всем':
        send_advertisement_to_all(message, advertisement_id)
    else:
        bot.send_message(message.chat.id, "Неверное действие! Попробуйте снова")
        choose_send_advertisement_action(message, advertisement_id)

def schedule_notification(message, advertisement_id):
    if message.text == "Вернуться в рекламу":
        show_advertisement_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    if advertisement_id not in advertisements['advertisements']:
        bot.send_message(message.chat.id, "❌ Ошибка: Реклама не найдена!")
        show_admin_panel(message)
        return

    advertisement = advertisements['advertisements'][advertisement_id]
    expected_datetime = datetime.strptime(f"{advertisement['expected_date']} {advertisement['expected_time']}", "%d.%m.%Y %H:%M")
    current_time = datetime.now()

    advertisement['status'] = 'accepted'  
    save_advertisements()

    if current_time >= expected_datetime:
        send_advertisement_to_all(message, advertisement_id)
    else:
        delay = (expected_datetime - current_time).total_seconds()
        threading.Timer(delay, send_advertisement_to_all, [message, advertisement_id]).start()
        bot.send_message(message.chat.id, f"✅ Реклама *{advertisement['theme'].lower()}* запланирована на {advertisement['expected_date']} в {advertisement['expected_time']}!", parse_mode="Markdown")
        show_advertisement_menu(message)

def send_advertisement_to_all(message, advertisement_id):
    if message.text == "Вернуться в рекламу":
        show_advertisement_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    if advertisement_id not in advertisements['advertisements']:
        bot.send_message(message.chat.id, "❌ Ошибка: Реклама не найдена!")
        show_admin_panel(message)
        return

    advertisement = advertisements['advertisements'][advertisement_id]
    from handlers.user.user_main_menu import load_users_data as load_users
    users = load_users()
    user_message_pairs = []  

    for user_id in users.keys():
        if user_id in blocked_users:
            continue

        media_group = []
        first_file = True
        for file in advertisement['files']:
            if first_file:
                caption = advertisement['text']
            else:
                caption = None
            if file['type'] == 'photo':
                media_group.append(telebot.types.InputMediaPhoto(file['file_id'], caption=caption))
            elif file['type'] == 'video':
                media_group.append(telebot.types.InputMediaVideo(file['file_id'], caption=caption))
            elif file['type'] == 'document':
                media_group.append(telebot.types.InputMediaDocument(file['file_id'], caption=caption))
            elif file['type'] == 'animation':
                media_group.append(telebot.types.InputMediaAnimation(file['file_id'], caption=caption))
            elif file['type'] == 'sticker':
                bot.send_sticker(user_id, file['file_id'])
            elif file['type'] == 'audio':
                media_group.append(telebot.types.InputMediaAudio(file['file_id'], caption=caption))
            elif file['type'] == 'voice':
                media_group.append(telebot.types.InputMediaAudio(file['file_id'], caption=caption))
            elif file['type'] == 'video_note':
                bot.send_video_note(user_id, file['file_id'])
            first_file = False

        try:
            if media_group:
                sent_messages = bot.send_media_group(user_id, media_group)
                for sent_message in sent_messages:
                    user_message_pairs.append((user_id, sent_message.message_id))
            else:
                sent_message = bot.send_message(user_id, advertisement['text'])
                user_message_pairs.append((user_id, sent_message.message_id))
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                if user_id not in blocked_users:
                    blocked_users.append(user_id)
                    save_blocked_users(blocked_users)
            else:
                continue

    advertisement['user_ids'] = [pair[0] for pair in user_message_pairs]
    advertisement['message_ids'] = [pair[1] for pair in user_message_pairs]
    advertisement['status'] = 'sent'
    save_advertisements()

    bot.send_message(message.chat.id, "✅ Реклама отправлена всем пользователям!")
    show_admin_panel(message)

    from handlers.user.others.others_advertising import schedule_advertisement_deletion
    schedule_advertisement_deletion(advertisement_id, advertisement['end_date'], advertisement['end_time'])

def check_advertisement_expiration():
    while True:
        now = datetime.now()
        for adv_id, adv in list(advertisements['advertisements'].items()):
            if adv['status'] == 'accepted':
                end_datetime = datetime.strptime(f"{adv['end_date']} {adv['end_time']}", "%d.%m.%Y %H:%M")
                if now >= end_datetime:
                    from handlers.user.others.others_advertising import delete_advertisement_messages
                    delete_advertisement_messages(adv_id)
        time.sleep(60)
threading.Thread(target=check_advertisement_expiration, daemon=True).start()

def check_pending_advertisement_expiration():
    while True:
        current_time = datetime.now()
        for adv_id, adv in list(advertisements['advertisements'].items()):
            if adv['status'] == 'pending':
                end_datetime = datetime.strptime(f"{adv['end_date']} {adv['end_time']}", "%d.%m.%Y %H:%M")
                if current_time >= end_datetime:
                    user_id = adv['user_id']
                    theme = adv['theme']
                    del advertisements['advertisements'][adv_id]
                    save_advertisements()
                    bot.send_message(user_id, f"❌ Ваша заявка по теме *{theme.lower()}* была отклонена, так как срок истек!", parse_mode="Markdown")
        time.sleep(60)

threading.Thread(target=check_pending_advertisement_expiration, daemon=True).start()

# -------------------------------------------------- РЕКЛАМА (удалить рекламу) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Удалить рекламу' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_advertisement(message):
    if message.text == "Вернуться в рекламу":
        show_advertisement_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Удалить рекламу'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if advertisements['advertisements']:
        advertisement_list = [
            f"⭐️ №{i + 1}\n\n"
            f"👤 *Пользователь*: `{adv['user_id']}`\n"
            f"📝 *Тема*: {adv['theme'].lower()}\n"
            f"📅 *Начало*: {adv['expected_date']} в {adv['expected_time']}\n"
            f"⌛️ *Конец*: {adv.get('end_date', 'N/A')} в {adv.get('end_time', 'N/A')}\n"
            for i, adv in enumerate(advertisements['advertisements'].values()) if adv['status'] == 'accepted'
        ]
        if advertisement_list:
            full_message = "*Список опубликованных реклам*:\n\n" + "\n\n".join(advertisement_list)

            max_length = 4096
            if len(full_message) > max_length:
                parts = [full_message[i:i + max_length] for i in range(0, len(full_message), max_length)]
                for part in parts:
                    bot.send_message(message.chat.id, part, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, full_message, parse_mode="Markdown")

            markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            markup.add('Вернуться в рекламу')
            markup.add('В меню админ-панели')
            bot.send_message(message.chat.id, "Введите номер рекламы для удаления:", reply_markup=markup)
            bot.register_next_step_handler(message, process_delete_advertisement)
        else:
            bot.send_message(message.chat.id, "❌ У вас нет опубликованных реклам!", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ Нет опубликованных реклам!", parse_mode="Markdown")

def process_delete_advertisement(message):
    if message.text == "Вернуться в рекламу":
        show_advertisement_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        index = int(message.text) - 1
        advertisement_list = list(advertisements['advertisements'].values())
        if 0 <= index < len(advertisement_list):
            advertisement_id = list(advertisements['advertisements'].keys())[index]
            from handlers.user.others.others_advertising import delete_advertisement_messages
            delete_advertisement_messages(advertisement_id)
            bot.send_message(message.chat.id, f"✅ Реклама удалена!")
            show_advertisement_menu(message)
        else:
            bot.send_message(message.chat.id, "Неверный номер рекламы! Попробуйте снова")
            delete_advertisement(message)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер рекламы!")
        delete_advertisement(message)