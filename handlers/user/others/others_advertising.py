from core.imports import wraps, telebot, types, os, json, re, datetime, timedelta, time, threading, ApiTelegramException
from core.bot_instance import bot, BASE_DIR
from decorators.blocked_user import load_blocked_users, save_blocked_users
from handlers.admin.advertisement.advertisement import advertisements, temp_advertisement, save_advertisements, validate_date_format, validate_future_date, validate_time_format, validate_future_time
from .others_main import view_others
from ..user_main_menu import return_to_menu
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# --------------------------------------------- ПРОЧЕЕ (для рекламы) -----------------------------------------------

blocked_users = load_blocked_users()

@bot.message_handler(func=lambda message: message.text == "Для рекламы")
@check_function_state_decorator('Для рекламы')
@track_usage('Для рекламы')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_add_menu(message, show_description=True):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Заявка на рекламу', 'Ваши заявки')
    markup.add('Вернуться в прочее')
    markup.add('В главное меню')

    description = (
        "ℹ️ *Краткая справка по рекламе*\n\n"
        "📌 *Заявка:*\n"
        "Вы можете отправить заявку на рекламу в боте по кнопке, где нужно заполнить определенные поля\n\n"
        "📌 *Ваши заявки:*\n"
        "Вы можете посмотреть свои заявки на рекламу, а если нужно, то и отозвать\n\n"
        "📌 *Оплата и вопросы:*\n"
        "Заявки на рекламу и оплату принимает *администратор (разработчик)* - [@x_evgenyalex_x](https://t.me/x_evgenyalex_x). Если что-то не понятно, то вы можете обратиться к нему!\n\n"
    )

    if show_description:
        bot.send_message(message.chat.id, description, parse_mode="Markdown")

    bot.send_message(message.chat.id, "Выберите действие с рекламой:", reply_markup=markup)

# --------------------------------------------- ПРОЧЕЕ (заявка на рекламу) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Заявка на рекламу')
@check_function_state_decorator('Заявка на рекламу')
@track_usage('Заявка на рекламу')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_advertisement_request(message):
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('Вернуться в меню для рекламы')
    markup.add('Вернуться в прочее')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Введите тему рекламы и кратко о чем она:", reply_markup=markup)
    bot.register_next_step_handler(message, set_advertisement_theme)

@text_only_handler
def set_advertisement_theme(message):

    if message.text == 'Вернуться в меню для рекламы':
        temp_advertisement.clear()
        view_add_menu(message, show_description=False)
        return

    if message.text == 'Вернуться в прочее':
        temp_advertisement.clear()
        view_others(message)
        return

    if message.text == 'В главное меню':
        temp_advertisement.clear()
        return_to_menu(message)
        return

    advertisement_theme = message.text
    bot.send_message(message.chat.id, "Введите дату в формате ДД.ММ.ГГГГ, на которую вы хотите разместить рекламу:")
    bot.register_next_step_handler(message, set_advertisement_date, advertisement_theme)

@text_only_handler
def set_advertisement_date(message, advertisement_theme):

    if message.text == 'Вернуться в меню для рекламы':
        temp_advertisement.clear()
        view_add_menu(message, show_description=False)
        return

    if message.text == 'Вернуться в прочее':
        temp_advertisement.clear()
        view_others(message)
        return

    if message.text == 'В главное меню':
        temp_advertisement.clear()
        return_to_menu(message)
        return

    expected_date = message.text
    if expected_date is None or not validate_date_format(expected_date):
        bot.send_message(message.chat.id, "Неверный формат даты!\nПожалуйста, введите дату в формате ДД.ММ.ГГГГ")
        bot.register_next_step_handler(message, set_advertisement_date, advertisement_theme)
        return

    if not validate_future_date(expected_date):
        bot.send_message(message.chat.id, "Дата не может быть раньше текущей даты!\nПожалуйста, введите корректную дату")
        bot.register_next_step_handler(message, set_advertisement_date, advertisement_theme)
        return

    bot.send_message(message.chat.id, "Введите время в формате ЧЧ:ММ, на которое вы хотите разместить рекламу:")
    bot.register_next_step_handler(message, set_advertisement_time, advertisement_theme, expected_date)

@text_only_handler
def set_advertisement_time(message, advertisement_theme, expected_date):

    if message.text == 'Вернуться в меню для рекламы':
        temp_advertisement.clear()
        view_add_menu(message, show_description=False)
        return

    if message.text == 'Вернуться в прочее':
        temp_advertisement.clear()
        view_others(message)
        return

    if message.text == 'В главное меню':
        temp_advertisement.clear()
        return_to_menu(message)
        return

    expected_time = message.text
    if not validate_time_format(expected_time):
        bot.send_message(message.chat.id, "Неверный формат времени!\nПожалуйста, введите время в формате ЧЧ:ММ")
        bot.register_next_step_handler(message, set_advertisement_time, advertisement_theme, expected_date)
        return

    if not validate_future_time(expected_date, expected_time):
        bot.send_message(message.chat.id, "Время не может быть раньше текущего времени!\nПожалуйста, введите корректное время")
        bot.register_next_step_handler(message, set_advertisement_time, advertisement_theme, expected_date)
        return

    bot.send_message(message.chat.id, "Введите дату в формате ДД.ММ.ГГГГ для окончания действия рекламы:")
    bot.register_next_step_handler(message, set_advertisement_end_date, advertisement_theme, expected_date, expected_time)

@text_only_handler
def set_advertisement_end_date(message, advertisement_theme, expected_date, expected_time):
    if message.text == 'В главное меню':
        temp_advertisement.clear()
        return_to_menu(message)
        return

    if message.text == 'Вернуться в прочее':
        temp_advertisement.clear()
        view_others(message)
        return

    if message.text == 'Вернуться в меню для рекламы':
        temp_advertisement.clear()
        view_add_menu(message, show_description=False)
        return

    end_date = message.text
    if not validate_date_format(end_date):
        bot.send_message(message.chat.id, "Неверный формат даты!\nПожалуйста, введите дату в формате ДД.ММ.ГГГГ")
        bot.register_next_step_handler(message, set_advertisement_end_date, advertisement_theme, expected_date, expected_time)
        return

    if not validate_future_date(end_date):
        bot.send_message(message.chat.id, "Дата окончания не может быть раньше текущей даты!\nПожалуйста, введите корректную дату")
        bot.register_next_step_handler(message, set_advertisement_end_date, advertisement_theme, expected_date, expected_time)
        return

    start_datetime = datetime.strptime(f"{expected_date} {expected_time}", "%d.%m.%Y %H:%M")
    end_datetime = datetime.strptime(f"{end_date} 23:59", "%d.%m.%Y %H:%M")  
    if end_datetime.date() < start_datetime.date():
        bot.send_message(message.chat.id, "Дата окончания не может быть раньше даты начала!\nПожалуйста, введите корректную дату")
        bot.register_next_step_handler(message, set_advertisement_end_date, advertisement_theme, expected_date, expected_time)
        return

    bot.send_message(message.chat.id, "Введите время в формате ЧЧ:ММ для окончания действия рекламы:")
    bot.register_next_step_handler(message, set_advertisement_end_time, advertisement_theme, expected_date, expected_time, end_date)

@text_only_handler
def set_advertisement_end_time(message, advertisement_theme, expected_date, expected_time, end_date):
    if message.text == 'Вернуться в меню для рекламы':
        temp_advertisement.clear()
        view_add_menu(message, show_description=False)
        return

    if message.text == 'Вернуться в прочее':
        temp_advertisement.clear()
        view_others(message)
        return

    if message.text == 'В главное меню':
        temp_advertisement.clear()
        return_to_menu(message)
        return

    end_time = message.text
    if not validate_time_format(end_time):
        bot.send_message(message.chat.id, "Неверный формат времени!\nПожалуйста, введите время в формате ЧЧ:ММ:")
        bot.register_next_step_handler(message, set_advertisement_end_time, advertisement_theme, expected_date, expected_time, end_date)
        return

    start_datetime = datetime.strptime(f"{expected_date} {expected_time}", "%d.%m.%Y %H:%M")
    end_datetime = datetime.strptime(f"{end_date} {end_time}", "%d.%m.%Y %H:%M")
    if end_datetime <= start_datetime:
        bot.send_message(message.chat.id, "Дата и время окончания должны быть позже даты и времени начала!\nПожалуйста, введите корректное время")
        bot.register_next_step_handler(message, set_advertisement_end_time, advertisement_theme, expected_date, expected_time, end_date)
        return

    bot.send_message(message.chat.id, "Отправьте текст рекламы:")
    bot.register_next_step_handler(message, collect_advertisement_text, advertisement_theme, expected_date, expected_time, end_date, end_time)

@text_only_handler
def collect_advertisement_text(message, advertisement_theme, expected_date, expected_time, end_date, end_time):

    if message.text == 'Вернуться в меню для рекламы':
        temp_advertisement.clear()
        view_add_menu(message, show_description=False)
        return

    if message.text == 'Вернуться в прочее':
        temp_advertisement.clear()
        view_others(message)
        return

    if message.text == 'В главное меню':
        return_to_menu(message)
        return

    temp_advertisement['text'] = message.text
    temp_advertisement['chat_id'] = message.chat.id

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('Пропустить медиафайлы')
    markup.add('Вернуться в прочее')
    markup.add('Вернуться в меню для рекламы')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Отправьте мультимедийные файлы (если есть):", reply_markup=markup)
    bot.register_next_step_handler(message, collect_advertisement_media, advertisement_theme, expected_date, expected_time, end_date, end_time)

def collect_advertisement_media(message, advertisement_theme, expected_date, expected_time, end_date, end_time):

    if message.text == 'Вернуться в меню для рекламы':
        temp_advertisement.clear()
        view_add_menu(message, show_description=False)
        return

    if message.text == 'Вернуться в прочее':
        temp_advertisement.clear()
        view_others(message)
        return

    if message.text == 'В главное меню':
        temp_advertisement.clear()
        return_to_menu(message)
        return

    if message.text == "Пропустить медиафайлы":
        temp_advertisement['files'] = []
        save_advertisement_request(message, advertisement_theme, expected_date, expected_time, end_date, end_time)
        return

    content_type = message.content_type
    file_id = None

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

    if file_id:
        if 'files' not in temp_advertisement:
            temp_advertisement['files'] = []
        temp_advertisement['files'].append({
            'type': content_type,
            'file_id': file_id,
            'caption': temp_advertisement.get('text', '')
        })

        if len(temp_advertisement['files']) >= 10:
            save_advertisement_request(message, advertisement_theme, expected_date, expected_time, end_date, end_time)
            return

        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add('Добавить еще', 'Завершить отправку')
        markup.add('Вернуться в прочее')
        markup.add('Вернуться в меню для рекламы')
        markup.add('В главное меню')
        bot.send_message(message.chat.id, "Медиафайл добавлен! Хотите добавить еще?", reply_markup=markup)
        bot.register_next_step_handler(message, handle_advertisement_media_options, advertisement_theme, expected_date, expected_time, end_date, end_time)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте мультимедийный файл!")
        bot.register_next_step_handler(message, collect_advertisement_media, advertisement_theme, expected_date, expected_time, end_date, end_time)

def handle_advertisement_media_options(message, advertisement_theme, expected_date, expected_time, end_date, end_time):

    if message.text == 'Вернуться в меню для рекламы':
        temp_advertisement.clear()
        view_add_menu(message, show_description=False)
        return

    if message.text == 'Вернуться в прочее':
        temp_advertisement.clear()
        view_others(message)
        return

    if message.text == 'В главное меню':
        temp_advertisement.clear()
        return_to_menu(message)
        return

    if message.text == "Добавить еще":
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add('Пропустить медиафайлы')
        markup.add('Вернуться в меню для рекламы')
        markup.add('Вернуться в прочее')
        markup.add('В главное меню')
        bot.send_message(message.chat.id, "Отправьте следующий мультимедийный файл:", reply_markup=markup)
        bot.register_next_step_handler(message, collect_advertisement_media, advertisement_theme, expected_date, expected_time, end_date, end_time)
    elif message.text == "Завершить отправку":
        save_advertisement_request(message, advertisement_theme, expected_date, expected_time, end_date, end_time)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите действие!")
        bot.register_next_step_handler(message, handle_advertisement_media_options, advertisement_theme, expected_date, expected_time, end_date, end_time)

def save_advertisement_request(message, advertisement_theme, expected_date, expected_time, end_date, end_time):
    user_id = message.chat.id
    username = message.from_user.username
    advertisement_id = str(len(advertisements['advertisements']) + 1)
    advertisements['advertisements'][advertisement_id] = {
        'user_id': user_id,
        'username': username,
        'theme': advertisement_theme,
        'expected_date': expected_date,
        'expected_time': expected_time,
        'end_date': end_date,
        'end_time': end_time,
        'text': temp_advertisement['text'],
        'files': temp_advertisement['files'],
        'status': 'pending',
        'user_ids': [],
        'message_ids': []
    }

    save_advertisements()
    bot.send_message(message.chat.id, "✅ Ваша заявка на рекламу была успешно сформирована и отправлена администратору!")

    try:
        with open(os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json'), 'r', encoding='utf-8') as file:
            admin_data = json.load(file)
            admin_ids = admin_data.get('admin_sessions', [])
    except (FileNotFoundError, json.JSONDecodeError):
        admin_ids = []

    for admin_id in admin_ids:
        try:
            bot.send_message(admin_id, f"⚠️ У вас новая заявка на рекламу от пользователя `{user_id}` по теме *{advertisement_theme.lower()}* на {expected_date} в {expected_time} до {end_date} в {end_time}!", parse_mode="Markdown")
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                if admin_id not in blocked_users:
                    blocked_users.append(admin_id)
                    save_blocked_users(blocked_users)
            else:
                raise e

    temp_advertisement.clear()
    view_others(message)

def schedule_advertisement_deletion(advertisement_id, end_date, end_time):
    try:
        end_datetime = datetime.strptime(f"{end_date} {end_time}", "%d.%m.%Y %H:%M")
        delay = (end_datetime - datetime.now()).total_seconds()
        if delay > 0:
            threading.Timer(delay, delete_advertisement_messages, [advertisement_id]).start()
        else:
            delete_advertisement_messages(advertisement_id)
    except ValueError as e:
        pass

def delete_advertisement_messages(advertisement_id):
    if advertisement_id not in advertisements['advertisements']:
        return

    advertisement = advertisements['advertisements'][advertisement_id]
    user_ids = advertisement['user_ids']
    message_ids = advertisement['message_ids']

    if len(user_ids) != len(message_ids):
        pass
    
    for user_id, message_id in zip(user_ids, message_ids):
        try:
            bot.delete_message(user_id, message_id)
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 400 and 'message to delete not found' in e.result_json['description']:
                pass
            elif e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                if user_id not in blocked_users:
                    blocked_users.append(user_id)
                    save_blocked_users(blocked_users)
            else:
                pass

    del advertisements['advertisements'][advertisement_id]
    save_advertisements()

# --------------------------------------------- ПРОЧЕЕ (ваши заявки) -----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Ваши заявки')
@check_function_state_decorator('Ваши заявки')
@track_usage('Ваши заявки')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_user_advertisement_requests(message):
    user_id = message.chat.id
    user_advertisements = [adv for adv in advertisements['advertisements'].values() if adv['user_id'] == user_id]

    status_translation = {
        'pending': 'Ожидает',
        'accepted': 'Запланирована',
        'sent': 'Отправлена'
    }

    if user_advertisements:
        advertisement_list = [
            f"⭐ №{i + 1}\n\n"
            f"📝 *Тема*: {adv['theme'].lower()}\n"
            f"📅 *Начало*: {adv['expected_date']} в {adv['expected_time']}\n"
            f"⌛ *Конец*: {adv.get('end_date', 'N/A')} в {adv.get('end_time', 'N/A')}\n"
            f"📍 *Статус*: {status_translation.get(adv['status'], 'Неизвестен')}\n"
            for i, adv in enumerate(user_advertisements)
        ]
        full_message = "*Ваши заявки на рекламу*:\n\n" + "\n\n".join(advertisement_list)

        max_length = 4096
        if len(full_message) > max_length:
            parts = [full_message[i:i + max_length] for i in range(0, len(full_message), max_length)]
            for part in parts:
                bot.send_message(message.chat.id, part, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, full_message, parse_mode="Markdown")

        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add('Вернуться в меню для рекламы')
        markup.add('Вернуться в прочее')
        markup.add('В главное меню')
        bot.send_message(message.chat.id, "Введите номер заявки для просмотра:", reply_markup=markup)
        bot.register_next_step_handler(message, show_user_advertisement_request_details)
    else:
        bot.send_message(message.chat.id, "❌ У вас нет активных заявок на рекламу!", parse_mode="Markdown")

@text_only_handler
def show_user_advertisement_request_details(message):
    if message.text == "Вернуться в меню для рекламы":
        view_add_menu(message, show_description=False)
        return

    if message.text == 'Вернуться в прочее':
        view_others(message)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    status_translation = {
        'pending': 'Ожидает',
        'accepted': 'Запланирована',
        'sent': 'Отправлена'
    }

    try:
        index = int(message.text) - 1
        user_id = message.chat.id
        user_advertisements = [adv for adv in advertisements['advertisements'].values() if adv['user_id'] == user_id]

        if 0 <= index < len(user_advertisements):
            advertisement = user_advertisements[index]
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

            markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            if advertisement['status'] == 'pending':
                markup.add('Отозвать рекламу')
            markup.add('Вернуться в меню для рекламы')
            markup.add('Вернуться в прочее')
            markup.add('В главное меню')
            bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)
            bot.register_next_step_handler(message, handle_user_advertisement_request_action, index)
        else:
            bot.send_message(message.chat.id, "Неверный номер заявки!\nПопробуйте снова")
            show_user_advertisement_requests(message)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер заявки!")
        show_user_advertisement_requests(message)

@text_only_handler
def handle_user_advertisement_request_action(message, index):
    if message.text == "Вернуться в меню для рекламы":
        view_add_menu(message, show_description=False)
        return

    if message.text == 'Вернуться в прочее':
        view_others(message)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    user_id = message.chat.id
    user_advertisements = [adv for adv in advertisements['advertisements'].values() if adv['user_id'] == user_id]
    advertisement_id = list(advertisements['advertisements'].keys())[list(advertisements['advertisements'].values()).index(user_advertisements[index])]
    advertisement = user_advertisements[index]

    if message.text == 'Отозвать рекламу':
        if advertisement['status'] != 'pending':
            bot.send_message(message.chat.id, "❌ Ошибка: Реклама уже запланирована или отправлена и не может быть отозвана!")
            show_user_advertisement_requests(message)
            return

        del advertisements['advertisements'][advertisement_id]
        save_advertisements()
        bot.send_message(message.chat.id, "✅ Ваша заявка была успешно отозвана!")

        with open(os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json'), 'r', encoding='utf-8') as file:
            admin_data = json.load(file)
            admin_ids = admin_data.get('admin_sessions', [])

        for admin_id in admin_ids:
            try:
                bot.send_message(admin_id, f"✅ Заявка на рекламу от пользователя `{user_id}` по теме *{advertisement['theme'].lower()}* была отозвана!", parse_mode="Markdown")
            except ApiTelegramException as e:
                if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                    if admin_id not in blocked_users:
                        blocked_users.append(admin_id)
                        save_blocked_users(blocked_users)
                else:
                    raise e

        view_others(message)
    else:
        bot.send_message(message.chat.id, "Неверное действие!\nПопробуйте снова")
        show_user_advertisement_request_details(message)