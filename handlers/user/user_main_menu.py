from core.imports import wraps, telebot, types, os, json, re, time, threading, shutil, datetime, timedelta, ApiTelegramException, InlineKeyboardMarkup, InlineKeyboardButton
from core.bot_instance import bot, BASE_DIR
from decorators.blocked_user import load_blocked_users, save_blocked_users
from .utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage
)

def get_payment_provider_token():
    from handlers.user.subscription.subscription_main import PAYMENT_PROVIDER_TOKEN as _T
    return _T

def create_referral_link(user_id):
    from handlers.user.subscription.referral import create_referral_link as _f
    return _f(user_id)

def track_referral_activity(referral_code, new_user_id):
    from handlers.user.subscription.referral import track_referral_activity as _f
    return _f(referral_code, new_user_id)

def apply_referral_bonus(referrer_id):
    from handlers.user.subscription.referral import apply_referral_bonus as _f
    return _f(referrer_id)

def is_user_subscribed(user_id):
    from handlers.user.subscription.ad_channels import is_user_subscribed as _f
    return _f(user_id)

def send_subscription_options(message):
    from handlers.user.subscription.buy_subscription import send_subscription_options as _f
    return _f(message)

# ------------------------------------ ПОДПИСКА НА БОТА (инициализация бд, платежки, активности пользователей) ------------------------------------------

PAYMENTS_DATABASE_PATH = os.path.join(BASE_DIR, "data", "admin", "admin_user_payments", "payments.json")
USERS_DATABASE_PATH = os.path.join(BASE_DIR, "data", "admin", "admin_user_payments", "users.json")

PROMO_CODES = {}
AD_CHANNELS = {}
PROMO_FILE_MTIME = 0

active_users = {}
total_users = set()

def load_promo_and_channels():
    global PROMO_CODES, AD_CHANNELS, PROMO_FILE_MTIME
    json_dir = os.path.join(BASE_DIR, 'files', 'files_for_bot')
    json_path = os.path.join(json_dir, 'promo_and_channels.json')
    
    os.makedirs(json_dir, exist_ok=True)
    
    if not os.path.exists(json_path):
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({"promo_codes": {}, "ad_channels": {}}, f, ensure_ascii=False, indent=4)
        PROMO_FILE_MTIME = os.path.getmtime(json_path)
    try:
        current_mtime = os.path.getmtime(json_path)
        if current_mtime != PROMO_FILE_MTIME:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                PROMO_FILE_MTIME = current_mtime
                PROMO_CODES = data.get('promo_codes', {})
                AD_CHANNELS = data.get('ad_channels', {})
        return PROMO_CODES, AD_CHANNELS
    except json.JSONDecodeError:
        PROMO_CODES = {}
        AD_CHANNELS = {}
        return PROMO_CODES, AD_CHANNELS

def initialize_ad_channels():
    promo_codes, ad_channels = load_promo_and_channels()
    return {chat_id: channel for chat_id, channel in ad_channels.items() if channel['active']}

AD_CHANNELS = initialize_ad_channels()

def monitor_promo_file_changes():
    while True:
        load_promo_and_channels()  
        time.sleep(5)  

promo_monitor_thread = threading.Thread(target=monitor_promo_file_changes, daemon=True)
promo_monitor_thread.start()

PAYMENTS_LOCK = threading.Lock()

def load_payment_data():
    global PROMO_CODES, AD_CHANNELS
    promo_codes, ad_channels = load_promo_and_channels()

    default_data = {
        'subscriptions': {'users': {}},
        'subscription_history': {},
        'referrals': {
            'links': {},
            'stats': {},
            'bonuses': {},
            'leaderboard_history': {
                'current_leader': None,
                'leader_start_date': None,
                'days_at_top': 0
            },
            'top_formed_date': None,
            'last_top10_bonus': None
        },
        'all_users_total_amount': 0,
        'promo_codes': promo_codes,
        'ad_channels': ad_channels,
        'refunds': []
    }

    with PAYMENTS_LOCK:
        if not os.path.exists(PAYMENTS_DATABASE_PATH) or os.path.getsize(PAYMENTS_DATABASE_PATH) == 0:
            os.makedirs(os.path.dirname(PAYMENTS_DATABASE_PATH), exist_ok=True)
            with open(PAYMENTS_DATABASE_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=4, ensure_ascii=False)
            return default_data

        try:
            with open(PAYMENTS_DATABASE_PATH, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    raise json.JSONDecodeError("Файл пуст", content, 0)
                data = json.loads(content)

            if not isinstance(data, dict) or 'subscriptions' not in data:
                raise ValueError("Некорректная структура данных в payments.json")

            for key, value in default_data.items():
                if key not in data:
                    data[key] = value
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if sub_key not in data[key]:
                            data[key][sub_key] = sub_value

            if 'subscriptions' in data and 'users' in data['subscriptions']:
                for user_id in list(data['subscriptions']['users']):
                    if not isinstance(data['subscriptions']['users'][user_id], dict):
                        data['subscriptions']['users'][user_id] = {
                            "username": "неизвестный",
                            "plans": [],
                            "total_amount": 0,
                            "referral_points": 0,
                            "free_feature_trials": {},
                            "promo_usage_history": [],
                            "referral_milestones": {},
                            "points_history": [],
                            "last_promo_used": None,
                            "daily_bonus_date": None,
                            "last_bonus_timestamp": None,
                            "streak_days": 0,
                            "discount": 0,
                            "applicable_category": None,
                            "applicable_items": [],
                            "discount_type": None,
                            "ad_channels_subscribed": []
                        }
                    user_data = data['subscriptions']['users'][user_id]
                    for field, default in {
                        'referral_points': 0,
                        'promo_usage_history': [],
                        'referral_milestones': {},
                        'points_history': [],
                        'ad_channels_subscribed': [],
                        'last_promo_used': None,
                        'daily_bonus_date': None,
                        'last_bonus_timestamp': None,
                        'streak_days': 0,
                        'discount': 0,
                        'applicable_category': None,
                        'applicable_items': [],
                        'discount_type': None
                    }.items():
                        user_data.setdefault(field, default)

            return data

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Ошибка при загрузке payments.json: {e}")
            backup_path = PAYMENTS_DATABASE_PATH + ".backup"
            if os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            data = json.loads(content)
                            if isinstance(data, dict) and 'subscriptions' in data:
                                shutil.copy(backup_path, PAYMENTS_DATABASE_PATH)
                                print("Восстановлены данные из бэкапа")
                                return data
                except json.JSONDecodeError:
                    print("Бэкап повреждён, создаётся новый файл")
            with open(PAYMENTS_DATABASE_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=4, ensure_ascii=False)
            return default_data

def update_user_activity(user_id, username=None, first_name="", last_name="", phone="", function_name=None):

    from handlers.admin.statistics.statistics import load_statistics, save_statistics

    active_users[user_id] = datetime.now()
    total_users.add(user_id)
    user_id_str = str(user_id)
    current_time = datetime.now().strftime('%d.%m.%Y в %H:%M:%S')
    now = datetime.now()
    today = now.strftime('%d.%m.%Y')

    statistics = load_statistics()
    data = load_payment_data()
    users_data = load_users_data()

    formatted_username = f"@{username}" if username else ""

    if user_id_str not in data['subscriptions']['users']:
        data['subscriptions']['users'][user_id_str] = {
            "username": formatted_username or "неизвестный",
            "plans": [],
            "total_amount": 0,
            "referral_points": 0,
            "free_feature_trials": {},
            "promo_usage_history": [],
            "referral_milestones": {},
            "points_history": [],
            "last_promo_used": None,
            "daily_bonus_date": None,
            "last_bonus_timestamp": None,
            "streak_days": 0,
            "discount": 0,
            "applicable_category": None,
            "applicable_items": [],
            "discount_type": None
        }

    user_subscription = data['subscriptions']['users'][user_id_str]
    user_subscription['username'] = formatted_username or user_subscription.get('username', "неизвестный")

    last_bonus_date = user_subscription.get('daily_bonus_date')
    join_date = users_data.get(user_id_str, {}).get('join_date', now.strftime("%d.%m.%Y в %H:%M"))
    days_since_join = (now - datetime.strptime(join_date, "%d.%m.%Y в %H:%M")).days
    bonus_points = 1.0 if days_since_join <= 7 else 0.5 

    can_award_bonus = False
    if not last_bonus_date or last_bonus_date != today:
        can_award_bonus = True

    if can_award_bonus:
        user_subscription['last_bonus_timestamp'] = current_time
        user_subscription['daily_bonus_date'] = today
        streak_days = user_subscription.get('streak_days', 0)

        if last_bonus_date:
            last_date = datetime.strptime(last_bonus_date, "%d.%m.%Y")
            if (now.date() - last_date.date()).days == 1:
                streak_days += 1 
            else:
                streak_days = 1  
        else:
            streak_days = 1 

        user_subscription['streak_days'] = streak_days
        user_subscription['referral_points'] += bonus_points
        user_subscription['points_history'].append({
            "action": "earned",
            "points": bonus_points,
            "reason": "Ежедневный вход",
            "date": current_time
        })

    if user_id_str not in users_data:
        users_data[user_id_str] = {
            "username": formatted_username or "неизвестный",
            "activity": {},
            "usage_stats": {},
            "join_date": now.strftime("%d.%m.%Y в %H:%M"),
            "user_id": user_id,
            "first_name": first_name or "",
            "last_name": last_name or "",
            "phone": phone,
            "last_active": current_time,
            "blocked": False,
            "actions": 0,
            "session_time": 0,
            "returning": False
        }
    else:
        users_data[user_id_str]['username'] = formatted_username or users_data[user_id_str].get('username', "неизвестный")
        users_data[user_id_str]['first_name'] = first_name or ""
        users_data[user_id_str]['last_name'] = last_name or ""
        users_data[user_id_str]['phone'] = phone
        users_data[user_id_str]['last_active'] = current_time
        users_data[user_id_str].setdefault('activity', {})
        users_data[user_id_str].setdefault('usage_stats', {})
        users_data[user_id_str].setdefault('join_date', now.strftime("%d.%m.%Y в %H:%M"))

    today_stats = datetime.now().strftime('%d.%m.%Y')
    if today_stats not in statistics:
        statistics[today_stats] = { 'users': set(), 'functions': {} }
    statistics[today_stats]['users'].add(user_id)
    if function_name:
        if function_name not in statistics[today_stats]['functions']:
            statistics[today_stats]['functions'][function_name] = 0
        statistics[today_stats]['functions'][function_name] += 1

    save_statistics(statistics)
    save_payments_data(data)
    save_users_data(users_data)

def save_payments_data(data):
    try:
        if not data or not isinstance(data, dict) or 'subscriptions' not in data:
            error_msg = "Попытка сохранить пустые или некорректные данные в payments.json"
            print(error_msg)
            raise ValueError(error_msg)

        json.dumps(data, ensure_ascii=False)

        with PAYMENTS_LOCK:
            temp_file = PAYMENTS_DATABASE_PATH + ".temp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            if os.path.exists(PAYMENTS_DATABASE_PATH):
                backup_path = PAYMENTS_DATABASE_PATH + ".backup"
                shutil.copy(PAYMENTS_DATABASE_PATH, backup_path)

            shutil.move(temp_file, PAYMENTS_DATABASE_PATH)

    except json.JSONEncodeError as e:
        error_msg = f"Ошибка при сериализации данных в JSON: {e}"
        print(error_msg)
        raise Exception("Не удалось сохранить payments.json из-за ошибки сериализации")
    except Exception as e:
        error_msg = f"Ошибка при записи в {PAYMENTS_DATABASE_PATH}: {e}"
        print(error_msg)
        raise Exception(f"Не удалось сохранить payments.json: {e}")

def load_users_data():
    ensure_directory_exists(USERS_DATABASE_PATH)

    if not os.path.exists(USERS_DATABASE_PATH):
        with open(USERS_DATABASE_PATH, 'w', encoding='utf-8') as file:
            json.dump({}, file)
        return {}

    try:
        with open(USERS_DATABASE_PATH, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            data = json.loads(content)
        
        now = datetime.now().strftime("%d.%m.%Y в %H:%M")
        for user_id in data:
            data[user_id].setdefault('join_date', now)
            data[user_id].setdefault('username', 'неизвестный')
            data[user_id].setdefault('usage_stats', {})
            data[user_id].setdefault('activity', {})
            data[user_id].pop('last_promo_used', None)
            data[user_id].pop('auto_renew', None)
        
        save_users_data(data)
        return data
    except json.JSONDecodeError as e:
        with open(USERS_DATABASE_PATH, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        return {}
    except Exception as e:
        with open(USERS_DATABASE_PATH, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        return {}

def save_users_data(data):
    with open(USERS_DATABASE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def ensure_directory_exists(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

# ------------------------------ ПОДПИСКА НА БОТА (бесплатные и платные функции, пробный период, фоновые функции) -----------------------------

def load_features():
    json_dir = os.path.join(BASE_DIR, 'files', 'files_for_bot')
    json_path = os.path.join(json_dir, 'free_and_paid_features.json')
    
    os.makedirs(json_dir, exist_ok=True)
    
    if not os.path.exists(json_path):
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({"free_features": [], "paid_features": []}, f, ensure_ascii=False, indent=4)
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('free_features', []), data.get('paid_features', [])
    except json.JSONDecodeError:
        return [], []

FREE_FEATURES, PAID_FEATURES = load_features()

def set_free_trial_period(user_id, days, source="default"):
    data = load_payment_data()
    user_id_str = str(user_id)

    if user_id_str not in data['subscriptions']['users']:
        data['subscriptions']['users'][user_id_str] = {
            "plans": [],
            "total_amount": 0,
            "username": "неизвестный",
            "referral_points": 0,
            "promo_usage_history": [],
            "referral_milestones": {},
            "points_history": [],
            "ad_bonus_received": False
        }

    user_data = data['subscriptions']['users'][user_id_str]
    now = datetime.now()

    if 'plans' not in user_data:
        user_data['plans'] = []

    start_date = now
    
    if source == "referral" and user_data['plans']:
        trial_plans = [p for p in user_data['plans'] if p.get('plan_name') == "free" and p.get('source') != "referral"]
        if trial_plans:
            latest_trial = max(trial_plans, key=lambda p: datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M"))
            start_date = datetime.strptime(latest_trial['end_date'], "%d.%m.%Y в %H:%M")
        else:
            latest_end = max([datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") for p in user_data['plans']])
            start_date = max(latest_end, now)
    elif user_data['plans']:
        latest_end = max([datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") for p in user_data['plans']])
        start_date = max(latest_end, now)

    new_end = start_date + timedelta(days=days)

    user_data['plans'].append({
        "plan_name": "free",
        "start_date": start_date.strftime("%d.%m.%Y в %H:%M"),
        "end_date": new_end.strftime("%d.%m.%Y в %H:%M"),
        "price": 0,
        "source": source
    })

    save_payments_data(data)
    return new_end

def is_premium_user(user_id):
    data = load_payment_data()
    user_id_str = str(user_id)
    user_data = data['subscriptions']['users'].get(user_id_str, {})
    plans = user_data.get('plans', [])
    
    now = datetime.now()
    for plan in plans:
        end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
        if end_date > now:
            return True
    
    return False

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout_query(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

def safe_send_message(user_id, text, **kwargs):
    try:
        bot.send_message(user_id, text, **kwargs)
    except ApiTelegramException as e:
        if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
            blocked_users = load_blocked_users()
            if user_id not in blocked_users:
                blocked_users.append(user_id)
                save_blocked_users(blocked_users)
        else:
            raise e

def background_subscription_expiration_check():
    time.sleep(86400)
    while True:
        data = load_payment_data()
        users_data = load_users_data()
        for user_id, user_data in data['subscriptions']['users'].items():
            if not is_user_subscribed(int(user_id)):
                continue
            active = any(datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") > datetime.now() for p in user_data.get('plans', []))
            if not active and not user_data.get('offer_sent', False):
                last_end = max([datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") for p in user_data['plans']]) if user_data.get('plans') else datetime.now()
                if (datetime.now() - last_end).days >= 30:
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("Вернуться за 99 ₽", callback_data="special_offer_weekly"))
                    safe_send_message(user_id, (
                        "🎁 *Соскучились?*\n\n"
                        "✨ Вернитесь с подпиской на 7 дней всего за *99 ₽*!\n"
                    ), reply_markup=markup, parse_mode="Markdown")
                    user_data['offer_sent'] = True
                    save_payments_data(data)
            for plan in user_data.get('plans', []):
                end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
                now = datetime.now()
                remaining_time = end_date - now
                remaining_days = remaining_time.days
                remaining_hours = remaining_time.seconds // 3600
                remaining_minutes = (remaining_time.seconds % 3600) // 60
                if remaining_days == 1:
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("Продлить", callback_data="buy_subscription"))
                    safe_send_message(user_id, (
                        f"⏳ <b>Ваша подписка истекает через:</b> {remaining_days} дней {remaining_hours:02}:{remaining_minutes:02} часов!\n\n"
                        f"📅 <b>Срок действия:</b> {plan['end_date']}\n\n"
                        "🚀 Продлите подписку прямо сейчас!"
                    ), parse_mode="HTML")
                elif remaining_days < 2 and remaining_days >= 0:
                    safe_send_message(user_id, (
                        f"⏳ *Ваша подписка истекает через:* {remaining_days} дн. {remaining_hours:02}:{remaining_minutes:02} ч.!\n\n"
                        f"📅 *Срок действия:* {plan['end_date']}\n\n"
                        "🚀 Продлите подписку прямо сейчас!"
                    ), parse_mode="Markdown")
                elif now > end_date and not user_data.get('trial_ended_notified', False):
                    safe_send_message(user_id, (
                        "⏳ *Ваш пробный период завершился!*\n\n"
                        "💳 Пожалуйста, оплатите подписку для продолжения использования бота и доступа ко всем функциям, если вы ее еще не купили!\n\n"
                        "🎉 Не упустите возможность продлить доступ и наслаждаться полным функционалом!"
                    ), parse_mode="Markdown")
                    user_data['trial_ended_notified'] = True
                    save_payments_data(data)
        time.sleep(86400)

thread_expiration = threading.Thread(target=background_subscription_expiration_check, daemon=True)
thread_expiration.start()

@bot.callback_query_handler(func=lambda call: call.data == "buy_subscription")
@text_only_handler
def handle_buy_subscription(call):
    send_subscription_options(call.message)
    bot.answer_callback_query(call.id, "🚀 Выберите подписку для продления!")

@bot.callback_query_handler(func=lambda call: call.data == "special_offer_weekly")
@text_only_handler
def send_special_offer_invoice(call):
    user_id = call.from_user.id
    try:
        bot.send_invoice(
            user_id,
            "🌟 Специальное предложение: 7 дней",
            (
                "🎁 *С возвращением!*\n\n"
                "✨ Вернитесь с подпиской по суперцене!\n\n"
                "🚀 Полный доступ ко всем функциям бота!"
            ),
            get_payment_provider_token(),
            "sub",
            "RUB",
            [types.LabeledPrice("🌟 7 дней", 9900)],
            "weekly_subscription_7",
        )
        bot.answer_callback_query(call.id, "🎉 С возвращением!")
    except ApiTelegramException as e:
        if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
            blocked_users = load_blocked_users()
            if user_id not in blocked_users:
                blocked_users.append(user_id)
                save_blocked_users(blocked_users)
        else:
            raise e

# --------------------------- ПОДПИСКА НА БОТА (команда /start, инициализация главного меню, проверка подписки на канал) --------------------

def create_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    itembuysub = types.KeyboardButton("Подписка на бота")
    item12 = types.KeyboardButton("Найти бенз")
    item1 = types.KeyboardButton("Калькуляторы")
    item2 = types.KeyboardButton("Траты и ремонты")
    item3 = types.KeyboardButton("Найти транспорт")
    item4 = types.KeyboardButton("Поиск мест")
    item5 = types.KeyboardButton("Погода")
    item6 = types.KeyboardButton("Цены на топливо")
    item7 = types.KeyboardButton("Код региона")
    item8 = types.KeyboardButton("Коды OBD2")
    item9 = types.KeyboardButton("Напоминания")
    item10 = types.KeyboardButton("Антирадар")
    item11 = types.KeyboardButton("Прочее")

    markup.add(itembuysub)
    markup.add(item12)
    markup.add(item1, item2)
    markup.add(item3, item4)
    markup.add(item5, item6)
    markup.add(item7, item8)
    markup.add(item9, item10)
    markup.add(item11)
    return markup

@bot.message_handler(commands=['start'])
@check_subscription_chanal
@rate_limit_with_captcha
@check_chat_state
def start(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username or "неизвестный"
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    now = datetime.now().strftime("%d.%m.%Y в %H:%M")

    update_user_activity(user_id, username, first_name, last_name)

    referral_code = None
    if hasattr(message, 'text') and message.text is not None:
        text_parts = message.text.split()
        if len(text_parts) > 1:
            referral_code = text_parts[-1]

    data = load_payment_data()
    users_data = load_users_data()

    if str(user_id) not in data['subscriptions']['users']:
        data['subscriptions']['users'][str(user_id)] = {
            "username": username,
            "plans": [],
            "total_amount": 0,
            "referral_points": 0,
            "free_feature_trials": {},
            "promo_usage_history": [],
            "referral_milestones": {},
            "points_history": []
        }

    user_plans = data['subscriptions']['users'][str(user_id)].get('plans', [])
    has_active_plan = any(datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M") > datetime.now() for plan in user_plans)
    has_trial = any(plan['plan_name'] == "free" for plan in user_plans)

    is_referral = any(str(user_id) in refs for refs in data['referrals']['stats'].values())

    if is_referral and (user_plans or has_trial):
        markup = create_main_menu()
        bot.send_message(chat_id, f"Добро пожаловать, @{username}!\nВыберите действие из меню:", reply_markup=markup)
        return

    referral_bonus_applied = False
    referral_message = ""
    if referral_code:
        referrer_id = track_referral_activity(referral_code, user_id)
        if referrer_id:
            apply_referral_bonus(referrer_id)
            data = load_payment_data()
            user_plans = data['subscriptions']['users'].get(str(user_id), {}).get('plans', [])
            
            trial_end_date = None
            for plan in user_plans:
                if plan.get('plan_name') == "free" and plan.get('source') != "referral":
                    trial_end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
            
            if not trial_end_date:
                trial_end_date = datetime.now()
                
            new_end = set_free_trial_period(user_id, 1, "referral")
            
            referral_bonus_applied = True
            referral_message = (
                "✨ <b>Вам начислен +1 день подписки</b> за переход по реферальной ссылке!\n\n"
                f"🕒 <b>Начало:</b> {trial_end_date.strftime('%d.%m.%Y в %H:%M')}\n"
                f"⌛ <b>Конец:</b> {(trial_end_date + timedelta(days=1)).strftime('%d.%m.%Y в %H:%M')}\n"
            )

    if not user_plans or not has_trial:
        new_end_trial = set_free_trial_period(user_id, 3)
        start_date = datetime.now().strftime("%d.%m.%Y в %H:%M") 
        end_date_str = new_end_trial.strftime("%d.%m.%Y в %H:%M")  
        referral_link = create_referral_link(user_id)
        trial_message = (
            "🎉 <b>Поздравляем!</b>\n\n"
            "✨ У вас активирован <b>пробный период</b> на <b>3 дня</b>!\n"
            f"🕒 <b>Начало:</b> {start_date}\n"
            f"⌛ <b>Конец:</b> {end_date_str}\n\n"
            "📅 После окончания пробного периода вам необходимо будет оформить подписку, чтобы продолжить пользоваться ботом!\n\n"
            f"🔗 <b>Ваша реферальная ссылка:</b>\n<a href='{referral_link}'>{referral_link}</a>\n"
            "🤝 <b>Приглашайте друзей</b> и получайте до <b>+30 дней и 35% скидки</b>!\n\n"
        )
        bot.send_message(chat_id, trial_message, parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
        if referral_bonus_applied:
            bot.send_message(chat_id, referral_message, parse_mode="HTML")
    elif has_active_plan and referral_bonus_applied:
        referral_link = create_referral_link(user_id)
        active_plans = [plan for plan in user_plans if datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M") > datetime.now()]
        latest_plan = max(active_plans, key=lambda p: datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M"))
        start_date = latest_plan['start_date'] 
        end_date_str = latest_plan['end_date']
        trial_message = (
            "🎉 <b>Поздравляем!</b>\n\n"
            "✨ У вас активирован <b>пробный период</b> на <b>3 дня</b>!\n"
            f"🕒 <b>Начало:</b> {start_date}\n"
            f"⌛ <b>Конец:</b> {end_date_str}\n\n"
            "📅 После окончания пробного периода вам необходимо будет оформить подписку, чтобы продолжить пользоваться ботом!\n\n"
            f"🔗 <b>Ваша реферальная ссылка:</b>\n<a href='{referral_link}'>{referral_link}</a>\n"
            "🤝 <b>Приглашайте друзей</b> и получайте до <b>+30 дней и 35% скидки</b>!\n\n"
        )
        bot.send_message(chat_id, trial_message, parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
        bot.send_message(chat_id, referral_message, parse_mode="HTML")
    else:
        markup = create_main_menu()
        bot.send_message(chat_id, f"Добро пожаловать, @{username}!\nВыберите действие из меню:", reply_markup=markup)
        return

    markup = create_main_menu()
    bot.send_message(chat_id, f"Добро пожаловать, @{username}!\nВыберите действие из меню:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "confirm_subscription")
@text_only_handler
def handle_subscription_confirmation(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    username = call.from_user.username or 'неизвестный'

    bot.answer_callback_query(call.id, text="Проверка статуса подписки...")

    if is_user_subscribed(user_id):
        data = load_payment_data()
        user_data = data['subscriptions']['users'].get(str(user_id), {})

        has_active_plan = any(datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M") > datetime.now()
                             for plan in user_data.get('plans', []))

        if not has_active_plan:
            new_end_trial = set_free_trial_period(user_id, 3)
            referral_link = create_referral_link(user_id)
            markup = create_main_menu()
            combined_message = (
                "🎉 <b>Поздравляем!</b>\n\n"
                "✨ У вас активирован <b>пробный период</b> на <b>3 дня</b>!\n"
                f"🕒 <b>Начало:</b> {datetime.now().strftime('%d.%m.%Y в %H:%M')}\n"
                f"⌛ <b>Конец:</b> {new_end_trial.strftime('%d.%m.%Y в %H:%M')}\n\n"
                "📅 После окончания пробного периода вам необходимо будет оформить подписку, чтобы продолжить пользоваться ботом!\n\n"
                f"🔗 <b>Ваша реферальная ссылка:</b>\n<a href='{referral_link}'>{referral_link}</a>\n"
                "🤝 <b>Приглашайте друзей</b> и получайте до <b>+30 дней и 15% скидки</b>!\n\n"
            )
            bot.send_message(chat_id, combined_message, parse_mode="HTML")
            bot.send_message(chat_id, f"Добро пожаловать, @{username}!\nВыберите действие из меню:", reply_markup=markup)
        else:
            markup = create_main_menu()
            bot.send_message(chat_id, f"Добро пожаловать, @{username}!\nВыберите действие из меню:", reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, text="Вы еще не подписаны! Пожалуйста, подпишитесь!")
        bot.send_message(chat_id, "Вы еще не подписаны на канал! Подпишитесь, чтобы продолжить!", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "В главное меню")
@check_function_state_decorator('В главное меню')
@track_usage('В главное меню')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_menu(message):
    start(message)