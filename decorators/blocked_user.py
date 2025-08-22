from core.imports import *
from core.bot_instance import bot, BASE_DIR

# ------------------------------------ ДЕКОРАТОРЫ (декоратор для отслеживания бокировки бота пользователем) ---------------------------

BLOCKED_USERS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'bloked_bot', 'blocked_bot_users.json')

def load_blocked_users():
    if os.path.exists(BLOCKED_USERS_FILE):
        with open(BLOCKED_USERS_FILE, 'r') as file:
            return json.load(file)
    return []

def save_blocked_users(blocked_users):
    with open(BLOCKED_USERS_FILE, 'w') as file:
        json.dump(blocked_users, file, indent=4)

def check_user_blocked(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        user_id = message.chat.id
        blocked_users = load_blocked_users()

        if message.text == '/start' and user_id in blocked_users:
            blocked_users.remove(user_id)
            save_blocked_users(blocked_users)  

        if user_id in blocked_users:
            return

        try:
            return func(message, *args, **kwargs)
        except ApiTelegramException as e:
            if e.result_json['error_code'] == 403 and 'bot was blocked by the user' in e.result_json['description']:
                if user_id not in blocked_users:
                    blocked_users.append(user_id)
                    save_blocked_users(blocked_users)  
            else:
                raise e
    return wrapper