from core.imports import wraps
from core.bot_instance import bot

# ------------------------------------ ДЕКОРАТОРЫ (декоратор для отслеживания текстовых сообщений) ---------------------------

def text_only_handler(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        if (message.photo or message.video or message.document or 
            message.animation or message.sticker or message.audio or 
            message.contact or message.voice or message.video_note):
            sent = bot.send_message(
                message.chat.id, 
                "⛔ Извините, но отправка мультимедийных файлов не разрешена! Пожалуйста, введите текстовое сообщение..."
            )
            bot.register_next_step_handler(sent, func, *args, **kwargs)
            return
        return func(message, *args, **kwargs)
    return wrapper