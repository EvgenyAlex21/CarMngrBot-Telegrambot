from core.imports import wraps, telebot, types, os, json, re, requests, datetime
from core.bot_instance import bot
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ----------------------------------------------------- ПРОЧЕЕ (курсы валют) ----------------------------------------------------

def fetch_exchange_rates_cbr():
    url = 'https://www.cbr-xml-daily.ru/daily_json.js'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        rates = data['Valute']
        return {
            'USD': rates['USD']['Value'],
            'EUR': rates['EUR']['Value'],
            'GBP': rates['GBP']['Value'],
            'CHF': rates['CHF']['Value'],
            'JPY': rates['JPY']['Value'] / 100,
            'CNY': rates['CNY']['Value'] / 10,
            'AUD': rates['AUD']['Value'],
            'CAD': rates['CAD']['Value'],
            'BYN': rates['BYN']['Value'],
            'KRW': rates['KRW']['Value'] / 1000,
            'SGD': rates['SGD']['Value'],
            'NZD': rates['NZD']['Value'],
            'RUB': 1
        }
    except Exception:
        return fetch_exchange_rates_moex()

def fetch_exchange_rates_moex():
    url = 'https://iss.moex.com/iss/statistics/engines/futures/markets/indicativerates.json'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        rates = data['securities']['data']
        exchange_rates = get_default_rates()
        for rate in rates:
            currency_pair = rate[0]
            value = rate[2]
            if currency_pair == 'USD/RUB':
                exchange_rates['USD'] = value
            elif currency_pair == 'EUR/RUB':
                exchange_rates['EUR'] = value
            elif currency_pair == 'GBP/RUB':
                exchange_rates['GBP'] = value
            elif currency_pair == 'CHF/RUB':
                exchange_rates['CHF'] = value
            elif currency_pair == 'JPY/RUB':
                exchange_rates['JPY'] = value / 100
            elif currency_pair == 'CNY/RUB':
                exchange_rates['CNY'] = value / 10
        return exchange_rates
    except Exception:
        return get_default_rates()

def get_default_rates():
    return {
        'USD': 83.6813,
        'EUR': 89.6553,
        'GBP': 104.3210,
        'CHF': 94.1234,
        'JPY': 0.55,
        'CNY': 11.46,
        'AUD': 55.4321,
        'CAD': 60.9876,
        'BYN': 27.34,
        'KRW': 0.05705,
        'SGD': 61.2345,
        'NZD': 50.8765,
        'RUB': 1
    }

CURRENCY_NAMES = {
    'USD': ('Доллар США', '🇺🇸'),
    'EUR': ('Евро', '🇪🇺'),
    'GBP': ('Британский фунт', '🇬🇧'),
    'CHF': ('Швейцарский франк', '🇨🇭'),
    'JPY': ('Японская иена', '🇯🇵'),
    'CNY': ('Китайский юань', '🇨🇳'),
    'AUD': ('Австралийский доллар', '🇦🇺'),
    'CAD': ('Канадский доллар', '🇨🇦'),
    'BYN': ('Белорусский рубль', '🇧🇾'),
    'KRW': ('Южнокорейская вона', '🇰🇷'),
    'SGD': ('Сингапурский доллар', '🇸🇬'),
    'NZD': ('Новозеландский доллар', '🇳🇿'),
    'RUB': ('Российский рубль', '🇷🇺')
}

@bot.message_handler(func=lambda message: message.text == "Курсы валют")
@check_function_state_decorator('Курсы валют')
@track_usage('Курсы валют')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_exchange_rates(message):

    from .others_notifications import initialize_user_notifications
    initialize_user_notifications(message.chat.id)

    exchange_rates = fetch_exchange_rates_cbr()

    current_time = datetime.now().strftime("%d.%m.%Y в %H:%M")
    rates_message = f"📊 *Актуальные курсы валют на {current_time}*\n\n"
    for currency, rate in exchange_rates.items():
        if currency in CURRENCY_NAMES:
            name, emoji = CURRENCY_NAMES[currency]
            rates_message += f"{emoji} {name} - {rate:.2f} руб.\n"

    bot.send_message(message.chat.id, rates_message, parse_mode='Markdown')