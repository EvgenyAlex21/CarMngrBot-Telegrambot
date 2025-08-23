from core.imports import wraps, telebot, types, os, json, re, time, requests, threading, datetime, schedule, BeautifulSoup, Controller, Signal
from core.config import LOCATIONIQ_API_KEY
from core.imports import Signal as BlinkerSignal
from core.bot_instance import bot, BASE_DIR
from handlers.user.user_main_menu import return_to_menu
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription)
    
def save_user_location(chat_id, latitude, longitude, city_code):
    from handlers.user.others.others_notifications import save_user_location as _f
    return _f(chat_id, latitude, longitude, city_code)

def load_user_locations():
    from handlers.user.others.others_notifications import load_user_locations as _f
    return _f()

# --------------------------------------------------- ЦЕНЫ НА ТОПЛИВО ---------------------------------------------------------

CITYFORPRICE_DIR = os.path.join(BASE_DIR, "data", "user", "cityforprice")
AZS_DIR = os.path.join(BASE_DIR, "data", "user", "azs")
DATA_FILE_PATH = os.path.join(CITYFORPRICE_DIR, "city_for_the_price.json")
PROXY_FILE_PATH = os.path.join(BASE_DIR, "files", "files_for_price_weather", "proxy.txt")
TOR_BRIDGES_FILE_PATH = os.path.join(BASE_DIR, "files", "files_for_price_weather", "tor_most.txt")

for directory in [CITYFORPRICE_DIR, AZS_DIR]:
    os.makedirs(directory, exist_ok=True)

if not os.path.exists(DATA_FILE_PATH):
    try:
        with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
    except Exception:
        pass
if not os.path.exists(PROXY_FILE_PATH):
    try:
        with open(PROXY_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write("")
    except Exception as e:
        pass
if not os.path.exists(TOR_BRIDGES_FILE_PATH):
    try:
        with open(TOR_BRIDGES_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write("")
    except Exception as e:
        pass

if not os.path.exists(DATA_FILE_PATH):
    try:
        with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

user_state = {}
user_data = {}

def load_citys_users_data():
    global user_data
    try:
        with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        unique_user_data = {}
        for chat_id, data in raw_data.items():
            if chat_id not in unique_user_data:
                unique_user_data[chat_id] = {
                    'city_code': data.get('city_code'),
                    'site_type': data.get('site_type', 'default_site_type'),
                    'recent_cities': data.get('recent_cities', [])
                }
            else:
                existing_cities = unique_user_data[chat_id].get('recent_cities', [])
                new_cities = data.get('recent_cities', [])
                unique_user_data[chat_id]['recent_cities'] = list(set(existing_cities + new_cities))
                if data.get('city_code'):
                    unique_user_data[chat_id]['city_code'] = data['city_code']

        user_data = unique_user_data
        save_citys_users_data()  
    except (FileNotFoundError, json.JSONDecodeError):
        user_data = {}
        save_citys_users_data()
    except Exception as e:
        user_data = {}

def save_citys_users_data():
    try:
        with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        pass
    
load_citys_users_data()

def create_filename(city_code, date):
    date_str = date.strftime('%d_%m_%Y')
    return f"{city_code}_table_azs_data_{date_str}.json"

def save_fuel_data(city_code, fuel_prices):
    filename = f'{city_code}_table_azs_data.json'
    filepath = os.path.join(AZS_DIR, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(fuel_prices, f, ensure_ascii=False, indent=4)

def load_saved_data(city_code):
    filename = f'{city_code}_table_azs_data.json'
    filepath = os.path.join(BASE_DIR, 'data', 'user', 'azs', filename)

    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f) 
    except (FileNotFoundError, json.JSONDecodeError):
        return None

cities_file_path = os.path.join(BASE_DIR, 'files', 'files_for_price_weather', 'combined_cities.txt')

def load_cities():
    cities = {}
    try:
        with open(cities_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '-' in line:
                    city, city_code = line.strip().split(' - ')
                    cities[city.lower()] = city_code
    except (FileNotFoundError, Exception):
        pass
    return cities

cities_dict = load_cities()

def get_city_code(city_name):
    return cities_dict.get(city_name.lower())

def load_proxies():
    proxies = []
    try:
        with open(PROXY_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                proxy = line.strip()
                if proxy:
                    proxies.append(proxy)
    except FileNotFoundError:
        pass
    return proxies

def load_tor_bridges():
    bridges = []
    try:
        with open(TOR_BRIDGES_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                bridge = line.strip()
                if bridge and bridge.startswith('obfs4'):
                    bridges.append(bridge)
    except FileNotFoundError:
        print(f"Файл {TOR_BRIDGES_FILE_PATH} не найден.")
    except Exception as e:
        print(f"Ошибка при загрузке мостов: {e}")
    return bridges

@bot.message_handler(func=lambda message: message.text == "Цены на топливо")
@check_function_state_decorator('Цены на топливо')
@track_usage('Цены на топливо')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def fuel_prices_command(message, show_description=True):
    chat_id = message.chat.id
    load_citys_users_data()
    user_state[chat_id] = "choosing_city"

    str_chat_id = str(chat_id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    if str_chat_id in user_data and 'recent_cities' in user_data[str_chat_id]:
        recent_cities = user_data[str_chat_id]['recent_cities']
        city_buttons = [types.KeyboardButton(city.capitalize()) for city in recent_cities]
        markup.row(*city_buttons)

    markup.add(types.KeyboardButton("Отправить геопозицию", request_location=True))
    markup.add(types.KeyboardButton("В главное меню"))

    reference_info = (
        "ℹ️ *Краткая справка по ценам на топливо*\n\n"
        "📌 *Город:* Вводится *город* или отправляется *геопозиция* для получения актуальных средних цен на топливо разных марок АЗС\n\n"
        "📌 *Тип:* Выбирается тип топлива *(АИ-92, АИ-95, АИ-98, АИ-100, ДТ, ГАЗ)*\n\n"
        "📌 *Цены:* *Получение цен* на нужный вид топлива *в выбранном городе*\n\n"
        "_P.S. Данная функция может работать некорректно из-за хостинга или серверов telegram. "
        "Цены обновляются 1 раз в сутки. Если ваш город не найден или таблица с ценами для города отсутствует, "
        "то проверяем другие, например г. Москва или г. Чебоксары, и если данные будут доступны для этих городов, "
        "то следует обратиться к администратору (разработчику) для устранения вашей проблемы!_"
    )

    if show_description:
        bot.send_message(chat_id, reference_info, parse_mode='Markdown')

    bot.send_message(chat_id, "Введите город, выберите из последних или отправьте геопозицию:", reply_markup=markup)
    bot.register_next_step_handler(message, process_city_selection)

def get_city_from_coordinates(latitude, longitude):
    time.sleep(1) 
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json"
        headers = {
            'User-Agent': 'CarMngrBot/1.0 (google@gmail.com)'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        address = data.get('address', {})
        city = address.get('city') or address.get('town') or address.get('village')
        return city
    except Exception as e:
        return None

def geocode_city_to_coords(city_name: str):
    if not city_name:
        return None, None
    if LOCATIONIQ_API_KEY:
        try:
            params = {
                'key': LOCATIONIQ_API_KEY,
                'q': city_name,
                'format': 'json',
                'limit': 1,
                'accept-language': 'ru'
            }
            r = requests.get('https://eu1.locationiq.com/v1/search.php', params=params, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and data:
                    return float(data[0]['lat']), float(data[0]['lon'])
        except Exception:
            pass
    try:
        params = {'q': city_name, 'format': 'json', 'limit': 1}
        headers = {'User-Agent': 'CarMngrBot/1.0'}
        r = requests.get('https://nominatim.openstreetmap.org/search', params=params, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        pass
    return None, None

@text_only_handler
def process_city_selection(message):
    chat_id = message.chat.id
    str_chat_id = str(chat_id)

    if message.text and message.text == "В главное меню":
        return_to_menu(message)
        return

    if user_state.get(chat_id) != "choosing_city":
        bot.send_message(chat_id, "Пожалуйста, используйте доступные кнопки для навигации")
        return

    city_name = None
    city_code = None

    incoming_text = (message.text or "").strip().lower() if hasattr(message, 'text') else ""

    latitude = None
    longitude = None
    if message.location:
        latitude = message.location.latitude
        longitude = message.location.longitude
        city_name_detected = get_city_from_coordinates(latitude, longitude)
        if not city_name_detected:
            bot.send_message(chat_id, "Не удалось определить город по вашей геопозиции!\nПожалуйста, введите город вручную")
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
            recent_cities = user_data.get(str_chat_id, {}).get('recent_cities', [])
            if recent_cities:
                markup.add(*[types.KeyboardButton(city.title()) for city in recent_cities])
            markup.add(types.KeyboardButton("Отправить геопозицию", request_location=True))
            markup.add(types.KeyboardButton("В главное меню"))
            bot.send_message(chat_id, "Введите город, выберите из последних или отправьте геопозицию:", reply_markup=markup)
            bot.register_next_step_handler(message, process_city_selection)
            return
        city_name = city_name_detected.lower()
        city_code = get_city_code(city_name)
    else:
        if not incoming_text:
            bot.send_message(chat_id, "⛔️ Извините, но отправка мультимедийных файлов не разрешена! Пожалуйста, введите текстовое сообщение...")
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
            recent_cities = user_data.get(str_chat_id, {}).get('recent_cities', [])
            if recent_cities:
                markup.add(*[types.KeyboardButton(city.title()) for city in recent_cities])
            markup.add(types.KeyboardButton("Отправить геопозицию", request_location=True))
            markup.add(types.KeyboardButton("В главное меню"))
            bot.send_message(chat_id, "Введите город, выберите из последних или отправьте геопозицию:", reply_markup=markup)
            bot.register_next_step_handler(message, process_city_selection)
            return
        city_name = incoming_text
        city_code = get_city_code(city_name)
    latitude, longitude = geocode_city_to_coords(city_name)

    if not city_code:
        bot.send_message(chat_id, f"Город {city_name.capitalize()} не найден!\nПожалуйста, проверьте правильность написания и попробуйте еще раз")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        recent_cities = user_data.get(str_chat_id, {}).get('recent_cities', [])
        if recent_cities:
            markup.add(*[types.KeyboardButton(city.title()) for city in recent_cities])
        markup.add(types.KeyboardButton("Отправить геопозицию", request_location=True))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(chat_id, "Введите город, выберите из последних или отправьте геопозицию:", reply_markup=markup)
        bot.register_next_step_handler(message, process_city_selection)
        return

    if str_chat_id not in user_data:
        user_data[str_chat_id] = {
            'recent_cities': [],
            'city_code': city_code,
            'site_type': 'default_site_type'
        }
    else:
        user_data[str_chat_id]['city_code'] = city_code
        if 'site_type' not in user_data[str_chat_id]:
            user_data[str_chat_id]['site_type'] = 'default_site_type'

    update_recent_cities(str_chat_id, city_name)
    save_citys_users_data()

    if latitude is None or longitude is None:
        lat_tmp, lon_tmp = geocode_city_to_coords(city_name)
        if lat_tmp is not None and lon_tmp is not None:
            latitude, longitude = lat_tmp, lon_tmp
    save_user_location(chat_id, latitude, longitude, city_code)

    site_type = user_data[str_chat_id]['site_type']
    show_fuel_price_menu(chat_id, city_code, site_type)

def update_recent_cities(chat_id, city_name):
    if chat_id not in user_data:
        user_data[chat_id] = {
            'recent_cities': [],
            'city_code': None,
            'site_type': 'default_site_type'
        }

    recent_cities = user_data[chat_id].get('recent_cities', [])

    if city_name in recent_cities:
        recent_cities.remove(city_name)
    
    recent_cities.append(city_name)

    if len(recent_cities) > 3:
        recent_cities = recent_cities[-3:]

    user_data[chat_id]['recent_cities'] = recent_cities
    save_citys_users_data()

fuel_types = ["АИ-92", "АИ-95", "АИ-98", "АИ-100", "ДТ", "Газ"]

def show_fuel_price_menu(chat_id, city_code, site_type):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    row1 = [types.KeyboardButton(fuel_type) for fuel_type in fuel_types[:3]]
    row2 = [types.KeyboardButton(fuel_type) for fuel_type in fuel_types[3:]]
    row3 = [types.KeyboardButton("Выбрать другой город")]
    row4 = [types.KeyboardButton("В главное меню")]
    markup.add(*row1, *row2)
    markup.add(*row3)
    markup.add(*row4)
    sent = bot.send_message(chat_id, "Выберите тип топлива для отображения актуальных цен:", reply_markup=markup)
    bot.register_next_step_handler(sent, lambda msg: process_fuel_price_selection(msg, city_code, site_type))

progress = 0
progress_lock = threading.Lock()
processing_complete = False  

def update_progress(chat_id, message_id, bot, start_time):
    global progress, processing_complete
    while True:
        time.sleep(1)
        elapsed_time = time.time() - start_time
        with progress_lock:
            if processing_complete:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"✅ Обработка завершена!\n\nВыполнено: 100%\nПрошло времени: {elapsed_time:.2f} секунд"
                )
                break
            current_progress = min(progress, 99)  
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"⚠️ Данные обрабатываются... Ожидайте, никуда не выходите!\n\nВыполнено: {current_progress:.2f}%\nПрошло времени: {elapsed_time:.2f} секунд"
        )

@text_only_handler
def process_fuel_price_selection(message, city_code, site_type):
    global progress, processing_complete
    chat_id = message.chat.id

    if chat_id not in user_data:
        user_data[chat_id] = {'city_code': city_code, 'site_type': site_type}

    if message.text and message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text and message.text == "Выбрать другой город":
        user_state[chat_id] = "choosing_city"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        recent_cities = user_data.get(str(chat_id), {}).get('recent_cities', [])
        city_buttons = [types.KeyboardButton(city.capitalize()) for city in recent_cities]
        if city_buttons:
            markup.row(*city_buttons)
        markup.add(types.KeyboardButton("Отправить геопозицию", request_location=True))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(chat_id, "Введите город, выберите из последних или отправьте геопозицию:", reply_markup=markup)
        bot.register_next_step_handler(message, process_city_selection)
        return

    if not message.text:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите тип топлива из предложенных вариантов!")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        row1 = [types.KeyboardButton(fuel_type) for fuel_type in fuel_types[:3]]
        row2 = [types.KeyboardButton(fuel_type) for fuel_type in fuel_types[3:]]
        row3 = [types.KeyboardButton("Выбрать другой город")]
        row4 = [types.KeyboardButton("В главное меню")]
        markup.add(*row1, *row2)
        markup.add(*row3)
        markup.add(*row4)
        bot.send_message(chat_id, "Выберите тип топлива для отображения актуальных цен:", reply_markup=markup)
        bot.register_next_step_handler(sent, lambda msg: process_fuel_price_selection(msg, city_code, site_type))
        return

    selected_fuel_type = message.text.strip().lower()

    fuel_type_mapping = {
        "аи-92": ["АИ-92", "Премиум 92"],
        "аи-95": ["АИ-95", "Премиум 95"],
        "аи-98": ["АИ-98", "Премиум 98"],
        "аи-100": ["АИ-100", "Премиум 100"],
        "дт": ["ДТ", "Премиум ДТ"],
        "газ": ["Газ", "Газ СПБТ"],
    }

    if selected_fuel_type not in fuel_type_mapping:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите тип топлива из предложенных вариантов!")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        row1 = [types.KeyboardButton(fuel_type) for fuel_type in fuel_types[:3]]
        row2 = [types.KeyboardButton(fuel_type) for fuel_type in fuel_types[3:]]
        row3 = [types.KeyboardButton("Выбрать другой город")]
        row4 = [types.KeyboardButton("В главное меню")]
        markup.add(*row1, *row2)
        markup.add(*row3)
        markup.add(*row4)
        bot.send_message(chat_id, "Выберите тип топлива для отображения актуальных цен:", reply_markup=markup)
        bot.register_next_step_handler(sent, lambda msg: process_fuel_price_selection(msg, city_code, site_type))
        return

    actual_fuel_types = fuel_type_mapping[selected_fuel_type]

    progress_message = bot.send_message(chat_id, "⚠️ Данные обрабатываются... Ожидайте, никуда не выходите!")
    message_id = progress_message.message_id

    start_time = time.time()
    progress = 0
    processing_complete = False  
    progress_thread = threading.Thread(target=update_progress, args=(chat_id, message_id, bot, start_time))
    progress_thread.start()

    try:
        fuel_prices = []
        total_steps = len(actual_fuel_types) * 2
        current_step = 0

        saved_data = load_saved_data(city_code)
        today = datetime.now().date()

        if saved_data:
            file_modification_time = datetime.fromtimestamp(
                os.path.getmtime(os.path.join(BASE_DIR, 'data', 'user', 'azs', f"{city_code}_table_azs_data.json"))
            ).date()
            if file_modification_time >= today:
                print(f"Данные для города {city_code} уже обновлены сегодня. Пропускаем парсинг...")
                fuel_prices = [
                    item for item in saved_data
                    if item[1].lower() in [ft.lower() for ft in actual_fuel_types]
                ]
                with progress_lock:
                    progress = 90  
            else:
                for fuel_type in actual_fuel_types:
                    try:
                        print(f"Пытаемся получить данные с сайта AZCPRICE для города {city_code} и типа топлива {fuel_type}")
                        fuel_prices.extend(get_fuel_prices_from_site(city_code, "azcprice"))
                        current_step += 1
                    except ValueError:
                        try:
                            print(f"Сайт AZCPRICE недоступен. Пытаемся получить данные с сайта petrolplus для города {city_code} и типа топлива {fuel_type}")
                            fuel_prices.extend(get_fuel_prices_from_site(city_code, "petrolplus"))
                            current_step += 1
                        except ValueError:
                            print(f"Оба сайта недоступны для города {city_code} и типа топлива {fuel_type}")
                            current_step += 1

                    with progress_lock:
                        progress = (current_step / total_steps) * 90  

                save_fuel_data(city_code, fuel_prices)
        else:
            for fuel_type in actual_fuel_types:
                try:
                    print(f"Пытаемся получить данные с сайта AZCPRICE для города {city_code} и типа топлива {fuel_type}")
                    fuel_prices.extend(get_fuel_prices_from_site(city_code, "azcprice"))
                    current_step += 1
                except ValueError:
                    try:
                        print(f"Сайт AZCPRICE недоступен. Пытаемся получить данные с сайта petrolplus для города {city_code} и типа топлива {fuel_type}")
                        fuel_prices.extend(get_fuel_prices_from_site(city_code, "petrolplus"))
                        current_step += 1
                    except ValueError:
                        print(f"Оба сайта недоступны для города {city_code} и типа топлива {fuel_type}")
                        current_step += 1

                with progress_lock:
                    progress = (current_step / total_steps) * 90  

            save_fuel_data(city_code, fuel_prices)

        if not fuel_prices:
            raise ValueError("Нет данных по ценам!")

        fuel_prices = [
            item for item in fuel_prices
            if item[1].lower() in [ft.lower() for ft in actual_fuel_types]
        ]

        brand_prices = {}
        for brand, fuel_type, price in fuel_prices:
            price = float(price)
            brand_name = brand.split(' №')[0]
            if brand_name not in brand_prices:
                brand_prices[brand_name] = []
            brand_prices[brand_name].append((fuel_type, price))

        normal_prices = {brand: [price for fuel_type, price in prices if 'Премиум' not in fuel_type] for brand, prices in brand_prices.items()}
        premium_prices = {brand: [price for fuel_type, price in prices if 'Премиум' in fuel_type] for brand, prices in brand_prices.items()}

        normal_prices = {brand: prices for brand, prices in normal_prices.items() if prices}
        premium_prices = {brand: prices for brand, prices in premium_prices.items() if prices}

        averaged_normal_prices = {brand: sum(prices) / len(prices) for brand, prices in normal_prices.items()}
        averaged_premium_prices = {brand: sum(prices) / len(prices) for brand, prices in premium_prices.items()}

        sorted_normal_prices = sorted(averaged_normal_prices.items(), key=lambda x: x[1])
        sorted_premium_prices = sorted(averaged_premium_prices.items(), key=lambda x: x[1])

        readable_fuel_type = selected_fuel_type.upper()

        normal_prices_message = "\n\n".join([f"⛽ {i + 1}. {brand} - {avg_price:.2f} руб./л." for i, (brand, avg_price) in enumerate(sorted_normal_prices)])
        premium_prices_message = "\n\n".join([f"⛽ {i + 1}. {brand} - {avg_price:.2f} руб./л." for i, (brand, avg_price) in enumerate(sorted_premium_prices)])

        max_length = 4000
        normal_parts = [normal_prices_message[i:i + max_length] for i in range(0, len(normal_prices_message), max_length)]
        premium_parts = [premium_prices_message[i:i + max_length] for i in range(0, len(premium_prices_message), max_length)]

        with progress_lock:
            progress = 100
            processing_complete = True 

        if normal_parts:
            for i, part in enumerate(normal_parts):
                if i == 0:
                    bot.send_message(chat_id, f"*Актуальные цены на {readable_fuel_type}:*\n\n{part}", parse_mode="Markdown")
                else:
                    bot.send_message(chat_id, part, parse_mode="Markdown")

        if premium_parts:
            for i, part in enumerate(premium_parts):
                if i == 0:
                    bot.send_message(chat_id, f"*Актуальные цены на {readable_fuel_type} Премиум:*\n\n{part}", parse_mode="Markdown")
                else:
                    bot.send_message(chat_id, part, parse_mode="Markdown")

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        another_fuel_button = types.KeyboardButton("Посмотреть цены на другое топливо")
        choose_another_city_button = types.KeyboardButton("Выбрать другой город")
        main_menu_button = types.KeyboardButton("В главное меню")
        markup.add(another_fuel_button)
        markup.add(choose_another_city_button)
        markup.add(main_menu_button)

        user_state[chat_id] = "next_action"
        sent = bot.send_message(chat_id, "Вы можете посмотреть цены на другое топливо или выбрать другой город:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_next_action)

    except Exception as e:
        with progress_lock:
            progress = 100
            processing_complete = True 

        bot.send_message(chat_id, "❌ Ошибка получения цен!\n\nНе найдена таблица с ценами...\n\nПопробуйте выбрать другой город или тип топлива!")
        show_fuel_price_menu(chat_id, city_code, site_type)
        return
    
def process_next_action(message):
    chat_id = message.chat.id
    text = message.text.strip().lower()

    if text == "выбрать другой город":
        user_state[chat_id] = "choosing_city"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        recent_cities = user_data.get(str(chat_id), {}).get('recent_cities', [])
        city_buttons = [types.KeyboardButton(city.capitalize()) for city in recent_cities]
        if city_buttons:
            markup.row(*city_buttons)
        markup.add(types.KeyboardButton("Отправить геопозицию", request_location=True))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(chat_id, "Введите город, выберите из последних или отправьте геопозицию:", reply_markup=markup)
        bot.register_next_step_handler(message, process_city_selection)

    elif text == "посмотреть цены на другое топливо":
        city_code = user_data[str(chat_id)]['city_code']
        site_type = "default_site_type"
        show_fuel_price_menu(chat_id, city_code, site_type)

    elif text == "в главное меню":
        return_to_menu(message)

    else:
        bot.send_message(chat_id, "Пожалуйста, выберите одно из предложенных действий")
        bot.register_next_step_handler(message, process_next_action)

def process_city_fuel_data(city_code, selected_fuel_type, site_type, actual_fuel_types):
    today = datetime.now().date()
    saved_data = load_saved_data(city_code)

    filepath = os.path.join(BASE_DIR, 'data', 'user', 'azs', f"{city_code}_table_azs_data.json")
    if saved_data:
        file_modification_time = datetime.fromtimestamp(os.path.getmtime(filepath)).date()
        if file_modification_time < today:
            all_fuel_prices = []
            for fuel_type in actual_fuel_types:
                try:
                    print(f"Пытаемся получить данные с сайта AZCPRICE для города {city_code} и типа топлива {fuel_type}")
                    fuel_prices = get_fuel_prices_from_site(city_code, "azcprice")
                except ValueError:
                    try:
                        print(f"Сайт AZCPRICE недоступен. Пытаемся получить данные с сайта petrolplus для города {city_code} и типа топлива {fuel_type}")
                        fuel_prices = get_fuel_prices_from_site(city_code, "petrolplus")
                    except ValueError:
                        print(f"Оба сайта недоступны для города {city_code} и типа топлива {fuel_type}")
                        if saved_data:
                            return [
                                item for item in saved_data
                                if item[1].lower() in [ft.lower() for ft in actual_fuel_types]
                            ]
                        raise ValueError("❌ Ошибка получения цен!\n\nНе найдена таблица с ценами...\n\nПопробуйте выбрать другой город или тип топлива!")

                fuel_prices = remove_duplicate_prices(fuel_prices)
                all_fuel_prices.extend(fuel_prices)

            save_fuel_data(city_code, all_fuel_prices)
            saved_data = all_fuel_prices

    if not saved_data:
        all_fuel_prices = []
        for fuel_type in actual_fuel_types:
            try:
                print(f"Пытаемся получить данные с сайта AZCPRICE для города {city_code} и типа топлива {fuel_type}")
                fuel_prices = get_fuel_prices_from_site(city_code, "azcprice")
            except ValueError:
                try:
                    print(f"Сайт AZCPRICE недоступен. Пытаемся получить данные с сайта petrolplus для города {city_code} и типа топлива {fuel_type}")
                    fuel_prices = get_fuel_prices_from_site(city_code, "petrolplus")
                except ValueError:
                    print(f"Оба сайта недоступны для города {city_code} и типа топлива {fuel_type}")
                    raise ValueError("❌ Ошибка получения цен!\n\nНе найдена таблица с ценами...\n\nПопробуйте выбрать другой город или тип топлива!")

            fuel_prices = remove_duplicate_prices(fuel_prices)
            all_fuel_prices.extend(fuel_prices)

        save_fuel_data(city_code, all_fuel_prices)
        saved_data = all_fuel_prices

    filtered_prices = [
        item for item in saved_data
        if item[1].lower() in [ft.lower() for ft in actual_fuel_types]
    ]
    return remove_duplicate_prices(filtered_prices)

def remove_duplicate_prices(fuel_prices):
    unique_prices = {}
    for brand, fuel_type, price in fuel_prices:
        price = float(price)
        key = (brand, fuel_type)
        if key not in unique_prices or price < unique_prices[key]:
            unique_prices[key] = price
    return [(brand, fuel_type, price) for (brand, fuel_type), price in unique_prices.items()]

def renew_tor_circuit():
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            time.sleep(5)  
            print("Цепочка Tor успешно переключена.")
    except Exception as e:
        print(f"Ошибка при переключении цепочки Tor: {e}")

def get_fuel_prices_from_site(city_code, site_type, proxies=None, retry_count=1):
    headers = {
        'User-Agent': 'CarMngrBot/1.0 (google@gmail.com)'
    }
    
    def parse_table(soup, site_type):
        fuel_prices = []
        table = soup.find('table')
        if not table:
            raise ValueError("Не найдена таблица с ценами")
        
        if site_type == "azcprice":
            rows = table.find_all('tr')
            for row in rows[1:]:
                columns = row.find_all('td')
                if len(columns) < 5:
                    continue
                brand = columns[1].text.strip()
                fuel_type = columns[2].text.strip()
                today_price = clean_price(columns[3].text.strip())
                if fuel_type == "Газ СПБТ":
                    fuel_type = "Газ"
                fuel_prices.append((brand, fuel_type, today_price))
        
        elif site_type == "petrolplus":
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    brand = cols[1].text.strip()
                    fuel_types = [ft.strip() for ft in cols[2].stripped_strings]
                    prices = [p.strip().replace(',', '.') for p in cols[3].stripped_strings]
                    for fuel_type, price in zip(fuel_types, prices):
                        if fuel_type == "Газ СПБТ":
                            fuel_type = "Газ"
                        fuel_prices.append((brand, fuel_type, clean_price(price)))
        
        return fuel_prices

    try:
        if site_type == "azcprice":
            url = f'https://fuelprice.ru/t-{city_code}'
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return parse_table(soup, site_type)
        
        elif site_type == "petrolplus":
            base_url = f'https://www.petrolplus.ru/fuelstations/{city_code}/?PAGEN_='
            page = 1
            all_fuel_prices = []
            while True:
                url = f'{base_url}{page}'
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table')
                if not table:
                    break
                all_fuel_prices.extend(parse_table(soup, site_type))
                page += 1
            return all_fuel_prices

    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Ошибка при парсинге с текущего IP для {site_type}: {e}")

        if proxies:
            for proxy in proxies:
                try:
                    proxy_dict = {
                        'http': proxy,
                        'https': proxy,
                        'socks4': proxy,
                        'socks5': proxy
                    }
                    print(f"Попытка через прокси: {proxy}")
                    if site_type == "azcprice":
                        url = f'https://fuelprice.ru/t-{city_code}'
                        response = requests.get(url, headers=headers, proxies=proxy_dict, timeout=10)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.text, 'html.parser')
                        return parse_table(soup, site_type)
                    
                    elif site_type == "petrolplus":
                        base_url = f'https://www.petrolplus.ru/fuelstations/{city_code}/?PAGEN_='
                        page = 1
                        all_fuel_prices = []
                        while True:
                            url = f'{base_url}{page}'
                            response = requests.get(url, headers=headers, proxies=proxy_dict, timeout=10)
                            response.raise_for_status()
                            soup = BeautifulSoup(response.text, 'html.parser')
                            table = soup.find('table')
                            if not table:
                                break
                            all_fuel_prices.extend(parse_table(soup, site_type))
                            page += 1
                        return all_fuel_prices

                except (requests.exceptions.RequestException, ValueError) as proxy_error:
                    print(f"Ошибка при использовании прокси {proxy} для {site_type}: {proxy_error}")
                    continue

        print(f"Попытка через Tor для {site_type}...")
        try:
            renew_tor_circuit()
            if site_type == "azcprice":
                url = f'https://fuelprice.ru/t-{city_code}'
                response = requests.get(url, headers=headers, timeout=10) 
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                return parse_table(soup, site_type)
            
            elif site_type == "petrolplus":
                base_url = f'https://www.petrolplus.ru/fuelstations/{city_code}/?PAGEN_='
                page = 1
                all_fuel_prices = []
                while True:
                    url = f'{base_url}{page}'
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    table = soup.find('table')
                    if not table:
                        break
                    all_fuel_prices.extend(parse_table(soup, site_type))
                    page += 1
                return all_fuel_prices

        except (requests.exceptions.RequestException, ValueError) as tor_error:
            print(f"Ошибка при использовании Tor для {site_type}: {tor_error}")

            if retry_count > 0:
                print(f"Повторная попытка ({retry_count}) через 5 секунд...")
                time.sleep(5)
                return get_fuel_prices_from_site(city_code, site_type, proxies, retry_count - 1)
            else:
                raise ValueError("❌ Ошибка получения цен!\n\nНе найдена таблица с ценами...\n\nПопробуйте выбрать другой город или тип топлива!")
            
def clean_price(price):
    cleaned_price = ''.join([ch for ch in price if ch.isdigit() or ch == '.'])
    return cleaned_price

def parse_fuel_prices():
    cities_to_parse = os.listdir(os.path.join(BASE_DIR, 'data', 'user', 'azs'))
    for city_code in cities_to_parse:
        city_code = city_code.replace('_table_azs_data.json', '')
        saved_data = load_saved_data(city_code)

        today = datetime.now().date()
        if saved_data:
            file_modification_time = datetime.fromtimestamp(
                os.path.getmtime(os.path.join(BASE_DIR, 'data', 'user', 'azs', f"{city_code}_table_azs_data.json"))
            ).date()
            if file_modification_time >= today:
                print(f"Данные для города {city_code} уже обновлены сегодня. Пропускаем.")
                continue

        all_fuel_prices = []
        for fuel_type in fuel_types:
            try:
                fuel_prices = get_fuel_prices_from_site(city_code, "azcprice")
            except ValueError:
                try:
                    fuel_prices = get_fuel_prices_from_site(city_code, "petrolplus")
                except ValueError:
                    print(f"Оба сайта недоступны для города {city_code}")
                    continue

            fuel_prices = remove_duplicate_prices(fuel_prices)
            all_fuel_prices.extend(fuel_prices)

        print(f"Сохранение данных для города {city_code} с {len(all_fuel_prices)} записями.")
        save_fuel_data(city_code, all_fuel_prices)
        print(f"Данные для города {city_code} успешно обновлены.")

def parse_fuel_prices_scheduled():
    proxies = load_proxies()
    bridges = load_tor_bridges() 
    cities_to_parse = os.listdir(os.path.join(BASE_DIR, 'data', 'user', 'azs'))
    
    for i, city_code in enumerate(cities_to_parse):
        city_code = city_code.replace('_table_azs_data.json', '')
        saved_data = load_saved_data(city_code)

        today = datetime.now().date()
        if saved_data:
            file_modification_time = datetime.fromtimestamp(
                os.path.getmtime(os.path.join(BASE_DIR, 'data', 'user', 'azs', f"{city_code}_table_azs_data.json"))
            ).date()
            if file_modification_time >= today:
                print(f"Данные для города {city_code} уже обновлены сегодня. Пропускаем.")
                continue

        all_fuel_prices = []
        for fuel_type in fuel_types:
            try:
                fuel_prices = get_fuel_prices_from_site(city_code, "azcprice", proxies=proxies)
            except ValueError:
                try:
                    fuel_prices = get_fuel_prices_from_site(city_code, "petrolplus", proxies=proxies)
                except ValueError:
                    print(f"Оба сайта недоступны для города {city_code}")
                    continue

            fuel_prices = remove_duplicate_prices(fuel_prices)
            all_fuel_prices.extend(fuel_prices)

        print(f"Сохранение данных для города {city_code} с {len(all_fuel_prices)} записями.")
        save_fuel_data(city_code, all_fuel_prices)
        print(f"Данные для города {city_code} успешно обновлены.")
        
        if i < len(cities_to_parse) - 1: 
            time.sleep(300)  

def schedule_tasks_for_azs():
    schedule.every().day.at("00:00").do(parse_fuel_prices_scheduled)
    while True:
        schedule.run_pending()
        time.sleep(60)

threading.Thread(target=schedule_tasks_for_azs, daemon=True).start()