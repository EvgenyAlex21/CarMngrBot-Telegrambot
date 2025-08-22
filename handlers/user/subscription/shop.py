from core.imports import wraps, telebot, types, os, json, re, datetime, timedelta, pytz, requests, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from core.bot_instance import bot
from handlers.user.user_main_menu import load_payment_data, save_payments_data
from handlers.user.subscription.buy_subscription import STORE_ITEMS, SUBSCRIPTION_PLANS
from handlers.user.subscription.subscription_main import PAYMENT_PROVIDER_TOKEN
from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

def return_to_menu(message):
    from handlers.user.user_main_menu import return_to_menu as _f
    return _f(message)

# ------------------------------------------------ ПОДПИСКА НА БОТА (магазин) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "Магазин")
@check_function_state_decorator('Магазин')
@track_usage('Магазин')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_store_options(message):
    user_id = str(message.from_user.id)
    data = load_payment_data()
    user_discount = data['subscriptions']['users'].get(user_id, {}).get('discount', 0)
    applicable_category = data['subscriptions']['users'].get(user_id, {}).get('applicable_category')
    applicable_items = data['subscriptions']['users'].get(user_id, {}).get('applicable_items', [])

    discount_applicable_to_store = (
        applicable_category == "store" or
        any(item in STORE_ITEMS for item in applicable_items) or
        (applicable_category is None and not applicable_items)
    )

    display_discount = round(user_discount) if discount_applicable_to_store else 0
    applicability_str = ""
    if discount_applicable_to_store and user_discount > 0:
        if applicable_category == "subscriptions":
            applicability_str = " (применимо к: все подписки)"
        elif applicable_category == "store":
            applicability_str = " (применимо к: весь магазин)"
        elif applicable_category is None and not applicable_items:
            applicability_str = " (применимо к: все товары)"
        else:
            applicable_labels = []
            for item in applicable_items:
                if item in SUBSCRIPTION_PLANS:
                    label = SUBSCRIPTION_PLANS[item]['label'].lower()
                    applicable_labels.append(f"{label} в подписках")
                elif item in STORE_ITEMS:
                    label = STORE_ITEMS[item]['label']
                    applicable_labels.append(f"{label} в магазине")
                else:
                    applicable_labels.append(item)
            applicability_str = f" (применимо к: {', '.join(applicable_labels)})"
    discount_info_text = f"🎁 *Ваша скидка:* {display_discount:.0f}%{applicability_str}\n"

    fictitious_discount_text = ""
    has_fictitious_discount = False

    points_items = {k: v for k, v in STORE_ITEMS.items() if k.startswith("points_")}
    for item_key, item_info in points_items.items():
        fictitious_discount = item_info.get("fictitious_discount", 0)
        label = item_info["label"]
        if fictitious_discount > 0:
            fictitious_discount_text += f"🎁 *Акционная скидка* (применимо к: {label}): {fictitious_discount:.2f} ₽\n"
            has_fictitious_discount = True

    time_items = {k: v for k, v in STORE_ITEMS.items() if k.startswith("time_")}
    for item_key, item_info in time_items.items():
        fictitious_discount = item_info.get("fictitious_discount", 0)
        label = item_info["label"]
        if fictitious_discount > 0:
            fictitious_discount_text += f"🎁 *Акционная скидка* (применимо к: {label}): {fictitious_discount:.2f} ₽\n"
            has_fictitious_discount = True

    if not has_fictitious_discount:
        fictitious_discount_text = "🎁 *Акционная скидка:* 0.00 ₽\n"

    fictitious_discount_text += "\n"

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📍 Пакеты баллов", callback_data="show_points_0"))
    markup.add(InlineKeyboardButton("⏳ Пакеты времени", callback_data="show_time_0"))

    bot.send_message(user_id, (
        "🏪 *Магазин баллов и времени*\n\n"
        f"{discount_info_text}"
        f"{fictitious_discount_text}"
        "📍 *Пакеты баллов*:\n"
        "Покупайте баллы для обмена на время, скидки или подарки друзьям!\n"
        "⏳ *Пакеты времени*:\n"
        "Добавьте дни к вашей подписке для полного доступа к функциям!\n\n"
        "Выберите категорию:"
    ), reply_markup=markup, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в подписку')
    markup.add('В главное меню')
    bot.send_message(user_id, "Выберите категорию для просмотра:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_points_"))
def show_points_packages(call):
    user_id = str(call.from_user.id)
    data = load_payment_data()
    user_discount = data['subscriptions']['users'].get(user_id, {}).get('discount', 0)
    applicable_category = data['subscriptions']['users'].get(user_id, {}).get('applicable_category')
    applicable_items = data['subscriptions']['users'].get(user_id, {}).get('applicable_items', [])

    page = int(call.data.split("_")[-1]) if call.data != "show_points" else 0
    items_per_page = 6
    points_items = [k for k in STORE_ITEMS.keys() if k.startswith("points_")]
    total_pages = (len(points_items) + items_per_page - 1) // items_per_page

    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(points_items))
    current_items = points_items[start_idx:end_idx]

    markup = InlineKeyboardMarkup()
    for i in range(0, len(current_items), 2):
        row = []
        for key in current_items[i:i+2]:
            item = STORE_ITEMS[key]
            discount_applicable = (
                applicable_category == "store" or
                (applicable_category is None and not applicable_items) or
                key in applicable_items
            )
            MINIMUM_AMOUNT = 90
            discounted = item["base_price"] * (1 - (user_discount / 100 if discount_applicable else 0))
            price = max(MINIMUM_AMOUNT, max(1, round(discounted, 2)))
            button = InlineKeyboardButton(f"💰 {item['label']} ({price:.2f} ₽)", callback_data=key)
            row.append(button)
        markup.add(*row)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"show_points_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"show_points_{page+1}"))
    if nav_row:
        markup.add(*nav_row)

    markup.add(InlineKeyboardButton("🔙 Назад в магазин", callback_data="back_to_store"))

    bot.edit_message_text(
        chat_id=user_id,
        message_id=call.message.message_id,
        text=f"📍 *Пакеты баллов (страница {page+1}/{total_pages})*\n\nВыберите пакет баллов:",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_time_"))
def show_time_packages(call):
    user_id = str(call.from_user.id)
    data = load_payment_data()
    user_discount = data['subscriptions']['users'].get(user_id, {}).get('discount', 0)
    applicable_category = data['subscriptions']['users'].get(user_id, {}).get('applicable_category')
    applicable_items = data['subscriptions']['users'].get(user_id, {}).get('applicable_items', [])

    page = int(call.data.split("_")[-1]) if call.data != "show_time" else 0
    items_per_page = 6
    time_items = [k for k in STORE_ITEMS.keys() if k.startswith("time_")]
    total_pages = (len(time_items) + items_per_page - 1) // items_per_page

    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(time_items))
    current_items = time_items[start_idx:end_idx]

    markup = InlineKeyboardMarkup()
    for i in range(0, len(current_items), 2):
        row = []
        for key in current_items[i:i+2]:
            item = STORE_ITEMS[key]
            discount_applicable = (
                applicable_category == "store" or
                (applicable_category is None and not applicable_items) or
                key in applicable_items
            )
            MINIMUM_AMOUNT = 90
            discounted = item["base_price"] * (1 - (user_discount / 100 if discount_applicable else 0))
            price = max(MINIMUM_AMOUNT, max(1, round(discounted, 2)))
            button = InlineKeyboardButton(f"⏰ {item['label']} ({price:.2f} ₽)", callback_data=key)
            row.append(button)
        markup.add(*row)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"show_time_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"show_time_{page+1}"))
    if nav_row:
        markup.add(*nav_row)

    markup.add(InlineKeyboardButton("🔙 Назад в магазин", callback_data="back_to_store"))

    bot.edit_message_text(
        chat_id=user_id,
        message_id=call.message.message_id,
        text=f"⏳ *Пакеты времени (страница {page+1}/{total_pages})*\n\nВыберите пакет времени:",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_store")
def back_to_store(call):
    user_id = str(call.from_user.id)
    
    if call.from_user.is_bot:
        bot.answer_callback_query(call.id, "Боты не могут взаимодействовать с магазином!")
        return

    try:
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
    except Exception as e:
        pass

    fake_message = types.Message(
        message_id=call.message.message_id,
        chat=call.message.chat,
        from_user=call.from_user,
        date=call.message.date,
        content_type='text',
        options={},
        json_string={}
    )
    
    send_store_options(fake_message)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text == "Вернуться в магазин")
@check_function_state_decorator('Вернуться в магазин')
@track_usage('Вернуться в магазин')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_store(message):
    send_store_options(message)

@bot.callback_query_handler(func=lambda call: call.data in STORE_ITEMS)
def send_store_invoice(call):
    user_id = str(call.from_user.id)
    item_key = call.data
    item_info = STORE_ITEMS[item_key]
    base_price = item_info["base_price"]
    fictitious_discount = item_info["fictitious_discount"]
    label = item_info["label"]

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(user_id, {"plans": [], "store_purchases": []})
    user_discount = data['subscriptions']['users'].get(user_id, {}).get('discount', 0)
    applicable_category = data['subscriptions']['users'].get(user_id, {}).get('applicable_category')
    applicable_items = data['subscriptions']['users'].get(user_id, {}).get('applicable_items', [])

    discount_applicable = (
        applicable_category == "store" or
        item_key in applicable_items or
        (applicable_category is None and not applicable_items)
    )
    user_discount = user_discount if discount_applicable else 0

    if item_key.startswith("time_"):
        duration = item_info["duration"]
        monthly_key = datetime.now().strftime("%m.%Y")
        monthly_days = sum(
            p['duration'] for p in user_data.get('store_purchases', [])
            if p['purchase_date'].startswith(monthly_key) and p['item_key'].startswith("time_")
        )
        if monthly_days + duration > 365:
            bot.send_message(user_id, (
                "⚠️ Вы превысили месячный лимит покупки времени в размере 365 дней!\n"
                "Попробуйте снова в следующем месяце..."
            ), parse_mode="Markdown")
            bot.answer_callback_query(call.id)
            return

    user_discount_amount = round(base_price * (user_discount / 100), 2)
    discounted_price = base_price - user_discount_amount

    MINIMUM_AMOUNT = 90

    final_price = discounted_price - fictitious_discount
    if final_price < MINIMUM_AMOUNT:
        total_discount = base_price - MINIMUM_AMOUNT
        user_discount_amount = min(user_discount_amount, total_discount)
        user_discount_amount = round(user_discount_amount, 2)
        remaining_discount = total_discount - user_discount_amount
        fictitious_discount = min(fictitious_discount, remaining_discount)
        fictitious_discount = round(fictitious_discount, 2)
        final_price = MINIMUM_AMOUNT

    provider_token = PAYMENT_PROVIDER_TOKEN
    currency = "RUB"
    invoice_payload = item_key

    bot_functions = (
        "🚀 Покупайте баллы для обмена на время, скидки или подарки, "
        "или добавляйте время подписки для полного доступа к функциям!"
    )

    title = f"🏪 Покупка: {label}"
    description = (
        f"✨ {label} для вашего аккаунта!\n"
        f"💰 Базовая цена: {base_price:.2f} ₽\n"
    )
    prices = [types.LabeledPrice(label, int(base_price * 100))]

    if user_discount > 0 and user_discount_amount > 0:
        description += f"🏷️ Скидка {user_discount}%: -{user_discount_amount:.2f} ₽\n"
        user_discount_amount_kopecks = int(round(user_discount_amount * 100))
        prices.append(types.LabeledPrice(f"Скидка {user_discount}%", -user_discount_amount_kopecks))

    if fictitious_discount > 0:
        description += f"🎁 Акционная скидка: -{fictitious_discount:.2f} ₽\n"
        fictitious_discount_kopecks = int(round(fictitious_discount * 100))
        prices.append(types.LabeledPrice("Акционная скидка", -fictitious_discount_kopecks))

    if item_key.startswith("time_"):
        now = datetime.now()
        if user_data['plans']:
            latest_end = max([datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") for p in user_data['plans']])
            start_date = max(latest_end, now)  
        else:
            start_date = now
        description += f"🕒 Начало подписки: {start_date.strftime('%d.%m.%Y в %H:%M')}\n"

    description += f"💸 Итог: {final_price:.2f} ₽\n\n{bot_functions}"

    total_amount = sum(price.amount for price in prices)
    if total_amount < MINIMUM_AMOUNT * 100:
        prices = [types.LabeledPrice(label, int(MINIMUM_AMOUNT * 100))]
        description += f"\n⚠️ Цена скорректирована до минимальной ({MINIMUM_AMOUNT} ₽) из-за требований платежной системы!\n"

    save_payments_data(data)

    try:
        bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            invoice_payload=invoice_payload,
            provider_token=provider_token,
            currency=currency,
            prices=prices,
            start_parameter="store"
        )
    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка при создании платежа!\nПопробуйте позже или обратитесь в поддержку...")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в подписку')
    markup.add('В главное меню')
    bot.send_message(user_id, "Выберите товар для покупки:", reply_markup=markup)
    bot.answer_callback_query(call.id, "Счёт отправлен!")