from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, timedelta, uuid
from core.bot_instance import bot
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from handlers.admin.system_management.system_management import manage_system
from handlers.admin.statistics.statistics import check_admin_access, escape_markdown
from handlers.user.user_main_menu import load_payment_data, save_payments_data, load_users_data as load_users, save_users_data
from handlers.user.subscription.gifts import split_message, format_number
from handlers.user.user_main_menu import PAID_FEATURES
from handlers.admin.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

# ------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ (управление обменами) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Управление обменами' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def manage_exchanges(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Управление обменами'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Выполнить обмен', 'Просмотр обменов')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите действие для управления обменами:", reply_markup=markup)

# ------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ ОБМЕНАМИ (выполнить обмен) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Выполнить обмен' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def perform_exchange(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Выполнить обмен'):
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
    markup.add('Вернуться в управление обменами')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для выполнения обмена:", reply_markup=markup)
    bot.register_next_step_handler(message, process_perform_exchange)

@text_only_handler
def process_perform_exchange(message):
    if message.text == "Вернуться в управление обменами":
        manage_exchanges(message)
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
        bot.register_next_step_handler(message, process_perform_exchange)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})
    points = user_data.get('referral_points', 0)
    if points < 2:
        bot.send_message(message.chat.id, "❌ У пользователя недостаточно баллов для обмена!", parse_mode="Markdown")
        manage_exchanges(message)
        return

    exchange_rate = 1.0 / 5.0

    username = users_data.get(str(user_id), {}).get('username', f"@{user_id}")
    if not username.startswith('@'):
        username = f"@{username}"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Обмен на время', 'Обмен на скидку', 'Обмен на функцию')
    markup.add('Вернуться в управление обменами')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, (
        f"Выберите тип обмена для пользователя {escape_markdown(username)} - `{user_id}`:\n\n"
        f"🎁 *Текущие баллы:* {format_number(points)}\n\n"
        f"🔄 *Возможные обмены:*\n"
        f"⏳ - *Время подписки:* _5 баллов = 1 час_\n"
        f"🔓 - *Доступ к функциям:* _2 балла = 15 минут_\n"
        f"🏷️ - *Скидка:* _10 баллов = 5% (макс. 35%)_\n"
    ), reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_perform_exchange_type, user_id, exchange_rate)

@text_only_handler
def process_perform_exchange_type(message, user_id, exchange_rate):
    if message.text == "Вернуться в управление обменами":
        manage_exchanges(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    exchange_type = message.text.strip()
    if exchange_type not in ['Обмен на время', 'Обмен на скидку', 'Обмен на функцию']:
        bot.send_message(message.chat.id, "Неверный тип обмена!\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_perform_exchange_type, user_id, exchange_rate)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})
    points = user_data.get('referral_points', 0)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в управление обменами')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    if exchange_type == 'Обмен на время':
        bot.send_message(message.chat.id, (
            f"Введите количество баллов для обмена на время:\n_P.S. 5 баллов = 1 час_"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_perform_exchange_time, user_id, exchange_rate)
    elif exchange_type == 'Обмен на скидку':
        bot.send_message(message.chat.id, (
            f"Введите количество баллов для обмена на скидку:\n_P.S. 10 баллов = 5%, макс. 35%_"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_perform_exchange_discount, user_id)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for i in range(0, len(PAID_FEATURES), 2):
            if i + 1 < len(PAID_FEATURES):
                markup.add(PAID_FEATURES[i], PAID_FEATURES[i + 1])
            else:
                markup.add(PAID_FEATURES[i])
        markup.add('Вернуться в управление обменами')
        markup.add('Вернуться в управление системой')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, (
            f"Выберите функцию для обмена:\n_P.S. 2 балла = 15 минут_"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_perform_exchange_feature, user_id)

@text_only_handler
def process_perform_exchange_time(message, user_id, exchange_rate):
    if message.text == "Вернуться в управление обменами":
        manage_exchanges(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        points_needed = float(message.text.replace(',', '.'))
        if points_needed < 5:
            raise ValueError("Минимальное количество баллов — 5!")
        if points_needed % 5 != 0:
            raise ValueError("Баллы должны быть кратны 5!")
        if points_needed > 6000:
            raise ValueError("Максимальный обмен — 6000 баллов (50 дней)!")

        data = load_payment_data()
        user_data = data['subscriptions']['users'].get(str(user_id), {})
        points = user_data.get('referral_points', 0)
        if points < points_needed:
            raise ValueError("Недостаточно баллов для обмена!")

        users_data = load_users()
        username = users_data.get(str(user_id), {}).get('username', f"@{user_id}")
        if not username.startswith('@'):
            username = f"@{username}"

        total_hours = points_needed * exchange_rate
        days = int(total_hours // 24)
        remaining_hours = total_hours % 24

        latest_end = max([datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M")
                         for p in user_data.get('plans', [])] or [datetime.now()])
        new_end = latest_end + timedelta(days=days, hours=remaining_hours)

        start_date = latest_end.strftime("%d.%m.%Y в %H:%M")
        end_date_str = new_end.strftime("%d.%m.%Y в %H:%M")

        duration_str = ""
        if days > 0 and remaining_hours > 0:
            duration_str = f"{days} дн. {format_number(remaining_hours)} ч."
        elif days > 0:
            duration_str = f"{days} дн."
        else:
            duration_str = f"{format_number(remaining_hours)} ч."

        user_data['referral_points'] -= points_needed
        user_data.setdefault('points_history', []).append({
            'action': 'spent',
            'points': points_needed,
            'exchange_type': 'subscription',
            'reason': f"обмен на {duration_str}",
            'date': datetime.now().strftime("%d.%m.%Y в %H:%M")
        })

        user_data.setdefault('plans', []).append({
            'plan_name': 'exchange_time',
            'start_date': start_date,
            'end_date': end_date_str,
            'price': 0,
            'source': 'admin_exchange'
        })

        save_payments_data(data)

        admin_message = (
            f"✅ Для пользователя {username} - `{user_id}` выполнен обмен:\n\n"
            f"💰 *Баллы:* {format_number(points_needed)} баллов\n"
            f"🔄 *Тип обмена:* время пользования\n"
            f"🔄 *Количество обмена:* {duration_str}\n"
            f"🕒 *Начало:* {start_date}\n"
            f"⌛ *Конец:* {end_date_str}"
        )
        user_message = (
            f"✅ Администратор обменял *{format_number(points_needed)} ваших баллов*:\n\n"
            f"💰 *Баллы:* {format_number(points_needed)} баллов\n"
            f"🔄 *Тип обмена:* время пользования\n"
            f"🔄 *Количество обмена:* {duration_str}\n"
            f"🕒 *Начало:* {start_date}\n"
            f"⌛ *Конец:* {end_date_str}"
        )

        bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
        bot.send_message(user_id, user_message, parse_mode="Markdown")

        manage_exchanges(message)
    except ValueError as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_perform_exchange_time, user_id, exchange_rate)

@text_only_handler
def process_perform_exchange_discount(message, user_id):
    if message.text == "Вернуться в управление обменами":
        manage_exchanges(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        points_needed = float(message.text.replace(',', '.'))
        if points_needed < 10:
            raise ValueError("Минимальное количество баллов — 10!")
        if points_needed % 10 != 0:
            raise ValueError("Баллы должны быть кратны 10!")

        data = load_payment_data()
        user_data = data['subscriptions']['users'].get(str(user_id), {})
        points = user_data.get('referral_points', 0)
        if points < points_needed:
            raise ValueError("Недостаточно баллов для обмена!")

        users_data = load_users()
        username = users_data.get(str(user_id), {}).get('username', f"@{user_id}")
        if not username.startswith('@'):
            username = f"@{username}"

        discount = (points_needed // 10) * 5
        current_discount = users_data.get(str(user_id), {}).get('discount', 0)
        if current_discount + discount > 35:
            raise ValueError("Максимальная скидка — 35%!")

        user_data['referral_points'] -= points_needed
        user_data.setdefault('points_history', []).append({
            'action': 'spent',
            'points': points_needed,
            'exchange_type': 'discount',
            'reason': f"Обмен на {discount}% скидки",
            'date': datetime.now().strftime("%d.%m.%Y в %H:%M")
        })

        users_data.setdefault(str(user_id), {})
        users_data[str(user_id)]['discount'] = current_discount + discount
        users_data[str(user_id)]['discount_type'] = "points"

        promo_code = f"DISC{uuid.uuid4().hex[:8].upper()}"
        data.setdefault('promo_codes', {})[promo_code] = {
            'discount': discount,
            'used': False,
            'user_id': str(user_id),
            'created_at': datetime.now().strftime("%d.%m.%Y в %H:%M"),
            'source': 'admin_exchange'
        }

        save_payments_data(data)
        save_users_data(users_data)

        admin_message = (
            f"✅ Для пользователя {username} - `{user_id}` выполнен обмен:\n\n"
            f"💰 *Баллы:* {format_number(points_needed)} баллов\n"
            f"🔄 *Тип обмена:* скидка\n"
            f"🔄 *Количество обмена:* {format_number(discount)}%\n"
            f"📌 *Промокод:* `{promo_code}`"
        )
        user_message = (
            f"✅ Администратор обменял *{format_number(points_needed)} ваших баллов*:\n\n"
            f"💰 *Баллы:* {format_number(points_needed)} баллов\n"
            f"🔄 *Тип обмена:* скидка\n"
            f"🔄 *Количество обмена:* {format_number(discount)}%\n"
            f"📌 *Промокод:* `{promo_code}`"
        )

        bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
        bot.send_message(user_id, user_message, parse_mode="Markdown")

        manage_exchanges(message)
    except ValueError as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_perform_exchange_discount, user_id)

@text_only_handler
def process_perform_exchange_feature(message, user_id):
    if message.text == "Вернуться в управление обменами":
        manage_exchanges(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    feature = message.text.strip()
    if feature not in PAID_FEATURES:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for i in range(0, len(PAID_FEATURES), 2):
            if i + 1 < len(PAID_FEATURES):
                markup.add(PAID_FEATURES[i], PAID_FEATURES[i + 1])
            else:
                markup.add(PAID_FEATURES[i])
        markup.add('Вернуться в управление обменами')
        markup.add('Вернуться в управление системой')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Выберите функцию из списка:", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_perform_exchange_feature, user_id)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})
    points = user_data.get('referral_points', 0)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в управление обменами')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, (
        f"Введите количество баллов для обмена на функцию *{feature.lower()}:*\n"
        f"_P.S. 2 балла = 15 минут_"
    ), reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_perform_exchange_feature_amount, user_id, feature)

@text_only_handler
def process_perform_exchange_feature_amount(message, user_id, feature):
    if message.text == "Вернуться в управление обменами":
        manage_exchanges(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        points_needed = float(message.text.replace(',', '.'))
        if points_needed < 2:
            raise ValueError("Минимальное количество баллов — 2!")
        if points_needed % 2 != 0:
            raise ValueError("Баллы должны быть кратны 2!")

        data = load_payment_data()
        user_data = data['subscriptions']['users'].get(str(user_id), {})
        points = user_data.get('referral_points', 0)
        if points < points_needed:
            raise ValueError("Недостаточно баллов для обмена!")

        users_data = load_users()
        username = users_data.get(str(user_id), {}).get('username', f"@{user_id}")
        if not username.startswith('@'):
            username = f"@{username}"

        total_minutes = points_needed * (15.0 / 2.0)
        days = int(total_minutes // (24 * 60))
        remaining_minutes = total_minutes % (24 * 60)
        remaining_hours = remaining_minutes // 60
        remaining_minutes = remaining_minutes % 60

        feature_access = user_data.get('feature_access', {})
        current_end = datetime.strptime(feature_access.get(feature, "01.01.2025 в 00:00"), "%d.%m.%Y в %H:%M")
        latest_end = max(current_end, datetime.now())
        new_end = latest_end + timedelta(days=days, hours=remaining_hours, minutes=remaining_minutes)

        start_date = latest_end.strftime("%d.%m.%Y в %H:%M")
        end_date_str = new_end.strftime("%d.%m.%Y в %H:%M")

        duration_str = ""
        if days > 0:
            duration_str = f"{days} дн. {remaining_hours} ч. {format_number(remaining_minutes)} мин."
        elif remaining_hours > 0:
            duration_str = f"{remaining_hours} ч. {format_number(remaining_minutes)} мин."
        else:
            duration_str = f"{format_number(remaining_minutes)} мин."

        user_data['referral_points'] -= points_needed
        user_data.setdefault('points_history', []).append({
            'action': 'spent',
            'points': points_needed,
            'exchange_type': 'feature',
            'reason': f"обмен на функцию '{feature}' ({duration_str})",
            'feature_name': feature,
            'date': datetime.now().strftime("%d.%m.%Y в %H:%M")
        })

        user_data.setdefault('feature_access', {})
        user_data['feature_access'][feature] = end_date_str

        save_payments_data(data)

        admin_message = (
            f"✅ Для пользователя {username} - `{user_id}` выполнен обмен:\n\n"
            f"💰 *Баллы:* {format_number(points_needed)} баллов\n"
            f"🔄 *Тип обмена:* доступ к функции *{feature.lower()}*\n"
            f"🔄 *Количество обмена:* {duration_str}\n"
            f"🕒 *Начало:* {start_date}\n"
            f"⌛ *Конец:* {end_date_str}"
        )
        user_message = (
            f"✅ Администратор обменял *{format_number(points_needed)} ваших баллов*:\n\n"
            f"💰 *Баллы:* {format_number(points_needed)} баллов\n"
            f"🔄 *Тип обмена:* доступ к функции *{feature.lower()}*\n"
            f"🔄 *Количество обмена:* {duration_str}\n"
            f"🕒 *Начало:* {start_date}\n"
            f"⌛ *Конец:* {end_date_str}"
        )

        bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
        bot.send_message(user_id, user_message, parse_mode="Markdown")

        manage_exchanges(message)
    except ValueError as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_perform_exchange_feature_amount, user_id, feature)

# ------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ ОБМЕНАМИ (просмотр обменов) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Просмотр обменов' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_exchanges(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Просмотр обменов'):
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
    markup.add('Вернуться в управление обменами')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для просмотра обменов:", reply_markup=markup)
    bot.register_next_step_handler(message, process_view_exchanges)

@text_only_handler
def process_view_exchanges(message):
    if message.text == "Вернуться в управление обменами":
        manage_exchanges(message)
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
        bot.register_next_step_handler(message, process_view_exchanges)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})
    history = user_data.get('points_history', [])
    exchanges = [
        entry for entry in history
        if isinstance(entry, dict)
        and entry.get('action') == 'spent'
        and 'обмен' in str(entry.get('reason', '')).lower()
    ]
    if not exchanges:
        bot.send_message(message.chat.id, "❌ У пользователя нет обменов!", parse_mode="Markdown")
        manage_exchanges(message)
        return

    username = users_data.get(str(user_id), {}).get('username', f"@{user_id}")
    if not username.startswith('@'):
        username = f"@{username}"

    def format_reason(reason: str) -> str:
        reason_text = str(reason)
        m_func = re.search(r"обмен на функцию\s+'([^']+)'\s*\(([^)]+)\)", reason_text, flags=re.IGNORECASE)
        if m_func:
            func_name = escape_markdown(m_func.group(1).strip().lower())
            duration = escape_markdown(m_func.group(2).strip())
            return f"обмен на функцию *{func_name}* ({duration})"
        m_disc = re.search(r"обмен на\s+([\d.,]+)%\s*скидк", reason_text, flags=re.IGNORECASE)
        if m_disc:
            pct_raw = m_disc.group(1).replace(',', '.')
            try:
                pct = float(pct_raw)
            except ValueError:
                pct = pct_raw
            pct_str = format_number(pct) if isinstance(pct, (int, float)) else escape_markdown(str(pct))
            return f"обмен на {pct_str}% скидки"
        m_generic = re.search(r"обмен на\s+(.+)$", reason_text, flags=re.IGNORECASE)
        if m_generic:
            tail = escape_markdown(m_generic.group(1).strip())
            return f"обмен на {tail}"
        return escape_markdown(reason_text)

    exchanges_summary = f"*История обменов пользователя* {username} - `{user_id}`:\n\n"
    for idx, entry in enumerate(exchanges, 1):
        formatted_reason = format_reason(entry['reason'])
        exchanges_summary += (
            f"📝 *№{idx}. Потрачено:*\n\n"
            f"💰 *Количество:* {format_number(entry['points'])} баллов\n"
            f"📅 *Дата:* {entry['date']}\n"
            f"📋 *Причина:* {formatted_reason}\n\n"
        )

    message_parts = split_message(exchanges_summary)
    for part in message_parts:
        bot.send_message(message.chat.id, part, parse_mode="Markdown")

    manage_exchanges(message)