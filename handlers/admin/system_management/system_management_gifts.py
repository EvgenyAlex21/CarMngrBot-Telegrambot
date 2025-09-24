from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, timedelta
from core.bot_instance import bot
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from handlers.admin.system_management.system_management_main import manage_system
from handlers.admin.statistics.statistics import check_admin_access, escape_markdown
from handlers.user.user_main_menu import load_payment_data, save_payments_data, load_users_data as load_users
from handlers.user.subscription.gifts import split_message, format_time, format_number
from handlers.admin.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

# ------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ (управление подарками) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Управление подарками' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def manage_gifts(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Управление подарками'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Назначить подарок', 'Просмотр подарков')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите действие для управления подарками:", reply_markup=markup)

# ------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ ПОДАРКАМИ (назначить подарок) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Назначить подарок' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def assign_gift(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Назначить подарок'):
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
    markup.add('Вернуться в управление подарками')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя, который будет *отправителем* подарка:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_gift_sender)

@text_only_handler
def process_gift_sender(message):
    if message.text == "Вернуться в управление подарками":
        manage_gifts(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    user_input = message.text.strip()
    sender_id = None

    users_data = load_users()
    if user_input.isdigit():
        if len(user_input) >= 5:
            sender_id = user_input
        else:
            idx = int(user_input)
            if 1 <= idx <= len(users_data):
                sender_id = list(users_data.keys())[idx - 1]
    elif user_input.startswith('@'):
        username = user_input[1:]
        for uid, data in users_data.items():
            db_username = data['username'].lstrip('@')
            if db_username.lower() == username.lower():
                sender_id = uid
                break

    if not sender_id or sender_id not in users_data:
        bot.send_message(message.chat.id, "Пользователь не найден!\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_gift_sender)
        return

    user_list = []
    for user_id, data in users_data.items():
        if user_id == sender_id:
            continue
        username = escape_markdown(data['username'])
        status = " - *заблокирован* 🚫" if data.get('blocked', False) else " - *разблокирован* ✅"
        user_list.append(f"№{len(user_list) + 1}. {username} - `{user_id}`{status}")

    response_message = "📋 Список *всех* пользователей для получения подарка:\n\n" + "\n\n".join(user_list)
    if len(response_message) > 4096:
        bot.send_message(message.chat.id, "📜 Список пользователей слишком большой для отправки в одном сообщении!")
    else:
        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Вернуться в управление подарками')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя, который будет *получателем* подарка:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_gift_recipient, sender_id)

@text_only_handler
def process_gift_recipient(message, sender_id):
    if message.text == "Вернуться в управление подарками":
        manage_gifts(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    user_input = message.text.strip()
    recipient_id = None

    users_data = load_users()
    user_list = []
    filtered_users = []
    for user_id, data in users_data.items():
        if user_id == sender_id:
            continue
        filtered_users.append(user_id)
        username = escape_markdown(data['username'])
        status = " - *заблокирован* 🚫" if data.get('blocked', False) else " - *разблокирован* ✅"
        user_list.append(f"№{len(user_list) + 1}. {username} - `{user_id}`{status}")

    response_message = "📋 Список *всех* пользователей для получения подарка:\n\n" + "\n\n".join(user_list)
    if len(response_message) > 4096:
        bot.send_message(message.chat.id, "📜 Список пользователей слишком большой для отправки в одном сообщении!")
        return

    if user_input.isdigit():
        if len(user_input) >= 5:
            recipient_id = user_input
        else:
            idx = int(user_input)
            if 1 <= idx <= len(filtered_users):
                recipient_id = filtered_users[idx - 1]
    elif user_input.startswith('@'):
        username = user_input[1:]
        for uid, data in users_data.items():
            db_username = data['username'].lstrip('@')
            if db_username.lower() == username.lower():
                recipient_id = uid
                break

    if not recipient_id or recipient_id not in users_data:
        bot.send_message(message.chat.id, "Пользователь не найден!\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_gift_recipient, sender_id)
        return

    if recipient_id == sender_id:
        bot.send_message(message.chat.id, "❌ Нельзя подарить подарок самому себе!\nПожалуйста, выберите другого получателя", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_gift_recipient, sender_id)
        return

    sender_username = escape_markdown(users_data.get(sender_id, {}).get('username', f"@{sender_id}"))
    recipient_username = escape_markdown(users_data.get(recipient_id, {}).get('username', f"@{recipient_id}"))

    data = load_payment_data()
    sender_data = data['subscriptions']['users'].get(sender_id, {})
    sender_points = sender_data.get('referral_points', 0)

    paid_plans = [
        plan for plan in sender_data.get('plans', [])
        if plan['plan_name'] in ['trial', 'weekly', 'monthly', 'quarterly', 'semiannual', 'yearly']
        and plan['source'] == 'user'
        and datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M") > datetime.now()
    ]
    total_remaining_minutes = 0
    now = datetime.now()
    for plan in paid_plans:
        end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
        if end_date > now:
            total_remaining_minutes += int((end_date - now).total_seconds() // 60)

    days = total_remaining_minutes // 1440
    hours = (total_remaining_minutes % 1440) // 60
    minutes = total_remaining_minutes % 60
    time_description = f"{days} дн. {hours} ч. {minutes} мин."

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Подарок баллов', 'Подарок времени')
    markup.add('Вернуться в управление подарками')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, (
        f"🎁 *Назначение подарка*\n\n"
        f"📤 *Отправитель:* {sender_username} (`{sender_id}`)\n"
        f"📥 *Получатель:* {recipient_username} (`{recipient_id}`)\n\n"
        f"💰 *Доступно баллов у отправителя:* {format_number(sender_points)}\n"
        f"⏳ *Доступно времени у отправителя:* {time_description}\n\n"
        "Выберите тип подарка:"
    ), reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_gift_type, sender_id, recipient_id)

@text_only_handler
def process_gift_type(message, sender_id, recipient_id):
    if message.text == "Вернуться в управление подарками":
        manage_gifts(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    gift_type = message.text.strip()
    if gift_type not in ['Подарок баллов', 'Подарок времени']:
        bot.send_message(message.chat.id, "Неверный тип подарка!\nПожалуйста, выберите снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_gift_type, sender_id, recipient_id)
        return

    users_data = load_users()
    data = load_payment_data()
    sender_data = data['subscriptions']['users'].get(sender_id, {})
    sender_username = escape_markdown(users_data.get(sender_id, {}).get('username', f"@{sender_id}"))
    recipient_username = escape_markdown(users_data.get(recipient_id, {}).get('username', f"@{recipient_id}"))

    sender_points = sender_data.get('referral_points', 0)

    allowed_plan_names = ['trial', 'weekly', 'monthly', 'quarterly', 'semiannual', 'yearly', 'points_bonus', 'gift_time', 'store_time', 'custom']
    paid_plans = [
        plan for plan in sender_data.get('plans', [])
        if plan['plan_name'] in allowed_plan_names
        and datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M") > datetime.now()
    ]
    total_remaining_minutes = 0
    now = datetime.now()
    for plan in paid_plans:
        end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
        if end_date > now:
            total_remaining_minutes += int((end_date - now).total_seconds() // 60)

    days = total_remaining_minutes // 1440
    hours = (total_remaining_minutes % 1440) // 60
    minutes = total_remaining_minutes % 60
    time_description = f"{days} дн. {hours} ч. {minutes} мин."

    if gift_type == 'Подарок баллов' and sender_points < 0.5:
        bot.send_message(message.chat.id, (
            f"❌ У отправителя недостаточно баллов для подарка!\n\n"
            f"💰 *Доступно баллов у отправителя:* {format_number(sender_points)}\n"
            f"👉 Пожалуйста, выберите другой тип подарка или отправителя"
        ), parse_mode="Markdown")
        bot.register_next_step_handler(message, process_gift_type, sender_id, recipient_id)
        return
    if gift_type == 'Подарок времени' and total_remaining_minutes == 0:
        bot.send_message(message.chat.id, (
            f"❌ У отправителя нет доступного времени для подарка!\n\n"
            f"⏳ *Доступно времени у отправителя:* {time_description}\n"
            f"👉 Пожалуйста, выберите другой тип подарка или отправителя"
        ), parse_mode="Markdown")
        bot.register_next_step_handler(message, process_gift_type, sender_id, recipient_id)
        return

    if gift_type == 'Подарок баллов':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в управление подарками')
        markup.add('Вернуться в управление системой')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, (
            f"🎁 *Подарок баллов*\n\n"
            f"📤 *Отправитель:* {sender_username} (`{sender_id}`)\n"
            f"📥 *Получатель:* {recipient_username} (`{recipient_id}`)\n\n"
            f"💰 *Доступно баллов у отправителя:* {format_number(sender_points)}\n\n"
            "Введите количество баллов для подарка:"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_gift_points_amount, sender_id, recipient_id)
    else:  
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Минуты', 'Часы', 'Дни')
        markup.add('Вернуться в управление подарками')
        markup.add('Вернуться в управление системой')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, (
            f"🎁 *Подарок времени*\n\n"
            f"📤 *Отправитель:* {sender_username} (`{sender_id}`)\n"
            f"📥 *Получатель:* {recipient_username} (`{recipient_id}`)\n\n"
            f"⏳ *Доступно времени у отправителя:* {time_description}\n\n"
            "Выберите единицу времени для подарка:"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_gift_time_unit, sender_id, recipient_id)

@text_only_handler
def process_gift_points_amount(message, sender_id, recipient_id):
    if message.text == "Вернуться в управление подарками":
        manage_gifts(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        gift_points = float(message.text.replace(',', '.'))
        if gift_points < 0.5:
            raise ValueError("Минимальное количество баллов — 0.5!")
        if gift_points % 0.5 != 0:
            raise ValueError("Баллы должны быть кратны 0.5!")

        data = load_payment_data()
        users_data = load_users()

        raw_sender_username = users_data.get(sender_id, {}).get('username', f"@{sender_id}")
        raw_recipient_username = users_data.get(recipient_id, {}).get('username', f"@{recipient_id}")

        sender_data = data['subscriptions']['users'].setdefault(sender_id, {
            "plans": [], "total_amount": 0, "username": raw_sender_username, "referral_points": 0,
            "free_feature_trials": {}, "promo_usage_history": [], "referral_milestones": {}, "points_history": []
        })
        available_points = sender_data.get('referral_points', 0)
        if gift_points > available_points:
            raise ValueError(f"Недостаточно баллов! Доступно: {format_number(available_points)}")

        sender_data['referral_points'] = max(0, sender_data.get('referral_points', 0) - gift_points)
        sender_data['points_history'].append({
            "action": "spent",
            "points": gift_points,
            "reason": f"подарок {raw_recipient_username} (от админа)",  
            "date": datetime.now().strftime("%d.%m.%Y в %H:%M")
        })

        recipient_data = data['subscriptions']['users'].setdefault(recipient_id, {
            "plans": [], "total_amount": 0, "username": raw_recipient_username, "referral_points": 0,
            "free_feature_trials": {}, "promo_usage_history": [], "referral_milestones": [], "points_history": []
        })
        recipient_data['referral_points'] += gift_points
        recipient_data['points_history'].append({
            "action": "earned",
            "points": gift_points,
            "reason": f"подарок от {raw_sender_username} (от админа)", 
            "date": datetime.now().strftime("%d.%m.%Y в %H:%M")
        })

        save_payments_data(data)

        admin_message = (
            f"✅ Подарок назначен:\n\n"
            f"📤 *Отправитель:* {escape_markdown(raw_sender_username)} (`{sender_id}`)\n"
            f"📥 *Получатель:* {escape_markdown(raw_recipient_username)} (`{recipient_id}`)\n\n"
            f"🎁 *Подарок:* {format_number(gift_points)} баллов"
        )
        sender_message = (
            f"✅ *Администратор от вашего имени подарил {raw_recipient_username} {format_number(gift_points)} баллов!*\n"
        )
        recipient_message = (
            f"✅ *{raw_sender_username} подарил вам {format_number(gift_points)} баллов!*\n"
            f"🚀 Используйте их в системе баллов или в магазине!"
        )

        bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
        bot.send_message(sender_id, sender_message, parse_mode="Markdown")
        bot.send_message(recipient_id, recipient_message, parse_mode="Markdown")

        manage_gifts(message)
    except ValueError as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_gift_points_amount, sender_id, recipient_id)

@text_only_handler
def process_gift_time_unit(message, sender_id, recipient_id):
    if message.text == "Вернуться в управление подарками":
        manage_gifts(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    unit = message.text.strip().lower()
    if unit not in ['минуты', 'часы', 'дни']:
        bot.send_message(message.chat.id, "Неверная единица измерения!\nПожалуйста, выберите снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_gift_time_unit, sender_id, recipient_id)
        return

    users_data = load_users()
    data = load_payment_data()
    sender_data = data['subscriptions']['users'].get(sender_id, {})
    sender_username = escape_markdown(users_data.get(sender_id, {}).get('username', f"@{sender_id}"))
    recipient_username = escape_markdown(users_data.get(recipient_id, {}).get('username', f"@{recipient_id}"))

    allowed_plan_names = ['trial', 'weekly', 'monthly', 'quarterly', 'semiannual', 'yearly', 'points_bonus', 'gift_time', 'store_time', 'custom']
    paid_plans = [
        plan for plan in sender_data.get('plans', [])
        if plan['plan_name'] in allowed_plan_names
        and datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M") > datetime.now()
    ]
    total_remaining_minutes = 0
    now = datetime.now()
    for plan in paid_plans:
        end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
        if end_date > now:
            total_remaining_minutes += int((end_date - now).total_seconds() // 60)

    days = total_remaining_minutes // 1440
    hours = (total_remaining_minutes % 1440) // 60
    minutes = total_remaining_minutes % 60
    time_description = f"{days} дн. {hours} ч. {minutes} мин."

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в управление подарками')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    prompt = f"Введите количество {unit} для подарка:"
    bot.send_message(message.chat.id, (
        f"🎁 *Подарок времени*\n\n"
        f"📤 *Отправитель:* {sender_username} (`{sender_id}`)\n"
        f"📥 *Получатель:* {recipient_username} (`{recipient_id}`)\n\n"
        f"⏳ *Доступно времени у отправителя:* {time_description}\n\n"
        f"{prompt}"
    ), reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_gift_time_amount, sender_id, recipient_id, unit)

@text_only_handler
def process_gift_time_amount(message, sender_id, recipient_id, unit):
    if message.text == "Вернуться в управление подарками":
        manage_gifts(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError("Количество должно быть положительным!")

        if unit == 'минуты':
            gift_minutes = amount
        elif unit == 'часы':
            gift_minutes = amount * 60
        else:  
            gift_minutes = amount * 1440

        data = load_payment_data()
        users_data = load_users()

        raw_sender_username = users_data.get(sender_id, {}).get('username', f"@{sender_id}")
        raw_recipient_username = users_data.get(recipient_id, {}).get('username', f"@{recipient_id}")

        sender_data = data['subscriptions']['users'].setdefault(sender_id, {
            "plans": [], "total_amount": 0, "username": raw_sender_username, "referral_points": 0,
            "free_feature_trials": {}, "promo_usage_history": [], "referral_milestones": {}, "points_history": []
        })
        allowed_plan_names = ['trial', 'weekly', 'monthly', 'quarterly', 'semiannual', 'yearly', 'points_bonus', 'gift_time', 'store_time', 'custom']
        paid_plans = [
            plan for plan in sender_data.get('plans', [])
            if plan['plan_name'] in allowed_plan_names
            and datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M") > datetime.now()
        ]
        total_remaining_minutes = 0
        now = datetime.now()
        for plan in paid_plans:
            end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
            if end_date > now:
                total_remaining_minutes += int((end_date - now).total_seconds() // 60)
        
        days = total_remaining_minutes // 1440
        hours = (total_remaining_minutes % 1440) // 60
        minutes = total_remaining_minutes % 60
        time_description = f"{days} дн. {hours} ч. {minutes} мин."

        if gift_minutes > total_remaining_minutes:
            raise ValueError(f"Недостаточно времени! Доступно: {time_description}")

        gift_duration = timedelta(minutes=gift_minutes)
        remaining_minutes = gift_minutes
        user_plans = sender_data.get('plans', [])
        for plan in sorted(
            [p for p in user_plans if datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") > datetime.now() and p['plan_name'] in allowed_plan_names],
            key=lambda x: datetime.strptime(x['end_date'], "%d.%m.%Y в %H:%M")
        ):
            if remaining_minutes <= 0:
                break
            end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
            available_minutes = int((end_date - datetime.now()).total_seconds() // 60)
            minutes_to_deduct = min(remaining_minutes, available_minutes)
            new_end_date = end_date - timedelta(minutes=minutes_to_deduct)
            plan['end_date'] = new_end_date.strftime("%d.%m.%Y в %H:%M")
            remaining_minutes -= minutes_to_deduct

        sender_data['plans'] = [p for p in user_plans if datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") > datetime.now()]

        recipient_data = data['subscriptions']['users'].setdefault(recipient_id, {
            "plans": [], "total_amount": 0, "username": raw_recipient_username, "referral_points": 0,
            "free_feature_trials": {}, "promo_usage_history": [], "referral_milestones": [], "points_history": []
        })

        recipient_prev_end = max(
            [datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") for p in recipient_data['plans']] or [datetime.now()]
        )
        gift_start_dt = max(datetime.now(), recipient_prev_end)
        gift_end_dt = gift_start_dt + gift_duration

        recipient_data['plans'].append({
            "plan_name": "gift_time",
            "start_date": gift_start_dt.strftime("%d.%m.%Y в %H:%M"),
            "end_date": gift_end_dt.strftime("%d.%m.%Y в %H:%M"),
            "price": 0,
            "source": f"gift_from_{sender_id}_admin"
        })

        days = int(gift_minutes // 1440)
        hours = int((gift_minutes % 1440) // 60)
        minutes = int(gift_minutes % 60)
        gift_description = ""
        if days > 0:
            gift_description += f"{days} дн. "
        if hours > 0:
            gift_description += f"{hours} ч. "
        if minutes > 0:
            gift_description += f"{minutes} мин."

        sender_data['points_history'].append({
            "action": "spent",
            "points": 0,
            "reason": f"подарок времени {raw_recipient_username}: {gift_description} (от админа)",  
            "date": datetime.now().strftime("%d.%m.%Y в %H:%M")
        })
        recipient_data['points_history'].append({
            "action": "earned",
            "points": 0,
            "reason": f"подарок времени от {raw_sender_username}: {gift_description} (от админа)", 
            "date": datetime.now().strftime("%d.%m.%Y в %H:%M")
        })

        save_payments_data(data)

        admin_message = (
            f"✅ Подарок времени назначен:\n\n"
            f"📤 *Отправитель:* {escape_markdown(raw_sender_username)} (`{sender_id}`)\n"
            f"📥 *Получатель:* {escape_markdown(raw_recipient_username)} (`{recipient_id}`)\n\n"
            f"🎁 *Подарок:* {gift_description}\n\n"
            f"🕒 *Начало:* {gift_start_dt.strftime('%d.%m.%Y в %H:%M')}\n"
            f"⌛ *Конец:* {gift_end_dt.strftime('%d.%m.%Y в %H:%M')}"
        )
        sender_message = (
            f"✅ *Администратор от вашего имени подарил {raw_recipient_username} {gift_description}!*\n\n"
            f"🕒 *Начало:* {gift_start_dt.strftime('%d.%m.%Y в %H:%M')}\n"
            f"⌛ *Конец:* {gift_end_dt.strftime('%d.%m.%Y в %H:%M')}"
        )
        recipient_message = (
            f"✅ *{raw_sender_username} подарил вам {gift_description}!*\n\n"
            f"🕒 *Начало:* {gift_start_dt.strftime('%d.%m.%Y в %H:%M')}\n"
            f"⏳ *Конец:* {gift_end_dt.strftime('%d.%m.%Y в %H:%M')}"
        )

        bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
        bot.send_message(sender_id, sender_message, parse_mode="Markdown")
        bot.send_message(recipient_id, recipient_message, parse_mode="Markdown")

        manage_gifts(message)
    except ValueError as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, введите корректное число", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_gift_time_amount, sender_id, recipient_id, unit)

# ------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ ПОДАРКАМИ (просмотр подарков) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Просмотр подарков' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_gifts(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Просмотр подарков'):
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
    markup.add('Вернуться в управление подарками')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для просмотра истории подарков:", reply_markup=markup)
    bot.register_next_step_handler(message, process_view_gifts)

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

@text_only_handler
def process_view_gifts(message):
    if message.text == "Вернуться в управление подарками":
        manage_gifts(message)
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

    if not user_id or user_id not in users_data:
        bot.send_message(message.chat.id, "Пользователь не найден!\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_view_gifts)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})
    history = user_data.get('points_history', [])
    gift_entries = [entry for entry in history if isinstance(entry, dict) and 'reason' in entry and 'подарок' in str(entry['reason']).lower()]

    if not gift_entries:
        bot.send_message(message.chat.id, "❌ У пользователя нет истории подарков!", parse_mode="Markdown")
        manage_gifts(message)
        return

    username = escape_markdown(users_data.get(str(user_id), {}).get('username', f"@{user_id}"))

    def format_time(time_str):
        time_str = clean_escaped_text(time_str)
        try:
            num_str = time_str.split()[0].replace(',', '.')
            minutes = float(num_str)
            if "минут" in time_str.lower():
                pass
            elif "ч" in time_str.lower():
                minutes *= 60
            elif "дн" in time_str.lower():
                minutes *= 1440
            days = int(minutes // 1440)
            hours = int((minutes % 1440) // 60)
            minutes = int(minutes % 60)
            time_description = ""
            if days > 0:
                time_description += f"{days} дн. "
            if hours > 0:
                time_description += f"{hours} ч. "
            if minutes > 0:
                time_description += f"{minutes} мин."
            return time_description.strip() or "0 мин."
        except (ValueError, IndexError):
            return time_str

    history_summary = f"*История подарков пользователя* {username} - `{user_id}`:\n\n"
    for idx, entry in enumerate(gift_entries, 1):
        action = "подарено" if entry['action'] == "spent" else "получено"
        gift_type = []
        if entry['points'] > 0:
            gift_type.append(f"{format_number(entry['points'])} {pluralize_points(entry['points'])}")
        if "времени" in entry['reason']:
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

    manage_gifts(message)