from core.imports import wraps, telebot, types, os, json, re, openpyxl, Workbook, Font, Alignment, get_column_letter, datetime, timedelta, defaultdict
from core.bot_instance import bot, BASE_DIR
from handlers.admin.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

try:
    from handlers.admin.admin_main_menu import check_permission  
except Exception:
    def check_permission(admin_id, permission):
        return True

# -------------------------------------------------- СТАТИСТИКА ---------------------------------------------------

ADMIN_SESSIONS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')
USER_DATA_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'users.json')
STATS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'statistics', 'stats.json')
ERRORS_LOG_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'log', 'errors_log.json')

active_users = {}
total_users = set()

def load_admin_sessions():
    try:
        with open(ADMIN_SESSIONS_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data.get('admin_sessions', [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def load_user_data():
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_user_data(data):
    os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def load_statistics():
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return {date: {'users': set(data[date]['users']), 'functions': data[date].get('functions', {})} for date in data}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_statistics(data):
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    with open(STATS_FILE, 'w', encoding='utf-8') as file:
        json.dump({date: {'users': list(data[date]['users']), 'functions': data[date]['functions']} for date in data}, file, indent=4, ensure_ascii=False)

def check_admin_access(message):
    admin_sessions = load_admin_sessions()
    if str(message.chat.id) in admin_sessions:
        return True
    else:
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return False

def escape_markdown(text):
    return re.sub(r'([*_`])', r'\\\1', text)

@bot.message_handler(func=lambda message: message.text == 'Статистика' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_statistics(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Статистика'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if not check_admin_access(message):
        return

    bot.send_message(message.chat.id, "Выберите категорию статистики:", reply_markup=create_submenu_buttons())

def create_submenu_buttons():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        types.KeyboardButton("Пользователи"),
        types.KeyboardButton("Использование функций"),
        types.KeyboardButton("Список ошибок"),
        types.KeyboardButton("Версия и аптайм"),
        types.KeyboardButton("В меню админ-панели")
    ]
    markup.row(buttons[0], buttons[1])
    markup.row(buttons[2], buttons[3])
    markup.row(buttons[4])
    return markup

# -------------------------------------------------- СТАТИСТИКА (пользователи) ---------------------------------------------------

def is_user_active(last_active):
    try:
        last_active_time = datetime.strptime(last_active, '%d.%m.%Y в %H:%M:%S')
    except ValueError:
        return False
    return (datetime.now() - last_active_time).total_seconds() < 1 * 60

def get_aggregated_statistics(period='all'):
    statistics = load_statistics()
    today = datetime.now()
    user_result = defaultdict(int)
    function_result = defaultdict(int)

    for date_str, usage in statistics.items():
        record_date = datetime.strptime(date_str, '%d.%m.%Y')

        if period == 'day' and record_date.date() == today.date():
            user_result['users'] += len(usage['users'])
            if 'functions' in usage:
                for func_name, count in usage['functions'].items():
                    function_result[func_name] += count
        elif period == 'week' and today - timedelta(days=today.weekday()) <= record_date <= today:
            user_result['users'] += len(usage['users'])
            if 'functions' in usage:
                for func_name, count in usage['functions'].items():
                    function_result[func_name] += count
        elif period == 'month' and record_date.year == today.year and record_date.month == today.month:
            user_result['users'] += len(usage['users'])
            if 'functions' in usage:
                for func_name, count in usage['functions'].items():
                    function_result[func_name] += count
        elif period == 'year' and record_date.year == today.year:
            user_result['users'] += len(usage['users'])
            if 'functions' in usage:
                for func_name, count in usage['functions'].items():
                    function_result[func_name] += count
        elif period == 'all':
            user_result['users'] += len(usage['users'])
            if 'functions' in usage:
                for func_name, count in usage['functions'].items():
                    function_result[func_name] += count

    return dict(user_result), dict(function_result)

def get_statistics():
    users_data = load_user_data()
    online_users = len([user for user in users_data.values() if is_user_active(user["last_active"]) and not user['blocked']])
    total_users = len(users_data)

    statistics = load_statistics()
    today = datetime.now().strftime('%d.%m.%Y')
    week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%d.%m.%Y')
    month_start = datetime.now().replace(day=1).strftime('%d.%m.%Y')
    year_start = datetime.now().replace(month=1, day=1).strftime('%d.%m.%Y')

    users_today = len(statistics.get(today, {}).get('users', set()))
    users_week = len(set().union(*[data.get('users', set()) for date, data in statistics.items() if week_start <= date <= today]))
    users_month = len(set().union(*[data.get('users', set()) for date, data in statistics.items() if month_start <= date <= today]))
    users_year = len(set().union(*[data.get('users', set()) for date, data in statistics.items() if year_start <= date <= today]))

    return online_users, total_users, users_today, users_week, users_month, users_year

def list_active_users():
    users_data = load_user_data()
    active_users = [
        f"{index + 1}) `{user_id}`: {escape_markdown(user.get('username', 'неизвестный'))}"
        for index, (user_id, user) in enumerate(users_data.items())
        if is_user_active(user["last_active"]) and not user['blocked']
    ]
    return "\n".join(active_users) if active_users else None

def get_top_users(top_n=10):
    users_data = load_user_data()
    user_activity = {user_id: user['last_active'] for user_id, user in users_data.items() if not user['blocked']}
    sorted_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)
    top_users = sorted_users[:top_n]
    return [f"{index + 1}) {user_id}: {escape_markdown(users_data[user_id].get('username', 'неизвестный'))}" for index, (user_id, _) in enumerate(top_users)]

def get_recent_actions(limit=10):
    users_data = load_user_data()
    recent_actions = sorted(users_data.items(), key=lambda x: x[1]['last_active'], reverse=True)
    return [f"{user_id}: {escape_markdown(user['username'])} - {user['last_active']}" for user_id, user in recent_actions[:limit]]

def get_peak_usage_time():
    statistics = load_statistics()
    usage_times = defaultdict(int)

    for date_str, usage in statistics.items():
        record_date = datetime.strptime(date_str, '%d.%m.%Y')
        for func_name, count in usage.items():
            usage_times[record_date.hour] += count

    peak_hour = max(usage_times, key=usage_times.get)
    return peak_hour, usage_times[peak_hour]

# -------------------------------------------------- СТАТИСТИКА (версия и аптайм) ---------------------------------------------------

def get_bot_version():
    return "1.0"

def get_uptime():
    start_time = datetime(2025, 1, 1)
    uptime = datetime.now() - start_time
    days, seconds = uptime.days, uptime.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{days} дней, {hours}:{minutes} часов"

def get_development_start_time():
    start_time = datetime(2023, 11, 6)
    uptime = datetime.now() - start_time
    days, seconds = uptime.days, uptime.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{days} дней, {hours}:{minutes} часов"

def get_last_update_time():
    last_update = datetime(2025, 5, 7)
    uptime = datetime.now() - last_update
    days, seconds = uptime.days, uptime.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{days} дней, {hours}:{minutes} часов"

# -------------------------------------------------- СТАТИСТИКА (список ошибок) ---------------------------------------------------

def load_errors():
    with open(ERRORS_LOG_FILE, 'r', encoding='utf-8') as file:
        return json.load(file)

def get_error_list():
    errors = load_errors()
    error_list = []
    for index, error in enumerate(errors, start=1):
        error_details = error.get('error_details', '')
        error_details_more = "\n".join(error.get('error_details_more', []))
        error_list.append(f"{error_details}\n\n{error_details_more}")
    return error_list

def get_user_last_active():
    users_data = load_user_data()
    user_last_active = [
        f"📌 {index + 1}) `{user_id}`: {escape_markdown(user.get('username', 'неизвестный'))} - {user['last_active'][:-3]}"
        for index, (user_id, user) in enumerate(users_data.items())
        if 'blocked' not in user or not user['blocked'] 
    ]
    return "\n".join(user_last_active) if user_last_active else None

# ------------------------------------------------------- СТАТИСТИКА (общая функция) ----------------------------------------------

@bot.message_handler(func=lambda message: message.text in ["Пользователи", "Версия и аптайм", "Использование функций", "Список ошибок", "В меню админ-панели"])
@restricted
@track_user_activity
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_submenu_buttons(message):
    if not check_admin_access(message):
        return

    if message.text == "Пользователи":
        admin_id = str(message.chat.id)
        if not check_permission(admin_id, 'Пользователи'):
            bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
            return

        online_count, total_count, users_today, users_week, users_month, users_year = get_statistics()
        active_user_list = list_active_users()
        user_last_active_list = get_user_last_active()
        response_message = (
            f"*🌐 Пользователи онлайн:* {online_count}\n"
            f"*👥 Всего пользователей:* {total_count}\n\n"
            f"*📅 Пользователи за день:* {users_today}\n"
            f"*📅 Пользователи за неделю:* {users_week}\n"
            f"*📅 Пользователи за месяц:* {users_month}\n"
            f"*📅 Пользователи за год:* {users_year}\n\n"
        )
        if active_user_list:
            response_message += "*🌐 Пользователи онлайн:*\n\n"
            for user in active_user_list.split('\n'):
                response_message += f"👤 {user}\n"
        else:
            response_message += "*🌐 Нет активных пользователей*\n\n"

        if user_last_active_list:
            response_message += "*\n🕒 Последняя активность пользователей:*\n\n"
            response_message += user_last_active_list
        else:
            response_message += "*\n🕒 Нет данных о последней активности пользователей*"

        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")
    elif message.text == "Версия и аптайм":
        admin_id = str(message.chat.id)
        if not check_permission(admin_id, 'Версия и аптайм'):
            bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
            return

        bot_version = get_bot_version()
        uptime = get_uptime()
        development_start = get_development_start_time()
        last_update = get_last_update_time()
        bot.send_message(message.chat.id, (
            f"*🤖 Версия бота:* {bot_version}\n\n"
            f"*⚡ Запуск разработки:* {development_start} (06.11.2023)\n\n"
            f"*⏳ Аптайм бота:* {uptime} (01.01.2025)\n\n"
            f"*🔄 Последнее обновление:* {last_update} (18.03.2025)"
        ), parse_mode="Markdown")
    elif message.text == "Использование функций":
        admin_id = str(message.chat.id)
        if not check_permission(admin_id, 'Использование функций'):
            bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
            return

        stats_day_users, stats_day_functions = get_aggregated_statistics('day')
        stats_week_users, stats_week_functions = get_aggregated_statistics('week')
        stats_month_users, stats_month_functions = get_aggregated_statistics('month')
        stats_year_users, stats_year_functions = get_aggregated_statistics('year')
        stats_all_users, stats_all_functions = get_aggregated_statistics('all')
        file_path = os.path.join(BASE_DIR, 'data', 'admin', 'statistics', 'function_usage.xlsx')
        wb = Workbook()

        sheets = {
            "За день": stats_day_functions,
            "За неделю": stats_week_functions,
            "За месяц": stats_month_functions,
            "За год": stats_year_functions,
            "За всё время": stats_all_functions
        }

        for sheet_name, functions in sheets.items():
            ws = wb.create_sheet(title=sheet_name)

            headers = ["Название функции", "Количество"]
            ws.append(headers)
            bold_font = Font(bold=True)
            for col_num, column_title in enumerate(headers, 1):
                col_letter = get_column_letter(col_num)
                ws[col_letter + '1'].font = bold_font

            for func_name, count in functions.items():
                ws.append([func_name, count])

            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter 
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = (max_length + 2)
                ws.column_dimensions[column].width = adjusted_width

            for row in ws.iter_rows():
                for cell in row:
                    cell.alignment = Alignment(wrapText=True)
                    ws.row_dimensions[cell.row].height = max(len(str(cell.value).split('\n')) * 15, 20)  

        if 'Sheet' in wb.sheetnames:
            del wb['Sheet']
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        wb.save(file_path)

        with open(file_path, 'rb') as file:
            bot.send_document(message.chat.id, file, caption="📊 Использование функций")
    elif message.text == "Список ошибок":
        admin_id = str(message.chat.id)
        if not check_permission(admin_id, 'Список ошибок'):
            bot.send_message(message.chat.id, "⛔️ У вас <b>нет прав доступа</b> к этой функции!", parse_mode="HTML")
            return

        error_list = get_error_list()
        if not error_list:
            bot.send_message(message.chat.id, "❌ Данные не найдены! Активные ошибки не обнаружены!", parse_mode="HTML")
        else:
            escaped_error_list = [
                f"🛑 <b>ОШИБКА №{index}</b> 🛑\n\n{error}"
                for index, error in enumerate(error_list, start=1)
            ]
            full_message = "\n".join(escaped_error_list)
            if len(full_message) > 4096:
                parts = [full_message[i:i + 4096] for i in range(0, len(full_message), 4096)]
                for part in parts:
                    bot.send_message(message.chat.id, part, parse_mode="HTML")
            else:
                bot.send_message(message.chat.id, full_message, parse_mode="HTML")
    elif message.text == "В меню админ-панели":
        bot.send_message(message.chat.id, "Выберите категорию статистики:", reply_markup=create_submenu_buttons())