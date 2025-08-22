from core.imports import wraps, telebot, types, os, json, re, pytz, datetime, timedelta, ReplyKeyboardMarkup, ReplyKeyboardRemove
from core.bot_instance import bot
from handlers.user.subscription.subscription_main import payments_function
from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage
)

def return_to_menu(message):
    from handlers.user.user_main_menu import return_to_menu as _f
    return _f(message)

def load_payment_data():
    from handlers.user.user_main_menu import load_payment_data as _f
    return _f()

def save_payments_data(data):
    from handlers.user.user_main_menu import save_payments_data as _f
    return _f(data)

def load_users_data():
    from handlers.user.user_main_menu import load_users_data as _f
    return _f()

def return_to_scores_menu(message):
    from handlers.user.subscription.points import points_menu as _f
    return _f(message)

# ------------------------------------------------ ПОДПИСКА НА БОТА (подарки) -----------------------------------------

def escape_markdown(text):
    return re.sub(r'([*_`])', r'\\\1', text)

def split_message(message, max_length=4000):
    if len(message) <= max_length:
        return [message]
    
    parts = []
    current_part = ""
    
    for line in message.split('\n'):
        if len(current_part) + len(line) + 1 > max_length:
            parts.append(current_part)
            current_part = line + '\n'
        else:
            current_part += line + '\n'
    
    if current_part:
        parts.append(current_part)
    
    return parts

def format_number(number):
    try:
        n = float(number)
    except (TypeError, ValueError):
        return str(number)
    if n.is_integer():
        return str(int(n))
    return f"{n:.2f}"

def format_time(minutes):
    if isinstance(minutes, str):
        try:
            minutes = float(minutes.split()[0].replace(',', '.'))
        except (ValueError, IndexError):
            return minutes
    if minutes < 60:
        return f"{format_number(minutes)} мин."
    days = minutes // 1440
    hours = (minutes % 1440) // 60
    mins = minutes % 60
    parts = []
    if days:
        parts.append(f"{format_number(days)} дн.")
    if hours:
        parts.append(f"{format_number(hours)} ч.")
    if mins:
        parts.append(f"{format_number(mins)} мин.")
    return " ".join(parts)

def clean_escaped_text(text):
    return re.sub(r'\\([_*[\]()~`>#+\-=|{}.!])', r'\1', text)

def pluralize_points(points):
    if isinstance(points, str):
        try:
            points = float(points)
        except ValueError:
            return "баллов"
    points = int(points)
    if points % 10 == 1 and points % 100 != 11:
        return "балл"
    elif 2 <= points % 10 <= 4 and (points % 100 < 10 or points % 100 >= 20):
        return "балла"
    else:
        return "баллов"

@bot.message_handler(func=lambda message: message.text == "Подарки")
@check_function_state_decorator('Подарки')
@track_usage('Подарки')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def gifts_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Подарить баллы', 'Подарить время', 'История подарков')
    markup.add('Вернуться в баллы')
    markup.add('Вернуться в подписку')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите действие из меню подарков:", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Вернуться в подарки")
@check_function_state_decorator('Вернуться в подарки')
@track_usage('Вернуться в подарки')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_gifts_menu(message):
    gifts_menu(message)

# ------------------------------------------------ ПОДПИСКА НА БОТА (подарки) -----------------------------------------

def format_number(number):
    try:
        n = float(number)
    except (TypeError, ValueError):
        return str(number)
    if n.is_integer():
        return str(int(n))
    return f"{n:.2f}"

def format_time(minutes):
    if isinstance(minutes, str):
        try:
            minutes = float(minutes.split()[0].replace(',', '.'))
        except (ValueError, IndexError):
            return minutes
    if minutes < 60:
        return f"{format_number(minutes)} мин."
    days = minutes // 1440
    hours = (minutes % 1440) // 60
    mins = minutes % 60
    parts = []
    if days:
        parts.append(f"{format_number(days)} дн.")
    if hours:
        parts.append(f"{format_number(hours)} ч.")
    if mins:
        parts.append(f"{format_number(mins)} мин.")
    return " ".join(parts)

def clean_escaped_text(text):
    return re.sub(r'\\([_*[\]()~`>#+\-=|{}.!])', r'\1', text)

def pluralize_points(points):
    if isinstance(points, str):
        try:
            points = float(points)
        except ValueError:
            return "баллов"
    points = int(points)
    if points % 10 == 1 and points % 100 != 11:
        return "балл"
    elif 2 <= points % 10 <= 4 and (points % 100 < 10 or points % 100 >= 20):
        return "балла"
    else:
        return "баллов"

@bot.message_handler(func=lambda message: message.text == "Подарки")
@check_function_state_decorator('Подарки')
@track_usage('Подарки')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def gifts_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Подарить баллы', 'Подарить время', 'История подарков')
    markup.add('Вернуться в баллы')
    markup.add('Вернуться в подписку')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите действие из меню подарков:", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Вернуться в подарки")
@check_function_state_decorator('Вернуться в подарки')
@track_usage('Вернуться в подарки')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_gifts_menu(message):
    gifts_menu(message)

# ------------------------------------------------ ПОДПИСКА НА БОТА (подарить баллы) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "Подарить баллы")
@check_function_state_decorator('Подарить баллы')
@track_usage('Подарить баллы')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def gift_points_handler(message):
    user_id = str(message.from_user.id)
    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(user_id, {})
    points = user_data.get('referral_points', 0)
    
    last_gift_time = next(
        (entry['date'] for entry in reversed(user_data.get('points_history', []))
         if entry['action'] == "spent" and "подарок @" in entry['reason'].lower() and "времени" not in entry['reason'].lower()),
        "01.01.2025 в 00:00"
    )
    last_gift_dt = datetime.strptime(last_gift_time, "%d.%m.%Y в %H:%M")
    if (datetime.now() - last_gift_dt).total_seconds() < 24 * 3600:
        remaining_time = timedelta(seconds=24 * 3600 - (datetime.now() - last_gift_dt).total_seconds())
        hours_left = remaining_time.seconds // 3600
        minutes_left = (remaining_time.seconds % 3600) // 60
        bot.send_message(message.chat.id, (
            f"⚠️ Вы уже дарили баллы сегодня!\n"
            f"⏳ Следующий подарок баллов доступен через {hours_left} ч. {minutes_left} мин."
        ), parse_mode="Markdown")
        return_to_scores_menu(message)
        return
    
    if points < 0.5:
        bot.send_message(message.chat.id, (
            f"❌ У вас недостаточно баллов для подарка!\n\n"
            f"💰 *Доступно баллов:* {format_number(points)}\n"
            f"👉 Пожалуйста, накопите больше баллов и попробуйте снова"
        ), parse_mode="Markdown")
        return_to_scores_menu(message)
        return
    
    referrals = list(set(data['referrals']['stats'].get(user_id, [])))
    if referrals:
        referral_message = "*Список ваших рефералов для подарка:*\n\n"
        for idx, referral_id in enumerate(referrals, 1):
            referral_username = data['subscriptions']['users'].get(referral_id, {}).get('username', 'неизвестный')
            escaped_username = escape_markdown(referral_username)
            referral_message += f"👤 №{idx}. {escaped_username} - `{referral_id}`\n"
        bot.send_message(message.chat.id, referral_message, parse_mode="Markdown")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в подарки", "Вернуться в баллы")
    markup.add(types.KeyboardButton("Вернуться в подписку"))
    markup.add(types.KeyboardButton("В главное меню"))
    bot.send_message(message.chat.id, (
        f"*Подарить баллы:*\n\n"
        f"💰 *Ваши баллы:* {format_number(points)}\n\n"
        "Введите @username или id пользователя (можно из вашего списка), которому хотите подарить баллы:"
    ), reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, user_process_gift_recipient, points)

@text_only_handler
def user_process_gift_recipient(message, sender_points):
    if message.text == "Вернуться в баллы":
        return_to_scores_menu(message)
        return
    if message.text == "Вернуться в подарки":
        return_to_gifts_menu(message)
        return
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    user_id = str(message.from_user.id)
    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(user_id, {})
    sender_username = escape_markdown(user_data.get('username', f"@{user_id}"))
    recipient_input = message.text.strip()
    
    recipient_id = None
    if recipient_input.startswith('@'):
        recipient_id = next((uid for uid, data_user in data['subscriptions']['users'].items() 
                            if data_user.get('username', '').lower() == recipient_input.lower()), None)
    elif recipient_input.isdigit():
        if recipient_input in data['subscriptions']['users']:
            recipient_id = recipient_input
    
    if not recipient_id:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в подарки", "Вернуться в баллы")
        markup.add(types.KeyboardButton("Вернуться в подписку"))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, (
            "❌ Пользователь не найден! Проверьте username или id\n\n"
            "Введите @username или id пользователя:"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, user_process_gift_recipient, sender_points)
        return
    
    if recipient_id == user_id:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в подарки", "Вернуться в баллы")
        markup.add(types.KeyboardButton("Вернуться в подписку"))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, (
            "❌ Нельзя подарить баллы самому себе!\n\n"
            "👉 Пожалуйста, выберите другого пользователя"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, user_process_gift_recipient, sender_points)
        return
    
    users_data = load_users_data()
    join_date_str = users_data.get(recipient_id, {}).get('join_date', "01.01.2025 в 00:00")
    join_date = datetime.strptime(join_date_str, "%d.%m.%Y в %H:%M")
    if (datetime.now() - join_date).total_seconds() < 24 * 3600:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в подарки", "Вернуться в баллы")
        markup.add(types.KeyboardButton("Вернуться в подписку"))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, (
            "❌ Нельзя дарить баллы пользователям, зарегистрированным менее 24 часов назад!\n"
            "👉 Пожалуйста, выберите другого пользователя"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, user_process_gift_recipient, sender_points)
        return
    
    recipient_username = escape_markdown(data['subscriptions']['users'][recipient_id].get('username', 'неизвестный'))
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в подарки", "Вернуться в баллы")
    markup.add(types.KeyboardButton("Вернуться в подписку"))
    markup.add(types.KeyboardButton("В главное меню"))
    bot.send_message(message.chat.id, (
        f"🎁 *Подарок баллов*\n\n"
        f"📤 *Отправитель:* {sender_username} (`{user_id}`)\n"
        f"📥 *Получатель:* {recipient_username} (`{recipient_id}`)\n\n"
        f"💰 *Доступно баллов:* {format_number(sender_points)}\n\n"
        "Введите количество баллов для подарка:"
    ), reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_gift_amount, recipient_id, sender_points)

@text_only_handler
def process_gift_amount(message, recipient_id, sender_points):
    if message.text == "Вернуться в баллы":
        return_to_scores_menu(message)
        return
    if message.text == "Вернуться в подарки":
        return_to_gifts_menu(message)
        return
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    user_id = str(message.from_user.id)
    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(user_id, {})
    sender_username = escape_markdown(user_data.get('username', f"@{user_id}"))
    
    try:
        gift_points = float(message.text.replace(',', '.'))
        if gift_points < 0.5:
            raise ValueError("⚠️ Минимальное количество баллов — 0.5!")
        if gift_points > sender_points:
            raise ValueError(f"❌ Недостаточно баллов!\n💰 *Доступно баллов:* {format_number(sender_points)}")
        if gift_points % 0.5 != 0:
            raise ValueError("⚠️ Баллы должны быть кратны 0.5!")
        
        sender_username_raw = user_data.get('username', f"@{user_id}")
        recipient_username = data['subscriptions']['users'][recipient_id].get('username', 'неизвестный')
        
        data['subscriptions']['users'][user_id]['referral_points'] -= gift_points
        data['subscriptions']['users'][user_id].setdefault('points_history', []).append({
            "action": "spent",
            "points": gift_points,
            "reason": f"подарок {recipient_username}",
            "date": datetime.now().strftime("%d.%m.%Y в %H:%M")
        })
        
        data['subscriptions']['users'].setdefault(recipient_id, {}).setdefault('referral_points', 0)
        data['subscriptions']['users'][recipient_id]['referral_points'] += gift_points
        data['subscriptions']['users'][recipient_id].setdefault('points_history', []).append({
            "action": "earned",
            "points": gift_points,
            "reason": f"подарок от {sender_username_raw}",
            "date": datetime.now().strftime("%d.%m.%Y в %H:%M")
        })
        
        save_payments_data(data)
        
        bot.send_message(user_id, (
            f"🎉 *Вы подарили* {escape_markdown(recipient_username)} *{format_number(gift_points)} {pluralize_points(gift_points)}!*\n"
        ), parse_mode="Markdown")
        try:
            bot.send_message(recipient_id, (
                f"🎁 *{sender_username} подарил вам {format_number(gift_points)} {pluralize_points(gift_points)}!*\n"
                "🚀 Используйте их в системе баллов!"
            ), parse_mode="Markdown")
        except:
            pass
        
        gifts_menu(message)
        
    except ValueError as e:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в подарки", "Вернуться в баллы")
        markup.add(types.KeyboardButton("Вернуться в подписку"))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_gift_amount, recipient_id, sender_points)

# ------------------------------------------------ ПОДПИСКА НА БОТА (подарить время) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "Подарить время")
@check_function_state_decorator('Подарить время')
@track_usage('Подарить время')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def gift_time_handler(message):
    user_id = str(message.from_user.id)
    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(user_id, {})
    
    last_gift_time = next(
        (entry['date'] for entry in reversed(user_data.get('points_history', []))
         if "подарок времени" in entry['reason'].lower() and entry['action'] == "spent"),
        "01.01.2025 в 00:00"
    )
    last_gift_dt = datetime.strptime(last_gift_time, "%d.%m.%Y в %H:%M")
    if (datetime.now() - last_gift_dt).total_seconds() < 24 * 3600:
        remaining_time = timedelta(seconds=24 * 3600 - (datetime.now() - last_gift_dt).total_seconds())
        hours_left = remaining_time.seconds // 3600
        minutes_left = (remaining_time.seconds % 3600) // 60
        bot.send_message(message.chat.id, (
            f"⚠️ Вы уже дарили время сегодня!\n"
            f"⏳ Следующий подарок времени доступен через {hours_left} ч. {minutes_left} мин."
        ), parse_mode="Markdown")
        return_to_gifts_menu(message)
        return

    giftable_plans = [
        plan for plan in user_data.get('plans', [])
        if (
            plan['plan_name'] in ['points_bonus', 'gift_time', 'exchange_time']
            or (
                plan['plan_name'] in ['trial', 'weekly', 'monthly', 'quarterly', 'semiannual', 'yearly', 'store_time', 'custom']
                and plan['source'] in ['user', 'store']
            )
        )
        and datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M") > datetime.now()
    ]
    
    if not giftable_plans:
        bot.send_message(message.chat.id, (
            "❌ У вас нет активных подписок, которые можно подарить!\n"
            "🚀 Купите подписку или используйте баллы, чтобы получить время для подарка!"
        ), parse_mode="Markdown")
        return_to_gifts_menu(message)
        return
    
    now = datetime.now()
    total_remaining_minutes = 0
    for plan in giftable_plans:
        end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
        if end_date > now:
            total_remaining_minutes += int((end_date - now).total_seconds() // 60)
    
    time_description = format_time(total_remaining_minutes)
    
    if total_remaining_minutes < 1440:  
        bot.send_message(message.chat.id, (
            f"❌ У вас осталось менее 1 дня подписки для подарка!\n\n"
            f"⏳ *Доступно времени:* {time_description}\n"
            f"👉 Пожалуйста, продлите подписку, чтобы дарить время!"
        ), parse_mode="Markdown")
        return_to_gifts_menu(message)
        return
    
    referrals = list(set(data['referrals']['stats'].get(user_id, [])))
    if referrals:
        referral_message = "*Список ваших рефералов для подарка:*\n\n"
        for idx, referral_id in enumerate(referrals, 1):
            referral_username = data['subscriptions']['users'].get(referral_id, {}).get('username', 'неизвестный')
            escaped_username = escape_markdown(referral_username)
            referral_message += f"👤 №{idx}. {escaped_username} - `{referral_id}`\n"
        bot.send_message(message.chat.id, referral_message, parse_mode="Markdown")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в подарки", "Вернуться в баллы")
    markup.add(types.KeyboardButton("Вернуться в подписку"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(message.chat.id, (
        f"🎁 *Подарить время:*\n\n"
        f"⏳ *Доступное время:* {time_description}\n\n"
        "Введите @username или id пользователя (можно из вашего списка), которому хотите подарить время:"
    ), reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, user_process_gift_time_recipient, total_remaining_minutes)

@text_only_handler
def user_process_gift_time_recipient(message, total_available_minutes):
    if message.text == "Вернуться в баллы":
        return_to_scores_menu(message)
        return
    if message.text == "Вернуться в подарки":
        return_to_gifts_menu(message)
        return
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    user_id = str(message.from_user.id)
    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(user_id, {})
    sender_username = escape_markdown(user_data.get('username', f"@{user_id}"))
    recipient_input = message.text.strip()
    
    recipient_id = None
    if recipient_input.startswith('@'):
        recipient_id = next(
            (uid for uid, data_user in data['subscriptions']['users'].items()
             if data_user.get('username', '').lower() == recipient_input.lower()), None
        )
    elif recipient_input.isdigit():
        if recipient_input in data['subscriptions']['users']:
            recipient_id = recipient_input
    
    if not recipient_id:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в подарки", "Вернуться в баллы") 
        markup.add(types.KeyboardButton("Вернуться в подписку"))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, (
            "❌ Пользователь не найден! Проверьте username или id\n\n"
            "Введите @username или id пользователя:"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, user_process_gift_time_recipient, total_available_minutes)
        return
    
    if recipient_id == user_id:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в подарки", "Вернуться в баллы") 
        markup.add(types.KeyboardButton("Вернуться в подписку"))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, (
            "❌ Нельзя подарить время самому себе!\n"
            "👉 Пожалуйста, выберите другого пользователя"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, user_process_gift_time_recipient, total_available_minutes)
        return
    
    users_data = load_users_data()
    join_date_str = users_data.get(recipient_id, {}).get('join_date', "01.01.2025 в 00:00")
    join_date = datetime.strptime(join_date_str, "%d.%m.%Y в %H:%M")
    if (datetime.now() - join_date).total_seconds() < 24 * 3600:
        bot.send_message(message.chat.id, (
            "❌ Нельзя дарить время пользователям, зарегистрированным менее 24 часов назад!\n"
            "👉 Пожалуйста, выберите другого пользователя"
        ), parse_mode="Markdown")
        return_to_gifts_menu(message)
        return
    
    recipient_username = escape_markdown(data['subscriptions']['users'][recipient_id].get('username', 'неизвестный'))
    time_description = format_time(total_available_minutes)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Минуты"), types.KeyboardButton("Часы"), types.KeyboardButton("Дни"))
    markup.add("Вернуться в подарки", "Вернуться в баллы")
    markup.add(types.KeyboardButton("Вернуться в подписку"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(message.chat.id, (
        f"🎁 *Подарок времени*\n\n"
        f"📤 *Отправитель:* {sender_username} (`{user_id}`)\n"
        f"📥 *Получатель:* {recipient_username} (`{recipient_id}`)\n\n"
        f"⏳ *Доступно времени:* {time_description}\n\n"
        "Выберите единицу времени для подарка:"
    ), reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, user_process_gift_time_unit, recipient_id, total_available_minutes)

@text_only_handler
def user_process_gift_time_unit(message, recipient_id, total_available_minutes):
    if message.text == "Вернуться в баллы":
        return_to_scores_menu(message)
        return
    if message.text == "Вернуться в подарки":
        return_to_gifts_menu(message)
        return
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    user_id = str(message.from_user.id)
    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(user_id, {})
    sender_username = escape_markdown(user_data.get('username', f"@{user_id}"))
    recipient_username = escape_markdown(data['subscriptions']['users'][recipient_id].get('username', 'неизвестный'))
    time_description = format_time(total_available_minutes)
    
    unit = message.text
    if unit not in ["Минуты", "Часы", "Дни"]:
        bot.send_message(message.chat.id, (
            "❌ Выберите одну из предложенных единиц времени!\n"
            "👉 Пожалуйста, попробуйте снова"
        ), parse_mode="Markdown")
        user_process_gift_time_recipient(message, total_available_minutes)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в подарки", "Вернуться в баллы")
    markup.add(types.KeyboardButton("Вернуться в подписку"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    unit_prompt = {
        "Минуты": "минут",
        "Часы": "часов",
        "Дни": "дней"
    }[unit]
    
    bot.send_message(message.chat.id, (
        f"🎁 *Подарок времени*\n\n"
        f"📤 *Отправитель:* {sender_username} (`{user_id}`)\n"
        f"📥 *Получатель:* {recipient_username} (`{recipient_id}`)\n\n"
        f"⏳ *Доступно времени:* {time_description}\n\n"
        f"Введите количество {unit_prompt} для подарка:"
    ), reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, user_process_gift_time_amount, recipient_id, total_available_minutes, unit)

@text_only_handler
def user_process_gift_time_amount(message, recipient_id, total_available_minutes, unit):
    if message.text == "Вернуться в баллы":
        return_to_scores_menu(message)
        return
    if message.text == "Вернуться в подарки":
        return_to_gifts_menu(message)
        return
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    user_id = str(message.from_user.id)
    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(user_id, {})
    sender_username = user_data.get('username', f"@{user_id}")
    recipient_username = data['subscriptions']['users'][recipient_id].get('username', 'неизвестный')
    time_description = format_time(total_available_minutes)
    
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError("⚠️ Количество должно быть положительным!")
        
        if unit == "Минуты":
            gift_minutes = amount
        elif unit == "Часы":
            gift_minutes = amount * 60
        elif unit == "Дни":
            gift_minutes = amount * 1440
        
        if gift_minutes > total_available_minutes:
            raise ValueError(f"❌ Недостаточно времени!\n⏳ *Доступно времени:* {time_description}")
        
        gift_duration = timedelta(minutes=gift_minutes)
        remaining_minutes = gift_minutes
        
        user_plans = data['subscriptions']['users'][user_id]['plans']
        for plan in sorted(
            [p for p in user_plans if p['plan_name'] in ['trial', 'weekly', 'monthly', 'quarterly', 'semiannual', 'yearly'] and p['source'] == 'user'],
            key=lambda x: datetime.strptime(x['end_date'], "%d.%m.%Y в %H:%M")
        ):
            if remaining_minutes <= 0:
                break
            end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
            if end_date <= datetime.now():
                continue
            available_minutes = int((end_date - datetime.now()).total_seconds() // 60)
            minutes_to_deduct = min(remaining_minutes, available_minutes)
            new_end_date = end_date - timedelta(minutes=minutes_to_deduct)
            plan['end_date'] = new_end_date.strftime("%d.%m.%Y в %H:%M")
            remaining_minutes -= minutes_to_deduct
        
        user_plans[:] = [p for p in user_plans if datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") > datetime.now()]
        
        recipient_data = data['subscriptions']['users'].setdefault(recipient_id, {
            "plans": [],
            "total_amount": 0,
            "username": recipient_username,
            "referral_points": 0,
            "free_feature_trials": {},
            "promo_usage_history": [],
            "referral_milestones": {},
            "points_history": []
        })
        
        latest_end = max(
            [datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") for p in recipient_data['plans']] or [datetime.now()]
        )
        new_end = latest_end + gift_duration
        
        recipient_data['plans'].append({
            "plan_name": "gift_time",
            "start_date": latest_end.strftime("%d.%m.%Y в %H:%M"),
            "end_date": new_end.strftime("%d.%m.%Y в %H:%M"),
            "price": 0,
            "source": f"gift_from_{user_id}"
        })
        
        data['subscriptions']['users'][user_id].setdefault('points_history', []).append({
            "action": "spent",
            "points": 0,
            "reason": f"подарок времени {recipient_username}: {gift_minutes} минут",
            "date": datetime.now().strftime("%d.%m.%Y в %H:%M")
        })
        
        recipient_data.setdefault('points_history', []).append({
            "action": "earned",
            "points": 0,
            "reason": f"подарок времени от {sender_username}: {gift_minutes} минут",
            "date": datetime.now().strftime("%d.%m.%Y в %H:%M")
        })
        
        save_payments_data(data)
        
        gift_description = format_time(gift_minutes)
        
        active_plans = [p for p in user_plans if datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") > datetime.now()]
        end_date = min([datetime.strptime(p['end_date'], '%d.%m.%Y в %H:%M') for p in active_plans] or [datetime.now()]).strftime('%d.%m.%Y в %H:%M')
        
        bot.send_message(user_id, (
            f"🎉 *Вы подарили* {escape_markdown(recipient_username)} *{gift_description}!*\n"
            f"⏳ Ваша подписка теперь активна до: {end_date}"
        ), parse_mode="Markdown")
        
        bot.send_message(recipient_id, (
            f"🎁 *{escape_markdown(sender_username)} подарил вам {gift_description}!*\n"
            f"⏳ Ваша подписка теперь активна до: {new_end.strftime('%d.%m.%Y в %H:%M')}"
        ), parse_mode="Markdown")
        
        gifts_menu(message)
        
    except ValueError as e:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в подарки", "Вернуться в баллы")  
        markup.add(types.KeyboardButton("Вернуться в подписку"))
        markup.add(types.KeyboardButton("В главное меню"))
        error_msg = str(e) if str(e).startswith(("Недостаточно", "Количество")) else "Введите корректное число!"
        bot.send_message(message.chat.id, f"Произошла ошибка: {error_msg}!\nПожалуйста, попробуйте снова", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, user_process_gift_time_amount, recipient_id, total_available_minutes, unit)

# ------------------------------------------------ ПОДПИСКА НА БОТА (история подарков) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "История подарков")
@check_function_state_decorator('История подарков')
@track_usage('История подарков')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_gifts_history(message):
    user_id = str(message.from_user.id)
    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(user_id, {})
    history = user_data.get('points_history', [])
    gift_entries = [entry for entry in history if "подарок" in entry['reason'].lower()]

    if not gift_entries:
        bot.send_message(message.chat.id, "❌ У вас нет истории подарков!", parse_mode="Markdown")
        gifts_menu(message)
        return

    username = escape_markdown(user_data.get('username', f"@{user_id}"))

    history_summary = f"*История подарков*:\n\n"
    for idx, entry in enumerate(gift_entries, 1):
        action = "Подарено" if entry['action'] == "spent" else "Получено"
        gift_type = []
        if entry['points'] > 0:
            gift_type.append(f"{format_number(entry['points'])} {pluralize_points(entry['points'])}")
        if "времени" in entry['reason'].lower():
            reason_parts = clean_escaped_text(entry['reason']).split(': ')
            if len(reason_parts) > 1:
                time_part = reason_parts[-1].split(' (от админа)')[0]
                gift_type.append(format_time(time_part))
            else:
                gift_type.append("неизвестное время")
        gift_type = " и ".join(gift_type) if gift_type else "неизвестный подарок"
        reason = escape_markdown(clean_escaped_text(entry['reason']))
        history_summary += (
            f"🎁 *№{idx}. {action}:*\n\n"
            f"💰 *Подарок:* {gift_type}\n"
            f"📅 *Дата:* {entry['date']}\n\n"
        )

    message_parts = split_message(history_summary)
    for part in message_parts:
        bot.send_message(message.chat.id, part, parse_mode="Markdown")

    gifts_menu(message)