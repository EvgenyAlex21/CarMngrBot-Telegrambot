from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, timedelta
from core.bot_instance import bot
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from handlers.admin.system_management.system_management_main import manage_system
from handlers.admin.statistics.statistics import check_admin_access, escape_markdown
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

# --------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ (управление магазином) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Управление магазином' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def manage_store(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Управление магазином'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Начисление покупки', 'Просмотр покупок', 'Удаление покупок')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите действие для управления магазином:", reply_markup=markup)

# --------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ МАГАЗИНОМ (начисление покупки) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Начисление покупки' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def add_store_purchase(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Начисление покупки'):
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
    markup.add('Вернуться в управление магазином')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для начисления покупки:", reply_markup=markup)
    bot.register_next_step_handler(message, process_add_store_purchase)

@text_only_handler
def process_add_store_purchase(message):
    if message.text == "Вернуться в управление магазином":
        manage_store(message)
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
        bot.register_next_step_handler(message, process_add_store_purchase)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Баллы', 'Дни подписки')
    markup.add('Вернуться в управление магазином')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите тип покупки для начисления:", reply_markup=markup)
    bot.register_next_step_handler(message, process_add_store_purchase_type, user_id)

@text_only_handler
def process_add_store_purchase_type(message, user_id):
    if message.text == "Вернуться в управление магазином":
        manage_store(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    purchase_type = message.text.strip()
    if purchase_type not in ['Баллы', 'Дни подписки']:
        bot.send_message(message.chat.id, "Неверный тип покупки!\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_add_store_purchase_type, user_id)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if purchase_type == 'Баллы':
        prompt = "Введите количество баллов для начисления:"
        markup.add('Вернуться в управление магазином')
        markup.add('Вернуться в управление системой')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, prompt, reply_markup=markup)
        bot.register_next_step_handler(message, process_add_store_purchase_amount, user_id, purchase_type, 'days')
    else:
        markup.add('В минутах', 'В часах', 'В днях')
        markup.add('Вернуться в управление магазином')
        markup.add('Вернуться в управление системой')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Выберите единицу измерения времени:", reply_markup=markup)
        bot.register_next_step_handler(message, process_add_store_purchase_unit, user_id)

@text_only_handler
def process_add_store_purchase_unit(message, user_id):
    if message.text == "Вернуться в управление магазином":
        manage_store(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    unit = message.text.strip()
    if unit not in ['В минутах', 'В часах', 'В днях']:
        bot.send_message(message.chat.id, "Неверная единица измерения!\nПожалуйста, выберите снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_add_store_purchase_unit, user_id)
        return

    unit_map = {
        'В минутах': 'minutes',
        'В часах': 'hours',
        'В днях': 'days'
    }
    unit_key = unit_map[unit]
    prompt = f"Введите количество {unit.lower()} для начисления:"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Вернуться в управление магазином')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, prompt, reply_markup=markup)
    bot.register_next_step_handler(message, process_add_store_purchase_amount, user_id, 'Дни подписки', unit_key)

@text_only_handler
def process_add_store_purchase_amount(message, user_id, purchase_type, unit='days'):
    if message.text == "Вернуться в управление магазином":
        manage_store(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        input_text = message.text.strip().replace(',', '.')
        input_amount = float(input_text)
        if input_amount <= 0:
            raise ValueError("Количество должно быть положительным!")

        display_amount = f"{int(input_amount)}" if float(input_amount).is_integer() else f"{input_amount:.2f}"

        amount = input_amount
        if purchase_type == 'Дни подписки':
            if unit == 'minutes':
                amount = input_amount / (24 * 60)  
            elif unit == 'hours':
                amount = input_amount / 24  

        unit_display = {
            'minutes': 'минут',
            'hours': 'часов',
            'days': 'дней'
        }.get(unit, 'дней')

        data = load_payment_data()
        user_data = data['subscriptions']['users'].setdefault(str(user_id), {
            'plans': [], 'total_amount': 0, 'referral_points': 0, 'store_purchases': []
        })

        if 'store_purchases' not in user_data:
            user_data['store_purchases'] = []

        users_data = load_users()
        username = escape_markdown(users_data.get(str(user_id), {}).get('username', f"@{user_id}"))
        purchase_date = datetime.now().strftime("%d.%m.%Y в %H:%M")
        monthly_key = datetime.now().strftime("%m.%Y")

        monthly_points = sum(p['points'] for p in user_data['store_purchases'] if p['purchase_date'].startswith(monthly_key))
        monthly_days = sum(p['duration'] for p in user_data['store_purchases'] if p['purchase_date'].startswith(monthly_key))

        if purchase_type == 'Баллы':
            if monthly_points + amount > 3000:
                bot.send_message(message.chat.id, (
                    "⚠️ Пользователь превысит месячный лимит покупки баллов в размере 3000!\nПопробуйте меньшее количество..."
                ), parse_mode="Markdown")
                bot.register_next_step_handler(message, process_add_store_purchase_amount, user_id, purchase_type, unit)
                return

            user_data['referral_points'] += amount
            user_data.setdefault('points_history', []).append({
                'action': 'earned',
                'points': amount,
                'reason': 'Начисление от администратора',
                'date': purchase_date,
                'source': 'admin_purchase'
            })

            user_data['store_purchases'].append({
                "item_key": "admin_points",
                "label": f"{display_amount} баллов",
                "points": amount,
                "duration": 0,
                "price": 0,
                "purchase_date": purchase_date,
                "telegram_payment_charge_id": None,
                "provider_payment_charge_id": None,
                "source": "admin",
                "user_discount": 0,
                "fictitious_discount": 0
            })

            admin_message = f"✅ Пользователю {username} - `{user_id}` начислено *{display_amount} баллов* из магазина!"
            user_message = f"✅ Администратор начислил вам *{display_amount} баллов* из магазина!"

        else:
            if monthly_days + amount > 365:
                bot.send_message(message.chat.id, (
                    "⚠️ Пользователь превысит месячный лимит покупки времени в размере 365 дней!\nПопробуйте меньшее количество..."
                ), parse_mode="Markdown")
                bot.register_next_step_handler(message, process_add_store_purchase_amount, user_id, purchase_type, unit)
                return

            latest_end = max([datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") for p in user_data['plans']] or [datetime.now()])
            new_end = latest_end + timedelta(days=amount)

            plan_name_rus = "подписка из магазина"

            user_data['plans'].append({
                'plan_name': 'store_time',
                'start_date': latest_end.strftime("%d.%m.%Y в %H:%M"),
                'end_date': new_end.strftime("%d.%m.%Y в %H:%M"),
                'price': 0,
                'telegram_payment_charge_id': None,
                'provider_payment_charge_id': None,
                'source': 'admin',
                'user_discount': 0,
                'fictitious_discount': 0
            })

            user_data['store_purchases'].append({
                "item_key": "admin_time",
                "label": f"{display_amount} {unit_display} подписки",
                "points": 0,
                "duration": amount,
                "price": 0,
                "purchase_date": purchase_date,
                "telegram_payment_charge_id": None,
                "provider_payment_charge_id": None,
                "source": "admin",
                "user_discount": 0,
                "fictitious_discount": 0
            })

            admin_message = (
                f"✅ Пользователю {username} - `{user_id}` назначено:\n\n"
                f"💼 *План подписки:* {plan_name_rus}\n"
                f"🕒 *Начало:* {latest_end.strftime('%d.%m.%Y в %H:%M')}\n"
                f"⌛ *Конец:* {new_end.strftime('%d.%m.%Y в %H:%M')}"
            )
            user_message = (
                f"✅ Администратор назначил вам:\n\n"
                f"💼 *План подписки:* {plan_name_rus}\n"
                f"🕒 *Начало:* {latest_end.strftime('%d.%m.%Y в %H:%M')}\n"
                f"⌛ *Конец:* {new_end.strftime('%d.%m.%Y в %H:%M')}\n\n"
            )

        save_payments_data(data)
        bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
        bot.send_message(user_id, user_message, parse_mode="Markdown")
        manage_store(message)

    except ValueError as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_add_store_purchase_amount, user_id, purchase_type, unit)
    except Exception as e:
        bot.send_message(message.chat.id, f"{str(e)}\nОбратитесь в поддержку", parse_mode="Markdown")
        manage_store(message)

# --------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ МАГАЗИНОМ (просмотр покупок) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Просмотр покупок' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_store_purchases(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Просмотр покупок'):
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
    markup.add('Вернуться в управление магазином')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для просмотра покупок:", reply_markup=markup)
    bot.register_next_step_handler(message, process_view_store_purchases)

@text_only_handler
def process_view_store_purchases(message):
    if message.text == "Вернуться в управление магазином":
        manage_store(message)
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
        bot.register_next_step_handler(message, process_view_store_purchases)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})
    store_purchases = user_data.get('store_purchases', [])
    plans = user_data.get('plans', [])

    if not store_purchases:
        bot.send_message(message.chat.id, "❌ У пользователя нет покупок в магазине!", parse_mode="Markdown")
        manage_store(message)
        return

    purchases_summary = "💎 *Список покупок в магазине:*\n\n"
    for idx, purchase in enumerate(store_purchases, start=1):
        points = purchase.get('points', 0)
        days = purchase.get('duration', 0)
        price = purchase.get('price', 0)
        purchase_date = purchase.get('purchase_date', 'Неизвестно')
        label = purchase.get('label', 'Неизвестно')
        source = purchase.get('source', 'user')

        purchase_type = "баллов" if points > 0 else "времени"
        time_unit = "дней подписки"
        display_duration = f"{days:.2f}"
        if "минут" in label.lower():
            time_unit = "минут подписки"
            display_duration = f"{days * 24 * 60:.2f}"
        elif "часов" in label.lower():
            time_unit = "часов подписки"
            display_duration = f"{days * 24:.2f}"
        else:
            time_unit = "дней подписки"
            display_duration = f"{days:.2f}"

        if points > 0:
            if isinstance(points, int):
                points_display = f"{points}"
            else:
                points_display = f"{int(float(points))}" if float(points).is_integer() else f"{float(points):.2f}"
        if days > 0:
            duration_value = float(display_duration)
            if duration_value.is_integer():
                display_duration = f"{int(duration_value)}"
            else:
                display_duration = f"{duration_value:.2f}"

        purchase_entry = f"📅 *№{idx}. Покупка {purchase_type}:*\n\n"
        purchase_entry += f"🕒 *Дата:* {purchase_date}\n"
        if points > 0:
            purchase_entry += f"💰 *Баллы:* {points_display}\n"
        if days > 0:
            purchase_entry += f"📆 *{time_unit.capitalize()}:* {display_duration}\n"
        purchase_entry += f"💸 *Стоимость:* {price:.2f} руб.\n"
        purchase_entry += f"🔗 *Источник:* {'администратор' if source == 'admin' else 'пользователь'}\n\n"

        purchases_summary += purchase_entry

    message_parts = split_message(purchases_summary)
    for part in message_parts:
        bot.send_message(message.chat.id, part, parse_mode="Markdown")

    current_time = datetime.now()
    active_plans = [p for p in plans if datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") > current_time]
    
    purchase_types = [purchase['label'] for purchase in store_purchases]
    types_str = ", ".join(purchase_types) if purchase_types else "Нет покупок"

    total_points = sum(purchase['points'] for purchase in store_purchases)
    total_points_display = f"{int(total_points)}" if float(total_points).is_integer() else f"{total_points:.2f}"

    if active_plans:
        latest_end = max(datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") for p in active_plans)
        time_left = latest_end - current_time
        days_left = time_left.days
        hours_left = time_left.seconds // 3600
        minutes_left = (time_left.seconds % 3600) // 60
        time_left_str = f"{days_left} дней и {hours_left:02d}:{minutes_left:02d} часов" if days_left >= 0 else "0 дней и 00:00 часов"
    else:
        time_left_str = "0 дней и 00:00 часов"

    start_date = min((datetime.strptime(p['start_date'], "%d.%m.%Y в %H:%M") for p in active_plans), default=current_time) if active_plans else current_time
    end_date = latest_end if active_plans else current_time
    start_date_str = start_date.strftime("%d.%m.%Y в %H:%M")
    end_date_str = end_date.strftime("%d.%m.%Y в %H:%M")

    active_purchase_dates = {p['start_date'] for p in active_plans}.union({p['end_date'] for p in active_plans})
    active_cost = sum(purchase['price'] for purchase in store_purchases if purchase['purchase_date'] in active_purchase_dates or purchase['source'] == 'admin')
    total_cost = sum(purchase['price'] for purchase in store_purchases)
    active_cost_display = f"{int(active_cost)}" if float(active_cost).is_integer() else f"{active_cost:.2f}"
    total_cost_display = f"{int(total_cost)}" if float(total_cost).is_integer() else f"{total_cost:.2f}"

    summary = (
        f"💎 *Итоговая оценка покупок:*\n\n"
        f"💼 *Типы покупок:* {types_str}\n"
        f"💰 *Всего баллов:* {total_points_display}\n"
        f"📅 *Дней осталось:* {time_left_str}\n"
        f"🕒 *Начало:* {start_date_str}\n"
        f"⌛ *Конец:* {end_date_str}\n"
        f"💰 *Общая стоимость активных покупок:* {active_cost_display} руб.\n"
        f"💰 *Общая стоимость всех покупок:* {total_cost_display} руб.\n"
    )

    bot.send_message(message.chat.id, summary, parse_mode="Markdown")

    manage_store(message)

# --------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ МАГАЗИНОМ (удаление покупок) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Удаление покупок' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_store_purchase(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Удаление покупок'):
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
    markup.add('Вернуться в управление магазином')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для удаления покупки:", reply_markup=markup)
    bot.register_next_step_handler(message, process_delete_store_purchase)

@text_only_handler
def process_delete_store_purchase(message):
    if message.text == "Вернуться в управление магазином":
        manage_store(message)
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
        bot.register_next_step_handler(message, process_delete_store_purchase)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})
    store_purchases = user_data.get('store_purchases', [])
    plans = user_data.get('plans', [])

    if not store_purchases:
        bot.send_message(message.chat.id, "❌ У пользователя нет покупок для удаления!", parse_mode="Markdown")
        manage_store(message)
        return

    purchases_summary = "💎 *Список покупок в магазине:*\n\n"
    for idx, purchase in enumerate(store_purchases, start=1):
        points = purchase.get('points', 0)
        days = purchase.get('duration', 0)
        price = purchase.get('price', 0)
        purchase_date = purchase.get('purchase_date', 'Неизвестно')
        label = purchase.get('label', 'Неизвестно')
        source = purchase.get('source', 'user')

        purchase_type = "баллов" if points > 0 else "времени"
        time_unit = "дней подписки"
        display_duration = f"{days:.2f}"
        if "минут" in label.lower():
            time_unit = "минут подписки"
            display_duration = f"{days * 24 * 60:.2f}"
        elif "часов" in label.lower():
            time_unit = "часов подписки"
            display_duration = f"{days * 24:.2f}"
        else:
            time_unit = "дней подписки"
            display_duration = f"{days:.2f}"

        if points > 0:
            if isinstance(points, int):
                points_display = f"{points}"
            else:
                points_display = f"{int(float(points))}" if float(points).is_integer() else f"{float(points):.2f}"
        if days > 0:
            duration_value = float(display_duration)
            if duration_value.is_integer():
                display_duration = f"{int(duration_value)}"
            else:
                display_duration = f"{duration_value:.2f}"

        purchase_entry = f"📅 *№{idx}. Покупка {purchase_type}:*\n\n"
        purchase_entry += f"🕒 *Дата:* {purchase_date}\n"
        if points > 0:
            purchase_entry += f"💰 *Баллы:* {points_display}\n"
        if days > 0:
            purchase_entry += f"📆 *{time_unit.capitalize()}:* {display_duration}\n"
        purchase_entry += f"💸 *Стоимость:* {price:.2f} руб.\n"
        purchase_entry += f"🔗 *Источник:* {'администратор' if source == 'admin' else 'пользователь'}\n\n"

        purchases_summary += purchase_entry

    message_parts = split_message(purchases_summary)
    for part in message_parts:
        bot.send_message(message.chat.id, part, parse_mode="Markdown")

    current_time = datetime.now()
    active_plans = [p for p in plans if datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") > current_time]
    
    purchase_types = [purchase['label'] for purchase in store_purchases]
    types_str = ", ".join(purchase_types) if purchase_types else "Нет покупок"

    total_points = sum(purchase['points'] for purchase in store_purchases)
    total_points_display = f"{int(total_points)}" if float(total_points).is_integer() else f"{total_points:.2f}"

    if active_plans:
        latest_end = max(datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") for p in active_plans)
        time_left = latest_end - current_time
        days_left = time_left.days
        hours_left = time_left.seconds // 3600
        minutes_left = (time_left.seconds % 3600) // 60
        time_left_str = f"{days_left} дней и {hours_left:02d}:{minutes_left:02d} часов" if days_left >= 0 else "0 дней и 00:00 часов"
    else:
        time_left_str = "0 дней и 00:00 часов"

    start_date = min((datetime.strptime(p['start_date'], "%d.%m.%Y в %H:%M") for p in active_plans), default=current_time) if active_plans else current_time
    end_date = latest_end if active_plans else current_time
    start_date_str = start_date.strftime("%d.%m.%Y в %H:%M")
    end_date_str = end_date.strftime("%d.%m.%Y в %H:%M")

    active_purchase_dates = {p['start_date'] for p in active_plans}.union({p['end_date'] for p in active_plans})
    active_cost = sum(purchase['price'] for purchase in store_purchases if purchase['purchase_date'] in active_purchase_dates or purchase['source'] == 'admin')
    total_cost = sum(purchase['price'] for purchase in store_purchases)
    active_cost_display = f"{int(active_cost)}" if float(active_cost).is_integer() else f"{active_cost:.2f}"
    total_cost_display = f"{int(total_cost)}" if float(total_cost).is_integer() else f"{total_cost:.2f}"

    summary = (
        f"💎 *Итоговая оценка покупок:*\n\n"
        f"💼 *Типы покупок:* {types_str}\n"
        f"💰 *Всего баллов:* {total_points_display}\n"
        f"📅 *Дней осталось:* {time_left_str}\n"
        f"🕒 *Начало:* {start_date_str}\n"
        f"⌛ *Конец:* {end_date_str}\n"
        f"💰 *Общая стоимость активных покупок:* {active_cost_display} руб.\n"
        f"💰 *Общая стоимость всех покупок:* {total_cost_display} руб.\n"
    )

    bot.send_message(message.chat.id, summary, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Вернуться в управление магазином')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номера покупок для удаления:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_delete_store_purchase_select, user_id)

@text_only_handler
def process_delete_store_purchase_select(message, user_id):
    if message.text == "Вернуться в управление магазином":
        manage_store(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        purchase_numbers = [num.strip() for num in message.text.split(',')]
        valid_numbers = []
        invalid_numbers = []

        data = load_payment_data()
        user_data = data['subscriptions']['users'].get(str(user_id), {})
        store_purchases = user_data.get('store_purchases', [])
        for num in purchase_numbers:
            try:
                purchase_number = int(num)
                if 1 <= purchase_number <= len(store_purchases):
                    valid_numbers.append(purchase_number)
                else:
                    invalid_numbers.append(num)
            except ValueError:
                invalid_numbers.append(num)

        if not valid_numbers:
            bot.send_message(message.chat.id, "❌ Все введенные номера некорректны! Пожалуйста, попробуйте снова", parse_mode="Markdown")
            bot.register_next_step_handler(message, process_delete_store_purchase_select, user_id)
            return

        if invalid_numbers:
            invalid_str = ", ".join(invalid_numbers)
            bot.send_message(message.chat.id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode="Markdown")

        valid_numbers.sort(reverse=True)
        users_data = load_users()
        username = escape_markdown(users_data.get(str(user_id), {}).get('username', f"@{user_id}"))

        for purchase_number in valid_numbers:
            purchase = store_purchases[purchase_number - 1]
            points = purchase.get('points', 0)
            days = purchase.get('duration', 0)
            price = purchase.get('price', 0)
            purchase_date = purchase.get('purchase_date', 'Неизвестно')
            label = purchase.get('label', 'Неизвестно')
            source = purchase.get('source', 'user')

            purchase_type = "баллы" if points > 0 else "время"
            time_unit = "дней подписки"
            display_duration = f"{days:.2f}"
            if "минут" in label.lower():
                time_unit = "минут подписки"
                display_duration = f"{days * 24 * 60:.2f}"
            elif "часов" in label.lower():
                time_unit = "часов подписки"
                display_duration = f"{days * 24:.2f}"
            else:
                time_unit = "дней подписки"
                display_duration = f"{days:.2f}"

            if points > 0:
                points_f = float(points)
                points_display = f"{int(points_f)}" if points_f.is_integer() else f"{points_f:.2f}"
            if days > 0:
                duration_value = float(display_duration)
                if duration_value.is_integer():
                    display_duration = f"{int(duration_value)}"
                else:
                    display_duration = f"{duration_value:.2f}"

            if points > 0:
                user_data['referral_points'] = max(0, user_data.get('referral_points', 0) - points)
                user_data.setdefault('points_history', []).append({
                    'action': 'spent',
                    'points': points,
                    'reason': 'удаление покупок администратором',
                    'date': datetime.now().strftime("%d.%m.%Y в %H:%M"),
                    'source': 'admin_delete'
                })

            if days > 0:
                for plan in user_data['plans'][:]:
                    if plan.get('source') == source and plan.get('plan_name') == 'store_time':
                        if source == 'admin' and plan.get('start_date') == purchase_date:
                            user_data['plans'].remove(plan)
                            break
                        elif source != 'admin' and plan.get('telegram_payment_charge_id') == purchase.get('telegram_payment_charge_id'):
                            user_data['plans'].remove(plan)
                            break

            user_data['total_amount'] = max(0, user_data.get('total_amount', 0) - price)
            data['all_users_total_amount'] = max(0, data.get('all_users_total_amount', 0) - price)

            store_purchases.pop(purchase_number - 1)

            admin_message = f"🚫 Удалена покупка пользователя {username} - `{user_id}`:\n\n"
            admin_message += f"💳 *Тип покупки:* {purchase_type}\n"
            admin_message += f"📅 *Время покупки:* {purchase_date}\n"
            if points > 0:
                admin_message += f"💰 *Баллы:* {points_display}\n"
            if days > 0:
                admin_message += f"📆 *{time_unit.capitalize()}:* {display_duration}\n"
            admin_message += f"💸 *Стоимость:* {price:.2f} руб.\n"

            user_message = "🚫 Администратор удалил вашу покупку:\n\n"
            user_message += f"💳 *Тип покупки:* {purchase_type}\n"
            user_message += f"📅 *Время покупки:* {purchase_date}\n"
            if points > 0:
                user_message += f"💰 *Баллы:* {points_display}\n"
            if days > 0:
                user_message += f"📆 *{time_unit.capitalize()}:* {display_duration}\n"
            user_message += f"💸 *Стоимость:* {price:.2f} руб.\n"

            bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
            bot.send_message(user_id, user_message, parse_mode="Markdown")

        user_data['store_purchases'] = store_purchases
        save_payments_data(data)
        manage_store(message)

    except Exception as e:
        bot.send_message(message.chat.id, f"{str(e)}\nОбратитесь в поддержку", parse_mode="Markdown")
        manage_store(message)