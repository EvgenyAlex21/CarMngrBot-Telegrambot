from core.imports import threading, time, os, sys, traceback, ApiTelegramException, requests, ConnectionError, ReadTimeout, logging, urllib3, ReadTimeoutError
from core.bot_instance import bot, BASE_DIR
from telebot import logger as tb_logger
from telebot.apihelper import ApiTelegramException as _ApiEx
from decorators.logging import ensure_directories_and_files
from decorators.captcha import load_captcha_data

# -------------------------------------------------- ФУНКЦИЯ ЗАПУСКА ----------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
ensure_directories_and_files()
load_captcha_data()

# -------------------------------------------------- ГЛОБАЛЬНЫЕ ХУКИ ДЛЯ ОШИБОК ------------------------------------

ERROR_LOG_DIR = os.path.join(BASE_DIR, 'data', 'admin', 'log')
ERROR_LOG_FILE = os.path.join(ERROR_LOG_DIR, 'bot_errors.log')

def _write_error_log(prefix: str, text: str):
    try:
        os.makedirs(ERROR_LOG_DIR, exist_ok=True)
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{ts}] {prefix}:\n{text}\n{'-'*80}\n")
    except Exception:
        print(text)

def _sys_excepthook(exc_type, exc, tb):
    text = ''.join(traceback.format_exception(exc_type, exc, tb))
    print('Необработанное исключение (sys):', exc)
    _write_error_log('UNCAUGHT (sys)', text)

def _threading_excepthook(args):
    text = ''.join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    print('Необработанное исключение в потоке:', args.exc_value)
    _write_error_log('UNCAUGHT (thread)', text)

sys.excepthook = _sys_excepthook
if hasattr(threading, 'excepthook'):
    threading.excepthook = _threading_excepthook

try:
    tb_logger.setLevel(logging.WARNING)
except Exception:
    pass

def background_subscription_expiration_check(chat_id):
    try:
        bot.send_message(chat_id, "Ваша подписка скоро заканчивается!")
    except ApiTelegramException as e:
        if e.result_json.get('description') == "Forbidden: bot was blocked by the user":
            print(f"Пользователь {chat_id} заблокировал бота. Пропускаем отправку сообщения.")
        else:
            pass

# -------------------------------------------------- ЗАЩИТА ОТ 429 (RATE LIMIT) ---------------------------------------

def _wrap_rate_limited(func_name: str):
    orig = getattr(bot, func_name)
    def wrapper(*args, **kwargs):
        try:
            return orig(*args, **kwargs)
        except _ApiEx as e:
            try:
                code = int(e.result_json.get('error_code', 0))
            except Exception:
                code = 0
            if code == 429:
                retry_after = 3
                desc = e.result_json.get('description') if isinstance(e.result_json, dict) else ''
                if isinstance(e.result_json, dict) and 'parameters' in e.result_json:
                    retry_after = int(e.result_json['parameters'].get('retry_after', retry_after))
                else:
                    import re as _re
                    m = _re.search(r'retry after (\d+)', str(desc))
                    if m:
                        retry_after = int(m.group(1))
                print(f"Rate limit 429 в {func_name}, ждём {retry_after} сек...")
                time.sleep(min(max(retry_after, 1), 3600))
                return orig(*args, **kwargs)
            raise
    return wrapper

for _name in (
    'send_message', 'send_document', 'send_photo', 'send_video', 'send_audio',
    'send_media_group', 'send_sticker', 'send_voice', 'send_location',
    'edit_message_text', 'edit_message_caption', 'edit_message_media'
):
    if hasattr(bot, _name):
        setattr(bot, _name, _wrap_rate_limited(_name))

# -------------------------------------------------- ФУНКЦИИ ОБНОВЛЕНИЯ ----------------------------------------------

def start_bot_with_retries(retries=10000000, delay=5):
    attempt = 0
    while attempt < retries:
        try:
            print(f"Запуск попытки №{attempt + 1}")
            try:
                if hasattr(bot, 'infinity_polling'):
                    bot.infinity_polling(interval=1, timeout=20, long_polling_timeout=60)
                else:
                    bot.polling(none_stop=True, interval=1, timeout=20, long_polling_timeout=60)
            except AttributeError:
                bot.polling(none_stop=True, interval=1, timeout=20, long_polling_timeout=60)
        except (ReadTimeout, ConnectionError, ReadTimeoutError, ApiTelegramException) as e:
            msg = f"Сетевая/Telegram-ошибка: {e}. Попытка {attempt + 1} из {retries}"
            print(msg)
            _write_error_log('NETWORK/TELEGRAM ERROR', traceback.format_exc())
            attempt += 1
            if attempt < retries:
                base = max(1, int(delay))
                sleep_s = min(300, base * (2 ** min(attempt, 6)))
                print(f"Повторная попытка через {sleep_s} секунд...")
                time.sleep(sleep_s)
            else:
                print("Превышено количество попыток! Бот не смог запуститься!")
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            _write_error_log('UNEXPECTED ERROR', traceback.format_exc())
            attempt += 1
            if attempt < retries:
                base = max(1, int(delay))
                sleep_s = min(300, base * (2 ** min(attempt, 6)))
                print(f"Повторная попытка через {sleep_s} секунд...")
                time.sleep(sleep_s)
            else:
                print("Превышено количество попыток! Бот не смог запуститься!")

try:
    from handlers.user import *
    from handlers.admin import *
    
    print("Обработчики успешно загружены")
except Exception as e:
    print(f"Ошибка при загрузке обработчиков: {e}")
    traceback.print_exc()

# -------------------------------------------------- ЗАПУСК БОТА ----------------------------------------------

try:
    from handlers.admin.statistics.statistics import load_statistics, save_statistics, active_users, total_users
except Exception as e:
    print(f"Ошибка при импорте модуля статистики: {e}")
    def load_statistics():
        return {}
    
    def save_statistics(data):
        pass
    
    active_users = set()
    total_users = set()

if __name__ == '__main__':
    print("Запуск бота...")
    start_bot_with_retries()