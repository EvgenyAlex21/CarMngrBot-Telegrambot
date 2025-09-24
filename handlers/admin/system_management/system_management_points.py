from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, timedelta
from core.bot_instance import bot
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from handlers.admin.system_management.system_management_main import manage_system
from handlers.admin.statistics.statistics import check_admin_access, escape_markdown
from handlers.user.subscription.gifts import split_message, format_time, format_number
from handlers.user.user_main_menu import PAID_FEATURES
from handlers.admin.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

def load_users():
    from handlers.user.user_main_menu import load_users_data as _load
    return _load()

def load_payment_data():
    from handlers.user.user_main_menu import load_payment_data as _load
    return _load()

def save_payments_data(data):
    from handlers.user.user_main_menu import save_payments_data as _save
    return _save(data)

# --------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ (упраление баллами) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Управление баллами' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def manage_points(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Управление баллами'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Начисление баллов', 'Списание баллов')
    markup.add('Просмотр баллов', 'Просмотр истории баллов')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите действие для управления баллами:", reply_markup=markup)

# --------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ БАЛЛАМИ (начисление баллов) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Начисление баллов' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def add_points(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Начисление баллов'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    users_data = load_users()
    user_list = []
    for user_id, data in users_data.items():
        username = escape_markdown(data['username'])
        status = " - *заблокирован* 🚫" if data.get('blocked', False) else " - *разблокирован* ✅"
        user_list.append(f"№{len(user_list) + 1}. {username} - `{user_id}`{status}")

    response_message = "📋 Список *всех* пользователей:\n\n" + "\n\n".join(user_list)
    if len(response_message) > 4096:
        bot.send_message(message.chat.id, "📜 Список пользователей слишком большой для отправки в одном сообщении!")
    else:
        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Вернуться в управление баллами')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для начисления баллов:", reply_markup=markup)
    bot.register_next_step_handler(message, process_add_points)

@text_only_handler
def process_add_points(message):
    if message.text == "Вернуться в управление баллами":
        manage_points(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    user_input = message.text.strip()
    user_id = None

    users_data = load_users()
    if user_input.isdigit():
        if len(user_input) >= 5:
            user_id = user_input
        else:
            idx = int(user_input)
            if 1 <= idx <= len(users_data):
                user_id = list(users_data.keys())[idx - 1]
    elif user_input.startswith('@'):
        username = user_input[1:]  
        for uid, data in users_data.items():
            db_username = data['username'].lstrip('@')  
            if db_username.lower() == username.lower(): 
                user_id = uid
                break

    if not user_id:
        bot.send_message(message.chat.id, "Пользователь не найден! Пожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_add_points)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в управление баллами')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите количество баллов для начисления:", reply_markup=markup)
    bot.register_next_step_handler(message, process_add_points_amount, user_id)

@text_only_handler
def process_add_points_amount(message, user_id):
    if message.text == "Вернуться в управление баллами":
        manage_points(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        input_text = message.text.strip().replace(',', '.')
        points = float(input_text)
        if points <= 0:
            raise ValueError("Количество баллов должно быть положительным!")

        points_display = f"{int(float(points))}" if float(points).is_integer() else f"{float(points):.2f}"

        data = load_payment_data()
        user_data = data['subscriptions']['users'].setdefault(str(user_id), {
            'plans': [], 'total_amount': 0, 'referral_points': 0
        })

        users_data = load_users()
        username = escape_markdown(users_data.get(str(user_id), {}).get('username', f"@{user_id}"))

        user_data['referral_points'] = user_data.get('referral_points', 0) + points
        user_data.setdefault('points_history', []).append({
            'action': 'earned',
            'points': points,
            'reason': 'Начисление от администратора',
            'date': datetime.now().strftime("%d.%m.%Y в %H:%M")
        })

        save_payments_data(data)
        admin_message = f"✅ Пользователю {username} - `{user_id}` начислено *{points_display} баллов*!"
        user_message = f"✅ Администратор начислил вам *{points_display} баллов*!"
        bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
        bot.send_message(user_id, user_message, parse_mode="Markdown")
        manage_points(message)
    except ValueError as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_add_points_amount, user_id)

# --------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ БАЛЛАМИ (просмотр баллов) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Просмотр баллов' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_points(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Просмотр баллов'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    users_data = load_users()
    user_list = []
    for user_id, data in users_data.items():
        username = escape_markdown(data['username'])
        status = " - *заблокирован* 🚫" if data.get('blocked', False) else " - *разблокирован* ✅"
        user_list.append(f"№{len(user_list) + 1}. {username} - `{user_id}`{status}")

    response_message = "📋 Список *всех* пользователей:\n\n" + "\n\n".join(user_list)
    if len(response_message) > 4096:
        bot.send_message(message.chat.id, "📜 Список пользователей слишком большой для отправки в одном сообщении!")
    else:
        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Вернуться в управление баллами')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для просмотра баллов:", reply_markup=markup)
    bot.register_next_step_handler(message, process_view_points)

@text_only_handler
def process_view_points(message):
    if message.text == "Вернуться в управление баллами":
        manage_points(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    user_input = message.text.strip()
    user_id = None

    users_data = load_users()
    if user_input.isdigit():
        if len(user_input) >= 5:
            user_id = user_input
        else:
            idx = int(user_input)
            if 1 <= idx <= len(users_data):
                user_id = list(users_data.keys())[idx - 1]
    elif user_input.startswith('@'):
        username = user_input[1:]  
        for uid, data in users_data.items():
            db_username = data['username'].lstrip('@') 
            if db_username.lower() == username.lower():  
                user_id = uid
                break

    if not user_id:
        bot.send_message(message.chat.id, "Пользователь не найден! Пожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_view_points)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})
    points = user_data.get('referral_points', 0)
    username = users_data.get(str(user_id), {}).get('username', f"@{user_id}")

    history = user_data.get('points_history', [])
    total_earned = sum(entry['points'] for entry in history if entry['action'] == 'earned')
    total_spent = sum(entry['points'] for entry in history if entry['action'] == 'spent')

    earned_daily = sum(entry['points'] for entry in history if entry['action'] == 'earned' and entry['reason'] == 'Ежедневный вход')
    earned_admin = sum(entry['points'] for entry in history if entry['action'] == 'earned' and entry['reason'].startswith('Начисление от администратора'))
    earned_gifts = sum(entry['points'] for entry in history if entry['action'] == 'earned' and entry['reason'].startswith('Подарок от'))
    earned_first_purchase = sum(entry['points'] for entry in history if entry['action'] == 'earned' and entry['reason'].startswith('Первая покупка подписки'))
    earned_points_purchase = sum(entry['points'] for entry in history if entry['action'] == 'earned' and entry['reason'].startswith('Покупка') and 'баллов' in entry['reason'])
    earned_referrals = sum(entry['points'] for entry in history if entry['action'] == 'earned' and 'Реферал' in entry['reason'])
    earned_top_referrals = sum(entry['points'] for entry in history if entry['action'] == 'earned' and 'Топ-10 рефералов' in entry['reason'])
    earned_purchases = sum(entry['points'] for entry in history if entry['action'] == 'earned' and entry['reason'].startswith('Покупка подписки'))

    spent_gifts = sum(entry['points'] for entry in history if entry['action'] == 'spent' and entry['reason'].lower().startswith('подарок'))
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
        elif entry['reason'].lower().startswith('подарок времени') and any(unit in entry['reason'] for unit in ['дн.', 'ч.', 'мин.', 'минут']):
            time_str = entry['reason'].split(': ')[1]
        
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
        f"💰 *Баллы пользователя* {username} - `{str(user_id)}`:\n\n"
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

    manage_points(message)

# --------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ БАЛЛАМИ (списание баллов) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Списание баллов' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def remove_points(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Списание баллов'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    users_data = load_users()
    user_list = []
    for user_id, data in users_data.items():
        username = escape_markdown(data['username'])
        status = " - *заблокирован* 🚫" if data.get('blocked', False) else " - *разблокирован* ✅"
        user_list.append(f"№{len(user_list) + 1}. {username} - `{user_id}`{status}")

    response_message = "📋 Список *всех* пользователей:\n\n" + "\n\n".join(user_list)
    if len(response_message) > 4096:
        bot.send_message(message.chat.id, "📜 Список пользователей слишком большой для отправки в одном сообщении!")
    else:
        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Вернуться в управление баллами')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для списания баллов:", reply_markup=markup)
    bot.register_next_step_handler(message, process_remove_points)

@text_only_handler
def process_remove_points(message):
    if message.text == "Вернуться в управление баллами":
        manage_points(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    user_input = message.text.strip()
    user_id = None

    users_data = load_users()
    if user_input.isdigit():
        if len(user_input) >= 5:
            user_id = user_input
        else:
            idx = int(user_input)
            if 1 <= idx <= len(users_data):
                user_id = list(users_data.keys())[idx - 1]
    elif user_input.startswith('@'):
        username = user_input[1:]  
        for uid, data in users_data.items():
            db_username = data['username'].lstrip('@')  
            if db_username.lower() == username.lower():  
                user_id = uid
                break

    if not user_id:
        bot.send_message(message.chat.id, "Пользователь не найден!\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_remove_points)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})
    points = user_data.get('referral_points', 0)
    if points == 0:
        bot.send_message(message.chat.id, "❌ У пользователя нет баллов для списания!", parse_mode="Markdown")
        manage_points(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в управление баллами')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, f"Введите количество баллов для списания:", reply_markup=markup)
    bot.register_next_step_handler(message, process_remove_points_amount, user_id)

@text_only_handler
def process_remove_points_amount(message, user_id):
    if message.text == "Вернуться в управление баллами":
        manage_points(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        input_text = message.text.strip().replace(',', '.')
        points = float(input_text)
        if points <= 0:
            raise ValueError("Количество баллов должно быть положительным!")

        points_display = f"{int(float(points))}" if float(points).is_integer() else f"{float(points):.2f}"

        data = load_payment_data()
        user_data = data['subscriptions']['users'].get(str(user_id), {})
        current_points = user_data.get('referral_points', 0)
        if points > current_points:
            raise ValueError("❌ Недостаточно баллов для списания!")

        users_data = load_users()
        username = users_data.get(str(user_id), {}).get('username', f"@{user_id}")
        if not username.startswith('@'):
            username = f"@{username}"

        user_data['referral_points'] = max(0, current_points - points)
        user_data.setdefault('points_history', []).append({
            'action': 'spent',
            'points': points,
            'reason': 'списание администратором',
            'date': datetime.now().strftime("%d.%m.%Y в %H:%M")
        })

        save_payments_data(data)
        admin_message = f"🚫 С пользователя {username} - `{user_id}` списано *{points_display} баллов*!"
        user_message = f"🚫 Администратор списал *{points_display} баллов*!"
        bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
        bot.send_message(user_id, user_message, parse_mode="Markdown")
        manage_points(message)
    except ValueError as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_remove_points_amount, user_id)

# ------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ БАЛЛАМИ (просмотр истории баллов) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Просмотр истории баллов' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_points_history(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Просмотр истории баллов'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    users_data = load_users()
    user_list = []
    for user_id, data in users_data.items():
        username = escape_markdown(data['username'])
        status = " - *заблокирован* 🚫" if data.get('blocked', False) else " - *разблокирован* ✅"
        user_list.append(f"№{len(user_list) + 1}. {username} - `{user_id}`{status}")

    response_message = "📋 Список *всех* пользователей:\n\n" + "\n\n".join(user_list)
    if len(response_message) > 4096:
        bot.send_message(message.chat.id, "📜 Список пользователей слишком большой для отправки в одном сообщении!")
    else:
        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Вернуться в управление баллами')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для просмотра истории баллов:", reply_markup=markup)
    bot.register_next_step_handler(message, process_view_points_history)

@text_only_handler
def process_view_points_history(message):
    if message.text == "Вернуться в управление баллами":
        manage_points(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    user_input = message.text.strip()
    user_id = None

    users_data = load_users()
    if user_input.isdigit():
        if len(user_input) >= 5:
            user_id = user_input
        else:
            idx = int(user_input)
            if 1 <= idx <= len(users_data):
                user_id = list(users_data.keys())[idx - 1]
    elif user_input.startswith('@'):
        username = user_input[1:] 
        for uid, data in users_data.items():
            db_username = data['username'].lstrip('@')  
            if db_username.lower() == username.lower():  
                user_id = uid
                break

    if not user_id:
        bot.send_message(message.chat.id, "Пользователь не найден!\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_view_points_history)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})
    history = user_data.get('points_history', [])
    if not history:
        bot.send_message(message.chat.id, "❌ История операций с баллами пуста!", parse_mode="Markdown")
        manage_points(message)
        return

    username = users_data.get(str(user_id), {}).get('username', f"@{user_id}")
    if not username.startswith('@'):
        username = f"@{username}"

    def format_date(date_str):
        return re.sub(r'(\d{2}\.\d{2}\.\d{4} в \d{2}:\d{2}):\d{2}', r'\1', date_str)

    history_summary = f"*История баллов пользователя* {escape_markdown(username)} - `{user_id}`:\n\n"
    for idx, entry in enumerate(history, 1):
        action = "Заработано" if entry['action'] == 'earned' else "Потрачено"
        points = format_number(entry['points'])
        date = format_date(entry['date'])
        reason = escape_markdown(entry['reason'].lower())
        history_summary += (
            f"📝 *№{idx}. {action}:*\n\n"
            f"💰 *Количество:* {points} баллов\n"
            f"📅 *Дата:* {date}\n"
            f"📋 *Причина:* {reason}\n\n"
        )

    message_parts = split_message(history_summary)
    for part in message_parts:
        bot.send_message(message.chat.id, part, parse_mode="Markdown")

    manage_points(message)