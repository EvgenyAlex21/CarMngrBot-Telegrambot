from core.imports import wraps, json, os
from core.bot_instance import bot, BASE_DIR

# ------------------------------------ ДЕКОРАТОРЫ (декоратор для проверки состояния чата при запросах на общение) ---------------------------

message_history = {}

ACTIVE_CHATS_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'chats', 'active_chats.json')

def _get_active_chats():
    try:
        if os.path.exists(ACTIVE_CHATS_PATH):
            with open(ACTIVE_CHATS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {int(k): v for k, v in data.get('active_chats', {}).items()}
    except Exception:
        pass
    try:
        from handlers.user.others.others_chat_with_admin import active_chats as _ac
        return _ac
    except Exception:
        return {}

def check_chat_state(func):
    def wrapper(message, *args, **kwargs):
        active_chats = _get_active_chats()
        user_id = message.from_user.id
        text = (getattr(message, 'text', None) or '').strip()

        if user_id in active_chats:
            chat = active_chats[user_id]
            status = chat.get('status')
            awaiting = chat.get('awaiting_response', False)

            if status == 'pending' and awaiting:
                if text.lower() not in ["принять", "отклонить"]:
                    bot.send_message(user_id, "Пожалуйста, выберите *ПРИНЯТЬ* или *ОТКЛОНИТЬ*!", parse_mode="Markdown")
                    return

            if status == 'active':
                pass

        return func(message, *args, **kwargs)
    return wrapper

def save_last_bot_message(user_id, message_text):
    message_history[user_id] = {"last_bot_message": message_text}