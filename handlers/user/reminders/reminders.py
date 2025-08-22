from core.imports import wraps, telebot, types, os, json, re, time, threading, datetime, timedelta, ApiTelegramException
from core.bot_instance import bot, BASE_DIR
from handlers.user.user_main_menu import return_to_menu
from decorators.blocked_user import load_blocked_users, save_blocked_users
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, track_usage, check_function_state_decorator, check_subscription
)

# --------------------------------------------------- НАПОМИНАНИЯ ---------------------------------------------------------

DB_PATH = os.path.join(BASE_DIR, 'data', 'user', 'reminders', 'reminders.json')

def load_data():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if not os.path.exists(DB_PATH):
        with open(DB_PATH, 'w', encoding='utf-8') as file:
            json.dump({"users": {}}, file, indent=4, ensure_ascii=False)
    with open(DB_PATH, 'r', encoding='utf-8') as file:
        data = json.load(file)
    if 'users' not in data:
        data['users'] = {}
    return data

def save_data(data):
    if 'users' not in data:
        data['users'] = {}
    with open(DB_PATH, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def send_reminders():
    data = load_data()
    blocked_users = load_blocked_users()
    current_time = datetime.now()

    for user_id, user_data in data["users"].items():
        if user_id in blocked_users:
            continue
        reminders = user_data.get("reminders", [])
        for reminder in reminders:
            reminder_type = reminder.get("type")
            reminder_datetime = datetime.strptime(reminder["date"] + " " + reminder["time"], "%d.%m.%Y %H:%M")
            if reminder["status"] == "active":
                try:
                    if reminder_type == "один раз":
                        if reminder_datetime <= current_time:
                            bot.send_message(user_id, f"⏰ *У вас напоминание!*\n\n📝 Название: {reminder['title'].lower()} \n📅 Дата: {reminder['date']} \n🕒 Время: {reminder['time']} \n🔖 Тип: {reminder['type']}", parse_mode="Markdown")
                            reminder["status"] = "expired"
                    elif reminder_type == "ежедневно":
                        if current_time.date() == reminder_datetime.date() and current_time.time() >= reminder_datetime.time():
                            bot.send_message(user_id, f"⏰ *У вас напоминание!*\n\n📝 Название: {reminder['title'].lower()} \n📅 Дата: {reminder['date']} \n🕒 Время: {reminder['time']} \n🔖 Тип: {reminder['type']}", parse_mode="Markdown")
                            reminder["date"] = (reminder_datetime + timedelta(days=1)).strftime("%d.%m.%Y")
                    elif reminder_type == "еженедельно":
                        if current_time.date() == reminder_datetime.date() and current_time.time() >= reminder_datetime.time():
                            bot.send_message(user_id, f"⏰ *У вас напоминание!*\n\n📝 Название: {reminder['title'].lower()} \n📅 Дата: {reminder['date']} \n🕒 Время: {reminder['time']} \n🔖 Тип: {reminder['type']}", parse_mode="Markdown")
                            reminder["date"] = (reminder_datetime + timedelta(weeks=1)).strftime("%d.%m.%Y")
                    elif reminder_type == "ежемесячно":
                        if current_time.date() == reminder_datetime.date() and current_time.time() >= reminder_datetime.time():
                            bot.send_message(user_id, f"⏰ *У вас напоминание!*\n\n📝 Название: {reminder['title'].lower()} \n📅 Дата: {reminder['date']} \n🕒 Время: {reminder['time']} \n🔖 Тип: {reminder['type']}", parse_mode="Markdown")
                            next_month = reminder_datetime.month % 12 + 1
                            next_year = reminder_datetime.year + (reminder_datetime.month // 12)
                            reminder["date"] = reminder_datetime.replace(day=reminder_datetime.day, month=next_month, year=next_year).strftime("%d.%m.%Y")
                except ApiTelegramException as e:
                    if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                        if user_id not in blocked_users:
                            blocked_users.append(user_id)
                            save_blocked_users(blocked_users)
                    else:
                        raise e
        save_data(data)

def run_scheduler():
    while True:
        send_reminders()
        time.sleep(15)

threading.Thread(target=run_scheduler, daemon=True).start()

@bot.message_handler(func=lambda message: message.text == "Напоминания")
@check_function_state_decorator('Напоминания')
@track_usage('Напоминания')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def reminders_menu(message, show_description=True):
    description = (
        "ℹ️ *Краткая справка для напоминаний*\n\n"
        "📌 *Добавление напоминаний:*\n"
        "Добавьте ваше напоминание, указав - *название, тип, дата и время*\n\n"
        "📌 *Просмотр напоминаний:*\n"
        "Вы можете посмотреть свои напоминания\n\n"
        "📌 *Удаление напоминаний:*\n"
        "Вы можете удалить напоминания, если они вам не нужны"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Добавить напоминание', 'Посмотреть напоминания', 'Удалить напоминания')
    markup.add('В главное меню')
    if show_description:
        bot.send_message(message.chat.id, description, parse_mode="Markdown")
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Вернуться в меню напоминаний")
@check_function_state_decorator('Вернуться в меню напоминаний')
@track_usage('Вернуться в меню напоминаний')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_reminders_menu(message):
    reminders_menu(message, show_description=False)

# -------------------------------------------- НАПОМИНАНИЯ (добавить напоминание) ----------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Добавить напоминание")
@check_function_state_decorator('Добавить напоминание')
@track_usage('Добавить напоминание')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def add_reminder(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, "Введите название напоминания:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_title_step)

@text_only_handler
def process_title_step(message):
    user_id = str(message.from_user.id)
    data = load_data()

    if message.text == "Вернуться в меню напоминаний":
        reminders_menu(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    if user_id not in data["users"]:
        data["users"][user_id] = {"reminders": []}
    reminder = {"title": message.text}
    data["users"][user_id]["current_reminder"] = reminder
    save_data(data)
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Один раз', 'Ежедневно')
    markup.add('Еженедельно', 'Ежемесячно')
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, "Выберите тип напоминания:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_type_step)

@text_only_handler
def process_type_step(message):
    user_id = str(message.from_user.id)
    data = load_data()
    reminder = data["users"][user_id]["current_reminder"]

    if message.text == "Вернуться в меню напоминаний":
        reminders_menu(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    reminder_type = message.text.lower()
    if reminder_type in ["ежедневно", "еженедельно", "ежемесячно", "один раз"]:
        reminder["type"] = reminder_type
    else:
        msg = bot.send_message(message.chat.id, "Неверный тип!\nВыберите из предложенных")
        bot.register_next_step_handler(msg, process_type_step)
        return
    save_data(data)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, "Введите дату напоминания в формате ДД.ММ.ГГГГ:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_date_step_for_repairs)

@text_only_handler
def process_date_step_for_repairs(message):
    user_id = str(message.from_user.id)
    data = load_data()
    reminder = data["users"][user_id]["current_reminder"]

    if message.text == "Вернуться в меню напоминаний":
        reminders_menu(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    date_input = message.text
    if re.match(r"^\d{2}\.\d{2}\.\d{4}$", date_input):
        try:
            day, month, year = map(int, date_input.split('.'))
            if 1 <= month <= 12 and 1 <= day <= 31 and 2000 <= year <= 3000:
                reminder_date = datetime.strptime(date_input, "%d.%m.%Y")
                current_date = datetime.now()
                if reminder_date.date() >= current_date.date():
                    reminder["date"] = date_input
                else:
                    raise ValueError("Дата не может быть меньше текущей")
            else:
                raise ValueError
        except ValueError as e:
            msg = bot.send_message(message.chat.id, f"Произошла ошибка: {e}!\nВведите дату в формате ДД.ММ.ГГГГ")
            bot.register_next_step_handler(msg, process_date_step_for_repairs)
            return
    else:
        msg = bot.send_message(message.chat.id, "Неверный формат!\nВведите дату в формате ДД.ММ.ГГГГ")
        bot.register_next_step_handler(msg, process_date_step_for_repairs)
        return
    save_data(data)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, "Введите время в формате ЧЧ:ММ:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_time_step)

@text_only_handler
def process_time_step(message):
    user_id = str(message.from_user.id)
    data = load_data()
    reminder = data["users"][user_id]["current_reminder"]

    if message.text == "Вернуться в меню напоминаний":
        reminders_menu(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    time_input = message.text
    if re.match(r"^\d{2}:\d{2}$", time_input):
        try:
            hour, minute = map(int, time_input.split(':'))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                reminder_time = datetime.strptime(time_input, "%H:%M").time()
                current_time = datetime.now().time()
                reminder_date = datetime.strptime(reminder["date"], "%d.%m.%Y").date()
                current_date = datetime.now().date()
                if reminder_date > current_date or (reminder_date == current_date and reminder_time >= current_time):
                    reminder["time"] = time_input
                    reminder["status"] = "active"
                else:
                    raise ValueError("Время не может быть меньше текущего")
            else:
                raise ValueError
        except ValueError as e:
            msg = bot.send_message(message.chat.id, f"Произошла ошибка: {e}!\nВведите время в формате ЧЧ:ММ")
            bot.register_next_step_handler(msg, process_time_step)
            return
    else:
        msg = bot.send_message(message.chat.id, "Неверный формат!\nВведите время в формате ЧЧ:ММ")
        bot.register_next_step_handler(msg, process_time_step)
        return
    data["users"][user_id]["reminders"].append(reminder)
    del data["users"][user_id]["current_reminder"]
    save_data(data)
    bot.send_message(message.chat.id, "✅ Напоминание добавлено!")
    new_message_3 = message
    new_message_3.text = "Напоминания"  
    reminders_menu(new_message_3, show_description=False)

# -------------------------------------------- НАПОМИНАНИЯ (посмотреть напоминания) ----------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Посмотреть напоминания")
@check_function_state_decorator('Посмотреть напоминания')
@track_usage('Посмотреть напоминания')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_reminders(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Активные', 'Истекшие')
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')    
    bot.send_message(message.chat.id, "Выберите тип напоминаний:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ['Активные', 'Истекшие'])
@check_function_state_decorator('Активные')
@check_function_state_decorator('Истекшие')
@track_usage('Активные')
@track_usage('Истекшие')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_reminders_by_status(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Один раз', 'Ежедневно')
    markup.add('Еженедельно', 'Ежемесячно')
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')
    status = message.text.lower()
    bot.send_message(message.chat.id, f"Выберите тип {status} напоминаний:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda msg: view_reminders_by_type(msg, status))

def view_reminders_by_type(message, status):
    user_id = str(message.from_user.id)
    data = load_data()
    reminders = data["users"].get(user_id, {}).get("reminders", [])
    current_date = datetime.now()
    reminder_type = message.text.lower()

    if message.text == "Вернуться в меню напоминаний":
        reminders_menu(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    if reminder_type not in ["один раз", "ежедневно", "еженедельно", "ежемесячно"]:
        bot.send_message(message.chat.id, "Неверный тип!\nВыберите из предложенных")
        view_reminders(message)
        return
    filtered_reminders = []
    for reminder in reminders:
        reminder_datetime = datetime.strptime(reminder["date"] + ' ' + reminder["time"], "%d.%m.%Y %H:%M")
        if reminder["type"] == reminder_type and reminder["status"] == ("active" if status == "активные" else "expired"):
            if status == "активные":
                if reminder_type == "один раз" and reminder_datetime >= current_date:
                    filtered_reminders.append(reminder)
                elif reminder_type == "ежедневно" and reminder_datetime.date() >= current_date.date():
                    filtered_reminders.append(reminder)
                elif reminder_type == "еженедельно" and reminder_datetime.weekday() == current_date.weekday():
                    filtered_reminders.append(reminder)
                elif reminder_type == "ежемесячно" and reminder_datetime.day == current_date.day:
                    filtered_reminders.append(reminder)
            else:
                filtered_reminders.append(reminder)
    if filtered_reminders:
        response = f"*{status.capitalize()} напоминания ({reminder_type}):*\n\n"
        for i, reminder in enumerate(filtered_reminders, 1):
            response += (
                f"\n{'⭐' if status == 'активные' else '❌'} №{i} {'⭐' if status == 'активные' else '❌'}\n\n"
                f"📝 Название: {reminder['title'].lower()}\n"
                f"📅 Дата: {reminder['date']}\n"
                f"🕒 Время: {reminder['time']}\n"
                f"✅ Статус: {'активное' if status == 'активные' else 'истекло'}\n"
                f"🔖 Тип: {reminder['type']}\n\n"
            )
    else:
        response = f"*{status.capitalize()} напоминания ({reminder_type}):*\n\n❌ Нет {status} напоминаний!"
    bot.send_message(message.chat.id, response, parse_mode="Markdown")
    view_reminders(message)

# -------------------------------------------- НАПОМИНАНИЯ (удалить напоминания) ----------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Удалить напоминания")
@check_function_state_decorator('Удалить напоминания')
@track_usage('Удалить напоминания')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_reminder(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Del Активные', 'Del Истекшие')
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите тип напоминаний для удаления:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ['Del Активные', 'Del Истекшие'])
@check_function_state_decorator('Del Активные')
@check_function_state_decorator('Del Истекшие')
@track_usage('Del Активные')
@track_usage('Del Истекшие')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_reminders_by_status(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Del Один раз', 'Del Ежедневно')
    markup.add('Del Еженедельно', 'Del Ежемесячно')
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')
    status = message.text.replace('Del ', '').lower()
    bot.send_message(message.chat.id, f"Выберите тип {status} напоминаний для удаления:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda msg: delete_reminders_by_type(msg, status))

@bot.message_handler(func=lambda message: message.text in ['Del Один раз', 'Del Ежедневно', 'Del Еженедельно', 'Del Ежемесячно'])
@check_function_state_decorator('Del Один раз')
@check_function_state_decorator('Del Ежедневно')
@check_function_state_decorator('Del Еженедельно')
@check_function_state_decorator('Del Ежемесячно')
@track_usage('Del Один раз')
@track_usage('Del Ежедневно')
@track_usage('Del Еженедельно')
@track_usage('Del Ежемесячно')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_reminders_by_type(message, status):
    user_id = str(message.from_user.id)
    data = load_data()
    reminders = data["users"].get(user_id, {}).get("reminders", [])
    reminder_type = message.text.replace('Del ', '').lower()

    if message.text == "Вернуться в меню напоминаний":
        reminders_menu(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if reminder_type not in ["один раз", "ежедневно", "еженедельно", "ежемесячно"]:
        bot.send_message(message.chat.id, "Неверный тип\nВыберите из предложенных")
        delete_reminder(message)
        return

    filtered_reminders = [r for r in reminders if r["status"] == ("active" if status == "активные" else "expired") and r["type"] == reminder_type]

    if not filtered_reminders:
        bot.send_message(message.chat.id, f"*{status.capitalize()} напоминания ({reminder_type}) для удаления:*\n\n❌ Нет {status} напоминаний!", parse_mode="Markdown")
        delete_reminder(message)
        return

    response = f"*{status.capitalize()} напоминания ({reminder_type}) для удаления:*\n\n"
    for i, reminder in enumerate(filtered_reminders, 1):
        response += (
            f"\n❌ №{i}\n\n"
            f"📝 Название: {reminder['title']}\n"
            f"📅 Дата: {reminder['date']}\n"
            f"🕒 Время: {reminder['time']}\n"
            f"✅ Статус: {'активное' if status == 'активные' else 'истекло'}\n"
            f"🔖 Тип: {reminder['type']}\n\n"
        )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, response, parse_mode="Markdown")
    data["users"][user_id]["current_reminder_type"] = reminder_type
    data["users"][user_id]["current_reminders"] = filtered_reminders
    data["users"][user_id]["current_status"] = status
    save_data(data)

    msg = bot.send_message(message.chat.id, "Введите номера напоминаний для удаления:", reply_markup=markup)
    bot.register_next_step_handler(msg, confirm_delete_step)

@text_only_handler
def confirm_delete_step(message):
    user_id = str(message.from_user.id)
    data = load_data()
    reminders = data["users"][user_id].get("current_reminders", [])
    reminder_type = data["users"][user_id].get("current_reminder_type")
    status = data["users"][user_id].get("current_status")

    if message.text == "Вернуться в меню напоминаний":
        reminders_menu(message, show_description=False)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    try:
        indices = [int(num.strip()) - 1 for num in message.text.split(',')]
        valid_indices = []
        invalid_indices = []

        for index in indices:
            if 0 <= index < len(reminders) and reminders[index]["type"] == reminder_type:
                valid_indices.append(index)
            else:
                invalid_indices.append(index + 1)

        if not valid_indices and invalid_indices:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add('Вернуться в меню напоминаний')
            markup.add('В главное меню')
            msg = bot.send_message(user_id, "Некорректные номера!\nВведите существующие номера", reply_markup=markup)
            bot.register_next_step_handler(msg, confirm_delete_step)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(user_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode='Markdown')

        valid_indices.sort(reverse=True)
        user_reminders = data["users"][user_id]["reminders"]
        for index in valid_indices:
            user_reminders.remove(reminders[index])

        save_data(data)
        bot.send_message(user_id, "✅ Выбранные напоминания удалены!")
        new_message_3 = message
        new_message_3.text = "Напоминания"  
        reminders_menu(new_message_3, show_description=False)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в меню напоминаний')
        markup.add('В главное меню')
        msg = bot.send_message(user_id, "Некорректный ввод!\nВведите номера", reply_markup=markup)
        bot.register_next_step_handler(msg, confirm_delete_step)