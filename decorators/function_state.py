from core.imports import wraps
from core.bot_instance import bot

# ---------------------------------------- ДЕКОРАТОРЫ (декоратор для проверки состояния функции) ---------------------------------

def _get_function_states():
    try:
        from handlers.admin.functions.functions import function_states as _fs
        return _fs if isinstance(_fs, dict) else {}
    except Exception:
        return {}

def check_function_state(function_name):
    states = _get_function_states()
    if not states:
        return True
    value = states.get(function_name)
    if isinstance(value, dict):
        return bool(value.get('state', True))
    if isinstance(value, bool):
        return value
    return True

def check_function_state_decorator(function_name):
    def decorator(func):
        @wraps(func)
        def wrapped(message, *args, **kwargs):
            if check_function_state(function_name):
                return func(message, *args, **kwargs)
            else:
                bot.send_message(message.chat.id, f"⚠️ Функция *{function_name.lower()}* временно недоступна!", parse_mode="Markdown")
        return wrapped
    return decorator