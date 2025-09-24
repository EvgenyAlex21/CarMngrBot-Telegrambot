from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, timedelta, pytz
from core.bot_instance import bot
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from handlers.admin.system_management.system_management_main import manage_system
from handlers.admin.statistics.statistics import check_admin_access, escape_markdown
from handlers.user.subscription.buy_subscription import load_subscriptions_and_store
from handlers.user.subscription.your_subscription import translate_plan_name
from handlers.user.subscription.gifts import split_message
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

def save_users_data(data):
    from handlers.user.user_main_menu import save_users_data as _save
    return _save(data)

# ------------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ (управление подписками) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Управление подписками' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def manage_subscriptions(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Управление подписками'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Добавление подписки', 'Просмотр подписок', 'Удаление подписок')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите действие для управления подписками:", reply_markup=markup)

def split_message(message, max_length=4096):
    parts = []
    while len(message) > max_length:
        part = message[:max_length]
        last_space = part.rfind(' ')
        if last_space != -1:
            parts.append(part[:last_space])
            message = message[last_space:]
        else:
            parts.append(part)
            message = message[max_length:]
    parts.append(message)
    return parts

# --------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ ПОДПИСКАМИ (добавление подписки) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Добавление подписки' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def add_subscription(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Добавление подписки'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    list_users_for_payments_pay(message)

@text_only_handler
def list_users_for_payments_pay(message):
    if message.text == "Вернуться в управление подписками":
        manage_subscriptions(message)
        return
		
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
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
    markup.add(types.KeyboardButton('Вернуться в управление подписками'))
    markup.add(types.KeyboardButton('Вернуться в управление системой'))
    markup.add(types.KeyboardButton('В меню админ-панели'))
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для добавления подписки:", reply_markup=markup)
    bot.register_next_step_handler(message, process_add_subscription)

@text_only_handler
def process_add_subscription(message):
    if message.text == "Вернуться в управление подписками":
        manage_subscriptions(message)
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
        bot.register_next_step_handler(message, process_add_subscription)
        return

    subscription_plans = load_subscriptions_and_store()[0]
    if not subscription_plans:
        bot.send_message(message.chat.id, "❌ Планы подписки не загружены!")
        manage_system(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    plan_labels = [plan['label'] for plan in subscription_plans.values()]

    for i in range(0, len(plan_labels), 3):
        row = plan_labels[i:i+3]
        markup.row(*row)
    
    markup.row('Свой план')
    markup.row('Вернуться в управление подписками')
    markup.row('Вернуться в управление системой')
    markup.row('В меню админ-панели')

    bot.send_message(message.chat.id, "Выберите план подписки:", reply_markup=markup)
    bot.register_next_step_handler(message, process_add_subscription_plan, user_id)

@text_only_handler
def process_add_subscription_plan(message, user_id):
    if message.text in ["Вернуться в управление подписками", "Вернуться в управление системой", "В меню админ-панели"]:
        if message.text == "Вернуться в управление подписками":
            manage_subscriptions(message)
        elif message.text == "Вернуться в управление системой":
            manage_system(message)
        else:
            show_admin_panel(message)
        return

    plan_name = message.text.strip().lower()
    subscription_plans = load_subscriptions_and_store()[0]
    valid_plans = {v['label'].lower(): k for k, v in subscription_plans.items()}
    valid_plans['свой план'] = 'custom'

    if plan_name not in valid_plans:
        bot.send_message(message.chat.id, "Неверный план подписки!\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_add_subscription_plan, user_id)
        return

    if plan_name == 'свой план':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('В минутах', 'В часах', 'В днях')
        markup.add('Вернуться в управление подписками')
        markup.add('Вернуться в управление системой')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Выберите единицу измерения длительности подписки:", reply_markup=markup)
        bot.register_next_step_handler(message, process_custom_plan_unit, user_id)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].setdefault(str(user_id), {'plans': []})

    latest_end_date = datetime.now()
    for plan in user_data['plans']:
        plan_end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
        if plan_end_date > latest_end_date:
            latest_end_date = plan_end_date

    plan_key = valid_plans[plan_name]
    plan_details = subscription_plans[plan_key]
    duration = plan_details['duration']
    plan_name_rus = plan_details['label']
    new_end_date = latest_end_date + timedelta(days=duration)
    plan_name_eng = plan_key.replace('_subscription_', '_')

    for plan in user_data['plans']:
        if (plan['plan_name'] == plan_name_eng and
            plan['start_date'] == latest_end_date.strftime("%d.%m.%Y в %H:%M") and
            plan['end_date'] == new_end_date.strftime("%d.%m.%Y в %H:%M")):
            bot.send_message(message.chat.id, f"❌ Подписка '{plan_name_rus}' уже существует для пользователя!", parse_mode="Markdown")
            manage_system(message)
            return

    new_plan = {
        "plan_name": plan_name_eng,
        "start_date": latest_end_date.strftime("%d.%m.%Y в %H:%M"),
        "end_date": new_end_date.strftime("%d.%m.%Y в %H:%M"),
        "price": 0,
        "source": "admin"
    }
    user_data['plans'].append(new_plan)
    data['subscriptions']['users'][str(user_id)] = user_data
    save_payments_data(data)

    users_data = load_users()
    username = escape_markdown(users_data.get(str(user_id), {}).get('username', f"@{user_id}"))

    admin_message = (
        f"✅ Пользователю {username} - `{user_id}` назначен:\n\n"
        f"💼 *План подписки:* {plan_name_rus}\n"
        f"🕒 *Начало:* {latest_end_date.strftime('%d.%m.%Y в %H:%M')}\n"
        f"⌛ *Конец:* {new_end_date.strftime('%d.%m.%Y в %H:%M')}"
    )
    user_message = (
        f"✅ Администратор назначил вам:\n\n"
        f"💼 *План подписки:* {plan_name_rus}\n"
        f"🕒 *Начало:* {latest_end_date.strftime('%d.%m.%Y в %H:%M')}\n"
        f"⌛ *Конец:* {new_end_date.strftime('%d.%m.%Y в %H:%M')}\n\n"
    )

    bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
    bot.send_message(user_id, user_message, parse_mode="Markdown")

    manage_system(message)

@text_only_handler
def process_custom_plan_unit(message, user_id):
    if message.text == "Вернуться в управление подписками":
        manage_subscriptions(message)
        return
		
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    unit = message.text.strip().lower()
    if unit not in ['в минутах', 'в часах', 'в днях']:
        bot.send_message(message.chat.id, "Неверная единица измерения!\nПожалуйста, выберите снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_custom_plan_unit, user_id)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в управление подписками')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    if unit == 'в минутах':
        prompt = "Введите количество минут для подписки:"
    elif unit == 'в часах':
        prompt = "Введите количество часов для подписки:"
    else:  
        prompt = "Введите количество дней для подписки:"

    bot.send_message(message.chat.id, prompt, reply_markup=markup)
    bot.register_next_step_handler(message, process_custom_plan_duration, user_id, unit)

@text_only_handler
def process_custom_plan_duration(message, user_id, unit):
    if message.text == "Вернуться в управление подписками":
        manage_subscriptions(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        input_text = message.text.strip().replace(',', '.')
        duration = float(input_text)
        if duration <= 0:
            raise ValueError("Длительность должна быть положительным числом!")

        duration_display = f"{int(duration)}" if float(duration).is_integer() else f"{duration:.2f}"
        duration_int = int(duration)

        data = load_payment_data()
        user_data = data['subscriptions']['users'].setdefault(str(user_id), {'plans': []})

        latest_end_date = datetime.now()
        for plan in user_data['plans']:
            plan_end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
            if plan_end_date > latest_end_date:
                latest_end_date = plan_end_date

        unit_mapping = {
            'в минутах': 'минуты',
            'в часах': 'часы',
            'в днях': 'дни'
        }
        unit_display = {
            'минуты': 'мин.',
            'часы': 'ч.',
            'дни': 'дн.'
        }
        duration_unit = unit_mapping.get(unit.lower(), 'дни')

        if unit.lower() == 'в минутах':
            new_end_date = latest_end_date + timedelta(minutes=duration)
            duration_str = f"{duration_display} мин."
        elif unit.lower() == 'в часах':
            new_end_date = latest_end_date + timedelta(hours=duration)
            duration_str = f"{duration_display} ч."
        else:
            new_end_date = latest_end_date + timedelta(days=duration)
            duration_str = f"{duration_display} дн."

        new_plan = {
            "plan_name": "custom",
            "start_date": latest_end_date.strftime("%d.%m.%Y в %H:%M"),
            "end_date": new_end_date.strftime("%d.%m.%Y в %H:%M"),
            "price": 0,
            "source": "admin",
            "duration_unit": duration_unit,
            "duration_value": duration_int
        }
        user_data['plans'].append(new_plan)
        data['subscriptions']['users'][str(user_id)] = user_data
        save_payments_data(data)

        users_data = load_users()
        username = escape_markdown(users_data.get(str(user_id), {}).get('username', f"@{user_id}"))

        admin_message = (
            f"✅ Пользователю {username} - `{user_id}` назначен:\n\n"
            f"💼 *План подписки:* индивидуальный ({duration_str})\n"
            f"🕒 *Начало:* {latest_end_date.strftime('%d.%m.%Y в %H:%M')}\n"
            f"⌛ *Конец:* {new_end_date.strftime('%d.%m.%Y в %H:%M')}"
        )
        user_message = (
            f"✅ Администратор назначил вам:\n\n"
            f"💼 *План подписки:* индивидуальный ({duration_str})\n"
            f"🕒 *Начало:* {latest_end_date.strftime('%d.%m.%Y в %H:%M')}\n"
            f"⌛ *Конец:* {new_end_date.strftime('%d.%m.%Y в %H:%M')}\n\n"
        )

        bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
        bot.send_message(user_id, user_message, parse_mode="Markdown")
        manage_system(message)
    except ValueError as e:
        bot.send_message(message.chat.id, f"❌ {str(e)}!\nПожалуйста, введите корректное число")
        bot.register_next_step_handler(message, process_custom_plan_duration, user_id, unit)

# --------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ ПОДПИСКАМИ (просмотр подписок) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Просмотр подписок' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_subscriptions(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Просмотр подписок'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return
    
    list_users_for_payments_view(message)

@text_only_handler
def list_users_for_payments_view(message):
    if message.text == "Вернуться в управление подписками":
        manage_subscriptions(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
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
    markup.add(types.KeyboardButton('Вернуться в управление подписками'))
    markup.add(types.KeyboardButton('Вернуться в управление системой'))
    markup.add(types.KeyboardButton('В меню админ-панели'))
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для просмотра подписок:", reply_markup=markup)
    bot.register_next_step_handler(message, process_view_subscriptions)

@text_only_handler
def process_view_subscriptions(message):
    if message.text == "Вернуться в управление подписками":
        manage_subscriptions(message)
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
        bot.register_next_step_handler(message, process_view_subscriptions)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})
    if 'plans' not in user_data or not user_data['plans']:
        bot.send_message(message.chat.id, "❌ У пользователя нет подписок!", parse_mode="Markdown")
        manage_system(message)
        return

    plans_summary = "💎 *Список подписок:*\n\n"
    total_days_left = 0
    total_cost_active = 0
    active_plans = []
    now = datetime.now()

    unit_display = {
        'минуты': 'мин.',
        'часы': 'ч.',
        'дни': 'дн.'
    }

    for idx, plan in enumerate(user_data['plans'], start=1):
        end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
        is_active = end_date >= now

        if is_active:
            remaining_time = end_date - now
            days_left = remaining_time.days
            hours_left, remainder = divmod(remaining_time.seconds, 3600)
            minutes_left = remainder // 60
            time_status = f"📅 *Дней осталось:* {days_left} дней и {hours_left:02d}:{minutes_left:02d} часов"
            total_days_left += days_left
            total_cost_active += plan['price']
            active_plans.append(plan)
        else:
            elapsed_time = now - end_date
            days_elapsed = elapsed_time.days
            hours_elapsed, remainder = divmod(elapsed_time.seconds, 3600)
            minutes_elapsed = remainder // 60
            time_status = f"📅 *Завершено:* {days_elapsed} дней и {hours_elapsed:02d}:{minutes_elapsed:02d} часов назад"

        plan_name_lower = plan['plan_name'].lower()
        source = plan.get('source', '')

        if plan_name_lower in {"free", "referral_bonus", "ad_bonus", "activity", "points_bonus", "referral", "monthly_leader_bonus", "leaderboard"}:
            period_type = f"🎁 *№{idx}. {'(Завершён)' if not is_active else ''} Бонусный период:*"
            subscription_type = translate_plan_name(plan_name_lower)

        elif plan_name_lower in {"gift_time", "custom", "exchangetime"}:
            period_type = f"✨ *№{idx}. {'(Завершён)' if not is_active else ''} Подаренный период:*"
            if plan_name_lower == "custom":
                duration_value = int(plan.get('duration_value', 1))
                duration_unit = plan.get('duration_unit', 'дни')
                subscription_type = f"индивидуальный ({duration_value} {unit_display.get(duration_unit, 'дн.')})"
            else:
                subscription_type = translate_plan_name(plan_name_lower)
        else:
            if source in {"user", "promo_100_percent", "store"}:
                period_type = f"💳 *№{idx}. {'(Завершён)' if not is_active else ''} Платный период:*"
            else:  
                period_type = f"📦 *№{idx}. {'(Завершён)' if not is_active else ''} Назначенный период:*"
            subscription_type = translate_plan_name(plan_name_lower)

        price_formatted = f"{plan['price']:.2f}"
        plans_summary += (
            f"{period_type}\n\n"
            f"💼 *Тип подписки:* {subscription_type}\n"
            f"{time_status}\n"
            f"🕒 *Начало:* {plan['start_date']}\n"
            f"⌛ *Конец:* {plan['end_date']}\n"
            f"💰 *Стоимость подписки:* {price_formatted} руб.\n\n"
        )

    message_parts = split_message(plans_summary)
    for part in message_parts:
        bot.send_message(message.chat.id, part, parse_mode="Markdown")

    total_amount = user_data.get('total_amount', 0)
    total_cost_active_formatted = f"{total_cost_active:.2f}"
    total_amount_formatted = f"{total_amount:.2f}"

    if active_plans:
        subscription_types = []
        for p in active_plans:
            plan_name_lower = p['plan_name'].lower()
            if plan_name_lower == 'custom':
                duration_value = int(p.get('duration_value', 1))
                duration_unit = p.get('duration_unit', 'дни')
                subscription_types.append(f"индивидуальный ({duration_value} {unit_display.get(duration_unit, 'дн.')})")
            else:
                subscription_types.append(translate_plan_name(p['plan_name']))

        total_amount_message = (
            "💎 *Итоговая подписочная оценка:*\n\n"
            f"💼 *Типы подписок:* {', '.join(subscription_types)}\n"
            f"📅 *Дней осталось:* {total_days_left} дней и {hours_left:02d}:{minutes_left:02d} часов\n"
            f"🕒 *Начало:* {min(datetime.strptime(p['start_date'], '%d.%m.%Y в %H:%M') for p in active_plans).strftime('%d.%m.%Y в %H:%M')}\n"
            f"⌛ *Конец:* {max(datetime.strptime(p['end_date'], '%d.%m.%Y в %H:%M') for p in active_plans).strftime('%d.%m.%Y в %H:%M')}\n"
            f"💰 *Общая стоимость активных подписок:* {total_cost_active_formatted} руб.\n"
            f"💰 *Общая стоимость всех подписок:* {total_amount_formatted} руб."
        )
    else:
        total_amount_message = (
            "💎 *Итоговая подписочная оценка:*\n\n"
            "📅 *Активных подписок нет!*\n"
            f"💰 *Общая стоимость всех подписок:* {total_amount_formatted} руб."
        )

    bot.send_message(message.chat.id, total_amount_message, parse_mode="Markdown")
    manage_system(message)

# --------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ ПОДПИСКАМИ (удаление подписок) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Удаление подписок' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_subscription(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Удаление подписок'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return
    
    list_users_for_payments_del(message)

@text_only_handler
def list_users_for_payments_del(message):
    if message.text == "Вернуться в управление подписками":
        manage_subscriptions(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
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
    markup.add(types.KeyboardButton('Вернуться в управление подписками'))
    markup.add(types.KeyboardButton('Вернуться в управление системой'))
    markup.add(types.KeyboardButton('В меню админ-панели'))
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для удаления подписки:", reply_markup=markup)
    bot.register_next_step_handler(message, process_delete_subscription)

@text_only_handler
def process_delete_subscription(message):
    if message.text == "Вернуться в управление подписками":
        manage_subscriptions(message)
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
        bot.register_next_step_handler(message, process_delete_subscription)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})
    if 'plans' not in user_data or not user_data['plans']:
        bot.send_message(message.chat.id, "❌ У пользователя нет подписок для удаления!", parse_mode="Markdown")
        manage_system(message)
        return

    now = datetime.now(pytz.UTC)
    active_plans = [p for p in user_data['plans'] if datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC) > now and p['plan_name'].lower() != 'free']
    if not active_plans:
        bot.send_message(message.chat.id, "❌ У пользователя нет активных подписок для удаления!", parse_mode="Markdown")
        manage_system(message)
        return

    plans_summary = "💎 *Список активных подписок:*\n\n"

    unit_display = {
        'минуты': 'мин.',
        'часы': 'ч.',
        'дни': 'дн.'
    }

    for idx, plan in enumerate(active_plans, start=1):
        end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC)
        remaining_time = end_date - now
        days_left = remaining_time.days
        hours_left, remainder = divmod(remaining_time.seconds, 3600)
        minutes_left = remainder // 60

        plan_name_lower = plan['plan_name'].lower()
        source = plan.get('source', '')

        if plan_name_lower in {"referral_bonus", "ad_bonus", "activity", "points_bonus", "referral", "monthly_leader_bonus", "leaderboard"}:
            period_type = f"🎁 *№{idx}. Бонусный период:*"
            subscription_type = translate_plan_name(plan_name_lower)
        elif plan_name_lower in {"gift_time", "custom", "exchangetime"}:
            period_type = f"✨ *№{idx}. Подаренный период:*"
            if plan_name_lower == "custom":
                duration_value = int(plan.get('duration_value', 1))
                duration_unit = plan.get('duration_unit', 'дни')
                subscription_type = f"индивидуальный ({duration_value} {unit_display.get(duration_unit, 'дн.')})"
            else:
                subscription_type = translate_plan_name(plan_name_lower)
        else:
            if source in {"user", "promo_100_percent", "store"}:
                period_type = f"💳 *№{idx}. Платный период:*"
            else:  
                period_type = f"📦 *№{idx}. Назначенный период:*"
            subscription_type = translate_plan_name(plan_name_lower)

        price_formatted = f"{plan['price']:.2f}"
        plans_summary += (
            f"{period_type}\n\n"
            f"💼 *Тип подписки:* {subscription_type}\n"
            f"📅 *Дней осталось:* {days_left} дней и {hours_left:02d}:{minutes_left:02d} часов\n"
            f"🕒 *Начало:* {plan['start_date']}\n"
            f"⌛ *Конец:* {plan['end_date']}\n"
            f"💰 *Стоимость подписки:* {price_formatted} руб.\n\n"
        )

    message_parts = split_message(plans_summary)
    for part in message_parts:
        bot.send_message(message.chat.id, part, parse_mode="Markdown")

    bot.send_message(message.chat.id, "Введите номера подписок для удаления:")
    bot.register_next_step_handler(message, process_delete_subscription_plan, user_id, active_plans)

@text_only_handler
def process_delete_subscription_plan(message, user_id, plans):
    if message.text == "Вернуться в управление подписками":
        manage_subscriptions(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    user_input = message.text.strip()
    plan_numbers = []
    invalid_numbers = []

    input_numbers = [num.strip() for num in user_input.split(',') if num.strip()]
    
    for num in input_numbers:
        try:
            num_int = int(num)
            if 1 <= num_int <= len(plans):
                plan_numbers.append(num_int)
            else:
                invalid_numbers.append(num)
        except ValueError:
            invalid_numbers.append(num)

    if not plan_numbers:
        bot.send_message(message.chat.id, "Ни один из введенных номеров не является корректным!\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_delete_subscription_plan, user_id, plans)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'][str(user_id)]
    data['subscription_history'].setdefault(str(user_id), [])

    users_data = load_users()
    username = escape_markdown(users_data.get(str(user_id), {}).get('username', f"@{user_id}"))

    unit_display = {
        'минуты': 'мин.',
        'часы': 'ч.',
        'дни': 'дн.'
    }

    for plan_number in sorted(set(plan_numbers), reverse=True):
        plan = plans[plan_number - 1]

        plan_name_lower = plan['plan_name'].lower()
        subscription_type = translate_plan_name(plan_name_lower)
        if plan_name_lower == 'custom':
            duration_value = int(plan.get('duration_value', 1))
            duration_unit = plan.get('duration_unit', 'дни')
            subscription_type = f"индивидуальный ({duration_value} {unit_display.get(duration_unit, 'дн.')})"

        target_plan = None
        for p in user_data['plans']:
            if (p.get('telegram_payment_charge_id') == plan.get('telegram_payment_charge_id') and
                p.get('start_date') == plan.get('start_date') and
                p.get('end_date') == plan.get('end_date') and
                p.get('plan_name') == plan.get('plan_name')):
                target_plan = p
                break

        if not target_plan:
            bot.send_message(message.chat.id, f"⚠️ Подписка №{plan_number} ({subscription_type}) не найдена в активных подписках пользователя!", parse_mode="Markdown")
            continue

        target_plan['status'] = 'cancelled'
        target_plan['cancelled_date'] = datetime.now(pytz.UTC).strftime("%d.%m.%Y в %H:%M")
        data['subscription_history'][str(user_id)].append(target_plan)

        admin_message = (
            f"🚫 Пользователю {username} - `{user_id}` отменён:\n\n"
            f"💼 *План подписки:* {subscription_type}\n"
            f"🕒 *Начало:* {target_plan['start_date']}\n"
            f"⌛ *Конец:* {target_plan['end_date']}"
        )
        user_message = (
            f"🚫 Администратор отменил вам:\n\n"
            f"💼 *План подписки:* {subscription_type}\n"
            f"🕒 *Начало:* {target_plan['start_date']}\n"
            f"⌛ *Конец:* {target_plan['end_date']}"
        )

        user_data['plans'].remove(target_plan)
        bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
        bot.send_message(user_id, user_message, parse_mode="Markdown")

    now = datetime.now(pytz.UTC)
    active_plans = [p for p in user_data['plans'] if datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC) > now]
    if active_plans:
        active_plans.sort(key=lambda x: datetime.strptime(x['start_date'], "%d.%m.%Y в %H:%M"))
        previous_end_date = now
        for plan in active_plans:
            start_date = datetime.strptime(plan['start_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC)
            end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC)
            duration = (end_date - start_date).total_seconds() / (24 * 3600) 
            plan['start_date'] = previous_end_date.strftime("%d.%m.%Y в %H:%M")
            plan['end_date'] = (previous_end_date + timedelta(days=duration)).strftime("%d.%m.%Y в %H:%M")
            previous_end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC)

            plan_name_lower = plan['plan_name'].lower()
            subscription_type = translate_plan_name(plan_name_lower)
            if plan_name_lower == 'custom':
                duration_value = int(plan.get('duration_value', 1))
                duration_unit = plan.get('duration_unit', 'дни')
                subscription_type = f"индивидуальный ({duration_value} {unit_display.get(duration_unit, 'дн.')})"
            admin_message = (
                f"🔄 Пользователю {username} - `{user_id}` изменены даты подписки:\n\n"
                f"💼 *План подписки:* {subscription_type}\n"
                f"🕒 *Новое начало:* {plan['start_date']}\n"
                f"⌛ *Новый конец:* {plan['end_date']}"
            )
            user_message = (
                f"🔄 Администратор изменил даты вашей подписки:\n\n"
                f"💼 *План подписки:* {subscription_type}\n"
                f"🕒 *Новое начало:* {plan['start_date']}\n"
                f"⌛ *Новый конец:* {plan['end_date']}"
            )
            bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
            bot.send_message(user_id, user_message, parse_mode="Markdown")

    user_data['total_amount'] = sum(p['price'] for p in user_data.get('plans', []))
    data['all_users_total_amount'] = sum(
        u.get('total_amount', 0) for u in data['subscriptions']['users'].values()
    )

    save_payments_data(data)

    if invalid_numbers:
        invalid_numbers_str = ", ".join(invalid_numbers)
        bot.send_message(message.chat.id, f"⚠️ Номера `{invalid_numbers_str}` некорректны и пропущены!", parse_mode="Markdown")

    manage_system(message)