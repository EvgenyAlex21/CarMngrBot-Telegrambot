from core.imports import wraps, datetime
from core.bot_instance import bot

# ------------------------------------ ДЕКОРАТОРЫ (декоратор для отслеживания платной и бесплатной подписки на бот) ---------------------------

def check_subscription(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        from handlers.user.user_main_menu import load_payment_data as _load_pay
        from handlers.user.user_main_menu import FREE_FEATURES as _FREE
        from handlers.user.user_main_menu import PAID_FEATURES as _PAID
        try:
            from handlers.admin.functions.functions import NEW_FUNCTIONS as _NEW
        except Exception:
            _NEW = {}

        user_id = str(message.from_user.id)

        if getattr(message, 'from_user', None) and message.from_user.is_bot:
            return
        msg_text = getattr(message, 'text', None)
        if msg_text is None:
            return

        if msg_text in _FREE:
            return func(message, *args, **kwargs)

        data = _load_pay()
        user_data = data['subscriptions']['users'].get(user_id, {})

        has_active_plan = any(
            datetime.strptime(plan['end_date'], "%d.%m.%Y в %H:%M") > datetime.now()
            for plan in user_data.get('plans', [])
        )
        if has_active_plan:
            return func(message, *args, **kwargs)

        feature_access = user_data.get('feature_access', {})

        parent_feature = None
        specific_feature = None

        for feature, subfunctions in _NEW.items():
            if msg_text == feature and feature in _PAID:
                parent_feature = feature
                specific_feature = feature
                break
            if msg_text in subfunctions:
                if msg_text in _PAID:
                    specific_feature = msg_text
                    break
                if feature in _PAID:
                    parent_feature = feature
                    break
                for parent, parent_subfunctions in _NEW.items():
                    if feature in parent_subfunctions and parent in _PAID:
                        parent_feature = parent
                        break
            if specific_feature or parent_feature:
                break

        def _has_time(access_key: str) -> bool:
            access_end = feature_access.get(access_key, "01.01.2025 в 00:00")
            try:
                end_date = datetime.strptime(access_end, "%d.%m.%Y в %H:%M")
                return end_date > datetime.now()
            except Exception:
                return False

        if specific_feature and _has_time(specific_feature):
            return func(message, *args, **kwargs)
        if parent_feature and _has_time(parent_feature):
            return func(message, *args, **kwargs)

        bot.send_message(user_id, (
            "⚠️ Эта функция доступна только премиум-пользователям!\n"
            "🚀 Оформите подписку или обменяйте баллы для продолжения!"
        ), parse_mode="Markdown")
    return wrapper