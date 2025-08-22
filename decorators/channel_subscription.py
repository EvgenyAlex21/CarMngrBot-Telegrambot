from core.imports import wraps, types, InlineKeyboardMarkup
from core.bot_instance import bot
from core.config import CHANNEL_CHAT_ID, SUBSCRIBE_CHANNEL_URL

# ------------------------------------ ДЕКОРАТОРЫ (декоратор для отслеживания подписки на основной канал бота) ---------------------------

def check_subscription_chanal(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        try:
            member = bot.get_chat_member(CHANNEL_CHAT_ID, user_id)
            subscribed = member.status in ['member', 'administrator', 'creator'] and member.status != 'kicked'
        except Exception:
            subscribed = False

        if not subscribed:
            bot.send_message(message.chat.id, "⚠️ Пожалуйста, подпишитесь на канал, чтобы продолжить...", reply_markup=types.ReplyKeyboardRemove())

            markup = InlineKeyboardMarkup()
            subscribe_button = types.InlineKeyboardButton("Подписаться на канал", url=SUBSCRIBE_CHANNEL_URL)
            confirm_button = types.InlineKeyboardButton("Я подписался", callback_data="confirm_subscription")
            markup.add(subscribe_button)
            markup.add(confirm_button)
            bot.send_message(message.chat.id, (
                "👋 Добро пожаловать в бот @CarMngrBot!\n\n"
                "⚠️ Перед началом работы, пожалуйста, ознакомьтесь с функционалом бота, а также с политикой конфиденциальности и пользовательским соглашением! Перейти к документам можно по ссылке: <a href='https://carmngrbot.com.swtest.ru'>Сайт CAR MANAGER</a>!\n\n"
                "🚀 Если вы новый пользователь или еще не подписаны на наш канал, рекомендуем подписаться прямо сейчас, чтобы не пропустить важные обновления:"
            ), reply_markup=markup, parse_mode="HTML")
            return
        return func(message, *args, **kwargs)
    return wrapper