from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, timedelta
from core.bot_instance import bot
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from handlers.admin.system_management.system_management import manage_system
from handlers.admin.statistics.statistics import check_admin_access, escape_markdown
from handlers.user.user_main_menu import load_payment_data, load_users_data as load_users
from handlers.user.subscription.gifts import split_message
from handlers.admin.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

# --------------------------------------- УПРАВЛЕНИЕ СИСТЕМОЙ (статистика системы) -------------------------------------

def format_number(num):
    if isinstance(num, int):
        return f"{num}"
    elif isinstance(num, float):
        return f"{num:.2f}" if num != int(num) else f"{int(num)}"
    return str(num)

@bot.message_handler(func=lambda message: message.text == 'Статистика системы' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_referrals_and_stats(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Статистика системы'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == "Вернуться в управление системой":
        manage_system(message)
        return

    if message.text == "В меню админ-панели":
        show_admin_panel(message)
        return

    data = load_payment_data()
    users_data = load_users()
    now = datetime.strptime("01.01.2025 в 00:00", "%d.%m.%Y в %H:%M")

    referral_summary = "*Статистика реферальной системы:*\n\n"
    referral_stats = data.get('referrals', {}).get('stats', {})
    total_referrals = 0
    active_referral_subscriptions = 0
    total_referral_points = 0
    referral_users = 0
    if referral_stats:
        referral_summary += "*Пользователи и их приглашенные:*\n\n"
        for idx, (user_id, referrals) in enumerate(referral_stats.items(), 1):
            username = users_data.get(user_id, {}).get('username', user_id)
            if not username.startswith('@'):
                username = f"@{username}"
            referral_summary += (
                f"🎁 *№{idx}.* {escape_markdown(username)} (`{escape_markdown(user_id)}`): "
                f"{len(referrals)} рефералов\n"
            )
            total_referrals += len(referrals)
            for referral_id in referrals:
                user_plans = data.get('subscriptions', {}).get('users', {}).get(referral_id, {}).get('plans', [])
                for plan in user_plans:
                    end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
                    if end_date >= now:
                        active_referral_subscriptions += 1
                        break
        referral_summary += (
            f"\n\n*Общая статистика:*\n\n"
            f"👥 Всего рефералов: {total_referrals}\n"
            f"📈 Рефералов с активной подпиской: {active_referral_subscriptions}\n"
        )
    else:
        referral_summary += "❌ Данные о рефералах отсутствуют!\n\n"

    for user_id, user_data in data.get('subscriptions', {}).get('users', {}).items():
        points = user_data.get('referral_points', 0)
        total_referral_points += points
        if points > 0:
            referral_users += 1
    avg_referral_points = total_referral_points / referral_users if referral_users > 0 else 0
    referral_summary += (
        f"\n\n🎯 Всего реферальных баллов: {total_referral_points:.2f}\n"
        f"📊 Среднее количество баллов на пользователя: {avg_referral_points:.2f}\n"
    )

    subscription_summary = "*Статистика подписок и платежей:*\n\n"
    subscription_users = data.get('subscriptions', {}).get('users', {})
    total_amount = data.get('all_users_total_amount', 0)
    transaction_count = 0
    paying_users = 0
    active_subscriptions = 0
    store_purchase_count = 0
    store_purchase_amount = 0
    if subscription_users:
        subscription_summary += "*Общая сумма платежей по пользователям:*\n\n"
        for idx, (user_id, user_data) in enumerate(subscription_users.items(), 1):
            user_total_amount = user_data.get('total_amount', 0)
            username = user_data.get('username', users_data.get(user_id, {}).get('username', user_id))
            if not username.startswith('@'):
                username = f"@{username}"
            subscription_summary += (
                f"👤 *№{idx}.* {escape_markdown(username)} (`{escape_markdown(user_id)}`): "
                f"{user_total_amount:.2f} руб.\n"
            )
            if user_total_amount > 0:
                paying_users += 1
            for plan in user_data.get('plans', []):
                end_date = datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M")
                if end_date >= now:
                    active_subscriptions += 1
                    break
            for purchase in user_data.get('store_purchases', []):
                store_purchase_count += 1
                store_purchase_amount += purchase.get('price', 0)
                if purchase.get('price', 0) > 0:
                    transaction_count += 1
            for plan in user_data.get('plans', []):
                if plan.get('price', 0) > 0 and plan.get('source') != 'store':
                    transaction_count += 1
        avg_payment = total_amount / paying_users if paying_users > 0 else 0
        subscription_summary += (
            f"\n\n*Общая статистика:*\n\n"
            f"💰 Итоговая сумма платежей: {total_amount:.2f} руб.\n"
            f"👥 Платящих пользователей: {paying_users}\n"
            f"📊 Средний чек: {avg_payment:.2f} руб.\n"
            f"📝 Всего транзакций: {transaction_count}\n"
            f"📈 Активных подписок: {active_subscriptions}\n"
            f"🛒 Покупок в магазине: {store_purchase_count}\n"
            f"💸 Сумма покупок в магазине: {store_purchase_amount:.2f} руб.\n"
        )
    else:
        subscription_summary += "❌ Данные о подписках отсутствуют!\n"

    promo_summary = "*Статистика промокодов:*\n\n"
    promo_codes = data.get('promo_codes', {})
    total_promo_codes = len(promo_codes)
    active_promo_codes = 0
    used_promo_codes = 0
    total_discount_amount = 0
    total_promo_uses = 0
    if promo_codes:
        for code, details in promo_codes.items():
            used = details.get('used', False)
            active = details.get('active', not used)
            if active and not used:
                active_promo_codes += 1
            elif used or not active:
                used_promo_codes += 1
            uses = len(details.get('used_by', []))
            total_promo_uses += uses
            for user_id, user_data in subscription_users.items():
                for promo in user_data.get('promo_usage_history', []):
                    if promo['promo_code'] == code:
                        discount = promo['discount']
                        for purchase in user_data.get('store_purchases', []):
                            if purchase.get('purchase_date') == promo['used_at']:
                                price = purchase.get('price', 0)
                                total_discount_amount += (discount / 100) * price
        promo_summary += (
            f"📝 Всего промокодов: {total_promo_codes}\n"
            f"✅ Активных промокодов: {active_promo_codes}\n"
            f"🛒 Использованных промокодов: {used_promo_codes}\n"
            f"🎟 Всего использований промокодов: {total_promo_uses}\n"
            f"💸 Общая сумма скидок: {total_discount_amount:.2f} руб.\n"
        )
    else:
        promo_summary += "❌ Данные о промокодах отсутствуют!\n"

    exchange_summary = "*Статистика обменов:*\n\n"
    total_exchanges = 0
    subscription_exchanges = 0
    discount_exchanges = 0
    feature_exchanges = 0
    total_points_spent = 0
    total_subscription_days = 0
    total_subscription_hours = 0

    if subscription_users:
        for user_id, user_data in subscription_users.items():
            for history in user_data.get('points_history', []):
                if history.get('action') == 'spent' and ('Обмен на' in history.get('reason', '') or 'обмен на' in history.get('reason', '').lower()):
                    total_exchanges += 1
                    points = history.get('points', 0)
                    total_points_spent += points
                    reason = history.get('reason', '').lower()
                    if any(unit in reason for unit in ['дн.', 'ч.', 'мин.']) and 'функци' not in reason:
                        subscription_exchanges += 1
                        time_match = re.search(r'(\d+\.?\d*)\s*дн\.?\s*(\d+\.?\d*)\s*ч\.?', reason)
                        if time_match:
                            days = float(time_match.group(1))
                            hours = float(time_match.group(2))
                            total_subscription_days += days
                            total_subscription_hours += hours
                        else:
                            hours_match = re.search(r'(\d+\.?\d*)\s*ч\.?', reason)
                            if hours_match:
                                hours = float(hours_match.group(1))
                                total_subscription_hours += hours
                            minutes_match = re.search(r'(\d+\.?\d*)\s*мин\.?', reason)
                            if minutes_match:
                                minutes = float(minutes_match.group(1))
                                total_subscription_hours += minutes / 60
                    elif 'скидки' in reason:
                        discount_exchanges += 1
                    elif 'функци' in reason:
                        feature_exchanges += 1

        total_subscription_days += total_subscription_hours // 24
        total_subscription_hours = total_subscription_hours % 24
        avg_points_per_exchange = total_points_spent / total_exchanges if total_exchanges > 0 else 0
        exchange_summary += (
            f"🔄 Всего обменов: {total_exchanges}\n"
            f"⏰ Обменов на подписку: {subscription_exchanges}\n"
            f"🎟 Обменов на скидки: {discount_exchanges}\n"
            f"⚙️ Обменов на функции: {feature_exchanges}\n"
            f"🎯 Потрачено баллов: {total_points_spent:.2f}\n"
            f"📊 Среднее количество баллов на обмен: {avg_points_per_exchange:.2f}\n"
            f"⏳ Общее время подписки: {format_number(total_subscription_days)} дн. {format_number(total_subscription_hours)} ч.\n"
        )
    else:
        exchange_summary += "❌ Данные об обменах отсутствуют!\n"

    summaries = [referral_summary, subscription_summary, promo_summary, exchange_summary]
    for summary in summaries:
        message_parts = split_message(summary)
        for part in message_parts:
            bot.send_message(message.chat.id, part, parse_mode="Markdown")

    manage_system(message)