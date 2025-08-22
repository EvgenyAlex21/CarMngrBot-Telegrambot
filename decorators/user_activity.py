from core.imports import wraps, datetime, json, os

# ------------------------------------ ДЕКОРАТОРЫ (декоратор для отслеживания активности действий пользователя) ---------------------------

def track_user_activity(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        user_id = getattr(message.from_user, 'id', None)
        username = getattr(message.from_user, 'username', None) or "неизвестный"
        first_name = getattr(message.from_user, 'first_name', None) or ""
        last_name = getattr(message.from_user, 'last_name', None) or ""

        try:
            from handlers.user.user_main_menu import update_user_activity as _update_user_activity
            if user_id is not None:
                _update_user_activity(user_id, username, first_name, last_name)
        except Exception:
            pass

        return func(message, *args, **kwargs)
    return wrapper