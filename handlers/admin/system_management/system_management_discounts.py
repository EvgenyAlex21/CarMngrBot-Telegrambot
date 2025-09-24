from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, timedelta, uuid
from core.bot_instance import bot
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from handlers.admin.system_management.system_management_main import manage_system
from handlers.admin.statistics.statistics import check_admin_access, escape_markdown
from handlers.user.user_main_menu import load_payment_data, save_payments_data, load_users_data as load_users
from handlers.user.subscription.buy_subscription import SUBSCRIPTION_PLANS, STORE_ITEMS
from handlers.user.subscription.gifts import split_message
from handlers.admin.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

# ------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ (управление скидками) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Управление скидками' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def manage_discounts(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Управление скидками'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Создать промокод','Назначить скидку') 
    markup.add('Просмотр промокодов', 'Удаление промокодов')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите действие для управления скидками:", reply_markup=markup)

# ------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ СКИДКАМИ (создать промокод) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Создать промокод' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def create_promo_code(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Создать промокод'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в управление скидками')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите процент скидки для нового промокода:", reply_markup=markup)
    bot.register_next_step_handler(message, process_create_promo_code_discount)

@text_only_handler
def process_create_promo_code_discount(message):
    if message.text in ["Вернуться в управление скидками", "Вернуться в управление системой", "В меню админ-панели"]:
        if message.text == "Вернуться в управление скидками":
            manage_discounts(message)
        elif message.text == "Вернуться в управление системой":
            manage_system(message)
        else:
            show_admin_panel(message)
        return

    try:
        discount = float(message.text.replace(',', '.').strip())
        if discount <= 0 or discount > 100:
            raise ValueError("Процент скидки должен быть от 1 до 100!")

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в управление скидками')
        markup.add('Вернуться в управление системой')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Введите количество пользователей, которые могут использовать промокод:", reply_markup=markup)
        bot.register_next_step_handler(message, process_create_promo_code_uses, discount)
    except ValueError as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_create_promo_code_discount)

@text_only_handler
def process_create_promo_code_uses(message, discount):
    if message.text in ["Вернуться в управление скидками", "Вернуться в управление системой", "В меню админ-панели"]:
        if message.text == "Вернуться в управление скидками":
            manage_discounts(message)
        elif message.text == "Вернуться в управление системой":
            manage_system(message)
        else:
            show_admin_panel(message)
        return

    try:
        uses = int(message.text.strip())
        if uses < 1:
            raise ValueError("Количество пользователей должно быть >1!")

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Все товары', 'Все подписки', 'Весь магазин')
        markup.add('Конкретные товары')
        markup.add('Вернуться в управление скидками')
        markup.add('Вернуться в управление системой')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, 
            "Выберите, к чему применим промокод:\n\n"
            "💳 - Все товары: подписки и магазин\n"
            "🎁 - Все подписки: только подписки\n"
            "🛒 - Весь магазин: только товары магазина\n"
            "🏷️ - Конкретные товары: выберите отдельные товары/подписки", 
            reply_markup=markup)
        bot.register_next_step_handler(message, process_create_promo_code_category, discount, uses)
    except ValueError as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_create_promo_code_uses, discount)

@text_only_handler
def process_create_promo_code_category(message, discount, uses):
    if message.text in ["Вернуться в управление скидками", "Вернуться в управление системой", "В меню админ-панели"]:
        if message.text == "Вернуться в управление скидками":
            manage_discounts(message)
        elif message.text == "Вернуться в управление системой":
            manage_system(message)
        else:
            show_admin_panel(message)
        return

    applicable_category = None
    applicable_items = []

    if message.text == "Все товары":
        applicable_category = None
    elif message.text == "Все подписки":
        applicable_category = "subscriptions"
    elif message.text == "Весь магазин":
        applicable_category = "store"
    elif message.text == "Конкретные товары":
        available_items = list(SUBSCRIPTION_PLANS.keys()) + list(STORE_ITEMS.keys())
        items_display_lines = []
        
        for idx, item in enumerate(available_items, 1):
            label = SUBSCRIPTION_PLANS.get(item, STORE_ITEMS.get(item, {'label': item}))['label']
            emoji = "💳" if item in SUBSCRIPTION_PLANS else "🛒"
            items_display_lines.append(f"{emoji} №{idx}. {label}")

        items_display = "💎 Список подписок и товаров:\n\n" + "\n".join(items_display_lines) + "\n\nВведите номера товаров и подписок:"
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в управление скидками')
        markup.add('Вернуться в управление системой')
        markup.add('В меню админ-панели')
        
        bot.send_message(message.chat.id, items_display, reply_markup=markup)
        bot.register_next_step_handler(message, process_create_promo_code_items, discount, uses)
        return
    else:
        bot.send_message(message.chat.id, "Некорректный выбор!\nПожалуйста, выберите одну из предложенных опций", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_create_promo_code_category, discount, uses)
        return

    data = load_payment_data()
    promo_code = f"PROMO{uuid.uuid4().hex[:8].upper()}"
    data.setdefault('promo_codes', {})[promo_code] = {
        'discount': discount,
        'uses': uses,
        'used': False,
        'active': True,
        'user_id': None,
        'used_by': [],
        'created_at': datetime.now().strftime("%d.%m.%Y в %H:%M"),
        'source': 'admin',
        'applicable_category': applicable_category,
        'applicable_items': applicable_items
    }

    save_payments_data(data)
    discount_str = f"{int(discount)}%" if isinstance(discount, int) or float(discount).is_integer() else f"{float(discount):.2f}%".replace(".00%", "%")
    applicability_str = ("все товары" if applicable_category is None else 
                        "все подписки" if applicable_category == "subscriptions" else 
                        "весь магазин")
    bot.send_message(message.chat.id, 
        f"✅ Создан промокод:\n\n"
        f"🎁 *Промокод:* `{promo_code}`\n"
        f"🏷️ *Процент скидки:* {discount_str}\n"
        f"👥 *Пользователи:* {uses}\n"
        f"🛒 *Применим к:* {applicability_str}", 
        parse_mode="Markdown")
    manage_discounts(message)

@text_only_handler
def process_create_promo_code_items(message, discount, uses):
    if message.text in ["Вернуться в управление скидками", "Вернуться в управление системой", "В меню админ-панели"]:
        if message.text == "Вернуться в управление скидками":
            manage_discounts(message)
        elif message.text == "Вернуться в управление системой":
            manage_system(message)
        else:
            show_admin_panel(message)
        return

    available_items = [
        "trial_subscription_3", "weekly_subscription_7", "monthly_subscription_30",
        "quarterly_subscription_90", "semiannual_subscription_180", "yearly_subscription_365",
        "points_5", "points_10", "points_15", "points_25", "points_30", "points_50",
        "points_75", "points_100", "points_150", "points_200", "points_250", "points_350",
        "points_500", "points_750", "points_1000",
        "time_1day", "time_2days", "time_4days", "time_5days", "time_8days", "time_10days",
        "time_14days", "time_15days", "time_21days", "time_45days", "time_60days", "time_120days"
    ]    
    applicable_items = []

    try:
        indices = [int(idx.strip()) - 1 for idx in message.text.split(',')]
        for idx in indices:
            if 0 <= idx < len(available_items):
                applicable_items.append(available_items[idx])
            else:
                raise ValueError(f"Некорректный номер товара: {idx + 1}")
    except ValueError as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_create_promo_code_items, discount, uses)
        return

    data = load_payment_data()
    promo_code = f"PROMO{uuid.uuid4().hex[:8].upper()}"
    data.setdefault('promo_codes', {})[promo_code] = {
        'discount': discount,
        'uses': uses,
        'used': False,
        'active': True,
        'user_id': None,
        'used_by': [],
        'created_at': datetime.now().strftime("%d.%m.%Y в %H:%M"),
        'source': 'admin',
        'applicable_category': None,
        'applicable_items': applicable_items
    }

    save_payments_data(data)
    discount_str = f"{int(discount)}%" if isinstance(discount, int) or float(discount).is_integer() else f"{float(discount):.2f}%".replace(".00%", "%")
    items_str = ", ".join([SUBSCRIPTION_PLANS.get(item, STORE_ITEMS.get(item, {'label': item}))['label'] + (" в магазине" if item.startswith("points_") or item.startswith("time_") else "") for item in applicable_items])
    bot.send_message(message.chat.id, 
        f"✅ Создан промокод:\n\n"
        f"🎁 *Промокод:* `{promo_code}`\n"
        f"🏷️ *Процент скидки:* {discount_str}\n"
        f"👥 *Пользователи:* {uses}\n"
        f"🛒 *Применим к:* {items_str}", 
        parse_mode="Markdown")
    manage_discounts(message)

# ------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ СКИДКАМИ (назначить скидку) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Назначить скидку' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def assign_discount(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Назначить скидку'):
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
    markup.add('Вернуться в управление скидками')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер, id или username пользователя для назначения скидки:", reply_markup=markup)
    bot.register_next_step_handler(message, process_assign_discount)

@text_only_handler
def process_assign_discount(message):
    if message.text == "Вернуться в управление скидками":
        manage_discounts(message)
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
        bot.register_next_step_handler(message, process_assign_discount)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в управление скидками')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите процент скидки:", reply_markup=markup)
    bot.register_next_step_handler(message, process_assign_discount_amount, user_id)

@text_only_handler
def process_assign_discount_amount(message, user_id):
    if message.text in ["Вернуться в управление скидками", "Вернуться в управление системой", "В меню админ-панели"]:
        if message.text == "Вернуться в управление скидками":
            manage_discounts(message)
        elif message.text == "Вернуться в управление системой":
            manage_system(message)
        else:
            show_admin_panel(message)
        return

    try:
        discount = float(message.text.replace(',', '.').strip())
        if discount <= 0 or discount > 100:
            raise ValueError("Процент скидки должен быть от 1 до 100!")

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Все товары', 'Все подписки', 'Весь магазин')
        markup.add('Конкретные товары')
        markup.add('Вернуться в управление скидками')
        markup.add('Вернуться в управление системой')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, 
            "Выберите, к чему применима скидка:\n\n"
            "💳 - Все товары: подписки и магазин\n"
            "🎁 - Все подписки: только подписки\n"
            "🛒 - Весь магазин: только товары магазина\n"
            "🏷️ - Конкретные товары: выберите отдельные товары/подписки", 
            reply_markup=markup)
        bot.register_next_step_handler(message, process_assign_discount_category, user_id, discount)
    except ValueError as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_assign_discount_amount, user_id)

@text_only_handler
def process_assign_discount_category(message, user_id, discount):
    if message.text in ["Вернуться в управление скидками", "Вернуться в управление системой", "В меню админ-панели"]:
        if message.text == "Вернуться в управление скидками":
            manage_discounts(message)
        elif message.text == "Вернуться в управление системой":
            manage_system(message)
        else:
            show_admin_panel(message)
        return

    applicable_category = None
    applicable_items = []

    if message.text == "Все товары":
        applicable_category = None
    elif message.text == "Все подписки":
        applicable_category = "subscriptions"
    elif message.text == "Весь магазин":
        applicable_category = "store"
    elif message.text == "Конкретные товары":
        available_items = list(SUBSCRIPTION_PLANS.keys()) + list(STORE_ITEMS.keys())
        items_display_lines = []
        for idx, item in enumerate(available_items, 1):
            label = SUBSCRIPTION_PLANS.get(item, STORE_ITEMS.get(item, {'label': item}))['label']
            if item in SUBSCRIPTION_PLANS:
                emoji = "💳"  
            else:
                emoji = "🛒"  
            items_display_lines.append(f"{emoji} №{idx}. {label}")
        
        items_display = "💎 Список подписок и товаров:\n\n" + "\n".join(items_display_lines) + "\n\nВведите номера товаров и подписок:"
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в управление скидками')
        markup.add('Вернуться в управление системой')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, items_display, reply_markup=markup)
        bot.register_next_step_handler(message, process_assign_discount_items, user_id, discount)
        return
    else:
        bot.send_message(message.chat.id, "Некорректный выбор! Пожалуйста, выберите одну из предложенных опций.", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_assign_discount_category, user_id, discount)
        return

    data = load_payment_data()
    users_data = load_users()
    username = escape_markdown(users_data.get(str(user_id), {}).get('username', f"@{user_id}"))
    if not username.startswith('@'):
        username = f"@{username}"

    now = datetime.now()
    for code, promo in list(data.get('promo_codes', {}).items()):
        created_at_str = promo.get('created_at', now.strftime("%d.%m.%Y в %H:%M"))
        created_at = datetime.strptime(created_at_str, "%d.%m.%Y в %H:%M")
        if (now - created_at).days > 30 and not promo.get('used', False):
            promo['used'] = True
            promo['active'] = False
            promo['deactivated_at'] = now.strftime("%d.%m.%Y в %H:%M")
            promo['deactivation_reason'] = "истёк срок действия"

    promo_code = f"DISC{uuid.uuid4().hex[:8].upper()}"
    data.setdefault('promo_codes', {})[promo_code] = {
        'discount': discount,
        'uses': 1,
        'used': False,
        'active': True,
        'user_id': str(user_id),
        'used_by': [],
        'created_at': now.strftime("%d.%m.%Y в %H:%M"),
        'source': 'admin',
        'applicable_category': applicable_category,
        'applicable_items': applicable_items
    }

    save_payments_data(data)
    discount_str = f"{int(discount)}%" if isinstance(discount, int) or float(discount).is_integer() else f"{float(discount):.2f}%".replace(".00%", "%")
    applicability_str = ("все товары" if applicable_category is None else 
                        "все подписки" if applicable_category == "subscriptions" else 
                        "весь магазин")
    admin_message = (
        f"✅ Пользователю {username} - `{user_id}` назначена скидка:\n\n"
        f"🎁 *Промокод:* `{promo_code}`\n"
        f"🏷️ *Процент скидки:* {discount_str}\n"
        f"🛒 *Применим к:* {applicability_str}\n"
        f"⏳ Срок действия: 30 дней"
    )
    user_message = (
        f"✅ Администратор назначил вам скидку:\n\n"
        f"🎁 *Промокод:* `{promo_code}`\n"
        f"🏷️ *Процент скидки:* {discount_str}\n"
        f"🛒 *Применим к:* {applicability_str}\n"
        f"⏳ Срок действия: 30 дней\n\n"
        f"_P.S. скидка сгорит, если не использовать при покупке!_"
    )
    bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
    bot.send_message(user_id, user_message, parse_mode="Markdown")

    manage_discounts(message)

@text_only_handler
def process_assign_discount_items(message, user_id, discount):
    if message.text in ["Вернуться в управление скидками", "Вернуться в управление системой", "В меню админ-панели"]:
        if message.text == "Вернуться в управление скидками":
            manage_discounts(message)
        elif message.text == "Вернуться в управление системой":
            manage_system(message)
        else:
            show_admin_panel(message)
        return

    available_items = [
        "trial_subscription_3", "weekly_subscription_7", "monthly_subscription_30",
        "quarterly_subscription_90", "semiannual_subscription_180", "yearly_subscription_365",
        "points_5", "points_10", "points_15", "points_25", "points_30", "points_50",
        "points_75", "points_100", "points_150", "points_200", "points_250", "points_350",
        "points_500", "points_750", "points_1000",
        "time_1day", "time_2days", "time_4days", "time_5days", "time_8days", "time_10days",
        "time_14days", "time_15days", "time_21days", "time_45days", "time_60days", "time_120days"
    ]  
    applicable_items = []

    try:
        indices = [int(idx.strip()) - 1 for idx in message.text.split(',')]
        for idx in indices:
            if 0 <= idx < len(available_items):
                applicable_items.append(available_items[idx])
            else:
                raise ValueError(f"Некорректный номер товара: {idx + 1}")
    except ValueError as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_assign_discount_items, user_id, discount)
        return

    data = load_payment_data()
    users_data = load_users()
    username = escape_markdown(users_data.get(str(user_id), {}).get('username', f"@{user_id}"))
    if not username.startswith('@'):
        username = f"@{username}"

    now = datetime.now()
    for code, promo in list(data.get('promo_codes', {}).items()):
        created_at_str = promo.get('created_at', now.strftime("%d.%m.%Y в %H:%M"))
        created_at = datetime.strptime(created_at_str, "%d.%m.%Y в %H:%M")
        if (now - created_at).days > 30 and not promo.get('used', False):
            promo['used'] = True
            promo['active'] = False
            promo['deactivated_at'] = now.strftime("%d.%m.%Y в %H:%M")
            promo['deactivation_reason'] = "истёк срок действия"

    promo_code = f"DISC{uuid.uuid4().hex[:8].upper()}"
    data.setdefault('promo_codes', {})[promo_code] = {
        'discount': discount,
        'uses': 1,
        'used': False,
        'active': True,
        'user_id': str(user_id),
        'used_by': [],
        'created_at': now.strftime("%d.%m.%Y в %H:%M"),
        'source': 'admin',
        'applicable_category': None,
        'applicable_items': applicable_items
    }

    save_payments_data(data)
    discount_str = f"{int(discount)}%" if isinstance(discount, int) or float(discount).is_integer() else f"{float(discount):.2f}%".replace(".00%", "%")
    items_str = ", ".join([SUBSCRIPTION_PLANS.get(item, STORE_ITEMS.get(item, {'label': item}))['label'] + (" в магазине" if item.startswith("points_") or item.startswith("time_") else "") for item in applicable_items])
    admin_message = (
        f"✅ Пользователю {username} - `{user_id}` назначена скидка:\n\n"
        f"🎁 *Промокод:* `{promo_code}`\n"
        f"🏷️ *Процент скидки:* {discount_str}\n"
        f"🛒 *Применим к:* {items_str}\n"
        f"⏳ Срок действия: 30 дней"
    )
    user_message = (
        f"✅ Администратор назначил вам скидку:\n\n"
        f"🎁 *Промокод:* `{promo_code}`\n"
        f"🏷️ *Процент скидки:* {discount_str}\n"
        f"🛒 *Применим к:* {items_str}\n"
        f"⏳ Срок действия: 30 дней\n\n"
        f"_P.S. скидка сгорит, если не использовать при покупке!_"
    )
    bot.send_message(message.chat.id, admin_message, parse_mode="Markdown")
    bot.send_message(user_id, user_message, parse_mode="Markdown")

    manage_discounts(message)

# ------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ СКИДКАМИ (просмотр промокодов) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Просмотр промокодов' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_promo_codes(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Просмотр промокодов'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    data = load_payment_data()
    promo_codes = data.get('promo_codes', {})
    if not promo_codes:
        bot.send_message(message.chat.id, "❌ Промокоды отсутствуют!", parse_mode="Markdown")
        manage_discounts(message)
        return

    now = datetime.now()
    promo_summary = "*Список промокодов:*\n\n"
    for idx, (code, details) in enumerate(promo_codes.items(), 1):
        used = details.get('used', False)
        active = details.get('active', not used)
        status = "использован" if used or not active else "активен"
        if not used and active:
            created_at_str = details.get('created_at', now.strftime("%d.%m.%Y в %H:%M"))
            created_at = datetime.strptime(created_at_str, "%d.%m.%Y в %H:%M")
            if (now - created_at).days > 30:
                status = "истёк"
                details['used'] = True
                details['active'] = False
                details['deactivated_at'] = now.strftime("%d.%m.%Y в %H:%M")
                details['deactivation_reason'] = "истёк срок действия (30 дней)"

        source = details.get('source', 'system')
        user_id = details.get('user_id')
        if user_id:
            user_display = f"`{escape_markdown(str(user_id))}`"
        elif source == 'admin':
            user_display = "админский"
        else:
            user_display = "общий"

        created_at_display = details.get('created_at', 'неизвестно')
        uses = details.get('uses', 'неограничено')
        discount = details['discount']
        if isinstance(discount, int):
            discount_str = f"{discount}%"
        else:
            discount_f = float(discount)
            discount_str = f"{int(discount_f)}%" if discount_f.is_integer() else f"{discount_f:.2f}%".replace(".00%", "%")

        applicable_category = details.get('applicable_category')
        applicable_items = details.get('applicable_items', [])
        applicability_str = ("все товары" if applicable_category is None and not applicable_items else 
                            "все подписки" if applicable_category == "subscriptions" else 
                            "весь магазин" if applicable_category == "store" else 
                            ", ".join([SUBSCRIPTION_PLANS.get(item, STORE_ITEMS.get(item, {'label': item}))['label'] + (" в магазине" if item.startswith("points_") or item.startswith("time_") else "") for item in applicable_items]))

        promo_summary += (
            f"🎁 *№{idx}.* `{escape_markdown(code)}`\n"
            f"🏷️ *Скидка:* {discount_str}\n"
            f"📅 *Создан:* {created_at_display}\n"
            f"👥 *Использований:* {uses}\n"
            f"👤 *Пользователь:* {user_display}\n"
            f"🛒 *Применим к:* {applicability_str}\n"
            f"📋 *Статус:* {status}\n"
        )
        if details.get('deactivated_at'):
            promo_summary += f"⏳ *Деактивирован:* {details['deactivated_at']} ({details['deactivation_reason'].lower()})\n"
        if details.get('used_by'):
            for used_entry in details['used_by']:
                username = escape_markdown(used_entry['username'])
                if not username.startswith('@'):
                    username = f"@{username}"
                promo_summary += f"👤 *Использован:* {username} (`{escape_markdown(str(used_entry['user_id']))}`) в {used_entry['used_at']}\n"
        promo_summary += "\n"

    message_parts = split_message(promo_summary)
    for part in message_parts:
        bot.send_message(message.chat.id, part, parse_mode="Markdown")

    save_payments_data(data)
    manage_discounts(message)

# ------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ_УПРАВЛЕНИЕ СКИДКАМИ (удаление промокодов) -------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Удаление промокодов' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_promo_code(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Удаление промокодов'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    data = load_payment_data()
    promo_codes = data.get('promo_codes', {})
    if not promo_codes:
        bot.send_message(message.chat.id, "❌ Промокоды отсутствуют!", parse_mode="Markdown")
        manage_discounts(message)
        return

    now = datetime.now()
    promo_summary = "*Список промокодов для удаления:*\n\n"
    promo_list = []
    idx = 0
    for code, details in promo_codes.items():
        source = details.get('source', 'system')
        if source not in ('admin', 'admin_exchange'):
            continue

        idx += 1
        used = details.get('used', False)
        active = details.get('active', not used)
        status = "использован" if used or not active else "активен"
        if not used and active:
            created_at_str = details.get('created_at', now.strftime("%d.%m.%Y в %H:%M"))
            created_at = datetime.strptime(created_at_str, "%d.%m.%Y в %H:%M")
            if (now - created_at).days > 30:
                status = "истёк"
                details['used'] = True
                details['active'] = False
                details['deactivated_at'] = now.strftime("%d.%m.%Y в %H:%M")
                details['deactivation_reason'] = "истёк срок действия"

        user_id = details.get('user_id')
        if user_id:
            user_display = f"`{escape_markdown(str(user_id))}`"
        elif source == 'admin':
            user_display = "админский"
        else:
            user_display = "общий"

        created_at_display = details.get('created_at', 'неизвестно')
        uses = details.get('uses', 'неограничено')
        discount = details['discount']
        discount_str = f"{int(discount)}%" if isinstance(discount, int) or float(discount).is_integer() else f"{float(discount):.2f}%".replace(".00%", "%")
        applicable_category = details.get('applicable_category')
        applicable_items = details.get('applicable_items', [])
        applicability_str = ("все товары" if applicable_category is None and not applicable_items else 
                    "все подписки" if applicable_category == "subscriptions" else 
                    "весь магазин" if applicable_category == "store" else 
                    ", ".join([SUBSCRIPTION_PLANS.get(item, STORE_ITEMS.get(item, {'label': item}))['label'] + (" в магазине" if item.startswith("points_") or item.startswith("time_") else "") for item in applicable_items]))

        promo_summary += (
            f"🎁 *№{idx}.* `{escape_markdown(code)}`\n"
            f"🏷️ *Скидка:* {discount_str}\n"
            f"📅 *Создан:* {created_at_display}\n"
            f"👥 *Использований:* {uses}\n"
            f"👤 *Пользователь:* {user_display}\n"
            f"🛒 *Применим к:* {applicability_str}\n"
            f"📋 *Статус:* {status}\n"
        )
        if details.get('deactivated_at'):
            promo_summary += f"⏳ *Деактивирован:* {details['deactivated_at']} ({details['deactivation_reason']})\n"
        if details.get('used_by'):
            for used_entry in details['used_by']:
                username = escape_markdown(used_entry['username'])
                if not username.startswith('@'):
                    username = f"@{username}"
                promo_summary += f"👤 *Использован:* {username} (`{escape_markdown(str(used_entry['user_id']))}`) в {used_entry['used_at']}\n"
        promo_summary += "\n"
        promo_list.append(code)

    if not promo_list:
        bot.send_message(message.chat.id, "❌ Нет промокодов, доступных для удаления!", parse_mode="Markdown")
        manage_discounts(message)
        return

    message_parts = split_message(promo_summary)
    for part in message_parts:
        bot.send_message(message.chat.id, part, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Вернуться в управление скидками')
    markup.add('Вернуться в управление системой')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номера промокодов для удаления:", reply_markup=markup)
    bot.register_next_step_handler(message, process_delete_promo_code, promo_list)

@text_only_handler
def process_delete_promo_code(message, promo_list):
    if message.text == "Вернуться в управление скидками":
        manage_discounts(message)
        return
    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return
    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    try:
        indices = message.text.strip().split(',')
        valid_indices = []
        invalid_indices = []
        deleted_codes = []

        for idx in indices:
            idx = idx.strip()
            try:
                index = int(idx) - 1
                if 0 <= index < len(promo_list):
                    valid_indices.append(index)
                else:
                    invalid_indices.append(idx)
            except ValueError:
                invalid_indices.append(idx)

        if invalid_indices:
            invalid_str = ", ".join(invalid_indices)
            bot.send_message(message.chat.id, f"❌ Некорректные номера: `{invalid_str}`! Они будут пропущены...", parse_mode="Markdown")

        if valid_indices:
            data = load_payment_data()
            for index in valid_indices:
                promo_code = promo_list[index]
                if promo_code in data['promo_codes']:
                    del data['promo_codes'][promo_code]
                    deleted_codes.append(promo_code)
            save_payments_data(data)

            if deleted_codes:
                deleted_str = ", ".join([f"`{escape_markdown(code)}`" for code in deleted_codes])
                bot.send_message(message.chat.id, f"🚫 Промокоды: {deleted_str} удалены!", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "❌ Ни один промокод не был удалён!", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ Не указаны корректные номера промокодов!", parse_mode="Markdown")

        manage_discounts(message)
    except Exception as e:
        bot.send_message(message.chat.id, f"{str(e)}\nПожалуйста, попробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_delete_promo_code, promo_list)