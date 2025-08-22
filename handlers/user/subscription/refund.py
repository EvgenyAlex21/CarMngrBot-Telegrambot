from core.imports import wraps, telebot, types, os, json, re, pytz, requests, time, threading, datetime, timedelta, ReplyKeyboardMarkup, ReplyKeyboardRemove
from core.bot_instance import bot, BASE_DIR
from core.config import PAYMASTER_MERCHANT_ID, PAYMASTER_SECRET_KEY, PAYMASTER_TOKEN
from handlers.user.user_main_menu import load_payment_data, save_payments_data, safe_send_message
from handlers.user.subscription.subscription_main import payments_function
from handlers.user.subscription.your_subscription import translate_plan_name, send_long_message
from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

def return_to_menu(message):
    from handlers.user.user_main_menu import return_to_menu as _f
    return _f(message)

# ------------------------------------------------ ПОДПИСКА НА БОТА (возврат) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "Возврат")
@check_function_state_decorator('Возврат')
@track_usage('Возврат')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def refund_payment_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Отменить подписки', 'История возвратов')
    markup.add('Вернуться в подписку')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите действие из возврата:", reply_markup=markup, parse_mode="Markdown")

# ------------------------------------------------ ПОДПИСКА НА БОТА (отменить подписки) -----------------------------------------

PAYMASTER_API_URL = "https://paymaster.ru/api/v2/"
REFUND_COMMISSION = 0.25
MIN_REFUND_AMOUNT = 1.0
MAX_REFUNDS_PER_MONTH = 3
MAX_REFUNDS_PER_YEAR = 12
PAYMENTS_FILE = os.path.join(BASE_DIR, "data", "admin", "admin_user_payments", "payments.json")

def calculate_refunded_amount(plan):
    try:
        end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC)
        start_date = datetime.strptime(plan['start_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC)
        now = datetime.now(pytz.UTC)

        if plan['price'] <= 100:
            return 0.0, "Подписка стоимостью 100 рублей и менее не подлежит возврату!"

        if plan['price'] <= 0:
            return 0.0, "Подписка бесплатная и не подлежит возврату!"

        if now >= end_date:
            return 0.0, "Подписка уже истекла!"

        total_minutes = (end_date - start_date).total_seconds() / 60
        if total_minutes <= 0:
            return 0.0, "Некорректная длительность подписки!"

        if now < start_date:
            refund_amount = plan['price']
            commission = refund_amount * REFUND_COMMISSION
            if refund_amount <= commission:
                return 0.0, "Сумма возврата меньше комиссии!"
            return round(refund_amount - commission, 2), None

        remaining_time = end_date - now
        remaining_minutes = max(0, min(total_minutes, remaining_time.total_seconds() / 60))
        minute_cost = plan['price'] / total_minutes
        refund_amount = minute_cost * remaining_minutes
        refund_amount = min(refund_amount, plan['price'])
        commission = refund_amount * REFUND_COMMISSION
        if refund_amount <= commission:
            return 0.0, "Сумма возврата меньше комиссии!"
        final_refunded = refund_amount - commission
        final_refunded = round(final_refunded, 2)

        if final_refunded < MIN_REFUND_AMOUNT:
            return 0.0, "Сумма возврата слишком мала!"

        return final_refunded, None
    except Exception as e:
        return 0.0, f"Ошибка расчета возврата: {str(e)}"

def check_refund_limits(user_id):
    data = load_payment_data()
    now = datetime.now(pytz.UTC)
    current_month = now.strftime("%m.%Y")
    current_year = now.strftime("%Y")
    user_refunds = data.get("refunds", [])
    
    monthly_refunds = [r for r in user_refunds if r["user_id"] == str(user_id) and r["refund_date"].startswith(current_month)]
    yearly_refunds = [r for r in user_refunds if r["user_id"] == str(user_id) and r["refund_date"].split(" в ")[0][-4:] == current_year]
    
    if len(monthly_refunds) >= MAX_REFUNDS_PER_MONTH:
        return False, f"Превышен месячный лимит возвратов ({MAX_REFUNDS_PER_MONTH})!"
    if len(yearly_refunds) >= MAX_REFUNDS_PER_YEAR:
        return False, f"Превышен годовой лимит возвратов ({MAX_REFUNDS_PER_YEAR})!"
    return True, None

def check_daily_payment_limit(refund_amount):
    try:
        headers = {"Authorization": f"Bearer {PAYMASTER_TOKEN}"}
        today = datetime.now(pytz.UTC).strftime("%Y-%m-%d")
        response = requests.get(f"{PAYMASTER_API_URL}payments?dateFrom={today}&dateTo={today}", headers=headers)
        response.raise_for_status()
        payments = response.json().get("payments", [])
        total_successful = sum(float(p["amount"]["value"]) for p in payments if p["status"] == "success")
        if total_successful < refund_amount:
            return False, f"Сумма возврата ({refund_amount:.2f} руб.) превышает сумму успешных платежей за день ({total_successful:.2f} руб.)!"
        return True, None
    except Exception as e:
        return False, f"Ошибка проверки дневного лимита платежей: {str(e)}"

def refund_payment(user_id, refund_amount, payment_id, plan):
    can_refund, limit_error = check_daily_payment_limit(refund_amount)
    if not can_refund:
        data = load_payment_data()
        if "refunds" not in data:
            data["refunds"] = []
        refund_record = {
            "user_id": str(user_id),
            "plan_name": plan["plan_name"],
            "refund_amount": refund_amount,
            "refund_date": datetime.now(pytz.UTC).strftime("%d.%m.%Y в %H:%M"),
            "telegram_payment_charge_id": plan.get("telegram_payment_charge_id", ""),
            "provider_payment_charge_id": payment_id,
            "refund_id": None,
            "status": "failed",
            "error": limit_error
        }
        data["refunds"].append(refund_record)
        save_payments_data(data)
        return None, "failed"

    refund_data = {
        "paymentId": payment_id,
        "amount": {
            "value": f"{refund_amount:.2f}",
            "currency": "RUB"
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {PAYMASTER_TOKEN}",
        "Idempotency-Key": f"{user_id}_{int(datetime.now(pytz.UTC).timestamp())}"
    }
    try:
        response = requests.post(f"{PAYMASTER_API_URL}refunds", json=refund_data, headers=headers)
        response.raise_for_status()
        result = response.json()
        refund_id = result.get("id")
        status = result.get("status", "pending").lower()
        data = load_payment_data()
        if "refunds" not in data:
            data["refunds"] = []
        refund_record = {
            "user_id": str(user_id),
            "plan_name": plan["plan_name"],
            "refund_amount": refund_amount,
            "refund_date": datetime.now(pytz.UTC).strftime("%d.%m.%Y в %H:%M"),
            "telegram_payment_charge_id": plan.get("telegram_payment_charge_id", ""),
            "provider_payment_charge_id": payment_id,
            "refund_id": refund_id,
            "status": status,
            "error": None
        }
        data["refunds"].append(refund_record)
        save_payments_data(data)
        return refund_id, status
    except requests.exceptions.HTTPError as e:
        error_message = f"Ошибка API PayMaster: {str(e)}"
        if e.response.status_code == 400:
            error_message = "Некорректные данные для возврата! Проверьте ID платежа и сумму"
        elif e.response.status_code == 403:
            error_message = "Доступ запрещен! Проверьте токен авторизации..."
        data = load_payment_data()
        if "refunds" not in data:
            data["refunds"] = []
        refund_record = {
            "user_id": str(user_id),
            "plan_name": plan["plan_name"],
            "refund_amount": refund_amount,
            "refund_date": datetime.now(pytz.UTC).strftime("%d.%m.%Y в %H:%M"),
            "telegram_payment_charge_id": plan.get("telegram_payment_charge_id", ""),
            "provider_payment_charge_id": payment_id,
            "refund_id": None,
            "status": "failed",
            "error": error_message
        }
        data["refunds"].append(refund_record)
        save_payments_data(data)
        return None, "failed"
    except Exception as e:
        data = load_payment_data()
        if "refunds" not in data:
            data["refunds"] = []
        refund_record = {
            "user_id": str(user_id),
            "plan_name": plan["plan_name"],
            "refund_amount": refund_amount,
            "refund_date": datetime.now(pytz.UTC).strftime("%d.%m.%Y в %H:%M"),
            "telegram_payment_charge_id": plan.get("telegram_payment_charge_id", ""),
            "provider_payment_charge_id": payment_id,
            "refund_id": None,
            "status": "failed",
            "error": str(e)
        }
        data["refunds"].append(refund_record)
        save_payments_data(data)
        return None, "failed"

@bot.message_handler(func=lambda message: message.text == "Отменить подписки")
@check_function_state_decorator('Отменить подписки')
@track_usage('Отменить подписки')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def cancel_subscription(message):
    user_id = message.from_user.id
    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(str(user_id), {})

    if 'plans' not in user_data or not user_data['plans']:
        bot.send_message(user_id, (
            "⚠️ *У вас нет подписок!*\n\n"
            "🚀 Попробуй оформить первую подписку прямо сейчас!\n"
            "👉 Перейди в раздел *«купить подписку»*!"
        ), parse_mode="Markdown")
        payments_function(message, show_description=False)
        return

    now = datetime.now(pytz.UTC)
    refundable_plans = [
        p for p in user_data['plans']
        if p['plan_name'] in ['trial', 'weekly', 'monthly', 'quarterly', 'semiannual', 'yearly', 'store_time']
        and p['source'] in ['user', 'store', 'promo_100_percent']
        and datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC) > now
        and p.get('provider_payment_charge_id')
        and p['price'] > 100 
    ]

    if not refundable_plans:
        bot.send_message(user_id, (
            "⚠️ *У вас нет активных подписок стоимостью более 100 рублей, доступных для возврата!*\n\n"
            "🚀 Подключи подписку, чтобы воспользоваться функциями бота!\n"
            "👉 Перейди в раздел *«купить подписку»*!"
        ), parse_mode="Markdown")
        payments_function(message, show_description=False)
        return

    can_refund, limit_error = check_refund_limits(user_id)
    if not can_refund:
        bot.send_message(user_id, f"⚠️ *{limit_error}!*\nПопробуйте снова позже", parse_mode="Markdown")
        payments_function(message, show_description=False)
        return

    plans_summary = "💎 *Список активных подписок, доступных для возврата:*\n\n"
    unit_display = {
        'минуты': 'мин.',
        'часы': 'ч.',
        'дни': 'дн.'
    }
    for idx, plan in enumerate(refundable_plans):
        end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC)
        start_date = datetime.strptime(plan['start_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC)
        
        if start_date > now:
            remaining_time = end_date - start_date
        else:
            remaining_time = end_date - now
        
        days_left = remaining_time.days
        hours_left, remainder = divmod(remaining_time.seconds, 3600)
        minutes_left = remainder // 60
        
        plan_name_lower = plan['plan_name'].lower()
        subscription_type = translate_plan_name(plan_name_lower)
        if plan_name_lower == 'custom':
            duration_value = int(plan.get('duration_value', 1))
            duration_unit = plan.get('duration_unit', 'дни')
            subscription_type = f"индивидуальный ({duration_value} {unit_display.get(duration_unit, 'дн.')})"
        
        price_formatted = f"{plan['price']:.2f}"
        refund_amount, error = calculate_refunded_amount(plan)
        refund_status = f"💸 Возможный возврат: {refund_amount:.2f} руб." if not error else f"⚠️ {error}"
        plans_summary += (
            f"💳 *№{idx + 1}. Платный период:*\n\n"
            f"💼 *Тип подписки:* {subscription_type}\n"
            f"📅 *Дней осталось:* {days_left} дней и {hours_left:02d}:{minutes_left:02d} часов\n"
            f"🕒 *Начало:* {plan['start_date']}\n"
            f"⌛ *Конец:* {plan['end_date']}\n"
            f"💰 *Стоимость подписки:* {price_formatted} руб.\n"
            f"{refund_status}\n\n"
        )

    send_long_message(user_id, plans_summary)
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в подписку")
    markup.add("В главное меню")
    bot.send_message(user_id, "Введите номера подписок для отмены:", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_cancellation_step, refundable_plans=refundable_plans)

@text_only_handler
def confirm_cancellation_step(message, refundable_plans):
    user_id = message.from_user.id
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    try:
        subscription_numbers = [int(num.strip()) for num in message.text.split(',') if num.strip()]
        valid_numbers = [num for num in subscription_numbers if 1 <= num <= len(refundable_plans)]
        invalid_numbers = [num for num in subscription_numbers if num not in valid_numbers]

        if not valid_numbers:
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Вернуться в подписку")
            markup.add("В главное меню")
            bot.send_message(user_id, "⚠️ Все номера некорректны!\nВведите номера:", reply_markup=markup, parse_mode="Markdown")
            bot.register_next_step_handler(message, confirm_cancellation_step, refundable_plans=refundable_plans)
            return

        if invalid_numbers:
            bot.send_message(user_id, f"⚠️ Номера `{invalid_numbers}` некорректны и пропущены!", parse_mode="Markdown")

        refund_summary = "*Подтверждение отмены:*\n\n"
        total_refunded = 0.0
        selected_plans = []
        unit_display = {
            'минуты': 'мин.',
            'часы': 'ч.',
            'дни': 'дн.'
        }
        for num in valid_numbers:
            plan = refundable_plans[num - 1]
            refund_amount, error = calculate_refunded_amount(plan)
            if error:
                refund_summary += f"❌ Подписка №{num}: {error}\n"
                continue
            now = datetime.now(pytz.UTC)
            end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC)
            start_date = datetime.strptime(plan['start_date'], "%d.%m.%Y в %H:%M").replace(tzinfo=pytz.UTC)
            total_minutes = (end_date - start_date).total_seconds() / 60
            remaining_time = end_date - now
            remaining_minutes = max(0, min(total_minutes, remaining_time.total_seconds() / 60))
            days_left = remaining_minutes // (24 * 60)
            remaining_minutes_after_days = remaining_minutes % (24 * 60)
            hours_left = remaining_minutes_after_days // 60
            minutes_left = remaining_minutes_after_days % 60
            commission = refund_amount * REFUND_COMMISSION
            
            plan_name_lower = plan['plan_name'].lower()
            subscription_type = translate_plan_name(plan_name_lower)
            if plan_name_lower == 'custom':
                duration_value = int(plan.get('duration_value', 1))
                duration_unit = plan.get('duration_unit', 'дни')
                subscription_type = f"индивидуальный ({duration_value} {unit_display.get(duration_unit, 'дн.')})"
            
            remaining_time_str = f"{int(days_left)} дн. {int(hours_left):02d}:{int(minutes_left):02d} ч."
            if days_left == 0:
                remaining_time_str = f"{int(hours_left):02d}:{int(minutes_left):02d} ч."
            if hours_left == 0 and days_left == 0:
                remaining_time_str = f"{int(minutes_left)} мин."
            
            refund_summary += (
                f"💳 *Подписка №{num}*\n\n"
                f"💼 *Тип подписки:* {subscription_type}\n"
                f"📅 *Осталось времени:* {remaining_time_str}\n"
                f"💸 *Возврат:* {refund_amount:.2f} руб.\n"
                f"💸 *Комиссия:* {commission:.2f} руб.\n\n"
            )
            total_refunded += refund_amount
            selected_plans.append((num, plan))

        if total_refunded == 0:
            bot.send_message(user_id, "❌ Нет подписок для возврата!", parse_mode="Markdown")
            payments_function(message, show_description=False)
            return

        refund_summary += f"📥 Итого: *{total_refunded:.2f} руб.*"
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Подтвердить", "Отменить")
        markup.add("Вернуться в подписку")
        markup.add("В главное меню")
        bot.send_message(user_id, refund_summary, parse_mode="Markdown")
        bot.send_message(user_id, "Подтвердите действие:", reply_markup=markup)
        bot.register_next_step_handler(message, process_cancellation_step, selected_plans=selected_plans, total_refunded=total_refunded)
    except ValueError:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в подписку")
        markup.add("В главное меню")
        bot.send_message(user_id, "⚠️ Неверный формат!\nВведите номера:", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, confirm_cancellation_step, refundable_plans=refundable_plans)

@text_only_handler
def process_cancellation_step(message, selected_plans, total_refunded):
    user_id = message.from_user.id
    user_id_str = str(user_id)

    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Отменить":
        bot.send_message(user_id, "❌ Возврат отменен!", parse_mode="Markdown")
        payments_function(message, show_description=False)
        return
    if message.text != "Подтвердить":
        bot.send_message(user_id, "⚠️ Пожалуйста, выберите действие из предложенных!", parse_mode="Markdown")
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Подтвердить", "Отменить")
        markup.add("Вернуться в подписку")
        markup.add("В главное меню")
        bot.send_message(user_id, "Подтвердите действие:", reply_markup=markup)
        bot.register_next_step_handler(message, process_cancellation_step, selected_plans=selected_plans, total_refunded=total_refunded)
        return

    data = load_payment_data()
    user_data = data['subscriptions']['users'].get(user_id_str, {'plans': [], 'total_amount': 0})
    if user_id_str not in data['subscription_history']:
        data['subscription_history'][user_id_str] = []

    successful_refunds = []
    failed_refunds = []
    unit_display = {
        'минуты': 'мин.',
        'часы': 'ч.',
        'дни': 'дн.'
    }

    for num, plan in selected_plans:
        can_refund, limit_error = check_refund_limits(user_id)
        if not can_refund:
            failed_refunds.append((num, limit_error))
            continue

        refund_amount, error = calculate_refunded_amount(plan)
        if error:
            failed_refunds.append((num, error))
            continue

        payment_id = plan.get('provider_payment_charge_id', '')
        if not payment_id:
            failed_refunds.append((num, "Отсутствует ID платежа!"))
            continue

        refund_id, status = refund_payment(user_id, refund_amount, payment_id, plan)
        if status == "failed":
            failed_refunds.append((num, "Ошибка обработки возврата!"))
            continue

        original_start_date = plan['start_date']
        plan['status'] = 'cancelled'
        plan['refunded'] = refund_amount > 0
        plan['refund_id'] = refund_id
        plan['refund_status'] = status
        plan['cancelled_date'] = datetime.now(pytz.UTC).strftime("%d.%m.%Y в %H:%M")

        data['subscription_history'][user_id_str].append(plan)

        target_plan = None
        for p in user_data['plans']:
            if (p.get('telegram_payment_charge_id') == plan.get('telegram_payment_charge_id') and
                p.get('start_date') == plan.get('start_date') and
                p.get('end_date') == plan.get('end_date') and
                p.get('plan_name') == plan.get('plan_name')):
                target_plan = p
                break

        if not target_plan:
            failed_refunds.append((num, "Подписка не найдена в активных подписках!"))
            continue

        user_data['plans'].remove(target_plan)
        user_data['total_amount'] = max(0, user_data.get('total_amount', 0) - plan.get('price', 0))

        successful_refunds.append({
            "number": num,
            "plan_name": plan['plan_name'],
            "refund_amount": refund_amount,
            "refund_id": refund_id,
            "status": status,
            "original_start_date": original_start_date
        })

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
            user_message = (
                f"🔄 Изменены даты вашей подписки:\n\n"
                f"💼 *План подписки:* {subscription_type}\n"
                f"🕒 *Новое начало:* {plan['start_date']}\n"
                f"⌛ *Новый конец:* {plan['end_date']}"
            )
            bot.send_message(user_id, user_message, parse_mode="Markdown")

    data['all_users_total_amount'] = sum(
        u.get('total_amount', 0) for u in data['subscriptions']['users'].values()
    )

    save_payments_data(data)

    result_message = "📋 *Результат отмены подписок:*\n\n"
    for refund in successful_refunds:
        result_message += ( 
            f"✅ *Подписка №{refund['number']}*\n\n"
            f"💼 *Тип подписки:* {translate_plan_name(refund['plan_name'])}\n"
            f"💸 *Возвращено:* {refund['refund_amount']:.2f} руб.\n"
            f"📅 *Дата покупки:* {refund['original_start_date']}\n"
            f"🆔 *ID возврата:* {refund['refund_id'] or 'не присвоен'}\n"
            f"📈 *Статус:* {refund['status'].capitalize()}\n"
            f"💳 Ожидайте возврат на ваш счет в течение *1–7 рабочих дней*...\n\n"
        )
    for num, error in failed_refunds:
        plan = next((p for n, p in selected_plans if n == num), None)
        plan_name = plan['plan_name'] if plan else "Неизвестная подписка"
        result_message += (
            f"❌ *Подписка №{num}*\n\n"
            f"💼 *Тип подписки:* {translate_plan_name(plan_name)}\n"
            f"⚠️ *Ошибка:* {error}\n"
            f"📞 Обратитесь в поддержку для решения проблемы!\n\n"
        )

    if successful_refunds:
        result_message += f"📥 *Итого возвращено:* {total_refunded:.2f} руб.\n"
    if not successful_refunds and not failed_refunds:
        result_message = "❌ Не удалось отменить подписки!"

    send_long_message(user_id, result_message)
    payments_function(message, show_description=False)

def background_refund_status_check():
    while True:
        data = load_payment_data()
        pending_refunds = [r for r in data.get("refunds", []) if r["status"] in ["pending", "processing"]]
        for refund in pending_refunds:
            refund_id = refund.get("refund_id")
            if not refund_id:
                continue
            try:
                headers = {"Authorization": f"Bearer {PAYMASTER_TOKEN}"}
                response = requests.get(f"{PAYMASTER_API_URL}refunds/{refund_id}", headers=headers)
                response.raise_for_status()
                result = response.json()
                new_status = result.get("status", "pending").lower()
                if new_status != refund["status"]:
                    refund["status"] = new_status
                    refund["last_updated"] = datetime.now(pytz.UTC).strftime("%d.%m.%Y в %H:%M")
                    user_id = refund["user_id"]
                    status_message = (
                        f"📋 *Обновление статуса возврата:*\n\n"
                        f"💳 Подписка: {translate_plan_name(refund['plan_name'])}\n"
                        f"💸 Сумма: {refund['refund_amount']:.2f} руб.\n"
                        f"🆔 ID возврата: {refund_id}\n"
                        f"📈 Новый статус: {new_status.capitalize()}\n"
                        f"📅 Дата обновления: {refund['last_updated']}\n"
                    )
                    if new_status == "success":
                        status_message += "✅ Средства будут зачислены на ваш счет в течение 1–7 рабочих дней!"
                    elif new_status == "failed":
                        status_message += "⚠️ Возврат не удался! Обратитесь в поддержку..."
                    safe_send_message(user_id, status_message, parse_mode="Markdown")
                    save_payments_data(data)
            except Exception as e:
                refund["status"] = "failed"
                refund["error"] = str(e)
                refund["last_updated"] = datetime.now(pytz.UTC).strftime("%d.%m.%Y в %H:%M")
                safe_send_message(refund["user_id"], (
                    f"❌ *Ошибка проверки статуса возврата:*\n\n"
                    f"💳 Подписка: {translate_plan_name(refund['plan_name'])}\n"
                    f"💸 Сумма: {refund['refund_amount']:.2f} руб.\n"
                    f"🆔 ID возврата: {refund_id}\n"
                    f"⚠️ Ошибка: {str(e)}\n"
                    f"📞 Обратитесь в поддержку!"
                ), parse_mode="Markdown")
                save_payments_data(data)
        time.sleep(3600)

refund_status_thread = threading.Thread(target=background_refund_status_check, daemon=True)
refund_status_thread.start()

# ------------------------------------------------ ПОДПИСКА НА БОТА (история возвратов) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "История возвратов")
@check_function_state_decorator('История возвратов')
@track_usage('История возвратов')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_refund_history(message):
    user_id = str(message.from_user.id)
    data = load_payment_data()
    user_refunds = [r for r in data.get('refunds', []) if r['user_id'] == user_id]

    if not user_refunds:
        bot.send_message(user_id, (
            "❌ *У вас нет истории возвратов!*\n"
            "🚀 Начните с оформления подписки, чтобы использовать все возможности!"
        ), parse_mode="Markdown")
        return

    refunds_summary = "📜 *История возвратов:*\n\n"
    for idx, refund in enumerate(user_refunds):
        refunds_summary += (
            f"💳 *Возврат №{idx + 1}:*\n"
            f"💼 Подписка: {translate_plan_name(refund['plan_name'])}\n"
            f"💸 Сумма: {refund['refund_amount']:.2f} руб.\n"
            f"📅 Дата: {refund['refund_date']}\n"
            f"🆔 ID возврата: {refund.get('refund_id', 'Не присвоен')}\n"
            f"📈 Статус: {refund['status'].capitalize()}\n"
        )
        if refund.get('error'):
            refunds_summary += f"⚠️ Ошибка: {refund['error']}\n"
        refunds_summary += "\n"

    send_long_message(message.chat.id, refunds_summary)