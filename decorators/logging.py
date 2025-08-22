from core.imports import wraps, time, datetime, timedelta, json, os, logging, threading, schedule
from core.bot_instance import BASE_DIR

# ------------------------------------ ДЕКОРАТОРЫ (логирование действий пользователя и бота) ------------------------------------

def ensure_directories_and_files():
    log_dir = os.path.join(BASE_DIR, "data", "admin", "log")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "bot_logs.log")
    if not os.path.exists(log_file):
        with open(log_file, 'w', encoding='utf-8'):
            pass

    error_log_file = os.path.join(log_dir, "errors_log.json")
    if not os.path.exists(error_log_file):
        with open(error_log_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)


ensure_directories_and_files()

file_logger = logging.getLogger('fileLogger')
file_handler = logging.FileHandler(os.path.join(BASE_DIR, 'data', 'admin', 'log', 'bot_logs.log'), encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
file_logger.addHandler(file_handler)
file_logger.setLevel(logging.INFO)
file_logger.propagate = False

console_logger = logging.getLogger('consoleLogger')
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
console_logger.addHandler(console_handler)
console_logger.setLevel(logging.ERROR)


def log_to_json(user_id: int | str, log_entry: dict) -> None:
    log_file = os.path.join(BASE_DIR, 'data', 'admin', 'log', f"{user_id}_log.json")

    try:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as file:
                logs = json.load(file)
        else:
            logs = []
    except json.JSONDecodeError:
        file_logger.warning(f"Файл {log_file} поврежден! Создаем новый файл...")
        logs = []

    logs.append(log_entry)

    with open(log_file, 'w', encoding='utf-8') as file:
        json.dump(logs, file, ensure_ascii=False, indent=4)


def clear_logs_and_transfer_errors() -> None:
    log_dir = os.path.join(BASE_DIR, 'data', 'admin', 'log')
    error_log_file = os.path.join(log_dir, 'errors_log.json')

    file_logger.info("Начало переноса ошибок из логов пользователей!")

    try:
        if os.path.exists(error_log_file):
            with open(error_log_file, 'r', encoding='utf-8') as file:
                errors = json.load(file)
        else:
            errors = []
    except json.JSONDecodeError:
        file_logger.error("Файл errors_log.json поврежден! Перезаписываем файл...")
        errors = []

    for filename in os.listdir(log_dir):
        if filename.endswith("_log.json") and filename != "errors_log.json":
            file_path = os.path.join(log_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    logs = json.load(file)
            except json.JSONDecodeError:
                file_logger.warning(f"Файл {filename} поврежден! Пропускаем...")
                continue

            error_logs = [log for log in logs if log.get("level") == "ERROR"]
            errors.extend(error_logs)

            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump([], file, ensure_ascii=False, indent=4)

    with open(error_log_file, 'w', encoding='utf-8') as file:
        json.dump(errors, file, ensure_ascii=False, indent=4)

    file_logger.info("Перенос ошибок завершен!")


def remove_old_errors() -> None:
    error_log_file = os.path.join(BASE_DIR, 'data', 'admin', 'log', 'errors_log.json')

    file_logger.info("Начало удаления старых ошибок!")

    try:
        if os.path.exists(error_log_file):
            with open(error_log_file, 'r', encoding='utf-8') as file:
                errors = json.load(file)
        else:
            errors = []
    except json.JSONDecodeError:
        file_logger.error("Файл errors_log.json поврежден! Пропускаем удаление старых ошибок...")
        return

    current_time = datetime.now()
    errors = [error for error in errors if (current_time - datetime.strptime(error["timestamp"], '%d.%m.%Y в %H:%M:%S')) <= timedelta(days=7)]

    try:
        with open(error_log_file, 'w', encoding='utf-8') as file:
            json.dump(errors, file, ensure_ascii=False, indent=4)
    except Exception as e:
        file_logger.error(f"Ошибка записи в errors_log.json: {e}")

    file_logger.info("Удаление старых ошибок завершено!")

def log_user_actions(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        log_dir = os.path.join(BASE_DIR, 'data', 'admin', 'log')
        error_log_file = os.path.join(log_dir, 'errors_log.json')
        os.makedirs(log_dir, exist_ok=True)

        start_time = time.time()

        try:
            user_id = getattr(getattr(message, 'from_user', None), 'id', 'Unknown')
            command = func.__name__
            result = func(message, *args, **kwargs)
            execution_time = time.time() - start_time

            log_entry = {
                "timestamp": datetime.now().strftime('%d.%m.%Y в %H:%M:%S'),
                "level": "INFO",
                "event_type": "User Action",
                "user_id": user_id,
                "command": command,
                "result": "Success",
                "execution_time": f"{execution_time:.2f} sec"
            }
            file_logger.info(f"User {user_id} executed command {command} successfully in {execution_time:.2f} sec.")
        except Exception as e:
            execution_time = time.time() - start_time
            log_entry = {
                "timestamp": datetime.now().strftime('%d.%m.%Y в %H:%M:%S'),
                "level": "ERROR",
                "event_type": "User Action",
                "user_id": 'Unknown',
                "command": func.__name__,
                "result": "Error",
                "execution_time": f"{execution_time:.2f} sec",
                "error_details": str(e)
            }
            file_logger.error(f"Error while executing command {func.__name__}: {e}")
            console_logger.error(f"Error while executing command {func.__name__}: {e}")

            try:
                if os.path.exists(error_log_file):
                    with open(error_log_file, 'r', encoding='utf-8') as file:
                        errors = json.load(file)
                else:
                    errors = []

                errors.append(log_entry)

                with open(error_log_file, 'w', encoding='utf-8') as file:
                    json.dump(errors, file, ensure_ascii=False, indent=4)
            except Exception as error_logging_exception:
                file_logger.error(f"Ошибка записи в errors_log.json: {error_logging_exception}")

            raise
        finally:
            log_to_json(user_id if 'user_id' in locals() else 'Unknown', log_entry)

        return result

    return wrapper

def run_weekly_task():
    while True:
        remove_old_errors()
        time.sleep(7 * 24 * 60 * 60)

schedule.every().day.at("00:00").do(clear_logs_and_transfer_errors)

def run_scheduled_tasks():
    while True:
        schedule.run_pending()
        time.sleep(1)


scheduler_thread = threading.Thread(target=run_scheduled_tasks, daemon=True)
scheduler_thread.start()

weekly_task_thread = threading.Thread(target=run_weekly_task, daemon=True)
weekly_task_thread.start()