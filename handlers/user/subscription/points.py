from core.imports import wraps, telebot, types, os, json, re, pytz, datetime, timedelta, ReplyKeyboardMarkup, ReplyKeyboardRemove
from core.bot_instance import bot
from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
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

def get_paid_features():
    from handlers.user.user_main_menu import PAID_FEATURES as _PF
    return _PF

def payments_function(message, show_description=False):
    from handlers.user.subscription.subscription_main import payments_function as _f
    return _f(message, show_description=show_description)

def split_message(message, max_length=4000):
    from handlers.user.subscription.gifts import split_message as _f
    return _f(message, max_length=max_length)

def pluralize_points(points):
    from handlers.user.subscription.gifts import pluralize_points as _f
    return _f(points)

# ------------------------------------------------ ПОДПИСКА НА БОТА (баллы) -----------------------------------------

def escape_markdown(text):
    return re.sub(r'([*_`])', r'\\\1', text)

@bot.message_handler(func=lambda message: message.text == "Баллы")
@check_function_state_decorator('Баллы')
@track_usage('Баллы')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def points_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Ваши баллы', 'Обменять баллы', 'Подарки')
    markup.add('Вернуться в подписку')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите действие из меню баллов:", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Вернуться в баллы")
@check_function_state_decorator('Вернуться в баллы')
@track_usage('Вернуться в баллы')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_scores_menu(message):
    points_menu(message)

# ------------------------------------------------ ПОДПИСКА НА БОТА (ваши баллы) -----------------------------------------

def format_number(number):
    try:
        n = float(number)
    except (TypeError, ValueError):
        return str(number)
    if n.is_integer():
        return str(int(n))
    return f"{n:.2f}"

def format_time(minutes):
    if minutes < 60:
        return f"{format_number(minutes)} мин."
    days = minutes // 1440
    hours = (minutes % 1440) // 60
    mins = (minutes % 1440) % 60
    parts = []
    if days:
        parts.append(f"{format_number(days)} дн.")
    if hours:
        parts.append(f"{format_number(hours)} ч.")
    if mins:
        parts.append(f"{format_number(mins)} мин.")
    return " ".join(parts)

@bot.message_handler(func=lambda message: message.text == "Ваши баллы")
@check_function_state_decorator('Ваши баллы')
@track_usage('Ваши баллы')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_points(message):
    user_id = str(message.from_user.id)
    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(user_id, {})
    history = user_data.get('points_history', [])
    
    points = user_data.get('referral_points', 0)
    
    total_earned = sum(entry['points'] for entry in history if entry['action'] == 'earned')
    earned_daily = sum(entry['points'] for entry in history if entry['action'] == 'earned' and entry['reason'] == 'Ежедневный вход')
    earned_admin = sum(entry['points'] for entry in history if entry['action'] == 'earned' and entry['reason'].startswith('Начисление от администратора'))
    earned_gifts = sum(entry['points'] for entry in history if entry['action'] == 'earned' and ('подарок от' in entry['reason'].lower() or 'Подарок от' in entry['reason']))
    earned_first_purchase = sum(entry['points'] for entry in history if entry['action'] == 'earned' and entry['reason'].startswith('Первая покупка подписки'))
    earned_points_purchase = sum(entry['points'] for entry in history if entry['action'] == 'earned' and entry['reason'].startswith('Покупка') and 'баллов' in entry['reason'])
    earned_referrals = sum(entry['points'] for entry in history if entry['action'] == 'earned' and 'Реферал' in entry['reason'])
    earned_top_referrals = sum(entry['points'] for entry in history if entry['action'] == 'earned' and 'Топ-10 рефералов' in entry['reason'])
    earned_purchases = sum(entry['points'] for entry in history if entry['action'] == 'earned' and entry['reason'].startswith('Покупка подписки'))

    total_spent = sum(entry['points'] for entry in history if entry['action'] == 'spent')
    spent_gifts = sum(entry['points'] for entry in history if entry['action'] == 'spent' and 'подарок' in entry['reason'].lower())
    spent_time = sum(entry['points'] for entry in history if entry['action'] == 'spent' and entry['reason'].startswith('Обмен на') and any(unit in entry['reason'] for unit in ['дн.', 'ч.', 'мин.']))
    spent_discounts = sum(entry['points'] for entry in history if entry['action'] == 'spent' and entry['reason'].startswith('Обмен на') and '%' in entry['reason'])
    spent_features = sum(entry['points'] for entry in history if entry['action'] == 'spent' and entry['reason'].startswith('Обмен на функцию'))
    spent_admin_delete = sum(entry['points'] for entry in history if entry['action'] == 'spent' and entry['reason'] == 'удаление покупок администратором')
    spent_admin = sum(entry['points'] for entry in history if entry['action'] == 'spent' and entry['reason'].lower() == 'списание администратором')

    gifted_time_minutes = 0
    received_time_minutes = 0
    for entry in history:
        time_str = None
        if entry['reason'].startswith('Обмен на') and any(unit in entry['reason'] for unit in ['дн.', 'ч.', 'мин.']):
            time_str = entry['reason'].split('Обмен на ')[1]
        elif 'подарок времени' in entry['reason'].lower() and any(unit in entry['reason'] for unit in ['дн.', 'ч.', 'мин.', 'минут']):
            time_parts = entry['reason'].split(': ')
            if len(time_parts) > 1:
                time_str = time_parts[1]
        
        if time_str:
            days = hours = minutes = 0
            if 'дн.' in time_str:
                days_match = re.search(r'(\d+\.?\d*)\s*дн\.', time_str)
                if days_match:
                    days = float(days_match.group(1))
            if 'ч.' in time_str:
                hours_match = re.search(r'(\d+\.?\d*)\s*ч\.', time_str)
                if hours_match:
                    hours = float(hours_match.group(1))
            if 'мин.' in time_str or 'минут' in time_str:
                minutes_match = re.search(r'(\d+\.?\d*)\s*(мин\.|минут)', time_str)
                if minutes_match:
                    minutes = float(minutes_match.group(1))
            total_minutes = days * 24 * 60 + hours * 60 + minutes
            if entry['action'] == 'spent':
                gifted_time_minutes += total_minutes
            elif entry['action'] == 'earned':
                received_time_minutes += total_minutes

    points_summary = (
        f"💰 *Ваши баллы*\n\n"
        f"🎁 *Текущие баллы:* {format_number(points)}\n\n"
        f"🔥 *Всего заработано:* {format_number(total_earned)}\n"
        f"  • Ежедневный вход: {format_number(earned_daily)}\n"
        f"  • Начисление от администратора: {format_number(earned_admin)}\n"
        f"  • Подарок от других: {format_number(earned_gifts)}\n"
        f"  • Первая покупка подписки: {format_number(earned_first_purchase)}\n"
        f"  • Покупка баллов: {format_number(earned_points_purchase)}\n"
        f"  • За рефералов: {format_number(earned_referrals)}\n"
        f"  • За топ рефералов: {format_number(earned_top_referrals)}\n"
        f"  • За покупки: {format_number(earned_purchases)}\n\n"
        f"💸 *Всего потрачено:* {format_number(total_spent)}\n"
        f"  • Подарок другим: {format_number(spent_gifts)}\n"
        f"  • Обмен на время: {format_number(spent_time)}\n"
        f"  • Обмен на скидки: {format_number(spent_discounts)}\n"
        f"  • Обмен на функции: {format_number(spent_features)}\n"
        f"  • Удаление покупок администратором: {format_number(spent_admin_delete)}\n"
        f"  • Списание администратором: {format_number(spent_admin)}\n\n"
        f"⏳ *Подарено времени:* {format_time(gifted_time_minutes)}\n"
        f"⏳ *Получено времени:* {format_time(received_time_minutes)}"
    )

    message_parts = split_message(points_summary)
    for part in message_parts:
        bot.send_message(message.chat.id, part, parse_mode="Markdown")

# ------------------------------------------------ ПОДПИСКА НА БОТА (обменять баллы) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "Обменять баллы")
@check_function_state_decorator('Обменять баллы')
@track_usage('Обменять баллы')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def exchange_points_handler(message):
    user_id = str(message.from_user.id)
    data = load_payment_data()
    points = data['subscriptions']['users'].get(user_id, {}).get('referral_points', 0)
    
    if points < 2: 
        bot.send_message(message.chat.id, "❌ Недостаточно баллов!", parse_mode="Markdown")
        return_to_scores_menu(message)
        return
    
    has_subscription = False
    plans = data['subscriptions']['users'].get(user_id, {}).get('plans', [])
    now = datetime.now()
    for plan in plans:
        end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
        if end_date > now:
            has_subscription = True
            break
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("Обмен на время"), telebot.types.KeyboardButton("Обмен на скидку"), telebot.types.KeyboardButton("Обмен на функцию"))
    markup.add(telebot.types.KeyboardButton("Вернуться в баллы"))
    markup.add(telebot.types.KeyboardButton("Вернуться в подписку"))
    markup.add(telebot.types.KeyboardButton("В главное меню"))
    
    exchange_rate = 1.0 / 5.0  
    
    bot.send_message(message.chat.id, (
        f"*Обмен баллов:*\n\n"
        f"🎁 *Текущие баллы:* {format_number(points)}\n\n"
        f"🔄 *Возможные обмены:*\n"
        f"⏳ - *Время подписки:* _5 баллов = 1 час_\n"
        f"🔓 - *Доступ к функциям:* _2 балла = 15 минут_\n"
        f"🏷️ - *Скидка:* _10 баллов = 5% (макс. 35%)_\n\n"
        "Выберите опцию:"
    ), reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_exchange_option, points, exchange_rate, has_subscription)

@text_only_handler
def process_exchange_option(message, points, exchange_rate, has_subscription):
    if message.text == "Вернуться в баллы":
        return_to_scores_menu(message)
        return
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    user_id = str(message.from_user.id)
    data = load_payment_data()
    
    if message.text == "Обмен на время":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton("Вернуться в баллы"))
        markup.add(telebot.types.KeyboardButton("Вернуться в подписку"))
        markup.add(telebot.types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, (
            f"*Обмен баллов:*\n\n"
            f"🎁 *Текущие баллы:* {format_number(points)}\n"
            f"⏳ *Обмен на время:* _5 баллов = 1 час_\n\n"
            "Введите количество баллов для обмена:"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_points_exchange, exchange_rate)
    elif message.text == "Обмен на скидку":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton("Вернуться в баллы"))
        markup.add(telebot.types.KeyboardButton("Вернуться в подписку"))
        markup.add(telebot.types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, (
            f"*Обмен баллов:*\n\n"
            f"🎁 *Текущие баллы:* {format_number(points)}\n"
            f"🏷️ *Обмен на скидку:* _10 баллов = 5% (макс. 35%)_\n\n"
            "Введите количество баллов для обмена:"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_discount_exchange)
    elif message.text == "Обмен на функцию":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        paid_features = get_paid_features()
        for i in range(0, len(paid_features), 2):
            if i + 1 < len(paid_features):
                markup.add(paid_features[i], paid_features[i + 1])
            else:
                markup.add(paid_features[i])
        markup.add(telebot.types.KeyboardButton("Вернуться в баллы"))
        markup.add(telebot.types.KeyboardButton("Вернуться в подписку"))
        markup.add(telebot.types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, (
            f"*Обмен баллов на функции:*\n\n"
            f"🎁 *Текущие баллы:* {format_number(points)}\n"
            f"🔓 *Обмен на доступ к функциям:* _2 балла = 15 минут_\n\n"  
            "Выберите функцию:"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_feature_selection, points)
    else:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton("Обмен на время"), telebot.types.KeyboardButton("Обмен на скидку"), telebot.types.KeyboardButton("Обмен на функцию"))
        markup.add(telebot.types.KeyboardButton("Вернуться в баллы"))
        markup.add(telebot.types.KeyboardButton("Вернуться в подписку"))
        markup.add(telebot.types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, "Выберите одну из предложенных опций!", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_exchange_option, points, exchange_rate, has_subscription)

@text_only_handler
def process_feature_selection(message, points):
    if message.text == "Вернуться в баллы":
        return_to_scores_menu(message)
        return
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    user_id = str(message.from_user.id)
    data = load_payment_data()
    feature = message.text
    paid_features = get_paid_features()
    if feature not in paid_features:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        for i in range(0, len(paid_features), 2):
            if i + 1 < len(paid_features):
                markup.add(paid_features[i], paid_features[i + 1])
            else:
                markup.add(paid_features[i])
        markup.add(telebot.types.KeyboardButton("Вернуться в баллы"))
        markup.add(telebot.types.KeyboardButton("Вернуться в подписку"))
        markup.add(telebot.types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, "Выберите функцию из списка!", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_feature_selection, points)
        return
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("Вернуться в баллы"))
    markup.add(telebot.types.KeyboardButton("Вернуться в подписку"))
    markup.add(telebot.types.KeyboardButton("В главное меню"))
    bot.send_message(message.chat.id, (
        f"*Обмен баллов на функцию: {feature.lower()}*\n\n"
        f"🎁 *Текущие баллы:* {format_number(points)}\n"
        f"🔓 *Обмен на доступ к функции:* _2 балла = 15 минут_\n\n"  
        "Введите количество баллов для обмена:"
    ), reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_feature_exchange, feature, points)

@text_only_handler
def process_feature_exchange(message, feature, points):
    if message.text == "Вернуться в баллы":
        return_to_scores_menu(message)
        return
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    user_id = str(message.from_user.id)
    data = load_payment_data()
    
    try:
        exchange_points = float(message.text.replace(',', '.'))
        if exchange_points < 2:
            raise ValueError("Минимальное количество баллов — 2!")
        if exchange_points > points:
            raise ValueError("Недостаточно баллов!")
        if exchange_points % 2 != 0:
            raise ValueError("Баллы должны быть кратны 2!")
        
        total_minutes = exchange_points * (15.0 / 2.0) 
        days = int(total_minutes // (24 * 60))
        remaining_minutes = total_minutes % (24 * 60)
        remaining_hours = remaining_minutes // 60
        remaining_minutes = remaining_minutes % 60
        
        duration_str = ""
        if days > 0:
            duration_str = f"{days} дн. {format_number(remaining_hours)} ч. {format_number(remaining_minutes)} мин."
        elif remaining_hours > 0:
            duration_str = f"{format_number(remaining_hours)} ч. {format_number(remaining_minutes)} мин."
        else:
            duration_str = f"{format_number(remaining_minutes)} мин."
        
        feature_access = data['subscriptions']['users'].get(user_id, {}).get('feature_access', {})
        current_end = datetime.strptime(feature_access.get(feature, "01.01.2025 в 00:00"), "%d.%m.%Y в %H:%M")
        latest_end = max(current_end, datetime.now())
        new_end = latest_end + timedelta(days=days, hours=remaining_hours, minutes=remaining_minutes)
        
        start_date = latest_end.strftime("%d.%m.%Y в %H:%M")
        end_date_str = new_end.strftime("%d.%m.%Y в %H:%M")
        
        data['subscriptions']['users'][user_id]['referral_points'] -= exchange_points
        data['subscriptions']['users'][user_id].setdefault('points_history', []).append({
            "action": "spent",
            "points": exchange_points,
            "exchange_type": "feature",
            "reason": f"Обмен на функцию '{feature}' ({duration_str})",
            "feature_name": feature,
            "date": datetime.now().strftime("%d.%m.%Y в %H:%M")
        })
        
        data['subscriptions']['users'].setdefault(user_id, {}).setdefault('feature_access', {})
        data['subscriptions']['users'][user_id]['feature_access'][feature] = end_date_str
        
        save_payments_data(data)
        
        result_msg = (
            f"✅ *Обмен выполнен!*\n\n"
            f"💰 *Потрачено:* {format_number(exchange_points)} {pluralize_points(exchange_points)}\n"
            f"🔄 *Тип обмена:* доступ к функции *{feature.lower()}*\n"
            f"🔄 *Количество обмена:* {duration_str}\n\n"
            f"🕒 *Начало:* {start_date}\n"
            f"⌛ *Конец:* {end_date_str}"
        )
        
        bot.send_message(message.chat.id, result_msg, parse_mode="Markdown")
        points_menu(message)
    
    except ValueError as e:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton("Вернуться в баллы"))
        markup.add(telebot.types.KeyboardButton("Вернуться в подписку"))
        markup.add(telebot.types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, f"{str(e)}", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_feature_exchange, feature, points)

@text_only_handler
def process_points_exchange(message, exchange_rate):
    if message.text == "Вернуться в баллы":
        return_to_scores_menu(message)
        return
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    user_id = str(message.from_user.id)
    data = load_payment_data()
    points = data['subscriptions']['users'].get(user_id, {}).get('referral_points', 0)
    
    try:
        exchange_points = float(message.text.replace(',', '.'))
        if exchange_points < 5:
            raise ValueError("Минимальное количество баллов — 5!")
        if exchange_points > points:
            raise ValueError("Недостаточно баллов!")
        if exchange_points % 5 != 0:
            raise ValueError("Баллы должны быть кратны 5!")
        if exchange_points > 6000:  
            raise ValueError("Максимальный обмен — 6000 баллов (50 дней)!")
        
        total_hours = exchange_points * exchange_rate  
        days = int(total_hours // 24)
        remaining_hours = total_hours % 24
        
        duration_str = ""
        if days > 0 and remaining_hours > 0:
            duration_str = f"{days} дн. {format_number(remaining_hours)} ч."
        elif days > 0:
            duration_str = f"{days} дн."
        else:
            duration_str = f"{format_number(remaining_hours)} ч."
        
        latest_end = max([datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") 
                         for p in data['subscriptions']['users'].get(user_id, {}).get('plans', [])] 
                         or [datetime.now()])
        new_end = latest_end + timedelta(days=days, hours=remaining_hours)
        
        start_date = latest_end.strftime("%d.%m.%Y в %H:%M")
        end_date_str = new_end.strftime("%d.%m.%Y в %H:%M")
        
        data['subscriptions']['users'][user_id]['referral_points'] -= exchange_points
        data['subscriptions']['users'][user_id].setdefault('points_history', []).append({
            "action": "spent",
            "points": exchange_points,
            "exchange_type": "subscription",
            "reason": f"Обмен на {duration_str}",
            "date": datetime.now().strftime("%d.%m.%Y в %H:%M")
        })
        
        data['subscriptions']['users'].setdefault(user_id, {})
        data['subscriptions']['users'][user_id].setdefault('plans', []).append({
            "plan_name": "points_bonus",
            "start_date": start_date,
            "end_date": end_date_str,
            "price": 0
        })
        
        save_payments_data(data)
        
        result_msg = (
            f"✅ *Обмен выполнен!*\n\n"
            f"💰 *Потрачено:* {format_number(exchange_points)} {pluralize_points(exchange_points)}\n"
            f"🔄 *Тип обмена:* время пользования\n"
            f"🔄 *Количество обмена:* {duration_str}\n\n"
            f"🕒 *Начало:* {start_date}\n"
            f"⌛ *Конец:* {end_date_str}"
        )
        
        bot.send_message(message.chat.id, result_msg, parse_mode="Markdown")
        points_menu(message)
    
    except ValueError as e:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton("Вернуться в баллы"))
        markup.add(telebot.types.KeyboardButton("Вернуться в подписку"))
        markup.add(telebot.types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, f"{str(e)}", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_points_exchange, exchange_rate)

@text_only_handler
def process_discount_exchange(message):
    if message.text == "Вернуться в баллы":
        return_to_scores_menu(message)
        return
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    user_id = str(message.from_user.id)
    data = load_payment_data()
    users_data = load_users_data()
    points = data['subscriptions']['users'].get(user_id, {}).get('referral_points', 0)
    
    try:
        exchange_points = float(message.text.replace(',', '.'))
        if exchange_points < 10:
            raise ValueError("Минимальное количество баллов — 10!")
        if exchange_points > points:
            raise ValueError("Недостаточно баллов!")
        if exchange_points % 10 != 0:
            raise ValueError("Баллы должны быть кратны 10!")
        
        discount = (exchange_points // 10) * 5
        current_discount = users_data.get(user_id, {}).get('discount', 0)
        if current_discount + discount > 35:
            raise ValueError("Максимальная скидка — 35%!")
        
        data['subscriptions']['users'][user_id]['referral_points'] -= exchange_points
        data['subscriptions']['users'][user_id].setdefault('points_history', []).append({
            "action": "spent",
            "points": exchange_points,
            "exchange_type": "discount",
            "reason": f"Обмен на {discount}% скидки",
            "date": datetime.now().strftime("%d.%m.%Y в %H:%M")
        })
        
        users_data.setdefault(user_id, {})
        users_data[user_id]['discount'] = current_discount + discount
        users_data[user_id]['discount_type'] = "points"
        
        save_payments_data(data)
        
        bot.send_message(message.chat.id, (
            f"✅ *Обмен выполнен!*\n\n"
            f"💰 *Потрачено:* {format_number(exchange_points)} {pluralize_points(exchange_points)}\n"
            f"🔄 *Тип обмена:* скидка\n"
            f"🔄 *Количество обмена:* {format_number(discount)}%\n\n"
            f"📉 *Текущая скидка:* {format_number(users_data[user_id]['discount'])}%"
        ), parse_mode="Markdown")
        points_menu(message)
    
    except ValueError as e:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton("Вернуться в баллы"))
        markup.add(telebot.types.KeyboardButton("Вернуться в подписку"))
        markup.add(telebot.types.KeyboardButton("В главное меню"))
        bot.send_message(message.chat.id, f"{str(e)}", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_discount_exchange)