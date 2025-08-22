from core.imports import wraps
from core.bot_instance import bot

# ---------------------- ДЕКОРАТОРЫ (декоратор для ограничения действий пользователям, которые были заблокировны администратором) ---------------

def restricted(func):
    def wrapper(message, *args, **kwargs):
        try:
            from handlers.admin.ban.ban import is_user_blocked as _is_blocked
            from handlers.admin.ban.ban import get_user_id_by_username as _get_uid
        except Exception:
            _is_blocked = lambda _uid: False
            _get_uid = lambda _username: None

        user_id = message.from_user.id
        username = message.from_user.username

        try:
            if _is_blocked(user_id):
                bot.send_message(message.chat.id, "🚫 Вы *заблокированы* и не можете выполнять это действие!", parse_mode="Markdown")
                return
            if username:
                uid = _get_uid(username)
                if uid and _is_blocked(uid):
                    bot.send_message(message.chat.id, "🚫 Вы *заблокированы* и не можете выполнять это действие!", parse_mode="Markdown")
                    return
        except Exception:
            pass

        return func(message, *args, **kwargs)
    return wrapper