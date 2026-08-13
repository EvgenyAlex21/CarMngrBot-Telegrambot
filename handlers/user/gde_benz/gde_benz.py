from core.imports import wraps, telebot, requests, types, ReadTimeoutError
from core.bot_instance import bot, BASE_DIR
from datetime import datetime, timezone
from math import cos, radians
from typing import Optional
from handlers.user.user_main_menu import return_to_menu
from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ------------------------------------------------- НАЙТИ БЕНЗ --------------------------------------------------

RADIUS_KM = 18        
PER_PAGE = 5       

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

USER_DATA = {}

FUEL_ORDER = ["92", "95", "98", "100", "ДТ", "Газ", "СУГ", "Метан"]
FUEL_LABEL = {
    "92": "АИ-92",
    "95": "АИ-95",
    "98": "АИ-98",
    "100": "АИ-100",
    "ДТ": "ДТ",
    "Газ": "Газ",
    "СУГ": "СУГ",
    "Метан": "Метан",
}

user_states = {}

def search_city(query: str) -> list:
    try:
        r = requests.get(
            "https://gdebenz.ru/api/cities",
            params={"q": query},
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        return r.json().get("results") or []
    except Exception as e:
        print("city error:", e)
        return []

def get_nearby(lat: float, lon: float, radius_km: float) -> list:
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
        return r.json().get("stations") or []
    except Exception as e:
        print("nearby error:", e)
        return []

def get_stations_bbox(lat: float, lon: float, radius_km: float) -> list:
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * max(0.2, cos(radians(lat))))
    try:
        r = requests.get(
            "https://gdebenz.ru/api/stations",
            params={
                "lat1": round(lat - dlat, 4),
                "lon1": round(lon - dlon, 4),
                "lat2": round(lat + dlat, 4),
                "lon2": round(lon + dlon, 4),
            },
            headers=HEADERS,
            timeout=12,
            allow_redirects=True,
        )
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else (data.get("stations") or [])
    except Exception as e:
        print("stations error:", e)
        return []

def is_target_brand(brand: str) -> bool:
    if not brand:
        return False
    b = brand.lower().replace("ё", "е")
    return "лукойл" in b or "татнефть" in b

def parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

def rel_time(dt: Optional[datetime], now: Optional[datetime] = None) -> str:
    if not dt:
        return "нет данных"
    now = now or datetime.now()
    sec = int((now - dt).total_seconds())
    if sec < 0:
        sec = 0
    if sec < 60:
        return "только что"
    if sec < 3600:
        m = sec // 60
        return f"{m} мин назад"
    if sec < 86400:
        h = sec // 3600
        return f"{h} ч назад"
    days = sec // 86400
    hours = (sec % 86400) // 3600
    if days == 1:
        d_str = "1 день"
    elif 2 <= days <= 4:
        d_str = f"{days} дня"
    else:
        d_str = f"{days} дней"
    if hours and days < 7:
        return f"{d_str} {hours} ч"
    return d_str

def age_phrase(dt: Optional[datetime], now: Optional[datetime] = None) -> str:
    if not dt:
        return ""
    now = now or datetime.now()
    sec = max(0, int((now - dt).total_seconds()))
    if sec < 3600:
        return f"{max(1, sec // 60)} мин"
    if sec < 86400:
        return f"{sec // 3600} ч"
    days = sec // 86400
    hours = (sec % 86400) // 3600
    if days == 1:
        d_str = "1 день"
    elif 2 <= days <= 4:
        d_str = f"{days} дня"
    else:
        d_str = f"{days} дней"
    if hours:
        return f"{d_str} {hours} час" if hours == 1 else f"{d_str} {hours} часов"
    return d_str

def status_emoji(status: Optional[str], fuels_now: str) -> str:
    if status == "no":
        return "🚫"
    if status == "low" or status == "queue":
        return "🟡"
    if status == "yes":
        return "🟢"
    if fuels_now:
        return "🟢"
    return "❔"

def merge_stations(nearby: list, priced: list) -> list:
    by_id = {str(s.get("osm_id")): s for s in priced if s.get("osm_id")}
    result = []
    seen = set()

    for n in nearby:
        oid = str(n.get("osm_id") or "")
        if not is_target_brand(n.get("brand", "")):
            continue
        p = by_id.get(oid, {})
        merged = {**p, **n}  
        if p.get("prices_now") and not merged.get("prices_now"):
            merged["prices_now"] = p["prices_now"]
        if not merged.get("addr") and p.get("addr"):
            merged["addr"] = p["addr"]
        result.append(merged)
        seen.add(oid)

    for p in priced:
        oid = str(p.get("osm_id") or "")
        if oid in seen:
            continue
        if not is_target_brand(p.get("brand", "")):
            continue
        result.append(p)

    def sort_key(s):
        st = s.get("status")
        order = {"yes": 0, "low": 1, "queue": 2, "no": 3}.get(st, 4)
        conf = -(s.get("confidence_base") or 0)
        dist = s.get("distance_km") if s.get("distance_km") is not None else 999
        return (order, dist, conf)

    result.sort(key=sort_key)
    return result

def format_fuels(s: dict, now: datetime) -> list[str]:
    lines = []
    prices = s.get("prices_now") or {}
    fuels_now_raw = (s.get("fuels_now") or "").replace(" ", "")
    available = set()
    if fuels_now_raw:
        for part in fuels_now_raw.replace(";", ",").split(","):
            part = part.strip()
            if part:
                available.add(part)

    status = s.get("status")
    detail = (s.get("detail") or "").lower()

    keys = list(prices.keys())
    for k in available:
        if k not in keys:
            keys.append(k)
    def key_ord(k):
        try:
            return FUEL_ORDER.index(k)
        except ValueError:
            return 99

    keys = sorted(set(keys), key=key_ord)

    for k in keys:
        label = FUEL_LABEL.get(k, k)
        info = prices.get(k) or {}
        price = info.get("p")
        t_price = parse_dt(info.get("t"))
        in_stock = k in available or (
            status == "yes" and not available and k in prices  
        )

        if status == "no" or "не работает" in detail:
            if price is not None:
                age = age_phrase(t_price, now) if t_price else ""
                age_s = f" {age}" if age else ""
                lines.append(f"🚫 {label}: нет в наличии{age_s}")
            else:
                lines.append(f"🚫 {label}: нет в наличии")
            continue

        if in_stock and price is not None:
            lines.append(f"✅ {label}: {price:.2f}₽")
        elif in_stock:
            lines.append(f"✅ {label}: в наличии")
        elif status in ("low", "queue") and price is not None:
            lines.append(f"⚠️ {label}: Мало ({price:.2f}₽)")
        elif price is not None:
            age = age_phrase(t_price, now) if t_price else ""
            if t_price and (now - t_price).total_seconds() > 3 * 86400:
                lines.append(f"❔ {label}: {price:.2f}₽ (цена от {age})")
            else:
                lines.append(f"❔ {label}: {price:.2f}₽")

    if not lines and fuels_now_raw:
        lines.append(f"✅ Сейчас отмечено: {fuels_now_raw}")

    return lines

def format_station(s: dict, now: datetime) -> str:
    brand = s.get("brand") or "АЗС"
    addr = s.get("addr") or "адрес не указан"
    status = s.get("status")
    fuels_now = s.get("fuels_now") or ""
    emoji = status_emoji(status, fuels_now)
    last = parse_dt(s.get("last_at"))
    time_s = rel_time(last, now)

    conf = s.get("confidence_base")
    conf_pct = None
    if conf is not None and conf > 0:
        conf_pct = int(round(min(0.99, max(0.05, conf)) * 100))

    shield = ""
    if (s.get("confirmations") or 0) >= 3 or (conf and conf >= 0.55):
        shield = " 🛡️"

    head = f"{emoji} <b>{brand}</b>{shield} | ⏱ {time_s}"
    loc = f"📍 {addr}🗺"

    fuel_lines = format_fuels(s, now)
    body = "\n".join(fuel_lines) if fuel_lines else "⛽ нет детальных данных по маркам"

    parts = [head, loc, body]

    if conf_pct is not None:
        parts.append(f"💬 Шансы {conf_pct}% (на основе активности на АЗС)")

    detail = (s.get("detail") or "").strip()
    if detail and detail.lower() not in body.lower():
        parts.append(f"ℹ️ {detail}")

    return "\n".join(parts)

def build_page_text(city: str, stations: list, page: int, updated: str) -> str:
    total = len(stations)
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(0, min(page, pages - 1))
    start = page * PER_PAGE
    chunk = stations[start : start + PER_PAGE]
    now = datetime.now()

    header = f"📍 <b>{city}</b> · Лукойл + Татнефть\n"
    header += f"Стр. {page + 1}/{pages} · всего {total}\n"
    header += "────────────────────"

    blocks = [format_station(s, now) for s in chunk]
    text = header + "\n\n" + "\n\n".join(blocks)
    text += f"\n\nОбновлено {updated}"

    if page == pages - 1:
        text += (
            "\n\n"
            "🟢 Есть — шансы найти бенз всё же есть.\n"
            "🟡 Ограничено — заправляют выборочно или по «талонам».\n"
            "🚫 Пусто — оплат и топлива нет.\n"
            "🛡️ Проверено — больше подтверждений / выше уверенность."
        )
    return text

def build_keyboard(page: int, total: int) -> types.InlineKeyboardMarkup:
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    kb = types.InlineKeyboardMarkup()
    row = []
    if page > 0:
        row.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"p:{page - 1}"))
    row.append(types.InlineKeyboardButton(f"{page + 1}/{pages}", callback_data="noop"))
    if page < pages - 1:
        row.append(types.InlineKeyboardButton("Вперёд ➡️", callback_data=f"p:{page + 1}"))
    kb.row(*row)
    kb.row(types.InlineKeyboardButton("🔄 Обновить", callback_data="refresh"))
    return kb

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
        USER_DATA.pop(chat_id, None)
        return_to_menu(message)
        return
    
    q = (message.text or "").strip()
    if len(q) < 2:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('В главное меню')
        msg = bot.send_message(chat_id, "❌ Напиши название города (минимум 2 символа).", reply_markup=markup)
        bot.register_next_step_handler(msg, handle_city_input)
        return

    wait = bot.send_message(chat_id, f"🔍 Ищу «{q}»...")

    cities = search_city(q)
    if not cities:
        bot.edit_message_text(
            "Город не найден! Попробуй другое написание.",
            chat_id=message.chat.id,
            message_id=wait.message_id,
        )
        return

    city = cities[0]
    city_name = city.get("name") or q
    lat, lon = city["lat"], city["lon"]

    bot.edit_message_text(
        f"📍 {city_name}\nСобираю Лукойл и Татнефть...",
        chat_id=message.chat.id,
        message_id=wait.message_id,
    )

    nearby = get_nearby(lat, lon, RADIUS_KM)
    priced = get_stations_bbox(lat, lon, RADIUS_KM + 5)
    stations = merge_stations(nearby, priced)

    if not stations:
        bot.edit_message_text(
            f"В радиусе {RADIUS_KM} км от {city_name} не нашлось Лукойл / Татнефть.",
            chat_id=message.chat.id,
            message_id=wait.message_id,
        )
        return

    updated = datetime.now().strftime("%d.%m.%Y %H:%M")
    USER_DATA[message.chat.id] = {
        "city": city_name,
        "lat": lat,
        "lon": lon,
        "stations": stations,
        "page": 0,
        "updated": updated,
    }

    text = build_page_text(city_name, stations, 0, updated)
    kb = build_keyboard(0, len(stations))

    try:
        bot.delete_message(message.chat.id, wait.message_id)
    except Exception:
        pass

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML",
        reply_markup=kb,
        disable_web_page_preview=True,
    )
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Используй кнопки выше для навигации или вернись в главное меню:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "В главное меню" and user_states.get(message.chat.id, {}).get('in_search'))
@check_function_state_decorator('В главное меню')
@track_usage('В главное меню (gde_benz)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def exit_fuel_search(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    USER_DATA.pop(chat_id, None)
    return_to_menu(message)

@bot.callback_query_handler(func=lambda c: c.data.startswith("p:") or c.data in ("refresh", "noop"))
@text_only_handler
def on_callback(call):
    chat_id = call.message.chat.id
    
    if not user_states.get(chat_id, {}).get('in_search'):
        bot.answer_callback_query(call.id, "Сеанс завершен", show_alert=False)
        return
    
    data = call.data or ""
    state = USER_DATA.get(chat_id)

    if data == "noop":
        bot.answer_callback_query(call.id)
        return

    if not state:
        bot.answer_callback_query(call.id, "Данные устарели — напиши город снова...", show_alert=True)
        return

    if data == "refresh":
        bot.answer_callback_query(call.id, "Обновляю...")
        nearby = get_nearby(state["lat"], state["lon"], RADIUS_KM)
        priced = get_stations_bbox(state["lat"], state["lon"], RADIUS_KM + 5)
        stations = merge_stations(nearby, priced)
        if not stations:
            bot.answer_callback_query(call.id, "Сейчас пусто", show_alert=True)
            return
        state["stations"] = stations
        state["updated"] = datetime.now().strftime("%d.%m.%Y %H:%M")
        state["page"] = 0
        page = 0
    elif data.startswith("p:"):
        try:
            page = int(data.split(":")[1])
        except ValueError:
            bot.answer_callback_query(call.id)
            return
        state["page"] = page
        bot.answer_callback_query(call.id)
    else:
        bot.answer_callback_query(call.id)
        return

    stations = state["stations"]
    page = state["page"]
    text = build_page_text(state["city"], stations, page, state["updated"])
    kb = build_keyboard(page, len(stations))

    try:
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=kb,
            disable_web_page_preview=True,
        )
    except Exception as e:
        if "not modified" not in str(e).lower():
            print("edit error:", e)