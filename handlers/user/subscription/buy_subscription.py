from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, timedelta, InlineKeyboardMarkup, InlineKeyboardButton
from core.bot_instance import bot, BASE_DIR
from handlers.user.subscription.subscription_main import payments_function, PAYMENT_PROVIDER_TOKEN
from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage
)

def return_to_menu(message):
    from handlers.user.user_main_menu import return_to_menu as _f
    return _f(message)

def create_main_menu():
    from handlers.user.user_main_menu import create_main_menu as _f
    return _f()

def load_payment_data():
    from handlers.user.user_main_menu import load_payment_data as _f
    return _f()

def save_payments_data(data):
    from handlers.user.user_main_menu import save_payments_data as _f
    return _f(data)

def set_free_trial_period(user_id, days, source="default"):
    from handlers.user.user_main_menu import set_free_trial_period as _f
    return _f(user_id, days, source)

# ------------------------------------------------ ПОДПИСКА НА БОТА (купить подписку) -----------------------------------------

SUBSCRIPTION_PLANS = {}
STORE_ITEMS = {}
SUBS_FILE_MTIME = 0

def load_subscriptions_and_store():
    global SUBSCRIPTION_PLANS, STORE_ITEMS, SUBS_FILE_MTIME
    json_dir = os.path.join(BASE_DIR, 'files', 'files_for_bot')
    json_path = os.path.join(json_dir, 'subscription_and_store.json')
    
    os.makedirs(json_dir, exist_ok=True)
    
    if not os.path.exists(json_path):
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({"subscription_plans": {}, "store_items": {}}, f, ensure_ascii=False, indent=4)
        SUBS_FILE_MTIME = os.path.getmtime(json_path)
        SUBSCRIPTION_PLANS = {}
        STORE_ITEMS = {}
        return SUBSCRIPTION_PLANS, STORE_ITEMS
    
    try:
        current_mtime = os.path.getmtime(json_path)
        if current_mtime != SUBS_FILE_MTIME:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                SUBS_FILE_MTIME = current_mtime
                SUBSCRIPTION_PLANS = data.get('subscription_plans', {})
                STORE_ITEMS = data.get('store_items', {})
        return SUBSCRIPTION_PLANS, STORE_ITEMS
    except json.JSONDecodeError:
        SUBSCRIPTION_PLANS = {}
        STORE_ITEMS = {}
        return SUBSCRIPTION_PLANS, STORE_ITEMS

SUBSCRIPTION_PLANS, STORE_ITEMS = load_subscriptions_and_store()

def monitor_subscriptions_file_changes():
    while True:
        load_subscriptions_and_store() 
        time.sleep(5) 

subs_monitor_thread = threading.Thread(target=monitor_subscriptions_file_changes, daemon=True)
subs_monitor_thread.start()

@bot.message_handler(func=lambda message: message.text == "Купить подписку")
@check_function_state_decorator('Купить подписку')
@track_usage('Купить подписку')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def buy_subscription(message):
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    send_subscription_options(message)

def send_subscription_options(message):
    user_id = str(message.from_user.id)
    data = load_payment_data()
    user_discount = data['subscriptions']['users'].get(user_id, {}).get('discount', 0)
    applicable_category = data['subscriptions']['users'].get(user_id, {}).get('applicable_category')
    applicable_items = data['subscriptions']['users'].get(user_id, {}).get('applicable_items', [])
    markup = InlineKeyboardMarkup()
    MINIMUM_AMOUNT = 90

    discount_applicable_to_subscriptions = (
        applicable_category == "subscriptions" or
        any(item in SUBSCRIPTION_PLANS for item in applicable_items) or
        (applicable_category is None and not applicable_items)
    )

    display_discount = round(user_discount) if discount_applicable_to_subscriptions else 0
    applicability_str = ""
    if discount_applicable_to_subscriptions and user_discount > 0:
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
    buttons = []
    for plan_key, plan_info in SUBSCRIPTION_PLANS.items():
        base_price = plan_info["base_price"]
        fictitious_discount = plan_info.get("fictitious_discount", 0)
        label = plan_info["label"]

        discount_applicable = (
            applicable_category == "subscriptions" or
            (applicable_category is None and not applicable_items) or
            plan_key in applicable_items
        )
        discounted_price = base_price * (1 - (user_discount / 100 if discount_applicable else 0))
        final_price = max(MINIMUM_AMOUNT, max(1, round(discounted_price - fictitious_discount, 2)))

        if fictitious_discount > 0:
            fictitious_discount_text += f"🎁 *Акционная скидка* (применимо к: {label.lower()}): {fictitious_discount:.2f} ₽\n"
            has_fictitious_discount = True

        button_text = f"💳 {label} ({final_price:.2f} ₽)"
        buttons.append(InlineKeyboardButton(button_text, callback_data=plan_key))

    for i in range(0, len(buttons), 2):
        markup.add(*buttons[i:i+2])

    if not has_fictitious_discount:
        fictitious_discount_text = "🎁 *Акционная скидка:* 0.00 ₽\n"

    fictitious_discount_text += "\n"

    bot.send_message(user_id, (
        "Выберите период подписки:\n\n"
        f"{discount_info_text}"
        f"{fictitious_discount_text}"
        "📌 *3 дня*: использование функций бота в короткий срок!\n"
        "📌 *7 дней*: отличный способ протестировать все функции без долгих обязательств!\n"
        "📌 *30 дней*: оптимальный выбор для полноценного регулярного использования!\n"
        "📌 *90 дней*: удобный вариант с экономией и без необходимости частого продления!\n"
        "📌 *180 дней*: еще больше выгоды и стабильности!\n"
        "📌 *365 дней*: максимальная экономия — до 50% при длительном использовании!\n"
    ), reply_markup=markup, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_back = types.KeyboardButton("Вернуться в подписку")
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_back)
    markup.add(item_main)
    bot.send_message(user_id, "Выберите период подписки для оплаты:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in SUBSCRIPTION_PLANS)
def send_subscription_invoice(call):
    user_id = str(call.from_user.id)
    username = call.from_user.username or "неизвестный"  
    plan_key = call.data
    plan_info = SUBSCRIPTION_PLANS[plan_key]
    base_price = plan_info["base_price"]
    fictitious_discount = plan_info["fictitious_discount"]
    label = plan_info["label"]
    duration = plan_info["duration"]

    data = load_payment_data()
    user_discount = data['subscriptions']['users'].get(user_id, {}).get('discount', 0)
    applicable_category = data['subscriptions']['users'].get(user_id, {}).get('applicable_category')
    applicable_items = data['subscriptions']['users'].get(user_id, {}).get('applicable_items', [])
    discount_type = data['subscriptions']['users'].get(user_id, {}).get('discount_type', 'promo')

    discount_applicable = (
        applicable_category == "subscriptions" or
        plan_key in applicable_items or
        (applicable_category is None and not applicable_items)
    )
    user_discount = user_discount if discount_applicable else 0

    now = datetime.now()

    if user_discount >= 100:
        user_data = data['subscriptions']['users'].setdefault(user_id, {
            "plans": [], "total_amount": 0, "referral_points": 0, "store_purchases": []
        })

        if user_data['plans']:
            latest_end = max([datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") for p in user_data['plans']])
            start_date = max(latest_end, now) 
        else:
            start_date = now

        new_end = start_date + timedelta(days=duration)

        user_data['plans'].append({
            "plan_name": plan_key.split('_')[0],
            "start_date": start_date.strftime("%d.%m.%Y в %H:%M"),
            "end_date": new_end.strftime("%d.%m.%Y в %H:%M"),
            "price": 0,
            "telegram_payment_charge_id": None,
            "provider_payment_charge_id": None,
            "source": "promo_100_percent",
            "user_discount": user_discount,
            "fictitious_discount": fictitious_discount
        })

        if discount_type == "promo":
            bot.send_message(user_id, (
                "🎉 Ваша скидка в размере *100%* была успешно применена!\n"
                "🚀 Скидка сброшена! Используйте новые промокоды для получения скидок!"
            ), parse_mode="Markdown")
            data['subscriptions']['users'][user_id]['discount'] = 0
            data['subscriptions']['users'][user_id]['discount_type'] = None
            data['subscriptions']['users'][user_id]['applicable_category'] = None
            data['subscriptions']['users'][user_id]['applicable_items'] = []

        save_payments_data(data)

        bot.send_message(user_id, (
            "🎉 *Подписка активирована бесплатно!*\n\n"
            f"📅 *Начало:* {start_date.strftime('%d.%m.%Y в %H:%M')}\n"
            f"⏳ *Конец:* {new_end.strftime('%d.%m.%Y в %H:%M')}\n\n"
        ), parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Подписка активирована!")

        markup = create_main_menu()
        bot.send_message(user_id, f"Добро пожаловать, @{username}!\nВыберите действие из меню:", reply_markup=markup)
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
    invoice_payload = plan_key

    bot_functions = (
        "🚀 Ваш идеальный спутник в дороге: от расчета топлива и учета трат "
        "до прогноза погоды и антирадара — все для удобства и экономии!"
    )

    title = f"🌟 Подписка на {label}"
    description = (
        f"✨ Полный доступ ко всем функциям на {label.lower()}!\n"
        f"💰 Базовая цена: {base_price:.2f} ₽\n"
    )
    
    prices = [types.LabeledPrice(f"Подписка на {label}", int(base_price * 100))]
    if user_discount > 0 and user_discount_amount > 0:
        description += f"🏷️ Скидка {user_discount}%: -{user_discount_amount:.2f} ₽\n"
        user_discount_amount_kopecks = int(round(user_discount_amount * 100))
        prices.append(types.LabeledPrice(f"Скидка {user_discount}%", -user_discount_amount_kopecks))
    
    if fictitious_discount > 0:
        description += f"🎁 Акционная скидка: -{fictitious_discount:.2f} ₽\n"
        fictitious_discount_kopecks = int(round(fictitious_discount * 100))
        prices.append(types.LabeledPrice("Акционная скидка", -fictitious_discount_kopecks))

    description += f"💸 Итог: {final_price:.2f} ₽\n\n{bot_functions}"

    total_amount = sum(price.amount for price in prices)
    if total_amount < MINIMUM_AMOUNT * 100:
        prices = [types.LabeledPrice(f"Подписка на {label}", int(MINIMUM_AMOUNT * 100))]
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
            start_parameter="sub"
        )
    except Exception as e:
        bot.send_message(user_id, "❌ Произошла ошибка при создании платежа!\nПожалуйста, попробуйте позже или обратитесь в поддержку...")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_back = types.KeyboardButton("Вернуться в подписку")
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_back)
    markup.add(item_main)
    bot.send_message(user_id, "Выберите период подписки для оплаты:", reply_markup=markup)
    bot.answer_callback_query(call.id, "Счёт отправлен!")

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "неизвестный"
    payment_info = message.successful_payment
    data = load_payment_data()
    user_data = data['subscriptions']['users'].setdefault(user_id, {
        "plans": [], "total_amount": 0, "referral_points": 0, "store_purchases": []
    })

    payload = payment_info.invoice_payload
    user_discount = data['subscriptions']['users'].get(user_id, {}).get('discount', 0)
    applicable_category = data['subscriptions']['users'].get(user_id, {}).get('applicable_category')
    applicable_items = data['subscriptions']['users'].get(user_id, {}).get('applicable_items', [])
    discount_type = data['subscriptions']['users'].get(user_id, {}).get('discount_type', 'promo')

    now = datetime.now()

    if payload in SUBSCRIPTION_PLANS:
        plan_key = payload
        plan_info = SUBSCRIPTION_PLANS[plan_key]
        base_price = plan_info["base_price"]
        fictitious_discount = plan_info["fictitious_discount"]
        plan_duration = plan_info["duration"]

        discount_applicable = (
            applicable_category == "subscriptions" or
            plan_key in applicable_items or
            (applicable_category is None and not applicable_items)
        )
        applied_discount = round(user_discount) if discount_applicable else 0

        user_discount_amount = round(base_price * (applied_discount / 100), 2)
        discounted_price = base_price - user_discount_amount
        price = max(1, round(discounted_price - fictitious_discount, 2))

        if user_data['plans']:
            latest_end = max([datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") for p in user_data['plans']])
            start_date = max(latest_end, now)
        else:
            start_date = now

        new_end = start_date + timedelta(days=plan_duration)

        total_purchases = sum(1 for p in user_data['plans'] if p.get('source') == "user") + 1

        new_loyalty_discount = False
        if total_purchases % 3 == 0 and user_discount < 10:
            data['subscriptions']['users'][user_id]['discount'] = 10
            data['subscriptions']['users'][user_id]['discount_type'] = "loyalty"
            data['subscriptions']['users'][user_id]['applicable_category'] = "subscriptions"
            data['subscriptions']['users'][user_id]['applicable_items'] = []
            new_loyalty_discount = True
            bot.send_message(user_id, (
                "🎉 *Спасибо за лояльность!*\n\n"
                f"✨ Вы получили скидку *10%* за {total_purchases}-ю покупку подписки!\n"
                "🚀 Скидка применится к следующей покупке и сбросится после использования!"
            ), parse_mode="Markdown")

        user_data['plans'].append({
            "plan_name": plan_key.split('_')[0],
            "start_date": start_date.strftime("%d.%m.%Y в %H:%M"),
            "end_date": new_end.strftime("%d.%m.%Y в %H:%M"),
            "price": price,
            "telegram_payment_charge_id": payment_info.telegram_payment_charge_id,
            "provider_payment_charge_id": payment_info.provider_payment_charge_id,
            "source": "user",
            "user_discount": applied_discount,
            "fictitious_discount": fictitious_discount
        })
        user_data['total_amount'] = user_data.get('total_amount', 0) + price
        data['all_users_total_amount'] = data.get('all_users_total_amount', 0) + price

        is_first_purchase = not any(plan.get('source', 'unknown') == "user" for plan in user_data['plans'][:-1])
        join_date = data['subscriptions']['users'].get(user_id, {}).get('join_date', datetime.now().strftime("%d.%m.%Y в %H:%M"))
        days_since_join = (datetime.now() - datetime.strptime(join_date, "%d.%m.%Y в %H:%M")).days
        bonus_multiplier = 2 if days_since_join <= 7 else 1

        bonus_points = 0
        bonus_msg = ""
        notify_msg = ""
        if is_first_purchase:
            bonus_points = {3: 3, 7: 5, 30: 10, 90: 8, 180: 12, 365: 15}.get(plan_duration, 0)
            bonus_msg = f"Первая покупка подписки на {plan_duration} дней"
            notify_msg = f"✨ Вы получили *+{bonus_points * bonus_multiplier} баллов* за первую подписку на {plan_duration} дней!\n"
        else:
            bonus_points = {3: 0.5, 7: 1, 30: 3, 90: 2, 180: 5, 365: 10}.get(plan_duration, 0)
            bonus_msg = f"Покупка подписки на {plan_duration} дней"
            notify_msg = f"✨ Вы получили *+{bonus_points * bonus_multiplier} баллов* за подписку!\n"

        if bonus_points > 0:
            bonus_points *= bonus_multiplier
            user_data['referral_points'] += bonus_points
            user_data.setdefault('points_history', []).append({
                "action": "earned",
                "points": bonus_points,
                "reason": bonus_msg,
                "date": datetime.now().strftime("%d.%m.%Y в %H:%M")
            })
            bot.send_message(user_id, (
                f"🎁 *Спасибо за покупку!*\n\n"
                f"{notify_msg}"
                "🚀 Используйте их в системе баллов или в магазине!"
            ), parse_mode="Markdown")

        referrer_id = next((uid for uid, refs in data['referrals']['stats'].items() if user_id in refs), None)
        if referrer_id:
            bonus_days = {3: 0.5, 7: 1, 30: 3, 90: 2, 180: 5, 365: 7}.get(plan_duration, 1)
            new_end_referrer = set_free_trial_period(referrer_id, bonus_days, "referral_activity")
            bot.send_message(referrer_id, (
                "🎉 *Ваш реферал купил подписку!*\n\n"
                f"✨ Вы получили *+{bonus_days} день*!\n"
                f"⏳ *Активно до:* {new_end_referrer.strftime('%d.%m.%Y в %H:%M')}!\n\n"
                "😊 Спасибо за приглашение!"
            ), parse_mode="Markdown")

        if applied_discount > 0 and discount_type == "loyalty" and not new_loyalty_discount:
            bot.send_message(user_id, (
                f"🎉 Ваша скидка лояльности *{applied_discount:.0f}%* была применена!\n"
                "🚀 Скидка сброшена! Продолжайте покупать подписки для новых бонусов!"
            ), parse_mode="Markdown")
            data['subscriptions']['users'][user_id]['discount'] = 0
            data['subscriptions']['users'][user_id]['discount_type'] = None
            data['subscriptions']['users'][user_id]['applicable_category'] = None
            data['subscriptions']['users'][user_id]['applicable_items'] = []
        elif applied_discount > 0 and discount_type == "promo":
            bot.send_message(user_id, (
                f"🎉 Ваша скидка *{applied_discount:.0f}%* была применена!\n"
                "🚀 Скидка сброшена! Используйте новые промокоды для бонусов!"
            ), parse_mode="Markdown")
            data['subscriptions']['users'][user_id]['discount'] = 0
            data['subscriptions']['users'][user_id]['discount_type'] = None
            data['subscriptions']['users'][user_id]['applicable_category'] = None
            data['subscriptions']['users'][user_id]['applicable_items'] = []

        bot.send_message(user_id, (
            "🎉 *Спасибо за оплату*!\n\n"
            f"💰 *Оплачено:* {price:.2f} ₽\n\n"
            f"📅 *Ваша подписка начнётся:*\n{start_date.strftime('%d.%m.%Y в %H:%M')}\n"
            f"⏳ *Подписка будет активна до:*\n{new_end.strftime('%d.%m.%Y в %H:%M')}\n\n"
        ), parse_mode="Markdown")

    elif payload in STORE_ITEMS:
        item_info = STORE_ITEMS[payload]
        base_price = item_info["base_price"]
        fictitious_discount = item_info["fictitious_discount"]
        label = item_info["label"]

        discount_applicable = (
            applicable_category == "store" or
            payload in applicable_items or
            (applicable_category is None and not applicable_items)
        )
        applied_discount = round(user_discount) if discount_applicable else 0

        user_discount_amount = round(base_price * (applied_discount / 100), 2)
        discounted_price = base_price - user_discount_amount

        MINIMUM_AMOUNT = 90
        price = discounted_price - fictitious_discount
        if price < MINIMUM_AMOUNT:
            total_discount = base_price - MINIMUM_AMOUNT
            user_discount_amount = min(user_discount_amount, total_discount)
            user_discount_amount = round(user_discount_amount, 2)
            remaining_discount = total_discount - user_discount_amount
            fictitious_discount = min(fictitious_discount, remaining_discount)
            fictitious_discount = round(fictitious_discount, 2)
            price = MINIMUM_AMOUNT
        else:
            price = max(1, round(price, 2))

        purchase_date = datetime.now().strftime("%d.%m.%Y в %H:%M")
        monthly_key = datetime.now().strftime("%m.%Y")

        if 'store_purchases' not in user_data:
            user_data['store_purchases'] = []

        monthly_points = sum(p['points'] for p in user_data['store_purchases'] if p['purchase_date'].startswith(monthly_key))
        monthly_days = sum(p['duration'] for p in user_data['store_purchases'] if p['purchase_date'].startswith(monthly_key))

        if payload.startswith("points_"):
            points = item_info["points"]
            if monthly_points + points > 3000:
                bot.send_message(user_id, (
                    "⚠️ Вы превысили месячный лимит покупки баллов в размере 3000!\nПопробуйте снова в следующем месяце..."
                ), parse_mode="Markdown")
                return

            user_data['referral_points'] += points
            user_data.setdefault('points_history', []).append({
                "action": "earned",
                "points": points,
                "reason": f"Покупка {label}",
                "date": purchase_date
            })

            user_data['store_purchases'].append({
                "item_key": payload,
                "label": label,
                "points": points,
                "duration": 0,
                "price": price,
                "purchase_date": purchase_date,
                "telegram_payment_charge_id": payment_info.telegram_payment_charge_id,
                "provider_payment_charge_id": payment_info.provider_payment_charge_id,
                "source": "user",
                "user_discount": applied_discount,
                "fictitious_discount": fictitious_discount
            })

            bot.send_message(user_id, (
                f"🎉 *Спасибо за покупку!*\n\n"
                f"💰 *Оплачено:* {price:.2f} ₽\n"
                f"🎁 *Получено:* {points} баллов\n\n"
                "🚀 Используйте их в системе баллов!"
            ), parse_mode="Markdown")

        elif payload.startswith("time_"):
            duration = item_info["duration"]
            if monthly_days + duration > 365:
                bot.send_message(user_id, (
                    "⚠️ Вы превысили месячный лимит покупки времени в размере 365 дней!\nПопробуйте снова в следующем месяце..."
                ), parse_mode="Markdown")
                return

            if user_data['plans']:
                latest_end = max([datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") for p in user_data['plans']])
                start_date = max(latest_end, now)
            else:
                start_date = now

            new_end = start_date + timedelta(days=duration)

            user_data['plans'].append({
                "plan_name": "store_time",
                "start_date": start_date.strftime("%d.%m.%Y в %H:%M"),
                "end_date": new_end.strftime("%d.%m.%Y в %H:%M"),
                "price": price,
                "telegram_payment_charge_id": payment_info.telegram_payment_charge_id,
                "provider_payment_charge_id": payment_info.provider_payment_charge_id,
                "source": "store",
                "user_discount": applied_discount,
                "fictitious_discount": fictitious_discount
            })

            user_data['store_purchases'].append({
                "item_key": payload,
                "label": label,
                "points": 0,
                "duration": duration,
                "price": price,
                "purchase_date": purchase_date,
                "telegram_payment_charge_id": payment_info.telegram_payment_charge_id,
                "provider_payment_charge_id": payment_info.provider_payment_charge_id,
                "source": "user",
                "user_discount": applied_discount,
                "fictitious_discount": fictitious_discount
            })

            bot.send_message(user_id, (
                f"🎉 *Спасибо за покупку!*\n\n"
                f"💰 *Оплачено:* {price:.2f} ₽\n"
                f"📅 *Получено:* {duration} дней\n\n"
                f"🕒 *Начало:* {start_date.strftime('%d.%m.%Y в %H:%M')}\n"
                f"⌛ *Конец:* {new_end.strftime('%d.%m.%Y в %H:%M')}\n"
            ), parse_mode="Markdown")

        if applied_discount > 0 and discount_type == "promo":
            bot.send_message(user_id, (
                f"🎉 Ваша скидка в размере *{applied_discount:.0f}%* была успешно применена!\n"
                "🚀 Теперь скидка сброшена! Используйте новые промокоды для получения скидок!"
            ), parse_mode="Markdown")
            data['subscriptions']['users'][user_id]['discount'] = 0
            data['subscriptions']['users'][user_id]['discount_type'] = None
            data['subscriptions']['users'][user_id]['applicable_category'] = None
            data['subscriptions']['users'][user_id]['applicable_items'] = []

        user_data['total_amount'] = user_data.get('total_amount', 0) + price
        data['all_users_total_amount'] = data.get('all_users_total_amount', 0) + price

    else:
        bot.send_message(user_id, "❌ Неизвестный тип платежа!\nОбратитесь в поддержку...")
        return

    save_payments_data(data)

    markup = create_main_menu()
    bot.send_message(user_id, f"Добро пожаловать, @{username}!\nВыберите действие из меню:", reply_markup=markup)