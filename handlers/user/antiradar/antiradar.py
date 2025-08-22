from core.imports import wraps, telebot, types, os, json, re, time, threading, csv, geodesic, cKDTree
from core.bot_instance import bot, BASE_DIR
from handlers.user.user_main_menu import return_to_menu
from handlers.user.utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# ----------------------------------------------------- АНТИРАДАР ----------------------------------------------------

script_dir = os.path.dirname(os.path.abspath(__file__))
files_for_cams_dir = os.path.join(BASE_DIR, 'files', 'files_for_cams')
os.makedirs(files_for_cams_dir, exist_ok=True)

file_path = os.path.join(files_for_cams_dir, 'milestones.csv')

camera_data = []
coordinates = []
camera_tree = None

def read_csv_with_encoding(file_path):
    try:
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter=';')
            data = []
            for row in reader:
                try:
                    latitude = float(row['gps_y'])
                    longitude = float(row['gps_x'])
                    data.append({
                        'id': row['camera_id'],
                        'latitude': latitude,
                        'longitude': longitude,
                        'description': row['camera_place'],
                    })
                except ValueError as e:
                    continue
        return data
    except UnicodeDecodeError:
        return []

if os.path.exists(file_path):
    try:
        camera_data = read_csv_with_encoding(file_path)
        coordinates = [(cam['latitude'], cam['longitude']) for cam in camera_data]
    except Exception as e:
        pass
else:
    pass

if coordinates and all(len(coord) == 2 for coord in coordinates):
    camera_tree = cKDTree(coordinates)

user_tracking = {}

@bot.message_handler(func=lambda message: message.text == "Антирадар")
@check_function_state_decorator('Антирадар')
@track_usage('Антирадар')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@rate_limit_with_captcha
def start_antiradar(message):
    user_id = message.chat.id
    if not os.path.exists(file_path) or camera_tree is None:
        bot.send_message(user_id, "❌ База данных камер отсутствует!\nПожалуйста, попробуйте позже...")
        return
    
    user_tracking[user_id] = {'tracking': True, 'notification_ids': [], 'last_notified_camera': {}, 'location': None, 'started': False, 'database_missing_notified': False}

    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button_geo = telebot.types.KeyboardButton(text="Отправить геопозицию", request_location=True)
    button_off_geo = telebot.types.KeyboardButton(text="Выключить антирадар")
    keyboard.add(button_geo)
    keyboard.add(button_off_geo)
    bot.send_message(
        user_id,
        "⚠️ Пожалуйста, разрешите *доступ к геопозиции* для запуска антирадара!\n\nНажмите кнопку, чтобы отправить геопозицию...\n\n"
        "_P.S. Функция антирадар находится в бета-версии! Данные камер не обновляются автоматически из-за ограничений telegram! Обновляйте свою геопозицию вручную!_",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

    message_text = "⚠️ Внимание! Камеры впереди:\n\n"
    sent_message = bot.send_message(user_id, message_text, parse_mode="Markdown")

    bot.pin_chat_message(user_id, sent_message.message_id)
    user_tracking[user_id]['last_camera_message'] = sent_message.message_id

@bot.message_handler(content_types=['location'], func=lambda m: True if user_tracking.get(m.chat.id, {}).get('tracking', False) else False)
@check_function_state_decorator('Функция для обработки локации')
@track_usage('Функция для обработки локации')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@check_subscription_chanal
@rate_limit_with_captcha
def handle_antiradar_location(message):
    user_id = message.chat.id

    if not os.path.exists(file_path) or camera_tree is None:
        bot.send_message(user_id, "❌ База данных камер отсутствует!\nПожалуйста, попробуйте позже...")
        return

    if message.location:
        latitude = message.location.latitude
        longitude = message.location.longitude
    else:
        bot.send_message(user_id, "❌ Геолокация недоступна!\nПопробуйте снова")
        return

    if user_tracking.get(user_id, {}).get('tracking', False):
        user_tracking[user_id]['location'] = message.location

        if not user_tracking[user_id].get('started', False):
            user_tracking[user_id]['started'] = True
            track_user_location(user_id, message.location)

@bot.message_handler(func=lambda message: message.text == "Выключить антирадар")
@check_function_state_decorator('Выключить антирадар')
@track_usage('Выключить антирадар')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@rate_limit_with_captcha
def stop_antiradar(message):
    user_id = message.chat.id
    if user_id in user_tracking:
        user_tracking[user_id]['tracking'] = False
        bot.send_message(user_id, "❌ Антирадар остановлен!")

        if user_tracking[user_id].get('last_camera_message'):
            bot.unpin_chat_message(user_id, user_tracking[user_id]['last_camera_message'])
            bot.delete_message(user_id, user_tracking[user_id]['last_camera_message'])

        return_to_menu(message)
    else:
        bot.send_message(user_id, "❌ Антирадар не был запущен!")

def delete_messages(user_id, message_id):
    time.sleep(6)
    try:
        bot.delete_message(chat_id=user_id, message_id=message_id)
    except:
        pass

MAX_CAMERAS_IN_MESSAGE = 3
ALERT_DISTANCE = 500
EXIT_DISTANCE = 100
IN_ZONE_DISTANCE = 50

def track_user_location(user_id, initial_location):
    def monitor():
        while user_tracking.get(user_id, {}).get('tracking', False):
            if camera_tree is None:
                if not user_tracking[user_id].get('database_missing_notified', False):
                    bot.send_message(user_id, "❌ База данных камер отсутствует!\nПожалуйста, попробуйте позже...")
                    user_tracking[user_id]['database_missing_notified'] = True
                time.sleep(3)
                continue

            user_location = user_tracking[user_id]['location']
            user_position = (user_location.latitude, user_location.longitude)
            distances, indices = camera_tree.query(user_position, k=len(camera_data))
            nearest_cameras = []
            unique_addresses = set()

            for i, distance in enumerate(distances[:MAX_CAMERAS_IN_MESSAGE]):
                if distance <= 1000:
                    camera = camera_data[indices[i]]
                    actual_distance = int(geodesic(user_position, (camera['latitude'], camera['longitude'])).meters)
                    camera_address = camera['description']

                    if camera_address not in user_tracking[user_id]['last_notified_camera']:
                        nearest_cameras.append((actual_distance, camera))
                        unique_addresses.add(camera_address)
                        user_tracking[user_id]['last_notified_camera'][camera_address] = {
                            'entered': False,
                            'exited': False,
                            'in_zone': False,
                            'notified_once': {'entered': False, 'in_zone': False, 'exited': False}
                        }

                    if (actual_distance <= ALERT_DISTANCE and 
                        not user_tracking[user_id]['last_notified_camera'][camera_address]['entered'] and
                        not user_tracking[user_id]['last_notified_camera'][camera_address]['notified_once']['entered']):
                        notification_message = (
                            f"⚠️ Вы приближаетесь к камере!\n\n"
                            f"📷 Расстояние - *{actual_distance} м.*\n"
                            f"🗺️ *{camera_address}*"
                        )
                        try:
                            sent_message = bot.send_message(user_id, notification_message, parse_mode="Markdown")
                            user_tracking[user_id]['notification_ids'].append(sent_message.message_id)
                            user_tracking[user_id]['last_notified_camera'][camera_address]['entered'] = True
                            user_tracking[user_id]['last_notified_camera'][camera_address]['notified_once']['entered'] = True
                        except:
                            pass

                    if (actual_distance <= IN_ZONE_DISTANCE and 
                        not user_tracking[user_id]['last_notified_camera'][camera_address]['in_zone'] and
                        not user_tracking[user_id]['last_notified_camera'][camera_address]['notified_once']['in_zone']):
                        in_zone_message = (
                            f"📍 Вы находитесь в зоне действия камеры!\n\n"
                            f"🗺️ *{camera_address}*"
                        )
                        try:
                            in_zone_sent = bot.send_message(user_id, in_zone_message, parse_mode="Markdown")
                            user_tracking[user_id]['notification_ids'].append(in_zone_sent.message_id)
                            user_tracking[user_id]['last_notified_camera'][camera_address]['in_zone'] = True
                            user_tracking[user_id]['last_notified_camera'][camera_address]['notified_once']['in_zone'] = True
                        except:
                            pass

                    if (actual_distance > EXIT_DISTANCE and 
                        user_tracking[user_id]['last_notified_camera'][camera_address]['entered'] and
                        not user_tracking[user_id]['last_notified_camera'][camera_address]['notified_once']['exited']):
                        exit_message = (
                            f"🔔 Вы вышли из зоны действия камеры!\n\n"
                            f"🗺️ *{camera_address}*"
                        )
                        try:
                            exit_sent_message = bot.send_message(user_id, exit_message, parse_mode="Markdown")
                            user_tracking[user_id]['notification_ids'].append(exit_sent_message.message_id)
                            user_tracking[user_id]['last_notified_camera'][camera_address]['exited'] = True
                            user_tracking[user_id]['last_notified_camera'][camera_address]['notified_once']['exited'] = True
                        except:
                            pass

            message_text = "⚠️ Внимание! Камеры впереди:\n\n"
            for distance, camera in nearest_cameras:
                message_text += f"📷 Камера через *{distance} м.*\n🗺️ Адрес: *{camera['description']}*\n\n"

            if nearest_cameras:
                try:
                    if user_tracking[user_id].get('last_camera_message'):
                        bot.edit_message_text(chat_id=user_id, message_id=user_tracking[user_id]['last_camera_message'], text=message_text, parse_mode="Markdown")
                    else:
                        sent_message = bot.send_message(user_id, message_text, parse_mode="Markdown")
                        user_tracking[user_id]['last_camera_message'] = sent_message.message_id
                except:
                    pass

            time.sleep(3)

    threading.Thread(target=monitor, daemon=True).start()