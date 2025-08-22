from core.imports import schedule, os, json, re, datetime, timedelta, time, threading, ApiTelegramException
from core.bot_instance import bot, BASE_DIR

# -------------------------------------------------- УВЕДОМЛЕНИЕ О НЕАКТИВНОСТИ ---------------------------------------------------

DB_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'users.json')
BLOCKED_USERS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'bloked_bot', 'blocked_bot_users.json')
INACTIVITY_THRESHOLD = 30 * 24 * 60 * 60
CHECK_INTERVAL = 12 * 60 * 60
DELETE_THRESHOLD = 60 * 24 * 60 * 60

def load_blocked_users():
    if os.path.exists(BLOCKED_USERS_FILE):
        with open(BLOCKED_USERS_FILE, 'r') as file:
            return json.load(file)
    return []

def save_blocked_users(blocked_users):
    with open(BLOCKED_USERS_FILE, 'w') as file:
        json.dump(blocked_users, file, indent=4)

def escape_markdown(text):
    return re.sub(r'([_*\[\]()~`>#+\\|{}.!-])', r'\\\1', text)

def check_and_create_file():
    dir_path = os.path.dirname(DB_PATH)
    os.makedirs(dir_path, exist_ok=True)

    if not os.path.exists(DB_PATH):
        with open(DB_PATH, 'w', encoding='utf-8') as file:
            json.dump({}, file, ensure_ascii=False, indent=4)

def load_users():
    check_and_create_file()
    try:
        with open(DB_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except UnicodeDecodeError as e:
        with open(DB_PATH, 'r', encoding='cp1251') as file:
            content = file.read()
            with open(DB_PATH, 'w', encoding='utf-8') as outfile:
                json.dump(json.loads(content), outfile, ensure_ascii=False, indent=4)
            return json.loads(content)
    except json.JSONDecodeError as e:
        return {}

def save_users(users):
    check_and_create_file()
    try:
        with open(DB_PATH, 'w', encoding='utf-8') as file:
            json.dump(users, file, ensure_ascii=False, indent=4)
    except Exception as e:
        pass

def delete_user_data_from_all_files(user_id, users):
    username = users.get(str(user_id), {}).get('username', 'неизвестный')
    user_id_str = str(user_id)

    def remove_user_data(obj):
        if isinstance(obj, dict):
            keys_to_delete = [key for key in obj if key == user_id_str]
            for key in keys_to_delete:
                del obj[key]
            for key, value in list(obj.items()):
                remove_user_data(value)
        elif isinstance(obj, list):
            obj[:] = [item for item in obj if item != user_id_str]
            for item in obj:
                remove_user_data(item)

    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

                if file == 'payments.json' and 'data' in root and 'admin' in root:
                    users_section = data.get("subscriptions", {}).get("users", {})
                    if user_id_str in users_section:
                        user_info = users_section[user_id_str]
                        plans = user_info.get("plans", [])
                        filtered_plans = [plan for plan in plans if plan.get("plan_name") == "free"]
                        user_info["plans"] = filtered_plans
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                    continue

                remove_user_data(data)

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)

    if user_id_str in users:
        users.pop(user_id_str, None)
        save_users(users)

    try:
        bot.send_message(
            user_id,
            f"⛔ Ваши данные были удалены из-за длительной неактивности!\n"
            "Если вы хотите снова пользоваться ботом, зарегистрируйтесь заново с помощью команды /start",
            parse_mode="Markdown"
        )
    except ApiTelegramException as e:
        if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
            blocked_users = load_blocked_users()
            if user_id not in blocked_users:
                blocked_users.append(user_id)
                save_blocked_users(blocked_users)
        else:
            raise e

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

def check_inactivity():
    while True:
        users = load_users()
        current_time = datetime.now()

        for user_id, user_data in list(users.items()):
            last_active_str = user_data.get('last_active')
            first_notification_str = user_data.get('first_notification')

            if last_active_str:
                last_active = datetime.strptime(last_active_str, '%d.%m.%Y в %H:%M:%S')

                if current_time - last_active > timedelta(seconds=INACTIVITY_THRESHOLD):
                    if not first_notification_str:
                        users[user_id]['first_notification'] = current_time.strftime('%d.%m.%Y в %H:%M:%S')
                        save_users(users)
                        username = user_data.get('username', 'неизвестный')
                        message = f"⚠️ Уважаемый пользователь, {escape_markdown(username)}, от вас давно не было активности!\nИспользуйте бота или ваши данные будут удалены через 1 месяц!"
                        safe_send_message(user_id, message, parse_mode="Markdown")
                    else:
                        first_notification = datetime.strptime(first_notification_str, '%d.%m.%Y в %H:%M:%S')
                        if current_time - first_notification > timedelta(seconds=DELETE_THRESHOLD):
                            delete_user_data_from_all_files(user_id, users)

        save_users(users)
        time.sleep(CHECK_INTERVAL)

inactivity_thread = threading.Thread(target=check_inactivity)
inactivity_thread.daemon = True
inactivity_thread.start()