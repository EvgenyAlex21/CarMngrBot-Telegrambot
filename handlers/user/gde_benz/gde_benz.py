from core.imports import wraps, telebot, requests, types, ReadTimeoutError
from core.bot_instance import bot, BASE_DIR
from datetime import datetime, timezone
from math import cos, radians
from typing import Optional
import html as html_lib
import traceback
from handlers.user.user_main_menu import return_to_menu
from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ------------------------------------------------- НАЙТИ БЕНЗ --------------------------------------------------

RADIUS_KM = 18        
PER_PAGE = 5
MAX_BRAND_BUTTONS = 8       

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

USER_DATA = {}

FUEL_ORDER = ["92", "95", "98", "100", "ДТ", "Газ", "Метан"]
FUEL_LABEL = {
    "92": "АИ-92",
    "95": "АИ-95",
    "98": "АИ-98",
    "100": "АИ-100",
    "ДТ": "ДТ",
    "Газ": "Газ",
    "Метан": "Метан",
}

user_states = {}

def esc(text) -> str:
    if text is None:
        return ""
    return html_lib.escape(str(text))

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

def reverse_city(lat: float, lon: float) -> Optional[dict]:
    name = "Рядом с вами"
    try:
        r = requests.get(
            "https://gdebenz.ru/api/reverse-city",
            params={"lat": round(lat, 5), "lon": round(lon, 5)},
            headers=HEADERS,
            timeout=10,
            allow_redirects=True,
        )
        if r.ok:
            data = r.json()
            if isinstance(data, dict):
                name = (
                    data.get("city")
                    or data.get("name")
                    or data.get("title")
                    or name
                )
                results = data.get("results") or data.get("cities")
                if results and isinstance(results, list):
                    c = results[0]
                    name = c.get("name") or c.get("city") or name
    except Exception as e:
        print("reverse-city error:", e)

    return {"name": name, "lat": lat, "lon": lon}

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

def station_brand(s: dict) -> str:
    b = (s.get("brand") or "").strip()
    if b:
        return b
    name = (s.get("name") or "").strip()
    return name if name else "Другая"

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
        return f"{sec // 60} мин. назад"
    if sec < 86400:
        return f"{sec // 3600} ч. назад"
    days = sec // 86400
    hours = (sec % 86400) // 3600
    if days == 1:
        d_str = "1 день"
    elif 2 <= days <= 4:
        d_str = f"{days} дня"
    else:
        d_str = f"{days} дней"
    if hours and days < 7:
        return f"{d_str} {hours} ч."
    return d_str

def age_phrase(dt: Optional[datetime], now: Optional[datetime] = None) -> str:
    if not dt:
        return ""
    now = now or datetime.now()
    sec = max(0, int((now - dt).total_seconds()))
    if sec < 3600:
        return f"{max(1, sec // 60)} мин."
    if sec < 86400:
        return f"{sec // 3600} ч."
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
    if status in ("low", "queue"):
        return "🟡"
    if status == "yes" or fuels_now:
        return "🟢"
    return "❔"

def count_available_fuels(s: dict) -> int:
    status = s.get("status")
    detail_l = (s.get("detail") or "").lower()
    if status == "no" or "не работает" in detail_l:
        return 0

    fuels_now_raw = (s.get("fuels_now") or "").replace(" ", "")
    available = set()
    if fuels_now_raw:
        for part in fuels_now_raw.replace(";", ",").split(","):
            part = part.strip()
            if part:
                available.add(normalize_fuel_key(part))
    available |= collect_fuel_keys_from_detail(s.get("detail") or "")

    prices_raw = s.get("prices_now") or {}
    price_keys = {normalize_fuel_key(k) for k in prices_raw.keys()}

    if status == "yes" and not available and price_keys:
        return len(price_keys)
    if status in ("low", "queue"):
        return max(len(available), 1) if (available or price_keys) else 0
    return len(available)

def last_at_age_sec(s: dict) -> float:
    dt = parse_dt(s.get("last_at"))
    if not dt:
        return 10**12 
    return max(0.0, (datetime.now() - dt).total_seconds())

def station_rank(s: dict) -> tuple:
    st = s.get("status")
    status_order = {"yes": 0, "low": 1, "queue": 2, "no": 3}.get(st, 4)
    fuels_cnt = count_available_fuels(s)
    age = last_at_age_sec(s)
    dist = s.get("distance_km") if s.get("distance_km") is not None else 999
    conf = -(s.get("confidence_base") or 0)
    return (status_order, -fuels_cnt, age, dist, conf)

def merge_stations(nearby: list, priced: list) -> list:
    by_id = {str(s.get("osm_id")): s for s in priced if s.get("osm_id")}
    result = []
    seen = set()

    for n in nearby:
        oid = str(n.get("osm_id") or "")
        if not oid:
            continue
        p = by_id.get(oid, {})
        merged = {**p, **n}
        if p.get("prices_now") and not merged.get("prices_now"):
            merged["prices_now"] = p["prices_now"]
        if not merged.get("addr") and p.get("addr"):
            merged["addr"] = p["addr"]
        if not merged.get("brand") and p.get("brand"):
            merged["brand"] = p["brand"]
        result.append(merged)
        seen.add(oid)

    for p in priced:
        oid = str(p.get("osm_id") or "")
        if not oid or oid in seen:
            continue
        result.append(p)

    def sort_key(s):
        return station_rank(s)

    result.sort(key=sort_key)
    return result

def normalize_fuel_key(k: str) -> str:
    if not k:
        return k
    t = str(k).strip()
    low = t.lower().replace("ё", "е")
    low_compact = low.replace(" ", "").replace("-", "").replace("_", "").replace(".", "")
    if low_compact in ("92", "аи92", "a92", "ai92", "бензин92"):
        return "92"
    if low_compact in ("95", "аи95", "a95", "ai95", "бензин95"):
        return "95"
    if low_compact in ("98", "аи98", "a98", "ai98", "бензин98"):
        return "98"
    if low_compact in ("100", "аи100", "a100", "ai100", "бензин100"):
        return "100"
    if low_compact in ("дт", "дизель", "diesel", "dt", "дтт", "диз"):
        return "ДТ"
    if any(x in low for x in ("газ", "суг", "lpg", "пропан", "propane", "autogas", "газомотор")):
        return "Газ"
    if any(x in low for x in ("метан", "cng", "спг", "methane")):
        return "Метан"
    return t

def collect_fuel_keys_from_detail(detail: str) -> set:
    found = set()
    if not detail:
        return found
    low = detail.lower()
    for key, words in (
        ("Газ", ("газ", "суг", "lpg", "пропан")),
        ("Метан", ("метан", "cng")),
        ("92", ("92",)),
        ("95", ("95",)),
        ("98", ("98",)),
        ("100", ("100",)),
        ("ДТ", ("дт", "дизел")),
    ):
        if any(w in low for w in words):
            found.add(key)
    return found

def format_fuels(s: dict, now: datetime) -> list:
    lines = []
    prices_raw = s.get("prices_now") or {}
    prices = {}
    for k, v in prices_raw.items():
        prices[normalize_fuel_key(k)] = v

    fuels_now_raw = (s.get("fuels_now") or "").replace(" ", "")
    available = set()
    if fuels_now_raw:
        for part in fuels_now_raw.replace(";", ",").split(","):
            part = part.strip()
            if part:
                available.add(normalize_fuel_key(part))

    detail = (s.get("detail") or "")
    available |= collect_fuel_keys_from_detail(detail)

    status = s.get("status")
    detail_l = detail.lower()
    station_down = status == "no" or "не работает" in detail_l

    keys = set(prices.keys()) | set(available)

    if status == "yes" and not available and prices:
        available = set(prices.keys())

    def key_ord(k):
        try:
            return FUEL_ORDER.index(k)
        except ValueError:
            return 99

    keys = sorted(keys, key=key_ord)

    for k in keys:
        label = FUEL_LABEL.get(k, k)
        info = prices.get(k) or {}
        price = info.get("p")
        t_price = parse_dt(info.get("t"))
        in_stock = k in available and not station_down
        price_s = f"{price:.2f}₽" if price is not None else ""

        if station_down:
            age = age_phrase(t_price, now) if t_price else ""
            if price_s and age:
                lines.append(f"🚫 {label}: нет в наличии {age}")
            elif price_s:
                lines.append(f"🚫 {label}: нет в наличии · {price_s}")
            else:
                lines.append(f"🚫 {label}: нет в наличии")
            continue

        if status in ("low", "queue") and in_stock:
            if price_s:
                lines.append(f"⚠️ {label}: Мало ({price_s})")
            else:
                lines.append(f"⚠️ {label}: Мало")
            continue

        if in_stock:
            prefix = "🔥" if k == "Газ" else "✅"
            if price_s:
                lines.append(f"{prefix} {label}: {price_s}")
            else:
                lines.append(f"{prefix} {label}: в наличии")
        else:
            age = age_phrase(t_price, now) if t_price else ""
            if price_s and age:
                lines.append(f"🚫 {label}: нет · {price_s} (от {age})")
            elif price_s:
                lines.append(f"🚫 {label}: нет · {price_s}")
            else:
                lines.append(f"🚫 {label}: нет в наличии")

    if not lines and fuels_now_raw:
        lines.append(f"✅ Сейчас отмечено: {esc(fuels_now_raw)}")

    return lines

def format_station(s: dict, now: datetime) -> str:
    brand = esc(station_brand(s))
    addr = esc(s.get("addr") or "адрес не указан")
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
    loc = f"📍 {addr} 🗺"
    fuel_lines = format_fuels(s, now)
    body = "\n".join(fuel_lines) if fuel_lines else "⛽ нет детальных данных по маркам"
    parts = [head, loc, body]

    if conf_pct is not None:
        parts.append(f"💬 Шансы {conf_pct}% (на основе активности на АЗС)")

    detail = (s.get("detail") or "").strip()
    if detail and detail.lower() not in body.lower():
        parts.append(f"ℹ️ {esc(detail)}")

    return "\n".join(parts)

def filtered_stations(state: dict) -> list:
    all_st = state.get("stations") or []
    brand = state.get("brand_filter")
    if brand:
        brand_l = brand.lower()
        all_st = [s for s in all_st if station_brand(s).lower() == brand_l]
    return sorted(all_st, key=station_rank)

def brand_counts(stations: list) -> list:
    counts = {}
    for s in stations:
        b = station_brand(s)
        counts[b] = counts.get(b, 0) + 1
    return sorted(counts.items(), key=lambda x: (-x[1], x[0].lower()))

def build_page_text(state: dict, page: int) -> str:
    city = state["city"]
    stations = filtered_stations(state)
    total = len(stations)
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(0, min(page, pages - 1))
    start = page * PER_PAGE
    chunk = stations[start : start + PER_PAGE]
    now = datetime.now()

    brand_f = state.get("brand_filter")
    title_extra = f" · {esc(brand_f)}" if brand_f else " · все АЗС"

    header = (
        f"📍 <b>{esc(city)}</b>{title_extra}\n"
        f"Стр. {page + 1}/{pages} · всего {total}\n"
        f"{'─' * 20}"
    )
    if not chunk:
        text = header + "\n\nНет станций по этому фильтру."
    else:
        blocks = [format_station(s, now) for s in chunk]
        text = header + "\n\n" + "\n\n".join(blocks)

    text += f"\n\nОбновлено {esc(state['updated'])}"
    text += (
        "\n\n"
        "🟢 Есть — шансы найти бенз всё же есть\n"
        "🟡 Ограничено — заправляют выборочно или по «талонам»\n"
        "🚫 Пусто — оплат и топлива нет\n"
        "🛡️ Проверено — больше подтверждений / выше уверенность"
    )

    if len(text) > 4000:
        text = text[:3990] + "\n…"
    return text

def build_keyboard(state: dict, page: int) -> types.InlineKeyboardMarkup:
    stations_f = filtered_stations(state)
    total = len(stations_f)
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(0, min(page, pages - 1))

    kb = types.InlineKeyboardMarkup()

    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("⬅️", callback_data=f"page:{page - 1}"))
    nav.append(types.InlineKeyboardButton(f"{page + 1}/{pages}", callback_data="noop"))
    if page < pages - 1:
        nav.append(types.InlineKeyboardButton("➡️", callback_data=f"page:{page + 1}"))
    kb.row(*nav)

    current = state.get("brand_filter")
    counts = brand_counts(state.get("stations") or [])

    all_label = "• Все •" if not current else "Все"
    brand_btns = [types.InlineKeyboardButton(all_label, callback_data="brand:")]

    for brand, cnt in counts[:MAX_BRAND_BUTTONS]:
        cb = f"brand:{brand}"
        if len(cb.encode("utf-8")) > 64:
            cb = f"brand:{brand[:40]}"
        mark = "• " if current and current.lower() == brand.lower() else ""
        label = f"{mark}{brand} ({cnt})"
        if len(label) > 30:
            label = f"{mark}{brand[:18]}… ({cnt})"
        brand_btns.append(types.InlineKeyboardButton(label, callback_data=cb))

    for i in range(0, len(brand_btns), 3):
        kb.row(*brand_btns[i : i + 3])

    if len(counts) > MAX_BRAND_BUTTONS:
        kb.row(
            types.InlineKeyboardButton(
                f"Ещё сети ({len(counts) - MAX_BRAND_BUTTONS})…",
                callback_data="brands_more",
            )
        )

    kb.row(types.InlineKeyboardButton("🔄 Обновить", callback_data="refresh"))
    return kb

def build_brands_keyboard(state: dict) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    counts = brand_counts(state.get("stations") or [])
    current = state.get("brand_filter")

    kb.row(
        types.InlineKeyboardButton(
            "• Все •" if not current else "Все",
            callback_data="brand:",
        )
    )

    row = []
    for brand, cnt in counts:
        cb = f"brand:{brand}"
        if len(cb.encode("utf-8")) > 64:
            cb = f"brand:{brand[:40]}"
        mark = "• " if current and current.lower() == brand.lower() else ""
        label = f"{mark}{brand} ({cnt})"
        if len(label) > 28:
            label = f"{mark}{brand[:16]}…({cnt})"
        row.append(types.InlineKeyboardButton(label, callback_data=cb))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)

    kb.row(types.InlineKeyboardButton("« Назад к списку", callback_data="brands_back"))
    return kb

def fetch_and_store(
    chat_id: int,
    city_name: str,
    lat: float,
    lon: float,
    keep_filter: Optional[str] = None,
) -> Optional[dict]:
    nearby = get_nearby(lat, lon, RADIUS_KM)
    priced = get_stations_bbox(lat, lon, RADIUS_KM + 5)
    stations = merge_stations(nearby, priced)
    if not stations:
        return None
    updated = datetime.now().strftime("%d.%m.%Y %H:%M:%S")  

    brand_filter = keep_filter
    if brand_filter:
        names = {station_brand(s).lower() for s in stations}
        if brand_filter.lower() not in names:
            brand_filter = None

    state = {
        "city": city_name,
        "lat": lat,
        "lon": lon,
        "stations": stations,
        "page": 0,
        "updated": updated,
        "brand_filter": brand_filter,
    }
    USER_DATA[chat_id] = state
    return state

def resolve_brand_callback(state: dict, raw: str) -> Optional[str]:
    if raw is None or raw == "":
        return None
    for b, _ in brand_counts(state.get("stations") or []):
        if b == raw or b.lower() == raw.lower():
            return b
    for b, _ in brand_counts(state.get("stations") or []):
        if b.startswith(raw) or b.lower().startswith(raw.lower()):
            return b
    return raw

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
    user_states[chat_id] = {"in_search": True, "results_shown": False}
    USER_DATA.pop(chat_id, None)

    text = (
        "🔍 <b>Поиск бензина по городу</b>\n\n"
        "Просто Напишите название города (например: <code>Чебоксары</code>, <code>Казань</code>, <code>Уфа</code>) или отправь геопозицию, чтобы найти ближайшие АЗС с актуальными ценами на топливо\n\n"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Отправить геопозицию", request_location=True))
    markup.add("В главное меню")

    msg = bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
    bot.register_next_step_handler(msg, handle_city_input)

def handle_city_input(message):
    chat_id = message.chat.id

    st = user_states.get(chat_id) or {}
    if not st.get("in_search"):
        return

    if st.get("results_shown"):
        return handle_after_results(message)

    if message.location:
        return on_location(message)

    q = (message.text or "").strip()

    if q == "В главное меню":
        clear_gde_benz_state(chat_id)
        return_to_menu(message)
        return

    if q == "Другой город":
        return other_city(message)

    if q.startswith("/start") or q.startswith("/admin"):
        clear_gde_benz_state(chat_id)
        return

    if not q or q.startswith("/"):
        msg = bot.reply_to(message, "Напишите название города!")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Отправить геопозицию", request_location=True))
        markup.add("В главное меню")
        msg2 = bot.send_message(chat_id, "Попробуйте еще раз...", reply_markup=markup)
        bot.register_next_step_handler(msg2, handle_city_input)
        return
    if len(q) < 2:
        msg = bot.reply_to(message, "Напишите название города!")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Отправить геопозицию", request_location=True))
        markup.add("В главное меню")
        msg2 = bot.send_message(chat_id, "Попробуйте еще раз...", reply_markup=markup)
        bot.register_next_step_handler(msg2, handle_city_input)
        return

    wait = bot.send_message(chat_id, f"🔍 Ищу «{q}»...")

    cities = search_city(q)
    if not cities:
        try:
            bot.edit_message_text(
                "❌ Город не найден! Попробуйте другое написание...",
                chat_id=message.chat.id,
                message_id=wait.message_id,
            )
        except Exception:
            pass
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Отправить геопозицию", request_location=True))
        markup.add('В главное меню')
        msg2 = bot.send_message(chat_id, "Попробуйте еще раз...", reply_markup=markup)
        bot.register_next_step_handler(msg2, handle_city_input)
        return

    city = cities[0]
    city_name = city.get("name") or q
    lat, lon = float(city["lat"]), float(city["lon"])

    process_city_point(message, city_name, lat, lon, wait_msg=wait)

def process_city_point(message, city_name: str, lat: float, lon: float, wait_msg=None):
    chat_id = message.chat.id
    if wait_msg is None:
        wait_msg = bot.reply_to(message, f"Собираю АЗС по городу {city_name}...")
    else:
        try:
            bot.edit_message_text(
                f"Собираю АЗС по городу {city_name}...",
                chat_id=chat_id,
                message_id=wait_msg.message_id,
            )
        except Exception:
            pass

    state = fetch_and_store(chat_id, city_name, lat, lon)
    if not state:
        try:
            bot.edit_message_text(
                f"❌ В радиусе {RADIUS_KM} км. от {city_name} АЗС не найдено!",
                chat_id=chat_id,
                message_id=wait_msg.message_id,
            )
        except Exception:
            bot.reply_to(message, f"❌ В радиусе {RADIUS_KM} км. от {city_name} АЗС не найдено!")
        user_states[chat_id] = {"in_search": True, "results_shown": False}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Отправить геопозицию", request_location=True))
        markup.add("В главное меню")
        msg2 = bot.send_message(chat_id, "Попробуйте другой город или геопозицию...", reply_markup=markup)
        bot.register_next_step_handler(msg2, handle_city_input)
        return

    text = build_page_text(state, 0)
    kb = build_keyboard(state, 0)
    try:
        bot.delete_message(chat_id, wait_msg.message_id)
    except Exception:
        pass

    sent = bot.send_message(
        chat_id,
        text,
        parse_mode="HTML",
        reply_markup=kb,
        link_preview_options=types.LinkPreviewOptions(is_disabled=True),
    )
    state["message_id"] = sent.message_id

    user_states[chat_id] = {"in_search": True, "results_shown": True}

    bottom_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    bottom_markup.row("Другой город")
    bottom_markup.row("В главное меню")
    msg_bottom = bot.send_message(
        chat_id,
        "Вы можете посмотреть обстановку в другом городе или вернуться в главное меню...",
        reply_markup=bottom_markup,
    )
    bot.register_next_step_handler(msg_bottom, handle_after_results)

@bot.message_handler(content_types=["location"])
def on_location(message):
    chat_id = message.chat.id

    st = user_states.get(chat_id) or {}
    if not st.get("in_search"):
        return

    if st.get("results_shown"):
        bot.send_message(
            chat_id,
            "Чтобы искать в другом месте, нажмите «Другой город».",
        )
        bot.register_next_step_handler(message, handle_after_results)
        return

    if not message.location:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("В главное меню")
        bot.send_message(chat_id, "❌ Не удалось прочитать геопозицию! Попробуйте снова...", reply_markup=markup)
        return

    lat = float(message.location.latitude)
    lon = float(message.location.longitude)
    wait = bot.send_message(chat_id, "Определяю город по геопозиции...")
    city = reverse_city(lat, lon)
    city_name = city.get("name") or "Рядом с вами"
    process_city_point(message, city_name, lat, lon, wait_msg=wait)

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
def cmd_geo(message):
    chat_id = message.chat.id
    
    if not user_states.get(chat_id, {}).get('in_search'):
        return
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("Отправить геопозицию", request_location=True))
    kb.add('В главное меню')
    bot.send_message(
        chat_id,
        "Нажмите кнопку, чтобы отправить геопозицию!",
        reply_markup=kb,
    )

@bot.callback_query_handler(func=lambda c: c.data in ("noop", "refresh", "brands_more", "brands_back") or c.data.startswith("page:") or c.data.startswith("brand:"))
@text_only_handler
def on_callback(call):
    data = (call.data or "").strip()
    chat_id = call.message.chat.id if call.message else call.from_user.id
    msg_id = call.message.message_id if call.message else None

    print(f"[callback] chat={chat_id} data={data!r} msg={msg_id}")
    
    if not user_states.get(chat_id, {}).get('in_search'):
        try:
            bot.answer_callback_query(call.id, text="Сеанс завершен", show_alert=False)
        except Exception:
            pass
        return

    def answer(text=None, alert=False):
        try:
            bot.answer_callback_query(call.id, text=text, show_alert=alert)
        except Exception as e:
            print("answer_callback_query error:", e)

    try:
        if data == "noop":
            answer()
            return

        state = USER_DATA.get(chat_id)
        if not state:
            answer("Данные устарели — напишите город заново...", alert=True)
            return

        if data == "brands_more":
            answer()
            try:
                bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=msg_id,
                    reply_markup=build_brands_keyboard(state),
                )
            except Exception as e:
                print("brands_more error:", e)
            return

        if data == "brands_back":
            answer()
            page = state.get("page", 0)
            try:
                bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=msg_id,
                    reply_markup=build_keyboard(state, page),
                )
            except Exception as e:
                print("brands_back error:", e)
            return

        if data == "refresh":
            answer("Обновляю...")
            new_state = fetch_and_store(
                chat_id,
                state["city"],
                state["lat"],
                state["lon"],
                keep_filter=state.get("brand_filter"),
            )
            if not new_state:
                answer("Сейчас пусто!", alert=True)
                return
            state = new_state
            page = 0
            state["page"] = 0

        elif data.startswith("page:"):
            try:
                page = int(data.split(":", 1)[1])
            except ValueError:
                answer("Ошибка страницы!")
                return
            total = len(filtered_stations(state))
            pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
            page = max(0, min(page, pages - 1))
            state["page"] = page
            answer()

        elif data.startswith("brand:"):
            raw = data[6:]
            brand = resolve_brand_callback(state, raw)
            state["brand_filter"] = brand
            state["page"] = 0
            page = 0
            answer(f"Фильтр: {brand}" if brand else "Все АЗС")

        else:
            answer()
            return

        page = state.get("page", 0)
        text = build_page_text(state, page)
        kb = build_keyboard(state, page)

        if not msg_id:
            answer("Нет сообщения для обновления!", alert=True)
            return

        try:
            bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=msg_id,
                parse_mode="HTML",
                reply_markup=kb,
                link_preview_options=types.LinkPreviewOptions(is_disabled=True),
            )
            print(f"[edit ok] page={page} filter={state.get('brand_filter')}")
        except Exception as e:
            err = str(e).lower()
            if "message is not modified" in err:
                if data == "refresh":
                    answer("Уже актуально", alert=False)
                return
            print("edit_message_text error:", e)
            try:
                plain = (
                    text.replace("<b>", "")
                    .replace("</b>", "")
                    .replace("<code>", "")
                    .replace("</code>", "")
                )
                bot.edit_message_text(
                    plain,
                    chat_id=chat_id,
                    message_id=msg_id,
                    reply_markup=kb,
                    link_preview_options=types.LinkPreviewOptions(is_disabled=True),
                )
            except Exception as e2:
                err2 = str(e2).lower()
                if "message is not modified" in err2:
                    if data == "refresh":
                        answer("Уже актуально", alert=False)
                    return
                print("fallback edit error:", e2)
                traceback.print_exc()
                answer("❌ Не удалось обновить! Нажмите на кнопку другой город или введи город снова...", alert=True)

    except Exception as e:
        print("callback fatal:", e)
        traceback.print_exc()
        answer("❌ Ошибка! Нажмите на кнопку другой город или введи город снова...", alert=True)

def clear_gde_benz_state(chat_id: int) -> None:
    user_states.pop(chat_id, None)
    USER_DATA.pop(chat_id, None)
    try:
        bot.clear_step_handler_by_chat_id(chat_id)
    except Exception:
        pass

def handle_after_results(message):
    chat_id = message.chat.id
    st = user_states.get(chat_id) or {}

    if not st.get("in_search") or not st.get("results_shown"):
        return

    q = (message.text or "").strip() if message.text else ""

    if q == "Другой город":
        other_city(message)
        return

    if q == "В главное меню":
        clear_gde_benz_state(chat_id)
        return_to_menu(message)
        return

    if q.startswith("/start") or q.startswith("/admin"):
        clear_gde_benz_state(chat_id)
        return

    if message.location:
        bot.send_message(
            chat_id,
            "Чтобы искать в другом городе, нажмите на соответствующую кнопку!",
        )
        bot.register_next_step_handler(message, handle_after_results)
        return

    bot.send_message(
        chat_id,
        "Чтобы искать в другом городе, нажмите на соответствующую кнопку!",
    )
    bot.register_next_step_handler(message, handle_after_results)

def other_city(message):
    chat_id = message.chat.id
    USER_DATA.pop(chat_id, None)
    try:
        bot.clear_step_handler_by_chat_id(chat_id)
    except Exception:
        pass
    user_states[chat_id] = {"in_search": True, "results_shown": False}

    text = (
        "🔍 <b>Поиск бензина по городу</b>\n\n"
        "Просто Напишите название города (например: <code>Чебоксары</code>, <code>Казань</code>, <code>Уфа</code>) "
        "или отправь геопозицию, чтобы найти ближайшие АЗС с актуальными ценами на топливо\n\n"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Отправить геопозицию", request_location=True))
    markup.add("В главное меню")

    msg = bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
    bot.register_next_step_handler(msg, handle_city_input)

@bot.message_handler(
    func=lambda message: message.text == "Другой город"
    and bool(user_states.get(message.chat.id, {}).get("in_search"))
)
@check_function_state_decorator("Найти бенз")
@track_usage("Другой город")
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def other_city_handler(message):
    other_city(message)

@bot.message_handler(
    func=lambda message: message.text == "В главное меню"
    and bool(user_states.get(message.chat.id, {}).get("in_search"))
)
@track_usage("В главное меню (gde_benz)")
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@text_only_handler
def exit_fuel_search(message):
    clear_gde_benz_state(message.chat.id)
    return_to_menu(message)

@bot.message_handler(func=lambda message: (message.text or "").strip() == "В главное меню")
def gde_benz_clear_on_main_menu(message):
    clear_gde_benz_state(message.chat.id)