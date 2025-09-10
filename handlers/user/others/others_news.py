from core.imports import wraps, telebot, types, os, json, re, datetime
from core.bot_instance import bot, BASE_DIR
from .others_main import view_others
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ----------------------------------------------------- ПРОЧЕЕ (новости) ----------------------------------------------------

NEWS_DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'chats', 'news.json')

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

@bot.message_handler(func=lambda message: message.text == 'Новости')
@check_function_state_decorator('Новости')
@track_usage('Новости')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_news_menu(message, show_description=True):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add('3 новости', '5 новостей', '7 новостей')
    markup.add('10 новостей', '15 новостей')
    markup.add('Вернуться в прочее')
    markup.add('В главное меню')

    description = (
        "ℹ️ *Краткая справка по отображению новостей*\n\n"
        "📌 Вы можете выбрать *количество новостей* для показа *(3, 5, 7, 10, 15)*\n"
        "📌 Они сортируются от новых к старым\n"
        "📌 Если новости закончились, то вы вернетесь в меню прочее\n\n"
        "_P.S. Новости публикует редактор или администратор (разработчик). По техническим причинам новости могут не публиковаться!_"
    )

    if show_description:
        bot.send_message(message.chat.id, description, parse_mode="Markdown")

    bot.send_message(message.chat.id, "Выберите количество новостей:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ['3 новости', '5 новостей', '7 новостей', '10 новостей', '15 новостей'])
@check_function_state_decorator('3 новости')
@check_function_state_decorator('5 новостей')
@check_function_state_decorator('7 новостей')
@check_function_state_decorator('10 новостей')
@check_function_state_decorator('15 новостей')
@track_usage('3 новости')
@track_usage('5 новостей')
@track_usage('7 новостей')
@track_usage('10 новостей')
@track_usage('15 новостей')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_news_selection(message):

    count = int(message.text.split()[0])
    news_list = sorted(news.values(), key=lambda x: x['time'], reverse=True)

    if message.text == 'Вернуться в прочее':
        view_others(message)
        return

    if len(news_list) == 0:
        bot.send_message(message.chat.id, "❌ Новостей нет!")
        view_others(message)
        return

    for i in range(min(count, len(news_list))):
        news_item = news_list[i]
        if 'files' in news_item and news_item['files']:
            media_group = []
            caption = None
            for file in news_item['files']:
                if file.get('caption'):
                    caption = file['caption']
                    break

            if caption and len(caption) > 200:
                caption = caption[:200] + "..."

            first_file = True
            for file in news_item['files']:
                if file['type'] == 'photo':
                    media_group.append(telebot.types.InputMediaPhoto(file['file_id'], caption=caption if first_file else None))
                elif file['type'] == 'video':
                    media_group.append(telebot.types.InputMediaVideo(file['file_id'], caption=caption if first_file else None))
                elif file['type'] == 'document':
                    media_group.append(telebot.types.InputMediaDocument(file['file_id'], caption=caption if first_file else None))
                elif file['type'] == 'animation':
                    media_group.append(telebot.types.InputMediaAnimation(file['file_id'], caption=caption if first_file else None))
                elif file['type'] == 'sticker':
                    bot.send_sticker(message.chat.id, file['file_id'])
                elif file['type'] == 'audio':
                    media_group.append(telebot.types.InputMediaAudio(file['file_id'], caption=caption if first_file else None))
                elif file['type'] == 'voice':
                    media_group.append(telebot.types.InputMediaAudio(file['file_id'], caption=caption if first_file else None))
                elif file['type'] == 'video_note':
                    bot.send_video_note(message.chat.id, file['file_id'])
                first_file = False
            if media_group:
                bot.send_media_group(message.chat.id, media_group)
        if news_item['text']:
            bot.send_message(message.chat.id, news_item['text'])

    if len(news_list) > count:
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add('Еще новости')
        markup.add('Вернуться в прочее')
        markup.add('В главное меню')
        bot.send_message(message.chat.id, "Хотите посмотреть еще новости?", reply_markup=markup)
        bot.register_next_step_handler(message, handle_more_news, count)
    else:
        bot.send_message(message.chat.id, "✅ Новости закончились!")
        view_others(message)

@text_only_handler
def handle_more_news(message, start_index):

    if message.text == 'Вернуться в прочее':
        view_others(message)
        return

    if message.text == 'Еще новости':
        news_list = sorted(news.values(), key=lambda x: x['time'], reverse=True)
        if start_index >= len(news_list):
            bot.send_message(message.chat.id, "✅ Новости закончились!")
            view_others(message)
            return

        end_index = min(start_index + 3, len(news_list))
        for i in range(start_index, end_index):
            news_item = news_list[i]
            if 'files' in news_item and news_item['files']:
                media_group = []
                for file in news_item['files']:
                    if file['type'] == 'photo':
                        media_group.append(telebot.types.InputMediaPhoto(file['file_id'], caption=file.get('caption', "")))
                    elif file['type'] == 'video':
                        media_group.append(telebot.types.InputMediaVideo(file['file_id'], caption=file.get('caption', "")))
                    elif file['type'] == 'document':
                        media_group.append(telebot.types.InputMediaDocument(file['file_id'], caption=file.get('caption', "")))
                    elif file['type'] == 'animation':
                        media_group.append(telebot.types.InputMediaAnimation(file['file_id'], caption=file.get('caption', "")))
                    elif file['type'] == 'sticker':
                        bot.send_sticker(message.chat.id, file['file_id'])
                    elif file['type'] == 'audio':
                        media_group.append(telebot.types.InputMediaAudio(file['file_id'], caption=file.get('caption', "")))
                    elif file['type'] == 'voice':
                        media_group.append(telebot.types.InputMediaAudio(file['file_id'], caption=file.get('caption', "")))
                    elif file['type'] == 'video_note':
                        bot.send_video_note(message.chat.id, file['file_id'])
                if media_group:
                    bot.send_media_group(message.chat.id, media_group)
            if news_item['text']:
                bot.send_message(message.chat.id, news_item['text'])

        if end_index < len(news_list):
            markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            markup.add('Еще новости')
            markup.add('Вернуться в прочее')
            markup.add('В главное меню')
            bot.send_message(message.chat.id, "Хотите посмотреть еще новости?", reply_markup=markup)
            bot.register_next_step_handler(message, handle_more_news, end_index)
        else:
            bot.send_message(message.chat.id, "✅ Новости закончились!")
            view_others(message)
    else:
        view_others(message)