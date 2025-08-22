from core.imports import wraps, telebot, types, os, json, re, datetime
from core.bot_instance import bot, BASE_DIR
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from handlers.user.others.others_chat_with_admin import check_and_create_file, DB_PATH
from handlers.admin.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha,
)

# -------------------------------------------------- РЕДАКЦИЯ ----------------------------------------------

NEWS_DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'chats', 'news.json')
ADMIN_SESSIONS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')
USER_DATA_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'users.json')
news = {}
admin_sessions = []
temp_news = {}

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

def save_news_database():
    for key, value in news.items():
        if 'time' in value and isinstance(value['time'], datetime):
            value['time'] = value['time'].strftime("%d.%m.%Y в %H:%M")
    with open(NEWS_DATABASE_PATH, 'w', encoding='utf-8') as file:
        json.dump(news, file, ensure_ascii=False, indent=4)
    for key, value in news.items():
        if 'time' in value and isinstance(value['time'], str):
            value['time'] = datetime.strptime(value['time'], "%d.%m.%Y в %H:%M")

def load_news_database():
    if os.path.exists(NEWS_DATABASE_PATH):
        with open(NEWS_DATABASE_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)
            for key, value in data.items():
                if 'time' in value and value['time']:
                    value['time'] = datetime.strptime(value['time'], "%d.%m.%Y в %H:%M")
            return data
    return {}

news = load_news_database()

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
        bot.send_message(message.chat.id, "У вас нет прав доступа для выполнения этой операции!")
        return False

def split_text(text, chunk_size=4096):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

@bot.message_handler(func=lambda message: message.text == 'Редакция' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_editorial_menu(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Редакция'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Опубликовать новость', 'Отредактировать новость', 'Посмотреть новость', 'Удалить новость')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите действие из редакции:", reply_markup=markup)

# -------------------------------------------------- РЕДАКЦИЯ (опубликовать новость) ----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Опубликовать новость' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def publish_news(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Опубликовать новость'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В редакцию')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите заголовок новости:", reply_markup=markup)
    bot.register_next_step_handler(message, set_news_title)

@text_only_handler
def set_news_title(message):

    if message.text == "В редакцию":
        show_editorial_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    news_title = message.text.capitalize()
    temp_news['title'] = news_title
    temp_news['files'] = []
    temp_news['chat_id'] = message.chat.id

    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В редакцию')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите подпись для новости:", reply_markup=markup)
    bot.register_next_step_handler(message, collect_news_caption)

@text_only_handler
def collect_news_caption(message):

    if message.text == "В редакцию":
        show_editorial_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    caption = message.text
    temp_news['caption'] = caption

    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('Пропустить медиафайлы')
    markup.add('В редакцию')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Отправьте мультимедийные файлы или пропустите отправку:", reply_markup=markup)
    bot.register_next_step_handler(message, collect_news_media)

def collect_news_media(message):
    if message.text == "Пропустить медиафайлы":
        temp_news['text'] = temp_news['caption']
        temp_news['caption'] = None
        save_news(message)
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
        temp_news['files'].append({
            'type': content_type,
            'file_id': file_id,
            'caption': temp_news['caption']
        })

        if len(temp_news['files']) >= 10:
            save_news(message)
            return

        markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add('Добавить еще', 'Завершить отправку')
        markup.add('В редакцию')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Медиафайл добавлен! Хотите добавить еще?", reply_markup=markup)
        bot.register_next_step_handler(message, handle_media_options)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте мультимедийный файл!")
        bot.register_next_step_handler(message, collect_news_media)

def handle_media_options(message):
    if message.text == "Добавить еще":
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add('В редакцию')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Отправьте следующий мультимедийный файл:", reply_markup=markup)
        bot.register_next_step_handler(message, collect_news_media)
    elif message.text == "Завершить отправку":
        save_news(message)
    elif message.text == "В редакцию":
        show_editorial_menu(message)
    elif message.text == "В меню админ-панели":
        show_admin_panel(message)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите действие!")
        bot.register_next_step_handler(message, handle_media_options)

def save_news(message):
    news_id = str(len(news) + 1)
    news[news_id] = {
        'title': temp_news['title'],
        'text': temp_news.get('text'),
        'time': datetime.now(),
        'files': temp_news['files']
    }
    save_news_database()
    bot.send_message(temp_news['chat_id'], "✅ Новость опубликована!")
    temp_news.clear()
    show_editorial_menu(message)

# -------------------------------------------------- РЕДАКЦИЯ (отредактировать новость) ----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Отредактировать новость' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def edit_news(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Отредактировать новость'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    news_list = [
        f"📰 №{i + 1}. *{n['title']}* - {n['time'].strftime('%d.%m.%Y в %H:%M')}"
        for i, n in enumerate(news.values())
    ]

    if news_list:
        news_text = "\n\n".join(news_list)
        chunks = split_text(news_text)
        for chunk in chunks:
            markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            markup.add('В редакцию')
            markup.add('В меню админ-панели')
            bot.send_message(message.chat.id, "📜 *Список новостей*:\n\n" + chunk, parse_mode="Markdown", reply_markup=markup)
        bot.send_message(message.chat.id, "Введите номер новости для редактирования:", reply_markup=markup)
        bot.register_next_step_handler(message, choose_news_to_edit)
    else:
        bot.send_message(message.chat.id, "❌ Нет новостей для редактирования!")

@text_only_handler
def choose_news_to_edit(message):

    if message.text == "В редакцию":
        show_editorial_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        index = int(message.text) - 1
        news_list = list(news.values())
        if 0 <= index < len(news_list):
            news_id = list(news.keys())[index]
            news_item = news[news_id]

            caption = news_item['files'][0]['caption'] if 'files' in news_item and news_item['files'] else None

            if caption and len(caption) > 200:
                caption = caption[:200] + "..."

            if caption:
                message_text = f"📌 ЗАГОЛОВОК НОВОСТИ 📌\n\n\n{news_item['title']}\n\n\n📢 ПОДПИСЬ НОВОСТИ 📢\n\n\n{caption}"
            elif news_item.get('text'):
                message_text = f"📌 ЗАГОЛОВОК НОВОСТИ 📌\n\n\n{news_item['title']}\n\n\n📝 ТЕКСТ НОВОСТИ 📝\n\n\n{news_item['text']}"
            else:
                message_text = f"📌 ЗАГОЛОВОК НОВОСТИ 📌\n\n\n{news_item['title']}"

            if 'files' in news_item and news_item['files']:
                media_group = []
                first_file = True
                for file in news_item['files']:
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
                bot.send_message(message.chat.id, message_text, parse_mode="Markdown")

            edit_list = []
            edit_list.append(f"№1. Заголовок новости")
            if news_item['text']:
                edit_list.append(f"№2. Текст новости")
            if 'files' in news_item and news_item['files']:
                edit_list.append(f"№3. Подпись к новости")
                edit_list.append("№4. Медиафайлы")

            edit_text = "\n".join(edit_list)
            bot.send_message(message.chat.id, "Что вы хотите отредактировать?\n\n" + edit_text)

            markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            markup.add('В редакцию')
            markup.add('В меню админ-панели')
            bot.send_message(message.chat.id, "Введите номер пункта для редактирования:", reply_markup=markup)
            bot.register_next_step_handler(message, edit_news_item, news_id)
        else:
            bot.send_message(message.chat.id, "Неверный номер новости! Попробуйте снова")
            bot.register_next_step_handler(message, choose_news_to_edit)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер новости!")
        bot.register_next_step_handler(message, choose_news_to_edit)

@text_only_handler
def edit_news_item(message, news_id):

    if message.text == "В редакцию":
        show_editorial_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        choice = int(message.text)
        news_item = news[news_id]

        if choice == 1:
            markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            markup.add('В редакцию')
            markup.add('В меню админ-панели')
            bot.send_message(message.chat.id, "Введите новый заголовок новости:", reply_markup=markup)
            bot.register_next_step_handler(message, edit_news_title, news_id)
        elif choice == 2:
            if 'text' in news_item and news_item['text']:
                markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                markup.add('В редакцию')
                markup.add('В меню админ-панели')
                bot.send_message(message.chat.id, "Введите новый текст новости:", reply_markup=markup)
                bot.register_next_step_handler(message, edit_news_text, news_id)
            else:
                bot.send_message(message.chat.id, "Текст новости отсутствует! Выберите другой пункт для редактирования:")
                bot.register_next_step_handler(message, edit_news_item, news_id)
        elif choice == 3:
            if 'files' in news_item and news_item['files']:
                markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                markup.add('В редакцию')
                markup.add('В меню админ-панели')
                bot.send_message(message.chat.id, "Введите новую подпись к новости:", reply_markup=markup)
                bot.register_next_step_handler(message, edit_news_caption, news_id)
            else:
                bot.send_message(message.chat.id, "Подпись к новости отсутствует! Выберите другой пункт для редактирования:")
                bot.register_next_step_handler(message, edit_news_item, news_id)
        elif choice == 4:
            if 'files' in news_item and news_item['files']:
                markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                markup.add('В редакцию')
                markup.add('В меню админ-панели')
                bot.send_message(message.chat.id, "Отправьте новые медиафайлы:", reply_markup=markup)
                bot.register_next_step_handler(message, edit_news_media, news_id)
            else:
                bot.send_message(message.chat.id, "Медиафайлы отсутствуют! Выберите другой пункт для редактирования:")
                bot.register_next_step_handler(message, edit_news_item, news_id)
        else:
            bot.send_message(message.chat.id, "Неверный номер пункта! Попробуйте снова")
            bot.register_next_step_handler(message, edit_news_item, news_id)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер пункта!")
        bot.register_next_step_handler(message, edit_news_item, news_id)

@text_only_handler
def edit_news_title(message, news_id):

    if message.text == "В редакцию":
        show_editorial_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    news_title = message.text
    news[news_id]['title'] = news_title
    save_news_database()
    bot.send_message(message.chat.id, "✅ Заголовок новости отредактирован!")
    show_editorial_menu(message)

@text_only_handler
def edit_news_text(message, news_id):

    if message.text == "В редакцию":
        show_editorial_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    news_text = message.text
    news[news_id]['text'] = news_text
    save_news_database()
    bot.send_message(message.chat.id, "✅ Текст новости отредактирован!")
    show_editorial_menu(message)

@text_only_handler
def edit_news_caption(message, news_id):

    if message.text == "В редакцию":
        show_editorial_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    caption = message.text
    for file in news[news_id]['files']:
        file['caption'] = caption
    save_news_database()
    bot.send_message(message.chat.id, "✅ Подпись новости отредактирована!")
    show_editorial_menu(message)

def edit_news_media(message, news_id):
    if message.text == "В редакцию":
        show_editorial_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
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
        caption = news[news_id]['files'][0]['caption'] if 'files' in news[news_id] and news[news_id]['files'] else None

        if caption and len(caption) > 200:
            caption = caption[:200] + "..."

        if not news[news_id].get('new_files'):
            news[news_id]['new_files'] = []
            news[news_id]['files'] = []

        news[news_id]['new_files'].append({
            'type': content_type,
            'file_id': file_id,
            'caption': caption
        })

        if len(news[news_id]['new_files']) >= 10:
            news[news_id]['files'] = news[news_id].get('new_files', [])
            del news[news_id]['new_files']
            save_news_database()
            bot.send_message(message.chat.id, "✅ Медиафайлы новости отредактированы!")
            show_editorial_menu(message)
            return

        markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add('Добавить еще', 'Завершить отправку')
        markup.add('В редакцию')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Медиафайл добавлен! Хотите добавить еще?", reply_markup=markup)
        bot.register_next_step_handler(message, handle_edit_media_options, news_id)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте мультимедийный файл!")
        bot.register_next_step_handler(message, edit_news_media, news_id)

def handle_edit_media_options(message, news_id):
    if message.text == "Добавить еще":
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add('В редакцию')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Отправьте следующий мультимедийный файл:", reply_markup=markup)
        bot.register_next_step_handler(message, edit_news_media, news_id)
    elif message.text == "Завершить отправку":
        news[news_id]['files'] = news[news_id].get('new_files', [])
        del news[news_id]['new_files']
        save_news_database()
        bot.send_message(message.chat.id, "✅ Медиафайлы новости отредактированы!")
        show_editorial_menu(message)
    elif message.text == "В редакцию":
        show_editorial_menu(message)
    elif message.text == "В меню админ-панели":
        show_admin_panel(message)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите действие!")
        bot.register_next_step_handler(message, handle_edit_media_options, news_id)

# -------------------------------------------------- РЕДАКЦИЯ (посмотреть новость) ----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Посмотреть новость' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_news(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Посмотреть новость'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    news_list = [
        f"📰 №{i + 1}. *{n['title']}* - {n['time'].strftime('%d.%m.%Y в %H:%M')}"
        for i, n in enumerate(news.values())
    ]

    if news_list:
        news_text = "\n\n".join(news_list)
        chunks = split_text(news_text)
        for chunk in chunks:
            markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            markup.add('В редакцию')
            markup.add('В меню админ-панели')
            bot.send_message(message.chat.id, "📜 *Список новостей*:\n\n" + chunk, parse_mode="Markdown", reply_markup=markup)
        bot.send_message(message.chat.id, "Введите номера новостей для просмотра:", reply_markup=markup)
        bot.register_next_step_handler(message, choose_news_to_view)
    else:
        bot.send_message(message.chat.id, "❌ Нет новостей для просмотра!")

@text_only_handler
def choose_news_to_view(message):

    if message.text == "В редакцию":
        show_editorial_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        indices = [int(x.strip()) - 1 for x in message.text.split(',')]
        news_list = list(news.values())
        invalid_indices = []

        for index in indices:
            if not (0 <= index < len(news_list)):
                invalid_indices.append(index + 1)

        if invalid_indices:
            bot.send_message(message.chat.id, f"Неверные номера новостей: *{', '.join(map(str, invalid_indices))}*! Пожалуйста, введите корректные номера новостей", parse_mode="Markdown")
            bot.register_next_step_handler(message, choose_news_to_view)
        else:
            for index in indices:
                news_item = news_list[index]

                caption = news_item['files'][0]['caption'] if 'files' in news_item and news_item['files'] else None

                if caption and len(caption) > 200:
                    caption = caption[:200] + "..."

                if caption:
                    message_text = f"📌 ЗАГОЛОВОК НОВОСТИ 📌\n\n\n{news_item['title']}\n\n\n📢 ПОДПИСЬ НОВОСТИ 📢\n\n\n{caption}"
                elif news_item.get('text'):
                    message_text = f"📌 ЗАГОЛОВОК НОВОСТИ 📌\n\n\n{news_item['title']}\n\n\n📝 ТЕКСТ НОВОСТИ 📝\n\n\n{news_item['text']}"
                else:
                    message_text = f"📌 ЗАГОЛОВОК НОВОСТИ 📌\n\n\n{news_item['title']}"

                if 'files' in news_item and news_item['files']:
                    media_group = []
                    first_file = True
                    for file in news_item['files']:
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
                    bot.send_message(message.chat.id, message_text, parse_mode="Markdown")

            show_editorial_menu(message)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректные номера новостей!")
        bot.register_next_step_handler(message, choose_news_to_view)

# -------------------------------------------------- РЕДАКЦИЯ (удалить новость) ----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Удалить новость' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_news(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Удалить новость'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    news_list = [
        f"📰 №{i + 1}. *{n['title']}* - {n['time'].strftime('%d.%m.%Y в %H:%M')}"
        for i, n in enumerate(news.values())
    ]

    if news_list:
        news_text = "\n\n".join(news_list)
        chunks = split_text(news_text)
        for chunk in chunks:
            markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            markup.add('В редакцию')
            markup.add('В меню админ-панели')
            bot.send_message(message.chat.id, "📜 *Список новостей*:\n\n" + chunk, parse_mode="Markdown", reply_markup=markup)
        bot.send_message(message.chat.id, "Введите номера новостей для удаления:", reply_markup=markup)
        bot.register_next_step_handler(message, choose_news_to_delete)
    else:
        bot.send_message(message.chat.id, "❌ Нет новостей для удаления!")

@text_only_handler
def choose_news_to_delete(message):

    if message.text == "В редакцию":
        show_editorial_menu(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        indices = [int(x.strip()) - 1 for x in message.text.split(',')]
        news_list = list(news.values())
        deleted_news_titles = []
        invalid_indices = []

        for index in indices:
            if 0 <= index < len(news_list):
                news_id = list(news.keys())[index]
                deleted_news = news.pop(news_id)
                deleted_news_titles.append(deleted_news['title'])
            else:
                invalid_indices.append(index + 1)

        if invalid_indices:
            bot.send_message(message.chat.id, f"Неверные номера новостей: *{', '.join(map(str, invalid_indices))}*! Пожалуйста, введите корректные номера новостей", parse_mode="Markdown")
            bot.register_next_step_handler(message, choose_news_to_delete)
        else:
            if deleted_news_titles:
                new_news = {}
                for i, (key, value) in enumerate(news.items(), start=1):
                    new_news[str(i)] = value
                news.clear()
                news.update(new_news)

                save_news_database()
                deleted_news_titles_lower = [title.lower() for title in deleted_news_titles]
                bot.send_message(message.chat.id, f"✅ Новости (*{', '.join(deleted_news_titles_lower)}*) удалены!", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "❌ Нет новостей для удаления!")

            show_editorial_menu(message)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректные номера новостей!")
        bot.register_next_step_handler(message, choose_news_to_delete)