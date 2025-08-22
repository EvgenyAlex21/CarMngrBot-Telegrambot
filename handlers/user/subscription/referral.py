from core.imports import wraps, telebot, types, os, json, re, time, threading, ApiTelegramException, uuid, datetime, timedelta
from core.bot_instance import bot, BASE_DIR
from core.config import REFERRAL_BOT_URL
from handlers.user.subscription.subscription_main import payments_function
from handlers.user.subscription.points import escape_markdown
from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage
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

def load_users_data():
    from handlers.user.user_main_menu import load_users_data as _f
    return _f()

# ------------------------------------------------ ПОДПИСКА НА БОТА (реферальная система) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "Реферальная система")
@check_function_state_decorator('Реферальная система')
@track_usage('Реферальная система')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def refferal_payments_function(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Ваша ссылка', 'Ваши рефералы', 'Топ рефералов')
    markup.add('Вернуться в подписку')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите действие из реферальной системы:", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Вернуться в реферальную систему")
@check_function_state_decorator('Вернуться в реферальную систему')
@track_usage('Вернуться в реферальную систему')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_referral_menu(message):
    refferal_payments_function(message)

def send_long_message(chat_id, text, parse_mode="Markdown"):
    max_length = 4000  
    
    if len(text) <= max_length:
        bot.send_message(chat_id, text, parse_mode=parse_mode)
        return
    
    parts = []
    current_part = ""
    
    for line in text.split('\n'):
        if len(current_part) + len(line) + 1 > max_length:
            parts.append(current_part)
            current_part = line + '\n'
        else:
            current_part += line + '\n'
    
    if current_part:
        parts.append(current_part)
    
    for part in parts:
        bot.send_message(chat_id, part, parse_mode=parse_mode)
        time.sleep(0.1)  

def create_referral_link(user_id):
    data = load_payment_data()
    referral_code = data['referrals']['links'].get(str(user_id), str(uuid.uuid4()))
    data['referrals']['links'][str(user_id)] = referral_code
    save_payments_data(data)
    return f"{REFERRAL_BOT_URL}?start={referral_code}"

def track_referral_activity(referral_code, new_user_id):
    data = load_payment_data()
    referrer_id = next((uid for uid, code in data['referrals']['links'].items() if code == referral_code), None)
    
    if (referrer_id and referrer_id != str(new_user_id) and 
        str(new_user_id) not in data['referrals']['stats'].get(referrer_id, [])):
        data['referrals']['stats'].setdefault(referrer_id, []).append(str(new_user_id))
        now = datetime.now().strftime("%d.%m.%Y в %H:%M")
        
        referral_count = len(data['referrals']['stats'][referrer_id])
        data['subscriptions']['users'].setdefault(referrer_id, {}).setdefault('referral_milestones', {})
        if str(referral_count) not in data['subscriptions']['users'][referrer_id]['referral_milestones']:
            data['subscriptions']['users'][referrer_id]['referral_milestones'][str(referral_count)] = now
        
        save_payments_data(data)
        return referrer_id
    return None

def apply_referral_bonus(referrer_id):
    data = load_payment_data()
    referrer_id_str = str(referrer_id)
    
    if referrer_id_str not in data['referrals']['stats']:
        data['referrals']['stats'][referrer_id_str] = []
    
    referral_count = len(data['referrals']['stats'][referrer_id_str])
    
    points = 0
    if referral_count <= 4:
        points = 1.0
    elif 5 <= referral_count <= 7:
        points = 1.5
    elif 8 <= referral_count <= 10:
        points = 1.0
    else: 
        points = 1.5
    
    data['subscriptions']['users'][referrer_id_str]['referral_points'] += points
    data['subscriptions']['users'][referrer_id_str]['points_history'].append({
        "action": "earned",
        "points": points,
        "reason": f"Реферал №{referral_count}",
        "date": datetime.now().strftime("%d.%m.%Y в %H:%M")
    })
    
    bonus_days = 0
    discount = 0
    if referral_count == 1:
        bonus_days = 1
    elif referral_count == 5:
        bonus_days = 5
    elif referral_count == 10:
        bonus_days = 10
        discount = 10
    
    start_date = None
    end_date_str = None
    if bonus_days > 0:
        latest_end = max([datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") 
                         for p in data['subscriptions']['users'].get(referrer_id_str, {}).get('plans', [])] 
                         or [datetime.now()])
        new_end = latest_end + timedelta(days=bonus_days)
        start_date = latest_end.strftime("%d.%m.%Y в %H:%M") 
        end_date_str = new_end.strftime("%d.%m.%Y в %H:%M")  
        data['subscriptions']['users'][referrer_id_str]['plans'].append({
            "plan_name": "referral",
            "start_date": start_date,
            "end_date": end_date_str,
            "price": 0,
            "source": "referral"
        })
    
    if discount > 0:
        users_data = load_users_data()
        users_data[referrer_id_str]['discount'] = max(users_data.get(referrer_id_str, {}).get('discount', 0), discount)
        users_data[referrer_id_str]['discount_type'] = "referral"
    
    save_payments_data(data)
    
    try:
        _p = float(points)
    except (TypeError, ValueError):
        _p = points
    points_str = f"{int(_p)}" if isinstance(_p, float) and _p.is_integer() else (f"{_p:.2f}" if isinstance(_p, (int, float)) else str(_p))
    
    message = f"🎉 *Новый реферал!*\n\n✨ Вы получили +{points_str} балл{'а' if points != 1 else ''} за приглашение пользователя!\n\n"
    if bonus_days > 0:
        message += (
            f"📅 Получено: +{bonus_days} день подписки!\n"
            f"🕒 *Начало:* {start_date}\n"
            f"⌛ *Конец:* {end_date_str}\n\n"
        )
    if discount > 0:
        message += f"🎁 Получено: *{discount}% скидки*!\n\n"
    message += f"🔢 Всего рефералов: {referral_count}\n"
    
    bot.send_message(referrer_id, message, parse_mode="Markdown")

# ------------------------------------------------ ПОДПИСКА НА БОТА (ваша ссылка) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "Ваша ссылка")
@check_function_state_decorator('Ваша ссылка')
@track_usage('Ваша ссылка')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_referral_link_message(message):
    user_id = message.from_user.id
    referral_link = create_referral_link(user_id)
    bot.send_message(message.chat.id, (
        f"🔗 *Ваша реферальная ссылка:*  \n"
        f"[{referral_link}]({referral_link})  \n\n"
        f"🤝 *Приглашайте друзей и получайте бонусы:*  \n\n"
        f"- *1 реферал = +1 день подписки + 1 балл*  \n"
        f"- *5 рефералов = +5 дней подписки + 1.5 балла за каждого (5–7)*  \n"
        f"- *10 рефералов = +10 дней подписки + 10% скидка + 1 балл за 8–10, 1.5 за 11+*  \n"
        f"- Если реферал купит подписку:  \n"
        f"  - на 7 дней: *+1 день*  \n"
        f"  - на 30 дней: *+3 дня*  \n"
        f"  - на 365 дней: *+7 дней*  \n\n"
        f"🎁 *Что получает приглашённый:*  \n\n"
        f"- Как новому пользователю: *3 дня пробного периода*  \n"
        f"- За регистрацию по вашей ссылке: *+1 день подписки*  \n"
        f"Итого: *4 дня* для старта!  \n\n"
        f"🚀 Делитесь ссылкой и наслаждайтесь премиум-функциями дольше!\n"
    ), parse_mode="Markdown")

# ------------------------------------------------ ПОДПИСКА НА БОТА (ваши рефералы) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "Ваши рефералы")
@check_function_state_decorator('Ваши рефералы')
@track_usage('Ваши рефералы')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_referrals_and_bonuses(message):
    user_id = message.from_user.id
    data = load_payment_data()
    users_data = load_users_data()
    referrals = list(set(data['referrals']['stats'].get(str(user_id), [])))
    points = data['subscriptions']['users'].get(str(user_id), {}).get('referral_points', 0)
    discount = users_data.get(str(user_id), {}).get('discount', 0)

    if not referrals:
        bot.send_message(message.chat.id, (
            "🙁 У вас пока нет рефералов и бонусов!\n\n"
            "🤝 Приглашайте друзей и зарабатывайте дополнительные дни и баллы для использования!\n\n"
        ), parse_mode="Markdown")
        return

    referral_count = len(referrals)
    total_bonus_days = 0
    total_bonus_points = 0
    total_discount = 0

    for i in range(1, referral_count + 1):
        if i == 1:
            total_bonus_days += 1
        elif i == 5:
            total_bonus_days += 5
        elif i == 10:
            total_bonus_days += 10
            total_discount = 10

    for i in range(1, referral_count + 1):
        if i <= 4:
            total_bonus_points += 1.0
        elif 5 <= i <= 7:
            total_bonus_points += 1.5
        elif 8 <= i <= 10:
            total_bonus_points += 1.0
        else:  
            total_bonus_points += 1.5

    total_purchase_bonus_days = 0
    referral_purchase_bonuses = {} 
    for referral_id in referrals:
        referral_plans = data['subscriptions']['users'].get(referral_id, {}).get('plans', [])
        purchase_bonus_days = 0
        for plan in referral_plans:
            if plan.get('source') == "user": 
                duration = (datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M") - 
                           datetime.strptime(plan['start_date'], "%d.%m.%Y в %H:%M")).days
                if duration >= 365:
                    purchase_bonus_days += 7
                elif duration >= 30:
                    purchase_bonus_days += 3
                elif duration >= 7:
                    purchase_bonus_days += 1
        referral_purchase_bonuses[referral_id] = purchase_bonus_days
        total_purchase_bonus_days += purchase_bonus_days

    total_bonus_days += total_purchase_bonus_days

    try:
        _p2 = float(points)
    except (TypeError, ValueError):
        _p2 = points
    points_str = f"{int(_p2)}" if isinstance(_p2, float) and _p2.is_integer() else (f"{_p2:.2f}" if isinstance(_p2, (int, float)) else str(_p2))

    message_text = (
        f"🤝 *Ваши рефералы:*\n\n"
        f"👥 *Всего рефералов:* {len(referrals)} человек\n"
        f"🎁 *Текущие баллы:* {points_str}\n"
        f"📅 *Общее кол-во бонусных дней:* {total_bonus_days}\n"
        f"🏷️ *Текущая скидка:* {total_discount}%\n\n"
    )

    for index, referral_id in enumerate(referrals, start=1):
        referral_data = data['subscriptions']['users'].get(referral_id, {})
        referral_username = escape_markdown(referral_data.get('username', 'Неизвестно'))
        join_date = users_data.get(referral_id, {}).get('join_date', 'Неизвестно')
        
        referral_index = index  
        registration_bonus_days = 0
        registration_bonus_points = 0
        if referral_index == 1:
            registration_bonus_days = 1
            registration_bonus_points = 1.0
        elif referral_index == 5:
            registration_bonus_days = 5
            registration_bonus_points = 1.5
        elif referral_index == 10:
            registration_bonus_days = 10
            registration_bonus_points = 1.0
        elif 1 <= referral_index <= 4:
            registration_bonus_points = 1.0
        elif 5 <= referral_index <= 7:
            registration_bonus_points = 1.5
        elif 8 <= referral_index <= 10:
            registration_bonus_points = 1.0
        else:  
            registration_bonus_points = 1.5

        try:
            _rb = float(registration_bonus_points)
        except (TypeError, ValueError):
            _rb = registration_bonus_points
        registration_bonus_points_str = f"{int(_rb)}" if isinstance(_rb, float) and _rb.is_integer() else (f"{_rb:.2f}" if isinstance(_rb, (int, float)) else str(_rb))

        referral_bonus_days = sum((datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M") - 
                                  datetime.strptime(p['start_date'], "%d.%m.%Y в %H:%M")).days 
                                  for p in referral_data.get('plans', []) if p.get('source') == "referral")

        purchase_bonus_days = referral_purchase_bonuses.get(referral_id, 0)

        message_text += (
            f"✅ *№{index}. Пользователь:* {referral_username}\n"
            f"👤 *ID пользователя:* `{referral_id}`\n"
            f"📅 *Дата вступления:* {join_date}\n"
        )

        message_text += f"🎁 *Ваш бонус за регистрацию:*\n"
        if registration_bonus_days > 0:
            message_text += f"  • +{registration_bonus_days} дней подписки\n"
        message_text += f"  • +{registration_bonus_points_str} баллов\n"

        if purchase_bonus_days > 0:
            message_text += f"🎁 *Ваш бонус за покупки реферала:*\n"
            message_text += f"  • +{purchase_bonus_days} дней подписки\n"

        message_text += f"📅 *Бонус реферала:* {referral_bonus_days} дней\n\n"

    send_long_message(message.chat.id, message_text)

# ------------------------------------------------ ПОДПИСКА НА БОТА (топ рефералов) -----------------------------------------

@bot.message_handler(func=lambda message: message.text == "Топ рефералов")
@check_function_state_decorator('Топ рефералов')
@track_usage('Топ рефералов')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_referral_leaderboard(message):
    user_id = str(message.from_user.id) 
    data = load_payment_data()
    
    leaderboard_data = []
    for uid, refs in data['referrals']['stats'].items():
        unique_refs = len(set(refs))
        milestone_date = data['subscriptions']['users'].get(uid, {}).get('referral_milestones', {}).get(str(unique_refs), "01.01.2025 в 00:00")
        leaderboard_data.append((uid, unique_refs, milestone_date))
    
    leaderboard = sorted(leaderboard_data, key=lambda x: (-x[1], x[2]))
    
    if not leaderboard:
        bot.send_message(message.chat.id, (
            "🏆 Топ рефералов еще не сформирован...\n\n"
            "🚀 Приглашайте друзей, чтобы попасть в топ!"
        ), parse_mode="Markdown")
        return
        
    message_text = "*🏆 Топ 10 рефералов:*\n\n"
    for idx, (uid, ref_count, _) in enumerate(leaderboard[:10], 1):
        message_text += f"👤 №{idx}. `{uid}`: {ref_count} рефералов\n"
    
    leader_history = data['referrals']['leaderboard_history']
    if leader_history['current_leader']:
        days_at_top = leader_history['days_at_top']
        message_text += (
            f"\n👑 *Текущий лидер:* `{leader_history['current_leader']}`\n"
            f"⏳ *Дней на вершине:* {days_at_top}\n"
        )
    
    now = datetime.now()
    top_formed_date = data['referrals'].get('top_formed_date')
    last_bonus_date = data['referrals'].get('last_top10_bonus')
    
    if top_formed_date:
        if last_bonus_date:
            last_bonus_dt = datetime.strptime(last_bonus_date, "%d.%m.%Y в %H:%M")
            next_bonus_date = last_bonus_dt + timedelta(days=30)
        else:
            top_formed_dt = datetime.strptime(top_formed_date, "%d.%m.%Y в %H:%M")
            next_bonus_date = top_formed_dt + timedelta(days=30)
        
        days_until_next_bonus = (next_bonus_date - now).days
        if days_until_next_bonus >= 0:
            message_text += f"\n📅 *Следующее начисление бонусов через:* {days_until_next_bonus} дней\n"
        else:
            message_text += "\n📅 *Начисление бонусов скоро!*\n"
    
    user_position = None
    user_ref_count = 0
    for idx, (uid, ref_count, _) in enumerate(leaderboard, 1):
        if uid == user_id:
            user_position = idx
            user_ref_count = ref_count
            break
    
    message_text += "\n"
    if user_position:
        position_text = f"📍 *Ваша позиция* (`{user_id}`)*:* \n      Вы №{user_position} с {user_ref_count} рефералами"
        message_text += position_text
    else:
        position_text = f"📍 *Ваша позиция* (`{user_id}`)*:* \n      Вы пока не в рейтинге!"
        message_text += position_text
    
    send_long_message(message.chat.id, message_text)

BLOCKED_USERS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'bloked_bot', 'blocked_bot_users.json')

def load_blocked_users():
    if os.path.exists(BLOCKED_USERS_FILE):
        with open(BLOCKED_USERS_FILE, 'r') as file:
            return json.load(file)
    return []

def save_blocked_users(blocked_users):
    with open(BLOCKED_USERS_FILE, 'w') as file:
        json.dump(blocked_users, file, indent=4)

def safe_send_message(user_id, text, parse_mode=None):
    try:
        bot.send_message(user_id, text, parse_mode=parse_mode)
    except ApiTelegramException as e:
        if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
            blocked_users = load_blocked_users()
            if user_id not in blocked_users:
                blocked_users.append(user_id)
                save_blocked_users(blocked_users)
        else:
            raise e

def check_monthly_leader_bonus():
    while True:
        try:
            data = load_payment_data()
            
            if 'referrals' not in data or 'stats' not in data['referrals']:
                data['referrals'] = {
                    'links': {},
                    'stats': {},
                    'bonuses': {},
                    'leaderboard_history': {
                        'current_leader': None,
                        'leader_start_date': None,
                        'days_at_top': 0
                    },
                    'top_formed_date': None,
                    'last_top10_bonus': None
                }
                save_payments_data(data)
                time.sleep(86400)
                continue
            
            leaderboard_data = []
            for uid, refs in data['referrals']['stats'].items():
                ref_count = len(set(refs))
                milestone_date = data['subscriptions']['users'].get(uid, {}).get('referral_milestones', {}).get(str(ref_count), "01.01.2025 в 00:00")
                leaderboard_data.append((uid, ref_count, milestone_date))
            
            if not leaderboard_data:
                data['referrals']['top_formed_date'] = None
                save_payments_data(data)
                time.sleep(86400)
                continue
            
            now = datetime.now()
            
            if data['referrals'].get('top_formed_date') is None:
                data['referrals']['top_formed_date'] = now.strftime("%d.%m.%Y в %H:%M")
                save_payments_data(data)
            
            leaderboard = sorted(leaderboard_data, key=lambda x: (-x[1], x[2]))
            current_top_user, top_referrals, _ = leaderboard[0]
            leader_history = data['referrals']['leaderboard_history']
            current_leader = leader_history.get('current_leader')
            
            if current_leader != current_top_user:
                leader_history['current_leader'] = current_top_user
                leader_history['leader_start_date'] = now.strftime("%d.%m.%Y в %H:%M")
                leader_history['days_at_top'] = 1
            else:
                if leader_start_date := leader_history.get('leader_start_date'):
                    start_date = datetime.strptime(leader_start_date, "%d.%m.%Y в %H:%M")
                    days_at_top = (now - start_date).days + 1
                    leader_history['days_at_top'] = days_at_top
            
            top_formed_date = data['referrals'].get('top_formed_date')
            if top_formed_date:
                top_formed_dt = datetime.strptime(top_formed_date, "%d.%m.%Y в %H:%M")
                last_bonus_date = data['referrals'].get('last_top10_bonus')
                
                if last_bonus_date is None:
                    days_since_formation = (now - top_formed_dt).days
                    if days_since_formation >= 30:
                        for idx, (uid, ref_count, _) in enumerate(leaderboard[:10], 1):
                            data['subscriptions']['users'].setdefault(uid, {}).setdefault('referral_points', 0)
                            data['subscriptions']['users'][uid]['referral_points'] += 1
                            data['subscriptions']['users'][uid].setdefault('points_history', []).append({
                                "action": "earned",
                                "points": 1,
                                "reason": "Топ-10 рефералов за месяц",
                                "date": now.strftime("%d.%m.%Y в %H:%M")
                            })
                            
                            bonus_days = {1: 3, 2: 2, 3: 1}.get(idx, 0)
                            if bonus_days > 0:
                                new_end = set_free_trial_period(int(uid), bonus_days, f"leaderboard_top_{idx}")
                                user_plans = data['subscriptions']['users'].get(uid, {}).get('plans', [])
                                latest_plan = max(user_plans, key=lambda p: datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M"))
                                start_date = latest_plan['start_date']
                                safe_send_message(uid, (
                                    f"🎉 *Поздравляем!*\n\n"
                                    f"✨ Вы на {idx}-м месте в топе рефералов!\n\n"
                                    f"🎁 Вы получили *+{bonus_days} дней* к использованию!\n"
                                    f"🕒 *Начало:* {start_date}\n"
                                    f"⌛ *Конец:* {new_end.strftime('%d.%m.%Y в %H:%M')}\n\n"
                                    "🚀 Продолжайте приглашать друзей!"
                                ), parse_mode="Markdown")
                            
                            safe_send_message(uid, (
                                "🎉 *Вы в ТОП-10 рефералов месяца!*\n"
                                "✨ Получено *+1 балл*! Продолжайте приглашать!"
                            ), parse_mode="Markdown")
                        
                        data['referrals']['last_top10_bonus'] = now.strftime("%d.%m.%Y в %H:%M")
                else:
                    try:
                        last_bonus_dt = datetime.strptime(last_bonus_date, "%d.%m.%Y в %H:%M")
                    except ValueError:
                        last_bonus_dt = datetime.strptime(f"{last_bonus_date} в 00:00", "%d.%m.%Y в %H:%M")
                        data['referrals']['last_top10_bonus'] = last_bonus_dt.strftime("%d.%m.%Y в %H:%M")
                    
                    days_since_last_bonus = (now - last_bonus_dt).days
                    if days_since_last_bonus >= 30:
                        for idx, (uid, ref_count, _) in enumerate(leaderboard[:10], 1):
                            data['subscriptions']['users'].setdefault(uid, {}).setdefault('referral_points', 0)
                            data['subscriptions']['users'][uid]['referral_points'] += 1
                            data['subscriptions']['users'][uid].setdefault('points_history', []).append({
                                "action": "earned",
                                "points": 1,
                                "reason": "Топ-10 рефералов за месяц",
                                "date": now.strftime("%d.%m.%Y в %H:%M")
                            })
                            
                            bonus_days = {1: 3, 2: 2, 3: 1}.get(idx, 0)
                            if bonus_days > 0:
                                new_end = set_free_trial_period(int(uid), bonus_days, f"leaderboard_top_{idx}")
                                user_plans = data['subscriptions']['users'].get(uid, {}).get('plans', [])
                                latest_plan = max(user_plans, key=lambda p: datetime.strptime(p['end_date'], "%d.%m.%Y в %H:%M"))
                                start_date = latest_plan['start_date']
                                safe_send_message(uid, (
                                    f"🎉 *Поздравляем!*\n\n"
                                    f"✨ Вы на {idx}-м месте в топе рефералов!\n\n"
                                    f"🎁 Вы получили *+{bonus_days} дней* к использованию!\n"
                                    f"🕒 *Начало:* {start_date}\n"
                                    f"⌛ *Конец:* {new_end.strftime('%d.%m.%Y в %H:%M')}\n\n"
                                    "🚀 Продолжайте приглашать друзей!"
                                ), parse_mode="Markdown")
                            
                            safe_send_message(uid, (
                                "🎉 *Вы в ТОП-10 рефералов месяца!*\n"
                                "✨ Получено *+1 балл*! Продолжайте приглашать!"
                            ), parse_mode="Markdown")
                        
                        data['referrals']['last_top10_bonus'] = now.strftime("%d.%m.%Y в %H:%M")
            
            save_payments_data(data)
        
        except Exception as e:
            time.sleep(60)
        
        time.sleep(86400)

leader_thread = threading.Thread(target=check_monthly_leader_bonus, daemon=True)
leader_thread.start()