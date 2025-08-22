from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, timedelta, InlineKeyboardMarkup, InlineKeyboardButton
from core.bot_instance import bot
from handlers.user.subscription.subscription_main import payments_function
from decorators.channel_subscription import CHANNEL_CHAT_ID
from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

def return_to_menu(message):
    from handlers.user.user_main_menu import return_to_menu as _f
    return _f(message)

def load_payment_data():
    from handlers.user.user_main_menu import load_payment_data as _f
    return _f()

def save_payments_data(data):
    from handlers.user.user_main_menu import save_payments_data as _f
    return _f(data)

def set_free_trial_period(user_id, days, source="default"):
    from handlers.user.user_main_menu import set_free_trial_period as _f
    return _f(user_id, days, source)

# ------------------------------------------------ ПОДПИСКА НА БОТА (рекламные каналы) -----------------------------------------

def is_user_subscribed(user_id, chat_id=CHANNEL_CHAT_ID):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['member', 'administrator', 'creator'] and member.status != 'kicked'
    except telebot.apihelper.ApiTelegramException as e:
        return False
    except Exception as e:
        return False

def is_channel_available(chat_id):
    try:
        chat = bot.get_chat(chat_id)
        return chat.type in ['channel', 'group', 'supergroup']
    except telebot.apihelper.ApiTelegramException as e:
        return False
    except Exception as e:
        return False

def background_subscription_check():
    while True:
        try:
            data = load_payment_data()
            for user_id in data['subscriptions']['users']:
                if not is_user_subscribed(int(user_id)):
                    pass
            time.sleep(3600)
        except Exception:
            time.sleep(2)
            continue

thread = threading.Thread(target=background_subscription_check, daemon=True)
thread.start()

@bot.message_handler(func=lambda message: message.text == "Рекламные каналы")
@rate_limit_with_captcha
def get_day_for_ad(message):
    if message.text == "Вернуться в подписку":
        payments_function(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    user_id = message.from_user.id
    data = load_payment_data()
    markup = InlineKeyboardMarkup()

    if 'ad_channels' not in data:
        bot.send_message(user_id, (
            "❌ Данные о рекламных каналах отсутствуют!\nПожалуйста, попробуйте позже или обратитесь к администратору...\n"
        ), parse_mode="Markdown")
        return

    user_data = data['subscriptions']['users'].get(str(user_id), {})
    subscribed_channels = user_data.get('ad_channels_subscribed', [])

    active_channels = False
    available_channels = False

    for chat_id, channel in data['ad_channels'].items():
        if not isinstance(channel, dict):
            channel = {'name': channel, 'active': False}
            data['ad_channels'][chat_id] = channel
            save_payments_data(data)  

        if channel.get('active', False) and is_channel_available(chat_id):
            active_channels = True
            if chat_id not in subscribed_channels:
                markup.add(InlineKeyboardButton(
                    f"Подписаться на {channel['name']}",
                    callback_data=f"subscribe_ad_{chat_id}"
                ))
                available_channels = True

    if not active_channels:
        bot.send_message(user_id, (
            "❌ На данный момент рекламные каналы недоступны!\nПожалуйста, попробуйте позже...\n"
        ), parse_mode="Markdown")
        return

    if not available_channels:
        bot.send_message(user_id, (
            "🎉 *Рекламных каналов больше нет!*\n\n"
            "✨ Вы уже подписались на все доступные каналы!\n"
            "⏳ Ожидайте новых через некоторое время...\n"
        ), parse_mode="Markdown")
        return

    bot.send_message(user_id, (
        "📢 *Подпишитесь на один из наших рекламных каналов!*\n\n"
        "✨ Получите *+1 день подписки* за подписку на любой канал!\n\n"
        "👉 Выберите канал ниже:"
    ), reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("subscribe_ad_"))
def check_ad_subscription(call):
    user_id = call.from_user.id
    selected_channel_id = call.data.replace("subscribe_ad_", "")
    data = load_payment_data()
    
    if selected_channel_id not in data['ad_channels'] or not data['ad_channels'][selected_channel_id]['active']:
        bot.send_message(call.message.chat.id, (
            "❌ Этот канал больше недоступен!\nПожалуйста, попробуйте позже или выберите другой канал...\n"
        ), parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Канал недоступен!")
        return
    
    channel_name = data['ad_channels'][selected_channel_id]['name']
    
    if not is_channel_available(selected_channel_id):
        bot.send_message(call.message.chat.id, (
            "❌ Канал временно недоступен!\nПожалуйста, попробуйте позже...\n"
        ), parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Канал недоступен!")
        return
    
    if not is_user_subscribed(user_id, selected_channel_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"Подписаться на {channel_name}", url=f"https://t.me/{channel_name.replace(' ', '')}"))
        markup.add(InlineKeyboardButton("Проверить подписку", callback_data=call.data))
        bot.send_message(call.message.chat.id, (
            f"⚠️ Вы еще не подписаны на *{channel_name}*! Подпишитесь и нажмите «проверить подписку»\n"
        ), reply_markup=markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Подпишитесь на канал!")
        return
    
    user_data = data['subscriptions']['users'].setdefault(str(user_id), {
        "plans": [],
        "total_amount": 0,
        "username": "неизвестный",
        "referral_points": 0,
        "free_feature_trials": {},
        "promo_usage_history": [],
        "referral_milestones": {},
        "points_history": [],
        "ad_channels_subscribed": [],
        "discount": 0,
        "applicable_category": None,
        "applicable_items": [],
        "discount_type": None
    })
    
    if selected_channel_id in user_data['ad_channels_subscribed']:
        bot.send_message(call.message.chat.id, (
            f"⚠️ Вы уже получили бонус за подписку на *{channel_name}*!\nВыберите другой канал для нового бонуса\n"
        ), parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Бонус уже получен!")
        return
    
    new_end = set_free_trial_period(user_id, 1, f"ad_bonus_{selected_channel_id}")
    user_plans = user_data.get('plans', [])
    if user_plans:
        latest_plan = max(user_plans, key=lambda p: datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M"))
        start_date = latest_plan['start_date']
    else:
        start_date = datetime.now().strftime("%d.%m.%Y в %H:%M")
    
    user_data['ad_channels_subscribed'].append(selected_channel_id)
    save_payments_data(data)
    
    bot.send_message(call.message.chat.id, (
        "🎉 *Поздравляем!*\n\n"
        f"✨ Вы получили *+1 день подписки* за подписку на *{channel_name}*!\n"
        f"🕒 *Начало:* {start_date}\n"
        f"⌛ *Конец:* {new_end.strftime('%d.%m.%Y в %H:%M')}\n\n"
        "😊 Вы можете подписаться на другие каналы, если они есть, для дополнительных бонусов!"
    ), parse_mode="Markdown")
    bot.answer_callback_query(call.id, "Спасибо за подписку!")