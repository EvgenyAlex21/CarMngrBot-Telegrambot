from core.imports import wraps, random, time, json, os
from core.bot_instance import bot, BASE_DIR

# ------------------------------------ ДЕКОРАТОРЫ (декоратор для ограничения запросов - капча) ---------------------------

REQUEST_LIMIT = 5
TIME_WINDOW = 10
CAPTCHA_TIMEOUT = 300 

user_requests = {}
captcha_data = {}

def save_captcha_data():
    try:
        path = os.path.join(BASE_DIR, 'data', 'admin', 'captcha', 'captcha_data.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(captcha_data, f)
    except Exception as e:
        pass

def load_captcha_data():
    global captcha_data
    try:
        path = os.path.join(BASE_DIR, 'data', 'admin', 'captcha', 'captcha_data.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path, 'r', encoding='utf-8') as f:
                captcha_data = json.load(f)
        else:
            captcha_data = {}
    except json.JSONDecodeError as e:
        captcha_data = {}
    except Exception as e:
        captcha_data = {}

def rate_limit_with_captcha(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        current_time = time.time()

        if user_id not in user_requests:
            user_requests[user_id] = []

        user_requests[user_id] = [t for t in user_requests[user_id] if current_time - t < TIME_WINDOW]

        if user_id in captcha_data:
            if time.time() - captcha_data[user_id]['timestamp'] > CAPTCHA_TIMEOUT:
                del captcha_data[user_id]
                bot.send_message(message.chat.id, "⚠️ Капча устарела!\nОтправляем новую...")
                send_captcha(message)
                bot.register_next_step_handler(message, handle_captcha, func, *args, **kwargs)
                save_captcha_data()
                return

            try:
                user_answer = int(message.text.strip())
                correct_answer = captcha_data[user_id]['answer']
                
                if user_answer == correct_answer:
                    del captcha_data[user_id]
                    user_requests[user_id] = []
                    bot.send_message(message.chat.id, "✅ Капча пройдена!\n🚀 Продолжайте использовать бота...")
                    save_captcha_data()
                    return func(message, *args, **kwargs)
                else:
                    bot.send_message(message.chat.id, f"❌ Неверный ответ!\n\nРешите задачу снова:\n\n{captcha_data[user_id]['question']}")
                    bot.register_next_step_handler(message, handle_captcha, func, *args, **kwargs)
                    return
            except ValueError:
                bot.send_message(message.chat.id, f"❌ Пожалуйста, введите число!\n\nРешите задачу:\n\n{captcha_data[user_id]['question']}")
                bot.register_next_step_handler(message, handle_captcha, func, *args, **kwargs)
                return
            except KeyError:
                del captcha_data[user_id]
                bot.send_message(message.chat.id, "⚠️ Ошибка капчи!\nОтправляем новую...")
                send_captcha(message)
                bot.register_next_step_handler(message, handle_captcha, func, *args, **kwargs)
                save_captcha_data()
                return

        if len(user_requests[user_id]) >= REQUEST_LIMIT:
            send_captcha(message)
            bot.register_next_step_handler(message, handle_captcha, func, *args, **kwargs)
            save_captcha_data()
            return

        user_requests[user_id].append(current_time)
        return func(message, *args, **kwargs)
    
    return wrapper

def send_captcha(message):
    user_id = message.from_user.id
    if user_id in captcha_data:
        bot.send_message(message.chat.id, f"⚠️ Пожалуйста, решите текущую капчу:\n\n{captcha_data[user_id]['question']}")
        return

    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    operation = random.choice(['+', '-', '*'])
    answer = num1 + num2 if operation == '+' else num1 - num2 if operation == '-' else num1 * num2
    question = f"{num1} {operation} {num2} = ?"
    captcha_data[user_id] = {
        'question': question,
        'answer': answer,
        'timestamp': time.time()
    }
    bot.send_message(message.chat.id, f"⚠️ Вы отправляете слишком много запросов!\n\nРешите задачу:\n\n{question}")

def handle_captcha(message, original_func, *args, **kwargs):
    user_id = message.from_user.id
    
    if user_id not in captcha_data:
        bot.send_message(message.chat.id, "⚠️ Сессия капчи истекла или не найдена! Попробуйте снова")
        return original_func(message, *args, **kwargs)
    
    if time.time() - captcha_data[user_id]['timestamp'] > CAPTCHA_TIMEOUT:
        del captcha_data[user_id]
        bot.send_message(message.chat.id, "⚠️ Капча устарела!\nОтправляем новую...")
        send_captcha(message)
        bot.register_next_step_handler(message, handle_captcha, original_func, *args, **kwargs)
        save_captcha_data()
        return
    
    try:
        user_answer = int(message.text.strip())
        correct_answer = captcha_data[user_id]['answer']
        if user_answer == correct_answer:
            del captcha_data[user_id]
            user_requests[user_id] = []
            bot.send_message(message.chat.id, "✅ Капча пройдена!\n🚀 Продолжайте использовать бота...")
            save_captcha_data()
            return original_func(message, *args, **kwargs)
        else:
            bot.send_message(message.chat.id, f"❌ Неверный ответ!\n\nРешите задачу снова:\n\n{captcha_data[user_id]['question']}")
            bot.register_next_step_handler(message, handle_captcha, original_func, *args, **kwargs)
    except ValueError:
        bot.send_message(message.chat.id, f"❌ Пожалуйста, введите число!\n\nРешите задачу:\n\n{captcha_data[user_id]['question']}")
        bot.register_next_step_handler(message, handle_captcha, original_func, *args, **kwargs)
    except KeyError:
        del captcha_data[user_id]
        bot.send_message(message.chat.id, "⚠️ Ошибка капчи!\nПопробуйте снова...")
        return original_func(message, *args, **kwargs)