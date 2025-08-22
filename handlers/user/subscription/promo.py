from core.imports import wraps, telebot, types, os, json, re, datetime, timedelta
from core.bot_instance import bot
from handlers.user.user_main_menu import load_payment_data, save_payments_data
from handlers.user.subscription.subscription_main import payments_function
from handlers.user.subscription.buy_subscription import SUBSCRIPTION_PLANS, STORE_ITEMS
from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage
)

def return_to_menu(message):
    from handlers.user.user_main_menu import return_to_menu as _f
    return _f(message)

# ------------------------------------------------ ПОДПИСКА НА БОТА (промокоды) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "Промокоды")
@check_function_state_decorator('Промокоды')
@track_usage('Промокоды')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def promo_payments_function(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Ввести промокод', 'Ваши промокоды')
    markup.add('Вернуться в подписку')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите действие из промокодов:", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Ввести промокод")
@check_function_state_decorator('Ввести промокод')
@track_usage('Ввести промокод')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def enter_promo_code(message):
    user_id = str(message.from_user.id)
    data = load_payment_data()

    last_promo_used = data['subscriptions']['users'].get(user_id, {}).get('last_promo_used')
    current_discount = data['subscriptions']['users'].get(user_id, {}).get('discount', 0)

    now = datetime.now()
    if last_promo_used and current_discount > 0:
        last_used_date = datetime.strptime(last_promo_used, "%d.%m.%Y в %H:%M")
        days_since_last_use = (now - last_used_date).days

        user_subscriptions = data['subscriptions']['users'].get(user_id, {}).get('plans', [])
        has_active_subscription = any(
            datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M") > now
            for plan in user_subscriptions
        )

        if days_since_last_use >= 30 and not has_active_subscription:
            data['subscriptions']['users'][user_id]['discount'] = 0
            save_payments_data(data)
            bot.send_message(message.chat.id, (
                "⚠️ Ваша скидка от предыдущего промокода истекла!\n"
                "⏳ Прошло более 30 дней, и подписка не была приобретена!\n\n"
                "Введите новый промокод, если он есть, чтобы получить скидку!"
            ), parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в промокоды")
    markup.add("Вернуться в подписку")
    markup.add("В главное меню")
    bot.send_message(message.chat.id, (
        "✍️ *Введите промокод:*\n\n"
        "💡 *Что будет после ввода?*\n"
        "Если промокод действителен, вы получите скидку на подписку (до 100% в зависимости от кода). "
        "Скидка будет автоматически применена при покупке подписки!\n\n"
        "📅 *Ограничения:*\n"
        "- Промокод можно использовать только один раз!\n"
        "- Новый промокод можно активировать только через 30 дней после предыдущего!\n"
        "- Если вы не купите подписку в течение 30 дней, скидка сгорит!"
    ), reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_promo_code)

@text_only_handler
def process_promo_code(message):
    if message.text == "Вернуться в промокоды":
        promo_payments_function(message)
        return
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    user_id = str(message.from_user.id)
    username = message.from_user.username or "неизвестный"
    code = message.text.upper()
    data = load_payment_data()
    promo_codes = data.get('promo_codes', {})

    now = datetime.now()
    last_promo_used = data['subscriptions']['users'].get(user_id, {}).get('last_promo_used')
    if last_promo_used:
        last_used_date = datetime.strptime(last_promo_used, "%d.%m.%Y в %H:%M")
        days_since_last_use = (now - last_used_date).days
        if days_since_last_use < 30:
            bot.send_message(user_id, (
                f"❌ *Вы уже использовали промокод в этом месяце!*\n"
                f"🔒 Вы сможете использовать следующий промокод через {30 - days_since_last_use} дней!"
            ), parse_mode="Markdown")
            payments_function(message, show_description=False)
            return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в промокоды")
    markup.add("Вернуться в подписку")
    markup.add("В главное меню")

    if code not in promo_codes:
        bot.send_message(user_id, (
            "❌ Неверный или несуществующий промокод! Проверьте код и попробуйте снова\n\n"
            "✍️ Введите промокод:"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_promo_code)
        return

    promo = promo_codes[code]
    uses = promo.get('uses', 1)
    used_by = promo.get('used_by', [])

    if len(used_by) >= uses:
        bot.send_message(user_id, (
            "❌ Этот промокод уже использован максимальное количество раз! Попробуйте другой промокод\n\n"
            "✍️ Введите промокод:"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_promo_code)
        return

    if any(entry['user_id'] == user_id for entry in used_by):
        bot.send_message(user_id, (
            "❌ Вы уже использовали этот промокод! Попробуйте другой промокод\n\n"
            "✍️ Введите промокод:"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_promo_code)
        return

    if promo.get('user_id') and promo['user_id'] != user_id:
        bot.send_message(user_id, (
            "❌ Этот промокод предназначен для другого пользователя! Попробуйте другой промокод\n\n"
            "✍️ Введите промокод:"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_promo_code)
        return

    created_at_str = promo.get('created_at')
    if created_at_str:
        try:
            created_at = datetime.strptime(created_at_str, "%d.%m.%Y в %H:%M")
            days_since_creation = (now - created_at).days
            if days_since_creation > 30:
                bot.send_message(user_id, (
                    "❌ Срок действия этого промокода истёк (30 дней)! Попробуйте другой промокод\n\n"
                    "✍️ Введите промокод:"
                ), reply_markup=markup, parse_mode="Markdown")
                bot.register_next_step_handler(message, process_promo_code)
                return
        except Exception:
            pass

    discount = promo['discount']
    applicable_category = promo.get('applicable_category')
    applicable_items = promo.get('applicable_items', [])

    if applicable_category is None and not applicable_items:
        applicability_str = "все товары"
    elif applicable_category == "subscriptions":
        applicability_str = "все подписки"
    elif applicable_category == "store":
        applicability_str = "весь магазин"
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
        applicability_str = ", ".join(applicable_labels)

    data['subscriptions']['users'].setdefault(user_id, {})['discount'] = discount
    data['subscriptions']['users'][user_id]['discount_type'] = 'promo'
    data['subscriptions']['users'][user_id]['applicable_category'] = applicable_category
    data['subscriptions']['users'][user_id]['applicable_items'] = applicable_items

    used_by.append({
        "user_id": user_id,
        "username": username,
        "used_at": now.strftime("%d.%m.%Y в %H:%M")
    })
    promo['used_by'] = used_by

    if len(used_by) >= uses:
        promo['used'] = True
        promo['active'] = False
        promo['deactivated_at'] = now.strftime("%d.%m.%Y в %H:%M")
        promo['deactivation_reason'] = "достигнуто максимальное количество использований"

    data['subscriptions']['users'].setdefault(user_id, {}).setdefault('last_promo_used', None)
    data['subscriptions']['users'][user_id]['last_promo_used'] = now.strftime("%d.%m.%Y в %H:%M")
    data['subscriptions']['users'].setdefault(user_id, {}).setdefault('promo_usage_history', []).append({
        "promo_code": code,
        "discount": discount,
        "used_at": now.strftime("%d.%m.%Y в %H:%M"),
        "applicable_category": applicable_category,
        "applicable_items": applicable_items
    })

    data['promo_codes'] = promo_codes
    save_payments_data(data)

    bot.send_message(user_id, (
        "🎉 *Промокод успешно активирован!*\n\n"
        f"✨ Вы получили скидку {discount:.0f}%!\n"
        f"🛒 *Применим к:* {applicability_str}\n"
        "🚀 Используйте её при покупке соответствующих товаров!\n\n"
        "📅 Вы сможете использовать следующий промокод через 30 дней!\n"
        "⏳ Если вы не купите подписку в течение 30 дней, скидка сгорит!"
    ), parse_mode="Markdown")
    payments_function(message, show_description=False)

# ------------------------------------------------ ПОДПИСКА НА БОТА (ваши промокоды) -----------------------------------------

TRANSLATIONS_YOURPROMOCODES = {
    "all_items": "все товары",  
    "subscriptions": "все подписки",
    "store": "весь магазин",
    "points_5": "5 баллов в магазине", "points_10": "10 баллов в магазине", "points_15": "15 баллов в магазине", 
    "points_25": "25 баллов в магазине", "points_30": "30 баллов в магазине", "points_50": "50 баллов в магазине",
    "points_75": "75 баллов в магазине", "points_100": "100 баллов в магазине", "points_150": "150 баллов в магазине", 
    "points_200": "200 баллов в магазине", "points_250": "250 баллов в магазине", "points_350": "350 баллов в магазине",
    "points_500": "500 баллов в магазине", "points_750": "750 баллов в магазине", "points_1000": "1000 баллов в магазине",
    "time_1day": "1 день в магазине", "time_2days": "2 дня в магазине", "time_4days": "4 дня в магазине",
    "time_5days": "5 дней в магазине", "time_8days": "8 дней в магазине", "time_10days": "10 дней в магазине",
    "time_14days": "14 дней в магазине", "time_15days": "15 дней в магазине", "time_21days": "21 день в магазине", 
    "time_45days": "45 дней в магазине", "time_60days": "60 дней в магазине", "time_120days": "120 дней в магазине",
    "trial_subscription_3": "3 дня в подписках", "weekly_subscription_7": "7 дней в подписках",
    "monthly_subscription_30": "30 дней в подписках", "quarterly_subscription_90": "90 дней в подписках",
    "semiannual_subscription_180": "180 дней в подписках", "yearly_subscription_365": "365 дней в подписках",
    "discount_type_promo": "промокод", "discount_type_referral": "реферальная"
}

def get_applicability_str(applicable_category, applicable_items):
    if applicable_category is None and not applicable_items:
        return TRANSLATIONS_YOURPROMOCODES["all_items"] 
    if applicable_category in TRANSLATIONS_YOURPROMOCODES:
        return TRANSLATIONS_YOURPROMOCODES[applicable_category]
    applicable_labels = [TRANSLATIONS_YOURPROMOCODES.get(item, item) for item in applicable_items]
    return ", ".join(applicable_labels)

def send_long_message(chat_id, message_text, parse_mode="Markdown"):
    MAX_MESSAGE_LENGTH = 4096
    if len(message_text) <= MAX_MESSAGE_LENGTH:
        bot.send_message(chat_id, message_text, parse_mode=parse_mode)
        return
    
    parts = []
    current_part = ""
    for line in message_text.split("\n"):
        if len(current_part) + len(line) + 1 > MAX_MESSAGE_LENGTH:
            parts.append(current_part.strip())
            current_part = line + "\n"
        else:
            current_part += line + "\n"
    if current_part:
        parts.append(current_part.strip())
    
    for i, part in enumerate(parts, 1):
        if i == 1:
            bot.send_message(chat_id, part, parse_mode=parse_mode)
        else:
            header = f"*Продолжение {i}*\n\n"
            bot.send_message(chat_id, header + part, parse_mode=parse_mode)

def format_discount(discount):
    try:
        n = float(discount)
    except (TypeError, ValueError):
        return str(discount)
    if n.is_integer():
        return f"{int(n)}"
    return f"{n:.2f}"

@bot.message_handler(func=lambda message: message.text == "Ваши промокоды")
@check_function_state_decorator('Ваши промокоды')
@track_usage('Ваши промокоды')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_promo_codes(message):
    user_id = str(message.from_user.id)
    data = load_payment_data()
    
    user_data = data["subscriptions"]["users"].get(user_id, {})
    promo_history = user_data.get("promo_usage_history", [])
    
    current_discount = user_data.get("discount", 0)
    discount_type = user_data.get("discount_type", "promo")
    applicable_category = user_data.get("applicable_category", None)
    applicable_items = user_data.get("applicable_items", [])
    
    promo_codes = data.get("promo_codes", {})
    unused_promos = []
    used_promo_codes = [promo["promo_code"] for promo in promo_history]  
    
    now = datetime.now()
    for promo_code, promo_data in promo_codes.items():
        if not promo_data.get("active", False):
            continue
        
        used_by = [entry["user_id"] for entry in promo_data.get("used_by", [])]
        if user_id in used_by or promo_code in used_promo_codes:
            continue
        
        promo_user_id = promo_data.get("user_id")
        if promo_user_id != user_id:
            continue
        
        created_at_str = promo_data.get("created_at")
        if created_at_str:
            try:
                created_at = datetime.strptime(created_at_str, "%d.%m.%Y в %H:%M")
                days_since_creation = (now - created_at).days
                if days_since_creation > 30:
                    continue
            except Exception:
                pass
        
        uses = promo_data.get("uses", 1)
        if len(used_by) >= uses:
            continue
        
        unused_promos.append({
            "promo_code": promo_code,
            "discount": promo_data["discount"],
            "applicable_category": promo_data.get("applicable_category", None),
            "applicable_items": promo_data.get("applicable_items", [])
        })
    
    if not promo_history and current_discount == 0 and not unused_promos:
        bot.send_message(user_id, "❌ *У вас пока нет промокодов или скидок!*\n"
                                 "Введите новый промокод или продолжайте пользоваться ботом, чтобы получить скидки!",
                         parse_mode="Markdown")
        return
    
    response = "🎟 *Ваши промокоды и скидки:*\n\n"
    
    if promo_history:
        response += "✅ *Применённые промокоды:*\n\n"
        for index, promo in enumerate(promo_history, 1):
            promo_code = promo["promo_code"]
            discount = promo["discount"]
            used_at = promo["used_at"]
            category = promo.get("applicable_category", None)
            items = promo.get("applicable_items", [])
            
            applicability = get_applicability_str(category, items)
            
            response += (f"🔸 *№{index}.* `{promo_code}`:\n"
                         f"   *Скидка:* {format_discount(discount)}%\n"
                         f"   *Использован:* {used_at}\n"
                         f"   *Применимо к:* {applicability}\n\n")
    
    if current_discount > 0:
        applicability = get_applicability_str(applicable_category, applicable_items)
        translated_discount_type = TRANSLATIONS_YOURPROMOCODES.get(f"discount_type_{discount_type}", discount_type)
        
        response += (f"🔹 *Текущая скидка (активна сейчас):*\n"
                     f"   *Тип:* {translated_discount_type}\n"
                     f"   *Скидка:* {format_discount(current_discount)}%\n"
                     f"   *Применимо к:* {applicability}\n\n")
    
    if unused_promos:
        response += "⚠️ *Доступные промокоды:*\n\n"
        for index, promo in enumerate(unused_promos, 1):
            promo_code = promo["promo_code"]
            discount = promo["discount"]
            category = promo.get("applicable_category", None)
            items = promo.get("applicable_items", [])
            
            applicability = get_applicability_str(category, items)
            
            response += (f"🔷 *№{index}.* `{promo_code}`:\n"
                         f"   *Скидка:* {format_discount(discount)}%\n"
                         f"   *Применимо к:* {applicability}\n"
                         f"   *Статус:* доступен для применения\n\n")
    
    response += "🚀 Введите новый промокод, чтобы получить ещё больше скидок!"
    
    send_long_message(user_id, response)