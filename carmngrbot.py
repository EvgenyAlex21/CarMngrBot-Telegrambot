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
import time
import logging
import calendar
from telegram_bot_calendar import DetailedTelegramCalendar
from datetime import date
from requests.exceptions import ReadTimeout, ConnectionError

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
    item7 = types.KeyboardButton("Цены на топливо")
    
    markup.add(item1, item2)
    markup.add(item3, item4)
    markup.add(item5, item7)
    markup.add(item6)

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
        bot.register_next_step_handler(sent, process_passengers_step, date, distance, fuel_type, price_per_liter, fuel_consumption)  # type: ignore
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
        bot.register_next_step_handler(sent, process_passengers_step, date, distance, fuel_type, price_per_liter, fuel_consumption) # type: ignore
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
        bot.register_next_step_handler(sent, process_passengers_step, date, distance, fuel_type, price_per_liter, fuel_consumption) # type: ignore
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
        try:
            start_address = geolocator.reverse((location.latitude, location.longitude), timeout=10).address
        except GeocoderUnavailable: # type: ignore
            bot.send_message(chat_id, "Сервис геолокации временно недоступен. Попробуйте позже.")
            return
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
        try:
            location = geolocator.geocode(start_location, timeout=10)
        except GeocoderUnavailable: # type: ignore
            bot.send_message(chat_id, "Сервис геолокации временно недоступен. Попробуйте позже.")
            return
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
        try:
            start_address = geolocator.reverse((location.latitude, location.longitude), timeout=10).address
        except GeocoderUnavailable: # type: ignore
            bot.send_message(chat_id, "Сервис геолокации временно недоступен. Попробуйте позже.")
            return
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
        try:
            location = geolocator.geocode(start_location, timeout=10)
        except GeocoderUnavailable: # type: ignore
            bot.send_message(chat_id, "Сервис геолокации временно недоступен. Попробуйте позже.")
            return
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
        try:
            end_address = geolocator.reverse((location.latitude, location.longitude), timeout=10).address
        except GeocoderUnavailable: # type: ignore
            bot.send_message(chat_id, "Сервис геолокации временно недоступен. Попробуйте позже.")
            return
        trip_data[chat_id]["end_location"] = {
            "address": end_address,
            "latitude": location.latitude,
            "longitude": location.longitude
        }
        bot.send_message(chat_id, f"Ваше конечное местоположение:\n\n{end_address}")
    else:  # Если пользователь ввел текстовое местоположение
        end_location = message.text
        try:
            location = geolocator.geocode(end_location, timeout=10)
        except GeocoderUnavailable: # type: ignore
            bot.send_message(chat_id, "Сервис геолокации временно недоступен. Попробуйте позже.")
            return
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

    start_coords = (trip_data[chat_id]["start_location"]["latitude"], trip_data[chat_id]["start_location"]["longitude"])
    end_coords = (trip_data[chat_id]["end_location"]["latitude"], trip_data[chat_id]["end_location"]["longitude"])
    distance_km = geodesic(start_coords, end_coords).kilometers

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_auto = types.KeyboardButton("Использовать автоматическое расстояние")
    item_input = types.KeyboardButton("Ввести свое расстояние")
    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item2 = types.KeyboardButton("В главное меню")

    markup.add(item_auto, item_input)
    markup.add(item1)
    markup.add(item2)
    
    sent = bot.send_message(chat_id, "Выберите вариант:", reply_markup=markup)
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
        bot.send_message(chat_id, f"Вы ввели свое расстояние: {custom_distance:.2f} км.", reply_markup=markup)
        
        # Теперь отображаем кнопки для выбора способа ввода даты
        markup_date = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_calendar = types.KeyboardButton("Выбрать дату из календаря")
        item_manual = types.KeyboardButton("Ввести дату вручную")
        item_skip = types.KeyboardButton("Пропустить ввод даты")
        markup_date.add(item_calendar, item_manual, item_skip)
        markup_date.add(item1)
        markup_date.add(item2)

        sent = bot.send_message(chat_id, "Выберите способ ввода даты:", reply_markup=markup_date)
        bot.register_next_step_handler(sent, process_date_step, custom_distance)
    except ValueError:
        sent = bot.send_message(chat_id, "Пожалуйста, введите корректное число для расстояния.", reply_markup=markup)
        bot.register_next_step_handler(sent, process_custom_distance_step)


def process_distance_choice_step(message, distance_km):
    chat_id = message.chat.id
    trip_data[chat_id]["distance"] = distance_km

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_auto = types.KeyboardButton("Использовать автоматическое расстояние")
    item_input = types.KeyboardButton("Ввести свое расстояние")
    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item2 = types.KeyboardButton("В главное меню")

    markup.add(item_auto, item_input)
    markup.add(item1, item2)

    if message.text == "Использовать автоматическое расстояние":
        bot.send_message(chat_id, f"Расстояние между точками: {distance_km:.2f} км.")
        process_date_step(message, distance_km)  # Переходим к выбору даты

    elif message.text == "Ввести свое расстояние":
        custom_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
        item2 = types.KeyboardButton("В главное меню")
        custom_markup.add(item1)
        custom_markup.add(item2)
        
        sent = bot.send_message(chat_id, "Пожалуйста, введите ваше расстояние в километрах:", reply_markup=custom_markup)
        bot.register_next_step_handler(sent, process_custom_distance_step)
    else:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите один из вариантов.", reply_markup=markup)
        bot.register_next_step_handler(sent, process_distance_choice_step, distance_km)

def process_date_step(message, distance):
    chat_id = message.chat.id

    if message.text == "Пропустить ввод даты":
        selected_date = "Без даты"
        process_selected_date(message, selected_date)

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_calendar = types.KeyboardButton("Выбрать дату из календаря")
    item_manual = types.KeyboardButton("Ввести дату вручную")
    item_skip = types.KeyboardButton("Пропустить ввод даты")
    markup.add(item_calendar, item_manual, item_skip)
    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item2 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)

    # Отправляем сообщение с новыми кнопками для выбора способа ввода даты
    sent = bot.send_message(chat_id, "Выберите способ ввода даты:", reply_markup=markup)
    bot.register_next_step_handler(sent, handle_date_selection, distance)

def handle_date_selection(message, distance):
    chat_id = message.chat.id
    user_code = trip_data[chat_id].get("user_code", "ru")  # Задаем код по умолчанию

    if message.text == "Пропустить ввод даты":
        selected_date = "Без даты"
        process_selected_date(message, selected_date)

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text == "Выбрать дату из календаря":
        show_calendar(chat_id, user_code)  # Передаем user_code
    elif message.text == "Ввести дату вручную":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
        item2 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2)

        sent = bot.send_message(chat_id, "Введите дату поездки в формате ДД.ММ.ГГГГ:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_manual_date_step, distance)
    elif message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
    elif message.text == "В главное меню":
        return_to_menu(message)
    else:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите корректный вариант.")
        bot.register_next_step_handler(sent, handle_date_selection, distance)

def show_calendar(chat_id, user_code):
    # Inline-календарь с использованием кода пользователя
    calendar, _ = DetailedTelegramCalendar(min_date=date(2000, 1, 1), max_date=date(3000, 12, 31), locale=user_code).build()

    # Обычная клавиатура для кнопок навигации
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item2 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)

    # Отправляем сообщение с навигацией и календарем
    bot.send_message(chat_id, "Календарь:", reply_markup=markup)
    bot.send_message(chat_id, "Выберите дату", reply_markup=calendar)

@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def handle_calendar(call):
    result, key, step = DetailedTelegramCalendar(
        min_date=date(2000, 1, 1), max_date=date(3000, 12, 31), unique_key=call.data
    ).process(call.data)

    if not result and key:
        bot.edit_message_text(f"Выберите {step}",
                              call.message.chat.id,
                              call.message.message_id,
                              reply_markup=key)
    elif result:
        selected_date = result.strftime('%d.%m.%Y')
        bot.edit_message_text(f"Вы выбрали дату {selected_date}",
                              call.message.chat.id,
                              call.message.message_id)

        # Переходим к следующему шагу
        process_selected_date(call.message, selected_date)


def process_selected_date(message, selected_date):
    chat_id = message.chat.id
    distance_km = trip_data[chat_id].get("distance")  # Получаем расстояние

    if distance_km is None:
        bot.send_message(chat_id, "Расстояние не было задано. Пожалуйста, попробуйте снова.")
        return

    show_fuel_types(chat_id, selected_date, distance_km)


def process_manual_date_step(message, distance):
    chat_id = message.chat.id
    date_pattern = r"\d{2}\.\d{2}\.\d{4}"  # Формат ДД.ММ.ГГГГ
    
    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    # Разметка только с двумя кнопками
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item2 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)

    if message.photo or message.video or message.document or message.animation or message.sticker or message.audio or message.contact or message.voice or message.video_note:
        sent = bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.", reply_markup=markup)
        bot.register_next_step_handler(sent, process_manual_date_step, distance)
        return

    if re.match(date_pattern, message.text):
        day, month, year = map(int, message.text.split('.'))
        if 2000 <= year <= 3000:  # Проверка корректности года
            try:
                datetime(year, month, day)  # Проверка правильности даты
                bot.send_message(chat_id, f"Вы выбрали дату {message.text}.", reply_markup=markup)  # Отправляем сообщение с двумя кнопками
                show_fuel_types(chat_id, message.text, distance)
            except ValueError:
                sent = bot.send_message(chat_id, "Неправильная дата. Пожалуйста, введите корректную дату.", reply_markup=markup)
                bot.register_next_step_handler(sent, process_manual_date_step, distance)
        else:
            sent = bot.send_message(chat_id, "Год должен быть в диапазоне от 2000 г. до 3000 г.", reply_markup=markup)
            bot.register_next_step_handler(sent, process_manual_date_step, distance)
    else:
        sent = bot.send_message(chat_id, "Неправильный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.", reply_markup=markup)
        bot.register_next_step_handler(sent, process_manual_date_step, distance)


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
    if message is None:
        return  # Проверка на None

    chat_id = message.chat.id

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    # Проверка на наличие мультимедийных элементов
    if message.photo or message.video or message.document or message.animation or message.sticker or message.audio or message.voice or message.video_note:
        bot.send_message(chat_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        # Зарегистрируем следующий шаг для ожидания текстового сообщения
        sent = bot.send_message(chat_id, "Выберите тип топлива:")
        bot.register_next_step_handler(sent, process_fuel_type, date, distance)
        return

    fuel_type = message.text.strip().lower() if message.text else ""

    # Проверка на допустимые типы топлива
    fuel_type_mapping = {
        "аи-92": "аи-92",
        "аи-95": "аи-95",
        "аи-98": "аи-98",
        "аи-100": "аи-100",
        "дт": "дт",
        "газ": "газ спбт",
    }

    # Проверка на допустимые значения
    if fuel_type not in fuel_type_mapping:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите тип топлива только из предложенных вариантов.")
        bot.register_next_step_handler(sent, process_fuel_type, date, distance)
        return

    actual_fuel_type = fuel_type_mapping[fuel_type]

    # Дальнейшая логика обработки
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Использовать актуальную цену")
    item2 = types.KeyboardButton("Ввести свою цену")
    item3 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item4 = types.KeyboardButton("В главное меню")
    markup.add(item1, item2)
    markup.add(item3)
    markup.add(item4)

    sent = bot.send_message(chat_id, "Выберите вариант ввода цены топлива:", reply_markup=markup)
    bot.register_next_step_handler(sent, handle_price_input_choice, date, distance, actual_fuel_type)


def handle_price_input_choice(message, date, distance, fuel_type):
    chat_id = message.chat.id
    
    if message.text == "Ввести свою цену":
        # Создаем новую клавиатуру с двумя кнопками
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
        item2 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2)

        sent = bot.send_message(chat_id, "Пожалуйста, введите цену за литр топлива:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_price_per_liter_step, date, distance, fuel_type)
    
    elif message.text == "Использовать актуальную цену":
        try:
            fuel_prices = get_average_fuel_prices()
            fuel_prices_lower = {key.lower(): value for key, value in fuel_prices.items()}
            price_per_liter = fuel_prices_lower.get(fuel_type.lower())

            if price_per_liter is None:
                raise ValueError("Price not found")

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
            item2 = types.KeyboardButton("В главное меню")
            markup.add(item1)
            markup.add(item2) 

            bot.send_message(chat_id, f"Актуальная средняя цена для {fuel_type.upper()} в РФ: {price_per_liter:.2f} руб./л.", reply_markup=markup)
            sent = bot.send_message(chat_id, "Введите расход топлива на 100 км:", reply_markup=markup)
            bot.register_next_step_handler(sent, process_fuel_consumption_step, date, distance, fuel_type, price_per_liter)
        
        except Exception as e:
            print(f"Ошибка получения цены: {e}")
            # Создаем новую клавиатуру с двумя кнопками
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
            item2 = types.KeyboardButton("В главное меню")
            markup.add(item1)
            markup.add(item2)

            sent = bot.send_message(chat_id, "Не удалось получить актуальную цену. Пожалуйста, введите свою цену.", reply_markup=markup)
            bot.register_next_step_handler(sent, process_price_per_liter_step, date, distance, fuel_type)

    elif message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
    elif message.text == "В главное меню":
        return_to_menu(message)
    else:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите один из предложенных вариантов.")
        bot.register_next_step_handler(sent, handle_price_input_choice, date, distance, fuel_type)


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
        
        # Создаем новую клавиатуру с двумя кнопками
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
    summary_message = "*ИНФОРМАЦИЯ О ПОЕЗДКЕ:*\n"
    summary_message += f"*Начальное местоположение:*\n{start_location['address']}\n"
    summary_message += f"*Конечное местоположение:*\n{end_location['address']}\n"
    summary_message += f"*Дата поездки:* {date}\n"
    summary_message += f"*Расстояние:* {distance:.2f} км.\n"
    summary_message += f"*Тип топлива:* {fuel_type}\n"
    summary_message += f"*Цена топлива за литр:* {price_per_liter:.2f} руб.\n"
    summary_message += f"*Расход топлива на 100 км:* {fuel_consumption} л.\n"
    summary_message += f"*Количество пассажиров:* {passengers}\n"
    summary_message += f"*ПОТРАЧЕНО ЛИТРОВ ТОПЛИВА:* {fuel_spent:.2f} л.\n"
    summary_message += f"*СТОИМОСТЬ ТОПЛИВА ДЛЯ ПОЕЗДКИ:* {fuel_cost:.2f} руб.\n"
    summary_message += f"*СТОИМОСТЬ ТОПЛИВА НА ЧЕЛОВЕКА:* {fuel_cost_per_person:.2f} руб.\n"
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


def update_excel_file(user_id):
    # Определяем путь к папке и файлу
    folder_path = "data base"
    file_path = os.path.join(folder_path, f"{user_id}_trips.xlsx")

    # Проверяем, существует ли файл, если нет, создаем его с заголовками
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=[
            "Дата", "Начальное местоположение", "Конечное местоположение",
            "Расстояние (км)", "Тип топлива", "Цена топлива (руб/л)",
            "Расход топлива (л/100 км)", "Количество пассажиров",
            "Потрачено литров", "Стоимость топлива (руб)", "Стоимость на человека (руб)", "Ссылка на маршрут"
        ])
        df.to_excel(file_path, index=False)

    # Загружаем существующие данные
    df = pd.read_excel(file_path)

    # Получаем данные поездок для пользователя
    trips = user_trip_data.get(user_id, [])

    # Если поездок нет, удаляем все строки, оставляя только заголовок
    if not trips:
        df = df.iloc[0:0]  # Очищаем DataFrame
    else:
        # Преобразуем поездки в DataFrame
        trip_records = []
        for trip in trips:
            trip_records.append([
                trip['start_location']['address'],
                trip['end_location']['address'],
                trip['date'],
                trip['distance'],
                trip['fuel_type'],
                trip['price_per_liter'],
                trip['fuel_consumption'],
                trip['passengers'],
                trip['fuel_spent'],
                trip['fuel_cost'],
                trip['fuel_cost_per_person'],
                trip.get('route_link', "Нет ссылки")  # Добавляем ссылку на маршрут
            ])
        df = pd.DataFrame(trip_records, columns=[
            "Начальное местоположение", "Конечное местоположение", "Дата", 
            "Расстояние (км)", "Тип топлива", "Цена топлива (руб/л)",
            "Расход топлива (л/100 км)", "Количество пассажиров",
            "Потрачено литров", "Стоимость топлива (руб)", "Стоимость на человека (руб)", "Ссылка на маршрут"
        ])

    # Записываем обновленные данные обратно в файл
    df.to_excel(file_path, index=False)

    # Открываем файл Excel для стилизации
    workbook = load_workbook(file_path)
    worksheet = workbook.active

    # Устанавливаем ширину столбцов на основе максимальной длины содержимого
    for column in worksheet.columns:
        max_length = 0
        column_letter = column[0].column_letter  # Получаем букву столбца
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception as e:
                pass
        adjusted_width = (max_length + 2)  # Добавляем небольшое значение для отступа
        worksheet.column_dimensions[column_letter].width = adjusted_width

    # Центровка всех данных
    for row in worksheet.iter_rows(min_row=2):  # Пропускаем заголовок
        for cell in row:
            cell.alignment = Alignment(horizontal='center', vertical='center')

    # Добавляем толстые границы для последних 4 колонок
    thick_border = Border(left=Side(style='thick'), right=Side(style='thick'),
                          top=Side(style='thick'), bottom=Side(style='thick'))
    
    for row in worksheet.iter_rows(min_row=2, min_col=9, max_col=12):  # Колонки 9-12
        for cell in row:
            cell.border = thick_border

    # Сохраняем изменения в Excel
    workbook.save(file_path)

import os
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.styles import Alignment, Border, Side

import pandas as pd
import os
from openpyxl import load_workbook

def save_trip_to_excel(user_id, trip):
    # Путь к папке для хранения данных
    directory = "data base"
    if not os.path.exists(directory):
        os.makedirs(directory)

    file_path = os.path.join(directory, f"{user_id}_trips.xlsx")

    # Создание DataFrame для новой поездки
    new_trip_data = {
        "Начальное местоположение": trip['start_location']['address'],
        "Конечное местоположение": trip['end_location']['address'],
        "Дата": trip['date'],
        "Расстояние (км)": round(trip.get('distance', None), 2),  # Округление до 2 знаков
        "Тип топлива": trip.get('fuel_type', None),
        "Цена топлива (руб/л)": round(trip.get('price_per_liter', None), 2),  # Округление до 2 знаков
        "Расход топлива (л/100 км)": round(trip.get('fuel_consumption', None), 2),  # Округление до 2 знаков
        "Количество пассажиров": trip.get('passengers', None),
        "Потрачено литров": round(trip.get('fuel_spent', None), 2),  # Округление до 2 знаков
        "Стоимость топлива (руб)": round(trip.get('fuel_cost', None), 2),  # Округление до 2 знаков
        "Стоимость на человека (руб)": round(trip.get('fuel_cost_per_person', None), 2),  # Округление до 2 знаков
        "Ссылка на маршрут": trip.get('route_link', None)
    }

    new_trip_df = pd.DataFrame([new_trip_data])

    # Проверяем, существует ли файл и загружаем существующие данные
    if os.path.exists(file_path):
        existing_data = pd.read_excel(file_path)

        # Удаляем пустые столбцы из существующих данных
        existing_data = existing_data.dropna(axis=1, how='all')

        # Объединяем только если существуют данные в обоих DataFrame
        if not existing_data.empty and not new_trip_df.empty:
            updated_data = pd.concat([existing_data, new_trip_df], ignore_index=True)
        else:
            updated_data = existing_data if not existing_data.empty else new_trip_df
    else:
        updated_data = new_trip_df  # Если файла нет, просто используем новые данные

    # Сохраняем обновленный DataFrame в Excel
    updated_data.to_excel(file_path, index=False)

    # Открываем файл Excel и растягиваем ячейки
    workbook = load_workbook(file_path)
    worksheet = workbook.active

    # Устанавливаем ширину столбцов на основе максимальной длины содержимого
    for column in worksheet.columns:
        max_length = 0
        column_letter = column[0].column_letter  # Получаем букву столбца
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception as e:
                pass
        adjusted_width = (max_length + 2)  # Добавляем небольшое значение для отступа
        worksheet.column_dimensions[column_letter].width = adjusted_width

    # Применяем выравнивание по центру для всех данных
    for row in worksheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(horizontal="center", vertical="center")

    # Выделяем толстые границы для последних 4 колонок
    thick_border = Border(left=Side(style='thick'), right=Side(style='thick'),
                          top=Side(style='thick'), bottom=Side(style='thick'))

    for row in worksheet.iter_rows(min_col=worksheet.max_column-3, max_col=worksheet.max_column):
        for cell in row:
            cell.border = thick_border

    # Сохраняем изменения в Excel
    workbook.save(file_path)


# (9.14) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (КОМАНДА "СОХРАНИТЬ ПОЕЗДКУ") ---------------

@bot.message_handler(func=lambda message: message.text == "Сохранить поездку")
def save_data_handler(message):
    user_id = message.chat.id
    if user_id in temporary_trip_data and temporary_trip_data[user_id]:
        if user_id not in user_trip_data:
            user_trip_data[user_id] = []

        # Переносим данные из временных данных в постоянные
        user_trip_data[user_id].extend(temporary_trip_data[user_id])

        # Получаем последнюю поездку
        last_trip = user_trip_data[user_id][-1]

        # Сохраняем данные поездки в базу данных
        save_trip_data(user_id) 
        
        # Сохраняем последнюю поездку в Excel
        save_trip_to_excel(user_id, last_trip)

        # Очищаем временные данные
        temporary_trip_data[user_id] = []
        
        # Создаем клавиатуру для возврата в меню
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
        item2 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2) 
        
        bot.send_message(user_id, "Данные поездки успешно сохранены.", reply_markup=markup)

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
                button_text = f"{i}. {trip['date']}"
                markup.add(button_text)
            
            # Добавляем кнопку для просмотра в Excel
            markup.add("Посмотреть в Excel")
            markup.add("Вернуться в меню расчета топлива")
            markup.add("В главное меню")
            
            # Отправляем сообщение с запросом на выбор поездки и кнопками
            bot.send_message(user_id, "Выберите поездку для просмотра:", reply_markup=markup)
    else:
        bot.send_message(user_id, "У вас нет сохраненных поездок.")

@bot.message_handler(func=lambda message: message.text == "Посмотреть в Excel")
def send_excel_file(message):
    user_id = message.chat.id
    excel_file_path = f"data base/{user_id}_trips.xlsx"

    if os.path.exists(excel_file_path):
        with open(excel_file_path, 'rb') as excel_file:
            bot.send_document(user_id, excel_file)
    else:
        bot.send_message(user_id, "Файл Excel не найден. Убедитесь, что у вас есть сохраненные поездки.")

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
        summary_message = f"*ИТОГОВЫЕ ДАННЫЕ ПОЕЗДКИ* {trip_index + 1}:\n\n"
        summary_message += f"*Начальное местоположение:*\n\n{start_address}\n\n"
        summary_message += f"*Конечное местоположение:*\n\n{end_address}\n\n"
        summary_message += f"*Дата поездки:* {trip['date']}\n\n"
        summary_message += f"*Расстояние:* {trip['distance']:.2f} км.\n\n"
        summary_message += f"*Тип топлива:* {trip['fuel_type']}\n\n"
        summary_message += f"*Цена топлива за литр:* {trip['price_per_liter']:.2f} руб.\n\n"
        summary_message += f"*Расход топлива на 100 км:* {trip['fuel_consumption']} л.\n\n"
        summary_message += f"*Количество пассажиров:* {trip['passengers']}\n\n"
        summary_message += f"*ПОТРАЧЕНО ЛИТРОВ ТОПЛИВА:* {trip['fuel_spent']:.2f} л.\n\n"
        summary_message += f"*СТОИМОСТЬ ТОПЛИВА ДЛЯ ПОЕЗДКИ:* {trip['fuel_cost']:.2f} руб.\n\n"
        summary_message += f"*СТОИМОСТЬ ТОПЛИВА НА ЧЕЛОВЕКА:* {trip['fuel_cost_per_person']:.2f} руб.\n\n"

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

    if user_id in user_trip_data:
        if user_trip_data[user_id]:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

            # Изменяем создание кнопок для отображения номера и даты поездки
            for i, trip in enumerate(user_trip_data[user_id], start=1):
                trip_date = trip.get('date', 'Дата не указана')  # Получаем дату поездки
                button_text = f"№{i}. {trip_date}"  # Создаем текст кнопки с номером и датой
                markup.add(types.KeyboardButton(button_text))

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

    # Проверяем, соответствует ли текст кнопки формату "№N. дата"
    if message.text.startswith("№") and "." in message.text:
        try:
            trip_number = int(message.text.split(".")[0][1:])  # Извлекаем номер поездки
            if 1 <= trip_number <= len(user_trip_data[user_id]):
                deleted_trip = user_trip_data[user_id].pop(trip_number - 1)
                bot.send_message(user_id, f"Поездка номер {trip_number} успешно удалена.")
                
                # Обновляем Excel файл
                update_excel_file(user_id)

            else:
                bot.send_message(user_id, "Неверный номер поездки. Пожалуйста, укажите корректный номер.")
        except ValueError:
            bot.send_message(user_id, "Произошла ошибка при обработке номера поездки.")
    else:
        bot.send_message(user_id, "Пожалуйста, выберите номер поездки для удаления с помощью кнопок.")

    reset_and_start_over(user_id)

# Функция для подтверждения удаления всех поездок
def confirm_delete_all(message):
    user_id = message.chat.id
    
    if message.text is None:
        bot.send_message(user_id, "Пожалуйста, отправьте текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_all)
        return

    user_response = message.text.lower()

    if user_response == "да":
        if user_id in user_trip_data and user_trip_data[user_id]:
            user_trip_data[user_id].clear()
            bot.send_message(user_id, "Все поездки были успешно удалены.")
            # Очистка Excel файла
            update_excel_file(user_id)
        else:
            bot.send_message(user_id, "У вас нет поездок для удаления.")
            reset_and_start_over(user_id)
        
        # Очищаем Excel файл, оставляя только заголовки
        excel_file = os.path.join('data base', f"{user_id}_trips.xlsx")
        if os.path.exists(excel_file):
            workbook = load_workbook(excel_file)
            sheet = workbook.active
            for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row):
                for cell in row:
                    cell.value = None
            workbook.save(excel_file)

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
    item8 = types.KeyboardButton("Ваш транспорт")

    markup.add(item8)
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
    item8 = types.KeyboardButton("Ваш транспорт")
    
    markup.add(item8)
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

# Обработка данных о расходах
def save_expense_data(user_id, user_data, selected_transport):
    # Задаем новый путь к папке и файлу
    folder_path = os.path.join("data base", "expense")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Измененное имя файла: "user_id_expenses.json"
    file_path = os.path.join(folder_path, f"{user_id}_expenses.json")

    # Загружаем текущие данные пользователя, чтобы сохранить user_categories и другие поля
    current_data = load_expense_data(user_id)

    # Сохраняем категории и другие данные, если они уже есть
    if "user_categories" in current_data:
        user_data["user_categories"] = current_data["user_categories"]

    # Добавляем поле selected_transport для данного пользователя
    user_data["selected_transport"] = selected_transport

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(user_data, file, ensure_ascii=False, indent=4)

def load_expense_data(user_id):
    # Путь к файлу в новой папке
    folder_path = os.path.join("data base", "expense")
    file_path = os.path.join(folder_path, f"{user_id}_expenses.json")
    
    # Проверка, существует ли файл, перед его открытием
    if not os.path.exists(file_path):
        return {"user_categories": [], "selected_transport": ""}  # Возвращаем пустой словарь, если файла нет

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            if not isinstance(data, dict):
                raise ValueError("Данные не являются словарем.")
            if "selected_transport" not in data:
                data["selected_transport"] = ""  # Добавляем поле, если его нет
    except (FileNotFoundError, ValueError) as e:
        print("Ошибка загрузки данных:", e)
        data = {"user_categories": [], "selected_transport": ""}  # Обеспечиваем наличие пустого значения

    return data

def get_user_categories(user_id):
    data = load_expense_data(user_id)
    default_categories = ["Без категории", "АЗС", "Мойка", "Парковка", "Платная дорога", "Страховка", "Штрафы"]
    user_categories = data.get("user_categories", [])
    return default_categories + user_categories

def add_user_category(user_id, new_category):
    data = load_expense_data(user_id)
    if "user_categories" not in data:
        data["user_categories"] = []
    data["user_categories"].append(new_category)
    save_expense_data(user_id, data)

def remove_user_category(user_id, category_to_remove):
    data = load_expense_data(user_id)
    if "user_categories" in data and category_to_remove in data["user_categories"]:
        data["user_categories"].remove(category_to_remove)
        save_expense_data(user_id, data)

# Основная функция для записи траты
@bot.message_handler(func=lambda message: message.text == "Записать трату")
def record_expense(message):
    user_id = message.from_user.id

    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, record_expense)
        return

    markup = get_user_transport_keyboard(str(user_id))
    # Добавляем кнопки "Вернуться в меню трат и ремонтов" и "В главное меню"
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Выберите транспорт для записи траты:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection_for_record)

def handle_transport_selection_for_record(message):
    user_id = message.from_user.id

    # Проверяем, была ли выбрана кнопка для возврата в меню
    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return
    elif message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text == "Добавить транспорт":
        add_transport(message)
        return

    selected_transport = message.text
    for transport in user_transport.get(str(user_id), []):
        if f"{transport['brand']} {transport['model']} {transport['year']}" == selected_transport:
            brand, model, year = transport['brand'], transport['model'], transport['year']
            break
    else:
        bot.send_message(user_id, "Не удалось найти указанный транспорт. Пожалуйста, выберите снова.")
        bot.send_message(user_id, "Выберите транспорт или добавьте новый:", reply_markup=get_user_transport_keyboard(user_id))
        return

    # Получение категорий и обработка выбора категории
    process_category_selection(user_id, brand, model, year)

def process_category_selection(user_id, brand, model, year, prompt_message=None):
    categories = get_user_categories(user_id)

    # Создаем текстовый список категорий
    category_list = "\n".join(f"{i + 1}. {category}" for i, category in enumerate(categories))
    
    # Обновленный текст
    category_list = f"*Выберите категорию или '0' для отмены:*\n\n{category_list}"

    # Настраиваем клавиатуру с кнопками
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Добавляем кнопки в нужной конфигурации
    markup.row(
        types.KeyboardButton("Добавить категорию"),
        types.KeyboardButton("Удалить категорию")
    )
    markup.add(
        types.KeyboardButton("Вернуться в меню трат и ремонтов")
    )
    markup.add(
        types.KeyboardButton("В главное меню")
    )
    if prompt_message:
        bot.send_message(user_id, category_list, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(prompt_message, get_expense_category, brand, model, year)
    else:
        prompt_message = bot.send_message(user_id, category_list, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(prompt_message, get_expense_category, brand, model, year)

def get_expense_category(message, brand, model, year):
    user_id = message.from_user.id
    selected_index = message.text.strip()

    # Переход в меню в зависимости от выбора
    if selected_index == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return
    elif selected_index == "В главное меню":
        return_to_menu(message)
        return

    if selected_index == 'Без категории':
        selected_category = "Без категории"
        proceed_to_expense_name(message, selected_category, brand, model, year)
        return

    if selected_index == 'Добавить категорию':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            types.KeyboardButton("Вернуться в меню трат и ремонтов")
        )
        markup.add(
            types.KeyboardButton("В главное меню")
        )
        bot.send_message(user_id, "Введите название новой категории:", reply_markup=markup)
        bot.register_next_step_handler(message, add_new_category, brand, model, year)
        return

    if selected_index == 'Удалить категорию':
        handle_category_removal(message, brand, model, year)
        return

    if selected_index.isdigit():
        index = int(selected_index) - 1
        categories = get_user_categories(user_id)
        if 0 <= index < len(categories):
            selected_category = categories[index]
            proceed_to_expense_name(message, selected_category, brand, model, year)
        else:
            bot.send_message(user_id, "Неверный номер категории. Попробуйте снова.")
            bot.register_next_step_handler(message, get_expense_category, brand, model, year)
    else:
        bot.send_message(user_id, "Пожалуйста, введите номер категории.")
        bot.register_next_step_handler(message, get_expense_category, brand, model, year)

def add_new_category(message, brand, model, year):
    user_id = message.from_user.id
    new_category = message.text.strip()

    if new_category in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if new_category == "Вернуться в меню трат и ремонтов":
            return_to_menu_2(message)
        else:
            return_to_menu(message)
        return

    if new_category:
        add_user_category(user_id, new_category)
        bot.send_message(user_id, f"Категория '{new_category}' добавлена.")
    
    process_category_selection(user_id, brand, model, year)

def proceed_to_expense_name(message, selected_category, brand, model, year):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите название траты:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expense_name, selected_category, brand, model, year)

# Обработчик для ввода названия траты
def get_expense_name(message, selected_category, brand, model, year):
    user_id = message.from_user.id

    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_menu_2(message)
        else:
            return_to_menu(message)
        return

    expense_name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_skip = types.KeyboardButton("Пропустить описание")  
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_skip)
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите описание траты или пропустите этот шаг:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expense_description, selected_category, expense_name, brand, model, year)

def get_expense_description(message, selected_category, expense_name, brand, model, year):
    user_id = message.from_user.id

    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_menu_2(message)
        else:
            return_to_menu(message)
        return

    description = message.text if message.text != "Пропустить описание" else ""

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return) 
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите дату траты в формате ДД.ММ.ГГГГ:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expense_date, selected_category, expense_name, description, brand, model, year)

def get_expense_date(message, selected_category, expense_name, description, brand, model, year):
    user_id = message.from_user.id

    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_menu_2(message)
        else:
            return_to_menu(message)
        return

    expense_date = message.text
    date_parts = expense_date.split(".")
    if len(date_parts) != 3 or not all(part.isdigit() for part in date_parts):
        bot.send_message(user_id, "Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")
        bot.register_next_step_handler(message, get_expense_date, selected_category, expense_name, description, brand, model, year)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return) 
    markup.add(item_main_menu)
    
    bot.send_message(user_id, "Введите сумму траты:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expense_amount, selected_category, expense_name, description, expense_date, brand, model, year)
    
def get_expense_amount(message, selected_category, expense_name, description, expense_date, brand, model, year):
    user_id = message.from_user.id

    # Получаем сумму траты
    expense_amount = message.text.replace(",", ".")
    if not is_numeric(expense_amount):
        bot.send_message(user_id, "Пожалуйста, введите сумму траты в числовом формате.")
        bot.register_next_step_handler(message, get_expense_amount, selected_category, expense_name, description, expense_date, brand, model, year)
        return

    # Загружаем данные о расходах пользователя
    data = load_expense_data(user_id)
    if str(user_id) not in data:
        data[str(user_id)] = {"expenses": []}

    # Добавляем новый расход
    selected_transport = f"{brand} {model} {year}"
    expenses = data[str(user_id)].get("expenses", [])
    new_expense = {
        "category": selected_category,
        "name": expense_name,
        "date": expense_date,
        "amount": expense_amount,
        "description": description,
        "transport": {"brand": brand, "model": model, "year": year}
    }
    expenses.append(new_expense)
    data[str(user_id)]["expenses"] = expenses
    save_expense_data(user_id, data, selected_transport)  # Передаем selected_transport здесь

    # Сохраняем расход в Excel
    save_expense_to_excel(user_id, new_expense)

    bot.send_message(user_id, "Трата успешно записана!")
    send_menu(user_id)

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
import os

def save_expense_to_excel(user_id, expense_data):
    # Путь к Excel-файлу пользователя
    excel_path = os.path.join("data base", "expense", "excel", f"{user_id}_expenses.xlsx")

    # Проверяем, существует ли директория
    directory = os.path.dirname(excel_path)
    if not os.path.exists(directory):
        os.makedirs(directory)  # Создаем директорию, если она не существует

    # Загружаем или создаём рабочую книгу
    try:
        if os.path.exists(excel_path):
            workbook = load_workbook(excel_path)
        else:
            workbook = Workbook()
            workbook.remove(workbook.active)  # Удаляем стандартный лист
        
        # Лист для всех расходов (Summary)
        summary_sheet = workbook["Summary"] if "Summary" in workbook.sheetnames else workbook.create_sheet("Summary")
        
        # Лист для конкретного транспортного средства
        transport_sheet_name = f"{expense_data['transport']['brand']}_{expense_data['transport']['model']}_{expense_data['transport']['year']}"
        if transport_sheet_name not in workbook.sheetnames:
            transport_sheet = workbook.create_sheet(transport_sheet_name)
        else:
            transport_sheet = workbook[transport_sheet_name]
        
        # Определяем заголовки
        headers = ["Транспорт", "Категория", "Название", "Дата", "Сумма", "Описание"]
        
        # Вспомогательная функция для настройки листов
        def setup_sheet(sheet):
            if sheet.max_row == 1:
                sheet.append(headers)
                for cell in sheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal="center")

        # Добавляем заголовки и данные
        for sheet in [summary_sheet, transport_sheet]:
            setup_sheet(sheet)
            row_data = [
                f"{expense_data['transport']['brand']} {expense_data['transport']['model']} {expense_data['transport']['year']}",
                expense_data["category"],
                expense_data["name"],
                expense_data["date"],
                expense_data["amount"],
                expense_data["description"],
            ]
            sheet.append(row_data)
        
        # Автоподгонка столбцов
        for sheet in [summary_sheet, transport_sheet]:
            for col in sheet.columns:
                max_length = max(len(str(cell.value)) for cell in col)
                sheet.column_dimensions[get_column_letter(col[0].column)].width = max_length + 2

        # Сохраняем рабочую книгу
        workbook.save(excel_path)
    except Exception as e:
        print(f"Ошибка при сохранении данных в Excel: {e}")

# Удаление категории
# Удаление категории
@bot.message_handler(func=lambda message: message.text == "Удалить категорию")
def handle_category_removal(message, brand=None, model=None, year=None):
    user_id = message.from_user.id
    categories = get_user_categories(user_id)

    # Создаем текстовый список категорий
    category_list = "\n".join(f"{i + 1}. {category}" for i, category in enumerate(categories))
    
    # Обновленный текст с жирным началом
    category_list = f"*Выберите категорию для удаления или '0' для отмены:*\n\n{category_list}"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))

    bot.send_message(user_id, category_list, reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, remove_selected_category, brand, model, year)

def remove_selected_category(message, brand, model, year):
    user_id = message.from_user.id
    selected_index = message.text.strip()

    # Проверка на команды меню
    if selected_index == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return
    elif selected_index == "В главное меню":
        return_to_menu(message)
        return

    if selected_index == '0':
        bot.send_message(user_id, "Удаление категории отменено.")
        return process_category_selection(user_id, brand, model, year)

    if selected_index.isdigit():
        index = int(selected_index) - 1
        categories = get_user_categories(user_id)
        default_categories = ["Без категории", "АЗС", "Мойка", "Парковка", "Платная дорога", "Страховка", "Штрафы"]

        if 0 <= index < len(categories):
            category_to_remove = categories[index]
            if category_to_remove in default_categories:
                bot.send_message(user_id, f"Нельзя удалить системную категорию '{category_to_remove}'. Попробуйте еще раз.")
                return bot.register_next_step_handler(message, remove_selected_category, brand, model, year)

            remove_user_category(user_id, category_to_remove)
            bot.send_message(user_id, f"Категория '{category_to_remove}' успешно удалена.")
        else:
            bot.send_message(user_id, "Неверный номер категории. Попробуйте снова.")
            return bot.register_next_step_handler(message, remove_selected_category, brand, model, year)
    else:
        bot.send_message(user_id, "Пожалуйста, введите номер категории.")
        return bot.register_next_step_handler(message, remove_selected_category, brand, model, year)

    return process_category_selection(user_id, brand, model, year)

def is_numeric(s):
    if s is not None:
        try:
            float(s)
            return True
        except ValueError:
            return False
    return False

# (10.9) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "ПОСМОТРЕТЬ ТРАТЫ") ---------------

def create_transport_options_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_add_transport = types.KeyboardButton("Добавить транспорт")
    item_cancel = types.KeyboardButton("Отмена")
    markup.add(item_add_transport, item_cancel)
    return markup

def ask_add_transport(message):
    user_id = message.from_user.id

    if message.text == "Добавить транспорт":
        # Вызовите функцию для добавления транспорта
        add_transport(message)
    elif message.text == "Отмена":
        bot.send_message(user_id, "Вы отменили добавление транспорта.")
    else:
        bot.send_message(user_id, "Пожалуйста, выберите вариант.", reply_markup=create_transport_options_markup())
        bot.register_next_step_handler(message, ask_add_transport)

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

selected_transport_dict = {}

# Функция для фильтрации трат по транспорту
def filter_expenses_by_transport(user_id, expenses):
    selected_transport = selected_transport_dict.get(user_id)
    if not selected_transport:
        return expenses

    # Фильтруем по транспорту
    filtered_expenses = [expense for expense in expenses if f"{expense['transport']['brand']} {expense['transport']['model']} ({expense['transport']['year']})" == selected_transport]
    return filtered_expenses

# Функция для отправки сообщений, если сообщение длинное
def send_message_with_split(user_id, message_text):
    bot.send_message(user_id, message_text)

# Функция для отправки меню
def send_menu1(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Траты (по категориям)")
    item2 = types.KeyboardButton("Траты (месяц)")
    item3 = types.KeyboardButton("Траты (год)")
    item4 = types.KeyboardButton("Траты (всё время)")
    item_excel = types.KeyboardButton("Посмотреть траты в EXCEL")  # Новая кнопка
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item1, item2, item3, item4, item_excel)
    markup.add(item_return, item_main_menu)

    bot.send_message(user_id, "Выберите вариант просмотра трат:", reply_markup=markup)

# Обработчик для просмотра трат
@bot.message_handler(func=lambda message: message.text == "Посмотреть траты")
def view_expenses(message):
    user_id = message.from_user.id

    # Загружаем данные о транспорте
    transport_list = load_transport_data(user_id)

    if not transport_list:
        bot.send_message(user_id, "У вас нет сохраненного транспорта. Хотите добавить транспорт?", reply_markup=create_transport_options_markup())
        bot.register_next_step_handler(message, ask_add_transport)
        return

    # Если транспорт есть, продолжаем с выбором
    transport_buttons = [types.KeyboardButton(f"{t['brand']} {t['model']} ({t['year']})") for t in transport_list]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*transport_buttons)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    markup.add(item_return)

    bot.send_message(user_id, "Выберите ваш транспорт:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection)

# Обработчик выбора транспорта
def handle_transport_selection(message):
    user_id = message.from_user.id
    selected_transport = message.text

    if selected_transport == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    # Сохраняем выбранный транспорт для пользователя
    selected_transport_dict[user_id] = selected_transport

    # Теперь можем показывать доступные фильтры для трат
    bot.send_message(user_id, f"Показываю траты для транспорта: {selected_transport}")
    send_menu1(user_id)

@bot.message_handler(func=lambda message: message.text == "Посмотреть траты в EXCEL")
def send_expenses_excel(message):
    user_id = message.from_user.id

    # Путь к Excel файлу
    excel_path = os.path.join("data base", "expense", "excel", f"{user_id}_expenses.xlsx")

    # Проверяем наличие файла
    if not os.path.exists(excel_path):
        bot.send_message(user_id, "Файл с вашими тратами не найден.")
        return

    # Отправка файла пользователю
    with open(excel_path, 'rb') as excel_file:
        bot.send_document(user_id, excel_file)

# Обработчик для просмотра трат по категориям
@bot.message_handler(func=lambda message: message.text == "Траты (по категориям)")
def view_expenses_by_category(message):
    user_id = message.from_user.id
    user_data = load_expense_data(user_id)
    expenses = user_data.get(str(user_id), {}).get("expenses", [])

    # Фильтруем траты по выбранному транспорту
    expenses = filter_expenses_by_transport(user_id, expenses)

    # Получаем уникальные категории трат для выбранного транспорта
    categories = set(expense['category'] for expense in expenses)
    if not categories:
        bot.send_message(user_id, "Нет доступных категорий для выбранного транспорта.")
        send_menu1(user_id)  # Возврат в меню трат и ремонтов
        return

    category_buttons = [types.KeyboardButton(category) for category in categories]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*category_buttons)
    item_return_to_expenses = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_return_to_main = types.KeyboardButton("В главное меню")
    markup.add(item_return_to_expenses, item_return_to_main)

    bot.send_message(user_id, "Выберите категорию для просмотра трат:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_category_selection)

# Обработчик выбора категории
def handle_category_selection(message):
    user_id = message.from_user.id
    selected_category = message.text

    if selected_category == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if selected_category == "В главное меню":
        return_to_menu(message)  # Возврат в главное меню
        return

    user_data = load_expense_data(user_id)
    expenses = user_data.get(str(user_id), {}).get("expenses", [])

    # Фильтруем траты по выбранному транспорту
    expenses = filter_expenses_by_transport(user_id, expenses)

    # Проверяем, существует ли выбранная категория
    if selected_category not in {expense['category'] for expense in expenses}:
        bot.send_message(user_id, "Выбранная категория не найдена. Пожалуйста, выберите корректную категорию.")
        view_expenses_by_category(message)  # Запрашиваем повторный ввод категории
        return

    # Фильтруем траты по выбранной категории
    category_expenses = [expense for expense in expenses if expense['category'] == selected_category]

    total_expenses = 0
    expense_details = []

    for index, expense in enumerate(category_expenses, start=1):
        expense_name = expense.get("name", "Без названия")
        expense_date = expense.get("date", "")
        amount = float(expense.get("amount", 0))
        total_expenses += amount

        expense_details.append(
            f"  №: {index}\n\n"
            f"    КАТЕГОРИЯ: {selected_category}\n"
            f"    НАЗВАНИЕ: {expense_name}\n"
            f"    ДАТА: {expense_date}\n"
            f"    СУММА: {amount} руб.\n"
            f"    ОПИСАНИЕ: {expense.get('description', 'Без описания')}\n"
        )

    if expense_details:
        message_text = f"Траты в категории '{selected_category}':\n\n" + "\n\n".join(expense_details)
    else:
        message_text = f"В категории '{selected_category}' трат не найдено."

    send_message_with_split(user_id, message_text)
    bot.send_message(user_id, f"Итоговая сумма трат в категории '{selected_category}': {total_expenses} руб.")

    # Возвращаем пользователя в меню выбора категорий
    view_expenses_by_category(message)  # Запрашиваем выбор категории заново

# Обработчик трат за месяц
@bot.message_handler(func=lambda message: message.text == "Траты (месяц)")
def view_expenses_by_month(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    markup.add(item_return)

    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для просмотра трат за этот период:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expenses_by_month)

def get_expenses_by_month(message):
    user_id = message.from_user.id
    date = message.text.strip()

    if "." in date:
        parts = date.split(".")
        if len(parts) == 2:
            month, year = parts
            if month.isdigit() and year.isdigit() and 1 <= int(month) <= 12 and len(year) == 4:
                month, year = map(int, parts)
                
                user_data = load_expense_data(user_id)
                expenses = user_data.get(str(user_id), {}).get("expenses", [])

                # Фильтруем траты по выбранному транспорту
                expenses = filter_expenses_by_transport(user_id, expenses)

                total_expenses = 0
                expense_details = []

                for index, expense in enumerate(expenses, start=1):
                    expense_date = expense.get("date", "")
                    expense_date_parts = expense_date.split(".")
                    if len(expense_date_parts) >= 2:
                        expense_month, expense_year = map(int, expense_date_parts[1:3])

                        if expense_month == month and expense_year == year:
                            amount = float(expense.get("amount", 0))
                            total_expenses += amount

                            expense_name = expense.get("name", "Без названия")
                            description = expense.get("description", "")
                            category = expense.get("category", "Без категории")

                            expense_details.append(
                                f"  №: {index}\n\n"
                                f"    КАТЕГОРИЯ: {category}\n"
                                f"    НАЗВАНИЕ: {expense_name}\n"
                                f"    ДАТА: {expense_date}\n"
                                f"    СУММА: {amount} руб.\n"
                                f"    ОПИСАНИЕ: {description}\n"
                            )

                if expense_details:
                    message_text = f"Траты за {date}:\n\n" + "\n\n".join(expense_details)
                else:
                    message_text = f"За {date} трат не найдено."

                send_message_with_split(user_id, message_text)
                bot.send_message(user_id, f"Итоговая сумма трат за {date}: {total_expenses} руб.")
                send_menu1(user_id)  # Возвращаемся в меню после отображения информации
            else:
                bot.send_message(user_id, "Пожалуйста, введите корректный месяц и год в формате ММ.ГГГГ.")
                bot.register_next_step_handler(message, get_expenses_by_month)
                return  # Возврат из функции, чтобы не продолжать выполнение
        else:
            bot.send_message(user_id, "Пожалуйста, введите дату в формате ММ.ГГГГ.")
            bot.register_next_step_handler(message, get_expenses_by_month)
            return  # Возврат из функции, чтобы не продолжать выполнение
    else:
        bot.send_message(user_id, "Пожалуйста, введите дату в формате ММ.ГГГГ.")
        bot.register_next_step_handler(message, get_expenses_by_month)
        return  # Возврат из функции, чтобы не продолжать выполнение

# Обработчик трат за год
@bot.message_handler(func=lambda message: message.text == "Траты (год)")
def view_expenses_by_year(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    markup.add(item_return)

    bot.send_message(user_id, "Введите год в формате (ГГГГ) для просмотра трат за этот год:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expenses_by_year)

def get_expenses_by_year(message):
    user_id = message.from_user.id
    year = message.text.strip()

    if not year.isdigit() or len(year) != 4:
        bot.send_message(user_id, "Пожалуйста, введите год в формате ГГГГ.")
        bot.register_next_step_handler(message, get_expenses_by_year)
        return  # Возврат из функции, чтобы не продолжать выполнение

    year = int(year)
    user_data = load_expense_data(user_id)
    expenses = user_data.get(str(user_id), {}).get("expenses", [])

    # Фильтруем траты по выбранному транспорту
    expenses = filter_expenses_by_transport(user_id, expenses)

    total_expenses = 0
    expense_details = []

    for index, expense in enumerate(expenses, start=1):
        expense_date = expense.get("date", "")
        if "." in expense_date:
            date_parts = expense_date.split(".")
            if len(date_parts) >= 3:
                expense_year = int(date_parts[2])
                if expense_year == year:
                    amount = float(expense.get("amount", 0))
                    total_expenses += amount

                    expense_name = expense.get("name", "Без названия")
                    description = expense.get("description", "")
                    category = expense.get("category", "Без категории")

                    expense_details.append(
                        f"  №: {index}\n\n"
                        f"    КАТЕГОРИЯ: {category}\n"
                        f"    НАЗВАНИЕ: {expense_name}\n"
                        f"    ДАТА: {expense_date}\n"
                        f"    СУММА: {amount} руб.\n"
                        f"    ОПИСАНИЕ: {description}\n"
                    )

    if expense_details:
        message_text = f"Траты за {year} год:\n\n" + "\n\n".join(expense_details)
    else:
        message_text = f"За {year} год трат не найдено."

    send_message_with_split(user_id, message_text)
    bot.send_message(user_id, f"Итоговая сумма трат за {year} год: {total_expenses} руб.")

    # Возвращаемся в меню после отображения информации
    send_menu1(user_id)

# Обработчик всех трат
@bot.message_handler(func=lambda message: message.text == "Траты (всё время)")
def view_all_expenses(message):
    user_id = message.from_user.id

    user_data = load_expense_data(user_id)
    expenses = user_data.get(str(user_id), {}).get("expenses", [])

    # Фильтруем траты по выбранному транспорту
    expenses = filter_expenses_by_transport(user_id, expenses)

    total_expenses = 0
    expense_details = []

    for index, expense in enumerate(expenses, start=1):
        amount = float(expense.get("amount", 0))
        total_expenses += amount

        expense_name = expense.get("name", "Без названия")
        expense_date = expense.get("date", "")
        description = expense.get("description", "")
        category = expense.get("category", "Без категории")

        expense_details.append(
            f"  №: {index}\n\n"
            f"    КАТЕГОРИЯ: {category}\n"
            f"    НАЗВАНИЕ: {expense_name}\n"
            f"    ДАТА: {expense_date}\n"
            f"    СУММА: {amount} руб.\n"
            f"    ОПИСАНИЕ: {description}\n"
        )

    if expense_details:
        message_text = "Все траты:\n\n" + "\n\n".join(expense_details)
    else:
        message_text = "Трат не найдено."

    send_message_with_split(user_id, message_text)
    bot.send_message(user_id, f"Итоговая сумма всех трат: {total_expenses} руб.")

    # Возвращаемся в меню после отображения информации
    send_menu1(user_id)

# (10.18) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "УДАЛИТЬ ТРАТЫ") ---------------

# Глобальный словарь для хранения выбранного транспорта по user_id
selected_transports = {}

def save_selected_transport(user_id, selected_transport):
    user_data = load_expense_data(user_id).get(str(user_id), {})
    user_data["selected_transport"] = selected_transport
    save_expense_data(user_id, {str(user_id): user_data})
    print(f"Транспорт сохранён: {user_data['selected_transport']}")  # Для отладки

@bot.message_handler(func=lambda message: message.text == "Удалить траты")
def delete_expenses_menu(message):
    user_id = message.from_user.id

    transport_data = load_transport_data(user_id)
    if not transport_data:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_add_transport = types.KeyboardButton("Добавить транспорт")
        item_cancel = types.KeyboardButton("Отмена")
        markup.add(item_add_transport, item_cancel)
        bot.send_message(user_id, "У вас нет зарегистрированного транспорта. Хотите добавить транспорт?", reply_markup=markup)
        bot.register_next_step_handler(message, add_transport)
        return

    # Отображение транспорта для удаления
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for transport in transport_data:
        brand = transport.get("brand", "Без названия")
        model = transport.get("model", "Без названия")
        year = transport.get("year", "Неизвестно")
        button_label = f"{brand} {model} {year}"
        markup.add(types.KeyboardButton(button_label))

    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return, item_main_menu)
    bot.send_message(user_id, "Выберите транспорт для удаления трат:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection_for_deletion)

def handle_transport_selection_for_deletion(message):
    user_id = message.from_user.id
    selected_transport = message.text.strip()
    
    # Сохраняем выбранный транспорт в глобальном словаре
    selected_transports[user_id] = selected_transport
    save_selected_transport(user_id, selected_transport)  # Сохраняем в БД
    print(f"Сохранён транспорт для удаления: {selected_transports[user_id]}")  # Для отладки

    if selected_transport == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if selected_transport == "В главное меню":
        return_to_menu(message)
        return

    # Запрос на удаление трат
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_month = types.KeyboardButton("Del траты (месяц)")
    item_year = types.KeyboardButton("Del траты (год)")
    item_all_time = types.KeyboardButton("Del траты (всё время)")
    item_del_category_exp = types.KeyboardButton("Del траты (категория)")
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    
    markup.add(item_month, item_year, item_all_time, item_del_category_exp)
    markup.add(item_return, item_main_menu)
    bot.send_message(user_id, "Выберите вариант удаления трат:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Del траты (категория)")
def delete_expenses_by_category(message):
    user_id = message.from_user.id
    selected_transport = selected_transports.get(user_id)  # Получаем транспорт из глобального словаря

    print(f"Загружен транспорт: {selected_transport}")  # Для отладки

    if selected_transport is None:
        bot.send_message(user_id, "Не выбран транспорт. Вернитесь в меню.")
        send_menu(user_id)
        return

    # Получаем марку, модель и год из выбранного транспорта
    transport_info = selected_transport.split(" ")
    if len(transport_info) < 3:
        bot.send_message(user_id, "Ошибка с данными транспорта. Попробуйте снова.")
        send_menu(user_id)
        return

    selected_brand = transport_info[0]  # Марка
    selected_model = transport_info[1]  # Модель
    selected_year = transport_info[2]    # Год

    expenses = load_expense_data(user_id).get(str(user_id), {}).get("expenses", [])
    
    # Фильтруем траты по выбранному транспорту
    categories = list(set(expense.get("category") for expense in expenses 
                          if (expense.get("transport", {}).get("brand") == selected_brand and
                              expense.get("transport", {}).get("model") == selected_model and
                              str(expense.get("transport", {}).get("year")) == selected_year)))

    print(f"Найденные категории для удаления: {categories}")  # Для отладки

    if not categories:
        bot.send_message(user_id, "У вас нет категорий для удаления трат по выбранному транспорту.")
        send_menu(user_id)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for category in categories:
        markup.add(types.KeyboardButton(category))

    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return, item_main_menu)
    
    bot.send_message(user_id, "Выберите категорию для удаления:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_category_selection)

def handle_category_selection(message):
    user_id = message.from_user.id
    selected_category = message.text.strip()

    if selected_category == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    user_data = load_expense_data(user_id).get(str(user_id), {})
    expenses = user_data.get("expenses", [])

    # Получаем выбранный транспорт
    selected_transport = selected_transports.get(user_id)
    if selected_transport is None:
        bot.send_message(user_id, "Не выбран транспорт. Вернитесь в меню.")
        send_menu(user_id)
        return

    transport_info = selected_transport.split(" ")
    if len(transport_info) < 3:
        bot.send_message(user_id, "Ошибка с данными транспорта. Попробуйте снова.")
        send_menu(user_id)
        return

    selected_brand = transport_info[0]
    selected_model = transport_info[1]
    selected_year = transport_info[2]

    expenses_to_delete = [expense for expense in expenses if 
                          expense.get("category") == selected_category and
                          expense.get("transport", {}).get("brand") == selected_brand and
                          expense.get("transport", {}).get("model") == selected_model and
                          str(expense.get("transport", {}).get("year")) == selected_year]

    print(f"Найдены траты для удаления: {expenses_to_delete}")  # Для отладки

    if not expenses_to_delete:
        bot.send_message(user_id, f"Нет трат для удаления в категории '{selected_category}' по выбранному транспорту.")
        send_menu(user_id)
        return

    # Отображение трат для удаления в более удобном формате
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    keyboard.add(types.KeyboardButton("В главное меню"))
    
    for index, expense in enumerate(expenses_to_delete, start=1):
        expense_name = expense.get("name", "Без названия")
        keyboard.add(types.KeyboardButton(f"Удалить трату #{index} - {expense_name}"))

    bot.send_message(user_id, f"Выберите трату для удаления из категории '{selected_category}':", reply_markup=keyboard)
    bot.register_next_step_handler(message, confirm_delete_expense_by_category, expenses_to_delete)

def confirm_delete_expense_by_category(message, expenses_to_delete):
    user_id = message.from_user.id
    selected_option = message.text.strip()

    user_data = load_expense_data(user_id).get(str(user_id), {})
    selected_transport = selected_transports.get(user_id)

    if selected_transport is None:
        bot.send_message(user_id, "Не выбран транспорт. Вернитесь в меню.")
        send_menu(user_id)
        return

    # Получаем марку, модель и год из выбранного транспорта
    transport_info = selected_transport.split(" ")
    selected_brand = transport_info[0]  # Марка
    selected_model = transport_info[1]  # Модель
    selected_year = transport_info[2]    # Год

    if selected_option.startswith("Удалить трату #"):
        try:
            expense_index = int(selected_option.split("#")[1].split(" - ")[0]) - 1
            expenses = user_data.get("expenses", [])

            if 0 <= expense_index < len(expenses_to_delete):
                deleted_expense = expenses_to_delete[expense_index]
                expenses.remove(deleted_expense)
                user_data["expenses"] = expenses
                
                # Передаем selected_transport при вызове функции
                save_expense_data(user_id, {str(user_id): user_data}, selected_transport)
                
                update_excel_file(user_id)

                bot.send_message(user_id, f"Трата '{deleted_expense.get('name', 'Без названия')}' успешно удалена.")
            else:
                bot.send_message(user_id, "Неверный выбор. Попробуйте снова.")
                send_menu(user_id)
                return
        except (IndexError, ValueError):
            bot.send_message(user_id, "Ошибка при удалении. Попробуйте снова.")
            send_menu(user_id)
            return

    # Обработка возврата
    if selected_option == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if selected_option == "В главное меню":
        return_to_menu(message)
        return

    send_menu(user_id)

# Удаление трат за месяц
# Удаление трат за месяц

@bot.message_handler(func=lambda message: message.text == "Del траты (месяц)")
def delete_expense_by_month(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return, item_main_menu)
    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для удаления трат за этот месяц:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_expenses_by_month)

def delete_expenses_by_month(message):
    user_id = message.from_user.id
    month_year = message.text.strip()

    print(f"[DEBUG] Ввод месяца и года для удаления: {month_year}")

    # Проверка формата ввода
    if len(month_year) != 7 or month_year[2] != '.' or month_year[:2] not in valid_months:
        bot.send_message(user_id, "Введен неверный месяц. Пожалуйста, введите корректный месяц (ММ.ГГГГ).")
        bot.register_next_step_handler(message, delete_expenses_by_month)
        return

    user_data = load_expense_data(user_id).get(str(user_id), {})
    expenses = user_data.get("expenses", [])

    print(f"[DEBUG] Загруженные расходы: {expenses}")

    # Получаем выбранный транспорт из глобальной переменной
    selected_transport = selected_transports.get(user_id, None)

    if selected_transport:
        transport_info = selected_transport.split(" ")
        selected_brand = transport_info[0].strip()  # Первая часть - марка
        selected_model = transport_info[1].strip()  # Вторая часть - модель
        selected_year = str(transport_info[2].strip())  # Преобразуем год в строку
        print(f"[DEBUG] Выбранный транспорт: {selected_brand} {selected_model} {selected_year}")
    else:
        selected_brand = selected_model = selected_year = None
        print("[DEBUG] Выбранный транспорт не найден.")

    if not expenses:
        bot.send_message(user_id, f"У вас пока нет сохраненных трат за {month_year} для удаления.")
        send_menu(user_id)
        return

    expenses_to_delete = []
    for index, expense in enumerate(expenses, start=1):
        expense_date = expense.get("date", "")
        expense_month_year = expense_date.split(".")[1] + "." + expense_date.split(".")[2]

        # Получаем данные о транспорте из расходов
        expense_brand = expense.get("transport", {}).get("brand", "").strip()
        expense_model = expense.get("transport", {}).get("model", "").strip()
        expense_year = str(expense.get("transport", {}).get("year", "")).strip()  # Преобразуем год в строку

        print(f"[DEBUG] Проверка трат: {expense_month_year}, {month_year}, Транспорт: {expense_brand}, {expense_model}, Год: {expense_year}")

        # Проверяем, совпадает ли месяц, год и выбранный транспорт
        if (expense_month_year == month_year and
           expense_brand == selected_brand and
           expense_model == selected_model and
           expense_year == selected_year):
            expenses_to_delete.append((index, expense))

    print(f"[DEBUG] Найденные расходы для удаления: {expenses_to_delete}")

    if expenses_to_delete:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        keyboard.add(types.KeyboardButton("В главное меню"))
        for index, expense in expenses_to_delete:
            expense_name = expense.get("name", "Без названия")
            keyboard.add(types.KeyboardButton(f"Удалить трату #{index} - {expense_name}"))

        bot.send_message(user_id, "Выберите трату для удаления:", reply_markup=keyboard)
        bot.register_next_step_handler(message, confirm_delete_expense_month, expenses_to_delete)
    else:
        bot.send_message(user_id, f"За {month_year} месяц трат не найдено для удаления.")
        send_menu(user_id)

def confirm_delete_expense_month(message, expenses_to_delete):
    user_id = message.from_user.id
    selected_option = message.text

    print(f"[DEBUG] Выбор пользователя для удаления: {selected_option}")

    if selected_option.startswith("Удалить трату #"):
        try:
            expense_index = int(selected_option.split("#")[1].split(" - ")[0]) - 1
            user_data = load_expense_data(user_id).get(str(user_id), {})
            expenses = user_data.get("expenses", [])

            print(f"[DEBUG] Индекс удаления: {expense_index}")

            if 0 <= expense_index < len(expenses):
                deleted_expense = expenses.pop(expense_index)
                user_data["expenses"] = expenses 

                # Сохраняем данные, передавая выбранный транспорт
                selected_transport = selected_transports.get(user_id)
                save_expense_data(user_id, {str(user_id): user_data}, selected_transport) 

                update_excel_file(user_id)

                bot.send_message(user_id, f"Трата '{deleted_expense.get('name', 'Без названия')}' удалена успешно.")
            else:
                bot.send_message(user_id, "Недопустимый выбор. Пожалуйста, выберите трату из списка.")
        except ValueError:
            bot.send_message(user_id, "Ошибка при обработке выбора. Пожалуйста, выберите трату из списка.")
    else:
        bot.send_message(user_id, "Недопустимый выбор. Пожалуйста, выберите трату из списка.")

    send_menu(user_id)

# Удаление трат за год
@bot.message_handler(func=lambda message: message.text == "Del траты (год)")
def delete_expense_by_year(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return, item_main_menu)
    bot.send_message(user_id, "Введите год (ГГГГ) для удаления трат за этот год:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_expenses_by_year)

def delete_expenses_by_year(message):
    user_id = message.from_user.id
    year = message.text.strip()

    print(f"[DEBUG] Ввод года для удаления: {year}")

    user_data = load_expense_data(user_id).get(str(user_id), {})
    expenses = user_data.get("expenses", [])

    print(f"[DEBUG] Загруженные расходы: {expenses}")

    # Получаем выбранный транспорт из глобальной переменной
    selected_transport = selected_transports.get(user_id, None)

    if selected_transport:
        transport_info = selected_transport.split(" ")
        selected_brand = transport_info[0].strip()  # Первая часть - марка
        selected_model = transport_info[1].strip()  # Вторая часть - модель
        selected_year = str(transport_info[2].strip())  # Преобразуем год в строку
        print(f"[DEBUG] Выбранный транспорт: {selected_brand} {selected_model} {selected_year}")
    else:
        selected_brand = selected_model = selected_year = None
        print("[DEBUG] Выбранный транспорт не найден.")

    if not expenses:
        bot.send_message(user_id, f"У вас пока нет сохраненных трат за {year} для удаления.")
        send_menu(user_id)
        return

    expenses_to_delete = []
    for index, expense in enumerate(expenses, start=1):
        expense_date = expense.get("date", "")
        expense_year = expense_date.split(".")[2]  # Извлекаем год из даты

        # Получаем данные о транспорте из расходов
        expense_brand = expense.get("transport", {}).get("brand", "").strip()
        expense_model = expense.get("transport", {}).get("model", "").strip()

        print(f"[DEBUG] Проверка трат: Год: {expense_year}, Выбранный год: {year}")

        # Проверяем, совпадает ли год и выбранный транспорт
        if (expense_year == year and
           expense_brand == selected_brand and
           expense_model == selected_model):
            expenses_to_delete.append((index, expense))

    print(f"[DEBUG] Найденные расходы для удаления: {expenses_to_delete}")

    if expenses_to_delete:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        keyboard.add(types.KeyboardButton("В главное меню"))
        for index, expense in expenses_to_delete:
            expense_name = expense.get("name", "Без названия")
            keyboard.add(types.KeyboardButton(f"Удалить трату #{index} - {expense_name}"))

        bot.send_message(user_id, "Выберите трату для удаления:", reply_markup=keyboard)
        bot.register_next_step_handler(message, confirm_delete_expense_year, expenses_to_delete)
    else:
        bot.send_message(user_id, f"За {year} год трат не найдено для удаления.")
        send_menu(user_id)

def confirm_delete_expense_year(message, expenses_to_delete):
    user_id = message.from_user.id
    selected_option = message.text

    print(f"[DEBUG] Выбор пользователя для удаления: {selected_option}")

    if selected_option.startswith("Удалить трату #"):
        try:
            expense_index = int(selected_option.split("#")[1].split(" - ")[0]) - 1
            user_data = load_expense_data(user_id).get(str(user_id), {})
            expenses = user_data.get("expenses", [])

            print(f"[DEBUG] Индекс удаления: {expense_index}")

            if 0 <= expense_index < len(expenses):
                deleted_expense = expenses.pop(expense_index)
                user_data["expenses"] = expenses 

                # Сохраняем данные, передавая выбранный транспорт
                selected_transport = selected_transports.get(user_id)
                save_expense_data(user_id, {str(user_id): user_data}, selected_transport) 

                update_excel_file(user_id)

                bot.send_message(user_id, f"Трата '{deleted_expense.get('name', 'Без названия')}' удалена успешно.")
            else:
                bot.send_message(user_id, "Недопустимый выбор. Пожалуйста, выберите трату из списка.")
        except ValueError:
            bot.send_message(user_id, "Ошибка при обработке выбора. Пожалуйста, выберите трату из списка.")
    else:
        bot.send_message(user_id, "Недопустимый выбор. Пожалуйста, выберите трату из списка.")

    send_menu(user_id)


# Удаление всех трат
# Удаление всех трат
@bot.message_handler(func=lambda message: message.text == "Del траты (всё время)")
def delete_all_expenses_for_selected_transport(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return, item_main_menu)
    
    # Запрашиваем подтверждение
    bot.send_message(user_id, "Вы уверены, что хотите удалить все траты для выбранного транспорта? (да/нет)", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_delete_all_expenses)

def confirm_delete_all_expenses(message):
    user_id = message.from_user.id

    # Обработка возвратов в меню
    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    response = message.text.lower()

    # Получаем данные пользователя
    user_data = load_expense_data(user_id).get(str(user_id), {})
    expenses = user_data.get("expenses", [])

    # Получаем выбранный транспорт
    selected_transport = selected_transports.get(user_id, None)

    if selected_transport:
        transport_info = selected_transport.split(" ")
        selected_brand = transport_info[0].strip()
        selected_model = transport_info[1].strip()
        selected_year = transport_info[2].strip()
    else:
        selected_brand = selected_model = selected_year = None

    if response == "да":
        if not expenses:
            bot.send_message(user_id, "У вас пока нет сохраненных трат для удаления.")
            send_menu(user_id)
            return

        expenses_to_keep = []
        for expense in expenses:
            expense_brand = expense.get("transport", {}).get("brand", "").strip()
            expense_model = expense.get("transport", {}).get("model", "").strip()

            # Сравниваем с выбранным транспортом
            if not (expense_brand == selected_brand and expense_model == selected_model):
                expenses_to_keep.append(expense)

        # Обновляем список расходов пользователя
        user_data["expenses"] = expenses_to_keep
        save_expense_data(user_id, {str(user_id): user_data}, selected_transport)

        update_excel_file(user_id)

        # Сообщение об успешном удалении
        bot.send_message(user_id, f"Все траты для транспорта '{selected_brand} {selected_model} {selected_year}' успешно удалены.")
    else:
        bot.send_message(user_id, "Удаление трат отменено.")

    send_menu(user_id)


import os
import pandas as pd
import openpyxl

def delete_expense(user_id, deleted_expense):
    # Удаляем трату из базы данных
    user_data = load_expense_data(user_id).get(str(user_id), {})
    expenses = user_data.get("expenses", [])

    # Удаляем трату из списка расходов
    expenses = [expense for expense in expenses if not (
        expense["transport"]["brand"] == deleted_expense["transport"]["brand"] and
        expense["transport"]["model"] == deleted_expense["transport"]["model"] and
        expense["transport"]["year"] == deleted_expense["transport"]["year"] and
        expense["category"] == deleted_expense["category"] and
        expense["name"] == deleted_expense["name"] and
        expense["date"] == deleted_expense["date"] and
        expense["amount"] == deleted_expense["amount"] and
        expense["description"] == deleted_expense["description"]
    )]

    # Обновляем данные пользователя
    user_data["expenses"] = expenses
    save_expense_data(user_id, user_data)

    # Обновляем Excel файл
    update_excel_file(user_id)

def update_excel_file(user_id):
    user_data = load_expense_data(user_id).get(str(user_id), {})
    expenses = user_data.get("expenses", [])

    # Путь к Excel файлу пользователя
    excel_file_path = f"data base/expense/excel/{user_id}_expenses.xlsx"

    # Проверяем, существует ли файл
    if not os.path.exists(excel_file_path):
        workbook = openpyxl.Workbook()
        workbook.remove(workbook.active)
        workbook.save(excel_file_path)

    # Открываем существующий файл
    workbook = load_workbook(excel_file_path)

    # Обновление общего листа (Summary)
    summary_sheet = workbook["Summary"] if "Summary" in workbook.sheetnames else workbook.create_sheet("Summary")
    headers = ["Транспорт", "Категория", "Название", "Дата", "Сумма", "Описание"]

    # Очистка всех данных на листе Summary (кроме заголовков)
    if summary_sheet.max_row > 1:
        summary_sheet.delete_rows(2, summary_sheet.max_row)

    # Добавляем заголовки, если они еще не добавлены
    if summary_sheet.max_row == 0:  # Если лист пустой
        summary_sheet.append(headers)
        for cell in summary_sheet[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")

    # Заполняем общий лист новыми данными
    for expense in expenses:
        transport = expense["transport"]
        row_data = [
            f"{transport['brand']} {transport['model']} {transport['year']}",
            expense["category"],
            expense["name"],
            expense["date"],
            expense["amount"],
            expense["description"],
        ]
        summary_sheet.append(row_data)

    # Обновление индивидуальных листов для каждого транспорта
    unique_transports = set((exp["transport"]["brand"], exp["transport"]["model"], exp["transport"]["year"]) for exp in expenses)

    # Удаляем старые листы для уникальных транспортов
    for sheet_name in workbook.sheetnames:
        if sheet_name != "Summary" and (sheet_name.split('_')[0], sheet_name.split('_')[1], sheet_name.split('_')[2]) not in unique_transports:
            del workbook[sheet_name]

    for brand, model, year in unique_transports:
        sheet_name = f"{brand}_{model}_{year}"
        if sheet_name not in workbook.sheetnames:
            transport_sheet = workbook.create_sheet(sheet_name)
            transport_sheet.append(headers)
            for cell in transport_sheet[1]:
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal="center")
        else:
            transport_sheet = workbook[sheet_name]
            # Очистка всех данных на листе транспорта, кроме заголовков
            if transport_sheet.max_row > 1:
                transport_sheet.delete_rows(2, transport_sheet.max_row)

        # Заполняем траты для этого транспорта
        for expense in expenses:
            if (expense["transport"]["brand"], expense["transport"]["model"], expense["transport"]["year"]) == (brand, model, year):
                row_data = [
                    f"{brand} {model} {year}",
                    expense["category"],
                    expense["name"],
                    expense["date"],
                    expense["amount"],
                    expense["description"],
                ]
                transport_sheet.append(row_data)

    # Автоподгонка столбцов
    for sheet in workbook.sheetnames:
        current_sheet = workbook[sheet]
        for col in current_sheet.columns:
            max_length = max(len(str(cell.value)) for cell in col)
            current_sheet.column_dimensions[get_column_letter(col[0].column)].width = max_length + 2

    # Сохраняем изменения
    workbook.save(excel_file_path)
    workbook.close()


# (11) --------------- КОД ДЛЯ "РЕМОНТОВ" ---------------

# (11.1) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "ЗАПИСАТЬ РЕМОНТ") ---------------
# Системные категории ремонта
system_categories = [
    "Без категории", "ТО", "Ремонт", "Запчасть",
    "Диагностика", "Электрика", "Кузов"
]

user_transport = {}  # Это должно быть вашим хранилищем данных о транспорте

# Обработка данных о ремонтах
def save_repair_data(user_id, user_data):
    # Задаем новый путь к папке и файлу
    folder_path = os.path.join("data base", "repairs")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Измененное имя файла: "user_id_repairs.json"
    file_path = os.path.join(folder_path, f"{user_id}_repairs.json")

    # Загружаем текущие данные пользователя, чтобы сохранить user_categories
    current_data = load_repair_data(user_id)

    # Сохраняем только изменения, не перезаписывая user_categories
    if "user_categories" in current_data:
        user_data["user_categories"] = current_data["user_categories"]

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(user_data, file, ensure_ascii=False, indent=4)

def load_repair_data(user_id):
    # Путь к файлу в новой папке
    folder_path = os.path.join("data base", "repairs")
    file_path = os.path.join(folder_path, f"{user_id}_repairs.json")
    
    # Проверка, существует ли файл, перед его открытием
    if not os.path.exists(file_path):
        return {"user_categories": []}  # Если файла нет, возвращаем пустой словарь с пустым списком категорий

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            if not isinstance(data, dict):
                raise ValueError("Данные не являются словарем.")
    except (FileNotFoundError, ValueError) as e:
        print("Ошибка загрузки данных:", e)
        data = {"user_categories": []}  # Обеспечиваем наличие пустого списка категорий
    return data

@bot.message_handler(func=lambda message: message.text == "Записать ремонт")
def record_repair(message):
    user_id = message.from_user.id
    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, record_repair)
        return

    markup = get_user_transport_keyboard(user_id)
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Выберите транспорт для записи ремонта:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection_for_repair)

def get_user_transport_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    user_transports = user_transport.get(str(user_id), [])
    
    for transport in user_transports:
        transport_name = f"{transport['brand']} {transport['model']} {transport['year']}"
        markup.add(types.KeyboardButton(transport_name))
    
    markup.add(types.KeyboardButton("Добавить транспорт"))
    return markup

def handle_transport_selection_for_repair(message):
    user_id = message.from_user.id

    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return
    elif message.text == "В главное меню":
        return_to_menu(message)
        return

    selected_transport = message.text
    for transport in user_transport.get(str(user_id), []):
        if f"{transport['brand']} {transport['model']} {transport['year']}" == selected_transport:
            brand, model, year = transport['brand'], transport['model'], transport['year']
            break
    else:
        bot.send_message(user_id, "Не удалось найти указанный транспорт. Пожалуйста, выберите снова.")
        bot.send_message(user_id, "Выберите транспорт или добавьте новый:", reply_markup=get_user_transport_keyboard(user_id))
        return

    process_category_selection_repair(user_id, brand, model, year)

def process_category_selection_repair(user_id, brand, model, year):
    categories = get_user_repair_categories(user_id)

    # Убедитесь, что вы получаете уникальные категории
    category_list = "\n".join(f"{i + 1}. {category}" for i, category in enumerate(categories))
    category_list = f"*Выберите категорию или '0' для отмены:*\n\n{category_list}"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        types.KeyboardButton("Добавить категорию"),
        types.KeyboardButton("Удалить категорию")
    )
    markup.add(
        types.KeyboardButton("Вернуться в меню трат и ремонтов")
    )
    markup.add(
        types.KeyboardButton("В главное меню")
    )

    prompt_message = bot.send_message(user_id, category_list, reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(prompt_message, get_repair_category, brand, model, year)

def get_repair_category(message, brand, model, year):
    user_id = message.from_user.id
    selected_index = message.text.strip()

    if selected_index == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return
    elif selected_index == "В главное меню":
        return_to_menu(message)
        return

    # Проверка на ввод "0" для отмены
    if selected_index == '0':
        return_to_menu_2(message)  # Возвращаем в меню трат и ремонтов
        return

    if selected_index == 'Добавить категорию':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            types.KeyboardButton("Вернуться в меню трат и ремонтов")
        )
        markup.add(
            types.KeyboardButton("В главное меню")
        )
        bot.send_message(user_id, "Введите название новой категории:", reply_markup=markup)
        bot.register_next_step_handler(message, add_new_repair_category, brand, model, year)
        return

    if selected_index == 'Удалить категорию':
        handle_repair_category_removal(message, brand, model, year)
        return

    if selected_index.isdigit():
        index = int(selected_index) - 1
        all_categories = get_user_repair_categories(user_id)
        if 0 <= index < len(all_categories):
            selected_category = all_categories[index]
            proceed_to_repair_name(message, selected_category, brand, model, year)
        else:
            bot.send_message(user_id, "Неверный ввод категории. Попробуйте еще раз.")
            bot.register_next_step_handler(message, get_repair_category, brand, model, year)
    else:
        bot.send_message(user_id, "Пожалуйста, введите номер категории.")
        bot.register_next_step_handler(message, get_repair_category, brand, model, year)

def proceed_to_repair_name(message, selected_category, brand, model, year):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите название ремонта:", reply_markup=markup)
    bot.register_next_step_handler(message, get_repair_name, selected_category, brand, model, year)

def get_repair_name(message, selected_category, brand, model, year):
    user_id = message.from_user.id

    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_menu_2(message)
        else:
            return_to_menu(message)
        return

    repair_name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_skip = types.KeyboardButton("Пропустить описание")  # Исправлено на "Пропустить описание"
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_skip)
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите описание ремонта или пропустите этот шаг:", reply_markup=markup)
    bot.register_next_step_handler(message, get_repair_description, selected_category, repair_name, brand, model, year)

def get_repair_description(message, selected_category, repair_name, brand, model, year):
    user_id = message.from_user.id

    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_menu_2(message)
        else:
            return_to_menu(message)
        return

    repair_description = message.text if message.text != "Пропустить описание" else ""
    
    # Ввод даты
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите дату ремонта (в формате ДД.ММ.ГГГГ):", reply_markup=markup)
    bot.register_next_step_handler(message, get_repair_date, selected_category, repair_name, repair_description, brand, model, year)

def is_valid_date(date_str):
    # Проверяем формат даты: ДД.ММ.ГГГГ
    pattern = r'^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.(2000|20[01][0-9]|202[0-9]|203[0-9]|[2-9][0-9]{3})$'
    return bool(re.match(pattern, date_str))

def get_repair_date(message, selected_category, repair_name, repair_description, brand, model, year):
    user_id = message.from_user.id

    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_menu_2(message)
        else:
            return_to_menu(message)
        return

    repair_date = message.text

    # Проверка формата даты
    if not is_valid_date(repair_date):
        bot.send_message(user_id, "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")
        bot.register_next_step_handler(message, get_repair_date, selected_category, repair_name, repair_description, brand, model, year)
        return

    # Ввод суммы
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите сумму ремонта:", reply_markup=markup)
    bot.register_next_step_handler(message, save_repair_data_final, selected_category, repair_name, repair_description, repair_date, brand, model, year)

def save_repair_data_final(message, selected_category, repair_name, repair_description, repair_date, brand, model, year):
    user_id = message.from_user.id

    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_menu_2(message)
        else:
            return_to_menu(message)
        return

    try:
        repair_amount = float(message.text)
        repair_data = {
            "category": selected_category,
            "name": repair_name,
            "date": repair_date,
            "amount": repair_amount,
            "description": repair_description,
            "transport": {
                "brand": brand,
                "model": model,
                "year": year
            }
        }

        save_repair_data(user_id, repair_data)
        
        # Сохраняем данные ремонта в Excel
        save_repair_to_excel(user_id, repair_data)

        bot.send_message(user_id, "Ремонт успешно записан.")
        send_menu(user_id)

    except ValueError:
        bot.send_message(user_id, "Пожалуйста, введите корректную сумму.")
        bot.register_next_step_handler(message, save_repair_data_final, selected_category, repair_name, repair_description, repair_date, brand, model, year)


def save_repair_to_excel(user_id, repair_data):
    # Путь к Excel-файлу пользователя для ремонтов
    excel_path = os.path.join("data base", "repairs", "excel", f"{user_id}_repairs.xlsx")

    # Проверяем, существует ли директория
    directory = os.path.dirname(excel_path)
    if not os.path.exists(directory):
        os.makedirs(directory)  # Создаем директорию, если она не существует

    # Загружаем или создаём рабочую книгу
    try:
        if os.path.exists(excel_path):
            workbook = load_workbook(excel_path)
        else:
            workbook = Workbook()
            workbook.remove(workbook.active)  # Удаляем стандартный лист
        
        # Лист для всех ремонтов (Summary)
        summary_sheet = workbook["Summary"] if "Summary" in workbook.sheetnames else workbook.create_sheet("Summary")
        
        # Лист для конкретного транспортного средства
        transport_sheet_name = f"{repair_data['transport']['brand']}_{repair_data['transport']['model']}_{repair_data['transport']['year']}"
        if transport_sheet_name not in workbook.sheetnames:
            transport_sheet = workbook.create_sheet(transport_sheet_name)
        else:
            transport_sheet = workbook[transport_sheet_name]
        
        # Определяем заголовки
        headers = ["Транспорт", "Категория", "Название", "Дата", "Сумма", "Описание"]
        
        # Вспомогательная функция для настройки листов
        def setup_sheet(sheet):
            if sheet.max_row == 1:
                sheet.append(headers)
                for cell in sheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal="center")

        # Добавляем заголовки и данные
        for sheet in [summary_sheet, transport_sheet]:
            setup_sheet(sheet)
            row_data = [
                f"{repair_data['transport']['brand']} {repair_data['transport']['model']} {repair_data['transport']['year']}",
                repair_data["category"],
                repair_data["name"],
                repair_data["date"],
                repair_data["amount"],
                repair_data["description"],
            ]
            sheet.append(row_data)
        
        # Автоподгонка столбцов
        for sheet in [summary_sheet, transport_sheet]:
            for col in sheet.columns:
                max_length = max(len(str(cell.value)) for cell in col)
                sheet.column_dimensions[get_column_letter(col[0].column)].width = max_length + 2

        # Сохраняем рабочую книгу
        workbook.save(excel_path)
    except Exception as e:
        print(f"Ошибка при сохранении данных ремонта в Excel: {e}")

def add_new_repair_category(message, brand, model, year):
    user_id = message.from_user.id
    new_category = message.text.strip()

    if new_category in system_categories:
        bot.send_message(user_id, "Эта категория уже существует в системе.")
        process_category_selection_repair(user_id, brand, model, year)
        return

    # Сохранение новой категории
    data = load_repair_data(user_id)
    if new_category not in data["user_categories"]:
        data["user_categories"].append(new_category)
        # Сохраняем изменения в файл
        with open(os.path.join("data base", "repairs", f"{user_id}_repairs.json"), "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

        bot.send_message(user_id, f"Категория '{new_category}' успешно добавлена.")
    else:
        bot.send_message(user_id, "Эта категория уже существует.")

    process_category_selection_repair(user_id, brand, model, year)

def handle_repair_category_removal(message, brand, model, year):
    user_id = message.from_user.id
    categories = get_user_repair_categories(user_id)

    if not categories:
        bot.send_message(user_id, "Нет доступных категорий для удаления.")
        process_category_selection_repair(user_id, brand, model, year)
        return

    # Создание текста с жирным шрифтом для сообщения
    category_list = "\n".join(f"{i + 1}. {category}" for i, category in enumerate(categories))
    bot.send_message(user_id, f"Выберите категорию для удаления или '0' для отмены:\n\n{category_list}")

    # Создание кнопок
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")
    bot.send_message(user_id, "Выберите действие:", reply_markup=markup)

    bot.register_next_step_handler(message, remove_repair_category, categories, brand, model, year)

def remove_repair_category(message, categories, brand, model, year):
    user_id = message.from_user.id

    # Проверка на нажатие кнопки '0' для отмены
    if message.text == "0":
        # Возвращаемся к выбору категории для записи
        process_category_selection_repair(user_id, brand, model, year)
        return

    # Проверка на нажатие кнопок
    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return
    elif message.text == "В главное меню":
        return_to_menu(message)
        return

    try:
        index = int(message.text) - 1
        if 0 <= index < len(categories):
            removed_category = categories[index]

            # Проверка, является ли категория системной
            if removed_category in system_categories:
                bot.send_message(user_id, "Это системная категория, удаление невозможно. Попробуйте еще раз.")
                # Ждем повторного ввода
                bot.register_next_step_handler(message, remove_repair_category, categories, brand, model, year)
                return

            # Удаление категории
            data = load_repair_data(user_id)
            data["user_categories"].remove(removed_category)

            # Сохраняем изменения в файл
            with open(os.path.join("data base", "repairs", f"{user_id}_repairs.json"), "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)

            bot.send_message(user_id, f"Категория '{removed_category}' успешно удалена.")
            # После успешного удаления, можно вернуть пользователя обратно к выбору категории
            process_category_selection_repair(user_id, brand, model, year)

        else:
            bot.send_message(user_id, "Неверный номер категории. Попробуйте снова.")
            # Ждем повторного ввода
            bot.register_next_step_handler(message, remove_repair_category, categories, brand, model, year)

    except (ValueError, IndexError):
        bot.send_message(user_id, "Пожалуйста, введите корректный номер категории.")
        # Ждем повторного ввода
        bot.register_next_step_handler(message, remove_repair_category, categories, brand, model, year)

def get_user_repair_categories(user_id):
    data = load_repair_data(user_id)
    # Сначала системные категории, потом пользовательские
    return system_categories + data["user_categories"]

        
# (11.5) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "ПОСМОТРЕТЬ РЕМОНТЫ") ---------------

# Функция для фильтрации ремонтов по транспорту
def filter_repairs_by_transport(user_id, repairs):
    selected_transport = selected_transport_dict.get(user_id)
    if not selected_transport:
        return repairs

    # Фильтруем по транспорту
    filtered_repairs = [repair for repair in repairs if f"{repair['transport']['brand']} {repair['transport']['model']} ({repair['transport']['year']})" == selected_transport]
    return filtered_repairs

# Функция для отправки меню для ремонта
def send_repair_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Ремонты (месяц)")
    item2 = types.KeyboardButton("Ремонты (год)")
    item3 = types.KeyboardButton("Ремонты (всё время)")
    item4 = types.KeyboardButton("Ремонты (по категориям)")
    item5 = types.KeyboardButton("Посмотреть ремонты в EXCEL")
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item1, item2, item3, item4, item5)
    markup.add(item_return, item_main_menu)

    bot.send_message(user_id, "Выберите вариант просмотра ремонтов:", reply_markup=markup)

# Обработчик для просмотра ремонтов
@bot.message_handler(func=lambda message: message.text == "Посмотреть ремонты")
def view_repairs(message):
    user_id = message.from_user.id

    # Загружаем данные о транспорте
    transport_list = load_transport_data(user_id)

    if not transport_list:
        bot.send_message(user_id, "У вас нет сохраненного транспорта. Хотите добавить транспорт?", reply_markup=create_transport_options_markup())
        bot.register_next_step_handler(message, ask_add_transport)
        return

    # Если транспорт есть, продолжаем с выбором
    transport_buttons = [types.KeyboardButton(f"{t['brand']} {t['model']} ({t['year']})") for t in transport_list]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*transport_buttons)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    markup.add(item_return)

    bot.send_message(user_id, "Выберите ваш транспорт для просмотра ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection_for_repairs)

# Обработчик выбора транспорта для ремонта
def handle_transport_selection_for_repairs(message):
    user_id = message.from_user.id
    selected_transport = message.text

    if selected_transport == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    # Сохраняем выбранный транспорт для пользователя
    selected_transport_dict[user_id] = selected_transport

    # Теперь можем показывать доступные фильтры для ремонта
    bot.send_message(user_id, f"Показываю ремонты для транспорта: {selected_transport}")
    send_repair_menu(user_id)

@bot.message_handler(func=lambda message: message.text == "Посмотреть ремонты в EXCEL")
def send_repairs_excel(message):
    user_id = message.from_user.id

    # Путь к Excel файлу для ремонтов
    excel_path = os.path.join("data base", "repairs", "excel", f"{user_id}_repairs.xlsx")

    # Проверяем наличие файла
    if not os.path.exists(excel_path):
        bot.send_message(user_id, "Файл с вашими ремонтами не найден.")
        return

    # Отправка файла пользователю
    with open(excel_path, 'rb') as excel_file:
        bot.send_document(user_id, excel_file)


@bot.message_handler(func=lambda message: message.text == "Ремонты (по категориям)")
def view_repairs_by_category(message):
    user_id = message.from_user.id
    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])

    # Фильтруем ремонты по выбранному транспорту
    repairs = filter_repairs_by_transport(user_id, repairs)

    # Получаем уникальные категории ремонтов для выбранного транспорта
    categories = set(repair['category'] for repair in repairs)
    if not categories:
        bot.send_message(user_id, "Нет доступных категорий для выбранного транспорта.")
        send_menu1(user_id)  # Возврат в меню трат и ремонтов
        return

    category_buttons = [types.KeyboardButton(category) for category in categories]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*category_buttons)
    item_return_to_repairs = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_return_to_main = types.KeyboardButton("В главное меню")
    markup.add(item_return_to_repairs, item_return_to_main)

    bot.send_message(user_id, "Выберите категорию для просмотра ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_repair_category_selection)

# Обработчик выбора категории ремонтов
def handle_repair_category_selection(message):
    user_id = message.from_user.id
    selected_category = message.text

    if selected_category == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if selected_category == "В главное меню":
        return_to_menu(message)  # Возврат в главное меню
        return

    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])

    # Фильтруем ремонты по выбранному транспорту
    repairs = filter_repairs_by_transport(user_id, repairs)

    # Проверяем, существует ли выбранная категория
    if selected_category not in {repair['category'] for repair in repairs}:
        bot.send_message(user_id, "Выбранная категория не найдена. Пожалуйста, выберите корректную категорию.")
        view_repairs_by_category(message)  # Запрашиваем повторный ввод категории
        return

    # Фильтруем ремонты по выбранной категории
    category_repairs = [repair for repair in repairs if repair['category'] == selected_category]

    total_repairs_amount = 0
    repair_details = []

    for index, repair in enumerate(category_repairs, start=1):
        repair_name = repair.get("name", "Без названия")
        repair_date = repair.get("date", "")
        repair_amount = float(repair.get("amount", 0))
        total_repairs_amount += repair_amount

        repair_details.append(
            f"  №: {index}\n\n"
            f"    КАТЕГОРИЯ: {selected_category}\n"
            f"    НАЗВАНИЕ: {repair_name}\n"
            f"    ДАТА: {repair_date}\n"
            f"    СУММА: {repair_amount:.2f} ₽\n"
            f"    ОПИСАНИЕ: {repair.get('description', 'Без описания')}\n"
        )

    if repair_details:
        message_text = f"Ремонты в категории '{selected_category}':\n\n" + "\n\n".join(repair_details)
    else:
        message_text = f"В категории '{selected_category}' ремонтов не найдено."

    send_message_with_split(user_id, message_text)
    bot.send_message(user_id, f"Итоговая сумма ремонтов в категории '{selected_category}': {total_repairs_amount:.2f} ₽.")

    # Возвращаем пользователя в меню выбора категорий
    view_repairs_by_category(message)  # Запрашиваем выбор категории заново

# Обработчик ремонтов за месяц
@bot.message_handler(func=lambda message: message.text == "Ремонты (месяц)")
def view_repairs_by_month(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    markup.add(item_return)

    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для просмотра ремонтов за этот период:", reply_markup=markup)
    bot.register_next_step_handler(message, get_repairs_by_month)

def get_repairs_by_month(message):
    user_id = message.from_user.id
    date = message.text.strip()

    if "." in date:
        parts = date.split(".")
        if len(parts) == 2:
            month, year = parts
            if month.isdigit() and year.isdigit() and 1 <= int(month) <= 12 and len(year) == 4:
                month, year = map(int, parts)
                
                user_data = load_repair_data(user_id)
                repairs = user_data.get(str(user_id), {}).get("repairs", [])

                # Фильтруем ремонты по выбранному транспорту
                repairs = filter_repairs_by_transport(user_id, repairs)

                total_repairs = 0
                repair_details = []

                for index, repair in enumerate(repairs, start=1):
                    repair_date = repair.get("date", "")
                    repair_date_parts = repair_date.split(".")
                    if len(repair_date_parts) >= 2:
                        repair_month, repair_year = map(int, repair_date_parts[1:3])

                        if repair_month == month and repair_year == year:
                            amount = float(repair.get("amount", 0))
                            total_repairs += amount

                            repair_name = repair.get("name", "Без названия")
                            description = repair.get("description", "")
                            category = repair.get("category", "Без категории")

                            repair_details.append(
                                f"  №: {index}\n\n"
                                f"    КАТЕГОРИЯ: {category}\n"
                                f"    НАЗВАНИЕ: {repair_name}\n"
                                f"    ДАТА: {repair_date}\n"
                                f"    СУММА: {amount} руб.\n"
                                f"    ОПИСАНИЕ: {description}\n"
                            )

                if repair_details:
                    message_text = f"Ремонты за {date}:\n\n" + "\n\n".join(repair_details)
                else:
                    message_text = f"За {date} ремонтов не найдено."

                send_message_with_split(user_id, message_text)
                bot.send_message(user_id, f"Итоговая сумма ремонтов за {date}: {total_repairs} руб.")
                send_menu1(user_id)  # Возвращаемся в меню после отображения информации
            else:
                bot.send_message(user_id, "Пожалуйста, введите корректный месяц и год в формате ММ.ГГГГ.")
                bot.register_next_step_handler(message, get_repairs_by_month)
                return  # Возврат из функции, чтобы не продолжать выполнение
        else:
            bot.send_message(user_id, "Пожалуйста, введите дату в формате ММ.ГГГГ.")
            bot.register_next_step_handler(message, get_repairs_by_month)
            return  # Возврат из функции, чтобы не продолжать выполнение
    else:
        bot.send_message(user_id, "Пожалуйста, введите дату в формате ММ.ГГГГ.")
        bot.register_next_step_handler(message, get_repairs_by_month)
        return  # Возврат из функции, чтобы не продолжать выполнение

# Обработчик ремонтов за год
@bot.message_handler(func=lambda message: message.text == "Ремонты (год)")
def view_repairs_by_year(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    markup.add(item_return)

    bot.send_message(user_id, "Введите год в формате (ГГГГ) для просмотра ремонтов за этот год:", reply_markup=markup)
    bot.register_next_step_handler(message, get_repairs_by_year)

def get_repairs_by_year(message):
    user_id = message.from_user.id
    year = message.text.strip()

    if not year.isdigit() or len(year) != 4:
        bot.send_message(user_id, "Пожалуйста, введите год в формате ГГГГ.")
        bot.register_next_step_handler(message, get_repairs_by_year)
        return  # Возврат из функции, чтобы не продолжать выполнение

    year = int(year)
    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])

    # Фильтруем ремонты по выбранному транспорту
    repairs = filter_repairs_by_transport(user_id, repairs)

    total_repairs = 0
    repair_details = []

    for index, repair in enumerate(repairs, start=1):
        repair_date = repair.get("date", "")
        if "." in repair_date:
            date_parts = repair_date.split(".")
            if len(date_parts) >= 3:
                repair_year = int(date_parts[2])
                if repair_year == year:
                    amount = float(repair.get("amount", 0))
                    total_repairs += amount

                    repair_name = repair.get("name", "Без названия")
                    description = repair.get("description", "")
                    category = repair.get("category", "Без категории")

                    repair_details.append(
                        f"  №: {index}\n\n"
                        f"    КАТЕГОРИЯ: {category}\n"
                        f"    НАЗВАНИЕ: {repair_name}\n"
                        f"    ДАТА: {repair_date}\n"
                        f"    СУММА: {amount} руб.\n"
                        f"    ОПИСАНИЕ: {description}\n"
                    )

    if repair_details:
        message_text = f"Ремонты за {year} год:\n\n" + "\n\n".join(repair_details)
    else:
        message_text = f"За {year} год ремонтов не найдено."

    send_message_with_split(user_id, message_text)
    bot.send_message(user_id, f"Итоговая сумма ремонтов за {year} год: {total_repairs} руб.")

    # Возвращаемся в меню после отображения информации
    send_menu1(user_id)

# Обработчик всех ремонтов
@bot.message_handler(func=lambda message: message.text == "Ремонты (всё время)")
def view_all_repairs(message):
    user_id = message.from_user.id

    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])

    # Фильтруем ремонты по выбранному транспорту
    repairs = filter_repairs_by_transport(user_id, repairs)

    total_repairs = 0
    repair_details = []

    for index, repair in enumerate(repairs, start=1):
        amount = float(repair.get("amount", 0))
        total_repairs += amount

        repair_name = repair.get("name", "Без названия")
        repair_date = repair.get("date", "")
        description = repair.get("description", "")
        category = repair.get("category", "Без категории")

        repair_details.append(
            f"  №: {index}\n\n"
            f"    КАТЕГОРИЯ: {category}\n"
            f"    НАЗВАНИЕ: {repair_name}\n"
            f"    ДАТА: {repair_date}\n"
            f"    СУММА: {amount} руб.\n"
            f"    ОПИСАНИЕ: {description}\n"
        )

    if repair_details:
        message_text = "Все ремонты:\n\n" + "\n\n".join(repair_details)
    else:
        message_text = "Ремонт не найдено."

    send_message_with_split(user_id, message_text)
    bot.send_message(user_id, f"Итоговая сумма всех ремонтов: {total_repairs} руб.")

    # Возвращаемся в меню после отображения информации
    send_menu1(user_id)

# (11.9) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "УДАЛИТЬ РЕМОНТЫ") ---------------

valid_months = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

def save_selected_transport(user_id, selected_transport):
    user_data = load_repair_data(user_id).get(str(user_id), {})
    user_data["selected_transport"] = selected_transport
    save_repair_data(user_id, {str(user_id): user_data})

# Удаление ремонтов
@bot.message_handler(func=lambda message: message.text == "Удалить ремонты")
def delete_repairs_menu(message):
    user_id = message.from_user.id

    transport_data = load_transport_data(user_id)
    if not transport_data:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_add_transport = types.KeyboardButton("Добавить транспорт")
        item_cancel = types.KeyboardButton("Отмена")
        markup.add(item_add_transport, item_cancel)
        bot.send_message(user_id, "У вас нет зарегистрированного транспорта. Хотите добавить транспорт?", reply_markup=markup)
        bot.register_next_step_handler(message, add_transport)
        return

    # Отображение транспорта для удаления
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for transport in transport_data:
        brand = transport.get("brand", "Без названия")
        model = transport.get("model", "Без названия")
        year = transport.get("year", "Неизвестно")
        button_label = f"{brand} {model} {year}"
        markup.add(types.KeyboardButton(button_label))

    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return, item_main_menu)
    bot.send_message(user_id, "Выберите транспорт для удаления ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection_for_deletion_repairs)

def handle_transport_selection_for_deletion_repairs(message):
    user_id = message.from_user.id
    selected_transport = message.text

    # Сохраняем выбранный транспорт
    save_selected_transport(user_id, selected_transport)

    if selected_transport == "Del ремонты (категория)":
        delete_repairs_by_category(message)
        return

    if selected_transport == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if selected_transport == "В главное меню":
        return_to_menu(message)
        return

    # Запрос на удаление ремонтов
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_month = types.KeyboardButton("Del ремонты (месяц)")
    item_year = types.KeyboardButton("Del ремонты (год)")
    item_all_time = types.KeyboardButton("Del ремонты (всё время)")
    item_del_category_rep = types.KeyboardButton("Del ремонты (категория)")
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")

    markup.add(item_month, item_year, item_all_time, item_del_category_rep)
    markup.add(item_return, item_main_menu)
    bot.send_message(user_id, "Выберите вариант удаления ремонтов:", reply_markup=markup)

# Новый обработчик для удаления по категории
@bot.message_handler(func=lambda message: message.text == "Del ремонты (категория)")
def delete_repairs_by_category(message):
    user_id = message.from_user.id

    user_data = load_repair_data(user_id).get(str(user_id), {})
    selected_transport = user_data.get("selected_transport")

    if not selected_transport:
        bot.send_message(user_id, "Не выбран транспорт. Вернитесь в меню.")
        send_menu(user_id)
        return

    # Получаем марку, модель и год из выбранного транспорта
    transport_info = selected_transport.split(" ")
    selected_brand = transport_info[0]  # Марка
    selected_model = transport_info[1]  # Модель
    selected_year = transport_info[2]    # Год

    repairs = user_data.get("repairs", [])
    
    # Фильтруем ремонты по выбранному транспорту
    categories = list(set(repair.get("category") for repair in repairs 
                          if (repair.get("transport", {}).get("brand") == selected_brand and
                              repair.get("transport", {}).get("model") == selected_model and
                              str(repair.get("transport", {}).get("year")) == selected_year)))

    if not categories:
        bot.send_message(user_id, "У вас нет категорий для удаления ремонтов по выбранному транспорту.")
        send_menu(user_id)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for category in categories:
        markup.add(types.KeyboardButton(category))

    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return, item_main_menu)
    
    bot.send_message(user_id, "Выберите категорию для удаления:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_category_selection_repairs)

def handle_category_selection_repairs(message):
    user_id = message.from_user.id
    selected_category = message.text

    if selected_category == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    user_data = load_repair_data(user_id).get(str(user_id), {})
    repairs = user_data.get("repairs", [])
    
    # Получаем выбранный транспорт
    selected_transport = user_data.get("selected_transport")
    transport_info = selected_transport.split(" ")
    selected_brand = transport_info[0]
    selected_model = transport_info[1]
    selected_year = transport_info[2]

    repairs_to_delete = [repair for repair in repairs if 
                         repair.get("category") == selected_category and
                         repair.get("transport", {}).get("brand") == selected_brand and
                         repair.get("transport", {}).get("model") == selected_model and
                         str(repair.get("transport", {}).get("year")) == selected_year]

    if not repairs_to_delete:
        bot.send_message(user_id, f"Нет ремонтов для удаления в категории '{selected_category}' по выбранному транспорту.")
        send_menu(user_id)
        return

    # Отображение ремонтов для удаления в более удобном формате
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    keyboard.add(types.KeyboardButton("В главное меню"))
    
    for index, repair in enumerate(repairs_to_delete, start=1):
        repair_name = repair.get("name", "Без названия")
        keyboard.add(types.KeyboardButton(f"Удалить ремонт #{index} - {repair_name}"))

    bot.send_message(user_id, f"Выберите ремонт для удаления из категории '{selected_category}':", reply_markup=keyboard)
    bot.register_next_step_handler(message, confirm_delete_repair_by_category, repairs_to_delete)

def confirm_delete_repair_by_category(message, repairs_to_delete):
    user_id = message.from_user.id
    selected_option = message.text

    user_data = load_repair_data(user_id).get(str(user_id), {})
    selected_transport = user_data.get("selected_transport")

    # Получаем марку, модель и год из выбранного транспорта
    transport_info = selected_transport.split(" ")
    selected_brand = transport_info[0]  # Марка
    selected_model = transport_info[1]  # Модель
    selected_year = transport_info[2]    # Год

    if selected_option.startswith("Удалить ремонт #"):
        try:
            repair_index = int(selected_option.split("#")[1].split(" - ")[0]) - 1
            repairs = user_data.get("repairs", [])

            if 0 <= repair_index < len(repairs_to_delete):
                deleted_repair = repairs_to_delete[repair_index]
                repairs.remove(deleted_repair)  # Удаляем только ремонт
                user_data["repairs"] = repairs  # Обновляем список ремонтов
                save_repair_data(user_id, {str(user_id): user_data})  # Сохраняем изменения

                update_repairs_excel_file(user_id)

                bot.send_message(user_id, f"Ремонт '{deleted_repair.get('name', 'Без названия')}' удален успешно.")
            else:
                bot.send_message(user_id, "Недопустимый выбор. Пожалуйста, выберите ремонт из списка.")
        except ValueError:
            bot.send_message(user_id, "Ошибка при обработке выбора. Пожалуйста, выберите ремонт из списка.")
    else:
        bot.send_message(user_id, "Недопустимый выбор. Пожалуйста, выберите ремонт из списка.")

    send_menu(user_id)

# Удаление ремонтов за месяц
@bot.message_handler(func=lambda message: message.text == "Del ремонты (месяц)")
def delete_repairs_by_month(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return, item_main_menu)
    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для удаления ремонтов за этот месяц:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_repairs_by_month_handler)

def delete_repairs_by_month_handler(message):
    user_id = message.from_user.id
    month_year = message.text.strip()

    # Проверка формата ввода
    if len(month_year) != 7 or month_year[2] != '.' or month_year[:2] not in valid_months:
        bot.send_message(user_id, "Введен неверный месяц. Пожалуйста, введите корректный месяц (ММ.ГГГГ).")
        bot.register_next_step_handler(message, delete_repairs_by_month_handler)
        return

    user_data = load_repair_data(user_id).get(str(user_id), {})
    repairs = user_data.get("repairs", [])

    # Получаем выбранный транспорт
    selected_transport = user_data.get("selected_transport")

    # Извлекаем марку, модель и год из выбранного транспорта
    if selected_transport:
        transport_info = selected_transport.split(" ")
        selected_brand = transport_info[0]  # Первая часть - марка
        selected_model = transport_info[1]  # Вторая часть - модель
        selected_year = transport_info[2]    # Третья часть - год
    else:
        selected_brand = selected_model = selected_year = None

    if not repairs:
        bot.send_message(user_id, f"У вас пока нет сохраненных ремонтов за {month_year} для удаления.")
        send_menu(user_id)
        return

    repairs_to_delete = []
    for index, repair in enumerate(repairs, start=1):
        repair_date = repair.get("date", "")
        repair_month_year = repair_date.split(".")[1] + "." + repair_date.split(".")[2]

        # Проверяем, совпадает ли месяц, год и выбранный транспорт
        if repair_month_year == month_year and \
           repair.get("transport", {}).get("brand") == selected_brand and \
           repair.get("transport", {}).get("model") == selected_model and \
           str(repair.get("transport", {}).get("year")) == selected_year:
            repairs_to_delete.append((index, repair))

    if repairs_to_delete:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        keyboard.add(types.KeyboardButton("В главное меню"))
        for index, repair in repairs_to_delete:
            repair_name = repair.get("name", "Без названия")
            keyboard.add(types.KeyboardButton(f"Удалить ремонт #{index} - {repair_name}"))

        bot.send_message(user_id, "Выберите ремонт для удаления:", reply_markup=keyboard)
        bot.register_next_step_handler(message, confirm_delete_repair_month, repairs_to_delete)
    else:
        bot.send_message(user_id, f"За {month_year} месяц ремонтов не найдено для удаления.")
        send_menu(user_id)

def confirm_delete_repair_month(message, repairs_to_delete):
    user_id = message.from_user.id
    selected_option = message.text

    if selected_option.startswith("Удалить ремонт #"):
        try:
            repair_index = int(selected_option.split("#")[1].split(" - ")[0]) - 1
            user_data = load_repair_data(user_id).get(str(user_id), {})
            repairs = user_data.get("repairs", [])

            if 0 <= repair_index < len(repairs):
                deleted_repair = repairs.pop(repair_index)
                user_data["repairs"] = repairs 
                save_repair_data(user_id, {str(user_id): user_data}) 

                update_repairs_excel_file(user_id)

                bot.send_message(user_id, f"Ремонт '{deleted_repair.get('name', 'Без названия')}' удален успешно.")
            else:
                bot.send_message(user_id, "Недопустимый выбор. Пожалуйста, выберите ремонт из списка.")
        except ValueError:
            bot.send_message(user_id, "Ошибка при обработке выбора. Пожалуйста, выберите ремонт из списка.")
    else:
        bot.send_message(user_id, "Недопустимый выбор. Пожалуйста, выберите ремонт из списка.")

    send_menu(user_id)

# Удаление ремонтов за год
@bot.message_handler(func=lambda message: message.text == "Del ремонты (год)")
def delete_repairs_by_year(message):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return, item_main_menu)
    bot.send_message(user_id, "Введите год (ГГГГ) для удаления ремонтов за этот год:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_repairs_by_year_handler)

def delete_repairs_by_year_handler(message):
    user_id = message.from_user.id
    year = message.text.strip()

    user_data = load_repair_data(user_id).get(str(user_id), {})
    repairs = user_data.get("repairs", [])

    # Получаем выбранный транспорт
    selected_transport = user_data.get("selected_transport")
    
    # Извлекаем марку, модель и год из выбранного транспорта
    if selected_transport:
        transport_info = selected_transport.split(" ")
        selected_brand = transport_info[0]  # Первая часть - марка
        selected_model = transport_info[1]  # Вторая часть - модель
        selected_year = transport_info[2]    # Третья часть - год
    else:
        selected_brand = selected_model = selected_year = None

    if not repairs:
        bot.send_message(user_id, f"У вас пока нет сохраненных ремонтов за {year} для удаления.")
        send_menu(user_id)
        return

    repairs_to_delete = []
    for index, repair in enumerate(repairs, start=1):
        repair_year = repair.get("date", "").split(".")[2]
        # Проверяем, совпадает ли год и выбранный транспорт
        if repair_year == year and \
           repair.get("transport", {}).get("brand") == selected_brand and \
           repair.get("transport", {}).get("model") == selected_model and \
           str(repair.get("transport", {}).get("year")) == selected_year:
            repairs_to_delete.append((index, repair))

    if repairs_to_delete:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        keyboard.add(types.KeyboardButton("В главное меню"))
        for index, repair in repairs_to_delete:
            repair_name = repair.get("name", "Без названия")
            keyboard.add(types.KeyboardButton(f"Удалить ремонт #{index} - {repair_name}"))

        bot.send_message(user_id, "Выберите ремонт для удаления:", reply_markup=keyboard)
        bot.register_next_step_handler(message, confirm_delete_repair_year, repairs_to_delete)
    else:
        bot.send_message(user_id, f"За {year} год ремонтов не найдено для удаления.")
        send_menu(user_id)

def confirm_delete_repair_year(message, repairs_to_delete):
    user_id = message.from_user.id
    selected_option = message.text

    if selected_option.startswith("Удалить ремонт #"):
        try:
            repair_index = int(selected_option.split("#")[1].split(" - ")[0]) - 1
            user_data = load_repair_data(user_id).get(str(user_id), {})
            repairs = user_data.get("repairs", [])

            if 0 <= repair_index < len(repairs):
                deleted_repair = repairs.pop(repair_index)
                user_data["repairs"] = repairs 
                save_repair_data(user_id, {str(user_id): user_data}) 

                update_repairs_excel_file(user_id)

                bot.send_message(user_id, f"Ремонт '{deleted_repair.get('name', 'Без названия')}' удален успешно.")
            else:
                bot.send_message(user_id, "Недопустимый выбор. Пожалуйста, выберите ремонт из списка.")
        except ValueError:
            bot.send_message(user_id, "Ошибка при обработке выбора. Пожалуйста, выберите ремонт из списка.")
    else:
        bot.send_message(user_id, "Недопустимый выбор. Пожалуйста, выберите ремонт из списка.")

    send_menu(user_id)

# Удаление всех ремонтов
@bot.message_handler(func=lambda message: message.text == "Del ремонты (всё время)")
def delete_all_repairs(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return, item_main_menu)
    
    bot.send_message(user_id, "Вы уверены, что хотите удалить все ремонты для выбранного транспорта? (да/нет)", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_delete_all_repairs)

def confirm_delete_all_repairs(message):
    user_id = message.from_user.id

    # Обработка возвратов в меню
    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    response = message.text.lower()

    # Убедитесь, что вы получаете выбранный транспорт
    user_data = load_repair_data(user_id).get(str(user_id), {})
    selected_transport = user_data.get("selected_transport")  # Получаем сохранённый транспорт

    if response == "да":
        if selected_transport:
            # Разделяем выбранный транспорт на компоненты
            selected_transport_parts = selected_transport.split()
            selected_brand = selected_transport_parts[0].lower()
            selected_model = selected_transport_parts[1].lower()
            selected_year = selected_transport_parts[2]

            # Удаляем все ремонты для выбранного транспорта
            repairs_to_keep = []
            for repair in user_data.get("repairs", []):
                repair_brand = repair['transport']['brand'].lower()
                repair_model = repair['transport']['model'].lower()
                repair_year = str(repair['transport']['year'])

                # Если ремонты относятся к другому транспорту, сохраняем их
                if not (repair_brand == selected_brand and
                        repair_model == selected_model and
                        repair_year == selected_year):
                    repairs_to_keep.append(repair)

            # Сохраняем оставшиеся ремонты
            user_data["repairs"] = repairs_to_keep
            save_repair_data(user_id, {str(user_id): user_data})

            update_repairs_excel_file(user_id)

            bot.send_message(user_id, f"Все ремонты для транспорта '{selected_brand} {selected_model} {selected_year}' успешно удалены.")
        else:
            bot.send_message(user_id, "Не удалось найти выбранный транспорт.")
    else:
        bot.send_message(user_id, "Удаление ремонтов отменено.")

    send_menu(user_id)

def delete_repair(user_id, deleted_repair):
    # Загружаем данные о ремонтах пользователя
    user_data = load_repair_data(user_id).get(str(user_id), {})
    repairs = user_data.get("repairs", [])

    # Удаляем ремонт из списка ремонтов
    repairs = [repair for repair in repairs if not (
        repair["transport"]["brand"] == deleted_repair["transport"]["brand"] and
        repair["transport"]["model"] == deleted_repair["transport"]["model"] and
        repair["transport"]["year"] == deleted_repair["transport"]["year"] and
        repair["category"] == deleted_repair["category"] and
        repair["name"] == deleted_repair["name"] and
        repair["date"] == deleted_repair["date"] and
        repair["amount"] == deleted_repair["amount"] and
        repair["description"] == deleted_repair["description"]
    )]

    # Обновляем данные пользователя
    user_data["repairs"] = repairs
    save_repair_data(user_id, user_data)

    # Обновляем Excel файл
    update_repairs_excel_file(user_id)

def update_repairs_excel_file(user_id):
    user_data = load_repair_data(user_id).get(str(user_id), {})
    repairs = user_data.get("repairs", [])

    # Путь к Excel файлу пользователя для ремонтов
    excel_file_path = f"data base/repairs/excel/{user_id}_repairs.xlsx"

    # Проверяем, существует ли файл
    if not os.path.exists(excel_file_path):
        workbook = openpyxl.Workbook()
        workbook.remove(workbook.active)
        workbook.save(excel_file_path)

    # Открываем существующий файл
    workbook = load_workbook(excel_file_path)

    # Обновление общего листа (Summary)
    summary_sheet = workbook["Summary"] if "Summary" in workbook.sheetnames else workbook.create_sheet("Summary")
    headers = ["Транспорт", "Категория", "Название", "Дата", "Сумма", "Описание"]

    # Очистка всех данных на листе Summary (кроме заголовков)
    if summary_sheet.max_row > 1:
        summary_sheet.delete_rows(2, summary_sheet.max_row)

    # Добавляем заголовки, если они еще не добавлены
    if summary_sheet.max_row == 0:
        summary_sheet.append(headers)
        for cell in summary_sheet[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")

    # Заполняем общий лист новыми данными
    for repair in repairs:
        transport = repair["transport"]
        row_data = [
            f"{transport['brand']} {transport['model']} {transport['year']}",
            repair["category"],
            repair["name"],
            repair["date"],
            repair["amount"],
            repair["description"],
        ]
        summary_sheet.append(row_data)

    # Обновление индивидуальных листов для каждого транспорта
    unique_transports = set((rep["transport"]["brand"], rep["transport"]["model"], rep["transport"]["year"]) for rep in repairs)

    # Удаляем старые листы для уникальных транспортов
    for sheet_name in workbook.sheetnames:
        if sheet_name != "Summary" and (sheet_name.split('_')[0], sheet_name.split('_')[1], sheet_name.split('_')[2]) not in unique_transports:
            del workbook[sheet_name]

    for brand, model, year in unique_transports:
        sheet_name = f"{brand}_{model}_{year}"
        if sheet_name not in workbook.sheetnames:
            transport_sheet = workbook.create_sheet(sheet_name)
            transport_sheet.append(headers)
            for cell in transport_sheet[1]:
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal="center")
        else:
            transport_sheet = workbook[sheet_name]
            # Очистка всех данных на листе транспорта, кроме заголовков
            if transport_sheet.max_row > 1:
                transport_sheet.delete_rows(2, transport_sheet.max_row)

        # Заполняем ремонты для этого транспорта
        for repair in repairs:
            if (repair["transport"]["brand"], repair["transport"]["model"], repair["transport"]["year"]) == (brand, model, year):
                row_data = [
                    f"{brand} {model} {year}",
                    repair["category"],
                    repair["name"],
                    repair["date"],
                    repair["amount"],
                    repair["description"],
                ]
                transport_sheet.append(row_data)

    # Автоподгонка столбцов
    for sheet in workbook.sheetnames:
        current_sheet = workbook[sheet]
        for col in current_sheet.columns:
            max_length = max(len(str(cell.value)) for cell in col)
            current_sheet.column_dimensions[get_column_letter(col[0].column)].width = max_length + 2

    # Сохраняем изменения
    workbook.save(excel_file_path)
    workbook.close()

# (12) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" ---------------

# (12.1) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ВВОДНЫЕ ФУНКЦИИ) ---------------

geolocator = Nominatim(user_agent="geo_bot")

user_locations = {}

# Функция для генерации ссылки на Yandex.Карты
def get_yandex_maps_search_url(latitude, longitude, query):
    base_url = "https://yandex.ru/maps/?"
    search_params = {
        'll': f"{longitude},{latitude}",
        'z': 15,  # Уровень масштабирования карты
        'text': query,  # Тип объекта, например, 'АЗС'
        'mode': 'search'
    }
    query_string = "&".join([f"{key}={value}" for key, value in search_params.items()])
    return f"{base_url}{query_string}"

# Функция для сокращения URL
def shorten_url(original_url):
    endpoint = 'https://clck.ru/--'
    response = requests.get(endpoint, params={'url': original_url})
    return response.text

# Обработчик для главного меню "Поиск мест"
@bot.message_handler(func=lambda message: message.text == "Поиск мест")
def send_welcome(message):
    user_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Кнопки с категориями
    button_azs = types.KeyboardButton("АЗС")
    button_car_wash = types.KeyboardButton("Автомойки")
    button_auto_service = types.KeyboardButton("Автосервисы")
    button_parking = types.KeyboardButton("Парковки")
    button_evacuation = types.KeyboardButton("Эвакуация")
    button_gibdd_mreo = types.KeyboardButton("ГИБДД")
    button_accident_commissioner = types.KeyboardButton("Комиссары")
    button_impound = types.KeyboardButton("Штрафстоянка")  # Новая кнопка для штрафстоянки

    # Кнопка для возврата в главное меню
    item1 = types.KeyboardButton("В главное меню")

    # Добавление кнопок на клавиатуру
    markup.add(button_azs, button_car_wash, button_auto_service)
    markup.add(button_parking, button_evacuation, button_gibdd_mreo, button_accident_commissioner, button_impound)  # Добавляем кнопку штрафстоянки
    markup.add(item1)

    # Отправка пользователю
    bot.send_message(user_id, "Выберите категорию для ближайшего поиска:", reply_markup=markup)

# Обработчик для выбора категории заново
@bot.message_handler(func=lambda message: message.text == "Выбрать категорию заново")
def handle_reset_category(message):
    global selected_category
    selected_category = None
    send_welcome(message)

selected_category = None 

# Обработчик для выбора категории
@bot.message_handler(func=lambda message: message.text in {"АЗС", "Автомойки", "Автосервисы", "Парковки", "Эвакуация", "ГИБДД", "Комиссары", "Штрафстоянка"})
def handle_menu_buttons(message):
    global selected_category 
    if message.text in {"АЗС", "Автомойки", "Автосервисы", "Парковки", "Эвакуация", "ГИБДД", "Комиссары", "Штрафстоянка"}:  # Включаем "Штрафстоянка"
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

# Обработчик для получения геолокации
@bot.message_handler(content_types=['location'])
def handle_location(message):
    global selected_category, user_locations
    latitude = message.location.latitude
    longitude = message.location.longitude
    user_id = message.from_user.id

    try:
        # Получение адреса по координатам
        location = geolocator.reverse((latitude, longitude), language='ru', timeout=10)
        address = location.address

        if selected_category is None:
            bot.send_message(message.chat.id, "Пожалуйста, выберите категорию из меню.")
            return

        # Сохранение координат пользователя
        user_locations[user_id] = {"address": address, "coordinates": (latitude, longitude)}

        # Создание ссылки на Yandex.Карты
        search_url = get_yandex_maps_search_url(latitude, longitude, selected_category)
        short_search_url = shorten_url(search_url)

        # Формирование сообщения
        message_text = f"Ближайшие {selected_category.lower()} по адресу:\n\n{address}\n\n"
        message_text += f"Ссылка на карту: {short_search_url}"

        # Отправка сообщения
        bot.send_message(message.chat.id, message_text, parse_mode='HTML')

        # Сброс категории
        selected_category = None

        # Клавиатура для выбора новой категории или возврата в главное меню
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

# Обработчик для команды "Найти транспорт"
@bot.message_handler(func=lambda message: message.text == "Найти транспорт")
def start_transport_search(message):
    global location_data
    user_id = str(message.from_user.id)

    # Если уже начат процесс (начальная геопозиция была сохранена)
    if user_id in location_data and location_data[user_id].get('start_location') is not None and location_data[user_id].get('end_location') is None:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Продолжить")
        item2 = types.KeyboardButton("Начать заново")
        item3 = types.KeyboardButton("В главное меню")
        markup.add(item1, item2)
        markup.add(item3)
        bot.send_message(message.chat.id, "Хотите продолжить с того места, где остановились?", reply_markup=markup)
        bot.register_next_step_handler(message, continue_or_restart)
    else:
        start_new_transport_search(message)

# Функция для начала нового поиска транспорта
def start_new_transport_search(message):
    global location_data
    user_id = str(message.from_user.id)

    # Очищаем данные для нового поиска
    location_data[user_id] = {'start_location': None, 'end_location': None}
    save_location_data(location_data)

    request_transport_location(message)

# Функция для запроса геопозиции транспорта
def request_transport_location(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Отправить геопозицию", request_location=True)
    item2 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)

    bot.send_message(message.chat.id, "Отправьте геопозицию транспорта:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_car_location)

# Обработка ответа на предложение продолжить или начать заново
def continue_or_restart(message):
    if message.text == "Продолжить":
        # После продолжения вернем кнопки для отправки геопозиции
        request_user_location(message)
    elif message.text == "Начать заново":
        start_new_transport_search(message)
    else:
        return_to_menu(message)

# Функция для запроса геопозиции пользователя
def request_user_location(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Отправить геопозицию", request_location=True)
    item2 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)

    bot.send_message(message.chat.id, "Теперь отправьте свою геопозицию:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_car_location)

# Обработка геопозиции транспорта и пользователя
@bot.message_handler(content_types=['location'])
def handle_car_location(message):
    global location_data
    user_id = str(message.from_user.id)

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if user_id not in location_data:
        location_data[user_id] = {'start_location': None, 'end_location': None}

    # Сохранение геопозиции транспорта
    if location_data[user_id]['start_location'] is None:
        if message.location is not None:
            location_data[user_id]['start_location'] = {
                LATITUDE_KEY: message.location.latitude,
                LONGITUDE_KEY: message.location.longitude
            }

            # Сохраняем, что процесс поиска начат
            location_data[user_id]['process'] = 'in_progress'
            save_location_data(location_data)

            # Запрашиваем геопозицию пользователя
            request_user_location(message)
        else:
            handle_location_error(message)

    # Сохранение геопозиции пользователя
    elif location_data[user_id]['end_location'] is None:
        if message.location is not None:
            location_data[user_id]['end_location'] = {
                LATITUDE_KEY: message.location.latitude,
                LONGITUDE_KEY: message.location.longitude
            }

            # Завершаем процесс, сохранив данные
            location_data[user_id]['process'] = 'completed'
            save_location_data(location_data)

            send_map_link(message.chat.id, location_data[user_id]['start_location'], location_data[user_id]['end_location'])
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton("Найти транспорт")
            item2 = types.KeyboardButton("В главное меню")
            markup.add(item1)
            markup.add(item2)
            bot.send_message(message.chat.id, "Вы можете найти транспорт еще раз.", reply_markup=markup)
        else:
            handle_location_error(message)

# Функция обработки ошибки при получении геопозиции
def handle_location_error(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    bot.send_message(message.chat.id, "Извините, не удалось получить геопозицию. Попробуйте еще раз.")
    bot.register_next_step_handler(message, handle_car_location)

# Отправка карты с маршрутом
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
API_KEY = '2949ae1ef99c838462d16e7b0caf65b5'

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
        if period == 'сегодня':
            send_weather(chat_id, coords, WEATHER_URL)
        elif period == 'завтра':
            send_forecast_daily(chat_id, coords, FORECAST_URL, 1)
        elif period == 'неделя':
            send_forecast_weekly(chat_id, coords, FORECAST_URL, 8)
        elif period == 'месяц':
            send_forecast_monthly(chat_id, coords, FORECAST_URL, 31)
    else:
        bot.send_message(chat_id, "Не удалось получить координаты. Пожалуйста, отправьте местоположение еще раз.")

def send_weather(chat_id, coords, url):
    try:
        # Запрос текущей погоды
        params = {
            'lat': coords['latitude'],
            'lon': coords['longitude'],
            'appid': API_KEY,
            'units': 'metric'  # Изменено на 'metric' для получения температуры в Цельсиях
        }
        response = requests.get(url, params=params)
        data = response.json()

        if response.status_code == 200:
            temperature = round(data['main']['temp'])
            feels_like = round(data['main']['feels_like'])
            humidity = data['main']['humidity']
            pressure = data['main']['pressure']
            wind_speed = data['wind']['speed']
            description = translate_weather_description(data['weather'][0]['description'])

            current_time = datetime.now().strftime("%H:%M")
            current_date = datetime.now().strftime("%d.%m.%Y")

            message = (
                f"*Погода на {current_date} в {current_time}:*\n\n"
                f"*Температура:* {temperature}°C\n"
                f"*Ощущается как:* {feels_like}°C\n"
                f"*Влажность:* {humidity}%\n"
                f"*Давление:* {pressure} мм рт. ст.\n"
                f"*Скорость ветра:* {wind_speed} м/с\n"
                f"*Описание:* {description}\n"
            )
            bot.send_message(chat_id, message, parse_mode="Markdown")
            send_forecast_remaining_day(chat_id, coords, FORECAST_URL)
        else:
            bot.send_message(chat_id, "Не удалось получить текущую погоду. Проверьте, правильно ли указаны координаты.")
    except Exception as e:
        print(f"Ошибка при отправке текущей погоды: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе текущей погоды. Попробуйте позже.")

def send_forecast_remaining_day(chat_id, coords, url):
    try:
        params = {
            'lat': coords['latitude'],
            'lon': coords['longitude'],
            'appid': API_KEY,
            'units': 'metric',
            'lang': 'ru'
        }
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if response.status_code == 200:
            forecasts = data['list']
            now = datetime.now()
            message = "*Прогноз на оставшуюся часть дня:*\n\n"

            for forecast in forecasts:
                date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                
                # Только прогноз на сегодня
                if now.date() == date_time.date() and date_time > now:
                    formatted_date = date_time.strftime("%d.%m.%Y")
                    formatted_time = date_time.strftime("%H:%M")
                    temperature = round(forecast['main']['temp'])
                    feels_like = round(forecast['main']['feels_like'])
                    humidity = forecast['main']['humidity']
                    pressure = forecast['main']['pressure']
                    wind_speed = forecast['wind']['speed']
                    description = translate_weather_description(forecast['weather'][0]['description'])

                    message += (
                        f"*Погода на {formatted_date} в {formatted_time}:*\n\n"
                        f"*Температура:* {temperature}°C\n"
                        f"*Ощущается как:* {feels_like}°C\n"
                        f"*Влажность:* {humidity}%\n"
                        f"*Давление:* {pressure} мм рт. ст.\n"
                        f"*Скорость ветра:* {wind_speed} м/с\n"
                        f"*Описание:* {description}\n\n"
                    )

            if message == "*Прогноз на оставшуюся часть дня:*\n\n":
                message = "Нет доступного прогноза на оставшуюся часть дня."

            bot.send_message(chat_id, message, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "Не удалось получить прогноз на оставшуюся часть дня.")
    except Exception as e:
        print(f"Ошибка при отправке прогноза на оставшуюся часть дня: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на оставшуюся часть дня. Попробуйте позже.")


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
            message = "*Прогноз на завтра:*\n"

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
                    f"*Температура:* {temperature}°C\n"
                    f"*Ощущается как:* {feels_like}°C\n"
                    f"*Влажность:* {humidity}%\n"
                    f"*Давление:* {pressure} мм рт. ст\n"
                    f"*Скорость ветра:* {wind_speed} м/с\n"
                    f"*Описание:* {description}\n\n"
                )

            message_chunks = [message[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]

            for chunk in message_chunks:
                bot.send_message(chat_id, chunk, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "Не удалось получить прогноз погоды на завтра.")
    except Exception as e:
        print(f"Ошибка при отправке прогноза на завтра: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на завтра. Попробуйте позже.")

# (15.8) --------------- КОД ДЛЯ "ПОГОДЫ" (ФУНКЦИЯ ПОГОДЫ НА ЗАВТРА) ---------------

# ---------- ПРОГНОЗ НА ЗАВТРА -----------
def send_forecast_daily(chat_id, coords, url, days_ahead):
    try:
        params = {
            'lat': coords['latitude'],
            'lon': coords['longitude'],
            'appid': API_KEY,
            'units': 'metric',
            'lang': 'ru'
        }
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if response.status_code == 200:
            forecast = data['list'][days_ahead * 8]
            date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
            temperature = round(forecast['main']['temp'])
            feels_like = round(forecast['main']['feels_like'])
            humidity = forecast['main']['humidity']
            pressure = forecast['main']['pressure']
            wind_speed = forecast['wind']['speed']
            description = translate_weather_description(forecast['weather'][0]['description'])

            message = (
                f"*Прогноз на {date_time.strftime('%d.%m.%Y')}*\n\n"
                f"*Температура:* {temperature}°C\n"
                f"*Ощущается как:* {feels_like}°C\n"
                f"*Влажность:* {humidity}%\n"
                f"*Давление:* {pressure} мм рт. ст.\n"
                f"*Скорость ветра:* {wind_speed} м/с\n"
                f"*Описание:* {description}\n"
            )
            bot.send_message(chat_id, message, parse_mode="Markdown")

            send_hourly_forecast_tomorrow(chat_id, coords, url)
        else:
            bot.send_message(chat_id, "Не удалось получить прогноз на завтра.")
    except Exception as e:
        print(f"Ошибка при отправке прогноза на завтра: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на завтра. Попробуйте позже.")

# Функция для отправки почасового прогноза на завтра
def send_hourly_forecast_tomorrow(chat_id, coords, url):
    try:
        params = {
            'lat': coords['latitude'],
            'lon': coords['longitude'],
            'appid': API_KEY,
            'units': 'metric',
            'lang': 'ru'
        }
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if response.status_code == 200:
            forecasts = data['list']
            now = datetime.now()
            tomorrow = now + timedelta(days=1)
            message = "*Почасовой прогноз на завтра:*\n\n"  # Добавлен жирный шрифт и пустая строка

            for forecast in forecasts:
                date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                if tomorrow.date() == date_time.date():
                    formatted_time = date_time.strftime("%H:%M")
                    formatted_date = date_time.strftime("%d.%m.%Y")  # Форматирование даты
                    temperature = round(forecast['main']['temp'])
                    feels_like = round(forecast['main']['feels_like'])
                    humidity = forecast['main']['humidity']
                    pressure = forecast['main']['pressure']
                    wind_speed = forecast['wind']['speed']
                    description = translate_weather_description(forecast['weather'][0]['description'])

                    message += (
                        f"*Погода на {formatted_date} в {formatted_time}:*\n\n"
                        f"*Температура:* {temperature}°C\n"
                        f"*Ощущается как:* {feels_like}°C\n"
                        f"*Влажность:* {humidity}%\n"
                        f"*Давление:* {pressure} мм рт. ст.\n"
                        f"*Скорость ветра:* {wind_speed} м/с\n"
                        f"*Описание:* {description}\n\n"  # Пустая строка
                    )

            if message == "*Почасовой прогноз на завтра:*\n\n":
                message = "Нет доступного почасового прогноза на завтра."

            message_chunks = [message[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]
            for chunk in message_chunks:
                bot.send_message(chat_id, chunk, parse_mode="Markdown")  # Убедитесь, что используется Markdown
        else:
            bot.send_message(chat_id, "Не удалось получить почасовой прогноз на завтра.")
    except Exception as e:
        print(f"Ошибка при отправке почасового прогноза на завтра: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе почасового прогноза на завтра. Попробуйте позже.")
        
# (15.9) --------------- КОД ДЛЯ "ПОГОДЫ" (ФУНКЦИЯ ПОГОДЫ НА НЕДЕЛЮ) ---------------

from datetime import datetime, timedelta
from collections import defaultdict

# ---------- ПРОГНОЗ НА НЕДЕЛЮ -----------
from collections import defaultdict
from datetime import datetime

def send_forecast_weekly(chat_id, coords, url, retries=3):
    try:
        params = {
            'lat': coords['latitude'],
            'lon': coords['longitude'],
            'appid': API_KEY,
            'units': 'metric',
            'lang': 'ru'
        }

        daily_forecasts = defaultdict(list)
        message = "*Прогноз на неделю:*\n\n"

        for attempt in range(retries):
            try:
                response = requests.get(url, params=params, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    forecasts = data['list']

                    # Собираем прогнозы за 7 дней
                    for forecast in forecasts:
                        date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                        date_str = date_time.strftime('%d.%m.%Y')

                        if len(daily_forecasts) >= 7 and date_str not in daily_forecasts:
                            break

                        temperature = round(forecast['main']['temp'])
                        feels_like = round(forecast['main']['feels_like'])
                        humidity = forecast['main']['humidity']
                        pressure = forecast['main']['pressure']
                        wind_speed = forecast['wind']['speed']
                        description = translate_weather_description(forecast['weather'][0]['description'])

                        daily_forecasts[date_str].append({
                            'temperature': temperature,
                            'feels_like': feels_like,
                            'humidity': humidity,
                            'pressure': pressure,
                            'wind_speed': wind_speed,
                            'description': description
                        })

                    for date, forecasts in daily_forecasts.items():
                        temp_sum = sum(f['temperature'] for f in forecasts)
                        feels_like_sum = sum(f['feels_like'] for f in forecasts)
                        count = len(forecasts)
                        avg_temp = round(temp_sum / count)
                        avg_feels_like = round(feels_like_sum / count)

                        message += (
                            f"*Погода на {date}:*\n\n"
                            f"*Температура:* {avg_temp}°C\n"
                            f"*Ощущается как:* {avg_feels_like}°C\n"
                            f"*Влажность:* {forecasts[0]['humidity']}%\n"
                            f"*Давление:* {forecasts[0]['pressure']} мм рт. ст.\n"
                            f"*Скорость ветра:* {forecasts[0]['wind_speed']} м/с\n"
                            f"*Описание:* {forecasts[0]['description']}\n\n"
                        )

                    bot.send_message(chat_id, message, parse_mode="Markdown")
                    break
                else:
                    bot.send_message(chat_id, "Не удалось получить прогноз на неделю.")
                    break
            except Exception as e:
                print(f"Ошибка в попытке запроса: {e}")
                if attempt == retries - 1:
                    bot.send_message(chat_id, "Не удалось получить прогноз на неделю после нескольких попыток.")
    except Exception as e:
        print(f"Ошибка в send_forecast_weekly: {e}")
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на неделю. Попробуйте позже.")

# ---------- ПРОГНОЗ НА МЕСЯЦ -----------
from datetime import datetime, timedelta
from collections import defaultdict

# ---------- ПРОГНОЗ НА МЕСЯЦ -----------
# ---------- ПРОГНОЗ НА МЕСЯЦ -----------
import requests
from datetime import datetime, timedelta
import traceback

def send_forecast_monthly(chat_id, coords, url, days=31):
    try:
        params = {
            'lat': coords['latitude'],
            'lon': coords['longitude'],
            'appid': API_KEY,
            'units': 'metric',
            'lang': 'ru'
        }
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if response.status_code == 200:
            forecasts = data['list']
            message = "*Прогноз на месяц:*\n\n"

            # Получаем данные на месяц
            daily_forecasts = {}
            for forecast in forecasts:
                date_time = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S")
                date_str = date_time.strftime('%d.%m.%Y')  # Изменен формат даты на DD.MM.YYYY

                if date_str not in daily_forecasts:
                    daily_forecasts[date_str] = {
                        'temperature': round(forecast['main']['temp']),
                        'feels_like': round(forecast['main']['feels_like'])
                    }

            # Формируем сообщение
            for date, values in daily_forecasts.items():
                message += (
                    f"*{date}:*\n\n"
                    f"*Температура:* {values['temperature']}°C\n"
                    f"*Ощущается как:* {values['feels_like']}°C\n\n"
                )

            # Проверка на отсутствие данных и формирование диапазона
            unavailable_dates = []
            for date in pd.date_range(start=datetime.now(), periods=days).strftime('%d.%m.%Y'):
                if date not in daily_forecasts:
                    unavailable_dates.append(date)

            if unavailable_dates:
                start_date = unavailable_dates[0]
                end_date = unavailable_dates[-1]
                message += (f"*С {start_date} по {end_date}:*\n\n_" 
                             f"Данные недоступны из-за ограничений._\n\n")  # Курсив

            if message == "*Прогноз на месяц:*\n\n":
                message = "Нет доступного прогноза на месяц."

            bot.send_message(chat_id, message, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "Не удалось получить прогноз на месяц.")
    except Exception as e:
        print(f"Ошибка при отправке прогноза на месяц: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на месяц. Попробуйте позже.")

# ЦЕНЫ НА ТОПЛИВО

import threading

# Переменные для состояния пользователя и данных
user_state = {}
user_data = {}

os.makedirs(os.path.join('data base', 'azs'), exist_ok=True)

# Путь к файлу для сохранения данных
DATA_FILE_PATH = os.path.join('data base', 'city_for_the_price.json')

# Функция для загрузки данных пользователей
def load_citys_users_data():
    global user_data
    if os.path.exists(DATA_FILE_PATH):
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
    else:
        user_data = {}

# Функция для сохранения данных пользователей
def save_citys_users_data():
    with open(DATA_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)

# Загружаем данные пользователей при запуске
load_citys_users_data()

# Функция для создания имени файла на основе города и даты
def create_filename(city_code, date):
    date_str = date.strftime('%d_%m_%Y')
    return f"{city_code}_table_azs_data_{date_str}.json"

# Функция для сохранения данных в JSON
def save_data(city_code, fuel_prices):
    filename = f'{city_code}_table_azs_data.json'
    filepath = os.path.join('data base', 'azs', filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(fuel_prices, f, ensure_ascii=False, indent=4)

# Функция для загрузки сохранённых данных из JSON
def load_saved_data(city_code):
    filename = f'{city_code}_table_azs_data.json'
    filepath = os.path.join('data base', 'azs', filename)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

# Обновление функции для загрузки данных
def load_citys_users_data():
    global user_data
    if os.path.exists(DATA_FILE_PATH):
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
    else:
        user_data = {}

# Функция для сохранения данных городов пользователей в JSON
def save_citys_users_data():
    with open(DATA_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)

# Загружаем данные пользователей при запуске бота
load_citys_users_data()

# Функция для чтения городов и создания словаря для их URL
def load_cities():
    cities = {}
    try:
        with open('files/combined_cities.txt', 'r', encoding='utf-8') as file:
            for line in file:
                if '-' in line:  # Проверяем, что в строке есть дефис
                    city, city_code = line.strip().split(' - ')
                    cities[city.lower()] = city_code  # Приводим название города к нижнему регистру
    except FileNotFoundError:
        pass  # Если файл не найден, просто продолжаем
    return cities

# Загружаем города при запуске бота
cities_dict = load_cities()

# Функция для получения кода города на английском по его названию на русском
def get_city_code(city_name):
    # Здесь не нужно дополнительно приводить к нижнему регистру, так как он уже приведен в load_cities
    return cities_dict.get(city_name.lower())  # Приводим введённое название города к нижнему регистру

# Функция для создания имени файла на основе города и даты
def create_filename(city_code, date):
    date_str = date.strftime('%d_%m_%Y')  # Преобразуем дату в строку формата 'день_месяц_год'
    return f"{city_code}_table_azs_data_{date_str}.json"

# Функция для сохранения данных в JSON
def save_data(city_code, fuel_prices):
    filename = f'{city_code}_table_azs_data.json'  # Уникальный файл для каждого города
    filepath = os.path.join('data base', 'azs', filename)  # Указываем путь к папке

    # Сохраняем данные в файл, заменяя содержимое
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(fuel_prices, f, ensure_ascii=False, indent=4)

# Функция для загрузки сохранённых данных из JSON
def load_saved_data(city_code):
    filename = f'{city_code}_table_azs_data.json'  # Уникальный файл для каждого города
    filepath = os.path.join('data base', 'azs', filename)  # Указываем путь к папке
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

# Обработчик команды "Цены на топливо"
@bot.message_handler(func=lambda message: message.text == "Цены на топливо")
def fuel_prices_command(message):
    chat_id = message.chat.id
    load_citys_users_data()  # Загружаем данные перед использованием
    user_state[chat_id] = "choosing_city"  # Устанавливаем состояние выбора города

    str_chat_id = str(chat_id)

    # Создаем клавиатуру с кнопкой "В главное меню" и последними городами
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    if str_chat_id in user_data and 'recent_cities' in user_data[str_chat_id]:
        recent_cities = user_data[str_chat_id]['recent_cities']
        city_buttons = [types.KeyboardButton(city.capitalize()) for city in recent_cities]
        markup.row(*city_buttons)  # Все кнопки городов будут в одной строке
    else:
        pass  # Нет недавних городов

    markup.add(types.KeyboardButton("В главное меню"))

    # Отправляем сообщение с просьбой ввести город
    bot.send_message(chat_id, "Введите город или выберите из последних:", reply_markup=markup)
    # Регистрируем следующий шаг для обработки ввода города
    bot.register_next_step_handler(message, process_city_selection)
    
# Обработчик выбора города
# Обработчик выбора города
def process_city_selection(message):
    chat_id = message.chat.id
    str_chat_id = str(chat_id)

    if user_state.get(chat_id) != "choosing_city":
        bot.send_message(chat_id, "Пожалуйста, используйте доступные кнопки для навигации.")
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    city_name = message.text.strip().lower()  # Приводим к нижнему регистру
    cities = load_cities()  # Загружаем словарь городов
    
    city_code = get_city_code(city_name)  # Поиск кода города
    if city_code:
        # Убедимся, что данные о пользователе существуют
        if str_chat_id not in user_data:
            user_data[str_chat_id] = {'recent_cities': [], 'city_code': None}

        # Обновляем список последних городов
        update_recent_cities(str_chat_id, city_name)
        
        user_data[str_chat_id]['city_code'] = city_code  # Сохраняем новый код города
        save_citys_users_data()  # Сохраняем данные после обновления city_code
        show_fuel_price_menu(chat_id, city_code)
    else:
        bot.send_message(chat_id, "Город не найден. Пожалуйста, попробуйте еще раз.")
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(chat_id, "Введите город или выберите из последних:", reply_markup=markup)
        bot.register_next_step_handler(message, process_city_selection)

# Функция для обновления списка последних городов
# В функции update_recent_cities добавьте вызов сохранения данных
# Функция для обновления списка последних городов
def update_recent_cities(chat_id, city_name):
    # Убедитесь, что данные о пользователе существуют
    if chat_id not in user_data:
        user_data[chat_id] = {'recent_cities': [], 'city_code': None}

    # Извлекаем список последних городов
    recent_cities = user_data[chat_id].get('recent_cities', [])

    # Удаляем город, если он уже есть, и добавляем в конец
    if city_name in recent_cities:
        recent_cities.remove(city_name)
    elif len(recent_cities) >= 3:
        # Удаляем первый город, если уже 3 города
        recent_cities.pop(0)

    # Добавляем новый город в конец списка
    recent_cities.append(city_name)

    # Сохраняем обновлённые данные пользователей
    user_data[chat_id]['recent_cities'] = recent_cities
    save_citys_users_data()  # Сохраняем данные в файл

# Определяем доступные типы топлива
fuel_types = ["АИ-92", "АИ-95", "АИ-98", "АИ-100", "ДТ", "Газ"]

# Функция для создания клавиатуры с типами топлива
def show_fuel_price_menu(chat_id, city_code):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    
    row1 = [types.KeyboardButton(fuel_type) for fuel_type in fuel_types[:3]] 
    row2 = [types.KeyboardButton(fuel_type) for fuel_type in fuel_types[3:]] 
    row3 = [types.KeyboardButton("В главное меню")]
    
    markup.add(*row1, *row2, *row3)
    
    sent = bot.send_message(chat_id, "Выберите тип топлива для отображения актуальных цен:", reply_markup=markup)
    bot.register_next_step_handler(sent, lambda msg: process_fuel_price_selection(msg, city_code))

# Обработчик выбора топлива
def process_fuel_price_selection(message, city_code):
    chat_id = message.chat.id

    if chat_id not in user_data:
        user_data[chat_id] = {'city_code': city_code}

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    selected_fuel_type = message.text.strip().lower()

    fuel_type_mapping = {
        "аи-92": "АИ-92",
        "аи-95": "АИ-95",
        "аи-98": "АИ-98",
        "аи-100": "АИ-100",
        "дт": "ДТ",
        "газ": "Газ",
    }

    if selected_fuel_type not in fuel_type_mapping:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите тип топлива из предложенных вариантов.")
        bot.register_next_step_handler(sent, lambda msg: process_fuel_price_selection(msg, city_code))
        return

    actual_fuel_type = fuel_type_mapping[selected_fuel_type]

    try:
        # Проверяем наличие сохранённых данных или парсим сайт
        fuel_prices = process_city_fuel_data(city_code, actual_fuel_type)
        
        if not fuel_prices:
            raise ValueError("Нет данных по ценам.")

        brand_prices = {}
        for brand, fuel_type, price in fuel_prices:
            price = float(price)
            if brand not in brand_prices:
                brand_prices[brand] = []
            brand_prices[brand].append(price)

        averaged_prices = {brand: sum(prices) / len(prices) for brand, prices in brand_prices.items()}
        sorted_prices = sorted(averaged_prices.items(), key=lambda x: x[1])

        prices_message = "\n\n".join([f"{i + 1}. {brand} - {avg_price:.2f} руб./л" for i, (brand, avg_price) in enumerate(sorted_prices)])
        bot.send_message(chat_id, f"*Актуальные цены на {actual_fuel_type.upper()}:*\n\n{prices_message}", parse_mode='Markdown')

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        another_fuel_button = types.KeyboardButton("Посмотреть цены на другое топливо")
        choose_another_city_button = types.KeyboardButton("Выбрать другой город")
        main_menu_button = types.KeyboardButton("В главное меню")
        markup.add(another_fuel_button) 
        markup.add(choose_another_city_button)
        markup.add(main_menu_button)

        user_state[chat_id] = "next_action"
        sent = bot.send_message(chat_id, "Вы можете посмотреть цены на другое топливо или выбрать другой город.", reply_markup=markup)
        bot.register_next_step_handler(sent, process_next_action)

    except Exception as e:
        bot.send_message(chat_id, f"Ошибка получения цен: {e}\nПопробуйте выбрать другой тип топлива.")
        show_fuel_price_menu(chat_id, city_code)

# Обработчик следующих действий (посмотреть другое топливо или выбрать другой город)
def process_next_action(message):
    chat_id = message.chat.id
    text = message.text.strip().lower()

    if text == "посмотреть цены на другое топливо":
        city_code = user_data.get(chat_id, {}).get('city_code')
        if city_code:
            show_fuel_price_menu(chat_id, city_code)
        else:
            bot.send_message(chat_id, "Город не выбран. Пожалуйста, начните сначала.")
            return_to_menu(message)
    elif text == "выбрать другой город":
        user_state[chat_id] = "choosing_city"  # Устанавливаем состояние выбора города
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        # Добавляем кнопки с последними городами, если они есть
        if chat_id in user_data and 'recent_cities' in user_data[chat_id]:
            recent_cities = user_data[chat_id]['recent_cities']
            city_buttons = [types.KeyboardButton(city.capitalize()) for city in recent_cities]
            markup.row(*city_buttons)  # Все кнопки городов будут в одной строке

        # Добавляем кнопку "В главное меню" на отдельную строку
        markup.add(types.KeyboardButton("В главное меню"))

        bot.send_message(chat_id, "Введите название города или выберите из последних:", reply_markup=markup)
        bot.register_next_step_handler(message, process_city_selection)
    elif text == "в главное меню":
        return_to_menu(message)
    else:
        bot.send_message(chat_id, "Пожалуйста, выберите одно из предложенных действий.")
        bot.register_next_step_handler(message, process_next_action)

# Функция для обработки данных по всем видам топлива и их сохранения
def process_city_fuel_data(city_code, selected_fuel_type):
    today = datetime.now().date()
    saved_data = load_saved_data(city_code)

    # Проверяем дату файла
    filepath = os.path.join('data base', 'azs', f"{city_code}_table_azs_data.json")
    if saved_data:
        file_modification_time = datetime.fromtimestamp(os.path.getmtime(filepath)).date()
        if file_modification_time < today:  # Если файл устарел
            # Получаем новые данные
            all_fuel_prices = []
            for fuel_type in fuel_types:
                fuel_prices = get_fuel_prices_from_site(fuel_type, city_code)
                fuel_prices = remove_duplicate_prices(fuel_prices)
                all_fuel_prices.extend(fuel_prices)

            # Сохраняем новые данные
            save_data(city_code, all_fuel_prices)
            saved_data = all_fuel_prices  # Обновляем saved_data

    # Если данных нет, пытаемся их получить
    if not saved_data:
        all_fuel_prices = []
        for fuel_type in fuel_types:
            fuel_prices = get_fuel_prices_from_site(fuel_type, city_code)
            fuel_prices = remove_duplicate_prices(fuel_prices)
            all_fuel_prices.extend(fuel_prices)

        save_data(city_code, all_fuel_prices)
        saved_data = all_fuel_prices  # Возвращаем полученные данные

    # Фильтруем и возвращаем данные по выбранному типу топлива
    filtered_prices = [
        item for item in saved_data 
        if item[1].lower() == selected_fuel_type.lower() or
        (selected_fuel_type.lower() == "газ" and item[1].lower() == "газ спбт")
    ]
    return remove_duplicate_prices(filtered_prices)

# Обновлённая функция для удаления дублирующихся цен для каждой АЗС и каждого типа топлива
def remove_duplicate_prices(fuel_prices):
    unique_prices = {}
    for brand, fuel_type, price in fuel_prices:
        price = float(price)
        key = (brand, fuel_type)  # Используем комбинацию бренда и типа топлива как уникальный ключ
        if key not in unique_prices or price < unique_prices[key]:
            unique_prices[key] = price  # Сохраняем минимальную цену для каждого бренда и типа топлива
    return [(brand, fuel_type, price) for (brand, fuel_type), price in unique_prices.items()]

# Функция для парсинга данных с сайта
def get_fuel_prices_from_site(selected_fuel_type, city_code):
    url = f'https://azsprice.ru/benzin-{city_code}'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table')
    if not table:
        raise ValueError("Не найдена таблица с ценами.")

    fuel_prices = []

    rows = table.find_all('tr')
    for row in rows[1:]:
        columns = row.find_all('td')
        if len(columns) < 5:
            continue
        
        brand = columns[1].text.strip()
        fuel_type = columns[2].text.strip()
        today_price = clean_price(columns[3].text.strip())

        if fuel_type.lower() == selected_fuel_type.lower() or (fuel_type.lower() == "газ спбт" and selected_fuel_type.lower() == "газ"):
            fuel_prices.append((brand, fuel_type, today_price))
    
    return fuel_prices

# Функция для очистки цены
def clean_price(price):
    cleaned_price = ''.join([ch for ch in price if ch.isdigit() or ch == '.'])
    return cleaned_price

# Функция для проверки обновления и парсинга данных
def parse_fuel_prices():
    cities_to_parse = os.listdir(os.path.join('data base', 'azs'))  # Список городов для парсинга
    for city_code in cities_to_parse:
        city_code = city_code.replace('_table_azs_data.json', '')  # Убираем расширение для получения кода города
        saved_data = load_saved_data(city_code)
        
        today = datetime.now().date()
        if saved_data:
            file_modification_time = datetime.fromtimestamp(os.path.getmtime(os.path.join('data base', 'azs', f"{city_code}_table_azs_data.json"))).date()
            if file_modification_time >= today:
                print(f"Данные для города {city_code} уже обновлены сегодня. Пропускаем.")
                continue

        # Если файл устарел или не существует, парсим новые данные
        all_fuel_prices = []
        for fuel_type in fuel_types:
            fuel_prices = get_fuel_prices_from_site(fuel_type, city_code)
            all_fuel_prices.extend(fuel_prices)

        save_data(city_code, all_fuel_prices)
        print(f"Данные для города {city_code} успешно обновлены.")

# Функция планировщика
def schedule_parsing():
    while True:
        now = datetime.now()
        if now.hour == 23 and now.minute == 00:  # Запуск в 00:00
            parse_fuel_prices()
            time.sleep(60 * 5)  # Ожидание 5 минут перед следующим городом
        time.sleep(60)  # Проверка каждые 60 секунд

# Запуск планировщика в отдельном потоке
threading.Thread(target=schedule_parsing, daemon=True).start()


# Определение состояний
class States:
    ADDING_TRANSPORT = 1
    CONFIRMING_DELETE = 2

# Функции для работы с файлами
def save_transport_data(user_id, user_data):
    folder_path = "data base"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # Сохраняем данные о транспорте
    with open(os.path.join(folder_path, f"transport_{user_id}.json"), "w", encoding="utf-8") as file:
        json.dump(user_data, file, ensure_ascii=False, indent=4)

def load_transport_data(user_id):
    folder_path = "data base"  
    try:
        with open(os.path.join(folder_path, f"transport_{user_id}.json"), "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = []
    return data

# Хранение данных о транспорте в памяти
user_transport = {}

# Загрузка данных о транспорте при старте бота
def load_all_transport():
    users = os.listdir("data base")
    for user_file in users:
        if user_file.startswith("transport_"):
            user_id = user_file.split("_")[1].replace(".json", "")
            user_transport[user_id] = load_transport_data(user_id)

load_all_transport()

# Команда для управления транспортом
@bot.message_handler(func=lambda message: message.text == "Ваш транспорт")
def manage_transport(message):
    user_id = str(message.chat.id)
    
    # Создаем клавиатуру с тремя кнопками в первом ряду и двумя в следующих строках
    keyboard = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    
    # Добавляем три кнопки в первый ряд
    keyboard.add("Добавить транспорт", "Удалить транспорт", "Посмотреть транспорт")
    
    # Добавляем кнопки для возвращения в меню трат и в главное меню в следующих строках
    keyboard.add("Вернуться в меню трат и ремонтов")
    keyboard.add("В главное меню")
    
    bot.send_message(user_id, "Выберите действие:", reply_markup=keyboard)

# Функция для проверки наличия мультимедийных файлов
def check_media(message, user_id, next_step_handler=None, *args):
    if (message.photo or message.video or message.document or message.animation or 
        message.sticker or message.location or message.audio or 
        message.contact or message.voice or message.video_note):
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        if next_step_handler:
            bot.register_next_step_handler(message, next_step_handler, *args)  # Вернуться к следующему шагу
        return True
    return False

# Функция для создания новой клавиатуры
def create_transport_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    item_main_menu = types.KeyboardButton("В главное меню")
    item_return_transport = types.KeyboardButton("Вернуться в ваш транспорт")
    markup.add(item_return_transport)
    markup.add(item_main_menu)
    return markup

@bot.message_handler(func=lambda message: message.text == "Добавить транспорт")
def add_transport(message):
    user_id = str(message.chat.id)
    if check_media(message, user_id): return
    bot.send_message(user_id, "Введите марку транспорта:", reply_markup=create_transport_keyboard())
    bot.register_next_step_handler(message, process_brand)

def process_brand(message):
    user_id = str(message.chat.id)
    if check_media(message, user_id, process_brand): return

    # Обработка кнопок
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    brand = message.text
    bot.send_message(user_id, "Введите модель транспорта:", reply_markup=create_transport_keyboard())
    bot.register_next_step_handler(message, process_model, brand)

def process_model(message, brand):
    user_id = str(message.chat.id)
    if check_media(message, user_id, process_model, brand): return

    # Обработка кнопок
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    model = message.text
    bot.send_message(user_id, "Введите год транспорта:", reply_markup=create_transport_keyboard())
    bot.register_next_step_handler(message, process_year, brand, model)

def process_year(message, brand, model):
    user_id = str(message.chat.id)
    if check_media(message, user_id, process_year, brand, model): return

    # Обработка кнопок
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    # Проверка на корректность года
    try:
        year = int(message.text)
        if year < 1960 or year > 3000:  # Проверка диапазона
            raise ValueError("Год должен быть в диапазоне от 1960 г. до 3000 г.")
    except ValueError:
        bot.send_message(user_id, "Ошибка! Пожалуйста, введите корректный год (диапазон от 1960 г. до 3000 г.). Попробуйте снова.", reply_markup=create_transport_keyboard())
        bot.register_next_step_handler(message, process_year, brand, model)
        return

    bot.send_message(user_id, "Введите госномер:", reply_markup=create_transport_keyboard())
    bot.register_next_step_handler(message, process_license_plate, brand, model, year)

def process_license_plate(message, brand, model, year):
    user_id = str(message.chat.id)
    if check_media(message, user_id, process_license_plate, brand, model, year): return

    # Обработка кнопок
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    license_plate = message.text

    # Проверка на длину ГОС.НОМЕРА (8 или 9 символов)
    if len(license_plate) not in [8, 9]:
        bot.send_message(user_id, "Ошибка! Госномер должен содержать 8 или 9 символов. Попробуйте снова.", reply_markup=create_transport_keyboard())
        bot.register_next_step_handler(message, process_license_plate, brand, model, year)
        return

    # Сохраняем транспорт в память
    if user_id not in user_transport:
        user_transport[user_id] = []
    
    user_transport[user_id].append({"brand": brand, "model": model, "year": year, "license_plate": license_plate})
    save_transport_data(user_id, user_transport[user_id])  # Сохранение данных о транспорте
    
    bot.send_message(user_id, f"Транспорт добавлен: {brand} - {model} - {year} - {license_plate}", reply_markup=create_transport_keyboard())

    # Переход в меню "Ваш транспорт"
    manage_transport(message)

def delete_expenses_related_to_transport(user_id, transport):
    expenses_data = load_expense_data(user_id)  # Загрузите текущие расходы
    if user_id in expenses_data:
        updated_expenses = []
        for expense in expenses_data[user_id]['expenses']:
            # Проверка на совпадение транспорта
            if expense['transport']['brand'] != transport['brand'] or \
               expense['transport']['model'] != transport['model'] or \
               expense['transport']['year'] != transport['year']:
                updated_expenses.append(expense)

        # Обновляем данные о расходах
        expenses_data[user_id]['expenses'] = updated_expenses
        save_expense_data(user_id, expenses_data)  # Сохраняем обновленные данные

@bot.message_handler(func=lambda message: message.text == "Удалить транспорт")
def delete_transport(message):
    user_id = str(message.chat.id)
    if user_id in user_transport and user_transport[user_id]:
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        transport_list = user_transport[user_id]
        
        # Формирование списка транспорта для удаления
        for index, item in enumerate(transport_list, start=1):
            keyboard.add(f"{index}. {item['brand']} - {item['model']} - {item['year']} - {item['license_plate']}")
        
        # Добавление кнопок "Вернуться в меню трат и ремонтов" и "В главное меню"
        item_main_menu = types.KeyboardButton("В главное меню")
        item_return_transport = types.KeyboardButton("Вернуться в ваш транспорт")
        keyboard.add("Удалить весь транспорт")
        keyboard.add(item_return_transport)
        keyboard.add(item_main_menu)
        
        bot.send_message(user_id, "Выберите транспорт для удаления или вернитесь:", reply_markup=keyboard)
        bot.register_next_step_handler(message, process_transport_selection)
    else:
        bot.send_message(user_id, "У вас нет добавленного транспорта.")

def process_transport_selection(message):
    user_id = str(message.chat.id)
    selected_transport = message.text.strip()

    # Проверка на кнопки "Вернуться в меню трат и ремонтов" и "В главное меню"
    if selected_transport == "В главное меню":
        return_to_menu(message)
        return

    # Проверка на выбор "Удалить весь транспорт"
    if selected_transport == "Удалить весь транспорт":
        delete_all_transports(message)  # Переход к удалению всех транспортов
        return

    if message.text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    # Проверяем, выбрал ли пользователь транспорт из списка
    transport_list = user_transport.get(user_id, [])
    if transport_list:
        # Получаем возможные индексы транспорта
        possible_indices = [f"{i + 1}." for i in range(len(transport_list))]
        
        # Проверка, начинается ли текст с одного из возможных индексов
        if any(selected_transport.startswith(index) for index in possible_indices):
            index = int(selected_transport.split('.')[0]) - 1  # Определяем индекс транспорта
            
            if 0 <= index < len(transport_list):  # Проверяем, существует ли транспорт с таким индексом
                transport_to_delete = transport_list[index]
                
                # Отправка сообщения с подтверждением удаления
                bot.send_message(user_id, f"Вы точно хотите удалить данный транспорт: {transport_to_delete['brand']} - {transport_to_delete['model']} - {transport_to_delete['year']} - {transport_to_delete['license_plate']}?\nПожалуйста, введите 'ДА' для подтверждения или 'НЕТ' для отмены.", reply_markup=get_return_menu_keyboard())
                bot.register_next_step_handler(message, lambda msg: process_confirmation(msg, transport_to_delete))
            else:
                bot.send_message(user_id, "Неверный выбор. Попробуйте снова.")
                delete_transport(message)  # Возврат к выбору удаления транспорта
        else:
            bot.send_message(user_id, "Ошибка! Пожалуйста, выберите транспорт для удаления из списка.")
            delete_transport(message)  # Возврат к выбору удаления транспорта
    else:
        bot.send_message(user_id, "У вас нет добавленного транспорта.")

def process_confirmation(message, transport_to_delete):
    user_id = str(message.chat.id)
    confirmation = message.text.strip().upper()

    if confirmation == "ДА":
        if user_id in user_transport:
            user_transport[user_id].remove(transport_to_delete)  # Удаление элемента
            delete_expenses_related_to_transport(user_id, transport_to_delete)  # Удаление расходов, связанных с транспортом
            save_transport_data(user_id, user_transport[user_id])  # Сохранение после удаления
            bot.send_message(user_id, "Транспорт и связанные с ним траты успешно удалены.")
        else:
            bot.send_message(user_id, "Неверный выбор.")
    elif confirmation == "НЕТ":
        bot.send_message(user_id, "Удаление отменено.")
    else:
        bot.send_message(user_id, "Ошибка! Пожалуйста, введите 'ДА' для подтверждения или 'НЕТ' для отмены.")
        bot.register_next_step_handler(message, lambda msg: process_confirmation(msg, transport_to_delete))  # Ожидание повторного ввода

    manage_transport(message)

# Функция для создания клавиатуры с кнопками возврата
def get_return_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    item_main_menu = types.KeyboardButton("В главное меню")
    item_return_transport = types.KeyboardButton("Вернуться в ваш транспорт")
    markup.add(item_return_transport)
    markup.add(item_main_menu)
    return markup

@bot.message_handler(func=lambda message: message.text == "Удалить весь транспорт")
def delete_all_transports(message):
    user_id = str(message.chat.id)
    if user_id in user_transport and user_transport[user_id]:
        # Подтверждение удаления всех транспортов
        bot.send_message(user_id, "Вы уверены, что хотите удалить весь транспорт? Введите 'ДА' для подтверждения или 'НЕТ' для отмены.", reply_markup=get_return_menu_keyboard())
        bot.register_next_step_handler(message, process_delete_all_confirmation)
    else:
        bot.send_message(user_id, "У вас нет добавленного транспорта.")

def process_delete_all_confirmation(message):
    user_id = str(message.chat.id)
    confirmation = message.text.strip().upper()

    if confirmation == "ДА":
        if user_id in user_transport:
            # Удаляем все транспорты
            transports = user_transport[user_id]
            user_transport[user_id] = []  # Очищаем список
            save_transport_data(user_id, user_transport[user_id])  # Обновляем сохраненные данные

            # Удаляем все расходы, связанные с удаляемым транспортом
            for transport in transports:
                delete_expenses_related_to_transport(user_id, transport)

            bot.send_message(user_id, "Весь транспорт и связанные с ним траты успешно удалены.")
        else:
            bot.send_message(user_id, "У вас нет добавленного транспорта.")
    elif confirmation == "НЕТ":
        bot.send_message(user_id, "Удаление отменено.")
    else:
        bot.send_message(user_id, "Ошибка! Пожалуйста, введите 'ДА' для подтверждения или 'НЕТ' для отмены.")
        bot.register_next_step_handler(message, process_delete_all_confirmation)  # Ожидание повторного ввода

    manage_transport(message)

@bot.message_handler(func=lambda message: message.text == "Посмотреть транспорт")
def view_transport(message):
    user_id = str(message.chat.id)
    if user_id in user_transport and user_transport[user_id]:
        transport_list = user_transport[user_id]
        response = "\n\n".join([f"{index + 1}. {item['brand']} - {item['model']} - {item['year']} - {item['license_plate']}" for index, item in enumerate(transport_list)])
        bot.send_message(user_id, "Ваш транспорт:\n\n" + response)
    else:
        bot.send_message(user_id, "У вас нет добавленного транспорта.")


@bot.message_handler(func=lambda message: message.text == "Вернуться в ваш транспорт")
def return_to_transport_menu(message):
    manage_transport(message)  # Возвращаем пользователя в меню транспорта



ADMIN_USERNAME = "Alex"
ADMIN_PASSWORD = "hh1515az"
admin_sessions = set()

FEEDBACK_FILE_PATH = 'data base/feedback/feedback.json'

# Глобальные переменные для хранения статистики
active_users = {}  # {user_id: last_active_time}
total_users = set()   # Общее количество пользователей
function_usage = {
    'Статистика': 0,
    'Отзывы': 0,
    'Просмотр файлов БД': 0,
    'Просмотр всех файлов': 0,
}  # Статистика использования функций

INACTIVE_TIME = timedelta(minutes=1)  # Время для определения неактивного пользователя

def load_feedback():
    if os.path.exists(FEEDBACK_FILE_PATH):
        with open(FEEDBACK_FILE_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

def search_files_by_user_id(user_id):
    # Код поиска файлов по user_id
    pass

# Обновляем активность пользователя
def update_user_activity(user_id):
    active_users[user_id] = datetime.now()
    total_users.add(user_id)  # Добавляем пользователя в список всех, кто когда-либо использовал бот

# Проверяем активных пользователей
def get_active_users_count():
    now = datetime.now()
    return sum(1 for last_active in active_users.values() if now - last_active <= INACTIVE_TIME)

# Получаем статистику
def get_statistics():
    online_count = get_active_users_count()
    total_count = len(total_users)
    return online_count, total_count, function_usage

@bot.message_handler(commands=['admin'])
def handle_admin_login(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("В главное меню")
    bot.send_message(message.chat.id, "Введите логин:", reply_markup=markup)
    bot.register_next_step_handler(message, verify_username)

def verify_username(message):
    if message.text.lower() == "в главное меню":
        return_to_menu(message)
        return
    username = message.text
    bot.send_message(message.chat.id, "Введите пароль:")
    bot.register_next_step_handler(message, verify_password, username)

def verify_password(message, username):
    if message.text.lower() == "в главное меню":
        return_to_menu(message)
        return
    password = message.text
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        admin_sessions.add(message.chat.id)
        bot.send_message(message.chat.id, "Добро пожаловать в админ-панель!")
        show_admin_panel(message)
    else:
        bot.send_message(message.chat.id, "Неверные логин или пароль. Попробуйте снова.")
        handle_admin_login(message)

def show_admin_panel(message):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add('Просмотр файлов БД', 'Просмотр всех файлов', 'Просмотр отзывов', 'Статистика', 'Выход')
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Просмотр файлов БД' and message.chat.id in admin_sessions)
def view_db_files_prompt(message):
    # Код отображения файлов БД
    pass

@bot.message_handler(func=lambda message: message.text == 'Просмотр отзывов' and message.chat.id in admin_sessions)
def view_feedback(message):
    feedback_data = load_feedback()
    if feedback_data:
        feedbacks = "\n".join([f"{user_id}: {feedback}" for user_id, feedback in feedback_data.items()])
        bot.send_message(message.chat.id, f"Собранные отзывы:\n{feedbacks}")
    else:
        bot.send_message(message.chat.id, "Отзывы отсутствуют.")

@bot.message_handler(func=lambda message: message.text == 'Статистика' and message.chat.id in admin_sessions)
def show_statistics(message):
    online_count, total_count, function_usage = get_statistics()
    usage_summary = "\n".join([f"{func}: {count}" for func, count in function_usage.items()])
    
    response_message = (
        f"Пользователи онлайн: {online_count}\n"
        f"Всего пользователей: {total_count}\n\n"
        f"Использование функций:\n{usage_summary}"
    )
    bot.send_message(message.chat.id, response_message)

@bot.message_handler(func=lambda message: message.text == 'Выход' and message.chat.id in admin_sessions)
def logout(message):
    admin_sessions.discard(message.chat.id)
    return_to_menu(message)

@bot.message_handler(commands=['feedback'])
def get_feedback(message):
    update_user_activity(message.from_user.id)  # Обновляем активность пользователя
    bot.send_message(message.chat.id, "Напишите ваш отзыв:")
    bot.register_next_step_handler(message, save_feedback)

def save_feedback(message):
    feedback_data = load_feedback()
    user_id = str(message.from_user.id)
    feedback_data.setdefault(user_id, []).append(message.text)

    with open(FEEDBACK_FILE_PATH, 'w', encoding='utf-8') as file:
        json.dump(feedback_data, file, ensure_ascii=False, indent=4)
    bot.send_message(message.chat.id, "Спасибо за ваш отзыв!")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    update_user_activity(message.from_user.id)
    # Здесь можно добавить любые дополнительные обработки сообщений


# (16) --------------- КОД ДЛЯ "ФУНКЦИЯ ДЛЯ ОБНОВЛЕНИЙ ОТ TG" ---------------

# Функция для обработки повторных попыток
def start_bot_with_retries(retries=5, delay=5):
    attempt = 0
    while attempt < retries:
        try:
            print(f"Запуск попытки #{attempt + 1}")
            bot.polling(none_stop=True, interval=1, timeout=120, long_polling_timeout=120)
        except (ReadTimeout, ConnectionError) as e:
            print(f"Ошибка: {e}. Попытка {attempt + 1} из {retries}")
            attempt += 1
            if attempt < retries:
                print(f"Повторная попытка через {delay} секунд...")
                time.sleep(delay)  # Ожидание перед повторной попыткой
            else:
                print("Превышено количество попыток. Бот не смог запуститься.")
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            break

# Запуск бота с повторными попытками
start_bot_with_retries()

# Ваши обработчики сообщений остаются как обычно
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я бот.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, message.text)

# (17) --------------- КОД ДЛЯ "ЗАПУСК БОТА" ---------------
if __name__ == '__main__':
    bot.polling(none_stop=True, interval=1, timeout=120, long_polling_timeout=120)