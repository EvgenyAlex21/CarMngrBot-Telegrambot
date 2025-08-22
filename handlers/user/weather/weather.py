from core.imports import wraps, telebot, types, os, json, re, requests, datetime, timedelta, pd, defaultdict
from core.bot_instance import bot, BASE_DIR
from core.config import OPENWEATHERMAP_API_KEY, WEATHERAPI_API_KEY
from handlers.user.user_main_menu import return_to_menu
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

def save_user_location(chat_id, latitude, longitude, city_code):
    from handlers.user.others.others_notifications import save_user_location as _f
    return _f(chat_id, latitude, longitude, city_code)

def load_user_locations():
    from handlers.user.others.others_notifications import load_user_locations as _f
    return _f()

# ------------------------------------------------------------- ПОГОДА ---------------------------------------------------------

OPENWEATHERMAP_WEATHER_URL = 'http://api.openweathermap.org/data/2.5/weather'
OPENWEATHERMAP_FORECAST_URL = 'http://api.openweathermap.org/data/2.5/forecast'
OPENMETEO_FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
WEATHERAPI_CURRENT_URL = 'https://api.weatherapi.com/v1/current.json'
WEATHERAPI_FORECAST_URL = 'https://api.weatherapi.com/v1/forecast.json'
NOMINATIM_URL = 'https://nominatim.openstreetmap.org/reverse'

MAX_MESSAGE_LENGTH = 4096
user_data = {}

file_path = os.path.join(BASE_DIR, 'files', 'files_for_price_weather', 'combined_cities.txt')
os.makedirs(os.path.dirname(file_path), exist_ok=True)

if not os.path.exists(file_path):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("")
    except Exception as e:
        pass

def load_cities_from_file(file_path=os.path.join(BASE_DIR, 'files', 'files_for_price_weather', 'combined_cities.txt')):
    cities = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                city_name_rus, city_name_eng = line.strip().split(' - ')
                cities[city_name_eng.lower()] = city_name_rus
    except Exception as e:
        pass
    return cities

def translate_weather_description(english_description):
    translation_dict = {
        'clear sky': 'ясное небо',
        'few clouds': 'небольшая облачность',
        'scattered clouds': 'рассеянные облака',
        'broken clouds': 'облачно с прояснениями',
        'shower rain': 'небольшой дождь',
        'rain': 'дождь',
        'thunderstorm': 'гроза',
        'snow': 'снег',
        'mist': 'туман',
        'light snow': 'небольшой снег',
        'overcast clouds': 'пасмурно',
        'heavy snow': 'сильный снегопад',
        'sunny': 'ясное небо',
        'partly cloudy': 'небольшая облачность',
        'cloudy': 'облачно',
        'overcast': 'пасмурно',
        'light rain': 'небольшой дождь',
        'moderate rain': 'дождь',
        'heavy rain': 'сильный дождь',
        'patchy rain possible': 'возможен небольшой дождь',
        'light snow showers': 'небольшой снег',
        'heavy snow showers': 'сильный снегопад',
        'fog': 'туман',
        'thundery outbreaks possible': 'возможна гроза'
    }
    return translation_dict.get(english_description.lower(), english_description)

def get_city_coordinates(city):
    try:
        params = {'q': city, 'format': 'json', 'limit': 1}
        headers = {'User-Agent': 'CarMngrBot/1.0'}
        response = requests.get('https://nominatim.openstreetmap.org/search', params=params, headers=headers, timeout=5)
        data = response.json()
        if data and len(data) > 0:
            return {'latitude': float(data[0]['lat']), 'longitude': float(data[0]['lon'])}
        return None
    except Exception:
        return None

def get_city_name(latitude, longitude):
    try:
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'zoom': 10 
        }
        headers = {'User-Agent': 'CarMngrBot/1.0'}
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=5)
        data = response.json()
        if data and 'address' in data:
            city = data['address'].get('city') or data['address'].get('town') or data['address'].get('village') or 'Неизвестный город'
            return city
        return 'Неизвестный город'
    except Exception:
        return 'Неизвестный город'

def fetch_weather_data(url_type, params, api_type='openweathermap'):
    try:
        if api_type == 'openweathermap':
            response = requests.get(params['url'], params=params['params'], timeout=10)
            if response.status_code == 200:
                return response.json(), 'openweathermap'
            return None, 'openweathermap'

        elif api_type == 'openmeteo':
            openmeteo_params = {
                'latitude': params['params'].get('lat') or params['params'].get('latitude'),
                'longitude': params['params'].get('lon') or params['params'].get('longitude'),
                'current_weather': 'true' if url_type == 'weather' else 'false',
                'hourly': 'temperature_2m,relativehumidity_2m,pressure_msl,windspeed_10m,weathercode' if url_type == 'forecast' else '',
                'daily': 'temperature_2m_max,temperature_2m_min,weathercode' if url_type == 'forecast' else '',
                'timezone': 'auto'
            }
            response = requests.get(OPENMETEO_FORECAST_URL, params=openmeteo_params, timeout=10)
            if response.status_code == 200:
                return response.json(), 'openmeteo'
            return None, 'openmeteo'

        elif api_type == 'weatherapi':
            weatherapi_params = {
                'key': WEATHERAPI_API_KEY,
                'q': params['params'].get('q', f"{params['params'].get('lat')},{params['params'].get('lon')}"),
                'lang': 'ru'
            }
            if url_type == 'forecast':
                weatherapi_params['days'] = params.get('days', 7)
            url = WEATHERAPI_CURRENT_URL if url_type == 'weather' else WEATHERAPI_FORECAST_URL
            response = requests.get(url, params=weatherapi_params, timeout=10)
            if response.status_code == 200:
                return response.json(), 'weatherapi'
            return None, 'weatherapi'

    except Exception:
        return None, api_type

def normalize_weather_data(data, api_type, url_type):
    if not data:
        return None

    if api_type == 'openweathermap':
        return data

    elif api_type == 'openmeteo':
        if url_type == 'weather':
            weather_code = data['current_weather']['weathercode']
            description = {
                0: 'clear sky', 1: 'few clouds', 2: 'scattered clouds', 3: 'broken clouds',
                45: 'fog', 51: 'light rain', 61: 'rain', 71: 'light snow', 73: 'snow', 75: 'heavy snow',
                95: 'thunderstorm'
            }.get(weather_code, 'unknown')
            return {
                'main': {
                    'temp': data['current_weather']['temperature'],
                    'feels_like': data['current_weather']['temperature'],
                    'humidity': data.get('hourly', {}).get('relativehumidity_2m', [0])[0],
                    'pressure': data.get('hourly', {}).get('pressure_msl', [0])[0]
                },
                'wind': {'speed': data['current_weather']['windspeed']},
                'weather': [{'description': description}]
            }
        elif url_type == 'forecast':
            forecasts = []
            for i, time in enumerate(data['hourly']['time']):
                weather_code = data['hourly']['weathercode'][i]
                description = {
                    0: 'clear sky', 1: 'few clouds', 2: 'scattered clouds', 3: 'broken clouds',
                    45: 'fog', 51: 'light rain', 61: 'rain', 71: 'light snow', 73: 'snow', 75: 'heavy snow',
                    95: 'thunderstorm'
                }.get(weather_code, 'unknown')
                forecasts.append({
                    'dt_txt': time,
                    'main': {
                        'temp': data['hourly']['temperature_2m'][i],
                        'feels_like': data['hourly']['temperature_2m'][i],
                        'humidity': data['hourly']['relativehumidity_2m'][i],
                        'pressure': data['hourly']['pressure_msl'][i]
                    },
                    'wind': {'speed': data['hourly']['windspeed_10m'][i]},
                    'weather': [{'description': description}]
                })
            return {'list': forecasts}

    elif api_type == 'weatherapi':
        if url_type == 'weather':
            return {
                'main': {
                    'temp': data['current']['temp_c'],
                    'feels_like': data['current']['feelslike_c'],
                    'humidity': data['current']['humidity'],
                    'pressure': data['current']['pressure_mb']
                },
                'wind': {'speed': data['current']['wind_kph'] / 3.6},
                'weather': [{'description': data['current']['condition']['text']}]
            }
        elif url_type == 'forecast':
            forecasts = []
            for day in data['forecast']['forecastday']:
                for hour in day['hour']:
                    forecasts.append({
                        'dt_txt': hour['time'],
                        'main': {
                            'temp': hour['temp_c'],
                            'feels_like': hour['feelslike_c'],
                            'humidity': hour['humidity'],
                            'pressure': hour['pressure_mb']
                        },
                        'wind': {'speed': hour['wind_kph'] / 3.6},
                        'weather': [{'description': hour['condition']['text']}]
                    })
            return {'list': forecasts}

    return None

def get_current_weather(coords):
    try:
        city_name = get_city_name(coords['latitude'], coords['longitude'])
        params = {
            'url': OPENWEATHERMAP_WEATHER_URL,
            'params': {
                'lat': coords['latitude'],
                'lon': coords['longitude'],
                'appid': OPENWEATHERMAP_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            }
        }

        for api in ['openweathermap', 'openmeteo', 'weatherapi']:
            data, api_type = fetch_weather_data('weather', params, api)
            if data:
                data = normalize_weather_data(data, api_type, 'weather')
                if data:
                    temperature = round(data['main']['temp'])
                    feels_like = round(data['main']['feels_like'])
                    humidity = data['main']['humidity']
                    pressure = data['main']['pressure']
                    wind_speed = data['wind']['speed']
                    description = translate_weather_description(data['weather'][0]['description'])

                    current_time = datetime.now().strftime("%H:%M")
                    current_date = datetime.now().strftime("%d.%m.%Y")

                    return (
                        f"*Погода на {current_date} в {current_time}*:\n"
                        f"*(г. {city_name}; {coords['latitude']}, {coords['longitude']})*\n\n"
                        f"🌡️ *Температура:* {temperature}°C\n"
                        f"🌬️ *Ощущается как:* {feels_like}°C\n"
                        f"💧 *Влажность:* {humidity}%\n"
                        f"〽️ *Давление:* {pressure} мм рт. ст.\n"
                        f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                        f"☁️ *Описание:* {description}\n\n"
                    )
        return None
    except Exception as e:
        return None

@bot.message_handler(func=lambda message: message.text == "Погода")
@check_function_state_decorator('Погода')
@track_usage('Погода')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def weather(message, show_description=True):
    try:
        help_message = (
            "ℹ️ *Краткая справка по отображению погоды*\n\n"
            "📌 *Отправка геопозиции или ввод города:*\n"
            "Нажмите на кнопку ниже, чтобы отправить вашу геопозицию или введите город самостоятельно\n\n"
            "📌 *Выбор периода:*\n"
            "Выбираете период для просмотра погоды из кнопок\n\n"
            "📌 *Погода:*\n"
            "Вывод информации о погоде для выбранного периода\n\n"
        )

        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(telebot.types.KeyboardButton("Отправить геопозицию", request_location=True))
        markup.row(telebot.types.KeyboardButton("В главное меню"))

        if show_description:
            bot.send_message(message.chat.id, help_message, parse_mode="Markdown")

        bot.send_message(message.chat.id, "Отправьте геопозицию или введите название города:", reply_markup=markup)
        bot.register_next_step_handler(message, handle_input_5)

    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при обработке вашего запроса!\nПопробуйте позже")

@text_only_handler
def handle_input_5(message):
    try:
        if message.text == "В главное меню":
            return_to_menu(message)
            return

        if message.location:
            latitude = message.location.latitude
            longitude = message.location.longitude

            save_user_location(message.chat.id, latitude, longitude, None)

            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
            markup.row('Сегодня', 'Завтра')
            markup.row('Неделя', 'Месяц')
            markup.row('Другое место')
            markup.row('В главное меню')

            bot.send_message(message.chat.id, "Выберите период:", reply_markup=markup)
            return

        cities = load_cities_from_file()
        city_input = message.text.strip().lower()
        city_eng = None
        city_rus = None

        for eng, rus in cities.items():
            if rus.lower() == city_input:
                city_eng = eng
                city_rus = rus
                break

        if city_eng:
            user_data[message.chat.id] = {'city': city_eng, 'city_rus': city_rus}
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
            markup.row('Сегодня', 'Завтра')
            markup.row('Неделя', 'Месяц')
            markup.row('Другое место')
            markup.row('В главное меню')
            bot.send_message(message.chat.id, f"Вы выбрали город: *{city_rus}*\nТеперь выберите период:", reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ Город не найден!\nПожалуйста, введите название города еще раз или отправьте геопозицию")
            bot.register_next_step_handler(message, handle_input_5)

    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при обработке вашего ввода!\nПопробуйте позже")

@bot.message_handler(func=lambda message: message.text in ['Сегодня', 'Завтра', 'Неделя', 'Месяц', 'Другое место'])
@check_function_state_decorator('Сегодня')
@check_function_state_decorator('Завтра')
@check_function_state_decorator('Неделя')
@check_function_state_decorator('Месяц')
@check_function_state_decorator('Другое место')
@track_usage('Сегодня')
@track_usage('Завтра')
@track_usage('Неделя')
@track_usage('Месяц')
@track_usage('Другое место')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_period_5(message):
    period = message.text.lower()
    chat_id = message.chat.id

    user_locations = load_user_locations()
    coords = user_locations.get(str(chat_id))
    city_data = user_data.get(chat_id, {})

    if not coords and not city_data:
        bot.send_message(chat_id, "❌ Не удалось получить данные о местоположении или городе!\nПожалуйста, начните сначала...")
        weather(message, show_description=False)
        return

    if period == 'другое место':
        user_data.pop(chat_id, None)
        user_locations.pop(str(chat_id), None)
        weather(message, show_description=False)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    # Если пользователь ввёл город в текущей сессии, используем его В ПРИОРИТЕТЕ,
    # иначе используем сохранённые координаты
    if city_data:
        city = city_data.get('city')
        city_rus = city_data.get('city_rus')
        if period == 'сегодня':
            send_weather_by_city(chat_id, city, city_rus, 'weather')
        elif period == 'завтра':
            send_forecast_daily_by_city(chat_id, city, city_rus, 'forecast', 1)
        elif period == 'неделя':
            send_forecast_weekly_by_city(chat_id, city, city_rus, 'forecast', 8)
        elif period == 'месяц':
            send_forecast_monthly_by_city(chat_id, city, city_rus, 'forecast', 31)
    elif coords:
        if period == 'сегодня':
            send_weather(chat_id, coords, 'weather')
        elif period == 'завтра':
            send_forecast_daily(chat_id, coords, 'forecast', 1)
        elif period == 'неделя':
            send_forecast_weekly(chat_id, coords, 'forecast', 8)
        elif period == 'месяц':
            send_forecast_monthly(chat_id, coords, 'forecast', 31)

def send_weather(chat_id, coords, url_type):
    try:
        weather_message = get_current_weather(coords)
        if weather_message:
            bot.send_message(chat_id, weather_message, parse_mode="Markdown")
            send_forecast_remaining_day(chat_id, coords, 'forecast')
        else:
            bot.send_message(chat_id, "❌ Не удалось получить текущую погоду!")
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при запросе текущей погоды!\nПопробуйте позже")

def send_forecast_remaining_day(chat_id, coords, url_type):
    try:
        params = {
            'url': OPENWEATHERMAP_FORECAST_URL,
            'params': {
                'lat': coords['latitude'],
                'lon': coords['longitude'],
                'appid': OPENWEATHERMAP_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            }
        }

        for api in ['openweathermap', 'openmeteo', 'weatherapi']:
            data, api_type = fetch_weather_data(url_type, params, api)
            if data:
                data = normalize_weather_data(data, api_type, url_type)
                if data:
                    forecasts = data['list']
                    now = datetime.now()
                    message = "*Прогноз на оставшуюся часть дня:*\n\n"

                    for forecast in forecasts:
                        date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                        if now.date() == date_time.date() and date_time > now:
                            formatted_date = date_time.strftime("%d.%m.%Y")
                            formatted_time = date_time.strftime("%H:%M")
                            temperature = round(forecast['main']['temp'])
                            feels_like = round(forecast['main']['feels_like'])
                            humidity = forecast['main']['humidity']
                            pressure = forecast['main']['pressure']
                            wind_speed = forecast['wind']['speed']
                            description = translate_weather_description(forecast['weather'][0]['description'])

                            message += (
                                f"*Погода на {formatted_date} в {formatted_time}:*\n\n"
                                f"🌡️ *Температура:* {temperature}°C\n"
                                f"🌬️ *Ощущается как:* {feels_like}°C\n"
                                f"💧 *Влажность:* {humidity}%\n"
                                f"〽️ *Давление:* {pressure} мм рт. ст.\n"
                                f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                                f"☁️ *Описание:* {description}\n\n"
                            )

                    if message == "*Прогноз на оставшуюся часть дня:*\n\n":
                        message = "❌ Нет доступного прогноза на оставшуюся часть дня!"

                    bot.send_message(chat_id, message, parse_mode="Markdown")
                    return
        bot.send_message(chat_id, "❌ Не удалось получить прогноз на оставшуюся часть дня!")
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на оставшуюся часть дня!\nПопробуйте позже")

def send_forecast_daily(chat_id, coords, url_type, days_ahead):
    try:
        params = {
            'url': OPENWEATHERMAP_FORECAST_URL,
            'params': {
                'lat': coords['latitude'],
                'lon': coords['longitude'],
                'appid': OPENWEATHERMAP_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            },
            'days': days_ahead
        }

        for api in ['openweathermap', 'openmeteo', 'weatherapi']:
            data, api_type = fetch_weather_data(url_type, params, api)
            if data:
                data = normalize_weather_data(data, api_type, url_type)
                if data:
                    forecast = data['list'][min(days_ahead * 8, len(data['list']) - 1)]
                    date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                    temperature = round(forecast['main']['temp'])
                    feels_like = round(forecast['main']['feels_like'])
                    humidity = forecast['main']['humidity']
                    pressure = forecast['main']['pressure']
                    wind_speed = forecast['wind']['speed']
                    description = translate_weather_description(forecast['weather'][0]['description'])

                    message = (
                        f"*Прогноз на {date_time.strftime('%d.%m.%Y')}*\n\n"
                        f"🌡️ *Температура:* {temperature}°C\n"
                        f"🌬️ *Ощущается как:* {feels_like}°C\n"
                        f"💧 *Влажность:* {humidity}%\n"
                        f"〽️ *Давление:* {pressure} мм рт. ст.\n"
                        f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                        f"☁️ *Описание:* {description}\n"
                    )
                    bot.send_message(chat_id, message, parse_mode="Markdown")
                    send_hourly_forecast_tomorrow(chat_id, coords, url_type)
                    return
        bot.send_message(chat_id, "❌ Не удалось получить прогноз на завтра!")
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на завтра!\nПопробуйте позже")

def send_hourly_forecast_tomorrow(chat_id, coords, url_type):
    try:
        params = {
            'url': OPENWEATHERMAP_FORECAST_URL,
            'params': {
                'lat': coords['latitude'],
                'lon': coords['longitude'],
                'appid': OPENWEATHERMAP_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            }
        }

        for api in ['openweathermap', 'openmeteo', 'weatherapi']:
            data, api_type = fetch_weather_data(url_type, params, api)
            if data:
                data = normalize_weather_data(data, api_type, url_type)
                if data:
                    forecasts = data['list']
                    now = datetime.now()
                    tomorrow = now + timedelta(days=1)
                    message = "*Почасовой прогноз на завтра:*\n\n"

                    for forecast in forecasts:
                        date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                        if tomorrow.date() == date_time.date():
                            formatted_time = date_time.strftime("%H:%M")
                            formatted_date = date_time.strftime("%d.%m.%Y")
                            temperature = round(forecast['main']['temp'])
                            feels_like = round(forecast['main']['feels_like'])
                            humidity = forecast['main']['humidity']
                            pressure = forecast['main']['pressure']
                            wind_speed = forecast['wind']['speed']
                            description = translate_weather_description(forecast['weather'][0]['description'])

                            message += (
                                f"*Погода на {formatted_date} в {formatted_time}:*\n\n"
                                f"🌡️ *Температура:* {temperature}°C\n"
                                f"🌬️ *Ощущается как:* {feels_like}°C\n"
                                f"💧 *Влажность:* {humidity}%\n"
                                f"〽️ *Давление:* {pressure} мм рт. ст.\n"
                                f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                                f"☁️ *Описание:* {description}\n\n"
                            )

                    if message == "*Почасовой прогноз на завтра:*\n\n":
                        message = "❌ Нет доступного почасового прогноза на завтра!"

                    message_chunks = [message[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]
                    for chunk in message_chunks:
                        bot.send_message(chat_id, chunk, parse_mode="Markdown")
                    return
        bot.send_message(chat_id, "❌ Не удалось получить почасовой прогноз на завтра!")
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при запросе почасового прогноза на завтра!\nПопробуйте позже")

def send_forecast_weekly(chat_id, coords, url_type, retries=3):
    try:
        params = {
            'url': OPENWEATHERMAP_FORECAST_URL,
            'params': {
                'lat': coords['latitude'],
                'lon': coords['longitude'],
                'appid': OPENWEATHERMAP_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            }
        }

        daily_forecasts = defaultdict(list)
        message = "*Прогноз на неделю:*\n\n"

        for api in ['openweathermap', 'openmeteo', 'weatherapi']:
            for attempt in range(retries):
                data, api_type = fetch_weather_data(url_type, params, api)
                if data:
                    data = normalize_weather_data(data, api_type, url_type)
                    if data:
                        forecasts = data['list']
                        for forecast in forecasts:
                            date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                            date_str = date_time.strftime('%d.%m.%Y')

                            if len(daily_forecasts) >= 7 and date_str not in daily_forecasts:
                                break

                            temperature = round(forecast['main']['temp'])
                            feels_like = round(forecast['main']['feels_like'])
                            humidity = forecast['main']['humidity']
                            pressure = forecast['main']['pressure']
                            wind_speed = forecast['wind']['speed']
                            description = translate_weather_description(forecast['weather'][0]['description'])

                            daily_forecasts[date_str].append({
                                'temperature': temperature,
                                'feels_like': feels_like,
                                'humidity': humidity,
                                'pressure': pressure,
                                'wind_speed': wind_speed,
                                'description': description
                            })

                        for date, forecasts in daily_forecasts.items():
                            temp_sum = sum(f['temperature'] for f in forecasts)
                            feels_like_sum = sum(f['feels_like'] for f in forecasts)
                            count = len(forecasts)
                            avg_temp = round(temp_sum / count)
                            avg_feels_like = round(feels_like_sum / count)

                            message += (
                                f"*Погода на {date}:*\n\n"
                                f"🌡️ *Температура:* {avg_temp}°C\n"
                                f"🌬️ *Ощущается как:* {avg_feels_like}°C\n"
                                f"💧 *Влажность:* {forecasts[0]['humidity']}%\n"
                                f"〽️ *Давление:* {forecasts[0]['pressure']} мм рт. ст.\n"
                                f"💨 *Скорость ветра:* {forecasts[0]['wind_speed']} м/с\n"
                                f"☁️ *Описание:* {forecasts[0]['description']}\n\n"
                            )

                        bot.send_message(chat_id, message, parse_mode="Markdown")
                        return
                if attempt == retries - 1:
                    break
        bot.send_message(chat_id, "❌ Не удалось получить прогноз на неделю!")
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на неделю!\nПопробуйте позже")

def send_forecast_monthly(chat_id, coords, url_type, days=31):
    try:
        params = {
            'url': OPENWEATHERMAP_FORECAST_URL,
            'params': {
                'lat': coords['latitude'],
                'lon': coords['longitude'],
                'appid': OPENWEATHERMAP_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            },
            'days': days
        }

        for api in ['openweathermap', 'weatherapi']:
            data, api_type = fetch_weather_data(url_type, params, api)
            if data:
                data = normalize_weather_data(data, api_type, url_type)
                if data:
                    forecasts = data['list']
                    message = "*Прогноз на месяц:*\n\n"

                    daily_forecasts = {}
                    for forecast in forecasts:
                        date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                        date_str = date_time.strftime('%d.%m.%Y')

                        if date_str not in daily_forecasts:
                            daily_forecasts[date_str] = {
                                'temperature': round(forecast['main']['temp']),
                                'feels_like': round(forecast['main']['feels_like'])
                            }

                    for date, values in daily_forecasts.items():
                        message += (
                            f"*{date}:*\n\n"
                            f"🌡️ *Температура:* {values['temperature']}°C\n"
                            f"🌬️ *Ощущается как:* {values['feels_like']}°C\n\n"
                        )

                    unavailable_dates = [
                        date for date in pd.date_range(start=datetime.now(), periods=days).strftime('%d.%m.%Y')
                        if date not in daily_forecasts
                    ]

                    if unavailable_dates:
                        start_date = unavailable_dates[0]
                        end_date = unavailable_dates[-1]
                        message += (
                            f"*С {start_date} по {end_date}:*\n\n_"
                            f"Данные недоступны из-за ограничений_\n\n"
                        )

                    if message == "*Прогноз на месяц:*\n\n":
                        message = "❌ Нет доступного прогноза на месяц!"

                    bot.send_message(chat_id, message, parse_mode="Markdown")
                    return
        bot.send_message(chat_id, "❌ Не удалось получить прогноз на месяц!")
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на месяц!\nПопробуйте позже")

def send_weather_by_city(chat_id, city, city_rus, url_type):
    try:
        params = {
            'url': OPENWEATHERMAP_WEATHER_URL,
            'params': {
                'q': city,
                'appid': OPENWEATHERMAP_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            }
        }

        coords = get_city_coordinates(city_rus)
        if coords:
            params['params']['lat'] = coords['latitude']
            params['params']['lon'] = coords['longitude']

        for api in ['openweathermap', 'openmeteo', 'weatherapi']:
            data, api_type = fetch_weather_data(url_type, params, api)
            if data:
                data = normalize_weather_data(data, api_type, url_type)
                if data:
                    temperature = round(data['main']['temp'])
                    feels_like = round(data['main']['feels_like'])
                    humidity = data['main']['humidity']
                    pressure = data['main']['pressure']
                    wind_speed = data['wind']['speed']
                    description = translate_weather_description(data['weather'][0]['description'])

                    current_time = datetime.now().strftime("%H:%M")
                    current_date = datetime.now().strftime("%d.%m.%Y")

                    message = (
                        f"*Погода в {city_rus} на {current_date} в {current_time}:*\n\n"
                        f"🌡️ *Температура:* {temperature}°C\n"
                        f"🌬️ *Ощущается как:* {feels_like}°C\n"
                        f"💧 *Влажность:* {humidity}%\n"
                        f"〽️ *Давление:* {pressure} мм рт. ст.\n"
                        f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                        f"☁️ *Описание:* {description}\n"
                    )
                    bot.send_message(chat_id, message, parse_mode="Markdown")
                    send_forecast_remaining_day_by_city(chat_id, city, city_rus, 'forecast')
                    return
        bot.send_message(chat_id, "❌ Не удалось получить текущую погоду для города!")
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при запросе текущей погоды!\nПопробуйте позже")

def send_forecast_remaining_day_by_city(chat_id, city, city_rus, url_type):
    try:
        params = {
            'url': OPENWEATHERMAP_FORECAST_URL,
            'params': {
                'q': city,
                'appid': OPENWEATHERMAP_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            }
        }

        coords = get_city_coordinates(city_rus)
        if coords:
            params['params']['lat'] = coords['latitude']
            params['params']['lon'] = coords['longitude']

        for api in ['openweathermap', 'openmeteo', 'weatherapi']:
            data, api_type = fetch_weather_data(url_type, params, api)
            if data:
                data = normalize_weather_data(data, api_type, url_type)
                if data:
                    forecasts = data['list']
                    now = datetime.now()
                    message = "*Прогноз на оставшуюся часть дня:*\n\n"

                    for forecast in forecasts:
                        date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                        if now.date() == date_time.date() and date_time > now:
                            formatted_date = date_time.strftime("%d.%m.%Y")
                            formatted_time = date_time.strftime("%H:%M")
                            temperature = round(forecast['main']['temp'])
                            feels_like = round(forecast['main']['feels_like'])
                            humidity = forecast['main']['humidity']
                            pressure = forecast['main']['pressure']
                            wind_speed = forecast['wind']['speed']
                            description = translate_weather_description(forecast['weather'][0]['description'])

                            message += (
                                f"*Погода на {formatted_date} в {formatted_time}:*\n\n"
                                f"🌡️ *Температура:* {temperature}°C\n"
                                f"🌬️ *Ощущается как:* {feels_like}°C\n"
                                f"💧 *Влажность:* {humidity}%\n"
                                f"〽️ *Давление:* {pressure} мм рт. ст.\n"
                                f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                                f"☁️ *Описание:* {description}\n\n"
                            )

                    if message == "*Прогноз на оставшуюся часть дня:*\n\n":
                        message = "❌ Нет доступного прогноза на оставшуюся часть дня!"

                    bot.send_message(chat_id, message, parse_mode="Markdown")
                    return
        bot.send_message(chat_id, "❌ Не удалось получить прогноз на оставшуюся часть дня!")
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на оставшуюся часть дня!\nПопробуйте позже")

def send_forecast_daily_by_city(chat_id, city, city_rus, url_type, days_ahead):
    try:
        params = {
            'url': OPENWEATHERMAP_FORECAST_URL,
            'params': {
                'q': city,
                'appid': OPENWEATHERMAP_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            },
            'days': days_ahead
        }

        coords = get_city_coordinates(city_rus)
        if coords:
            params['params']['lat'] = coords['latitude']
            params['params']['lon'] = coords['longitude']

        for api in ['openweathermap', 'openmeteo', 'weatherapi']:
            data, api_type = fetch_weather_data(url_type, params, api)
            if data:
                data = normalize_weather_data(data, api_type, url_type)
                if data:
                    forecast = data['list'][min(days_ahead * 8, len(data['list']) - 1)]
                    date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                    temperature = round(forecast['main']['temp'])
                    feels_like = round(forecast['main']['feels_like'])
                    humidity = forecast['main']['humidity']
                    pressure = forecast['main']['pressure']
                    wind_speed = forecast['wind']['speed']
                    description = translate_weather_description(forecast['weather'][0]['description'])

                    message = (
                        f"*Прогноз для {city_rus} на {date_time.strftime('%d.%m.%Y')}*\n\n"
                        f"🌡️ *Температура:* {temperature}°C\n"
                        f"🌬️ *Ощущается как:* {feels_like}°C\n"
                        f"💧 *Влажность:* {humidity}%\n"
                        f"〽️ *Давление:* {pressure} мм рт. ст.\n"
                        f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                        f"☁️ *Описание:* {description}\n"
                    )
                    bot.send_message(chat_id, message, parse_mode="Markdown")
                    send_hourly_forecast_tomorrow_by_city(chat_id, city, city_rus, url_type)
                    return
        bot.send_message(chat_id, "❌ Не удалось получить прогноз на завтра!")
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на завтра!\nПопробуйте позже")

def send_hourly_forecast_tomorrow_by_city(chat_id, city, city_rus, url_type):
    try:
        params = {
            'url': OPENWEATHERMAP_FORECAST_URL,
            'params': {
                'q': city,
                'appid': OPENWEATHERMAP_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            }
        }

        coords = get_city_coordinates(city_rus)
        if coords:
            params['params']['lat'] = coords['latitude']
            params['params']['lon'] = coords['longitude']

        for api in ['openweathermap', 'openmeteo', 'weatherapi']:
            data, api_type = fetch_weather_data(url_type, params, api)
            if data:
                data = normalize_weather_data(data, api_type, url_type)
                if data:
                    forecasts = data['list']
                    now = datetime.now()
                    tomorrow = now + timedelta(days=1)
                    message = "*Почасовой прогноз на завтра:*\n\n"

                    for forecast in forecasts:
                        date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                        if tomorrow.date() == date_time.date():
                            formatted_time = date_time.strftime("%H:%M")
                            formatted_date = date_time.strftime("%d.%m.%Y")
                            temperature = round(forecast['main']['temp'])
                            feels_like = round(forecast['main']['feels_like'])
                            humidity = forecast['main']['humidity']
                            pressure = forecast['main']['pressure']
                            wind_speed = forecast['wind']['speed']
                            description = translate_weather_description(forecast['weather'][0]['description'])

                            message += (
                                f"*Погода на {formatted_date} в {formatted_time}:*\n\n"
                                f"🌡️ *Температура:* {temperature}°C\n"
                                f"🌬️ *Ощущается как:* {feels_like}°C\n"
                                f"💧 *Влажность:* {humidity}%\n"
                                f"〽️ *Давление:* {pressure} мм рт. ст.\n"
                                f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                                f"☁️ *Описание:* {description}\n\n"
                            )

                    if message == "*Почасовой прогноз на завтра:*\n\n":
                        message = "❌ Нет доступного почасового прогноза на завтра!"

                    message_chunks = [message[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]
                    for chunk in message_chunks:
                        bot.send_message(chat_id, chunk, parse_mode="Markdown")
                    return
        bot.send_message(chat_id, "❌ Не удалось получить почасовой прогноз на завтра!")
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при запросе почасового прогноза на завтра!\nПопробуйте позже")

def send_forecast_weekly_by_city(chat_id, city, city_rus, url_type, retries=3):
    try:
        params = {
            'url': OPENWEATHERMAP_FORECAST_URL,
            'params': {
                'q': city,
                'appid': OPENWEATHERMAP_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            }
        }

        coords = get_city_coordinates(city_rus)
        if coords:
            params['params']['lat'] = coords['latitude']
            params['params']['lon'] = coords['longitude']

        daily_forecasts = defaultdict(list)
        message = "*Прогноз на неделю:*\n\n"

        for api in ['openweathermap', 'openmeteo', 'weatherapi']:
            for attempt in range(retries):
                data, api_type = fetch_weather_data(url_type, params, api)
                if data:
                    data = normalize_weather_data(data, api_type, url_type)
                    if data:
                        forecasts = data['list']
                        for forecast in forecasts:
                            date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                            date_str = date_time.strftime('%d.%m.%Y')

                            if len(daily_forecasts) >= 7 and date_str not in daily_forecasts:
                                break

                            temperature = round(forecast['main']['temp'])
                            feels_like = round(forecast['main']['feels_like'])
                            humidity = forecast['main']['humidity']
                            pressure = forecast['main']['pressure']
                            wind_speed = forecast['wind']['speed']
                            description = translate_weather_description(forecast['weather'][0]['description'])

                            daily_forecasts[date_str].append({
                                'temperature': temperature,
                                'feels_like': feels_like,
                                'humidity': humidity,
                                'pressure': pressure,
                                'wind_speed': wind_speed,
                                'description': description
                            })

                        for date, forecasts in daily_forecasts.items():
                            temp_sum = sum(f['temperature'] for f in forecasts)
                            feels_like_sum = sum(f['feels_like'] for f in forecasts)
                            count = len(forecasts)
                            avg_temp = round(temp_sum / count)
                            avg_feels_like = round(feels_like_sum / count)

                            message += (
                                f"*Погода на {date}:*\n\n"
                                f"🌡️ *Температура:* {avg_temp}°C\n"
                                f"🌬️ *Ощущается как:* {avg_feels_like}°C\n"
                                f"💧 *Влажность:* {forecasts[0]['humidity']}%\n"
                                f"〽️ *Давление:* {forecasts[0]['pressure']} мм рт. ст.\n"
                                f"💨 *Скорость ветра:* {forecasts[0]['wind_speed']} м/с\n"
                                f"☁️ *Описание:* {forecasts[0]['description']}\n\n"
                            )

                        bot.send_message(chat_id, message, parse_mode="Markdown")
                        return
                if attempt == retries - 1:
                    break
        bot.send_message(chat_id, "❌ Не удалось получить прогноз на неделю!")
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на неделю!\nПопробуйте позже")

def send_forecast_monthly_by_city(chat_id, city, city_rus, url_type, days=31):
    try:
        params = {
            'url': OPENWEATHERMAP_FORECAST_URL,
            'params': {
                'q': city,
                'appid': OPENWEATHERMAP_API_KEY,
                'units': 'metric',
                'lang': 'ru'
            },
            'days': days
        }

        coords = get_city_coordinates(city_rus)
        if coords:
            params['params']['lat'] = coords['latitude']
            params['params']['lon'] = coords['longitude']

        for api in ['openweathermap', 'weatherapi']:
            data, api_type = fetch_weather_data(url_type, params, api)
            if data:
                data = normalize_weather_data(data, api_type, url_type)
                if data:
                    forecasts = data['list']
                    message = "*Прогноз на месяц:*\n\n"

                    daily_forecasts = {}
                    for forecast in forecasts:
                        date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                        date_str = date_time.strftime('%d.%m.%Y')

                        if date_str not in daily_forecasts:
                            daily_forecasts[date_str] = {
                                'temperature': round(forecast['main']['temp']),
                                'feels_like': round(forecast['main']['feels_like'])
                            }

                    for date, values in daily_forecasts.items():
                        message += (
                            f"*{date}:*\n\n"
                            f"🌡️ *Температура:* {values['temperature']}°C\n"
                            f"🌬️ *Ощущается как:* {values['feels_like']}°C\n\n"
                        )

                    unavailable_dates = [
                        date for date in pd.date_range(start=datetime.now(), periods=days).strftime('%d.%m.%Y')
                        if date not in daily_forecasts
                    ]

                    if unavailable_dates:
                        start_date = unavailable_dates[0]
                        end_date = unavailable_dates[-1]
                        message += (
                            f"*С {start_date} по {end_date}:*\n\n_"
                            f"Данные недоступны из-за ограничений_\n\n"
                        )

                    if message == "*Прогноз на месяц:*\n\n":
                        message = "❌ Нет доступного прогноза на месяц!"

                    bot.send_message(chat_id, message, parse_mode="Markdown")
                    return
        bot.send_message(chat_id, "❌ Не удалось получить прогноз на месяц!")
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на месяц!\nПопробуйте позже")