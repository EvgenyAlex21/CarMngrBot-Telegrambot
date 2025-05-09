# (1) --------------- ИМПОРТ МОДУЛЕЙ ---------------

import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telebot import types
import datetime
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import os
import json
import locale
import re
import requests
from functools import partial
from urllib.parse import quote
import traceback
from bs4 import BeautifulSoup

# (2) --------------- ТОКЕН БОТА ---------------

bot = telebot.TeleBot("7519948621:AAGPoPBJrnL8-vZepAYvTmm18TipvvmLUoE")

# (3) --------------- СОХРАНЕНИЯ И ЗАГРУЗКА ДАННЫХ ПОЛЬЗОВАТЕЛЯ ---------------

# (3.1) --------------- СОХРАНЕНИЯ И ЗАГРУЗКА ДАННЫХ ПОЛЬЗОВАТЕЛЯ (ПОЕЗДКИ) ---------------

def save_data(user_id): 
    if user_id in user_trip_data:
        folder_path = "data base"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        with open(os.path.join(folder_path, f"{user_id}_trip_data.json"), "w") as json_file:
            json.dump(user_trip_data[user_id], json_file)

def save_trip_data(user_id):
    if user_id in user_trip_data:
        folder_path = "data base"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        with open(os.path.join(folder_path, f"{user_id}_trip_data.json"), "w") as json_file:
            json.dump(user_trip_data[user_id], json_file)

def load_trip_data(user_id):
    folder_path = "data base" 
    try:
        with open(os.path.join(folder_path, f"{user_id}_trip_data.json"), "r") as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        return []

# (3.2) --------------- СОХРАНЕНИЯ И ЗАГРУЗКА ДАННЫХ ПОЛЬЗОВАТЕЛЯ (ТРАТЫ) ---------------

def save_expense_data(user_id, user_data):
    folder_path = "data base"  
    if not os.path.exists(folder_path):  
        os.makedirs(folder_path)

    with open(os.path.join(folder_path, f"expenses_{user_id}.json"), "w", encoding="utf-8") as file:
        json.dump(user_data, file, ensure_ascii=False, indent=4)

def load_expense_data(user_id):
    folder_path = "data base" 
    try:
        with open(os.path.join(folder_path, f"expenses_{user_id}.json"), "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}
    return data

# (3.3) --------------- СОХРАНЕНИЯ И ЗАГРУЗКА ДАННЫХ ПОЛЬЗОВАТЕЛЯ (РЕМОНТЫ) ---------------

def save_repair_data(user_id, user_data):
    folder_path = "data base"  
    if not os.path.exists(folder_path): 
        os.makedirs(folder_path)

    data = load_repair_data(user_id)  
    data.update(user_data)  
    with open(os.path.join(folder_path, f"repairs_{user_id}.json"), "w", encoding="utf-8") as file:
        json.dump({str(user_id): data}, file, ensure_ascii=False, indent=4)

def load_repair_data(user_id):
    folder_path = "data base" 
    try:
        with open(os.path.join(folder_path, f"repairs_{user_id}.json"), "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}
    return data.get(str(user_id), {}) 

# (3.4) --------------- СОХРАНЕНИЯ И ЗАГРУЗКА ДАННЫХ ПОЛЬЗОВАТЕЛЯ (ГЕОПОЗИЦИЯ) ---------------

def save_location_data(location_data):
    folder_path = "data base"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    with open(os.path.join(folder_path, "location_data.json"), "w") as json_file:
        json.dump(location_data, json_file)

def load_location_data():
    try:
        with open(os.path.join("data base", "location_data.json"), "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# (4) --------------- ЗАГРУЗКА ТЕКСТОВОГО ФАЙЛА С РЕГИОНАМИ ---------------

regions = {}
try:
    with open('files/regions.txt', 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split(' — ')
            if len(parts) == 2:
                code, name = parts
                regions[code.strip()] = name.strip()
except FileNotFoundError:
    print("Файл 'regions.txt' не найден.")

# (5) --------------- ОБРАБОТЧИК КОМАНДЫ /START ---------------

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_id = message.chat.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Расход топлива")
    item2 = types.KeyboardButton("Траты и ремонты")
    item3 = types.KeyboardButton("Найти транспорт")
    item4 = types.KeyboardButton("Поиск мест")
    item5 = types.KeyboardButton("Погода")
    item6 = types.KeyboardButton("Код региона")
    markup.add(item1, item2)
    markup.add(item3, item4)
    markup.add(item5, item6)
    bot.send_message(chat_id, "Добро пожаловать! Выберите действие из меню:", reply_markup=markup)

# (6) --------------- ОБРАБОТЧИК КОМАНДЫ /MAINMENU ---------------

@bot.message_handler(func=lambda message: message.text == "В главное меню")
@bot.message_handler(commands=['mainmenu'])
def return_to_menu(message):
    start(message)

# (7) --------------- ДОПОЛНИТЕЛЬНОЙ ИНФОРМАЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЯ ---------------

# (7.1) --------------- ОБРАБОТЧИК КОМАНДЫ /INFO ---------------

@bot.message_handler(func=lambda message: message.text == "Инфо")
@bot.message_handler(commands=['info'])
def information_handler(message):
    chat_id = message.chat.id
    if message.text == "Вернуться в меню":
        reset_and_start_over(chat_id)
        return  
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        sent = bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, process_passengers_step, date, distance, fuel_type, price_per_liter, fuel_consumption) # type: ignore
        return
    try:
        with open('files/about.txt', 'r', encoding='utf-8') as information_file:
            information_text = information_file.read()
        bot.send_message(message.chat.id, information_text)
    except FileNotFoundError:
        bot.send_message(message.chat.id, "Извините, информация недоступна в данный момент.")

# (7.2) --------------- ОБРАБОТЧИК КОМАНДЫ /MANUAL---------------

@bot.message_handler(func=lambda message: message.text == "Инструкция")
@bot.message_handler(commands=['manual'])
def information_handler(message):
    chat_id = message.chat.id
    if message.text == "Вернуться в меню":
        reset_and_start_over(chat_id)
        return  
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        sent = bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, process_passengers_step, date, distance, fuel_type, price_per_liter, fuel_consumption)
        return
    try:
        with open('files/manual.txt', 'r', encoding='utf-8') as information_file:
            information_text = information_file.read()
        bot.send_message(message.chat.id, information_text)
    except FileNotFoundError:
        bot.send_message(message.chat.id, "Извините, инструкция недоступна в данный момент.")

# (7.3) --------------- ОБРАБОТЧИК КОМАНДЫ /POLICY---------------

@bot.message_handler(func=lambda message: message.text == "Политика")
@bot.message_handler(commands=['policy'])
def privacy_policy_handler(message):
    chat_id = message.chat.id
    if message.text == "Вернуться в меню":
        reset_and_start_over(chat_id)
        return 
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        sent = bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, process_passengers_step, date, distance, fuel_type, price_per_liter, fuel_consumption)
        return
    try:
        with open('files/privacy_policy.txt', 'r', encoding='utf-8') as policy_file:
            privacy_policy_text = policy_file.read()
        bot.send_message(message.chat.id, privacy_policy_text)
    except FileNotFoundError:
        bot.send_message(message.chat.id, "Извините, политика конфиденциальности недоступна в данный момент.")

# (7.4) --------------- ОБРАБОТЧИК КОМАНДЫ /AGREEMENT---------------

@bot.message_handler(func=lambda message: message.text == "Соглашение")
@bot.message_handler(commands=['agreement'])
def user_agreement_handler(message):
    chat_id = message.chat.id
    if message.text == "Вернуться в меню":
        reset_and_start_over(chat_id)
        return
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        sent = bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, process_passengers_step, date, distance, fuel_type, price_per_liter, fuel_consumption)
        return
    try:
        with open('files/user_agreement.txt', 'r', encoding='utf-8') as agreement_file:
            user_agreement_text = agreement_file.read()
        bot.send_message(message.chat.id, user_agreement_text)
    except FileNotFoundError:
        bot.send_message(message.chat.id, "Извините, пользовательское соглашение недоступно в данный момент.")

# (8) --------------- ОБРАБОТЧИК КОМАНДЫ "РАСХОД ТОПЛИВА"---------------

@bot.message_handler(func=lambda message: message.text == "Расход топлива")
def handle_fuel_expense(message):
    user_id = message.from_user.id

    if user_id not in user_trip_data:
        user_trip_data[user_id] = load_trip_data(user_id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Рассчитать расход топлива")
    item2 = types.KeyboardButton("Посмотреть поездки")
    item3 = types.KeyboardButton("Удалить поездку")
    item4 = types.KeyboardButton("В главное меню")

    markup.add(item1)
    markup.add(item2, item3)
    markup.add(item4)

    bot.clear_step_handler_by_chat_id(user_id)
    bot.send_message(user_id, "Меню для учета расхода топлива. Выберите действие:", reply_markup=markup)

# (9) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" ---------------

# (9.1) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (СЛОВАРИ, СПИСОК, РЕГУЛЯРНОЕ ВЫРАЖЕНИЕ) ---------------

user_trip_data = {}

trip_data = {}

temporary_trip_data = {}

fuel_types = ["АИ-92", "АИ-95", "АИ-98", "АИ-100", "ДТ", "ГАЗ"]

date_pattern = r"^\d{2}.\d{2}.\d{4}$"

# (9.2) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (КОМАНДЫ /restart1 ) ---------------

@bot.message_handler(func=lambda message: message.text == "Вернуться в меню расчета топлива")
@bot.message_handler(commands=['restart1'])
def restart_handler(message):
    chat_id = message.chat.id
    user_id = message.chat.id
    reset_and_start_over(chat_id)
    if user_id not in user_trip_data:
        user_trip_data[user_id] = load_trip_data(user_id)
    load_trip_data(user_id)
    for user_id in user_trip_data.keys():
        user_trip_data[user_id] = load_trip_data(user_id)

def reset_and_start_over(chat_id):
    save_trip_data(chat_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Рассчитать расход топлива")
    item2 = types.KeyboardButton("Посмотреть поездки")
    item3 = types.KeyboardButton("Удалить поездку")
    item4 = types.KeyboardButton("В главное меню")

    markup.add(item1)
    markup.add(item2, item3)
    markup.add(item4)

    bot.send_message(chat_id, "Вы вернулись в меню расчета топлива. Выберите действие:", reply_markup=markup)
    pass

# (9.3) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (ЗАГРУЗКА ДАННЫХ ПРИ /restart1) ---------------

def reset_user_data(user_id):
    if user_id not in user_trip_data:
        user_trip_data[user_id] = load_trip_data(user_id)
    bot.clear_step_handler_by_chat_id(user_id) 

# (9.4) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (ФУНКЦИЯ НАЧАЛЬНОГО МЕСТОПОЛОЖЕНИЯ) ---------------

@bot.message_handler(func=lambda message: message.text == "Рассчитать расход топлива")
def calculate_fuel_cost_handler(message):
    chat_id = message.chat.id

    bot.clear_step_handler_by_chat_id(chat_id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item2 = types.KeyboardButton("В главное меню")
    item3 = types.KeyboardButton("Отправить геолокацию", request_location=True)
    markup.add(item3)
    markup.add(item1, item2)
    sent = bot.send_message(chat_id, "Введите начальное местоположение или отправьте геолокацию:", reply_markup=markup)
    reset_user_data(chat_id)  

    bot.register_next_step_handler(sent, process_start_location_step)
	

def process_start_location_step(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item2 = types.KeyboardButton("В главное меню")
    item3 = types.KeyboardButton("Отправить геолокацию", request_location=True)
    markup.add(item3)
    markup.add(item1, item2)

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return  
    if message.text == "В главное меню":
        return_to_menu(message) 
        return    

    if message.photo or message.video or message.document or message.animation or message.sticker or message.audio or message.contact or message.voice or message.video_note:
        sent = bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, process_start_location_step)
        return  

    if message.location:  # Если пользователь отправил геолокацию
        location = message.location
        start_address = geolocator.reverse((location.latitude, location.longitude)).address
        trip_data[chat_id] = {
            "start_location": {
                "address": start_address,
                "latitude": location.latitude,
                "longitude": location.longitude
            }
        }
        bot.send_message(chat_id, f"Ваше начальное местоположение:\n\n{start_address}")
    else:  # Если пользователь ввел текстовое местоположение
        start_location = message.text
        location = geolocator.geocode(start_location)
        if location:
            trip_data[chat_id] = {
                "start_location": {
                    "address": start_location,
                    "latitude": location.latitude,
                    "longitude": location.longitude
                }
            }
            bot.send_message(chat_id, f"Ваше начальное местоположение:\n\n{start_location}")
        else:
            sent = bot.send_message(chat_id, "Не удалось найти местоположение. Пожалуйста, введите корректный адрес.")
            bot.register_next_step_handler(sent, process_start_location_step)
            return
    
    sent = bot.send_message(chat_id, "Введите конечное местоположение или отправьте геолокацию:", reply_markup=markup)
    bot.register_next_step_handler(sent, process_end_location_step)


def process_end_location_step(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item2 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return  
    if message.text == "В главное меню":
        return_to_menu(message) 
        return    

    if message.photo or message.video or message.document or message.animation or message.sticker or message.audio or message.contact or message.voice or message.video_note:
        sent = bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, process_end_location_step)
        return

    if message.location:  # Если пользователь отправил геолокацию
        location = message.location
        end_address = geolocator.reverse((location.latitude, location.longitude)).address
        trip_data[chat_id]["end_location"] = {
            "address": end_address,
            "latitude": location.latitude,
            "longitude": location.longitude
        }
        bot.send_message(chat_id, f"Ваше конечное местоположение:\n\n{end_address}")
    else:  # Если пользователь ввел текстовое местоположение
        end_location = message.text
        location = geolocator.geocode(end_location)
        if location:
            trip_data[chat_id]["end_location"] = {
                "address": end_location,
                "latitude": location.latitude,
                "longitude": location.longitude
            }
            bot.send_message(chat_id, f"Ваше конечное местоположение:\n\n{end_location}")
        else:
            sent = bot.send_message(chat_id, "Не удалось найти местоположение. Пожалуйста, введите корректный адрес.")
            bot.register_next_step_handler(sent, process_end_location_step)
            return

    # Рассчитать расстояние между точками
    start_coords = (trip_data[chat_id]["start_location"]["latitude"], trip_data[chat_id]["start_location"]["longitude"])
    end_coords = (trip_data[chat_id]["end_location"]["latitude"], trip_data[chat_id]["end_location"]["longitude"])
    distance_km = geodesic(start_coords, end_coords).kilometers

    # Предлагаем пользователю выбрать между автоматическим расстоянием и вводом своего
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_auto = types.KeyboardButton("Использовать автоматическое расстояние")
    item_input = types.KeyboardButton("Ввести своё расстояние")
    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item2 = types.KeyboardButton("В главное меню")

    markup.add(item_auto, item_input)
    markup.add(item1, item2)
    
    sent = bot.send_message(chat_id, "Выберите вариант:", reply_markup=markup)
    bot.register_next_step_handler(sent, process_distance_choice_step, distance_km)


def process_distance_choice_step(message, distance_km):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Добавляем кнопки выбора расстояния
    item_auto = types.KeyboardButton("Использовать автоматическое расстояние")
    item_input = types.KeyboardButton("Ввести своё расстояние")
    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item2 = types.KeyboardButton("В главное меню")

    markup.add(item_auto, item_input)
    markup.add(item1, item2)

    if message.photo or message.video or message.document or message.animation or message.sticker or message.audio or message.contact or message.voice or message.video_note:
        sent = bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.", reply_markup=markup)
        bot.register_next_step_handler(sent, process_distance_choice_step, distance_km)
        return

    if message.text == "Использовать автоматическое расстояние":
        # Создаем новую клавиатуру с двумя кнопками
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
        item2 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2)

        bot.send_message(chat_id, f"Расстояние между точками: {distance_km:.2f} км.", reply_markup=markup)
        sent = bot.send_message(chat_id, "Введите дату поездки в формате ДД.ММ.ГГГГ:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_date_step, distance_km)

    elif message.text == "Ввести своё расстояние":
        # Теперь создаем новую клавиатуру с двумя кнопками
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
        item2 = types.KeyboardButton("В главное меню")
        markup.add(item1, item2)

        sent = bot.send_message(chat_id, "Введите расстояние в километрах:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_custom_distance_step)

    elif message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return

    elif message.text == "В главное меню":
        return_to_menu(message)
        return

    else:
        # Обработка некорректного ввода
        sent = bot.send_message(chat_id, "Пожалуйста, выберите один из предложенных вариантов.", reply_markup=markup)
        bot.register_next_step_handler(sent, process_distance_choice_step, distance_km)

def process_custom_distance_step(message):
    chat_id = message.chat.id

    # Создаем новую разметку для ввода расстояния
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item2 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)

    if message.photo or message.video or message.document or message.animation or message.sticker or message.audio or message.contact or message.voice or message.video_note:
        sent = bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.", reply_markup=markup)
        bot.register_next_step_handler(sent, process_custom_distance_step)
        return

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    try:
        custom_distance = float(message.text)
        bot.send_message(chat_id, f"Вы ввели своё расстояние: {custom_distance:.2f} км.", reply_markup=markup)
        # Переход к следующему шагу, например, вводу даты поездки
        sent = bot.send_message(chat_id, "Введите дату поездки в формате ДД.ММ.ГГГГ:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_date_step, custom_distance)
    except ValueError:
        sent = bot.send_message(chat_id, "Пожалуйста, введите корректное число для расстояния.", reply_markup=markup)
        bot.register_next_step_handler(sent, process_custom_distance_step)


def process_date_step(message, distance):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item2 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return    
    if message.text == "В главное меню":
        return_to_menu(message) 
        return    

    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        sent = bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, process_date_step) 
        return

    date = message.text
    date_pattern = r"\d{2}\.\d{2}\.\d{4}"
    
    if re.match(date_pattern, date):
        day, month, year = map(int, date.split('.'))
        try:
            datetime(year, month, day)  # Проверяем правильность даты
            
            # Переходим сразу к выбору топлива, передавая рассчитанное расстояние и дату
            show_fuel_types(chat_id, date, distance)
        except ValueError:
            sent = bot.send_message(chat_id, "Неправильная дата. Пожалуйста, введите корректную дату в формате ДД.ММ.ГГГГ.")
            bot.register_next_step_handler(sent, process_date_step, distance)
    else:
        sent = bot.send_message(chat_id, "Неправильный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")
        bot.register_next_step_handler(sent, process_date_step, distance)


def show_fuel_types(chat_id, date, distance):
    # Создаём клавиатуру с типами топлива и дополнительными кнопками
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    
    # Добавляем кнопки с типами топлива
    row1 = [KeyboardButton(fuel_type) for fuel_type in fuel_types[:3]] 
    row2 = [KeyboardButton(fuel_type) for fuel_type in fuel_types[3:]] 
    
    # Добавляем кнопки для возврата в меню и главное меню
    row3 = [KeyboardButton("Вернуться в меню расчета топлива"), KeyboardButton("В главное меню")]
    
    markup.add(*row1, *row2, *row3)
    
    sent = bot.send_message(chat_id, "Выберите тип топлива:", reply_markup=markup)
    bot.register_next_step_handler(sent, process_fuel_type, date, distance)


def clean_price(price):
    # Удаляем все символы, кроме цифр и точек
    cleaned_price = re.sub(r'[^\d.]', '', price)
    if cleaned_price.count('.') > 1:
        cleaned_price = cleaned_price[:cleaned_price.find('.') + 1] + cleaned_price[cleaned_price.find('.') + 1:].replace('.', '')
    return cleaned_price

def get_average_fuel_prices():
    url = 'https://azsprice.ru/benzin-cheboksary?ysclid=m1fguy8a6w869590461'  # Замените на URL сайта
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table')
    fuel_prices = {}

    rows = table.find_all('tr')
    
    for row in rows[1:]:
        columns = row.find_all('td')
        if len(columns) < 5:
            continue
        
        fuel_type = columns[2].text.strip()  # Марка топлива
        today_price = clean_price(columns[3].text.strip())  # Цена на топливо
        
        if today_price:
            try:
                price = float(today_price)

                # Если это первый раз, когда мы видим эту марку топлива, инициализируем список
                if fuel_type not in fuel_prices:
                    fuel_prices[fuel_type] = []
                
                # Добавляем цену в список
                fuel_prices[fuel_type].append(price)
            except ValueError:
                print(f"Не удалось преобразовать цену: {today_price}")

    # Возвращаем словарь, где для каждой марки топлива указана средняя цена
    average_prices = {}
    for fuel_type, prices in fuel_prices.items():
        average_prices[fuel_type] = sum(prices) / len(prices)  # Среднее значение

    return average_prices


def process_fuel_type(message, date, distance):
    chat_id = message.chat.id
    fuel_type = message.text.strip().lower()

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return    
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    fuel_type_mapping = {
        "газ": "газ спбт",
        "аи-92": "аи-92",
        "аи-95": "аи-95",
        "аи-98": "аи-98",
        "дт": "дт",
    }

    if fuel_type not in fuel_type_mapping:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите тип топлива только из предложенных вариантов.")
        bot.register_next_step_handler(sent, process_fuel_type, date, distance)
        return
    
    actual_fuel_type = fuel_type_mapping[fuel_type]
    
    try:
        fuel_prices = get_average_fuel_prices()
        fuel_prices_lower = {key.lower(): value for key, value in fuel_prices.items()}
        price_per_liter = fuel_prices_lower.get(actual_fuel_type.lower())

        if price_per_liter is None:
            raise ValueError("Price not found")

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item5 = types.KeyboardButton("Вернуться в меню расчета топлива")
        item6 = types.KeyboardButton("В главное меню")
        markup.add(item5)
        markup.add(item6)

        bot.send_message(chat_id, f"Вы выбрали тип топлива: {fuel_type.upper()}.", reply_markup=types.ReplyKeyboardRemove())
        bot.send_message(chat_id, f"Актуальная средняя цена для {fuel_type.upper()} в РФ: {price_per_liter:.2f} руб./л.", reply_markup=markup)
        
        sent = bot.send_message(chat_id, "Введите расход топлива на 100 км:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_fuel_consumption_step, date, distance, fuel_type, price_per_liter)

    except Exception as e:
        print(f"Ошибка получения цены: {e}")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Ввести свою цену")
        item2 = types.KeyboardButton("Повторить выбор топлива")
        item3 = types.KeyboardButton("Вернуться в меню расчета топлива")
        item4 = types.KeyboardButton("В главное меню")
        markup.add(item1, item2, item3, item4)
        
        sent = bot.send_message(chat_id, "Не удалось получить цену для выбранного типа топлива. Вы можете ввести свою цену или повторить выбор топлива.", reply_markup=markup)
        bot.register_next_step_handler(sent, handle_price_input_or_retry, date, distance, fuel_type)

def handle_price_input_or_retry(message, date, distance, fuel_type):
    chat_id = message.chat.id
    
    if message.text == "Ввести свою цену":
        sent = bot.send_message(chat_id, "Пожалуйста, введите цену за литр топлива:")
        bot.register_next_step_handler(sent, process_price_per_liter_step, date, distance, fuel_type)
    elif message.text == "Повторить выбор топлива":
        show_fuel_types(chat_id, date, distance)
    elif message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
    elif message.text == "В главное меню":
        return_to_menu(message)
    else:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите один из предложенных вариантов.")
        bot.register_next_step_handler(sent, handle_price_input_or_retry, date, distance, fuel_type)

# (9.10) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (ФУНКЦИЯ ДЛЯ ВВОДА РАСХОДА НА 100 КМ) ---------------

def process_price_per_liter_step(message, date, distance, fuel_type):
    chat_id = message.chat.id

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return    
    if message.text == "В главное меню":
        return_to_menu(message) 
        return    

    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        sent = bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, process_price_per_liter_step, date, distance, fuel_type)
        return

    input_text = message.text.replace(',', '.')
    
    try:
        price_per_liter = float(input_text)
        if price_per_liter <= 0:
            raise ValueError
        
        # Создаем новую клавиатуру с нужными кнопками
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
        item2 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2)

        # Запрашиваем расход топлива
        sent = bot.send_message(chat_id, "Введите расход топлива на 100 км:", reply_markup=markup)
        bot.clear_step_handler_by_chat_id(chat_id)  # Очистка предыдущего хендлера
        bot.register_next_step_handler(sent, process_fuel_consumption_step, date, distance, fuel_type, price_per_liter)
        
    except ValueError:
        sent = bot.send_message(chat_id, "Пожалуйста, введите положительное число для цены топлива за литр:")
        bot.register_next_step_handler(sent, process_price_per_liter_step, date, distance, fuel_type)

# (9.11) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (ФУНКЦИЯ ДЛЯ ПАССАЖИРОВ ) ---------------

def process_fuel_consumption_step(message, date, distance, fuel_type, price_per_liter):
    chat_id = message.chat.id
    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return
    if message.text == "В главное меню":
        return_to_menu(message) 
        return
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        sent = bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, process_fuel_consumption_step, date, distance, fuel_type, price_per_liter)
        return
    input_text = message.text.replace(',', '.') 
    try:
        fuel_consumption = float(input_text)
        if fuel_consumption <= 0:
            raise ValueError
        sent = bot.send_message(chat_id, "Введите количество пассажиров в машине:")
        bot.clear_step_handler_by_chat_id(chat_id) 
        bot.register_next_step_handler(sent, process_passengers_step, date, distance, fuel_type, price_per_liter, fuel_consumption)
    except ValueError:
        sent = bot.send_message(chat_id, "Пожалуйста, введите положительное число для расхода топлива на 100 км:")
        bot.register_next_step_handler(sent, process_fuel_consumption_step, date, distance, fuel_type, price_per_liter)

# (9.12) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (ФУНКЦИЯ ДЛЯ РАСЧЕТА) ---------------

def process_passengers_step(message, date, distance, fuel_type, price_per_liter, fuel_consumption):
    chat_id = message.chat.id
    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        sent = bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, process_passengers_step, date, distance, fuel_type, price_per_liter, fuel_consumption)
        return
    try:
        passengers = int(message.text)
        if passengers <= 0:
            raise ValueError

        # Считаем стоимость топлива
        fuel_cost = (distance / 100) * fuel_consumption * price_per_liter
        fuel_cost_per_person = fuel_cost / passengers

        # Получаем координаты начального и конечного местоположений
        start_location = trip_data[chat_id]['start_location']
        end_location = trip_data[chat_id]['end_location']
        
        # Сформируем ссылку на Яндекс.Карты для автомобилиста
        yandex_maps_url = f"https://yandex.ru/maps/?rtext={start_location['latitude']},{start_location['longitude']}~{end_location['latitude']},{end_location['longitude']}&rtt=auto"
        
        # Отправляем запрос на clck.ru для сокращения ссылки
        try:
            response = requests.get(f'https://clck.ru/--?url={yandex_maps_url}')
            short_url = response.text
        except Exception as e:
            bot.send_message(chat_id, f"Не удалось сократить ссылку: {str(e)}")
            short_url = yandex_maps_url  # Используем оригинальную ссылку, если сокращение не удалось
        
        if chat_id not in temporary_trip_data:
            temporary_trip_data[chat_id] = []
        
        # Добавляем временные данные поездки
        temporary_trip_data[chat_id].append({
            "start_location": start_location,
            "end_location": end_location,
            "date": date,
            "distance": distance,
            "fuel_type": fuel_type,
            "price_per_liter": price_per_liter,
            "fuel_consumption": fuel_consumption,
            "passengers": passengers,
            "fuel_spent": (distance / 100) * fuel_consumption,
            "fuel_cost": fuel_cost,
            "fuel_cost_per_person": fuel_cost_per_person,
            "route_link": short_url  # Сохраняем сокращенную ссылку в временные данные
        })

        display_summary(chat_id, fuel_cost, fuel_cost_per_person, fuel_type, date, distance, price_per_liter, fuel_consumption, passengers)
    except ValueError:
        sent = bot.send_message(chat_id, "Пожалуйста, введите положительное целое число для количества пассажиров:")
        bot.register_next_step_handler(sent, process_passengers_step, date, distance, fuel_type, price_per_liter, fuel_consumption)

# (9.13) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (ИТОГОВАЯ ИНФОРМАЦИЯ) ---------------

def display_summary(chat_id, fuel_cost, fuel_cost_per_person, fuel_type, date, distance, price_per_liter, fuel_consumption, passengers):
    fuel_spent = (distance / 100) * fuel_consumption 

    # Получаем координаты начального и конечного местоположений
    start_location = trip_data[chat_id]['start_location']
    end_location = trip_data[chat_id]['end_location']
    
    # Сформируем ссылку на Яндекс.Карты для автомобилиста
    yandex_maps_url = f"https://yandex.ru/maps/?rtext={start_location['latitude']},{start_location['longitude']}~{end_location['latitude']},{end_location['longitude']}&rtt=auto"
    
    # Отправляем запрос на clck.ru для сокращения ссылки
    try:
        response = requests.get(f'https://clck.ru/--?url={yandex_maps_url}')
        short_url = response.text
    except Exception as e:
        bot.send_message(chat_id, f"Не удалось сократить ссылку: {str(e)}")
        short_url = yandex_maps_url  # Используем оригинальную ссылку, если сокращение не удалось

    # Формируем итоговое сообщение
    summary_message = "ИНФОРМАЦИЯ О ПОЕЗДКЕ:\n"
    summary_message += f"Начальное местоположение:\n{start_location['address']}\n"
    summary_message += f"Конечное местоположение:\n{end_location['address']}\n"
    summary_message += f"Дата поездки: {date}\n"
    summary_message += f"Расстояние: {distance:.2f} км.\n"
    summary_message += f"Тип топлива: {fuel_type}\n"
    summary_message += f"Цена топлива за литр: {price_per_liter:.2f} руб.\n"
    summary_message += f"Расход топлива на 100 км: {fuel_consumption} л.\n"
    summary_message += f"Количество пассажиров: {passengers}\n"
    summary_message += f"ПОТРАЧЕНО ЛИТРОВ ТОПЛИВА: {fuel_spent:.2f} л.\n"
    summary_message += f"СТОИМОСТЬ ТОПЛИВА ДЛЯ ПОЕЗДКИ: {fuel_cost:.2f} руб.\n"
    summary_message += f"СТОИМОСТЬ ТОПЛИВА НА ЧЕЛОВЕКА: {fuel_cost_per_person:.2f} руб.\n"
    summary_message += f"[ССЫЛКА НА МАРШРУТ]({short_url})\n"

    summary_message = summary_message.replace('\n', '\n\n')
    bot.clear_step_handler_by_chat_id(chat_id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item2 = types.KeyboardButton("Сохранить поездку")
    item3 = types.KeyboardButton("В главное меню")
    markup.add(item2)
    markup.add(item1)
    markup.add(item3)

    bot.send_message(chat_id, summary_message, reply_markup=markup, parse_mode="Markdown")

# (9.14) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (КОМАНДА "СОХРАНИТЬ ПОЕЗДКУ") ---------------

@bot.message_handler(func=lambda message: message.text == "Сохранить поездку")
def save_data_handler(message):
    user_id = message.chat.id
    if user_id in temporary_trip_data and temporary_trip_data[user_id]:
        if user_id not in user_trip_data:
            user_trip_data[user_id] = []
        
        # Переносим данные из временных данных в постоянные
        user_trip_data[user_id].extend(temporary_trip_data[user_id])

        # Очищаем временные данные
        temporary_trip_data[user_id] = []
        
        # Сохраняем данные поездки в базу данных
        save_trip_data(user_id) 

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
        item2 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2)
        
        bot.send_message(user_id, "Данные поездки успешно сохранены.", reply_markup=markup)
    else:
        bot.send_message(user_id, "У вас нет данных для сохранения поездки.")

# (9.15) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (КОМАНДА "В ГЛАВНОЕ МЕНЮ  ВРЕМЕННЫХ ДАННЫХ") ---------------

@bot.message_handler(func=lambda message: message.text == "В главное меню")
@bot.message_handler(commands=['mainmenu'])
def return_to_menu(message):
    user_id = message.chat.id
    if user_id in temporary_trip_data:
        temporary_trip_data[user_id] = []
    start(message)

# (9.16) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (КОМАНДА "ВЕРНУТЬСЯ В МЕНЮ РАСЧЕТА ТОПЛИВА   ВРЕМЕННЫХ ДАННЫХ") ---------------

@bot.message_handler(func=lambda message: message.text == "Вернуться в меню расчета топлива")
@bot.message_handler(commands=['restart1'])
def restart_handler(message):
    user_id = message.chat.id

    reset_and_start_over(user_id)

    if user_id not in user_trip_data:
        user_trip_data[user_id] = load_trip_data(user_id)
    user_trip_data[user_id] = load_trip_data(user_id)
    
    start_fuel_calculation_menu(message)

# (9.17) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (КОМАНДА "ПОСМОТРЕТЬ ПОЕЗДКИ") ---------------

@bot.message_handler(func=lambda message: message.text == "Посмотреть поездки")
def view_trips(message):
    user_id = message.chat.id
    if user_id in user_trip_data:
        trips = user_trip_data[user_id]
        if not trips:
            bot.send_message(user_id, "У вас нет сохраненных поездок.")
        else:
            # Создаем кнопки для выбора поездок
            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            for i, trip in enumerate(trips, start=1):
                start_address = trip['start_location']['address']
                end_address = trip['end_location']['address']
                button_text = f"{i}. {start_address} - {end_address}"
                markup.add(button_text)
            
            # Добавляем кнопки "Вернуться в меню расчета топлива" и "В главное меню"
            markup.add("Вернуться в меню расчета топлива")
            markup.add("В главное меню")
            
            # Отправляем сообщение с запросом на выбор поездки и кнопками
            bot.send_message(user_id, "Выберите поездку для просмотра:", reply_markup=markup)
    else:
        bot.send_message(user_id, "У вас нет сохраненных поездок.")

@bot.message_handler(func=lambda message: message.text and message.text.startswith(tuple([f"{i}. " for i in range(1, 10)])))
def show_trip_details(message):
    user_id = message.chat.id
    trips = user_trip_data.get(user_id, [])
    
    # Получаем номер поездки из сообщения пользователя
    try:
        trip_index = int(message.text.split(".")[0]) - 1  # Получаем индекс поездки
        trip = trips[trip_index]

        # Формируем сообщение с данными поездки
        start_address = trip['start_location']['address']
        end_address = trip['end_location']['address']
        summary_message = f"ИТОГОВЫЕ ДАННЫЕ ПОЕЗДКИ {trip_index + 1}:\n\n"
        summary_message += f"Начальное местоположение:\n\n{start_address}\n\n"
        summary_message += f"Конечное местоположение:\n\n{end_address}\n\n"
        summary_message += f"Дата поездки: {trip['date']}\n\n"
        summary_message += f"Расстояние: {trip['distance']:.2f} км.\n\n"
        summary_message += f"Тип топлива: {trip['fuel_type']}\n\n"
        summary_message += f"Цена топлива за литр: {trip['price_per_liter']:.2f} руб.\n\n"
        summary_message += f"Расход топлива на 100 км: {trip['fuel_consumption']} л.\n\n"
        summary_message += f"Количество пассажиров: {trip['passengers']}\n\n"
        summary_message += f"ПОТРАЧЕНО ЛИТРОВ ТОПЛИВА: {trip['fuel_spent']:.2f} л.\n\n"
        summary_message += f"СТОИМОСТЬ ТОПЛИВА ДЛЯ ПОЕЗДКИ: {trip['fuel_cost']:.2f} руб.\n\n"
        summary_message += f"СТОИМОСТЬ ТОПЛИВА НА ЧЕЛОВЕКА: {trip['fuel_cost_per_person']:.2f} руб.\n\n"

        # Проверяем, есть ли 'route_link' в данных поездки
        if 'route_link' in trip:
            summary_message += f"[ССЫЛКА НА МАРШРУТ]({trip['route_link']})\n\n"
        else:
            summary_message += "Ссылка на маршрут недоступна.\n\n"

        # Отправляем подробную информацию о поездке
        bot.send_message(user_id, summary_message, parse_mode="Markdown")

        # Оставляем клавиатуру с кнопками после просмотра поездки
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("Посмотреть другие поездки")  # Эта кнопка будет выше
        markup.row("Вернуться в меню расчета топлива", "В главное меню")  # Эти кнопки будут на одной строке
        
        bot.send_message(user_id, "Вы можете посмотреть другие поездки или вернуться в меню.", reply_markup=markup)

    except (IndexError, ValueError):
        bot.send_message(user_id, "Ошибка при выборе поездки. Попробуйте снова.")

# Обработчик для кнопки "Посмотреть другие поездки"
@bot.message_handler(func=lambda message: message.text == "Посмотреть другие поездки")
def view_other_trips(message):
    view_trips(message)  # Вызываем функцию для повторного отображения списка поездок

# Обработчики для кнопок "Вернуться в меню расчета топлива" и "В главное меню"
@bot.message_handler(func=lambda message: message.text == "Вернуться в меню расчета топлива")
def return_to_fuel_calc_menu(message):
    chat_id = message.chat.id
    reset_and_start_over(chat_id)  # Ваша функция для сброса и возвращения в меню расчета топлива
    bot.send_message(chat_id, "Вы вернулись в меню расчета топлива.", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: message.text == "В главное меню")
def return_to_main_menu(message):
    chat_id = message.chat.id
    return_to_menu(message)  # Ваша функция для возврата в главное меню
    bot.send_message(chat_id, "Вы вернулись в главное меню.", reply_markup=types.ReplyKeyboardRemove())

# (9.18) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (КОМАНДА "УДАЛИТЬ ПОЕЗДКУ") ---------------

@bot.message_handler(func=lambda message: message.text == "Удалить поездку")
def ask_for_trip_to_delete(message):
    user_id = message.chat.id

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(user_id)
        return

    if user_id in user_trip_data:
        if user_trip_data[user_id]:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            
            for i in range(1, len(user_trip_data[user_id]) + 1):
                markup.add(types.KeyboardButton(str(i)))

            markup.add(types.KeyboardButton("Удалить все поездки"))
            markup.add(types.KeyboardButton("Вернуться в меню расчета топлива"))
            markup.add(types.KeyboardButton("В главное меню"))
            
            bot.send_message(user_id, "Выберите номер поездки для удаления или нажмите 'Удалить все поездки' для удаления всех поездок:", reply_markup=markup)
            bot.register_next_step_handler(message, confirm_trip_deletion)
        else:
            bot.send_message(user_id, "У вас нет поездок для удаления.")
            reset_and_start_over(user_id)
    else:
        bot.send_message(user_id, "У вас нет сохраненных поездок.")

# (9.19) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (ОБРАБОТЧИК УДАЛЕНИЯ ПОЕЗДКИ) ---------------

def confirm_trip_deletion(message):
    user_id = message.chat.id

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text == "Удалить все поездки":
        bot.send_message(user_id, "Вы уверены, что хотите удалить все поездки? (да/нет)")
        bot.register_next_step_handler(message, confirm_delete_all)
        return

    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        return
    
    if user_id not in user_trip_data or not user_trip_data[user_id]:
        bot.send_message(user_id, "У вас нет сохраненных поездок.")
        return

    if not message.text.isdigit():
        bot.send_message(user_id, "Пожалуйста, выберите номер поездки для удаления с помощью кнопок.")
        return

    trip_number = int(message.text)
    if 1 <= trip_number <= len(user_trip_data[user_id]):
        deleted_trip = user_trip_data[user_id].pop(trip_number - 1)
        bot.send_message(user_id, f"Поездка номер {trip_number} успешно удалена.")
    else:
        bot.send_message(user_id, "Неверный номер поездки. Пожалуйста, укажите корректный номер.")

    reset_and_start_over(user_id)

# (9.20) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (ФУНКЦИЯ ПОДТВЕРЖДЕНИЯ УДАЛЕНИЯ ВСЕХ ПОЕЗДОК) ---------------

def confirm_delete_all(message):
    user_id = message.chat.id
    
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_all)
        return 

    if message.text is None:
        bot.send_message(user_id, "Пожалуйста, отправьте текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_all)
        return

    user_response = message.text.lower()

    if user_response == "да":
        if user_id in user_trip_data and user_trip_data[user_id]:
            user_trip_data[user_id].clear()
            bot.send_message(user_id, "Все поездки были успешно удалены.")
        else:
            bot.send_message(user_id, "У вас нет поездок для удаления.")
        reset_and_start_over(user_id)
    elif user_response == "нет":
        bot.send_message(user_id, "Удаление всех поездок отменено.")
        reset_and_start_over(user_id)
    else:
        bot.send_message(user_id, "Пожалуйста, ответьте 'Да' для подтверждения или 'Нет' для отмены.")
        bot.register_next_step_handler(message, confirm_delete_all)

# (10) --------------- КОД ДЛЯ "ТРАТ" ---------------

# (10.1) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "ТРАТЫ И РЕМОНТЫ") ---------------

@bot.message_handler(func=lambda message: message.text == "Траты и ремонты")
def handle_expenses_and_repairs(message):
    user_id = message.from_user.id

    expense_data = load_expense_data(user_id).get(str(user_id), {})
    repair_data = load_repair_data(user_id).get(str(user_id), {})

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Записать трату")
    item2 = types.KeyboardButton("Посмотреть траты")
    item3 = types.KeyboardButton("Записать ремонт")
    item4 = types.KeyboardButton("Посмотреть ремонты")
    item5 = types.KeyboardButton("Удалить траты")
    item6 = types.KeyboardButton("Удалить ремонты")
    item7 = types.KeyboardButton("В главное меню")

    markup.add(item1, item3)
    markup.add(item2, item4)
    markup.add(item5, item6)
    markup.add(item7)

    bot.clear_step_handler_by_chat_id(user_id)
    bot.send_message(user_id, "Меню для учета трат и ремонтов. Выберите действие:", reply_markup=markup)

# (10.3) --------------- КОД ДЛЯ "ТРАТ" (ПРОВЕРКА НА МУЛЬТИМЕДИЮ) ---------------

def contains_media(message):
    return (message.photo or message.video or message.document or message.animation or
            message.sticker or message.location or message.audio or message.contact or
            message.voice or message.video_note)

# (10.4) --------------- КОД ДЛЯ "ТРАТ" (ВОЗВРАТ В МЕНЮ) ---------------

def send_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Записать трату")
    item2 = types.KeyboardButton("Посмотреть траты")
    item3 = types.KeyboardButton("Записать ремонт")
    item4 = types.KeyboardButton("Посмотреть ремонты")
    item5 = types.KeyboardButton("Удалить траты")
    item6 = types.KeyboardButton("Удалить ремонты")
    item7 = types.KeyboardButton("В главное меню")

    markup.add(item1, item3)
    markup.add(item2, item4)
    markup.add(item5, item6)
    markup.add(item7)

    bot.send_message(user_id, "Вы вернулись в меню. Выберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Вернуться в меню трат и ремонтов")
@bot.message_handler(commands=['restart2'])
def return_to_menu_2(message):
    user_id = message.from_user.id
    send_menu(user_id)

# (10.5) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "ЗАПИСАТЬ ТРАТУ") ---------------

@bot.message_handler(func=lambda message: message.text == "Записать трату")
def record_expense(message):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, record_expense)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
        item_main_menu = types.KeyboardButton("В главное меню")
        markup.add(item_return)
        markup.add(item_main_menu)
        bot.send_message(user_id, "Введите название траты:", reply_markup=markup)
        bot.register_next_step_handler(message, get_expense_name)

# (10.6) --------------- КОД ДЛЯ "ТРАТ" (ФУНКЦИЯ ИМЯ ТРАТЫ) ---------------

def get_expense_name(message):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    expense_name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)
    
    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, get_expense_name)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
        item_main_menu = types.KeyboardButton("В главное меню")
        markup.add(item_return)
        markup.add(item_main_menu)
        bot.send_message(user_id, "Введите дату траты в формате ДД.ММ.ГГГГ:", reply_markup=markup)
        bot.register_next_step_handler(message, get_expense_date, expense_name)

# (10.7) --------------- КОД ДЛЯ "ТРАТ" (ФУНКЦИЯ ДАТА ТРАТЫ) ---------------

def get_expense_date(message, expense_name):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return
    
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    expense_date = message.text

    if expense_date is None:
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, get_expense_name)
        return

    date_parts = expense_date.split(".")
    if len(date_parts) != 3:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
        item_main_menu = types.KeyboardButton("В главное меню")
        markup.add(item_return)
        markup.add(item_main_menu)
        bot.send_message(user_id, "Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")
        bot.register_next_step_handler(message, get_expense_date, expense_name)
        return

    day, month, year = date_parts

    if not day.isdigit() or not month.isdigit() or not year.isdigit():
        bot.send_message(user_id, "Пожалуйста, введите дату в числовом формате.")
        bot.register_next_step_handler(message, get_expense_date, expense_name)
        return

    day = int(day)
    month = int(month)
    year = int(year)

    if len(str(year)) != 4:
        bot.send_message(user_id, "Пожалуйста, введите корректную дату.")
        bot.register_next_step_handler(message, get_expense_date, expense_name)
        return

    if day < 1 or day > 31 or month < 1 or month > 12:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
        item_main_menu = types.KeyboardButton("В главное меню")
        markup.add(item_return)
        markup.add(item_main_menu)
        bot.send_message(user_id, "Пожалуйста, введите корректную дату.", reply_markup=markup)
        bot.register_next_step_handler(message, get_expense_date, expense_name)
        return

    bot.send_message(user_id, "Введите сумму траты:")
    bot.register_next_step_handler(message, get_expense_amount, expense_name, expense_date)

def is_numeric(s):
    if s is not None:
        try:
            float(s)
            return True
        except ValueError:
            return False
    return False

# (10.8) --------------- КОД ДЛЯ "ТРАТ" (СУММА ТРАТЫ) ---------------

def get_expense_amount(message, expense_name, expense_date):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id) 
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    expense_amount = message.text

    if expense_amount is not None:
        expense_amount = expense_amount.replace(",", ".")

    if expense_date is None:
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, get_expense_name)
        return

    if not is_numeric(expense_amount):
        bot.send_message(user_id, "Пожалуйста, введите сумму траты в числовом формате.")
        bot.register_next_step_handler(message, get_expense_amount, expense_name, expense_date)
        return

    data = load_expense_data(user_id)

    if str(user_id) not in data:
        data[str(user_id)] = {"expenses": []}

    expenses = data[str(user_id)].get("expenses", [])

    expenses.append({
        "name": expense_name,
        "date": expense_date,
        "amount": expense_amount
    })

    data[str(user_id)]["expenses"] = expenses

    save_expense_data(user_id, data)

    bot.send_message(user_id, "Трата успешно записана!")

# (10.9) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "ПОСМОТРЕТЬ ТРАТЫ") ---------------

@bot.message_handler(func=lambda message: message.text == "Посмотреть траты")
def view_expenses(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Траты (месяц)")
    item2 = types.KeyboardButton("Траты (год)")
    item3 = types.KeyboardButton("Траты (всё время)")
    item4 = types.KeyboardButton("Траты (на заправки)")
    item5 = types.KeyboardButton("Траты (на штрафы)")
    item6 = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item7 = types.KeyboardButton("В главное меню")

    markup.add(item1, item2, item3, item4, item5)
    markup.add(item6,item7)

    bot.send_message(user_id, "Выберите вариант просмотра трат:", reply_markup=markup)

# (10.10) --------------- КОД ДЛЯ "ТРАТ" (ФУНКЦИЯ МАКСИМАЛЬНОГО СООБЩЕНИЯ) ---------------

MAX_MESSAGE_LENGTH = 4096 

def send_message_with_split(user_id, message_text):
    if len(message_text) <= MAX_MESSAGE_LENGTH:
        bot.send_message(user_id, message_text)
    else:
        message_parts = [message_text[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message_text), MAX_MESSAGE_LENGTH)]
        for part in message_parts:
            bot.send_message(user_id, part)

# (10.11) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "ТРАТЫ ЗА МЕСЯЦ") ---------------

@bot.message_handler(func=lambda message: message.text == "Траты (месяц)")
def view_expenses_by_month(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    markup.add(item_return)

    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для просмотра трат за этот период:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expenses_by_month)

valid_months = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
item_main_menu = types.KeyboardButton("В главное меню")
markup.add(item_return)
markup.add(item_main_menu)

# (10.12) --------------- КОД ДЛЯ "ТРАТ" (ФУНКЦИЯ ТРАТЫ ЗА МЕСЯЦ) ---------------

def get_expenses_by_month(message):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, get_expenses_by_month)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id) 
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    date = message.text

    if "." in date:
        parts = date.split(".")
        if len(parts) == 2:
            month, year = map(int, parts)
            if 1 <= month <= 12 and len(str(year)) == 4:
                user_data = load_expense_data(user_id)
                expenses = user_data.get(str(user_id), {}).get("expenses", [])

                total_expenses = 0
                expense_details = []

                for index, expense in enumerate(expenses, start=1):
                    expense_date = expense.get("date", "")
                    expense_date_parts = expense_date.split(".")
                    if len(expense_date_parts) >= 2:
                        expense_month, expense_year = map(int, expense_date_parts[1:3])
                    else:
                        expense_month = 0
                        expense_year = 0

                    if expense_month == month and expense_year == year:
                        amount = float(expense.get("amount", 0))
                        total_expenses += amount

                        expense_name = expense.get("name", "Без названия")
                        expense_date = expense.get("date", "Без даты")
                        expense_month = expense_month
                        expense_year = expense_year

                        expense_details.append(
                            f"  №: {index}\n\n"
                            f"    НАЗВАНИЕ: {expense_name}\n"
                            f"    ДАТА: {expense_date}\n"
                            f"    СУММА: {amount} руб.\n"
                        )

                if expense_details:
                    message_text = f"Траты за {date}:\n\n" + "\n\n".join(expense_details)
                else:
                    message_text = f"За {date} трат не найдено."

                send_message_with_split(user_id, message_text)

                bot.send_message(user_id, f"Итоговая сумма трат за {date}: {total_expenses} руб.")
            else:
                bot.send_message(user_id, "Пожалуйста, введите корректный месяц и год в формате ММ.ГГГГ.", reply_markup=markup)
                bot.register_next_step_handler(message, get_expenses_by_month)  
        else:
            bot.send_message(user_id, "Пожалуйста, введите дату в формате ММ.ГГГГ.", reply_markup=markup)
            bot.register_next_step_handler(message, get_expenses_by_month)  
    else:
        bot.send_message(user_id, "Пожалуйста, введите дату в формате ММ.ГГГГ.", reply_markup=markup)
        bot.register_next_step_handler(message, get_expenses_by_month)  

# (10.13) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "ТРАТЫ ЗА ГОД") ---------------

@bot.message_handler(func=lambda message: message.text == "Траты (год)")
def view_expenses_by_year(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите год в формате (ГГГГ) для просмотра трат за этот год:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expenses_by_year)

# (10.14) --------------- КОД ДЛЯ "ТРАТ" (ФУНКЦИЯ ТРАТЫ ЗА ГОД) ---------------

def get_expenses_by_year(message):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, get_expenses_by_year)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    year = message.text.strip()

    if not year.isdigit() or len(year) != 4:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
        item_main_menu = types.KeyboardButton("В главное меню")
        markup.add(item_return)
        markup.add(item_main_menu)

        bot.send_message(user_id, "Пожалуйста, введите год в формате ГГГГ.", reply_markup=markup)
        bot.register_next_step_handler(message, get_expenses_by_year)
        return

    year = int(year)

    user_data = load_expense_data(user_id)
    expenses = user_data.get(str(user_id), {}).get("expenses", [])

    total_expenses = 0
    expenses_for_year = []

    for index, expense in enumerate(expenses, 1):
        expense_date = expense.get("date", "")
        if "." in expense_date:
            date_parts = expense_date.split(".")
            if len(date_parts) >= 3:
                expense_year = int(date_parts[2])
                if expense_year == year:
                    expense_amount = float(expense.get("amount", 0.0))
                    total_expenses += expense_amount
                    expenses_for_year.append({
                        "number": index,
                        "name": expense.get("name", ""),
                        "date": expense_date,
                        "month": date_parts[1],
                        "year": date_parts[2],
                        "amount": expense_amount
                    })

    response_message = f"Траты за {year} год:\n\n"
    for expense_info in expenses_for_year:
        response_message += f"  №: {expense_info['number']}\n\n"
        response_message += f"    НАЗВАНИЕ: {expense_info['name']}\n"
        response_message += f"    ДАТА: {expense_info['date']}\n"
        response_message += f"    СУММА: {expense_info['amount']:.2f} руб.\n\n"

    send_message_with_split(user_id, response_message)

    bot.send_message(user_id, f"Итоговая сумма трат за {year} год: {total_expenses:.2f} руб.")

# (10.15) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "ТРАТЫ ЗА ВСЁ ВРЕМЯ") ---------------

@bot.message_handler(func=lambda message: message.text == "Траты (всё время)")
def view_all_expenses(message):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)  
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    user_data = load_expense_data(user_id)
    expenses = user_data.get(str(user_id), {}).get("expenses", [])

    if expenses:
        total_expenses = 0
        expense_details = []

        for index, expense in enumerate(expenses, start=1):
            expense_name = expense.get("name", "Без названия")
            expense_date = expense.get("date", "Без даты")
            amount = float(expense.get("amount", 0))
            total_expenses += amount

            expense_details.append(
                f"  №: {index}\n\n"
                f"    НАЗВАНИЕ: {expense_name}\n"
                f"    ДАТА: {expense_date}\n"
                f"    СУММА: {amount} руб.\n"
            )

        if expense_details:
            message_text = "Все расходы:\n\n" + "\n\n".join(expense_details)
        else:
            message_text = "У вас пока нет трат."

        send_message_with_split(user_id, message_text)

        bot.send_message(user_id, f"Итоговая сумма трат за всё время: {total_expenses} руб.")
    else:
        bot.send_message(user_id, "У вас пока нет трат.")

# (10.16) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "ТРАТЫ НА ЗАПРАВКИ") ---------------

@bot.message_handler(func=lambda message: message.text == "Траты (на заправки)")
def view_fuel_expenses(message):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id) 
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    user_data = load_expense_data(user_id)
    expenses = user_data.get(str(user_id), {}).get("expenses", [])

    fuel_expenses = []
    total_fuel_expenses = 0.0

    for index, expense in enumerate(expenses, start=1):
        expense_name = expense.get("name", "").lower()
        if "заправка" in expense_name or "топливо" in expense_name or "бензин" in expense_name or "азс" in expense_name or "газ" in expense_name or "дизель" in expense_name:
            amount = float(expense.get("amount", 0.0))
            total_fuel_expenses += amount

            expense_date = expense.get("date", "Без даты")
            fuel_expenses.append(
                f"  №: {index}\n\n"
                f"    НАЗВАНИЕ: {expense_name}\n"
                f"    ДАТА: {expense_date}\n"
                f"    СУММА: {amount} руб.\n"
            )

    if fuel_expenses:
        message_text = "Траты на заправку:\n\n" + "\n\n".join(fuel_expenses)

        send_message_with_split(user_id, message_text)

        bot.send_message(user_id, f"Итоговая сумма трат на заправку: {total_fuel_expenses:.2f} руб.")
    else:
        bot.send_message(user_id, "У вас пока нет трат на заправки.")

# (10.17) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "ТРАТЫ НА ШТРАФЫ") ---------------

@bot.message_handler(func=lambda message: message.text == "Траты (на штрафы)")
def view_penalty_expenses(message):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    user_data = load_expense_data(user_id)
    expenses = user_data.get(str(user_id), {}).get("expenses", [])

    penalty_expenses = []
    total_penalty_expenses = 0.0

    for index, expense in enumerate(expenses, start=1):
        expense_name = expense.get("name", "").lower()
        if "штраф" in expense_name:
            amount = float(expense.get("amount", 0.0))
            total_penalty_expenses += amount

            expense_date = expense.get("date", "Без даты")
            penalty_expenses.append(
                f"  №: {index}\n\n"
                f"    НАЗВАНИЕ: {expense_name}\n"
                f"    ДАТА: {expense_date}\n"
                f"    СУММА: {amount} руб.\n"
            )

    if penalty_expenses:
        message_text = "Траты на штрафы:\n\n" + "\n\n".join(penalty_expenses)

        send_message_with_split(user_id, message_text)

        bot.send_message(user_id, f"Итоговая сумма трат на штрафы: {total_penalty_expenses:.2f} руб.")
    else:
        bot.send_message(user_id, "У вас пока нет трат на штрафы.")

# (10.18) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "УДАЛИТЬ ТРАТЫ") ---------------

@bot.message_handler(func=lambda message: message.text == "Удалить траты")
def delete_expenses_menu(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Del траты (месяц)")
    item2 = types.KeyboardButton("Del траты (год)")
    item3 = types.KeyboardButton("Del траты (всё время)")
    item4 = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item5 = types.KeyboardButton("В главное меню")

    markup.add(item1, item2, item3)
    markup.add(item4, item5)
    bot.send_message(user_id, "Выберите вариант удаления трат:", reply_markup=markup)

# (10.19) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "DEL ТРАТЫ (МЕСЯЦ)") ---------------

valid_months = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

@bot.message_handler(func=lambda message: message.text == "Del траты (месяц)")
def delete_expense_by_month(message):
    user_id = message.from_user.id

    if delete_expense_by_month is None:
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, confirm_delete_all_expenses)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)
    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для удаления трат за этот месяц:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_expenses_by_month)

# (10.20) --------------- КОД ДЛЯ "ТРАТ" (ФУНКЦИЯ УДАЛИТЬ ТРАТЫ ЗА МЕСЯЦ) ---------------

def delete_expenses_by_month(message):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, delete_expenses_by_month)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)  
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    month_year = message.text

    month = month_year.split(".")[0]
    if month not in valid_months:
        bot.send_message(user_id, "Введен неверный месяц. Пожалуйста, введите корректный месяц (ММ.ГГГГ).")
        bot.register_next_step_handler(message, delete_expenses_by_month)
        return

    user_data = load_expense_data(user_id).get(str(user_id), {})
    expenses = user_data.get("expenses", [])

    if not expenses:
        bot.send_message(user_id, f"У вас пока нет сохраненных трат за {month_year} для удаления.")
    else:
        expenses_to_delete = []

        for index, expense in enumerate(expenses, start=1):
            expense_date = expense.get("date", "")
            expense_date_parts = expense_date.split(".")
            if len(expense_date_parts) >= 2:
                expense_month_year = expense_date_parts[1] + "." + expense_date_parts[2]
            else:
                expense_month_year = ""

            if expense_month_year == month_year:
                expenses_to_delete.append((index, expense))

        if expenses_to_delete:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
            keyboard.add(types.KeyboardButton("В главное меню"))
            for index, expense in expenses_to_delete:
                expense_name = expense.get("name", "Без названия")
                keyboard.add(types.KeyboardButton(f"Удалить трату #{index} - {expense_name}"))

            bot.send_message(user_id, "Выберите трату для удаления:", reply_markup=keyboard)
            bot.register_next_step_handler(message, confirm_delete_expense_month)
        else:
            bot.send_message(user_id, f"За {month_year} месяц трат не найдено для удаления.")

# (10.21) --------------- КОД ДЛЯ "ТРАТ" (ФУНКЦИЯ ПОДТВЕРЖДЕНИЯ УДАЛЕНИЯ ТРАТ ЗА МЕСЯЦ) ---------------

def confirm_delete_expense_month(message):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, confirm_delete_expense_month)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    selected_option = message.text

    if selected_option.startswith("Удалить трату #"):
        try:
            expense_index = int(selected_option.split("#")[1].split(" - ")[0]) - 1
            user_data = load_expense_data(user_id).get(str(user_id), {})
            expenses = user_data.get("expenses", [])

            if 0 <= expense_index < len(expenses):
                deleted_expense = expenses.pop(expense_index)
                user_data["expenses"] = expenses 
                save_expense_data(user_id, {str(user_id): user_data}) 
                bot.send_message(user_id, f"Трата '{deleted_expense.get('name', 'Без названия')}' удалена успешно.")

            else:
                bot.send_message(user_id, "Недопустимый выбор. Пожалуйста, выберите трату из списка.")
        except ValueError:
            bot.send_message(user_id, "Ошибка при обработке выбора. Пожалуйста, выберите трату из списка.")
    else:
        bot.send_message(user_id, "Недопустимый выбор. Пожалуйста, выберите трату из списка.")

    send_menu(user_id)

# (10.22) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "DEL ТРАТЫ (ГОД)") ---------------

@bot.message_handler(func=lambda message: message.text == "Del траты (год)")
def delete_expense_by_year(message):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)
    bot.send_message(user_id, "Введите год (ГГГГ) для удаления трат за этот год:", reply_markup=markup)
    bot.register_next_step_handler(message, get_year_to_delete_expenses)

# (10.23) --------------- КОД ДЛЯ "ТРАТ" (ФУНКЦИЯ УДАЛЕНИЯ ТРАТ ЗА МЕСЯЦ) ---------------

def get_year_to_delete_expenses(message):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, get_year_to_delete_expenses)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id) 
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    year = message.text

    if not re.match(r'^\d{4}$', year):
        bot.send_message(user_id, "Пожалуйста, введите год в формате ГГГГ.")
        bot.register_next_step_handler(message, get_year_to_delete_expenses)
        return

    year = int(year)
    user_data = load_expense_data(user_id).get(str(user_id), {})
    expenses = user_data.get("expenses", [])

    if not expenses:
        bot.send_message(user_id, f"У вас пока нет сохраненных трат за {year} год для удаления.")
        return

    expenses_to_delete = []

    for index, expense in enumerate(expenses, start=1):
        expense_date = expense.get("date", "")
        expense_date_parts = expense_date.split(".")
        if len(expense_date_parts) >= 3:
            expense_year = int(expense_date_parts[2])
        else:
            expense_year = 0

        if expense_year == year:
            expenses_to_delete.append((index, expense))

    if expenses_to_delete:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        keyboard.add(types.KeyboardButton("В главное меню"))
        for index, expense in expenses_to_delete:
            expense_name = expense.get("name", "Без названия")
            keyboard.add(types.KeyboardButton(f"Удалить трату #{index} - {expense_name}"))

        bot.send_message(user_id, "Выберите трату для удаления:", reply_markup=keyboard)
        bot.register_next_step_handler(message, confirm_delete_expense)
    else:
        bot.send_message(user_id, f"За {year} год трат не найдено для удаления.")

# (10.24) --------------- КОД ДЛЯ "ТРАТ" (ФУНКЦИЯ ПОДТВЕРЖДЕНИЯ УДАЛЕНИЯ ТРАТ ЗА ГОД) ---------------

def confirm_delete_expense(message):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, confirm_delete_expense)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    user_data = load_expense_data(user_id).get(str(user_id), {})
    expenses = user_data.get("expenses", [])
    selected_option = message.text

    try:
        expense_index = int(selected_option.split("#")[1].split(" -")[0])
    except (IndexError, ValueError):
        bot.send_message(user_id, "Неверный выбор. Пожалуйста, выберите трату для удаления.")
        return

    if 1 <= expense_index <= len(expenses):
        deleted_expense = expenses.pop(expense_index - 1)
        user_data["expenses"] = expenses 
        save_expense_data(user_id, {str(user_id): user_data}) 
        bot.send_message(user_id, f"Трата \"{deleted_expense.get('name', 'Без названия')}\" удалена успешно.")
    else:
        bot.send_message(user_id, "Неверный выбор. Пожалуйста, выберите трату для удаления.")

    send_menu(user_id)

# (10.25) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "DEL ТРАТЫ (ВСЕ ВРЕМЯ)") ---------------

@bot.message_handler(func=lambda message: message.text == "Del траты (всё время)")
def delete_all_expenses(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)
    bot.send_message(user_id, "Вы уверены, что хотите удалить все траты? (да/нет)", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_delete_all_expenses)

# (10.26) --------------- КОД ДЛЯ "ТРАТ" (ФУНКЦИЯ ПОДТВЕРЖДЕНИЯ УДАЛЕНИЯ ТРАТ ЗА ВСЕ ВРЕМЯ) ---------------

def confirm_delete_all_expenses(message):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, confirm_delete_all_expenses)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id) 
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    response = message.text.lower()

    if response == "да":
        user_data = load_expense_data(user_id).get(str(user_id), {})
        user_data["expenses"] = [] 
        save_expense_data(user_id, user_data)
        bot.send_message(user_id, "Все траты удалены.")
    elif response == "нет":
        bot.send_message(user_id, "Удаление всех трат отменено.")
    else:
        bot.send_message(user_id, "Пожалуйста, введите 'да' или 'нет.")

    send_menu(user_id)

# (11) --------------- КОД ДЛЯ "РЕМОНТОВ" ---------------

# (11.1) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "ЗАПИСАТЬ РЕМОНТ") ---------------

@bot.message_handler(func=lambda message: message.text == "Записать ремонт")
def record_repair(message):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id) 
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, record_repair)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
        item_main_menu = types.KeyboardButton("В главное меню")
        markup.add(item_return)
        markup.add(item_main_menu)
        bot.send_message(user_id, "Введите название ремонта:", reply_markup=markup)
        bot.register_next_step_handler(message, get_repair_name, markup)

# (11.2) --------------- КОД ДЛЯ "РЕМОНТОВ" (ИМЯ РЕМОНТА) ---------------

def get_repair_name(message, markup):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id) 
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    repair_name = message.text

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, get_repair_name, markup)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
        item_main_menu = types.KeyboardButton("В главное меню")
        markup.add(item_return)
        markup.add(item_main_menu)
        bot.send_message(user_id, "Введите дату ремонта в формате ДД.ММ.ГГГГ:", reply_markup=markup)
        bot.register_next_step_handler(message, get_repair_date, repair_name, markup)

# (11.3) --------------- КОД ДЛЯ "РЕМОНТОВ" (ДАТА РЕМОНТА) ---------------

def get_repair_date(message, repair_name, markup):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    repair_date = message.text

    if repair_date is None:
        bot.send_message(user_id, "Неправильный формат даты. Введите дату в формате ДД.ММ.ГГГГ.:", reply_markup=markup)
        bot.register_next_step_handler(message, get_repair_date, repair_name, markup)
        return

    if not re.match(r'\d{2}\.\d{2}\.\d{4}', repair_date):
        bot.send_message(user_id, "Неправильный формат даты. Введите дату в формате ДД.ММ.ГГГГ.:", reply_markup=markup)
        bot.register_next_step_handler(message, get_repair_date, repair_name, markup)
        return

    day, month, year = map(int, repair_date.split('.'))
    if day < 1 or day > 31:
        bot.send_message(user_id, "Неправильный формат даты. Введите дату в формате ДД.ММ.ГГГГ.:", reply_markup=markup)
        bot.register_next_step_handler(message, get_repair_date, repair_name, markup)
        return

    if month < 1 or month > 12:
        bot.send_message(user_id, "Неправильный формат даты. Введите дату в формате ДД.ММ.ГГГГ.:", reply_markup=markup)
        bot.register_next_step_handler(message, get_repair_date, repair_name, markup)
        return

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.", reply_markup=markup)
        bot.register_next_step_handler(sent, get_repair_date, repair_name, markup)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
        item_main_menu = types.KeyboardButton("В главное меню")
        markup.add(item_return)
        markup.add(item_main_menu)
        bot.send_message(user_id, "Введите описание ремонта:", reply_markup=markup)
        bot.register_next_step_handler(message, get_repair_description, repair_name, repair_date, markup)

# (11.4) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОПИСАНИЕ РЕМОНТА) ---------------

def get_repair_description(message, repair_name, repair_date, markup):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id) 
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    repair_description = message.text

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, get_repair_description, repair_name, repair_date, markup)
        return

    user_data = load_repair_data(user_id)

    str_user_id = str(user_id)

    if str_user_id not in user_data:
        user_data[str_user_id] = {"repairs": []}

    if "repairs" not in user_data[str_user_id]:
        user_data[str_user_id] = {"repairs": []}

    user_data[str_user_id]["repairs"].append({
        "name": repair_name,
        "date": repair_date,
        "description": repair_description
    })

    save_repair_data(user_id, user_data)

    bot.send_message(user_id, f"Ремонт успешно записан!", reply_markup=markup)

# (11.5) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "ПОСМОТРЕТЬ РЕМОНТЫ") ---------------

@bot.message_handler(func=lambda message: message.text == "Посмотреть ремонты")
def view_repairs(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Ремонты (месяц)")
    item2 = types.KeyboardButton("Ремонты (год)")
    item3 = types.KeyboardButton("Ремонты (всё время)")
    item4 = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item5 = types.KeyboardButton("В главное меню")    
    markup.add(item1, item2, item3)
    markup.add(item4,item5)

    bot.send_message(user_id, "Выберите вариант просмотра ремонтов:", reply_markup=markup)

# (11.6) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "ПОСМОТРЕТЬ РЕМОНТЫ ЗА МЕСЯЦ") ---------------

@bot.message_handler(func=lambda message: message.text == "Ремонты (месяц)")
def view_repairs_by_month(message):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, view_repairs_by_month)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для просмотра ремонтов за этот период:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda message: get_repairs_by_month(message, markup))

def send_repairs_message(user_id, message_text, markup):
    max_message_length = 4096  
    message_parts = [message_text[i:i+max_message_length] for i in range(0, len(message_text), max_message_length)]

    for part in message_parts:
        bot.send_message(user_id, part, reply_markup=markup)

def get_repairs_by_month(message, markup):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    date = message.text

    if date is not None:
        month, year = date.split(".")
        month = int(month)
        year = int(year)

        if 1 <= month <= 12:
            user_data = load_repair_data(user_id)
            repairs = user_data.get(str(user_id), {}).get("repairs", [])

            repairs_by_month = []
            for repair in repairs:
                repair_date = repair.get("date", "")
                repair_month, repair_year = map(int, repair_date.split(".")[1:])
                if repair_month == month and repair_year == year:
                    repairs_by_month.append(repair)

            if repairs_by_month:
                message_text = f"Ремонты за {date}:\n\n"
                for index, repair in enumerate(repairs_by_month, start=1):
                    repair_name = repair.get("name", "")
                    repair_date = repair.get("date", "")
                    repair_description = repair.get("description", "")
                    message_text += f"  №: {index}\n\n    НАЗВАНИЕ: {repair_name}\n    ДАТА: {repair_date}\n    ОПИСАНИЕ: {repair_description}\n\n"

                send_repairs_message(user_id, message_text, markup)
            else:
                bot.send_message(user_id, f"За {date} ремонтов не найдено.", reply_markup=markup)
        else:
            bot.send_message(user_id, "Пожалуйста, введите корректный месяц от 1 до 12 (ММ.ГГГГ). Попробуйте еще раз.", reply_markup=markup)
            bot.register_next_step_handler(message, get_repairs_by_month, markup)
    else:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.", reply_markup=markup)

    bot.register_next_step_handler(message, lambda message: get_repairs_by_month(message, markup))

# (11.7) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "ПОСМОТРЕТЬ РЕМОНТЫ ЗА ГОД") ---------------

@bot.message_handler(func=lambda message: message.text == "Ремонты (год)")
def view_repairs_by_year(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите год (ГГГГ) для просмотра ремонтов за этот год:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda message: get_repairs_by_year(message, markup))

def send_repairs_message(user_id, message_text, markup):
    max_message_length = 4096 
    message_parts = [message_text[i:i+max_message_length] for i in range(0, len(message_text), max_message_length)]

    for part in message_parts:
        bot.send_message(user_id, part, reply_markup=markup)

def get_repairs_by_year(message, markup):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id) 
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text is None:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, lambda message: get_repairs_by_year(message, markup))
        return

    try:
        year = int(message.text)
    except ValueError:
        bot.send_message(user_id, "Пожалуйста, введите год в формате ГГГГ.")
        bot.register_next_step_handler(message, lambda message: get_repairs_by_year(message, markup))
        return

    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])

    repairs_by_year = []
    for repair in repairs:
        repair_date = repair.get("date", "")
        repair_year = int(repair_date.split(".")[2])
        if repair_year == year:
            repairs_by_year.append(repair)

    if repairs_by_year:
        message_text = f"Ремонты за {year} год:\n\n"
        for index, repair in enumerate(repairs_by_year, start=1):
            repair_name = repair.get("name", "")
            repair_date = repair.get("date", "")
            repair_description = repair.get("description", "")
            message_text += f"  №: {index}\n\n    НАЗВАНИЕ: {repair_name}\n    ДАТА: {repair_date}\n    ОПИСАНИЕ: {repair_description}\n\n"

        send_repairs_message(user_id, message_text, markup)
    else:
        message_text = f"За {year} ремонтов не найдено."

        bot.send_message(user_id, message_text, reply_markup=markup)

    bot.register_next_step_handler(message, lambda message: get_repairs_by_year(message, markup))

# (11.8) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "ПОСМОТРЕТЬ РЕМОНТЫ ЗА ВСЕ ВРЕМЯ") ---------------

@bot.message_handler(func=lambda message: message.text == "Ремонты (всё время)")
def view_all_repairs(message):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)  
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])

    if repairs:
        message_text = "Все ремонты:\n\n"
        for index, repair in enumerate(repairs, start=1):
            repair_name = repair.get("name", "")
            repair_date = repair.get("date", "")
            repair_description = repair.get("description", "")
            message_text += f"  №: {index}\n\n    НАЗВАНИЕ: {repair_name}\n    ДАТА: {repair_date}\n    ОПИСАНИЕ: {repair_description}\n\n"

        send_repairs_message(user_id, message_text, markup)
    else:
        message_text = "У вас пока нет ремонтов."

        bot.send_message(user_id, message_text, reply_markup=markup)

def send_repairs_message(user_id, message_text, markup):
    max_message_length = 4096 
    message_parts = [message_text[i:i+max_message_length] for i in range(0, len(message_text), max_message_length)]

    for part in message_parts:
        bot.send_message(user_id, part, reply_markup=markup)

# (11.9) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "УДАЛИТЬ РЕМОНТЫ") ---------------

@bot.message_handler(func=lambda message: message.text == "Удалить ремонты")
def delete_expenses_menu(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Del ремонты (месяц)")
    item2 = types.KeyboardButton("Del ремонты (год)")
    item3 = types.KeyboardButton("Del ремонты (всё время)")
    item4 = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item5 = types.KeyboardButton("В главное меню")

    markup.add(item1, item2, item3)
    markup.add(item4, item5)
    bot.send_message(user_id, "Выберите вариант удаления трат:", reply_markup=markup)

# (11.10) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "УДАЛИТЬ РЕМОНТЫ ЗА МЕСЯЦ") ---------------

@bot.message_handler(func=lambda message: message.text == "Del ремонты (месяц)")
def delete_repair_by_month(message):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, delete_repair_by_month)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)
    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для удаления ремонтов за этот период:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_repairs_by_month)

def delete_repairs_by_month(message):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, delete_repairs_by_month)
        return

    date = message.text

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id) 
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if len(date.split(".")) != 2:
        bot.send_message(user_id, "Пожалуйста, введите дату в формате ММ.ГГГГ (например, 01.2023).")
        return

    month, year = date.split(".")
    month = int(month)
    year = int(year)

    user_data = load_repair_data(user_id)

    repairs = user_data.get(str(user_id), {}).get("repairs", [])

    if not repairs:
        bot.send_message(user_id, f"У вас пока нет записей о ремонтах за {date} для удаления.")
        return

    repairs_to_delete = []

    for index, repair in enumerate(repairs, start=1):
        repair_date = repair.get("date", "")
        repair_date_parts = repair_date.split(".")
        if len(repair_date_parts) >= 2:
            repair_month, repair_year = map(int, repair_date_parts[1:3])
        else:
            repair_month = 0
            repair_year = 0

        if repair_month == month and repair_year == year:
            repairs_to_delete.append((index, repair))

    if repairs_to_delete:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        for index, repair in repairs_to_delete:
            repair_name = repair.get("name", "Без названия")
            keyboard.add(types.KeyboardButton(f"Удалить ремонт #{index} - {repair_name}"))

        bot.send_message(user_id, "Выберите ремонт для удаления:", reply_markup=keyboard)
        bot.register_next_step_handler(message, confirm_delete_repair, user_data, user_id)
    else:
        bot.send_message(user_id, f"За {date} ремонтов не найдено для удаления.")

# (11.11) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "УДАЛИТЬ РЕМОНТЫ ЗА МЕСЯЦ (ПОДТВЕРЖДЕНИЕ)") ---------------

def confirm_delete_repair(message, user_data, user_id):
    bot.register_next_step_handler(message, confirm_delete_repair, user_data, user_id)

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id) 
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    repair_index = int(message.text.split("#")[1].split(" -")[0])
    repairs = user_data.get(str(user_id), {}).get("repairs", [])

    if repair_index >= 1 and repair_index <= len(repairs):
        deleted_repair = repairs.pop(repair_index - 1)  
        save_repair_data(user_id, user_data)
        bot.send_message(user_id, f"Ремонт '{deleted_repair['name']}' удален.")
    else:
        bot.send_message(user_id, "Номер ремонта недействителен. Выберите номер из списка.")

    send_menu(user_id)

def is_valid_year(text):
    if text.isnumeric() and len(text) == 4:
        return True
    return False

# (11.12) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "УДАЛИТЬ РЕМОНТЫ ЗА ГОД") ---------------

@bot.message_handler(func=lambda message: message.text == "Del ремонты (год)")
def delete_repair_by_year(message):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, delete_repair_by_year)
        return

    user_data = load_repair_data(user_id) 
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)
    bot.send_message(user_id, "Введите год в формате (ГГГГ) для удаления ремонтов за этот год:", reply_markup=markup)
    bot.register_next_step_handler(message, check_and_delete_repairs_by_year, user_data, markup)

def check_and_delete_repairs_by_year(message, user_data, markup):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, check_and_delete_repairs_by_year, user_data, markup)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    input_year = message.text

    if not is_valid_year(input_year):
        bot.send_message(user_id, "Пожалуйста, введите корректный год в формате ГГГГ.")
        bot.register_next_step_handler(message, check_and_delete_repairs_by_year, user_data, markup)
        return

    year = int(input_year) 

    repairs = user_data.get(str(user_id), {}).get("repairs", [])

    if not repairs:
        bot.send_message(user_id, f"У вас пока нет записей о ремонтах за {year} год для удаления.")
        return

    repairs_to_delete = []

    for index, repair in enumerate(repairs, start=1):
        repair_date = repair.get("date", "")
        repair_date_parts = repair_date.split(".")
        if len(repair_date_parts) >= 3:
            repair_year = int(repair_date_parts[2])
        else:
            repair_year = 0

        if repair_year == year:
            repairs_to_delete.append((index, repair))

    if repairs_to_delete:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        keyboard.add(types.KeyboardButton("В главное меню"))
        for index, repair in repairs_to_delete:
            repair_name = repair.get("name", "Без названия")
            keyboard.add(types.KeyboardButton(f"Удалить ремонт #{index} - {repair_name}"))
        bot.send_message(user_id, "Выберите ремонт для удаления:", reply_markup=keyboard)
        bot.register_next_step_handler(message, confirm_delete_repair, user_data, user_id)
    else:
        bot.send_message(user_id, f"За {year} год ремонтов не найдено для удаления.")

# (11.13) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "УДАЛИТЬ РЕМОНТЫ ЗА ГОД (ПОДТВЕРЖДЕНИЕ)") ---------------

def confirm_delete_repair(message, user_data, user_id):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, confirm_delete_repair, user_data, user_id)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id) 
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    if not isinstance(user_data, dict):
        user_data = {}

    repairs = user_data.get(str(user_id), {}).get("repairs", [])

    if not repairs:
        bot.send_message(user_id, "У вас пока нет записей о ремонтах для удаления.")
        return

    repair_index_match = re.match(r'Удалить ремонт #(\d+)', message.text)

    if repair_index_match:
        repair_index = int(repair_index_match.group(1))
        if 1 <= repair_index <= len(repairs):
            deleted_repair = repairs.pop(repair_index - 1)
            user_data[str(user_id)]["repairs"] = repairs
            save_repair_data(user_id, user_data)
            bot.send_message(user_id, f"Ремонт #{repair_index} успешно удален.")
        else:
            bot.send_message(user_id, "Некорректный номер ремонта. Попробуйте еще раз.")
    else:
        bot.send_message(user_id, "Некорректный номер ремонта. Попробуйте еще раз.")

    send_menu(user_id)

# (11.14) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "УДАЛИТЬ РЕМОНТЫ ЗА ВСЕ ВРЕМЯ") ---------------

@bot.message_handler(func=lambda message: message.text == "Del ремонты (всё время)")
def delete_all_repairs(message):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, delete_all_repairs)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)
    bot.send_message(user_id, "Вы уверены, что хотите удалить все ремонты? (да/нет)", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_delete_all_repairs, markup)

# (11.15) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "УДАЛИТЬ РЕМОНТЫ ЗА ВСЕ ВРЕМЯ (ПОДТВЕРЖДЕНИЕ)") ---------------

def confirm_delete_all_repairs(message, markup):
    user_id = str(message.from_user.id) 
    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, confirm_delete_all_repairs, markup)
        return

    user_input = message.text.lower()

    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id) 
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    if user_input == "да":
        user_data = load_repair_data(user_id)
        if user_id in user_data:
            user_data[user_id] = [] 
            save_repair_data(user_id, user_data)
            bot.send_message(user_id, "Все ремонты удалены.")
        else:
            bot.send_message(user_id, "У вас нет ремонтов для удаления.")
    elif user_input == "нет":
        bot.send_message(user_id, "Удаление отменено.")
    else:
        bot.send_message(user_id, "Пожалуйста, введите 'да' или 'нет.")
        bot.register_next_step_handler(message, confirm_delete_all_repairs, markup)

    send_menu(user_id)

# (12) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" ---------------

# (12.1) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ВВОДНЫЕ ФУНКЦИИ) ---------------

geolocator = Nominatim(user_agent="geo_bot")

user_locations = {}

def calculate_distance(origin, destination):
    return geodesic(origin, destination).kilometers

# (12.2) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (СОКРАЩЕНИЕ ССЫЛОК) ---------------

def shorten_url(original_url):
    endpoint = 'https://clck.ru/--'
    response = requests.get(endpoint, params={'url': original_url})
    return response.text

# (12.3) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (АЗС) ---------------

def get_nearby_fuel_stations(latitude, longitude, user_coordinates):
    api_url = "https://search-maps.yandex.ru/v1/"
    params = {
        "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
        "text": "АЗС",
        "lang": "ru_RU",
        "ll": f"{longitude},{latitude}",
        "spn": "0.045,0.045", 
        "type": "biz"
    }
    response = requests.get(api_url, params=params)
    data = response.json()

    fuel_stations = []
    for feature in data["features"]:
        coordinates = feature["geometry"]["coordinates"]
        name = feature["properties"]["name"]
        address = feature["properties"]["description"]
        fuel_stations.append({"name": name, "coordinates": coordinates, "address": address})

    return fuel_stations

# (12.4) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (АВТОМОЙКИ) ---------------

def get_nearby_car_washes(latitude, longitude, user_coordinates):
    api_url = "https://search-maps.yandex.ru/v1/"
    params = {
        "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
        "text": "Автомойка",
        "lang": "ru_RU",
        "ll": f"{longitude},{latitude}",
        "spn": "0.045,0.045", 
        "type": "biz"
    }
    response = requests.get(api_url, params=params)
    data = response.json()

    car_washes = []
    for feature in data["features"]:
        coordinates = feature["geometry"]["coordinates"]
        name = feature["properties"]["name"]
        address = feature["properties"]["description"]
        car_washes.append({"name": name, "coordinates": coordinates, "address": address})

    return car_washes

# (12.5) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (АВТОСЕРВИС) ---------------

def get_nearby_auto_services(latitude, longitude, user_coordinates):
    api_url = "https://search-maps.yandex.ru/v1/"
    params = {
        "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
        "text": "Автосервис",
        "lang": "ru_RU",
        "ll": f"{longitude},{latitude}",
        "spn": "0.045,0.045",
        "type": "biz"
    }
    response = requests.get(api_url, params=params)
    data = response.json()

    auto_services = []
    for feature in data.get("features", []):
        coordinates = feature.get("geometry", {}).get("coordinates")
        name = feature.get("properties", {}).get("name")
        address = feature.get("properties", {}).get("description", "Адрес не указан")
        if coordinates and name:
            auto_services.append({"name": name, "coordinates": coordinates, "address": address})

    return auto_services

# (12.6) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ПАРКОВКИ) ---------------

def get_nearby_parking(latitude, longitude, user_coordinates):
    api_url = "https://search-maps.yandex.ru/v1/"
    params = {
        "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
        "text": "Парковки",
        "lang": "ru_RU",
        "ll": f"{longitude},{latitude}",
        "spn": "0.045,0.045",
        "type": "biz"
    }
    response = requests.get(api_url, params=params)
    data = response.json()

    parking_places = []
    for feature in data["features"]:
        coordinates = feature["geometry"]["coordinates"]
        name = feature["properties"]["name"]
        address = feature["properties"]["description"]
        parking_places.append({"name": name, "coordinates": coordinates, "address": address})

    return parking_places

# (12.7) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ЭВАКУАТОР) ---------------

def get_nearby_evacuation_services(latitude, longitude, user_coordinates):
    api_url = "https://search-maps.yandex.ru/v1/"
    params = {
        "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
        "text": "Эвакуация",
        "lang": "ru_RU",
        "ll": f"{longitude},{latitude}",
        "spn": "0.045,0.045",
        "type": "biz"
    }
    response = requests.get(api_url, params=params)
    data = response.json()

    evacuation_services = []
    for feature in data["features"]:
        coordinates = feature["geometry"]["coordinates"]
        name = feature["properties"]["name"]
        address = feature["properties"]["description"]
        evacuation_services.append({"name": name, "coordinates": coordinates, "address": address})

    return evacuation_services

# (12.8) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ГИБДД) ---------------

def get_nearby_gibdd_mreo(latitude, longitude, user_coordinates):
    api_url = "https://search-maps.yandex.ru/v1/"
    params = {
        "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
        "text": "ГИБДД",
        "lang": "ru_RU",
        "ll": f"{longitude},{latitude}",
        "spn": "0.045,0.045",
        "type": "biz"
    }
    response = requests.get(api_url, params=params)
    data = response.json()

    gibdd_mreo_offices = []
    for feature in data["features"]:
        coordinates = feature["geometry"]["coordinates"]
        name = feature["properties"]["name"]
        address = feature["properties"]["description"]
        gibdd_mreo_offices.append({"name": name, "coordinates": coordinates, "address": address})

    return gibdd_mreo_offices

# (12.9) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (КОМИССАРЫ) ---------------

def get_nearby_accident_commissioner(latitude, longitude, user_coordinates):
    api_url = "https://search-maps.yandex.ru/v1/"
    params = {
        "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
        "text": "Комиссары",
        "lang": "ru_RU",
        "ll": f"{longitude},{latitude}",
        "spn": "0.045,0.045",
        "type": "biz"
    }
    response = requests.get(api_url, params=params)
    data = response.json()

    accident_commissioners = []
    for feature in data["features"]:
        coordinates = feature["geometry"]["coordinates"]
        name = feature["properties"]["name"]
        address = feature["properties"]["description"]
        accident_commissioners.append({"name": name, "coordinates": coordinates, "address": address})

    return accident_commissioners

# (12.10) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ОБРАБОТЧИК "ПОИСК МЕСТ") ---------------

@bot.message_handler(func=lambda message: message.text == "Поиск мест")
def send_welcome(message):
    user_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    button_azs = types.KeyboardButton("АЗС")
    button_car_wash = types.KeyboardButton("Автомойки")
    button_auto_service = types.KeyboardButton("Автосервисы")
    button_parking = types.KeyboardButton("Парковки")
    button_evacuation = types.KeyboardButton("Эвакуация")
    button_gibdd_mreo = types.KeyboardButton("ГИБДД")
    button_accident_commissioner = types.KeyboardButton("Комиссары")

    item1 = types.KeyboardButton("В главное меню")

    markup.add(button_azs, button_car_wash, button_auto_service)
    markup.add(button_parking, button_evacuation, button_gibdd_mreo, button_accident_commissioner)
    markup.add(item1)

    bot.send_message(user_id, "Выберите категорию для ближайшего поиска:", reply_markup=markup)

# (12.11) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ОБРАБОТЧИК "ВЫБОР КАТЕГОРИИ ЗАНОВО") ---------------

@bot.message_handler(func=lambda message: message.text == "Выбрать категорию заново")
def handle_reset_category(message):
    global selected_category
    selected_category = None
    send_welcome(message)

selected_category = None 

# (12.12) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ОБРАБОТЧИК "ДЛЯ ВЫБОРА КАТЕГОРИИ") ---------------

@bot.message_handler(func=lambda message: message.text in {"АЗС", "Автомойки", "Автосервисы", "Парковки", "Эвакуация", "ГИБДД", "Комиссары"})
def handle_menu_buttons(message):
    global selected_category 
    if message.text in {"АЗС", "Автомойки", "Автосервисы", "Парковки", "Эвакуация", "ГИБДД", "Комиссары"}:
        selected_category = message.text 
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button_send_location = types.KeyboardButton("Отправить геолокацию", request_location=True)
        button_reset_category = types.KeyboardButton("Выбрать категорию заново")
        item1 = types.KeyboardButton("В главное меню")
        keyboard.add(button_send_location)
        keyboard.add(button_reset_category)
        keyboard.add(item1)
        bot.send_message(message.chat.id, f"Отправьте свою геолокацию. Вам будет выдан список ближайших {selected_category.lower()}.", reply_markup=keyboard)
    else:
        selected_category = None
        bot.send_message(message.chat.id, "Пожалуйста, выберите категорию из меню.")

# (12.13) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ОБРАБОТЧИК "ГЕОЛОКАЦИЯ") ---------------

@bot.message_handler(content_types=['location'])
def handle_location(message):
    global selected_category, selected_location, user_locations
    latitude = message.location.latitude
    longitude = message.location.longitude
    user_id = message.from_user.id

    try:
        location = geolocator.reverse((latitude, longitude), language='ru', timeout=10)
        address = location.address

        if selected_category is None:
            bot.send_message(message.chat.id, "Пожалуйста, выберите категорию из меню.")
            return

        user_locations[user_id] = {"address": address, "coordinates": (latitude, longitude)}

        if selected_category == "АЗС":
            locations = get_nearby_fuel_stations(latitude, longitude, user_locations[user_id]["coordinates"])
        elif selected_category == "Автомойки":
            locations = get_nearby_car_washes(latitude, longitude, user_locations[user_id]["coordinates"])
        elif selected_category == "Автосервисы":
            locations = get_nearby_auto_services(latitude, longitude, user_locations[user_id]["coordinates"])
        elif selected_category == "Парковки":
            locations = get_nearby_parking(latitude, longitude, user_locations[user_id]["coordinates"])
        elif selected_category == "Эвакуация":
            locations = get_nearby_evacuation_services(latitude, longitude, user_locations[user_id]["coordinates"])
        elif selected_category == "ГИБДД":
            locations = get_nearby_gibdd_mreo(latitude, longitude, user_locations[user_id]["coordinates"])
        elif selected_category == "Комиссары":
            locations = get_nearby_accident_commissioner(latitude, longitude, user_locations[user_id]["coordinates"])

        selected_location = {"address": address, "coordinates": (latitude, longitude)}

        message_text = f"Ближайшие объекты по адресу:\n\n{address}\n\n"
        message_text += f"{selected_category}:\n\n"

        for location in locations:
            name = location["name"]
            coordinates = location["coordinates"]
            address = location["address"]

            yandex_maps_url = f"https://yandex.ru/maps/?rtext={user_locations[user_id]['coordinates'][0]},{user_locations[user_id]['coordinates'][1]}~{coordinates[1]},{coordinates[0]}&l=map&rtt=auto&ruri=~ymapsbm1%3A%2F%2Forg%3Foid%3D1847883008%26name%3D{quote(name)}%26address%3D{quote(address)}\n\n"

            short_yandex_maps_url = shorten_url(yandex_maps_url)

            message_text += f"{name} ({address}):\n{short_yandex_maps_url}\n\n"

        bot.send_message(message.chat.id, message_text, parse_mode='HTML')

        selected_category = None

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button_reset_category = types.KeyboardButton("Выбрать категорию заново")
        item1 = types.KeyboardButton("В главное меню")
        keyboard.add(button_reset_category)
        keyboard.add(item1)
        bot.send_message(message.chat.id, "Выберите категорию заново или вернитесь в главное меню.", reply_markup=keyboard)

    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка при обработке вашего запроса: {e}")

# (13) --------------- КОД ДЛЯ "ПОИСКА ТРАНСПОРТА" ---------------

# (13.1) --------------- КОД ДЛЯ "ПОИСКА ТРАНСПОРТА" (СОХРАНЕНИЕ И ЗАГРУЗКА ГЕОЛОКАЦИИ) ---------------

LATITUDE_KEY = 'latitude'
LONGITUDE_KEY = 'longitude'

def save_location_data(location_data):
    folder_path = "data base"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    with open(os.path.join(folder_path, "location_data.json"), "w") as json_file:
        json.dump(location_data, json_file)

def load_location_data():
    try:
        with open(os.path.join("data base", "location_data.json"), "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

location_data = load_location_data()

# (13.2) --------------- КОД ДЛЯ "ПОИСКА ТРАНСПОРТА" (ОБРАБОТЧИК "НАЙТИ ТРАНСПОРТ") ---------------

@bot.message_handler(func=lambda message: message.text == "Найти транспорт")
def start3(message):
    global location_data
    user_id = str(message.from_user.id)

    if user_id in location_data and location_data[user_id]['start_location'] is not None:
        location_data[user_id]['start_location'] = None
        location_data[user_id]['end_location'] = None
        save_location_data(location_data)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Отправить геопозицию", request_location=True)
    item2 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)

    bot.send_message(message.chat.id, "Отправьте геопозицию транспорта:", reply_markup=markup)

    bot.register_next_step_handler(message, handle_car_location)

# (13.3) --------------- КОД ДЛЯ "ПОИСКА ТРАНСПОРТА" (ОБРАБОТЧИК "ЛОКАЦИЯ") ---------------

@bot.message_handler(content_types=['location'])
def handle_car_location(message):
    global location_data
    user_id = str(message.from_user.id)

    if user_id not in location_data:
        location_data[user_id] = {'start_location': None, 'end_location': None}

    if location_data[user_id]['start_location'] is None:
        if message.location is not None:
            location_data[user_id]['start_location'] = {
                LATITUDE_KEY: message.location.latitude,
                LONGITUDE_KEY: message.location.longitude
            }

            bot.send_message(message.chat.id, "Геопозиция транспорта сохранена.\n\nТеперь отправьте свою геопозицию:")
            bot.register_next_step_handler(message, handle_car_location)
        else:

            if message.text == "В главное меню":
                return_to_menu(message)
                return

            bot.send_message(message.chat.id, "Извините, не удалось получить геопозицию транспорта. Попробуйте еще раз.")
            bot.register_next_step_handler(message, handle_car_location)

    elif location_data[user_id]['end_location'] is None:
        if message.location is not None:
            location_data[user_id]['end_location'] = {
                LATITUDE_KEY: message.location.latitude,
                LONGITUDE_KEY: message.location.longitude
            }

            save_location_data(location_data)
            send_map_link(message.chat.id, location_data[user_id]['start_location'], location_data[user_id]['end_location'])
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton("Найти транспорт")
            item2 = types.KeyboardButton("В главное меню")
            markup.add(item1)
            markup.add(item2)
            bot.send_message(message.chat.id, "Вы можете найти транспорт еще раз.", reply_markup=markup)
        else:

            if message.text == "В главное меню":
                return_to_menu(message)
                return

            bot.send_message(message.chat.id, "Извините, не удалось получить геопозицию вашего места. Попробуйте еще раз.")
            bot.register_next_step_handler(message, handle_car_location)

# (13.4) --------------- КОД ДЛЯ "ПОИСКА ТРАНСПОРТА" (ОБРАБОТЧИК "НАЙТИ ТРАНСПОРТ") ---------------

@bot.message_handler(func=lambda message: message.text == "Найти транспорт")
def find_car(message):
    global location_data
    user_id = str(message.from_user.id)

    if user_id in location_data and location_data[user_id]['start_location'] is not None:
        location_data[user_id]['start_location'] = None
        location_data[user_id]['end_location'] = None
        save_location_data(location_data)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item = types.KeyboardButton("Отправить геопозицию", request_location=True)
    markup.add(item)

    bot.send_message(message.chat.id, "Отправьте геопозицию транспорта:", reply_markup=markup)

def send_map_link(chat_id, start_location, end_location):
    map_url = f"https://yandex.ru/maps/?rtext={end_location[LATITUDE_KEY]},{end_location[LONGITUDE_KEY]}~{start_location[LATITUDE_KEY]},{start_location[LONGITUDE_KEY]}&rtt=pd"
    short_url = shorten_url(map_url)    
    bot.send_message(chat_id, f"Маршрут для поиска:\n\n{short_url}")

# (14) --------------- КОД ДЛЯ "ПОИСК РЕГИОНА ПО ГОСНОМЕРУ" ---------------

@bot.message_handler(func=lambda message: message.text == "Код региона")
def handle_start4(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("В главное меню")
    markup.add(item1)

    bot.send_message(message.chat.id, "Отправьте государственный номер автомобиля, состоящий из 8 или 9 символов (РФ), для определения региона и выдачи краткой информации через сервис AvtoCod.", reply_markup=markup)

    bot.register_next_step_handler(message, handle_text)

def handle_text(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text == "Ввести ещё один":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        bot.send_message(message.chat.id, "Отправьте государственный номер автомобиля, состоящий из 8 или 9 символов (РФ), для определения региона и выдачи краткой информации через сервис AvtoCod.", reply_markup=markup)
        bot.register_next_step_handler(message, handle_text)
        return

    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(message.chat.id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, handle_text)  # Ожидаем новое текстовое сообщение
        return

    if 8 <= len(message.text) <= 9:
        car_number = message.text.upper()
        region_code = car_number[-3:] if len(car_number) == 9 else car_number[-2:] 
        if region_code in regions:
            region_name = regions[region_code]
            response = f"Регион для номера {car_number}: {region_name}"

            avtocod_url = f"https://avtocod.ru/proverkaavto/{car_number}?rd=GRZ"
            short_url = shorten_url(avtocod_url)
            response += f"\n\nСсылка на AvtoCod с поиском:\n\n{short_url}"

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton("Ввести ещё один")
            item2 = types.KeyboardButton("В главное меню")
            markup.add(item1)
            markup.add(item2)

            bot.send_message(message.chat.id, response, reply_markup=markup)
        else:
            response = "Не удалось определить регион для указанного номера."
            bot.send_message(message.chat.id, response)
    else:
        response = "Введите государственный номер автомобиля, состоящий из 8 или 9 символов."
        bot.send_message(message.chat.id, response)

    bot.register_next_step_handler(message, handle_text)

# (15) --------------- КОД ДЛЯ "ПОГОДЫ" ---------------

# (15.1) --------------- КОД ДЛЯ "ПОГОДЫ" (ВВОДНЫЕ ФУНКЦИИ) ---------------

# API ключ от OpenWeatherMap
API_KEY = '664b0be63fce35aab95f278f77459143'

WEATHER_URL = 'http://api.openweathermap.org/data/2.5/weather'

FORECAST_URL = 'http://api.openweathermap.org/data/2.5/forecast'

MAX_MESSAGE_LENGTH = 4096

user_data = {}

# (15.1) --------------- КОД ДЛЯ "ПОГОДЫ" (ОБРАБОТЧИК "ПОГОДА") ---------------

@bot.message_handler(func=lambda message: message.text == "Погода")
def handle_start_5(message):
    try:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(telebot.types.KeyboardButton("Отправить геопозицию", request_location=True))
        markup.row(telebot.types.KeyboardButton("В главное меню"))

        bot.send_message(message.chat.id, "Отправьте свою геопозицию для отображения погоды.", reply_markup=markup)

        bot.register_next_step_handler(message, handle_location_5)
    
    except Exception as e:
        print(f"Ошибка в обработчике 'Погода': {e}")
        traceback.print_exc()

        bot.send_message(message.chat.id, "Произошла ошибка при обработке вашего запроса. Попробуйте позже.")
        
# (15.2) --------------- КОД ДЛЯ "ПОГОДЫ" (ОБРАБОТЧИК "ГЕОЛОКАЦИЯ") ---------------

@bot.message_handler(content_types=['location'])
def handle_location_5(message):
    try:
        if message.location:
            latitude = message.location.latitude
            longitude = message.location.longitude

            user_data[message.chat.id] = {'latitude': latitude, 'longitude': longitude}

            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
            markup.row('Сегодня', 'Завтра')
            markup.row('Неделя', 'Месяц')
            markup.row('Вернуться назад')
            markup.row('В главное меню')

            bot.send_message(message.chat.id, "Выберите период или действие:", reply_markup=markup)
        elif message.text == "В главное меню":
            return_to_menu(message)
        else:
            bot.send_message(message.chat.id, "Не удалось получить данные о местоположении. Пожалуйста, отправьте местоположение еще раз.")
            bot.register_next_step_handler(message, handle_location_5)
    except Exception as e:
        print(f"Ошибка в обработчике 'Геолокация': {e}")
        traceback.print_exc()

        bot.send_message(message.chat.id, "Произошла ошибка при обработке местоположения. Попробуйте позже.")

keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=False, resize_keyboard=True)
keyboard.row('Сегодня', 'Завтра')
keyboard.row('Неделя', 'Месяц')
keyboard.row('Вернуться назад')
keyboard.row('В главное меню')

# (15.3) --------------- КОД ДЛЯ "ПОГОДЫ" (ОБРАБОТЧИК "НАЗАД") ---------------

@bot.message_handler(func=lambda message: message.text == 'Вернуться назад')
def handle_back_5(message):
    chat_id = message.chat.id
    user_data.pop(chat_id, None)
    handle_start_5(message)

# (15.4) --------------- КОД ДЛЯ "ПОГОДЫ" (ОБРАБОТЧИК "ВЫБОР ПЕРИОДА") ---------------

@bot.message_handler(func=lambda message: message.text in ['Сегодня', 'Завтра', 'Неделя', 'Месяц', 'Вернуться назад'])
def handle_period_5(message):
    period = message.text.lower()
    chat_id = message.chat.id
    coords = user_data.get(chat_id)

    if period == 'вернуться назад':
        user_data.pop(chat_id, None)
        handle_start_5(message)
        return

    if coords:
        if period == 'вернуться назад':
            user_data.pop(chat_id, None)
            handle_start(message)
            return
        elif period == 'сегодня':
            send_weather(chat_id, coords, WEATHER_URL)
        elif period == 'завтра':
            send_forecast_daily(chat_id, coords, FORECAST_URL, 1)
        elif period == 'неделя':
            send_forecast_weekly(chat_id, coords, FORECAST_URL, 7)
        elif period == 'месяц':
            send_forecast_monthly(chat_id, coords, FORECAST_URL, 30)
    else:
        bot.send_message(chat_id, "Не удалось получить координаты. Пожалуйста, отправьте местоположение еще раз.")

    bot.send_message(chat_id, "Выберите действие:", reply_markup=keyboard)

# (15.5) --------------- КОД ДЛЯ "ПОГОДЫ" (ФУНКЦИЯ ТЕКУЩЕЙ ПОГОДЫ) ---------------

def send_weather(chat_id, coords, url):
    try:
        params = {
            'lat': coords['latitude'],
            'lon': coords['longitude'],
            'appid': API_KEY,
        }
        response = requests.get(url, params=params)
        data = response.json()

        if response.status_code == 200:
            temperature = round(data['main']['temp'] - 273.15)
            feels_like = round(data['main']['feels_like'] - 273.15)
            humidity = data['main']['humidity']
            pressure = data['main']['pressure']
            wind_speed = data['wind']['speed']
            description = translate_weather_description(data['weather'][0]['description'])

            message = (
                f"Погода сейчас:\n"
                f"Температура: {temperature}°C\n"
                f"Ощущается как: {feels_like}°C\n"
                f"Влажность: {humidity}%\n"
                f"Давление: {pressure} мм рт. ст\n"
                f"Скорость ветра: {wind_speed} м/с\n"
                f"Описание погоды: {description}\n"
            )

            bot.send_message(chat_id, message)
        else:
            bot.send_message(chat_id, "Не удалось получить текущую погоду.")
    except Exception as e:
        print(f"Ошибка при отправке текущей погоды: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе текущей погоды. Попробуйте позже.")

# (15.6) --------------- КОД ДЛЯ "ПОГОДЫ" (ФУНКЦИЯ ПЕРЕВОДА) ---------------

def translate_weather_description(english_description):
    translation_dict = {
        'clear sky': 'ясное небо',
        'few clouds': 'небольшая облачность',
        'scattered clouds': 'рассеянные облака',
        'broken clouds': 'облачно с прояснениями',
        'shower rain': 'небольшой дождь',
        'rain': 'дождь',
        'thunderstorm': 'гроза',
        'snow': 'снег',
        'mist': 'туман',
        'light snow': 'небольшой снег',
        'overcast clouds': 'пасмурно',
        'light snow': 'небольшой снег',
        'snow': 'снег',
        'heavy snow': 'сильный снегопад',
    }

    return translation_dict.get(english_description, english_description)

# (15.7) --------------- КОД ДЛЯ "ПОГОДЫ" (ФУНКЦИЯ ОТПРАВКИ ПРОГНОЗА) ---------------

def send_forecast(chat_id, coords, url, days=1):
    try:
        params = {
            'lat': coords['latitude'],
            'lon': coords['longitude'],
            'appid': API_KEY,
        }
        response = requests.get(url, params=params)
        data = response.json()

        if response.status_code == 200:
            forecasts = data['list'][:days * 8]
            message = "Прогноз на завтра:\n"

            for forecast in forecasts:
                date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                formatted_date = date_time.strftime("%d-%m-%Y %H:%M:%S")
                temperature = round(forecast['main']['temp'] - 273.15)
                feels_like = round(forecast['main']['feels_like'] - 273.15)
                humidity = forecast['main']['humidity']
                pressure = forecast['main']['pressure']
                wind_speed = forecast['wind']['speed']
                description = translate_weather_description(forecast['weather'][0]['description'])

                message += (
                    f"{formatted_date}:\n"
                    f"Температура: {temperature}°C\n"
                    f"Ощущается как: {feels_like}°C\n"
                    f"Влажность: {humidity}%\n"
                    f"Давление: {pressure} мм рт. ст\n"
                    f"Скорость ветра: {wind_speed} м/с\n"
                    f"Описание погоды: {description}\n\n"
                )

            message_chunks = [message[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]

            for chunk in message_chunks:
                bot.send_message(chat_id, chunk)
        else:
            bot.send_message(chat_id, "Не удалось получить прогноз погоды на завтра.")
    except Exception as e:
        print(f"Ошибка при отправке прогноза на завтра: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на завтра. Попробуйте позже.")

# (15.8) --------------- КОД ДЛЯ "ПОГОДЫ" (ФУНКЦИЯ ПОГОДЫ НА ЗАВТРА) ---------------

def send_forecast_daily(chat_id, coords, url, days):
    try:
        params = {
            'lat': coords['latitude'],
            'lon': coords['longitude'],
            'appid': API_KEY,
        }
        response = requests.get(url, params=params)
        data = response.json()

        if response.status_code == 200:
            forecasts = data['list'][:days * 8]
            message = "Прогноз на завтра:\n"

            for forecast in forecasts:
                date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                formatted_date = date_time.strftime("%d-%m-%Y %H:%M:%S")
                temperature = round(forecast['main']['temp'] - 273.15)
                feels_like = round(forecast['main']['feels_like'] - 273.15)
                humidity = forecast['main']['humidity']
                pressure = forecast['main']['pressure']
                wind_speed = forecast['wind']['speed']
                description = translate_weather_description(forecast['weather'][0]['description'])

                message += (
                    f"{formatted_date}:\n"
                    f"Температура: {temperature}°C\n"
                    f"Ощущается как: {feels_like}°C\n"
                    f"Влажность: {humidity}%\n"
                    f"Давление: {pressure} мм рт. ст\n"
                    f"Скорость ветра: {wind_speed} м/с\n"
                    f"Описание погоды: {description}\n\n"
                )

            message_chunks = [message[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]

            for chunk in message_chunks:
                bot.send_message(chat_id, chunk)
        else:
            bot.send_message(chat_id, "Не удалось получить прогноз погоды.")
    except Exception as e:
        print(f"Ошибка при отправке прогноза на завтра: {e}")
        traceback.print_exc()

        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза погоды. Попробуйте позже.")

# (15.9) --------------- КОД ДЛЯ "ПОГОДЫ" (ФУНКЦИЯ ПОГОДЫ НА НЕДЕЛЮ) ---------------

def send_forecast_weekly(chat_id, coords, url, days=7):
    try:
        params = {
            'lat': coords['latitude'],
            'lon': coords['longitude'],
            'appid': API_KEY,
        }
        response = requests.get(url, params=params)
        data = response.json()

        if response.status_code == 200:
            forecasts = data['list'][:days * 8]
            message = "Прогноз на неделю:\n"

            for forecast in forecasts:
                date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                formatted_date = date_time.strftime("%d-%m-%Y %H:%M:%S")
                temperature = round(forecast['main']['temp'] - 273.15)
                feels_like = round(forecast['main']['feels_like'] - 273.15)
                humidity = forecast['main']['humidity']
                pressure = forecast['main']['pressure']
                wind_speed = forecast['wind']['speed']
                description = translate_weather_description(forecast['weather'][0]['description'])

                message += (
                    f"{formatted_date}:\n"
                    f"Температура: {temperature}°C\n"
                    f"Ощущается как: {feels_like}°C\n"
                    f"Влажность: {humidity}%\n"
                    f"Давление: {pressure} мм рт. ст\n"
                    f"Скорость ветра: {wind_speed} м/с\n"
                    f"Описание погоды: {description}\n\n"
                )

            message_chunks = [message[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]

            for chunk in message_chunks:
                bot.send_message(chat_id, chunk)
        else:
            bot.send_message(chat_id, "Не удалось получить прогноз погоды на неделю.")
    except Exception as e:
        print(f"Ошибка при отправке прогноза на неделю: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на неделю. Попробуйте позже.")

# (15.10) --------------- КОД ДЛЯ "ПОГОДЫ" (ФУНКЦИЯ ПОГОДЫ НА МЕСЯЦ) ---------------

def send_forecast_monthly(chat_id, coords, url, days=30):
    try:
        params = {
            'lat': coords['latitude'],
            'lon': coords['longitude'],
            'appid': API_KEY,
        }
        response = requests.get(url, params=params)
        data = response.json()

        if response.status_code == 200:
            forecasts = data['list'][:days * 8]
            message = "Прогноз на месяц:\n"

            for forecast in forecasts:
                date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                formatted_date = date_time.strftime("%d-%m-%Y %H:%M:%S")
                temperature = round(forecast['main']['temp'] - 273.15)
                feels_like = round(forecast['main']['feels_like'] - 273.15)
                humidity = forecast['main']['humidity']
                pressure = forecast['main']['pressure']
                wind_speed = forecast['wind']['speed']
                description = translate_weather_description(forecast['weather'][0]['description'])

                message += (
                    f"{formatted_date}:\n"
                    f"Температура: {temperature}°C\n"
                    f"Ощущается как: {feels_like}°C\n"
                    f"Влажность: {humidity}%\n"
                    f"Давление: {pressure} мм рт. ст\n"
                    f"Скорость ветра: {wind_speed} м/с\n"
                    f"Описание погоды: {description}\n\n"
                )

            message_chunks = [message[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]

            for chunk in message_chunks:
                bot.send_message(chat_id, chunk)
        else:
            bot.send_message(chat_id, "Не удалось получить прогноз погоды на месяц.")
    except Exception as e:
        print(f"Ошибка при отправке прогноза на месяц: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на месяц. Попробуйте позже.")

# (16) --------------- КОД ДЛЯ "ФУНКЦИЯ ДЛЯ ОБНОВЛЕНИЙ ОТ TG" ---------------

def main_polling():
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(5)

# (17) --------------- КОД ДЛЯ "ЗАПУСК БОТА" ---------------
if __name__ == '__main__':
    bot.polling(none_stop=True, interval=1, timeout=30)