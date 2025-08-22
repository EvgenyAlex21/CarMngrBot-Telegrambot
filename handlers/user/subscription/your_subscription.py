from core.imports import wraps, telebot, types, os, json, re, pytz, datetime, timedelta, requests, ReplyKeyboardMarkup, ReplyKeyboardRemove
from core.bot_instance import bot
from handlers.user.user_main_menu import load_payment_data, save_payments_data
from handlers.user.subscription.subscription_main import payments_function
from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

def return_to_menu(message):
    from handlers.user.user_main_menu import return_to_menu as _f
    return _f(message)

# ------------------------------------------------ ПОДПИСКА НА БОТА (ваши подписки) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "Ваши подписки")
@check_function_state_decorator('Ваши подписки')
@track_usage('Ваши подписки')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def your_subsctiptions(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Посмотреть подписки', 'История подписок')
    markup.add('Вернуться в подписку')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите действие из ваших подписок:", reply_markup=markup, parse_mode="Markdown")

# ------------------------------------------------ ПОДПИСКА НА БОТА (посмотреть подписки) -----------------------------------------

def translate_plan_name(plan_name):
    return {
        "free": "пробный период", "referral_bonus": "реферальный бонус", "ad_bonus": "рекламный бонус",     
        "trial": "3 дня", "weekly": "7 дней", "monthly": "30 дней", "quarterly": "90 дней", "semiannual": "180 дней", "yearly": "365 дней",                   
        "points_bonus": "бонус за баллы", "gift_time": "подаренное время", "referral": "бонус за реферала",    
        "monthly_leader_bonus": "бонус лидера месяца", "leaderboard": "бонус топ-1", "store_time": "время из магазина",  
        "custom": "индивидуальный", "exchange_time": "обменное время"    
    }.get(plan_name, plan_name)

def send_long_message(chat_id, message_text, parse_mode='Markdown'):
    max_length = 4096
    for i in range(0, len(message_text), max_length):
        bot.send_message(chat_id, message_text[i:i + max_length], parse_mode=parse_mode)

@bot.message_handler(func=lambda message: message.text == "Посмотреть подписки")
@check_function_state_decorator('Посмотреть подписки')
@track_usage('Посмотреть подписки')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_subscription(message):
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    user_id = message.from_user.id
    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})

    if 'plans' not in user_data or not user_data['plans']:
        bot.send_message(user_id, (
            "⚠️ *У вас нет подписок!*\n\n"
            "🚀 Попробуй оформить первую подписку прямо сейчас!\n"
            "👉 Перейди в раздел *«купить подписку»*!"
        ), parse_mode="Markdown")
        return

    now = datetime.now()
    active_plans = [p for p in user_data['plans'] if datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") > now]
    if not active_plans:
        bot.send_message(user_id, (
            "⚠️ *У вас нет активных подписок!*\n\n"
            "🚀 Подключи подписку, чтобы воспользоваться функциями бота!\n"
            "👉 Перейди в раздел *«купить подписку»*!"
        ), parse_mode="Markdown")
        return

    plans_summary = "💎 *Список активных подписок:*\n\n"
    total_cost_active = 0

    unit_display = {
        'минуты': 'мин.',
        'часы': 'ч.',
        'дни': 'дн.'
    }

    for idx, plan in enumerate(active_plans):
        end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
        remaining_time = end_date - now
        days_left = remaining_time.days
        hours_left, remainder = divmod(remaining_time.seconds, 3600)
        minutes_left = remainder // 60

        plan_name_lower = plan['plan_name'].lower()
        source = plan.get('source', '')

        if plan_name_lower in {"free", "referral_bonus", "ad_bonus", "activity", "points_bonus", "referral", "monthly_leader_bonus", "leaderboard"}:
            period_type = f"🎁 *№{idx + 1}. Бонусный период:*"
            subscription_type = translate_plan_name(plan_name_lower)
        elif plan_name_lower in {"gift_time", "custom", "exchangetime"}:
            period_type = f"✨ *№{idx + 1}. Подаренный период:*"
            if plan_name_lower == "custom":
                duration_value = int(plan.get('duration_value', 1))
                duration_unit = plan.get('duration_unit', 'дни')
                subscription_type = f"индивидуальный ({duration_value} {unit_display.get(duration_unit, 'дн.')})"
            else:
                subscription_type = translate_plan_name(plan_name_lower)
        else:
            if source in {"user", "promo_100_percent", "store"}:
                period_type = f"💳 *№{idx + 1}. Платный период:*"
            else:
                period_type = f"📦 *№{idx + 1}. Назначенный период:*"
            subscription_type = translate_plan_name(plan_name_lower)

        start_date = plan['start_date']
        end_date_str = plan['end_date']
        price_formatted = f"{plan['price']:.2f}"

        plans_summary += (
            f"{period_type}\n\n"
            f"💼 *Тип подписки:* {subscription_type}\n"
            f"📅 *Дней осталось:* {days_left} дней и {hours_left:02d}:{minutes_left:02d} часов\n"
            f"🕒 *Начало:* {start_date}\n"
            f"⌛ *Конец:* {end_date_str}\n"
            f"💰 *Стоимость подписки:* {price_formatted} руб.\n\n"
        )
        total_cost_active += plan['price']

    send_long_message(message.chat.id, plans_summary)

    subtypes = []
    for p in active_plans:
        plan_name_lower = p['plan_name'].lower()
        if plan_name_lower == 'custom':
            duration_value = int(p.get('duration_value', 1))
            duration_unit = p.get('duration_unit', 'дни')
            subtypes.append(f"индивидуальный ({duration_value} {unit_display.get(duration_unit, 'дн.')})")
        else:
            subtypes.append(translate_plan_name(plan_name_lower))

    start_date = min(datetime.strptime(p['start_date'], "%d.%m.%Y в %H:%M") for p in active_plans).strftime("%d.%m.%Y в %H:%M")
    end_date = max(datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") for p in active_plans)
    total_remaining_time = end_date - now
    total_days_left = total_remaining_time.days
    hours_left, remainder = divmod(total_remaining_time.seconds, 3600)
    minutes_left = remainder // 60
    end_date_str = end_date.strftime("%d.%m.%Y в %H:%M")
    total_cost_active_formatted = f"{total_cost_active:.2f}"
    total_amount = user_data.get('total_amount', 0)
    total_amount_formatted = f"{total_amount:.2f}"

    summary_message = (
        "💎 *Итоговая подписочная оценка:*\n\n"
        f"💼 *Типы подписок:* {', '.join(t for t in subtypes)}\n"
        f"📅 *Дней осталось:* {total_days_left} дней и {hours_left:02d}:{minutes_left:02d} часов\n"
        f"🕒 *Начало:* {start_date}\n"
        f"⌛ *Конец:* {end_date_str}\n"
        f"💰 *Общая стоимость активных подписок:* {total_cost_active_formatted} руб.\n"
        f"💰 *Общая стоимость всех подписок:* {total_amount_formatted} руб.\n"
    )
    send_long_message(message.chat.id, summary_message)

# ------------------------------------------------ ПОДПИСКА НА БОТА (история подписок) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "История подписок")
@check_function_state_decorator('История подписок')
@track_usage('История подписок')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_subscription_history(message):
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    user_id = str(message.from_user.id)
    data = load_payment_data()
    history_plans = data['subscription_history'].get(user_id, [])

    if not history_plans:
        bot.send_message(message.chat.id, (
            "❌ *У вас нет истории подписок!*\n"
            "🚀 Попробуйте оформить подписку и начните использовать все возможности бота!"
        ), parse_mode="Markdown")
        return

    now = datetime.now(pytz.UTC)
    plans_summary = "📜 *История подписок:*\n\n"

    unit_display = {
        'минуты': 'мин.',
        'часы': 'ч.',
        'дни': 'дн.'
    }

    for idx, plan in enumerate(history_plans):
        plan_status = plan.get('status', 'expired')
        end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC)
        
        if plan_status != 'active':
            elapsed_time = now - end_date
            days_elapsed = elapsed_time.days
            hours_elapsed, remainder = divmod(elapsed_time.seconds, 3600)
            minutes_elapsed = remainder // 60
        else:
            days_elapsed = hours_elapsed = minutes_elapsed = 0

        plan_name_lower = plan['plan_name'].lower()
        source = plan.get('source', '')

        if plan_name_lower in {"free", "referral_bonus", "ad_bonus", "activity", "points_bonus", "referral", "monthly_leader_bonus", "leaderboard"}:
            period_type = f"🎁 *№{idx + 1}. Бонусный период:*"
            subscription_type = translate_plan_name(plan_name_lower)
        elif plan_name_lower in {"gift_time", "custom", "exchangetime"}:
            period_type = f"✨ *№{idx + 1}. Подаренный период:*"
            if plan_name_lower == "custom":
                duration_value = int(plan.get('duration_value', 1))
                duration_unit = plan.get('duration_unit', 'дни')
                subscription_type = f"индивидуальный ({duration_value} {unit_display.get(duration_unit, 'дн.')})"
            else:
                subscription_type = translate_plan_name(plan_name_lower)
        else:
            if source in {"user", "promo_100_percent", "store"}:
                period_type = f"💳 *№{idx + 1}. Платный период:*"
            else:
                period_type = f"📦 *№{idx + 1}. Назначенный период:*"
            subscription_type = translate_plan_name(plan_name_lower)

        start_date = plan['start_date']
        end_date_str = plan['end_date']
        price_formatted = f"{plan['price']:.2f}"

        plans_summary += (
            f"{period_type}\n\n"
            f"💼 *Тип подписки:* {subscription_type}\n"
            f"📅 *Начало:* {start_date}\n"
            f"⌛ *Конец:* {end_date_str}\n"
        )
        if plan_status == 'cancelled':
            plans_summary += f"🚫 *Статус:* Отменена\n"
            if plan.get('refunded', False):
                plans_summary += (
                    f"💸 *Возвращено:* {plan.get('refund_amount', 0):.2f} руб.\n"
                    f"🆔 *ID возврата:* {plan.get('refund_id', 'Не присвоен')}\n"
                    f"📅 *Дата отмены:* {plan.get('cancelled_date', 'Не указана')}\n"
                )
        else:
            plans_summary += f"📈 *Статус:* {'Активна' if plan_status == 'active' else 'Истекла'}\n"
            if plan_status != 'active':
                plans_summary += f"⏳ *Дней прошло:* {days_elapsed} дней и {hours_elapsed:02d}:{minutes_elapsed:02d} часов\n"
        plans_summary += f"💰 *Стоимость подписки:* {price_formatted} руб.\n\n"

    send_long_message(message.chat.id, plans_summary)