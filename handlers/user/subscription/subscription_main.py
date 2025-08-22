from core.imports import wraps, telebot, types, os, json, re, datetime, timedelta, pytz, ReplyKeyboardMarkup, ReplyKeyboardRemove
from core.bot_instance import bot
from core.config import PAYMENT_PROVIDER_TOKEN

from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ---------------------------------------------------- ПОДПИСКА НА БОТА ------------------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Подписка на бота")
@check_function_state_decorator('Подписка на бота')
@track_usage('Подписка на бота')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def payments_function(message, show_description=True):
    description = (
        "ℹ️ *Подписка на бота*\n\n"
        "📌 Подписка открывает доступ ко *всем функциям бота*.\n*Бесплатно доступны:* _калькуляторы (алкоголь, налог), найти транспорт, код региона, коды obd2, антирадар, напоминания, прочее (новости, курсы валют, бланки, для рекламы, чат с админом)_\n\n"
        "📅 *Варианты подписки:*\n"
        "👉 *3 дня:* 70 ₽ — быстрый доступ для знакомства с ботом!\n"
        "👉 *7 дней:* 105 ₽ — идеально для тестирования всех функций!\n"
        "👉 *30 дней:* 360 ₽ — оптимальный выбор для регулярного использования!\n"
        "👉 *90 дней:* 900 ₽ — экономия и удобство без частого продления!\n"
        "👉 *180 дней:* 1620 ₽ — больше выгоды и стабильности!\n"
        "👉 *365 дней:* 2920 ₽ — максимальная экономия до 50%!\n\n"
        "🎁 Новым пользователям предоставляется *пробный период на 3 дня*!\n\n"
        "📈 *Баллы и бонусы:*\n"
        "- *1 балл в день* первые 7 дней, затем *0.5 балла в день* за вход\n"
        "- *3/5/10/8/12/15 баллов* за первую подписку (3/7/30/90/180/365 дней)\n"
        "- *0.5/1/3/2/5/10 баллов* за повторную подписку (3/7/30/90/180/365 дней)\n"
        "- *1 балл* для топ-10 рефералов каждые 30 дней\n"
        "- *Топ-1:* +3 дня, *Топ-2:* +2 дня, *Топ-3:* +1 день подписки каждые 30 дней\n\n"
        "🎉 Обменивайте баллы:\n"
        "- *5 баллов = 1 час* подписки\n"
        "- *2 балла = 15 минут* доступа к функциям\n"
        "- *10 баллов = 5% скидки* (до 35%)\n\n"
        "🤝 *Реферальная система:*\n"
        "Приглашайте друзей и получайте:\n"
        "- *1 реферал = +1 день подписки + 1 балл*\n"
        "- *5 рефералов = +5 дней подписки + 1.5 балла за каждого (5–7)*\n"
        "- *10 рефералов = +10 дней подписки + 10% скидка + 1 балл за 8–10, 1.5 за 11+*\n"
        "- Если реферал купит подписку:\n"
        "  - 3 дня: *+0.5 дня* подписки\n"
        "  - 7 дней: *+1 день* подписки\n"
        "  - 30 дней: *+3 дня* подписки\n"
        "  - 90 дней: *+2 дня* подписки\n"
        "  - 180 дней: *+5 дней* подписки\n"
        "  - 365 дней: *+7 дней* подписки\n\n"
        "🔥 *Подарки:*\n"
        "  - *Баллы:* возможность дарить баллы другому пользователю с ограничением 1 раз в 24 часа\n"
        "  - *Время:* возможность дарить время подписки другому пользователю с ограничением 1 раз в 24 часа\n\n"        
        "💥 *Лояльность:* 3 покупки подписки = *10% скидка* на следующую покупку (сбрасывается после использования)\n\n"
        "📺 *Рекламные каналы:* +1 день подписки за подписку на канал\n\n"
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Купить подписку')
    markup.add('Ваши подписки', 'Возврат')
    markup.add('Магазин', 'Баллы', 'Промокоды')
    markup.add('Реферальная система', 'Рекламные каналы')
    markup.add('В главное меню')

    if show_description:
        bot.send_message(message.chat.id, description, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Вернуться в подписку")
@check_function_state_decorator('Вернуться в подписку')
@track_usage('Вернуться в подписку')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_subscription(message):
    payments_function(message, show_description=False)