from core.imports import wraps, telebot, types, os, json, re, requests, Nominatim
from core.bot_instance import bot
from handlers.user.user_main_menu import return_to_menu
from handlers.user.antiradar.antiradar import user_tracking, track_user_location
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ----------------------------------------------- ПОИСК МЕСТ ---------------------------------------------------

geolocator = Nominatim(user_agent="geo_bot")

user_locations = {}

def get_yandex_maps_search_url(latitude, longitude, query):
    base_url = "https://yandex.ru/maps/?"
    search_params = {
        'll': f"{longitude},{latitude}",
        'z': 15,
        'text': query,
        'mode': 'search'
    }
    query_string = "&".join([f"{key}={value}" for key, value in search_params.items()])
    return f"{base_url}{query_string}"

def shorten_url(original_url):
    endpoint = 'https://clck.ru/--'
    response = requests.get(endpoint, params={'url': original_url})
    return response.text

@bot.message_handler(func=lambda message: message.text == "Поиск мест")
@check_function_state_decorator('Поиск мест')
@track_usage('Поиск мест')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def placesearch(message, show_description=True):
    user_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_azs = types.KeyboardButton("АЗС")
    button_car_wash = types.KeyboardButton("Автомойки")
    button_auto_service = types.KeyboardButton("Автосервисы")
    button_parking = types.KeyboardButton("Парковки")
    button_evacuation = types.KeyboardButton("Эвакуация")
    button_gibdd_mreo = types.KeyboardButton("ГИБДД")
    button_accident_commissioner = types.KeyboardButton("Комиссары")
    button_impound = types.KeyboardButton("Штрафстоянка")
    item1 = types.KeyboardButton("В главное меню")
    markup.add(button_azs, button_car_wash, button_auto_service)
    markup.add(button_parking, button_evacuation, button_gibdd_mreo, button_accident_commissioner, button_impound)
    markup.add(item1)

    help_message = (
        "ℹ️ *Краткая справка по поиску мест*\n\n"
        "📌 *Выбор поиска:*\n"
        "Выбираете категорию для поиска из кнопок\n\n"
        "📌 *Отправка геопозиции:*\n"
        "Отправляется ваша геопозиция\n\n"
        "📌 *Поиск:*\n"
        "Вывод ссылки(-ок) с ближайшими местами по вашей геопозиции\n\n"
    )

    if show_description:
        bot.send_message(user_id, help_message, parse_mode="Markdown")

    bot.send_message(user_id, "Выберите категорию для ближайшего поиска:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Выбрать категорию заново")
@check_function_state_decorator('Выбрать категорию заново')
@track_usage('Выбрать категорию заново')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_reset_category(message):
    selected_categories.pop(message.chat.id, None)
    placesearch(message, show_description=False)

selected_categories = {}

@bot.message_handler(func=lambda message: message.text in {"АЗС", "Автомойки", "Автосервисы", "Парковки", "Эвакуация", "ГИБДД", "Комиссары", "Штрафстоянка"})
@check_function_state_decorator('АЗС')
@check_function_state_decorator('Автомойки')
@check_function_state_decorator('Автосервисы')
@check_function_state_decorator('Парковки')
@check_function_state_decorator('Эвакуация')
@check_function_state_decorator('ГИБДД')
@check_function_state_decorator('Комиссары')
@check_function_state_decorator('Штрафстоянка')
@track_usage('АЗС')
@track_usage('Автомойки')
@track_usage('Автосервисы')
@track_usage('Парковки')
@track_usage('Эвакуация')
@track_usage('ГИБДД')
@track_usage('Комиссары')
@track_usage('Штрафстоянка')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_menu_category_buttons(message):
    if message.text in {"АЗС", "Автомойки", "Автосервисы", "Парковки", "Эвакуация", "ГИБДД", "Комиссары", "Штрафстоянка"}:
        selected_categories[message.chat.id] = message.text
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button_send_location = types.KeyboardButton("Отправить геолокацию", request_location=True)
        button_reset_category = types.KeyboardButton("Выбрать категорию заново")
        item1 = types.KeyboardButton("В главное меню")
        keyboard.add(button_send_location)
        keyboard.add(button_reset_category)
        keyboard.add(item1)
        bot.send_message(
            message.chat.id,
            f"Отправьте свою геолокацию!\nВам будет выдан список ближайших мест по категории - *{selected_categories[message.chat.id].lower()}:*",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
    else:
        selected_categories.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "Пожалуйста, выберите категорию из меню!")

def _has_selected_category(m):
    try:
        return selected_categories.get(m.chat.id) is not None
    except Exception:
        return False

@bot.message_handler(content_types=['location'], func=_has_selected_category)
@check_function_state_decorator('Функция для обработки локации')
@track_usage('Функция для обработки локации')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@check_subscription_chanal
@rate_limit_with_captcha
def handle_location(message):
    user_id = message.chat.id
    latitude = message.location.latitude
    longitude = message.location.longitude

    is_tracking = user_tracking.get(user_id, {}).get('tracking', False)
    current_category = selected_categories.get(user_id)

    if is_tracking:
        user_tracking[user_id]['location'] = message.location

        if not user_tracking[user_id].get('started', False):
            user_tracking[user_id]['started'] = True
            track_user_location(user_id, message.location)

        return
    elif current_category:
        try:
            location = geolocator.reverse((latitude, longitude), language='ru', timeout=10)
            address = location.address

            search_url = get_yandex_maps_search_url(latitude, longitude, current_category)
            try:
                short_search_url = shorten_url(search_url)
            except Exception:
                short_search_url = search_url

            message_text = f"🏙️ *Ближайшие {current_category.lower()} по адресу:* \n\n{address}\n\n"
            message_text += f"🗺️ [Ссылка на карту]({short_search_url})"

            bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
            selected_categories.pop(user_id, None)

            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button_reset_category = types.KeyboardButton("Выбрать категорию заново")
            item1 = types.KeyboardButton("В главное меню")
            keyboard.add(button_reset_category)
            keyboard.add(item1)
            bot.send_message(message.chat.id, "✅ Отлично, места найдены!\nВы можете повторить поиск по другой категории:", reply_markup=keyboard)

        except Exception as e:
            bot.send_message(message.chat.id, f"Произошла ошибка при обработке вашего запроса: {e}")
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите категорию из меню!")