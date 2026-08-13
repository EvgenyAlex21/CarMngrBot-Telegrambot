from core.imports import wraps, telebot, requests, types, ReadTimeoutError
from core.bot_instance import bot, BASE_DIR
from handlers.user.user_main_menu import return_to_menu
from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ------------------------------------------------- НАЙТИ БЕНЗ --------------------------------------------------

RADIUS_KM = 20         
MAX_STATIONS = 25       

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

STATUS_MAP = {
    "yes":   "🟢 Есть — шансы найти бензин есть",
    "low":   "🟡 Ограничено — мало / лимиты / выборочно",
    "queue": "🟡 Очередь — бензин есть, но ждать",
    "no":    "🚫 Пусто — топлива нет / не работает",
    None:    "❔ Нет свежих отметок",
}

user_states = {}

def search_city(query: str):
    try:
        r = requests.get(
            "https://gdebenz.ru/api/cities",
            params={"q": query},
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("results") or []
    except Exception as e:
        print("city search error:", e)
        return []

def get_stations(lat: float, lon: float, radius_km: float = 20):
    try:
        r = requests.get(
            "https://gdebenz.ru/api/nearby",
            params={
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "radius_km": radius_km,
                "full": 1,
            },
            headers=HEADERS,
            timeout=12,
            allow_redirects=True,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("stations") or []
    except Exception as e:
        print("stations error:", e)
        return []

def is_target_brand(brand: str) -> bool:
    if not brand:
        return False
    b = brand.lower().replace("ё", "е")
    return "лукойл" in b or "татнефть" in b

def format_station(s: dict) -> str:
    brand = s.get("brand") or ""
    name = s.get("name") or brand or "АЗС"
    if brand and brand not in name:
        title = f"{brand} — {name}"
    else:
        title = name

    addr = s.get("addr") or "адрес не указан"
    status = s.get("status")
    status_text = STATUS_MAP.get(status, f"❔ {status}")
    detail = (s.get("detail") or "").strip()
    fuels = (s.get("fuels_now") or "").strip()
    conf = s.get("confirmations") or 0
    last = s.get("last_at") or ""
    dist = s.get("distance_km")

    lines = [
        f"<b>{title}</b>",
        f"📍 {addr}",
    ]

    if dist is not None:
        lines.append(f"📏 ~{dist} км")

    if fuels:
        lines.append(f"⛽ Топливо сейчас: <b>{fuels}</b>")
    else:
        lines.append("⛽ Топливо: нет данных")

    lines.append(status_text)

    if detail:
        lines.append(f"ℹ️ {detail}")

    if last:
        lines.append(f"🕐 {last} · подтверждений: {conf}")

    return "\n".join(lines)

@bot.message_handler(func=lambda message: message.text == "Найти бенз")
@check_function_state_decorator('Найти бенз')
@track_usage('Найти бенз')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def start_fuel_search(message):
    chat_id = message.chat.id
    user_states[chat_id] = {'in_search': True}
    
    text = (
        "🔍 <b>Поиск бензина на Лукойл и Татнефть</b>\n\n"
        "Просто напиши название города (например: <code>Чебоксары</code>, <code>Казань</code>, <code>Уфа</code>)"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('В главное меню')
    
    msg = bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
    bot.register_next_step_handler(msg, handle_city_input)

@text_only_handler
def handle_city_input(message):
    chat_id = message.chat.id
    
    if not user_states.get(chat_id, {}).get('in_search'):
        return
    
    if message.text == "В главное меню":
        user_states.pop(chat_id, None)
        return_to_menu(message)
        return
    
    city_query = message.text.strip()
    if len(city_query) < 2:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "❌ Напиши название города более 2 символов.", reply_markup=markup)
        bot.register_next_step_handler(msg, handle_city_input)
        return

    msg = bot.send_message(chat_id, f"🔍 Ищу «{city_query}»...")

    cities = search_city(city_query)
    if not cities:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('В главное меню')
        bot.edit_message_text(
            "❌ Город не найден!",
            chat_id=chat_id,
            message_id=msg.message_id,
        )
        msg = bot.send_message(chat_id, "Попробуй снова:", reply_markup=markup)
        bot.register_next_step_handler(msg, handle_city_input)
        return

    city = cities[0]
    city_name = city.get("name", city_query)
    lat = city["lat"]
    lon = city["lon"]

    bot.edit_message_text(
        f"📍 {city_name}\n⏳ Загружаю АЗС Лукойл и Татнефть...",
        chat_id=chat_id,
        message_id=msg.message_id,
    )

    stations = get_stations(lat, lon, RADIUS_KM)
    filtered = [s for s in stations if is_target_brand(s.get("brand", ""))]

    if not filtered:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('В главное меню')
        bot.edit_message_text(
            f"❌ В радиусе {RADIUS_KM} км от <b>{city_name}</b> не найдены АЗС Лукойл / Татнефть с актуальными отметками",
            chat_id=chat_id,
            message_id=msg.message_id,
            parse_mode="HTML"
        )
        msg = bot.send_message(chat_id, "Попробуй другой город:", reply_markup=markup)
        bot.register_next_step_handler(msg, handle_city_input)
        return

    def sort_key(s):
        st = s.get("status")
        order = {"yes": 0, "low": 1, "queue": 2, "no": 3}.get(st, 4)
        return (order, s.get("distance_km") or 999)

    filtered.sort(key=sort_key)
    filtered = filtered[:MAX_STATIONS]

    header = (
        f"<b>{city_name}</b> • Лукойл + Татнефть\n"
        f"✅ Найдено: {len(filtered)} АЗС (радиус {RADIUS_KM} км)\n"
        f"{'─' * 35}"
    )

    chunks = [header]
    current = header

    for s in filtered:
        block = "\n\n" + format_station(s)
        if len(current) + len(block) > 3800:
            chunks.append(current)
            current = format_station(s)
        else:
            current += block

    chunks.append(current)

    try:
        bot.delete_message(chat_id, msg.message_id)
    except Exception:
        pass

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('В главное меню')
    
    for i, chunk in enumerate(chunks):
        if i == len(chunks) - 1:
            bot.send_message(chat_id, chunk, parse_mode="HTML", reply_markup=markup)
        else:
            bot.send_message(chat_id, chunk, parse_mode="HTML")
    
    msg = bot.send_message(chat_id, "Ищешь бензин в другом городе?", reply_markup=markup)
    bot.register_next_step_handler(msg, handle_city_input)