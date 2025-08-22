from core.imports import wraps, telebot, types, os, json, re, requests, datetime, time, threading, schedule, ApiTelegramException
from core.bot_instance import bot, BASE_DIR
from core.config import OPENWEATHERMAP_API_KEY, WEATHERAPI_API_KEY, LOCATIONIQ_API_KEY
from .others_main import view_others
from .others_exchange import fetch_exchange_rates_cbr, CURRENCY_NAMES
from ..weather.weather import translate_weather_description
from ..fuel_prices.fuel_prices import parse_fuel_prices
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# --------------------------------------------- ПРОЧЕЕ (уведомления (погода + цены + курсы)) -----------------------------------------------

NOTIFICATIONS_PATH = os.path.join(BASE_DIR, 'data', 'user', 'notifications', 'notifications.json')
PAYMENTS_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'payments.json')
OPENWEATHERMAP_WEATHER_URL = 'http://api.openweathermap.org/data/2.5/weather'
OPENMETEO_FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
WEATHERAPI_CURRENT_URL = 'https://api.weatherapi.com/v1/current.json'
WEATHERAPI_FORECAST_URL = 'https://api.weatherapi.com/v1/forecast.json'

def load_payment_data():
    from handlers.user.user_main_menu import load_payment_data as _f
    return _f()

def load_blocked_users():
    from decorators.blocked_user import load_blocked_users as _f
    return _f()

def save_blocked_users(data):
    from decorators.blocked_user import save_blocked_users as _f
    return _f(data)

def ensure_directory_exists(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def ensure_directory_exists(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def has_active_subscription(chat_id):
    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(chat_id), {})
    if 'plans' not in user_data:
        return False
    for plan in user_data['plans']:
        try:
            end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
            if end_date > datetime.now():
                return True
        except (ValueError, KeyError):
            continue
    return False

def initialize_user_notifications(chat_id):
    ensure_directory_exists(NOTIFICATIONS_PATH)
    try:
        with open(NOTIFICATIONS_PATH, 'r', encoding='utf-8') as f:
            notifications = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        notifications = {}

    str_chat_id = str(chat_id)
    active_subscription = has_active_subscription(chat_id)
    
    default_notifications = {
        "weather": True if active_subscription else False,
        "fuel_prices": True if active_subscription else False,
        "exchange_rates": True if active_subscription else False
    }

    if str_chat_id not in notifications:
        notifications[str_chat_id] = {
            "latitude": None,
            "longitude": None,
            "city_code": None,
            "notifications": default_notifications
        }
    else:
        if "notifications" not in notifications[str_chat_id]:
            notifications[str_chat_id]["notifications"] = default_notifications
        else:
            for key in default_notifications:
                if key not in notifications[str_chat_id]["notifications"]:
                    notifications[str_chat_id]["notifications"][key] = default_notifications[key]

    with open(NOTIFICATIONS_PATH, 'w', encoding='utf-8') as f:
        json.dump(notifications, f, ensure_ascii=False, indent=4)

    return notifications

def save_user_location(chat_id, latitude, longitude, city_code):
    ensure_directory_exists(NOTIFICATIONS_PATH)
    notifications = initialize_user_notifications(chat_id)
    str_chat_id = str(chat_id)

    if latitude is not None:
        notifications[str_chat_id]["latitude"] = float(latitude)
    if longitude is not None:
        notifications[str_chat_id]["longitude"] = float(longitude)
    if city_code is not None:
        notifications[str_chat_id]["city_code"] = city_code

    try:
        with open(NOTIFICATIONS_PATH, 'w', encoding='utf-8') as f:
            json.dump(notifications, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_user_locations():
    ensure_directory_exists(NOTIFICATIONS_PATH)
    try:
        with open(NOTIFICATIONS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(NOTIFICATIONS_PATH, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        return {}

def toggle_notification(chat_id, notification_type):
    if not has_active_subscription(chat_id):
        return False
    ensure_directory_exists(NOTIFICATIONS_PATH)
    notifications = initialize_user_notifications(chat_id)
    user_notifications = notifications.get(str(chat_id), {}).get("notifications", {})

    if notification_type in user_notifications:
        user_notifications[notification_type] = not user_notifications[notification_type]
        notifications[str(chat_id)]["notifications"] = user_notifications
        with open(NOTIFICATIONS_PATH, 'w', encoding='utf-8') as f:
            json.dump(notifications, f, ensure_ascii=False, indent=4)
        return user_notifications[notification_type]
    return False

def get_notification_status(chat_id):
    notifications = load_user_locations()
    default_status = {
        "weather": False,
        "fuel_prices": False,
        "exchange_rates": False
    }
    if not has_active_subscription(chat_id):
        return default_status
    return notifications.get(str(chat_id), {}).get("notifications", default_status)

def get_notification_status_message(chat_id):
    status = get_notification_status(chat_id)
    weather_status = "включены" if status.get("weather", False) else "выключены"
    fuel_status = "включены" if status.get("fuel_prices", False) else "выключены"
    exchange_status = "включены" if status.get("exchange_rates", False) else "выключены"
    
    return f"📬 Текущий статус уведомлений:\n\n" \
           f"🌤️ Погода: {weather_status}\n" \
           f"⛽ Цены на топливо: {fuel_status}\n" \
           f"💱 Курсы валют: {exchange_status}\n\n"

@bot.message_handler(func=lambda message: message.text == "Уведомления")
@check_function_state_decorator('Уведомления')
@track_usage('Уведомления')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def toggle_notifications_handler(message, show_description=True):
    chat_id = message.chat.id
    initialize_user_notifications(chat_id)
    notification_status = get_notification_status(chat_id)

    weather_button_text = "Выключить погоду" if notification_status.get("weather") else "Включить погоду"
    fuel_button_text = "Выключить цены" if notification_status.get("fuel_prices") else "Включить цены"
    exchange_button_text = "Выключить курсы" if notification_status.get("exchange_rates") else "Включить курсы"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(types.KeyboardButton(weather_button_text), types.KeyboardButton(fuel_button_text), types.KeyboardButton(exchange_button_text))
    markup.add(types.KeyboardButton("Выключить все" if any(notification_status.values()) else "Включить все"))
    markup.add(types.KeyboardButton("Вернуться в прочее"))
    markup.add(types.KeyboardButton("В главное меню"))

    info_message = (
        "ℹ️ *Краткая справка по уведомлениям*\n\n"
        "📌 *Сохранение данных:*\n"
        "Ваши последние *координаты для погоды* и *последний введенный город* сохраняются для отправки уведомлений\n\n"
        "📌 *Переключение уведомлений:*\n"
        "Вы можете *включать* или *отключать* уведомления\n\n"
        "📌 *Получение уведомлений:*\n"
        "Вы получаете *актуальную информацию* в установленное время _(7:30, 13:00, 17:00)_\n"
    )

    if show_description:
        bot.send_message(chat_id, info_message, parse_mode="Markdown")

    status_message = get_notification_status_message(chat_id)
    bot.send_message(chat_id, status_message + "Выберите, какие уведомления включить или выключить:", 
                    reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in [
    "Включить погоду", "Выключить погоду", 
    "Включить цены", "Выключить цены", 
    "Включить курсы", "Выключить курсы", 
    "Включить все", "Выключить все"
])
@check_function_state_decorator('Включить погоду')
@check_function_state_decorator('Выключить погоду')
@check_function_state_decorator('Включить цены')
@check_function_state_decorator('Выключить цены')
@check_function_state_decorator('Включить курсы')
@check_function_state_decorator('Выключить курсы')
@check_function_state_decorator('Включить все')
@check_function_state_decorator('Выключить все')
@track_usage('Включить погоду')
@track_usage('Выключить погоду')
@track_usage('Включить цены')
@track_usage('Выключить цены')
@track_usage('Включить курсы')
@track_usage('Выключить курсы')
@track_usage('Включить все')
@track_usage('Выключить все')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_notification_toggle(message):
    chat_id = message.chat.id

    if message.text == 'Вернуться в прочее':
        view_others(message)
        return

    if not has_active_subscription(chat_id):
        bot.send_message(
            chat_id,
            "❌ Все уведомления отключены, так как у вас нет активной подписки!\n🚀 Чтобы включить уведомления, оформите подписку или обменяйте баллы!", parse_mode="Markdown")
        toggle_notifications_handler(message, show_description=False)
        return

    notification_messages = []
    if message.text == "Включить погоду":
        new_status = toggle_notification(chat_id, "weather")
        notification_messages.append(f"🌤️ Уведомления о погоде {'включены' if new_status else 'выключены'}!")
    elif message.text == "Выключить погоду":
        new_status = toggle_notification(chat_id, "weather")
        notification_messages.append(f"🌤️ Уведомления о погоде {'включены' if new_status else 'выключены'}!")
    elif message.text == "Включить цены":
        new_status = toggle_notification(chat_id, "fuel_prices")
        notification_messages.append(f"⛽ Уведомления о ценах на топливо {'включены' if new_status else 'выключены'}!")
    elif message.text == "Выключить цены":
        new_status = toggle_notification(chat_id, "fuel_prices")
        notification_messages.append(f"⛽ Уведомления о ценах на топливо {'включены' if new_status else 'выключены'}!")
    elif message.text == "Включить курсы":
        new_status = toggle_notification(chat_id, "exchange_rates")
        notification_messages.append(f"💱 Уведомления о курсах валют {'включены' if new_status else 'выключены'}!")
    elif message.text == "Выключить курсы":
        new_status = toggle_notification(chat_id, "exchange_rates")
        notification_messages.append(f"💱 Уведомления о курсах валют {'включены' if new_status else 'выключены'}!")
    elif message.text == "Включить все":
        notifications = initialize_user_notifications(chat_id)
        user_notifications = notifications[str(chat_id)]["notifications"]
        any_changed = False
        for key in user_notifications:
            if not user_notifications[key]:
                user_notifications[key] = True
                any_changed = True
        if any_changed:
            notifications[str(chat_id)]["notifications"] = user_notifications
            with open(NOTIFICATIONS_PATH, 'w', encoding='utf-8') as f:
                json.dump(notifications, f, ensure_ascii=False, indent=4)
            notification_messages.append("📬 Все уведомления включены!")
        else:
            notification_messages.append("📬 Все уведомления уже включены!")
    elif message.text == "Выключить все":
        notifications = initialize_user_notifications(chat_id)
        user_notifications = notifications[str(chat_id)]["notifications"]
        any_changed = False
        for key in user_notifications:
            if user_notifications[key]:
                user_notifications[key] = False
                any_changed = True
        if any_changed:
            notifications[str(chat_id)]["notifications"] = user_notifications
            with open(NOTIFICATIONS_PATH, 'w', encoding='utf-8') as f:
                json.dump(notifications, f, ensure_ascii=False, indent=4)
            notification_messages.append("📬 Все уведомления выключены!")
        else:
            notification_messages.append("📬 Все уведомления уже выключены!")

    if notification_messages:
        bot.send_message(chat_id, "\n".join(notification_messages), parse_mode="Markdown")

    toggle_notifications_handler(message, show_description=False)

def get_city_name(latitude, longitude):
    try:
        geocode_url = "https://eu1.locationiq.com/v1/reverse.php"
        params = {
            'key': LOCATIONIQ_API_KEY,
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'accept-language': 'ru'
        }
        response = requests.get(geocode_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if response.status_code == 200:
            city = data.get("address", {}).get("city", None)
            if city:
                return city
            town = data.get("address", {}).get("town", None)
            village = data.get("address", {}).get("village", None)
            return town or village or f"неизвестное место ({latitude}, {longitude})"
        return None
    except (requests.exceptions.RequestException, ValueError):
        pass

    try:
        time.sleep(1)
        url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json"
        headers = {'User-Agent': 'CarMngrBot/1.0 (google@gmail.com)'}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        address = data.get('address', {})
        city = address.get('city') or address.get('town') or address.get('village')
        return city or f"неизвестное место ({latitude}, {longitude})"
    except (requests.exceptions.RequestException, ValueError):
        return f"неизвестное место ({latitude}, {longitude})"

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
    except Exception:
        return None

def get_average_fuel_prices(city_code):
    fuel_prices = {}
    file_path = os.path.join(BASE_DIR, 'data', 'user', 'azs', f'{city_code}_table_azs_data.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            prices_data = json.load(f)
            for entry in prices_data:
                fuel_type = entry[1]
                price = entry[2]
                try:
                    price = float(price)
                except ValueError:
                    continue
                if fuel_type not in fuel_prices:
                    fuel_prices[fuel_type] = []
                fuel_prices[fuel_type].append(price)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    average_prices = {fuel: sum(prices) / len(prices) for fuel, prices in fuel_prices.items()}
    return average_prices

def get_exchange_rates_message():
    try:
        exchange_rates = fetch_exchange_rates_cbr()
        current_time = datetime.now().strftime("%d.%m.%Y в %H:%M")
        rates_message = f"*Актуальные курсы валют на {current_time}:*\n\n"
        
        for currency in CURRENCY_NAMES:
            if currency in exchange_rates:
                name, emoji = CURRENCY_NAMES[currency]
                rates_message += f"{emoji} *{name}:* {exchange_rates[currency]:.2f} руб.\n"
            else:
                name, emoji = CURRENCY_NAMES[currency]
                rates_message += f"{emoji} *{name}:* Н/Д\n"  
        
        return rates_message
    except Exception as e:
        return f"*Ошибка при получении курсов валют:* {str(e)}"
    
def load_city_names(file_path):
    city_names = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                city_data = line.strip().split(' - ')
                if len(city_data) == 2:
                    city_name, city_code = city_data
                    city_names[city_code] = city_name
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return city_names

def send_weather_notifications():
    user_locations = load_user_locations()
    city_names = load_city_names(os.path.join(BASE_DIR, 'files', 'files_for_price_weather', 'combined_cities.txt'))
    blocked_users = load_blocked_users()
    for chat_id, coords in user_locations.items():
        if chat_id in blocked_users or not has_active_subscription(chat_id):
            continue
        notification_status = get_notification_status(chat_id)
        messages = []
        if notification_status.get("weather"):
            weather_message = get_current_weather(coords)
            if weather_message:
                messages.append(weather_message)
        if notification_status.get("fuel_prices"):
            city_code = coords.get('city_code')
            city_name = city_names.get(city_code, city_code)
            average_prices = get_average_fuel_prices(city_code)
            current_time = datetime.now().strftime("%d.%m.%Y в %H:%M")
            if average_prices:
                fuel_prices_message = "*Актуальные цены на топливо (г. {}) на дату {}:*\n\n".format(city_name, current_time)
                fuel_types_order = [
                    "Аи-92", "Премиум 92", "Аи-95", "Премиум 95", "Аи-98", "Премиум 98",
                    "Аи-100", "Премиум 100", "ДТ", "Премиум ДТ", "Газ"
                ]
                for fuel_type in fuel_types_order:
                    if fuel_type in average_prices:
                        fuel_prices_message += f"⛽ *{fuel_type}:* {average_prices[fuel_type]:.2f} руб./л.\n"
                messages.append(fuel_prices_message)
        if notification_status.get("exchange_rates"):
            exchange_message = get_exchange_rates_message()
            if exchange_message:
                messages.append(exchange_message)
        if messages:
            try:
                final_message = "🔔 *Вам пришло новое уведомление!*\n\n" + "\n".join(messages)
                bot.send_message(chat_id, final_message, parse_mode="Markdown")
            except ApiTelegramException as e:
                if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                    if chat_id not in blocked_users:
                        blocked_users.append(chat_id)
                        save_blocked_users(blocked_users)
                else:
                    raise e

schedule.every().day.at("07:30").do(send_weather_notifications)
schedule.every().day.at("13:00").do(send_weather_notifications)
schedule.every().day.at("17:00").do(send_weather_notifications)

def schedule_tasks_together():
    while True:
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            parse_fuel_prices()
            time.sleep(60 * 5)
        schedule.run_pending()
        time.sleep(300)

threading.Thread(target=schedule_tasks_together, daemon=True).start()