from core.imports import wraps, telebot, types, os, sys, json, re, zipfile, shutil, schedule, datetime, timedelta, ApiTelegramException
from core.bot_instance import bot, BASE_DIR
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from decorators.blocked_user import load_blocked_users, save_blocked_users
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

# ------------------------------------------------------- РЕЗЕРВНАЯ КОПИЯ ----------------------------------------------

BACKUP_DIR = 'backups'
SOURCE_DIR = '.'
EXECUTABLE_FILE = os.path.basename(sys.argv[0])  
ADMIN_SESSIONS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')

def normalize_name(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def load_admin_sessions():
    with open(ADMIN_SESSIONS_FILE, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data['admin_sessions']

def check_admin_access(message):
    admin_sessions = load_admin_sessions()
    if str(message.chat.id) in admin_sessions:
        return True
    else:
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return False

@bot.message_handler(func=lambda message: message.text == 'Резервная копия' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_backup_menu(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Резервная копия'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Создать копию', 'Восстановить данные')
    markup.add('В меню админ-панели')

    bot.send_message(message.chat.id, "Выберите действие с резервной копией:", reply_markup=markup)

# -------------------------------------------------- РЕЗЕРВНАЯ КОПИЯ (создать копию) ----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Создать копию' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_create_backup(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Создать копию'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    backup_path = create_full_backup()
    if backup_path:
        backup_message = f"✅ Резервная копия создана!\n\n➡️ Путь к резервной копии:\n{backup_path}"
    else:
        backup_message = "❌ Ошибка при создании резервной копии!"
    bot.send_message(message.chat.id, backup_message)
    show_admin_panel(message)

def create_full_backup():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f'full_backup_{timestamp}.zip')

    os.makedirs(BACKUP_DIR, exist_ok=True)

    try:
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(SOURCE_DIR):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                if 'backups' in dirs:
                    dirs.remove('backups')

                for file in files:
                    if file.startswith('.'): 
                        continue

                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, SOURCE_DIR)

                    if os.path.basename(file_path) == EXECUTABLE_FILE:
                        continue

                    if len(file_path) > 260:
                        continue

                    try:
                        zipf.write(file_path, arcname)
                    except Exception as e:
                        pass

        if not check_backup_integrity(backup_file):
            return None

        return backup_file
    except Exception as e:
        return None

# -------------------------------------------------- РЕЗЕРВНАЯ КОПИЯ (восстановить данные) ----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Восстановить данные' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_restore_backup(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Восстановить данные'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    success = restore_latest_backup()
    if success:
        bot.send_message(message.chat.id, "✅ Данные успешно восстановлены из последней резервной копии!")
    else:
        bot.send_message(message.chat.id, "❌ Резервные копии не найдены!")
    show_admin_panel(message)

def restore_latest_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)

    backups = sorted(os.listdir(BACKUP_DIR), reverse=True)
    if not backups:
        return False

    latest_backup = os.path.join(BACKUP_DIR, backups[0])

    if not os.path.exists(latest_backup):
        return False

    with zipfile.ZipFile(latest_backup, 'r') as zipf:
        zipf.extractall(SOURCE_DIR)

    return True

# -------------------------------------------------- РЕЗЕРВНАЯ КОПИЯ (автоматически) ----------------------------------------------

def create_incremental_backup(last_backup_time):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f'incremental_backup_{timestamp}.zip')

    os.makedirs(BACKUP_DIR, exist_ok=True)

    try:
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(SOURCE_DIR):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                if 'backups' in dirs:
                    dirs.remove('backups')

                for file in files:
                    if file.startswith('.'): 
                        continue

                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, SOURCE_DIR)

                    if os.path.basename(file_path) == EXECUTABLE_FILE:
                        continue

                    if len(file_path) > 260:
                        continue

                    if os.path.getmtime(file_path) > last_backup_time:
                        try:
                            zipf.write(file_path, arcname)
                        except Exception as e:
                            pass

        if not check_backup_integrity(backup_file):
            return None

        return backup_file
    except Exception as e:
        return None

def check_backup_integrity(backup_file):
    try:
        with zipfile.ZipFile(backup_file, 'r') as zipf:
            if zipf.testzip() is not None:
                return False
        return True
    except Exception as e:
        return False

def cleanup_old_backups():
    os.makedirs(BACKUP_DIR, exist_ok=True)

    now = datetime.now()
    for filename in os.listdir(BACKUP_DIR):
        file_path = os.path.join(BACKUP_DIR, filename)
        file_time = datetime.fromtimestamp(os.path.getctime(file_path))

        if "full_backup" in filename and (now - file_time) > timedelta(days=30):
            os.remove(file_path)
        elif "incremental_backup" in filename and (now - file_time) > timedelta(days=7):
            os.remove(file_path)

def monitor_disk_usage():
    total, used, free = shutil.disk_usage(SOURCE_DIR)
    print(f"Использование диска: {used / total:.2%}")

    if (used / total) > 0.9:
        print("Критический уровень использования диска!")
        notify_admin("⚠️ Критический уровень использования диска!")

def scheduled_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)

    today = datetime.now().weekday()
    last_backup_time = get_last_backup_time()

    if today == 0:  
        backup_path = create_full_backup()
    else:
        backup_path = create_incremental_backup(last_backup_time)

    if backup_path:
        notify_admin(f"✅ Резервная копия создана!\n\n➡️ Путь к резервной копии:\n{backup_path}")
    else:
        notify_admin("❌ Ошибка при создании резервной копии!")

    cleanup_old_backups()
    monitor_disk_usage()

def get_last_backup_time():
    os.makedirs(BACKUP_DIR, exist_ok=True)

    backups = sorted(os.listdir(BACKUP_DIR), reverse=True)
    if not backups:
        return 0

    latest_backup = os.path.join(BACKUP_DIR, backups[0])
    return os.path.getmtime(latest_backup)

def notify_admin(message):
    admin_sessions = load_admin_sessions()
    current_time = datetime.now().strftime('%d.%m.%Y в %H:%M')
    blocked_users = load_blocked_users()
    user_ids = []

    for admin_id in admin_sessions:
        if admin_id in blocked_users:
            continue
        try:
            bot.send_message(admin_id, f"{message}\n\nВремя: {current_time}", parse_mode="Markdown")
            user_ids.append(admin_id)
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                pass
                if admin_id not in blocked_users:
                    blocked_users.append(admin_id)
                    save_blocked_users(blocked_users)
            else:
                pass
            
schedule.every().day.at("00:00").do(scheduled_backup)