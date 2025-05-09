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
from scipy.spatial import cKDTree
import threading
import csv
import shutil
import hashlib
from statistics import mean

# (2) --------------- ТОКЕН БОТА ---------------

bot = telebot.TeleBot("7519948621:AAGPoPBJrnL8-vZepAYvTmm18TipvvmLUoE")

# (3) --------------- СОХРАНЕНИЯ И ЗАГРУЗКА ДАННЫХ ПОЛЬЗОВАТЕЛЯ ---------------

# (3.1) --------------- СОХРАНЕНИЯ И ЗАГРУЗКА ДАННЫХ ПОЛЬЗОВАТЕЛЯ (ПОЕЗДКИ) ---------------

def save_data(user_id): 
    if user_id in user_trip_data:
        folder_path = "data base\\trip"  # или используйте прямой слэш "data base/trip"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        with open(os.path.join(folder_path, f"{user_id}_trip_data.json"), "w") as json_file:
            json.dump(user_trip_data[user_id], json_file)

# Псевдоданные - просто для примера
# В реальном случае данные приходят из пользовательского ввода или другого источника
user_trip_data = {}

# Функция для добавления поездки
def add_trip(user_id, trip):
    if user_id not in user_trip_data:
        user_trip_data[user_id] = []
    user_trip_data[user_id].append(trip)

# Функция для сохранения данных
def save_trip_data(user_id):
    folder_path = "data base\\trip"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Сохраняем данные поездок для конкретного пользователя
    file_path = os.path.join(folder_path, f"{user_id}_trip_data.json")
    with open(file_path, "w") as json_file:
        json.dump(user_trip_data.get(user_id, []), json_file, ensure_ascii=False, indent=4)

# Данные поездок для всех пользователей
user_trip_data = {}

# Путь к папке с данными
folder_path = "data base\\trip"

# Функция для загрузки данных для одного пользователя
def load_trip_data(user_id):
    file_path = os.path.join(folder_path, f"{user_id}_trip_data.json")
    if os.path.exists(file_path):
        with open(file_path, "r") as json_file:
            return json.load(json_file)
    else:
        return []  # Если данных нет, возвращаем пустой список

# Функция для загрузки данных для всех пользователей
def load_all_user_data():
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)  # Если папка не существует, создаем её
    for filename in os.listdir(folder_path):
        if filename.endswith("_trip_data.json"):
            user_id = filename.split("_")[0]  # Извлекаем user_id из имени файла
            user_trip_data[user_id] = load_trip_data(user_id)  # Загружаем данные для пользователя

# Функция для сохранения данных
def save_trip_data(user_id):
    if user_id in user_trip_data:
        file_path = os.path.join(folder_path, f"{user_id}_trip_data.json")
        with open(file_path, "w") as json_file:
            json.dump(user_trip_data[user_id], json_file, ensure_ascii=False, indent=4)

# Функция для добавления поездки
def add_trip(user_id, trip):
    if user_id not in user_trip_data:
        user_trip_data[user_id] = []
    user_trip_data[user_id].append(trip)

# Функция для сохранения данных всех пользователей при выходе
def save_all_trip_data():
    for user_id in user_trip_data:
        save_trip_data(user_id)

# Загружаем все данные при старте бота
load_all_user_data()



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
def restricted(func):
    """Декоратор для ограничения доступа заблокированным пользователям."""
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        username = message.from_user.username

        # Проверка по ID
        if is_user_blocked(user_id):
            bot.send_message(message.chat.id, "Вы заблокированы и не можете выполнять это действие.")
            return

        # Проверка по username
        if username and is_user_blocked(get_user_id_by_username(username)):
            bot.send_message(message.chat.id, "Вы заблокированы и не можете выполнять это действие.")
            return
        
        return func(message, *args, **kwargs)
    return wrapper

def track_user_activity(func):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        username = message.from_user.username if message.from_user.username else "Неизвестный пользователь"
        update_user_activity(user_id, username)  # Обновляем активность пользователя
        return func(message, *args, **kwargs)
    return wrapper

function_states = {
    'Расход топлива': True,
    'Траты и ремонты': True,
    'Найти транспорт': True,
    'Поиск мест': True,
    'Погода': True,
    'Код региона': True,
    'Цены на топливо': True,
    'Анти-радар': True,
    'Напоминания': True,
    'Коды OBD2': True
}

@bot.message_handler(commands=['start'])
@restricted
@track_user_activity
def start(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else "Неизвестный пользователь"

    # Сохраняем информацию о пользователе
    update_user_activity(user_id, username)

    # Создание кнопок меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Расход топлива")
    item2 = types.KeyboardButton("Траты и ремонты")
    item3 = types.KeyboardButton("Найти транспорт")
    item4 = types.KeyboardButton("Поиск мест")
    item5 = types.KeyboardButton("Погода")
    item6 = types.KeyboardButton("Код региона")
    item7 = types.KeyboardButton("Цены на топливо")
    item8 = types.KeyboardButton("Анти-радар")
    item9 = types.KeyboardButton("Напоминания")
    item10 = types.KeyboardButton("Коды OBD2")

    markup.add(item1, item2)
    markup.add(item3, item4)
    markup.add(item5, item7)
    markup.add(item6, item8)
    markup.add(item9, item10)

    bot.send_message(chat_id, "Добро пожаловать! Выберите действие из меню:", reply_markup=markup)

# (6) --------------- ОБРАБОТЧИК КОМАНДЫ /MAINMENU ---------------
@restricted
@track_user_activity
@bot.message_handler(func=lambda message: message.text == "В главное меню")
@bot.message_handler(commands=['mainmenu'])
def return_to_menu(message):
    start(message)

# (7) --------------- ДОПОЛНИТЕЛЬНОЙ ИНФОРМАЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЯ ---------------

@bot.message_handler(func=lambda message: message.text == "Сайт")
@bot.message_handler(commands=['website'])
def send_website_file(message):
    # Отправка гиперссылки на сайт
    bot.send_message(message.chat.id, "[Сайт CAR MANAGER](carmngrbot.com.swtest.ru)", parse_mode="Markdown")  # http://carmngrbot.com.swtest.ru/ # https://goo.su/5htqWmk
    
    # Закомментированная часть для отправки файла
    # try:
    #     with open('files/website.html', 'rb') as website_file:
    #         bot.send_document(chat_id, website_file)
    # except FileNotFoundError:
    #     bot.send_message(chat_id, "Извините, файл website не найден")

# (8) --------------- ОБРАБОТЧИК КОМАНДЫ "РАСХОД ТОПЛИВА"---------------

@bot.message_handler(func=lambda message: message.text == "Расход топлива")
@restricted
@track_user_activity
def handle_fuel_expense(message):

    if not function_states['Расход топлива']:
        bot.send_message(message.chat.id, "Эта функция временно недоступна.")
        return  # Завершаем выполнение функции, если функция деактивирована

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

# Пример функции, которая вызывается при выходе в меню расчета топлива
@bot.message_handler(func=lambda message: message.text == "Вернуться в меню расчета топлива")
@restricted
@track_user_activity
def restart_handler(message):
    user_id = message.chat.id

    # Сохраняем данные перед выходом в меню
    save_trip_data(user_id)

    # Загружаем данные для пользователя при возвращении в меню
    user_trip_data[user_id] = load_trip_data(user_id)

    # Возвращаемся в меню
    reset_and_start_over(message.chat.id)

def reset_and_start_over(chat_id):
    # Отправляем новое меню пользователю
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Рассчитать расход топлива")
    item2 = types.KeyboardButton("Посмотреть поездки")
    item3 = types.KeyboardButton("Удалить поездку")
    item4 = types.KeyboardButton("В главное меню")

    markup.add(item1)
    markup.add(item2, item3)
    markup.add(item4)

    bot.send_message(chat_id, "Вы вернулись в меню расчета топлива. Выберите действие:", reply_markup=markup)

# Когда бот завершает работу или пользователь выходит из меню, сохраняем все данные
# Например, при перезапуске или выходе:
save_all_trip_data()

# (9.3) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (ЗАГРУЗКА ДАННЫХ ПРИ /restart1) ---------------

def reset_user_data(user_id):
    if user_id not in user_trip_data:
        user_trip_data[user_id] = load_trip_data(user_id)
    bot.clear_step_handler_by_chat_id(user_id) 

# (9.4) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (ФУНКЦИЯ НАЧАЛЬНОГО МЕСТОПОЛОЖЕНИЯ) ---------------


@bot.message_handler(func=lambda message: message.text == "Рассчитать расход топлива")
@track_user_activity
@restricted
def calculate_fuel_cost_handler(message):
    chat_id = message.chat.id

    bot.clear_step_handler_by_chat_id(chat_id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Отправить геолокацию", request_location=True)
    item2 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item3 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)
    markup.add(item3)
    sent = bot.send_message(chat_id, "Введите начальное местоположение или отправьте геолокацию:", reply_markup=markup)
    reset_user_data(chat_id)  

    bot.register_next_step_handler(sent, process_start_location_step)
	

def process_start_location_step(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Отправить геолокацию", request_location=True)
    item2 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item3 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)
    markup.add(item3)

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
    item1 = types.KeyboardButton("Отправить геолокацию", request_location=True)
    item2 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item3 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)
    markup.add(item3)

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
        
        # Переход к выбору даты
        markup_date = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_calendar = types.KeyboardButton("Из календаря")
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
    markup.add(item1)
    markup.add(item2)

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
    user_code = trip_data[chat_id].get("user_code", "ru")  # Задаем код по умолчанию

    if message.text == "Пропустить ввод даты":
        selected_date = "Без даты"
        process_selected_date(message, selected_date)
        return

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text == "Из календаря":
        show_calendar(chat_id, user_code)
    elif message.text == "Ввести дату вручную":
        # Создаем разметку с двумя кнопками
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
        item2 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2)

        # Отправляем сообщение с кнопками и текстом для ввода даты вручную
        sent = bot.send_message(chat_id, "Введите дату поездки в формате ДД.ММ.ГГГГ:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_manual_date_step, distance)
    else:
        # Повторный запрос способа ввода даты, если ввод неверный
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_calendar = types.KeyboardButton("Из календаря")
        item_manual = types.KeyboardButton("Ввести дату вручную")
        item_skip = types.KeyboardButton("Пропустить ввод даты")
        markup.add(item_calendar, item_manual, item_skip)

        item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
        item2 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2)

        sent = bot.send_message(chat_id, "Выберите способ ввода даты:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_date_step, distance)

def process_date_input_step(message, distance):
    chat_id = message.chat.id
    date_input = message.text.strip()  # Получаем введенную дату

    # Проверка формата даты (ДД.ММ.ГГГГ)
    date_pattern = r"^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.\d{4}$"
    if re.match(date_pattern, date_input):
        selected_date = date_input
        process_selected_date(message, selected_date)  # Переход к следующему шагу с двумя аргументами
    else:
        # Если формат неверный, сообщаем пользователю и запрашиваем ввод снова
        bot.send_message(chat_id, "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")
        bot.register_next_step_handler(message, process_date_input_step, distance)

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

    if message.text == "Из календаря":
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
@restricted
@track_user_activity
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
        bot.edit_message_text(f"Вы выбрали дату: {selected_date}",
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
                bot.send_message(chat_id, f"Вы выбрали дату: {message.text}", reply_markup=markup)  # Отправляем сообщение с двумя кнопками
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
@restricted
@track_user_activity
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
        bot.edit_message_text(f"Вы выбрали дату: {selected_date}",
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
                bot.send_message(chat_id, f"Вы выбрали дату: {message.text}", reply_markup=markup)  # Отправляем сообщение с двумя кнопками
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
    row3 = [KeyboardButton("Вернуться в меню расчета топлива")]
    row4 = [KeyboardButton("В главное меню")]

    markup.add(*row1, *row2, *row3)
    markup.add(*row4)
    
    sent = bot.send_message(chat_id, "Выберите тип топлива:", reply_markup=markup)
    bot.register_next_step_handler(sent, process_fuel_type, date, distance)


def clean_price(price):
    # Удаляем все символы, кроме цифр и точек
    cleaned_price = re.sub(r'[^\d.]', '', price)
    if cleaned_price.count('.') > 1:
        cleaned_price = cleaned_price[:cleaned_price.find('.') + 1] + cleaned_price[cleaned_price.find('.') + 1:].replace('.', '')
    return cleaned_price

fuel_type_mapping = {
    "аи-92": "Аи-92",
    "аи-95": "Аи-95",
    "аи-98": "Аи-98",
    "аи-100": "Аи-100",
    "дт": "ДТ",
    "газ": "Газ СПБТ",
}

def get_average_fuel_price_from_files(fuel_type, directory="data base/azs"):
    fuel_prices = []

    # Приводим fuel_type к нижнему регистру для унификации
    fuel_type = fuel_type.lower()

    # Проверяем, существует ли папка
    if not os.path.exists(directory):
        return None

    # Перебираем все файлы в папке
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            file_path = os.path.join(directory, filename)

            # Открываем и читаем файл JSON
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    data = json.load(file)

                    # Перебираем записи в файле и находим нужные по типу топлива
                    for entry in data:
                        if len(entry) == 3:  # Проверка структуры данных
                            company, fuel, price = entry
                            # Приводим fuel к нижнему регистру и сравниваем с введенным пользователем
                            if fuel.lower() == fuel_type:
                                try:
                                    price = float(price)
                                    fuel_prices.append(price)
                                except ValueError:
                                    continue  # Если цена не может быть преобразована в число, пропускаем
            except Exception as e:
                pass  # Игнорируем ошибку при чтении файла

    # Если есть собранные цены, возвращаем среднее значение
    if fuel_prices:
        average_price = sum(fuel_prices) / len(fuel_prices)
        return average_price
    else:
        return None


def get_average_fuel_prices(city_code='default_city_code'):
    url = f'https://azsprice.ru/benzin-{city_code}'  # Замените на подходящий URL с использованием city_code
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Проверка на успешный статус ответа
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.find('table')
        if not table:
            raise ValueError("Не найдена таблица с ценами")
        
        fuel_prices = {}
        rows = table.find_all('tr')
        
        for row in rows[1:]:  # Пропускаем заголовок таблицы
            columns = row.find_all('td')
            if len(columns) < 5:
                continue
            
            fuel_type = columns[2].text.strip()  # Марка топлива
            today_price = clean_price(columns[3].text.strip())  # Цена на топливо
            
            if today_price:
                try:
                    price = float(today_price)
                    if fuel_type not in fuel_prices:
                        fuel_prices[fuel_type] = []
                    fuel_prices[fuel_type].append(price)
                except ValueError:
                    pass  # Игнорируем ошибки преобразования цены

        average_prices = {fuel: sum(prices) / len(prices) for fuel, prices in fuel_prices.items()}
        return average_prices
    
    except (requests.RequestException, ValueError) as e:
        return None  # Вернем None в случае ошибки


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
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
        item2 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        markup.add(item2)

        sent = bot.send_message(chat_id, "Пожалуйста, введите цену за литр топлива:", reply_markup=markup)
        bot.register_next_step_handler(sent, process_price_per_liter_step, date, distance, fuel_type)
    
    elif message.text == "Использовать актуальную цену":
        # Пытаемся получить цену с сайта
        fuel_prices = get_average_fuel_prices(city_code="cheboksary")
        
        if fuel_prices:  # Если сайт доступен и данные получены
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
            item2 = types.KeyboardButton("В главное меню")
            markup.add(item1)
            markup.add(item2)
            
            if fuel_type.lower() in fuel_prices:  # Если выбранный тип топлива существует
                price = fuel_prices[fuel_type.lower()]
                bot.send_message(chat_id, f"Актуальная средняя цена на {fuel_type.upper()} по РФ: {price:.2f} руб./л.", reply_markup=markup)
                sent = bot.send_message(chat_id, "Введите расход топлива на 100 км:", reply_markup=markup)
                bot.register_next_step_handler(sent, process_fuel_consumption_step, date, distance, fuel_type, price)
            else:
                # Если для выбранного топлива нет данных на сайте, сразу переходим к проверке файлов
                price_from_files = get_average_fuel_price_from_files(fuel_type, directory="data base/azs")
                
                if price_from_files:  # Если цена найдена в файлах
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
                    item2 = types.KeyboardButton("В главное меню")
                    markup.add(item1)
                    markup.add(item2)
                    
                    bot.send_message(chat_id, f"Актуальная средняя цена на {fuel_type.upper()} по РФ: {price_from_files:.2f} руб./л.", reply_markup=markup)
                    sent = bot.send_message(chat_id, "Введите расход топлива на 100 км:", reply_markup=markup)
                    bot.register_next_step_handler(sent, process_fuel_consumption_step, date, distance, fuel_type, price_from_files)
                else:
                    # Если нет данных в файлах, запрашиваем цену вручную
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
                    item2 = types.KeyboardButton("В главное меню")
                    markup.add(item1)
                    markup.add(item2)
                    sent = bot.send_message(chat_id, f"Для выбранного топлива '{fuel_type}' данных нет. Пожалуйста, введите цену", reply_markup=markup)
                    bot.register_next_step_handler(sent, process_price_per_liter_step, date, distance, fuel_type)
        
        else:  # Если сайт недоступен
            # Получаем цены из файлов
            price_from_files = get_average_fuel_price_from_files(fuel_type, directory="data base/azs")
            
            if price_from_files:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
                item2 = types.KeyboardButton("В главное меню")
                markup.add(item1)
                markup.add(item2)
                
                bot.send_message(chat_id, f"Актуальная средняя цена на {fuel_type.upper()} по РФ: {price_from_files:.2f} руб./л.", reply_markup=markup)
                sent = bot.send_message(chat_id, "Введите расход топлива на 100 км:", reply_markup=markup)
                bot.register_next_step_handler(sent, process_fuel_consumption_step, date, distance, fuel_type, price_from_files)
            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item1 = types.KeyboardButton("Вернуться в меню расчета топлива")
                item2 = types.KeyboardButton("В главное меню")
                markup.add(item1)
                markup.add(item2)
                sent = bot.send_message(chat_id, f"Для выбранного топлива '{fuel_type}' данных нет. Пожалуйста, введите цену", reply_markup=markup)
                bot.register_next_step_handler(sent, process_price_per_liter_step, date, distance, fuel_type)
    
    elif message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(chat_id)
    elif message.text == "В главное меню":
        return_to_menu(message)
    else:
        sent = bot.send_message(chat_id, "Пожалуйста, выберите один из предложенных вариантов")
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
    summary_message = "🚗 *ИНФОРМАЦИЯ О ПОЕЗДКЕ* 🚗\n"
    summary_message += "-------------------------------------------------------------\n"
    summary_message += f"📍 *Начальное местоположение:*\n{start_location['address']}\n"
    summary_message += f"🏁 *Конечное местоположение:*\n{end_location['address']}\n"
    summary_message += f"🗓️ *Дата поездки:* {date}\n"
    summary_message += f"📏 *Расстояние:* {distance:.2f} км\n"
    summary_message += f"⛽ *Тип топлива:* {fuel_type}\n"
    summary_message += f"💵 *Цена топлива за литр:* {price_per_liter:.2f} руб.\n"
    summary_message += f"⚙️ *Расход топлива на 100 км:* {fuel_consumption} л.\n"
    summary_message += f"👥 *Количество пассажиров:* {passengers}\n"
    summary_message += "-------------------------------------------------------------\n"
    summary_message += f"🛢️ *ПОТРАЧЕНО ЛИТРОВ ТОПЛИВА:* {fuel_spent:.2f} л.\n"
    summary_message += f"💰 *СТОИМОСТЬ ТОПЛИВА ДЛЯ ПОЕЗДКИ:* {fuel_cost:.2f} руб.\n"
    summary_message += f"👤 *СТОИМОСТЬ ТОПЛИВА НА ЧЕЛОВЕКА:* {fuel_cost_per_person:.2f} руб.\n"
    summary_message += f"[ССЫЛКА НА МАРШРУТ]({short_url})\n"

    summary_message = summary_message.replace('\n', '\n\n')
    bot.clear_step_handler_by_chat_id(chat_id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Сохранить поездку")
    item2 = types.KeyboardButton("Вернуться в меню расчета топлива")
    item3 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)
    markup.add(item3)

    bot.send_message(chat_id, summary_message, reply_markup=markup, parse_mode="Markdown")


def update_excel_file(user_id):
    # Путь к папке с файлами Excel
    folder_path = "data base/trip/excel"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    file_path = os.path.join(folder_path, f"{user_id}_trips.xlsx")

    # Проверяем и создаем файл с заголовками
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=[
            "Дата", "Начальное местоположение", "Конечное местоположение",
            "Расстояние (км)", "Тип топлива", "Цена топлива (руб/л)",
            "Расход топлива (л/100 км)", "Количество пассажиров",
            "Потрачено литров", "Стоимость топлива (руб)", 
            "Стоимость на человека (руб)", "Ссылка на маршрут"
        ])
        df.to_excel(file_path, index=False)
    
    # Обновляем данные файла Excel
    df = pd.read_excel(file_path)
    trips = user_trip_data.get(user_id, [])
    trip_records = [
        [
            trip['start_location']['address'], trip['end_location']['address'], trip['date'],
            trip['distance'], trip['fuel_type'], trip['price_per_liter'], trip['fuel_consumption'], 
            trip['passengers'], trip['fuel_spent'], trip['fuel_cost'], trip['fuel_cost_per_person'], 
            trip.get('route_link', "Нет ссылки")
        ] for trip in trips
    ]
    df = pd.DataFrame(trip_records, columns=df.columns)
    df.to_excel(file_path, index=False)

    # Устанавливаем стилизацию Excel
    workbook = load_workbook(file_path)
    worksheet = workbook.active
    for column in worksheet.columns:
        max_length = max(len(str(cell.value)) for cell in column if cell.value) + 2
        worksheet.column_dimensions[column[0].column_letter].width = max_length
    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(horizontal='center', vertical='center')
    thick_border = Border(left=Side(style='thick'), right=Side(style='thick'), 
                          top=Side(style='thick'), bottom=Side(style='thick'))
    for row in worksheet.iter_rows(min_row=2, min_col=9, max_col=12):
        for cell in row:
            cell.border = thick_border
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
    # Путь к папке с файлами Excel
    directory = "data base/trip/excel"
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, f"{user_id}_trips.xlsx")

    # Создаем и обновляем файл Excel для конкретной поездки
    new_trip_data = {
        "Начальное местоположение": trip['start_location']['address'],
        "Конечное местоположение": trip['end_location']['address'],
        "Дата": trip['date'],
        "Расстояние (км)": round(trip.get('distance', None), 2),
        "Тип топлива": trip.get('fuel_type', None),
        "Цена топлива (руб/л)": round(trip.get('price_per_liter', None), 2),
        "Расход топлива (л/100 км)": round(trip.get('fuel_consumption', None), 2),
        "Количество пассажиров": trip.get('passengers', None),
        "Потрачено литров": round(trip.get('fuel_spent', None), 2),
        "Стоимость топлива (руб)": round(trip.get('fuel_cost', None), 2),
        "Стоимость на человека (руб)": round(trip.get('fuel_cost_per_person', None), 2),
        "Ссылка на маршрут": trip.get('route_link', None)
    }
    new_trip_df = pd.DataFrame([new_trip_data])

    if os.path.exists(file_path):
        existing_data = pd.read_excel(file_path).dropna(axis=1, how='all')
        updated_data = pd.concat([existing_data, new_trip_df], ignore_index=True)
    else:
        updated_data = new_trip_df

    updated_data.to_excel(file_path, index=False)
    workbook = load_workbook(file_path)
    worksheet = workbook.active
    for column in worksheet.columns:
        max_length = max(len(str(cell.value)) for cell in column if cell.value) + 2
        worksheet.column_dimensions[column[0].column_letter].width = max_length
    for row in worksheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(horizontal="center", vertical="center")
    thick_border = Border(left=Side(style='thick'), right=Side(style='thick'),
                          top=Side(style='thick'), bottom=Side(style='thick'))
    for row in worksheet.iter_rows(min_col=worksheet.max_column-3, max_col=worksheet.max_column):
        for cell in row:
            cell.border = thick_border
    workbook.save(file_path)



# (9.14) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (КОМАНДА "СОХРАНИТЬ ПОЕЗДКУ") ---------------

@bot.message_handler(func=lambda message: message.text == "Сохранить поездку")
@restricted
@track_user_activity
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
@restricted
@track_user_activity
@bot.message_handler(commands=['mainmenu'])
@restricted
@track_user_activity
def return_to_menu(message):
    user_id = message.chat.id
    if user_id in temporary_trip_data:
        temporary_trip_data[user_id] = []
    start(message)

# # (9.16) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (КОМАНДА "ВЕРНУТЬСЯ В МЕНЮ РАСЧЕТА ТОПЛИВА   ВРЕМЕННЫХ ДАННЫХ") ---------------

@bot.message_handler(func=lambda message: message.text == "Вернуться в меню расчета топлива")
@restricted
@track_user_activity
def restart_handler(message):
    user_id = message.chat.id

    # Убедитесь, что при возвращении в меню расчета топлива, данные не удаляются
    # Например, сохраняем данные перед сбросом, если это необходимо
    if user_id in user_trip_data:
        # Сохранить данные, прежде чем сбросить, если это требуется
        save_trip_data(user_id, user_trip_data[user_id])

    # Теперь вызываем reset, если это действительно нужно
    reset_and_start_over(user_id)

    # Загружаем поездки (не сбрасывая их)
    user_trip_data[user_id] = load_trip_data(user_id)

    # Возвращаем пользователя в меню расчета топлива
    reset_and_start_over(message)

# (9.17) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (КОМАНДА "ПОСМОТРЕТЬ ПОЕЗДКИ") ---------------

@bot.message_handler(func=lambda message: message.text == "Посмотреть поездки")
@restricted
@track_user_activity
def view_trips(message):
    user_id = message.chat.id
    trips = load_trip_data(user_id)  # Загрузим поездки из базы данных

    if trips:
        # Создаем кнопки для выбора поездок
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        buttons = []

        for i, trip in enumerate(trips, start=1):
            start_address = trip['start_location']['address']
            end_address = trip['end_location']['address']
            date = trip['date'] if trip['date'] != "Без даты" else "Без даты"  # Обрабатываем специальное значение
            button_text = f"№{i}. {date}"
            buttons.append(types.KeyboardButton(button_text))

            # Разделяем кнопки на несколько рядов, чтобы было удобнее
            if len(buttons) == 3 or i == len(trips):
                markup.row(*buttons)
                buttons = []  # Очищаем список для следующего ряда

        # Добавляем дополнительные кнопки
        markup.add("Посмотреть в Excel")
        markup.add("Вернуться в меню расчета топлива")
        markup.add("В главное меню")

        # Отправляем сообщение с кнопками
        bot.send_message(user_id, "Выберите поездку для просмотра:", reply_markup=markup)
    else:
        bot.send_message(user_id, "У вас нет сохраненных поездок")

@bot.message_handler(func=lambda message: message.text == "Посмотреть в Excel")
@restricted
@track_user_activity
def send_excel_file(message):
    user_id = message.chat.id
    excel_file_path = f"data base/trip/excel/{user_id}_trips.xlsx"

    if os.path.exists(excel_file_path):
        with open(excel_file_path, 'rb') as excel_file:
            bot.send_document(user_id, excel_file)
    else:
        bot.send_message(user_id, "Файл Excel не найден. Убедитесь, что у вас есть сохраненные поездки.")

@bot.message_handler(func=lambda message: message.text and re.match(r"№\d+\.\s*\d{2}\.\d{2}\.\d{4}|№\d+\.\s*Без даты", message.text))
@restricted
@track_user_activity
def show_trip_details(message):
    user_id = message.chat.id
    trips = load_trip_data(user_id)  # Загружаем поездки для пользователя

    try:
        # Извлекаем номер поездки из сообщения
        match = re.match(r"№(\d+)\.\s*(\d{2}\.\d{2}\.\d{4}|Без даты)", message.text)
        if match:
            trip_index = int(match.group(1)) - 1  # Получаем индекс поездки
            if 0 <= trip_index < len(trips):  # Проверка на корректность индекса
                trip = trips[trip_index]

                # Формируем сообщение с данными поездки
                start_address = trip['start_location']['address']
                end_address = trip['end_location']['address']
                date = trip['date'] if trip['date'] != "Без даты" else "Без даты"  # Обработка "Без даты"
                summary_message = f"*ИТОГОВЫЕ ДАННЫЕ ПОЕЗДКИ* *{trip_index + 1}* \n\n"
                summary_message += "-------------------------------------------------------------\n\n"
                summary_message += f"📍 *Начальное местоположение:*\n\n{start_address}\n\n"
                summary_message += f"🏁 *Конечное местоположение:*\n\n{end_address}\n\n"
                summary_message += f"🗓️ *Дата поездки:* {date}\n\n"
                summary_message += f"📏 *Расстояние:* {trip['distance']:.2f} км.\n\n"
                summary_message += f"⛽ *Тип топлива:* {trip['fuel_type']}\n\n"
                summary_message += f"💵 *Цена топлива за литр:* {trip['price_per_liter']:.2f} руб.\n\n"
                summary_message += f"⚙️ *Расход топлива на 100 км:* {trip['fuel_consumption']} л.\n\n"
                summary_message += f"👥 *Количество пассажиров:* {trip['passengers']}\n\n"
                summary_message += "-------------------------------------------------------------\n\n"
                summary_message += f"🛢️ *ПОТРАЧЕНО ЛИТРОВ ТОПЛИВА:* {trip['fuel_spent']:.2f} л.\n\n"
                summary_message += f"💰 *СТОИМОСТЬ ТОПЛИВА ДЛЯ ПОЕЗДКИ:* {trip['fuel_cost']:.2f} руб.\n\n"
                summary_message += f"👤 *СТОИМОСТЬ ТОПЛИВА НА ЧЕЛОВЕКА:* {trip['fuel_cost_per_person']:.2f} руб.\n\n"

                # Проверяем, есть ли 'route_link' в данных поездки
                if 'route_link' in trip:
                    summary_message += f"[ССЫЛКА НА МАРШРУТ]({trip['route_link']})\n\n"
                else:
                    summary_message += "Ссылка на маршрут недоступна.\n\n"

                # Отправляем подробную информацию о поездке
                bot.send_message(user_id, summary_message, parse_mode="Markdown")

                # Оставляем клавиатуру с кнопками после просмотра поездки
                markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add("Посмотреть другие поездки")
                markup.add("Вернуться в меню расчета топлива")
                markup.add("В главное меню")

                bot.send_message(user_id, "Вы можете посмотреть другие поездки или вернуться в меню.", reply_markup=markup)

            else:
                bot.send_message(user_id, "Поездка с таким номером не найдена. Попробуйте снова.")
        else:
            bot.send_message(user_id, "Ошибка при выборе поездки. Попробуйте снова.")

    except (IndexError, ValueError) as e:
        print(f"Error while processing trip data: {e}")
        bot.send_message(user_id, "Ошибка при обработке данных. Попробуйте снова.")

# Обработчик для кнопки "Посмотреть другие поездки"
@bot.message_handler(func=lambda message: message.text == "Посмотреть другие поездки")
@restricted
@track_user_activity

def view_other_trips(message):
    view_trips(message)  # Вызываем функцию для повторного отображения списка поездок

# # Обработчики для кнопок "Вернуться в меню расчета топлива" и "В главное меню"
# @bot.message_handler(func=lambda message: message.text == "Вернуться в меню расчета топлива")
# @restricted
# @track_user_activity

# def return_to_fuel_calc_menu(message):
#     chat_id = message.chat.id
#     reset_and_start_over(chat_id)  # Ваша функция для сброса и возвращения в меню расчета топлива
#     bot.send_message(chat_id, "Вы вернулись в меню расчета топлива", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: message.text == "В главное меню")
@restricted
@track_user_activity
def return_to_main_menu(message):
    chat_id = message.chat.id
    return_to_menu(message)  # Ваша функция для возврата в главное меню
    bot.send_message(chat_id, "Вы вернулись в главное меню.", reply_markup=types.ReplyKeyboardRemove())

# (9.18) --------------- КОД ДЛЯ "РАСХОД ТОПЛИВА" (КОМАНДА "УДАЛИТЬ ПОЕЗДКУ") ---------------

@bot.message_handler(func=lambda message: message.text == "Удалить поездку")
@restricted
@track_user_activity
def ask_for_trip_to_delete(message):
    user_id = message.chat.id

    if user_id in user_trip_data:
        if user_trip_data[user_id]:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            buttons = []

            # Изменяем создание кнопок для отображения номера и даты поездки
            for i, trip in enumerate(user_trip_data[user_id], start=1):
                trip_date = trip.get('date', 'Дата не указана')  # Получаем дату поездки
                button_text = f"№{i}. {trip_date}"  # Создаем текст кнопки с номером и датой
                buttons.append(types.KeyboardButton(button_text))

                # Добавляем кнопку в ряд по 3
                if len(buttons) == 3 or i == len(user_trip_data[user_id]):
                    markup.row(*buttons)
                    buttons = []  # Очистить список для следующего ряда

            # Добавляем дополнительные кнопки
            markup.add(types.KeyboardButton("Удалить все поездки"))
            markup.add(types.KeyboardButton("Вернуться в меню расчета топлива"))
            markup.add(types.KeyboardButton("В главное меню"))

            bot.send_message(user_id, "Выберите номер поездки для удаления или удалите все:", reply_markup=markup)
            bot.register_next_step_handler(message, confirm_trip_deletion)
        else:
            bot.send_message(user_id, "У вас нет поездок для удаления")
    else:
        bot.send_message(user_id, "У вас нет сохраненных поездок")

def confirm_trip_deletion(message):
    user_id = message.chat.id

    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text == "Удалить все поездки":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("Вернуться в меню расчета топлива"))
        markup.add(types.KeyboardButton("В главное меню"))
        
        bot.send_message(
            user_id,
            "*Вы уверены, что хотите удалить все поездки?*\n\nПожалуйста, введите *ДА* для подтверждения или *НЕТ* для отмены",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, confirm_delete_all)
        return

    # Проверяем, соответствует ли текст кнопки формату "№N. дата"
    if message.text.startswith("№") and "." in message.text:
        try:
            trip_number = int(message.text.split(".")[0][1:])  # Извлекаем номер поездки
            if 1 <= trip_number <= len(user_trip_data[user_id]):
                deleted_trip = user_trip_data[user_id].pop(trip_number - 1)
                bot.send_message(user_id, f"Поездка номер {trip_number} успешно удалена")
                
                # Обновляем Excel файл
                update_excel_file(user_id)

            else:
                bot.send_message(user_id, "Неверный номер поездки. Пожалуйста, укажите корректный номер")
        except ValueError:
            bot.send_message(user_id, "Произошла ошибка при обработке номера поездки")
    else:
        bot.send_message(user_id, "Пожалуйста, выберите номер поездки для удаления с помощью кнопок")

    reset_and_start_over(user_id)

# Функция для подтверждения удаления всех поездок
def confirm_delete_all(message):
    user_id = message.chat.id
    
    if message.text is None:
        bot.send_message(user_id, "Пожалуйста, отправьте текстовое сообщение")
        bot.register_next_step_handler(message, confirm_delete_all)
        return

    # Проверяем нажатие на кнопки "Вернуться в меню расчета топлива" и "В главное меню"
    if message.text == "Вернуться в меню расчета топлива":
        reset_and_start_over(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    user_response = message.text.lower()

    if user_response == "да":
        if user_id in user_trip_data and user_trip_data[user_id]:
            user_trip_data[user_id].clear()
            bot.send_message(user_id, "Все поездки были успешно удалены")
            # Очистка Excel файла
            update_excel_file(user_id)
        else:
            bot.send_message(user_id, "У вас нет поездок для удаления")
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
        bot.send_message(user_id, "Удаление всех поездок отменено")
        reset_and_start_over(user_id)
    else:
        bot.send_message(user_id, "Пожалуйста, ответьте *ДА* для подтверждения или *НЕТ* для отмены", parse_mode="Markdown")
        bot.register_next_step_handler(message, confirm_delete_all)

# (10) --------------- КОД ДЛЯ "ТРАТ" ---------------

# (10.1) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "ТРАТЫ И РЕМОНТЫ") ---------------

@bot.message_handler(func=lambda message: message.text == "Траты и ремонты")
@restricted
@track_user_activity
def handle_expenses_and_repairs(message):
    if not function_states['Траты и ремонты']:
        bot.send_message(message.chat.id, "Эта функция временно недоступна.")
        return  # Завершаем выполнение функции, если функция деактивирована

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
@restricted
@track_user_activity
@bot.message_handler(commands=['restart2'])
@restricted
@track_user_activity
def return_to_menu_2(message):
    user_id = message.from_user.id
    send_menu(user_id)

# (10.5) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "ЗАПИСАТЬ ТРАТУ") ---------------

# Обработка данных о расходах
def save_expense_data(user_id, user_data, selected_transport=None):
    folder_path = os.path.join("data base", "expense")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    file_path = os.path.join(folder_path, f"{user_id}_expenses.json")

    # Загружаем текущие данные
    current_data = load_expense_data(user_id)

    # Сохраняем категории и расходы, не трогая другие данные
    user_data["user_categories"] = user_data.get("user_categories", current_data.get("user_categories", []))
    user_data["expenses"] = current_data.get("expenses", [])

    # Сохраняем только, если новый транспорт был передан
    if selected_transport is not None:
        user_data["selected_transport"] = selected_transport

    # Запись данных в файл
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(user_data, file, ensure_ascii=False, indent=4)

def load_expense_data(user_id):
    folder_path = os.path.join("data base", "expense")
    file_path = os.path.join(folder_path, f"{user_id}_expenses.json")
    
    if not os.path.exists(file_path):
        return {"user_categories": [], "selected_transport": "", "expenses": []}

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, ValueError) as e:
        print("Ошибка загрузки данных:", e)
        data = {"user_categories": [], "selected_transport": "", "expenses": []}
    
    return data


def get_user_categories(user_id):
    data = load_expense_data(user_id)
    default_categories = ["Без категории", "АЗС", "Мойка", "Парковка", "Платная дорога", "Страховка", "Штрафы"]
    user_categories = data.get("user_categories", [])
    return default_categories + user_categories

def add_user_category(user_id, new_category):
    data = load_expense_data(user_id)
    
    # Проверяем, есть ли категория, и добавляем её
    if "user_categories" not in data:
        data["user_categories"] = []
    if new_category not in data["user_categories"]:
        data["user_categories"].append(new_category)

    # Сохраняем обновленные данные
    save_expense_data(user_id, data)  # Теперь данные категорий будут сохранены

def remove_user_category(user_id, category_to_remove, selected_transport=""):
    data = load_expense_data(user_id)
    if "user_categories" in data and category_to_remove in data["user_categories"]:
        data["user_categories"].remove(category_to_remove)
        save_expense_data(user_id, data, selected_transport)

def get_user_transport_keyboard(user_id):
    transports = user_transport.get(str(user_id), [])  # Приведение к строке для совместимости
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Добавляем кнопки транспорта
    for i in range(0, len(transports), 2):
        transport_buttons = [
            types.KeyboardButton(f"{transport['brand']} {transport['model']} ({transport['license_plate']})")
            for transport in transports[i:i+2]
        ]
        markup.row(*transport_buttons)

    markup.add(types.KeyboardButton("Добавить транспорт"))
    return markup

# Основная функция для записи траты
@bot.message_handler(func=lambda message: message.text == "Записать трату")
def record_expense(message):
    user_id = message.from_user.id

    # Обработка мультимедийных файлов
    if contains_media(message):
        sent = bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(sent, record_expense)
        return

    markup = get_user_transport_keyboard(str(user_id))
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Выберите транспорт для записи траты:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection_for_expense)

def handle_transport_selection_for_expense(message):
    user_id = message.from_user.id

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
        formatted_transport = f"{transport['brand']} {transport['model']} ({transport['license_plate']})"
        if formatted_transport == selected_transport:
            brand, model, license_plate = transport['brand'], transport['model'], transport['license_plate']
            break
    else:
        # Отправляем сообщение об ошибке и добавляем кнопки возврата в меню
        bot.send_message(user_id, "Не удалось найти указанный транспорт. Пожалуйста, выберите снова.")

        # Формируем клавиатуру с кнопками выбора транспорта и кнопками возврата в меню
        markup = get_user_transport_keyboard(user_id)
        markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        markup.add(types.KeyboardButton("В главное меню"))

        bot.send_message(user_id, "Выберите транспорт или добавьте новый:", reply_markup=markup)
        bot.register_next_step_handler(message, handle_transport_selection_for_expense)
        return

    # Продолжение процесса после выбора транспорта
    process_category_selection(user_id, brand, model, license_plate)

# Основной процесс выбора категории для записи траты
def process_category_selection(user_id, brand, model, license_plate, prompt_message=None):
    categories = get_user_categories(user_id)

    # Смайлы для категорий
    system_emoji = "🔹"
    user_emoji = "🔸"

    # Добавление смайлов к категориям: первые 7 считаются системными
    category_list = "\n".join(
        f"{system_emoji if i < 7 else user_emoji} {i + 1}. {category}"
        for i, category in enumerate(categories)
    )
    category_list = f"*Выберите категорию:*\n\n{category_list}"

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
    if prompt_message:
        bot.send_message(user_id, category_list, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(prompt_message, get_expense_category, brand, model, license_plate)
    else:
        prompt_message = bot.send_message(user_id, category_list, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(prompt_message, get_expense_category, brand, model, license_plate)

# Обработка выбора категории для траты
def get_expense_category(message, brand, model, license_plate):
    user_id = message.from_user.id
    
    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_expense_category, brand, model, license_plate)
        return

    # Проверка на текстовое сообщение
    if not message.text:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_expense_category, brand, model, license_plate)
        return
    
    selected_index = message.text.strip()

    # Переход в меню
    if selected_index == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return
    elif selected_index == "В главное меню":
        return_to_menu(message)
        return

    if selected_index == 'Без категории':
        selected_category = "Без категории"
        proceed_to_expense_name(message, selected_category, brand, model, license_plate)
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
        bot.register_next_step_handler(message, add_new_category, brand, model, license_plate)
        return

    if selected_index == 'Удалить категорию':
        handle_category_removal(message, brand, model, license_plate)
        return

    if selected_index.isdigit():
        index = int(selected_index) - 1
        categories = get_user_categories(user_id)
        if 0 <= index < len(categories):
            selected_category = categories[index]
            proceed_to_expense_name(message, selected_category, brand, model, license_plate)
        else:
            bot.send_message(user_id, "Неверный номер категории. Попробуйте снова.")
            bot.register_next_step_handler(message, get_expense_category, brand, model, license_plate)
    else:
        bot.send_message(user_id, "Пожалуйста, введите номер категории.")
        bot.register_next_step_handler(message, get_expense_category, brand, model, license_plate)

# Добавление новой категории для трат
def add_new_category(message, brand, model, license_plate):
    user_id = message.from_user.id

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, add_new_category, brand, model, license_plate)
        return

    # Проверка на текстовое сообщение
    if not message.text:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, add_new_category, brand, model, license_plate)
        return

    # Основной код функции
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
    
    process_category_selection(user_id, brand, model, license_plate)

def proceed_to_expense_name(message, selected_category, brand, model, license_plate):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите название траты:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expense_name, selected_category, brand, model, license_plate)

# Обработчик для ввода названия траты
def get_expense_name(message, selected_category, brand, model, license_plate):
    user_id = message.from_user.id

    # Проверка на мультимедийные файлы
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_expense_name, selected_category, brand, model, license_plate)
        return

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
    bot.register_next_step_handler(message, get_expense_description, selected_category, expense_name, brand, model, license_plate)

def get_expense_description(message, selected_category, expense_name, brand, model, license_plate):
    user_id = message.from_user.id

    # Проверка на мультимедийные файлы
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_expense_description, selected_category, expense_name, brand, model, license_plate)
        return

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
    bot.register_next_step_handler(message, get_expense_date, selected_category, expense_name, description, brand, model, license_plate)

def get_expense_date(message, selected_category, expense_name, description, brand, model, license_plate):
    user_id = message.from_user.id

    # Проверка на мультимедийные файлы
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_expense_date, selected_category, expense_name, description, brand, model, license_plate)
        return

    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_menu_2(message)
        else:
            return_to_menu(message)
        return

    expense_date = message.text

    # Проверка на формат даты
    if re.match(r"^\d{2}\.\d{2}\.\d{4}$", expense_date):
        try:
            day, month, year = map(int, expense_date.split('.'))
            # Проверка на корректность значений дня, месяца и года
            if 1 <= month <= 12 and 1 <= day <= 31 and 2000 <= year <= 3000:
                datetime.strptime(expense_date, "%d.%m.%Y")
            else:
                raise ValueError
        except ValueError:
            bot.send_message(user_id, "Неверный формат даты или значения. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")
            bot.register_next_step_handler(message, get_expense_date, selected_category, expense_name, description, brand, model, license_plate)
            return
    else:
        bot.send_message(user_id, "Неверный формат даты. Попробуйте еще раз в формате ДД.ММ.ГГГГ.")
        bot.register_next_step_handler(message, get_expense_date, selected_category, expense_name, description, brand, model, license_plate)
        return

    # Если дата корректна, переходим к следующему шагу
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)
    
    bot.send_message(user_id, "Введите сумму траты:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expense_amount, selected_category, expense_name, description, expense_date, brand, model, license_plate)
    
def get_expense_amount(message, selected_category, expense_name, description, expense_date, brand, model, license_plate):
    user_id = message.from_user.id

    # Проверка на мультимедийные файлы
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_expense_amount, selected_category, expense_name, description, expense_date, brand, model, license_plate)
        return

    # Получаем сумму траты
    expense_amount = message.text.replace(",", ".")
    if not is_numeric(expense_amount):
        bot.send_message(user_id, "Пожалуйста, введите сумму траты в числовом формате.")
        bot.register_next_step_handler(message, get_expense_amount, selected_category, expense_name, description, expense_date, brand, model, license_plate)
        return

    # Загружаем данные о расходах пользователя
    data = load_expense_data(user_id)
    if str(user_id) not in data:
        data[str(user_id)] = {"expenses": []}

    # Добавляем новый расход
    selected_transport = f"{brand} {model} {license_plate}"
    expenses = data[str(user_id)].get("expenses", [])
    new_expense = {
        "category": selected_category,
        "name": expense_name,
        "date": expense_date,
        "amount": expense_amount,
        "description": description,
        "transport": {"brand": brand, "model": model, "license_plate": license_plate}
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
        transport_sheet_name = f"{expense_data['transport']['brand']}_{expense_data['transport']['model']}_{expense_data['transport']['license_plate']}"
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
                f"{expense_data['transport']['brand']} {expense_data['transport']['model']} {expense_data['transport']['license_plate']}",
                expense_data["category"],
                expense_data["name"],
                expense_data["date"],
                float(expense_data["amount"]),  # Сохраняем сумму как число
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
@bot.message_handler(func=lambda message: message.text == "Удалить категорию")
@restricted
@track_user_activity
def handle_category_removal(message, brand=None, model=None, license_plate=None):
    user_id = message.from_user.id
    categories = get_user_categories(user_id)

    # Смайлы для категорий
    system_emoji = "🔹"
    user_emoji = "🔸"

    # Создаем текстовый список категорий с эмодзи
    category_list = "\n".join(
        f"{system_emoji if i < 7 else user_emoji} {i + 1}. {category}"
        for i, category in enumerate(categories)
    )
    category_list = f"*Выберите категорию для удаления или 0 для отмены:*\n\n{category_list}"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))

    bot.send_message(user_id, category_list, reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, remove_selected_category, brand, model, license_plate)

def remove_selected_category(message, brand, model, license_plate):
    user_id = message.from_user.id

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, remove_selected_category, brand, model, license_plate)
        return

    # Проверка на наличие текста в сообщении
    if not message.text:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, remove_selected_category, brand, model, license_plate)
        return

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
        return process_category_selection(user_id, brand, model, license_plate)

    if selected_index.isdigit():
        index = int(selected_index) - 1
        categories = get_user_categories(user_id)
        default_categories = ["Без категории", "АЗС", "Мойка", "Парковка", "Платная дорога", "Страховка", "Штрафы"]

        if 0 <= index < len(categories):
            category_to_remove = categories[index]
            if category_to_remove in default_categories:
                bot.send_message(user_id, f"Нельзя удалить системную категорию '{category_to_remove}'. Попробуйте еще раз.")
                return bot.register_next_step_handler(message, remove_selected_category, brand, model, license_plate)

            remove_user_category(user_id, category_to_remove)
            bot.send_message(user_id, f"Категория '{category_to_remove}' успешно удалена.")
        else:
            bot.send_message(user_id, "Неверный номер категории. Попробуйте снова.")
            return bot.register_next_step_handler(message, remove_selected_category, brand, model, license_plate)
    else:
        bot.send_message(user_id, "Пожалуйста, введите номер категории.")
        return bot.register_next_step_handler(message, remove_selected_category, brand, model, license_plate)

    return process_category_selection(user_id, brand, model, license_plate)

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
    item_cancel = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_add_transport)
    markup.add(item_cancel)
    markup.add(item_main)
    return markup

def ask_add_transport(message):
    user_id = message.from_user.id

    if message.text == "Добавить транспорт":
        add_transport(message)
        return
    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
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
    filtered_expenses = [expense for expense in expenses if f"{expense['transport']['brand']} {expense['transport']['model']} ({expense['transport']['license_plate']})" == selected_transport]
    return filtered_expenses

# Функция для отправки сообщений, если сообщение длинное
def send_message_with_split(user_id, message_text):
    bot.send_message(user_id, message_text, parse_mode="Markdown")

# Функция для отправки меню
def send_menu1(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Траты (по категориям)")
    item2 = types.KeyboardButton("Траты (месяц)")
    item3 = types.KeyboardButton("Траты (год)")
    item4 = types.KeyboardButton("Траты (все время)")
    item_excel = types.KeyboardButton("Посмотреть траты в EXCEL")  # Новая кнопка
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item1, item2)
    markup.add(item3, item4)
    markup.add(item_excel)
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Выберите вариант просмотра трат:", reply_markup=markup)

# Обработчик для просмотра трат
@bot.message_handler(func=lambda message: message.text == "Посмотреть траты")
@restricted
@track_user_activity
def view_expenses(message):
    user_id = message.from_user.id

    # Загружаем данные о транспорте
    transport_list = load_transport_data(user_id)

    if not transport_list:
        bot.send_message(user_id, "У вас нет сохраненного транспорта. Хотите добавить транспорт?", reply_markup=create_transport_options_markup())
        bot.register_next_step_handler(message, ask_add_transport)
        return

    # Если транспорт есть, продолжаем с выбором
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Разбиваем транспорт на группы по два элемента
    for i in range(0, len(transport_list), 2):
        transport_buttons = []
        for j in range(i, min(i + 2, len(transport_list))):
            transport = transport_list[j]
            transport_name = f"{transport['brand']} {transport['model']} ({transport['license_plate']})"
            transport_buttons.append(types.KeyboardButton(transport_name))
        
        # Добавляем пару кнопок в строку
        markup.add(*transport_buttons)
    
    # Добавляем кнопки возврата
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main)

    bot.send_message(user_id, "Выберите ваш транспорт:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection)

# Обработчик выбора транспорта
def handle_transport_selection(message):
    user_id = message.from_user.id
    selected_transport = message.text

    if selected_transport == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if selected_transport == "В главное меню":
        return_to_menu(message)
        return

    # Сохраняем выбранный транспорт для пользователя
    selected_transport_dict[user_id] = selected_transport

    # Теперь можем показывать доступные фильтры для трат
    bot.send_message(user_id, f"Показываю траты для транспорта: *{selected_transport}*", parse_mode="Markdown")
    send_menu1(user_id)

@bot.message_handler(func=lambda message: message.text == "Посмотреть траты в EXCEL")
@restricted
@track_user_activity
def send_expenses_excel(message):
    user_id = message.from_user.id

    # Путь к Excel файлу
    excel_path = os.path.join("data base", "expense", "excel", f"{user_id}_expenses.xlsx")

    # Проверяем наличие файла
    if not os.path.exists(excel_path):
        bot.send_message(user_id, "Файл с вашими тратами не найден")
        return

    # Отправка файла пользователю
    with open(excel_path, 'rb') as excel_file:
        bot.send_document(user_id, excel_file)

# Обработчик для просмотра трат по категориям
@bot.message_handler(func=lambda message: message.text == "Траты (по категориям)")
@restricted
@track_user_activity
def view_expenses_by_category(message):
    user_id = message.from_user.id
    user_data = load_expense_data(user_id)
    expenses = user_data.get(str(user_id), {}).get("expenses", [])

    # Фильтруем траты по выбранному транспорту
    expenses = filter_expenses_by_transport(user_id, expenses)

    # Получаем уникальные категории трат для выбранного транспорта
    categories = set(expense['category'] for expense in expenses)
    if not categories:
        bot.send_message(user_id, "*Нет доступных категорий* для выбранного транспорта", parse_mode="Markdown")
        send_menu1(user_id)  # Возврат в меню трат и ремонтов
        return

    category_buttons = [types.KeyboardButton(category) for category in categories]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*category_buttons)
    item_return_to_expenses = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_return_to_main = types.KeyboardButton("В главное меню")
    markup.add(item_return_to_expenses)
    markup.add(item_return_to_main)

    bot.send_message(user_id, "Выберите категорию для просмотра трат:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_category_selection)

# Обработчик выбора категории
def handle_category_selection(message):
    user_id = message.from_user.id
    selected_category = message.text

    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, handle_category_selection)
        return
    
    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):  
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, handle_category_selection)
        return

    user_data = load_expense_data(user_id)
    expenses = user_data.get(str(user_id), {}).get("expenses", [])

    # Фильтруем траты по выбранному транспорту
    expenses = filter_expenses_by_transport(user_id, expenses)

    # Проверяем, существует ли выбранная категория
    if selected_category not in {expense['category'] for expense in expenses}:
        bot.send_message(user_id, "Выбранная категория не найдена. Пожалуйста, выберите корректную категорию")
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
            f"💸 *№ {index}*\n\n"
            f"📂 *Категория:* {selected_category}\n"
            f"📌 *Название:* {expense_name}\n"
            f"📅 *Дата:* {expense_date}\n"
            f"💰 *Сумма:* {amount} руб.\n"
            f"📝 *Описание:* {expense.get('description', 'Без описания')}\n"
        )

    if expense_details:
        message_text = f"Траты в категории *{selected_category.lower()}*:\n\n\n" + "\n\n".join(expense_details)
        send_message_with_split(user_id, message_text)
        bot.send_message(
            user_id, 
            f"Итоговая сумма трат в категории *{selected_category.lower()}*: *{total_expenses}* руб.", 
            parse_mode="Markdown"
        )
    else:
        bot.send_message(user_id, f"В категории *{selected_category.lower()}* трат не найдено", parse_mode="Markdown")

    # Возвращаем пользователя в главное меню после отображения информации
    send_menu1(user_id)

# Обработчик трат за месяц
@bot.message_handler(func=lambda message: message.text == "Траты (месяц)")
@restricted
@track_user_activity
def view_expenses_by_month(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main)

    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для просмотра трат за этот период:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expenses_by_month)

def get_expenses_by_month(message):
    user_id = message.from_user.id
    date = message.text.strip() if message.text else None

    # Проверяем, есть ли текст в сообщении
    if not date:
        bot.send_message(user_id, "Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_expenses_by_month)
        return

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_expenses_by_month)
        return
    
    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):  
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_expenses_by_month)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    # Проверка формата и диапазонов месяца и года
    if "." in date:
        parts = date.split(".")
        if len(parts) == 2:
            month, year = parts
            if month.isdigit() and year.isdigit() and 1 <= int(month) <= 12 and 2000 <= int(year) <= 3000:
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
                                f"💸 *№ {index}*\n\n"
                                f"📂 *Категория:* {category}\n"
                                f"📌 *Название:* {expense_name}\n"
                                f"📅 *Дата:* {expense_date}\n"
                                f"💰 *Сумма:* {amount} руб.\n"
                                f"📝 *Описание:* {description}\n"
                            )

                if expense_details:
                    message_text = f"Траты за *{date}* месяц:\n\n\n" + "\n\n".join(expense_details)
                    send_message_with_split(user_id, message_text)
                    bot.send_message(user_id, f"Итоговая сумма трат за *{date}* месяц: *{total_expenses}* руб.", parse_mode="Markdown")
                else:
                    bot.send_message(user_id, f"За *{date}* месяц трат не найдено", parse_mode="Markdown")
                
                send_menu1(user_id)  # Возвращаемся в меню после отображения информации
            else:
                bot.send_message(user_id, "Пожалуйста, введите корректный месяц и год в формате ММ.ГГГГ")
                bot.register_next_step_handler(message, get_expenses_by_month)
                return
        else:
            bot.send_message(user_id, "Пожалуйста, введите дату в формате ММ.ГГГГ")
            bot.register_next_step_handler(message, get_expenses_by_month)
            return
    else:
        bot.send_message(user_id, "Пожалуйста, введите дату в формате ММ.ГГГГ")
        bot.register_next_step_handler(message, get_expenses_by_month)
        return

# Обработчик трат за год
@bot.message_handler(func=lambda message: message.text == "Траты (год)")
@restricted
@track_user_activity
def view_expenses_by_license_plate(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main)

    bot.send_message(user_id, "Введите год в формате (ГГГГ) для просмотра трат за этот год:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expenses_by_license_plate)

def get_expenses_by_license_plate(message):
    user_id = message.from_user.id

    # Проверяем, что сообщение содержит текст
    if not message.text:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_expenses_by_license_plate)
        return

    year_input = message.text.strip()

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_expenses_by_license_plate)
        return
    
    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):  
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_expenses_by_license_plate)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    # Проверка, что введено четырехзначное число
    if not year_input.isdigit() or len(year_input) != 4:
        bot.send_message(user_id, "Пожалуйста, введите год в формате ГГГГ")
        bot.register_next_step_handler(message, get_expenses_by_license_plate)
        return

    # Преобразуем год в число и проверяем диапазон
    year = int(year_input)
    if year < 2000 or year > 3000:
        bot.send_message(user_id, "Введите год в формате ГГГГ")
        bot.register_next_step_handler(message, get_expenses_by_license_plate)
        return

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
                        f"💸 *№ {index}*\n\n"
                        f"📂 *Категория:* {category}\n"
                        f"📌 *Название:* {expense_name}\n"
                        f"📅 *Дата:* {expense_date}\n"
                        f"💰 *Сумма:* {amount} руб.\n"
                        f"📝 *Описание:* {description}\n"
                    )
                    
    if expense_details:
        message_text = f"Траты за *{year}* год:\n\n\n" + "\n\n".join(expense_details)
        send_message_with_split(user_id, message_text)
        bot.send_message(user_id, f"Итоговая сумма трат за *{year}* год: *{total_expenses}* руб.", parse_mode="Markdown")
    else:
        bot.send_message(user_id, f"За *{year}* год трат не найдено", parse_mode="Markdown")

    # Возвращаемся в меню после отображения информации
    send_menu1(user_id)

# Обработчик всех трат
@bot.message_handler(func=lambda message: message.text == "Траты (все время)")
@restricted
@track_user_activity
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
            f"💸 *№ {index}*\n\n"
            f"📂 *Категория:* {category}\n"
            f"📌 *Название:* {expense_name}\n"
            f"📅 *Дата:* {expense_date}\n"
            f"💰 *Сумма:* {amount} руб.\n"
            f"📝 *Описание:* {description}\n"
        )

    if expense_details:
        message_text = "*Все* траты:\n\n\n" + "\n\n".join(expense_details)
        send_message_with_split(user_id, message_text)
        bot.send_message(user_id, f"Итоговая сумма всех трат: *{total_expenses}* руб.", parse_mode="Markdown")
    else:
        bot.send_message(user_id, "Трат не найдено", parse_mode="Markdown")

    # Возвращаемся в меню после отображения информации
    send_menu1(user_id)

# (10.18) --------------- КОД ДЛЯ "ТРАТ" (ОБРАБОТЧИК "УДАЛИТЬ ТРАТЫ") ---------------

# Глобальный словарь для хранения выбранного транспорта по user_id
selected_transports = {}

def save_selected_transport(user_id, selected_transport):
    user_data = load_expense_data(user_id)  # Загружаем данные пользователя
    # Изменяем только выбранный транспорт, не трогая остальные данные
    user_data["selected_transport"] = selected_transport
    save_expense_data(user_id, user_data)  # Сохраняем только изменения
    print(f"Транспорт сохранён: {selected_transport}")  # Для отладки

@bot.message_handler(func=lambda message: message.text == "Удалить траты")
@restricted
@track_user_activity
def delete_expenses_menu(message):
    user_id = message.from_user.id

    transport_data = load_transport_data(user_id)
    if not transport_data:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_add_transport = types.KeyboardButton("Добавить транспорт")
        item_cancel = types.KeyboardButton("Вернуться в меню трат и ремонтов")
        item_main = types.KeyboardButton("В главное меню")
        markup.add(item_add_transport)
        markup.add(item_cancel)
        markup.add(item_main)
        bot.send_message(user_id, "У вас нет сохраненного транспорта. Хотите добавить транспорт?", reply_markup=markup)
        bot.register_next_step_handler(message, ask_add_transport)
        return

    # Отображение транспорта для удаления в два столбца
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    transport_buttons = []  # Временный список для кнопок

    # Проходим по данным о транспорте и создаем кнопки
    for transport in transport_data:
        brand = transport.get("brand", "Без названия")
        model = transport.get("model", "Без названия")
        license_plate = transport.get("license_plate", "Неизвестно")
        # Добавляем номер транспорта в скобках
        button_label = f"{brand} {model} ({license_plate})"
        transport_buttons.append(types.KeyboardButton(button_label))

    # Формируем строки по две кнопки
    for i in range(0, len(transport_buttons), 2):
        markup.row(*transport_buttons[i:i + 2])

    # Добавляем кнопки возврата
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

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
    item_license_plate = types.KeyboardButton("Del траты (год)")
    item_all_time = types.KeyboardButton("Del траты (все время)")
    item_del_category_exp = types.KeyboardButton("Del траты (категория)")
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    
    markup.add(item_del_category_exp, item_month)
    markup.add(item_license_plate, item_all_time)
    markup.add(item_return)
    markup.add(item_main_menu)
    bot.send_message(user_id, "Выберите вариант удаления трат:", reply_markup=markup)

expenses_to_delete_dict = {}


MAX_MESSAGE_LENGTH = 4096

def send_long_message(user_id, text):
    # Разбиваем текст на части, если он слишком длинный
    while len(text) > MAX_MESSAGE_LENGTH:
        # Отправляем первую часть текста
        bot.send_message(user_id, text[:MAX_MESSAGE_LENGTH], parse_mode="Markdown")
        # Оставшийся текст
        text = text[MAX_MESSAGE_LENGTH:]
    # Отправляем остаток
    bot.send_message(user_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Del траты (категория)")
@restricted
@track_user_activity
def delete_expenses_by_category(message):
    user_id = message.from_user.id

    selected_transport = selected_transports.get(user_id)

    if not selected_transport:
        bot.send_message(user_id, "Не выбран транспорт")
        send_menu(user_id)
        return

    # Приводим транспорт в одинаковый формат и удаляем скобки
    selected_transport_info = selected_transport.strip().lower().replace('(', '').replace(')', '')

    # Загружаем данные пользователя
    user_data = load_expense_data(user_id).get(str(user_id), {})
    expenses = user_data.get("expenses", [])

    # Получаем категории для удаления по выбранному транспорту
    categories = list({
        expense.get("category")
        for expense in expenses
        if f"{expense.get('transport', {}).get('brand', '').strip().lower()} {expense.get('transport', {}).get('model', '').strip().lower()} {str(expense.get('transport', {}).get('license_plate', '')).strip().lower()}".replace('(', '').replace(')', '') == selected_transport_info
    })

    if not categories:
        bot.send_message(user_id, "У вас *нет категорий* для удаления трат по выбранному транспорту", parse_mode="Markdown")
        send_menu(user_id)
        return

    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(*[types.KeyboardButton(category) for category in categories])
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))

    bot.send_message(user_id, "Выберите категорию для удаления:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_category_selection_for_deletion)

# Глобальный словарь для хранения выбранной категории
selected_categories = {}

user_expenses_to_delete = {}

def handle_category_selection_for_deletion(message):
    user_id = message.from_user.id

    if not message.text:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, handle_category_selection_for_deletion)
        return

    selected_category = message.text.strip()

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, handle_category_selection_for_deletion)
        return
    
    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):  
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, handle_category_selection_for_deletion)
        return

    # Проверка возврата в меню
    if selected_category == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if selected_category == "В главное меню":
        return_to_menu(message)
        return

    selected_categories[user_id] = selected_category

    user_data = load_expense_data(user_id).get(str(user_id), {})
    expenses = user_data.get("expenses", [])

    selected_transport = selected_transports.get(user_id)
    selected_transport_info = selected_transport.strip().lower().replace('(', '').replace(')', '')

    # Фильтруем расходы
    expenses_to_delete = [
        expense for expense in expenses 
        if expense.get("category") == selected_category and 
           f"{expense.get('transport', {}).get('brand', '').strip().lower()} {expense.get('transport', {}).get('model', '').strip().lower()} {str(expense.get('transport', {}).get('license_plate', '')).strip().lower()}".replace('(', '').replace(')', '') == selected_transport_info
    ]

    if not expenses_to_delete:
        bot.send_message(user_id, f"Нет трат для удаления в категории *{selected_category.lower()}* по выбранному транспорту", parse_mode="Markdown")
        send_menu(user_id)
        return

    # Сохраняем список трат
    user_expenses_to_delete[user_id] = expenses_to_delete

    # Формируем текстовый список для отображения
    expense_list_text = f"Список трат для удаления по категории *{selected_category.lower()}*:\n\n\n"
    for index, expense in enumerate(expenses_to_delete, start=1):
        expense_name = expense.get("name", "Без названия")
        expense_date = expense.get("date", "Неизвестно")
        expense_list_text += f"📄 №{index}. {expense_name} - ({expense_date})\n\n"

    expense_list_text += "\nВведите номер траты для удаления или вернитесь в меню:"

    # Создаем клавиатуру с кнопками
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")

    # Отправляем сообщение с текстом и клавишами в одном вызове
    bot.send_message(user_id, expense_list_text, reply_markup=markup, parse_mode="Markdown")

    # Переход к следующему шагу (запрос номера траты для удаления)
    bot.register_next_step_handler(message, delete_expense_confirmation)


def delete_expense_confirmation(message):
    user_id = message.from_user.id

    # Проверка, если текстовое сообщение отсутствует
    if not message.text:
        bot.send_message(user_id, "Извините, отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_expense_confirmation)
        return

    selected_option = message.text.strip()

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_expense_confirmation)
        return

    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', selected_option):
        bot.send_message(user_id, "Извините, отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_expense_confirmation)
        return

    if selected_option == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if selected_option == "В главное меню":
        return_to_menu(message)
        return

    # Проверка, что введен номер
    if not selected_option.isdigit():
        bot.send_message(user_id, "Пожалуйста, введите номер траты из списка.")
        bot.register_next_step_handler(message, delete_expense_confirmation)
        return

    expense_index = int(selected_option) - 1
    expenses_to_delete = user_expenses_to_delete.get(user_id, [])

    # Проверка на правильность номера
    if 0 <= expense_index < len(expenses_to_delete):
        deleted_expense = expenses_to_delete.pop(expense_index)
        user_data = load_expense_data(user_id).get(str(user_id), {})
        user_expenses = user_data.get("expenses", [])

        # Удаление выбранной траты
        if deleted_expense in user_expenses:
            user_expenses.remove(deleted_expense)
            save_expense_data(user_id, {str(user_id): user_data})

        bot.send_message(
            user_id,
            f"Трата *{deleted_expense.get('name', 'Без названия').lower()}* успешно удалена.",
            parse_mode="Markdown"
        )

        # Возврат в меню после успешного удаления
        send_menu(user_id)
    else:
        bot.send_message(user_id, "Неверный номер траты. Попробуйте снова.")
        bot.register_next_step_handler(message, delete_expense_confirmation)
        return

# Удаление трат за месяц

MAX_MESSAGE_LENGTH = 4096

def send_long_message(user_id, text):
    # Разбиваем текст на части, если он слишком длинный
    while len(text) > MAX_MESSAGE_LENGTH:
        # Отправляем первую часть текста
        bot.send_message(user_id, text[:MAX_MESSAGE_LENGTH], parse_mode="Markdown")
        # Оставшийся текст
        text = text[MAX_MESSAGE_LENGTH:]
    # Отправляем остаток
    bot.send_message(user_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Del траты (месяц)")
@restricted
@track_user_activity
def delete_expense_by_month(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)
    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для удаления трат за этот месяц:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_expenses_by_month)

def delete_expenses_by_month(message):
    user_id = message.from_user.id
    month_year = message.text.strip() if message.text else None

    if not month_year:
        bot.send_message(user_id, "Извините, отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение")
        bot.register_next_step_handler(message, delete_expenses_by_month)
        return

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_expenses_by_month)
        return

    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):  
        bot.send_message(user_id, "Извините, отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_expenses_by_month)
        return

    # Проверка формата месяца и года
    match = re.match(r"^(0[1-9]|1[0-2])\.(20[0-9]{2})$", month_year)
    if not match:
        bot.send_message(user_id, "Введен неверный месяц или год. Пожалуйста, введите корректные данные (ММ.ГГГГ)")
        bot.register_next_step_handler(message, delete_expenses_by_month)
        return

    selected_month, selected_year = match.groups()

    # Проверка выбранного транспорта
    selected_transport = selected_transports.get(user_id)
    if not selected_transport:
        bot.send_message(user_id, "Транспорт не выбран. Пожалуйста, выберите транспорт")
        send_menu(user_id)
        return

    transport_info = selected_transport.split(" ")
    selected_brand = transport_info[0].strip()
    selected_model = transport_info[1].strip()
    selected_license_plate = transport_info[2].strip().replace("(", "").replace(")", "")

    user_data = load_expense_data(user_id).get(str(user_id), {})
    expenses = user_data.get("expenses", [])

    if not expenses:
        bot.send_message(user_id, f"У вас нет сохраненных трат за *{month_year}* месяц", parse_mode="Markdown")
        send_menu(user_id)
        return

    expenses_to_delete = []
    for index, expense in enumerate(expenses, start=1):
        expense_date = expense.get("date", "")

        if not expense_date or len(expense_date.split(".")) != 3:
            continue  # Пропускаем траты с некорректной датой

        expense_day, expense_month, expense_year = expense_date.split(".")

        if expense_month == selected_month and expense_year == selected_year:
            expense_license_plate = expense.get("transport", {}).get("license_plate", "").strip()
            expense_brand = expense.get("transport", {}).get("brand", "").strip()
            expense_model = expense.get("transport", {}).get("model", "").strip()

            if (expense_license_plate == selected_license_plate and
                expense_brand == selected_brand and
                expense_model == selected_model):
                expenses_to_delete.append((index, expense))

    if expenses_to_delete:
        # Сохранение списка трат для удаления
        expenses_to_delete_dict[user_id] = expenses_to_delete

        # Формирование сообщения
        expense_list_text = f"Список трат для удаления за *{month_year}* месяц:\n\n"
        for index, expense in expenses_to_delete:
            expense_name = expense.get("name", "Без названия")
            expense_date = expense.get("date", "Неизвестно")
            expense_list_text += f"📄 №{index}. {expense_name} - ({expense_date})\n\n"

        expense_list_text += "\nВведите номер траты для удаления или вернитесь в меню:"

        # Отправка сообщения
        send_long_message(user_id, expense_list_text)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов", "В главное меню")
        bot.register_next_step_handler(message, confirm_delete_expense_month)
    else:
        bot.send_message(user_id, f"Нет трат для удаления за *{month_year}* месяц", parse_mode="Markdown")
        send_menu(user_id)

def confirm_delete_expense_month(message):
    user_id = message.from_user.id

    # Проверка, если текстовое сообщение отсутствует
    if not message.text:
        bot.send_message(user_id, "Извините, отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение")
        bot.register_next_step_handler(message, confirm_delete_expense_month)
        return

    selected_option = message.text.strip()

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_expense_month)
        return

    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', selected_option):
        bot.send_message(user_id, "Извините, отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_expense_month)
        return

    # Проверка на возврат в меню
    if selected_option == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if selected_option == "В главное меню":
        return_to_menu(message)
        return

    # Проверка ввода номера траты
    if selected_option.isdigit():
        expense_index = int(selected_option) - 1
        expenses_to_delete = expenses_to_delete_dict.get(user_id, [])

        if 0 <= expense_index < len(expenses_to_delete):
            # Удаление выбранной траты
            _, deleted_expense = expenses_to_delete.pop(expense_index)

            # Обновление данных пользователя
            user_data = load_expense_data(user_id).get(str(user_id), {})
            if "expenses" in user_data and deleted_expense in user_data["expenses"]:
                user_data["expenses"].remove(deleted_expense)
                save_expense_data(user_id, {str(user_id): user_data})

            # Уведомление об успешном удалении
            bot.send_message(
                user_id,
                f"Трата *{deleted_expense.get('name', 'Без названия').lower()}* успешно удалена",
                parse_mode="Markdown"
            )

            # Обновление глобального списка
            expenses_to_delete_dict[user_id] = expenses_to_delete

            # Возврат в меню после успешного удаления
            send_menu(user_id)
        else:
            bot.send_message(user_id, "Неверный выбор. Пожалуйста, попробуйте снова.")
            bot.register_next_step_handler(message, confirm_delete_expense_month)
            return
    else:
        bot.send_message(user_id, "Некорректный ввод. Пожалуйста, введите номер траты.")
        bot.register_next_step_handler(message, confirm_delete_expense_month)
        return

# Удаление трат за год
MAX_MESSAGE_LENGTH = 4096

def send_long_message(user_id, text):
    # Разбиваем текст на части, если он слишком длинный
    while len(text) > MAX_MESSAGE_LENGTH:
        # Отправляем первую часть текста
        bot.send_message(user_id, text[:MAX_MESSAGE_LENGTH], parse_mode="Markdown")
        # Оставшийся текст
        text = text[MAX_MESSAGE_LENGTH:]
    # Отправляем остаток
    bot.send_message(user_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Del траты (год)")
@restricted
@track_user_activity
def delete_expense_by_license_plate(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)
    bot.send_message(user_id, "Введите год (ГГГГ) для удаления трат за этот год:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_expenses_by_license_plate)

def delete_expenses_by_license_plate(message):
    user_id = message.from_user.id
    license_plate = message.text.strip() if message.text else None  # Проверяем наличие текста

    # Проверка на отсутствие текста
    if not license_plate:
        bot.send_message(user_id, "Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_expenses_by_license_plate)
        return

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_expenses_by_license_plate)
        return

    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', license_plate):  
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_expenses_by_license_plate)
        return

    if license_plate == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if license_plate == "В главное меню":
        return_to_menu(message)
        return

    # Проверка формата года (от 2000 до 3000)
    if not re.match(r"^(20[0-9]{2}|2[1-9][0-9]{2}|3000)$", license_plate):
        bot.send_message(user_id, "Введен неверный год. Пожалуйста, введите корректный год.")
        bot.register_next_step_handler(message, delete_expenses_by_license_plate)
        return

    user_data = load_expense_data(user_id).get(str(user_id), {})
    expenses = user_data.get("expenses", [])

    selected_transport = selected_transports.get(user_id, None)

    if selected_transport:
        transport_info = selected_transport.split(" ")
        selected_brand = transport_info[0].strip()
        selected_model = transport_info[1].strip()
        selected_license_plate = str(transport_info[2].strip())
    else:
        selected_brand = selected_model = selected_license_plate = None

    if not expenses:
        bot.send_message(user_id, f"У вас пока нет сохраненных трат за *{license_plate}* год для удаления", parse_mode="Markdown")
        send_menu(user_id)
        return

    expenses_to_delete = []
    for index, expense in enumerate(expenses, start=1):
        expense_date = expense.get("date", "")
        expense_license_plate = expense_date.split(".")[2]

        expense_brand = expense.get("transport", {}).get("brand", "").strip()
        expense_model = expense.get("transport", {}).get("model", "").strip()

        if (expense_license_plate == license_plate and
           expense_brand == selected_brand and
           expense_model == selected_model):
            expenses_to_delete.append((index, expense))

    if expenses_to_delete:
        expenses_to_delete_dict[user_id] = expenses_to_delete

        expense_list_text = f"Список трат для удаления за *{license_plate}* год:\n\n\n"
        for index, expense in expenses_to_delete:
            expense_name = expense.get("name", "Без названия")
            expense_date = expense.get("date", "Неизвестно")
            expense_list_text += f"📄 №{index}. {expense_name} - ({expense_date})\n\n"

        expense_list_text += "\nВведите номер траты для удаления или вернитесь в меню:"
        send_long_message(user_id, expense_list_text)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.register_next_step_handler(message, confirm_delete_expense_license_plate)
    else:
        bot.send_message(user_id, f"За *{license_plate}* год трат не найдено для удаления", parse_mode="Markdown")
        send_menu(user_id)

def confirm_delete_expense_license_plate(message):
    user_id = message.from_user.id

    # Проверка, если текстовое сообщение отсутствует
    if not message.text:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_expense_license_plate)
        return

    selected_option = message.text.strip()

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_expense_license_plate)
        return
    
    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', selected_option):
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_expense_license_plate)
        return

    if selected_option == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if selected_option == "В главное меню":
        return_to_menu(message)
        return

    # Получаем список трат для удаления из глобальной переменной
    expenses_to_delete = expenses_to_delete_dict.get(user_id, [])

    if selected_option.isdigit():
        expense_index = int(selected_option) - 1

        if 0 <= expense_index < len(expenses_to_delete):
            _, deleted_expense = expenses_to_delete.pop(expense_index)

            user_data = load_expense_data(user_id).get(str(user_id), {})
            user_data["expenses"].remove(deleted_expense)
            save_expense_data(user_id, {str(user_id): user_data})

            bot.send_message(user_id, f"Трата *{deleted_expense.get('name', 'Без названия').lower()}* успешно удалена", parse_mode="Markdown")

            # Обновление списка трат для удаления
            expenses_to_delete_dict[user_id] = expenses_to_delete

            # Возврат в меню после успешного удаления
            send_menu(user_id)
        else:
            bot.send_message(user_id, "Неверный выбор. Пожалуйста, попробуйте снова.")
            bot.register_next_step_handler(message, confirm_delete_expense_license_plate)
    else:
        bot.send_message(user_id, "Некорректный ввод. Пожалуйста, введите номер траты.")
        bot.register_next_step_handler(message, confirm_delete_expense_license_plate)

# Удаление всех трат
@bot.message_handler(func=lambda message: message.text == "Del траты (все время)")
@restricted
@track_user_activity
def delete_all_expenses_for_selected_transport(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    # Запрашиваем подтверждение
    bot.send_message(user_id, 
                    "Вы уверены, что хотите удалить все траты для выбранного транспорта?\n\n"
                    "Пожалуйста, введите *ДА* для подтверждения или *НЕТ* для отмены",
                    reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler(message, confirm_delete_all_expenses)

def confirm_delete_all_expenses(message):
    user_id = message.from_user.id

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_all_expenses)
        return
    
    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):  
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_all_expenses)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    # Проверяем, что message.text не None
    if not message.text:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_all_expenses)
        return

    # Приводим ответ пользователя к нижнему регистру для проверки
    response = message.text.strip().lower()

    # Проверка на "да" и "нет"
    if response == "да":
        # Загружаем данные пользователя
        user_data = load_expense_data(user_id).get(str(user_id), {})
        expenses = user_data.get("expenses", [])

        # Получаем выбранный транспорт
        selected_transport = selected_transports.get(user_id, None)
        if selected_transport:
            transport_info = selected_transport.split(" ")
            selected_brand = transport_info[0].strip()
            selected_model = transport_info[1].strip()
            selected_license_plate = transport_info[2].strip()
        else:
            selected_brand = selected_model = selected_license_plate = None

        if not expenses:
            bot.send_message(user_id, "У вас пока нет сохраненных трат для удаления")
            send_menu(user_id)
            return

        # Фильтруем траты для удаления
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
        bot.send_message(user_id, f"Все траты для транспорта *{selected_brand} {selected_model} {selected_license_plate}* успешно удалены", parse_mode="Markdown")
    elif response == "нет":
        bot.send_message(user_id, "Удаление трат отменено")
    else:
        # Ответ для неподходящих сообщений
        bot.send_message(user_id, "Пожалуйста, введите *ДА* для подтверждения или *НЕТ* для отмены", parse_mode='Markdown')
        bot.register_next_step_handler(message, confirm_delete_all_expenses)
        return

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
        expense["transport"]["license_plate"] == deleted_expense["transport"]["license_plate"] and
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
            f"{transport['brand']} {transport['model']} {transport['license_plate']}",
            expense["category"],
            expense["name"],
            expense["date"],
            float(expense["amount"]),  # Сохраняем сумму как число
            expense["description"],
        ]
        summary_sheet.append(row_data)

    # Обновление индивидуальных листов для каждого транспорта
    unique_transports = set((exp["transport"]["brand"], exp["transport"]["model"], exp["transport"]["license_plate"]) for exp in expenses)

    # Удаляем старые листы для уникальных транспортов
    for sheet_name in workbook.sheetnames:
        if sheet_name != "Summary" and (sheet_name.split('_')[0], sheet_name.split('_')[1], sheet_name.split('_')[2]) not in unique_transports:
            del workbook[sheet_name]

    for brand, model, license_plate in unique_transports:
        sheet_name = f"{brand}_{model}_{license_plate}"
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
            if (expense["transport"]["brand"], expense["transport"]["model"], expense["transport"]["license_plate"]) == (brand, model, license_plate):
                row_data = [
                    f"{brand} {model} {license_plate}",
                    expense["category"],
                    expense["name"],
                    expense["date"],
                    float(expense["amount"]),  # Сохраняем сумму как число
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

user_transport = {}  # Это должно быть вашим хранилищем данных о транспорте

# Обработка данных о ремонтах
def save_repair_data(user_id, user_data, selected_transport=None):
    # Ваш код сохранения
    if selected_transport:
        user_data["selected_transport"] = selected_transport
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

    # Добавляем поле selected_transport для данного пользователя
    user_data["selected_transport"] = selected_transport

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(user_data, file, ensure_ascii=False, indent=4)

def load_repair_data(user_id):
    # Путь к файлу в новой папке
    folder_path = os.path.join("data base", "repairs")
    file_path = os.path.join(folder_path, f"{user_id}_repairs.json")
    
    # Проверка, существует ли файл, перед его открытием
    if not os.path.exists(file_path):
        return {"user_categories": [], "selected_transport": ""}  # Если файла нет, возвращаем пустой словарь с пустым списком категорий

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            if not isinstance(data, dict):
                raise ValueError("Данные не являются словарем.")
            if "selected_transport" not in data:
                data["selected_transport"] = ""  # Добавляем поле, если его нет
    except (FileNotFoundError, ValueError) as e:
        print("Ошибка аагрузки данных:", e)
        data = {"user_categories": [], "selected_transport": ""}  # Обеспечиваем наличие пустого списка категорий
    return data


def get_user_repair_categories(user_id):
    data = load_repair_data(user_id)
    system_categories = ["Без категории", "ТО", "Ремонт", "Запчасть", "Диагностика", "Электрика", "Кузов"]
    user_categories = data.get("user_categories", [])
    return system_categories + user_categories

def add_repair_category(user_id, new_category):
    data = load_repair_data(user_id)
    if "user_categories" not in data:
        data["user_categories"] = []
    if new_category not in data["user_categories"]:
        data["user_categories"].append(new_category)
    save_repair_data(user_id, data)

def remove_repair_category(user_id, category_to_remove):
    data = load_repair_data(user_id)
    if "user_categories" in data and category_to_remove in data["user_categories"]:
        data["user_categories"].remove(category_to_remove)
        save_repair_data(user_id, data)

@bot.message_handler(func=lambda message: message.text == "Записать ремонт")
@restricted
@track_user_activity
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

def handle_transport_selection_for_repair(message):
    user_id = message.from_user.id

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
        formatted_transport = f"{transport['brand']} {transport['model']} ({transport['license_plate']})"
        if formatted_transport == selected_transport:
            brand, model, license_plate = transport['brand'], transport['model'], transport['license_plate']
            break
    else:
        # Отправляем сообщение об ошибке и добавляем кнопки возврата в меню
        bot.send_message(user_id, "Не удалось найти указанный транспорт. Пожалуйста, выберите снова")

        # Формируем клавиатуру с кнопками выбора транспорта и кнопками возврата в меню
        markup = get_user_transport_keyboard(user_id)
        markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        markup.add(types.KeyboardButton("В главное меню"))

        bot.send_message(user_id, "Выберите транспорт или добавьте новый:", reply_markup=markup)
        bot.register_next_step_handler(message, handle_transport_selection_for_repair)
        return

    # Продолжение процесса после выбора транспорта
    process_category_selection_repair(user_id, brand, model, license_plate)

from functools import partial

def process_category_selection_repair(user_id, brand, model, license_plate):
    categories = get_user_repair_categories(user_id)

    # Смайлы для категорий
    system_emoji = "🔹"
    user_emoji = "🔸"

    # Добавление смайлов к категориям: первые 7 считаются системными
    category_list = "\n".join(
        f"{system_emoji if i < 7 else user_emoji} {i + 1}. {category}"
        for i, category in enumerate(categories)
    )
    category_list = f"*Выберите категорию:*\n\n{category_list}"

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
    
    # Используем partial для передачи дополнительных параметров
    bot.register_next_step_handler(prompt_message, partial(get_repair_category, brand=brand, model=model, license_plate=license_plate))

def get_repair_category(message, brand, model, license_plate):
    user_id = message.from_user.id
    selected_index = message.text.strip() if message.text else ""

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, partial(get_repair_category, brand=brand, model=model, license_plate=license_plate))
        return
    
    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):  
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, partial(get_repair_category, brand=brand, model=model, license_plate=license_plate))
        return

    if selected_index == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return
    elif selected_index == "В главное меню":
        return_to_menu(message)
        return

    if selected_index == 'Добавить категорию':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(user_id, "Введите название новой категории:", reply_markup=markup)
        bot.register_next_step_handler(message, partial(add_new_repair_category, brand=brand, model=model, license_plate=license_plate))
        return

    if selected_index == 'Удалить категорию':
        handle_repair_category_removal(message, brand, model, license_plate)
        return

    if selected_index.isdigit():
        index = int(selected_index) - 1
        categories = get_user_repair_categories(user_id)
        if 0 <= index < len(categories):
            selected_category = categories[index]
            proceed_to_repair_name(message, selected_category, brand, model, license_plate)
        else:
            bot.send_message(user_id, "Неверный ввод категории. Попробуйте еще раз")
            bot.register_next_step_handler(message, partial(get_repair_category, brand=brand, model=model, license_plate=license_plate))
    else:
        bot.send_message(user_id, "Пожалуйста, введите номер категории")
        bot.register_next_step_handler(message, partial(get_repair_category, brand=brand, model=model, license_plate=license_plate))

def add_new_repair_category(message, brand, model, license_plate):
    user_id = message.from_user.id

    # Проверка на пустое или None значение
    if not message.text:
        bot.send_message(user_id, "Пожалуйста, введите название категории")
        bot.register_next_step_handler(message, partial(add_new_repair_category, brand=brand, model=model, license_plate=license_plate))
        return

    new_category = message.text.strip()

    system_categories = ["Без категории", "ТО", "Ремонт", "Запчасть", "Диагностика", "Электрика", "Кузов"]

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, partial(add_new_repair_category, brand=brand, model=model, license_plate=license_plate))
        return
    
    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):  
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, partial(add_new_repair_category, brand=brand, model=model, license_plate=license_plate))
        return


    if new_category in system_categories:
        bot.send_message(user_id, "Эта категория уже существует в системе")
        process_category_selection_repair(user_id, brand, model, license_plate)
        return

    # Сохранение новой категории
    data = load_repair_data(user_id)
    if new_category not in data["user_categories"]:
        data["user_categories"].append(new_category)
        # Сохраняем изменения в файл
        with open(os.path.join("data base", "repairs", f"{user_id}_repairs.json"), "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

        bot.send_message(user_id, f"Категория *{new_category}* успешно добавлена", parse_mode="Markdown")
    else:
        bot.send_message(user_id, "Эта категория уже существует")

    process_category_selection_repair(user_id, brand, model, license_plate)

def handle_repair_category_removal(message, brand, model, license_plate):
    user_id = message.from_user.id
    categories = get_user_repair_categories(user_id)

    # Определение системных категорий
    system_categories = ["Без категории", "ТО", "Ремонт", "Запчасть", "Диагностика", "Электрика", "Кузов"]

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, partial(handle_repair_category_removal, brand=brand, model=model, license_plate=license_plate))
        return
    
    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):  
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, partial(handle_repair_category_removal, brand=brand, model=model, license_plate=license_plate))
        return

    if not categories:
        bot.send_message(user_id, "Нет доступных категорий для удаления")
        process_category_selection_repair(user_id, brand, model, license_plate)
        return

    # Смайлы для категорий
    system_emoji = "🔹"
    user_emoji = "🔸"

    # Создание текста с жирным шрифтом для сообщения с добавленными смайликами
    category_list = "\n".join(
        f"{system_emoji if category in system_categories else user_emoji} {i + 1}. {category}"
        for i, category in enumerate(categories)
    )
    bot.send_message(user_id, f"Выберите категорию для удаления или 0 для отмены:\n\n{category_list}")

    # Создание кнопок
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")
    bot.send_message(user_id, "Выберите действие:", reply_markup=markup)

    bot.register_next_step_handler(message, remove_repair_category, categories, system_categories, brand, model, license_plate)

def remove_repair_category(message, categories, system_categories, brand, model, license_plate):
    user_id = message.from_user.id

    # Проверка на нажатие кнопки '0' для отмены
    if message.text == "0":
        # Возвращаемся к выбору категории для записи
        process_category_selection_repair(user_id, brand, model, license_plate)
        return

    # Проверка на нажатие кнопок
    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return
    elif message.text == "В главное меню":
        return_to_menu(message)
        return

    # Проверяем, что message.text не является пустым или None
    if message.text:
        try:
            # Преобразуем текст в целое число
            index = int(message.text) - 1
            if 0 <= index < len(categories):
                removed_category = categories[index]

                # Проверка, является ли категория системной
                if removed_category in system_categories:
                    bot.send_message(user_id, "Это системная категория, удаление невозможно. Попробуйте еще раз")
                    # Ждем повторного ввода
                    bot.register_next_step_handler(message, remove_repair_category, categories, system_categories, brand, model, license_plate)
                    return

                # Удаление категории
                data = load_repair_data(user_id)
                data["user_categories"].remove(removed_category)

                # Сохраняем изменения в файл
                with open(os.path.join("data base", "repairs", f"{user_id}_repairs.json"), "w", encoding="utf-8") as file:
                    json.dump(data, file, ensure_ascii=False, indent=4)

                bot.send_message(user_id, f"Категория *{removed_category}* успешно удалена", parse_mode="Markdown")
                # После успешного удаления, можно вернуть пользователя обратно к выбору категории
                process_category_selection_repair(user_id, brand, model, license_plate)

            else:
                bot.send_message(user_id, "Неверный номер категории. Попробуйте снова")
                # Ждем повторного ввода
                bot.register_next_step_handler(message, remove_repair_category, categories, system_categories, brand, model, license_plate)

        except ValueError:
            bot.send_message(user_id, "Пожалуйста, введите корректный номер категории")
            # Ждем повторного ввода
            bot.register_next_step_handler(message, remove_repair_category, categories, system_categories, brand, model, license_plate)
    else:
        bot.send_message(user_id, "Пожалуйста, введите номер категории")
        # Ждем повторного ввода
        bot.register_next_step_handler(message, remove_repair_category, categories, system_categories, brand, model, license_plate)

def proceed_to_repair_name(message, selected_category, brand, model, license_plate):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите название ремонта:", reply_markup=markup)
    bot.register_next_step_handler(message, get_repair_name, selected_category, brand, model, license_plate)

def get_repair_name(message, selected_category, brand, model, license_plate):
    user_id = message.from_user.id

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(
            message,
            partial(get_repair_name, selected_category=selected_category, brand=brand, model=model, license_plate=license_plate)
        )
        return
    
    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):  
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(
            message,
            partial(get_repair_name, selected_category=selected_category, brand=brand, model=model, license_plate=license_plate)
        )
        return

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
    bot.register_next_step_handler(message, get_repair_description, selected_category, repair_name, brand, model, license_plate)

def get_repair_description(message, selected_category, repair_name, brand, model, license_plate):
    user_id = message.from_user.id

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(
            message,
            partial(get_repair_description, selected_category=selected_category, repair_name=repair_name, brand=brand, model=model, license_plate=license_plate)
        )
        return
    
    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):  
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(
            message,
            partial(get_repair_description, selected_category=selected_category, repair_name=repair_name, brand=brand, model=model, license_plate=license_plate)
        )
        return

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
    bot.register_next_step_handler(message, get_repair_date, selected_category, repair_name, repair_description, brand, model, license_plate)

def is_valid_date(date_str):
    # Проверяем формат даты: ДД.ММ.ГГГГ
    pattern = r'^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.(2000|20[01][0-9]|202[0-9]|203[0-9]|[2-9][0-9]{3})$'
    return bool(re.match(pattern, date_str))

def get_repair_date(message, selected_category, repair_name, repair_description, brand, model, license_plate):
    user_id = message.from_user.id

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(
            message, 
            partial(
                get_repair_date, 
                selected_category=selected_category, 
                repair_name=repair_name, 
                repair_description=repair_description, 
                brand=brand, 
                model=model, 
                license_plate=license_plate
            )
        )
        return

    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):  
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(
            message, 
            partial(
                get_repair_date, 
                selected_category=selected_category, 
                repair_name=repair_name, 
                repair_description=repair_description, 
                brand=brand, 
                model=model, 
                license_plate=license_plate
            )
        )
        return

    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_menu_2(message)
        else:
            return_to_menu(message)
        return

    repair_date = message.text

    # Проверка формата даты
    if not is_valid_date(repair_date):
        bot.send_message(user_id, "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ")
        bot.register_next_step_handler(
            message, 
            get_repair_date, 
            selected_category, 
            repair_name, 
            repair_description, 
            brand, 
            model, 
            license_plate
        )
        return

    # Ввод суммы
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите сумму ремонта:", reply_markup=markup)
    bot.register_next_step_handler(
        message, 
        save_repair_data_final, 
        selected_category, 
        repair_name, 
        repair_description, 
        repair_date, 
        brand, 
        model, 
        license_plate, 
        f"{brand} {model} {license_plate}"  # Здесь передаем selected_transport
    )

def save_repair_data_final(message, selected_category, repair_name, repair_description, repair_date, brand, model, license_plate, selected_transport):
    user_id = message.from_user.id

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(
            message,
            partial(
                save_repair_data_final,
                selected_category=selected_category,
                repair_name=repair_name,
                repair_description=repair_description,
                repair_date=repair_date,
                brand=brand,
                model=model,
                license_plate=license_plate,
                selected_transport=selected_transport
            )
        )
        return

    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(
            message,
            partial(
                save_repair_data_final,
                selected_category=selected_category,
                repair_name=repair_name,
                repair_description=repair_description,
                repair_date=repair_date,
                brand=brand,
                model=model,
                license_plate=license_plate,
                selected_transport=selected_transport
            )
        )
        return

    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_menu_2(message)
        else:
            return_to_menu(message)
        return

    try:
        # Преобразуем введённую сумму в число с плавающей точкой
        repair_amount = float(message.text)

        # Формирование данных о ремонте
        repair_data = {
            "category": selected_category,
            "name": repair_name,
            "date": repair_date,
            "amount": repair_amount,
            "description": repair_description,
            "transport": {
                "brand": brand,
                "model": model,
                "license_plate": license_plate
            }
        }

        # Загрузка данных о ремонтах пользователя
        data = load_repair_data(user_id)
        if str(user_id) not in data:
            data[str(user_id)] = {"repairs": []}

        # Добавление нового ремонта
        repairs = data[str(user_id)].get("repairs", [])
        repairs.append(repair_data)
        data[str(user_id)]["repairs"] = repairs

        # Сохранение данных в базу и Excel
        save_repair_data(user_id, data, selected_transport)  # Сохранение в базу
        save_repair_to_excel(user_id, repair_data)          # Сохранение в Excel

        bot.send_message(user_id, "Ремонт успешно записан")
        send_menu(user_id)

    except ValueError:
        bot.send_message(user_id, "Пожалуйста, введите корректную сумму")
        bot.register_next_step_handler(
            message,
            partial(
                save_repair_data_final,
                selected_category=selected_category,
                repair_name=repair_name,
                repair_description=repair_description,
                repair_date=repair_date,
                brand=brand,
                model=model,
                license_plate=license_plate,
                selected_transport=selected_transport
            )
        )


def save_repair_to_excel(user_id, repair_data):
    # Путь к Excel-файлу пользователя для ремонта
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
        transport_sheet_name = f"{repair_data['transport']['brand']}_{repair_data['transport']['model']}_{repair_data['transport']['license_plate']}"
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
                f"{repair_data['transport']['brand']} {repair_data['transport']['model']} {repair_data['transport']['license_plate']}",
                repair_data["category"],
                repair_data["name"],
                repair_data["date"],
                float(repair_data["amount"]),  # Сохраняем сумму как число
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
        print(f"Ошибка при сохранении данных в Excel: {e}")

        
# (11.5) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "ПОСМОТРЕТЬ РЕМОНТЫ") ---------------

selected_repair_transport_dict = {}

# Функция для фильтрации ремонтов по транспорту
def filter_repairs_by_transport(user_id, repairs):
    selected_transport = selected_repair_transport_dict.get(user_id)
    
    # Если транспорт не выбран, возвращаем весь список ремонтов
    if not selected_transport:
        return repairs

    # Форматирование строки транспорта для фильтрации
    filtered_repairs = [
        repair for repair in repairs 
        if f"{repair['transport']['brand']} {repair['transport']['model']} ({repair['transport']['license_plate']})" == selected_transport
    ]
    return filtered_repairs

# Функция для отправки сообщений с разделением на части (общая)
def send_message_with_split(user_id, message_text):
    bot.send_message(user_id, message_text, parse_mode="Markdown")

# Функция для отправки меню для ремонта
def send_repair_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Ремонты (месяц)")
    item2 = types.KeyboardButton("Ремонты (год)")
    item3 = types.KeyboardButton("Ремонты (все время)")
    item4 = types.KeyboardButton("Ремонты (по категориям)")
    item5 = types.KeyboardButton("Посмотреть ремонты в EXCEL")
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item4, item1)
    markup.add(item2, item3)
    markup.add(item5)
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Выберите вариант просмотра ремонтов:", reply_markup=markup)

# Обработчик для просмотра ремонтов
@bot.message_handler(func=lambda message: message.text == "Посмотреть ремонты")
@restricted
@track_user_activity
def view_repairs(message):
    user_id = message.from_user.id

    # Загружаем данные о транспорте
    transport_list = load_transport_data(user_id)

    if not transport_list:
        bot.send_message(user_id, "У вас нет сохраненного транспорта. Хотите добавить транспорт?", reply_markup=create_transport_options_markup())
        bot.register_next_step_handler(message, ask_add_transport)
        return

    # Если транспорт есть, формируем клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Группируем кнопки по 2 на строку
    transport_buttons = [
        types.KeyboardButton(f"{transport['brand']} {transport['model']} ({transport['license_plate']})")
        for transport in transport_list
    ]
    for i in range(0, len(transport_buttons), 2):
        markup.add(*transport_buttons[i:i+2])

    # Добавляем кнопки возврата
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main)

    bot.send_message(user_id, "Выберите ваш транспорт для просмотра ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection_for_repairs)

# Обработчик выбора транспорта для ремонта
def handle_transport_selection_for_repairs(message):
    user_id = message.from_user.id
    selected_transport = message.text

    # Обработка возврата в меню
    if selected_transport == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if selected_transport == "В главное меню":
        return_to_menu(message)
        return

    # Сохраняем выбранный транспорт для пользователя
    selected_repair_transport_dict[user_id] = selected_transport

    # Уведомляем пользователя о выбранном транспорте
    bot.send_message(
        user_id,
        f"Показываю ремонты для транспорта: *{selected_transport}*",
        parse_mode="Markdown"
    )

    # Отображаем меню ремонтов
    send_repair_menu(user_id)


@bot.message_handler(func=lambda message: message.text == "Посмотреть ремонты в EXCEL")
@restricted
@track_user_activity
def send_repairs_excel(message):
    user_id = message.from_user.id

    # Путь к Excel файлу
    excel_path = os.path.join("data base", "repairs", "excel", f"{user_id}_repairs.xlsx")

    # Проверяем наличие файла
    if not os.path.exists(excel_path):
        bot.send_message(user_id, "Файл с вашими ремонтами не найден")
        return

    # Отправка файла пользователю
    with open(excel_path, 'rb') as excel_file:
        bot.send_document(user_id, excel_file)

MAX_MESSAGE_LENGTH = 4096

def send_message_with_split(user_id, message_text):
    """Отправляет сообщение пользователю, разбивая на части, если превышена максимальная длина."""
    if len(message_text) <= MAX_MESSAGE_LENGTH:
        bot.send_message(user_id, message_text, parse_mode="Markdown")
    else:
        message_parts = [
            message_text[i:i + MAX_MESSAGE_LENGTH] 
            for i in range(0, len(message_text), MAX_MESSAGE_LENGTH)
        ]
        for part in message_parts:
            bot.send_message(user_id, part, parse_mode="Markdown")

MAX_MESSAGE_LENGTH = 4096

def send_message_with_split(user_id, message_text):
    """Отправляет сообщение пользователю, разбивая на части, если превышена максимальная длина."""
    if len(message_text) <= MAX_MESSAGE_LENGTH:
        bot.send_message(user_id, message_text, parse_mode="Markdown")
    else:
        message_parts = [
            message_text[i:i + MAX_MESSAGE_LENGTH] 
            for i in range(0, len(message_text), MAX_MESSAGE_LENGTH)
        ]
        for part in message_parts:
            bot.send_message(user_id, part, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Ремонты (по категориям)")
@restricted
@track_user_activity
def view_repairs_by_category(message):
    user_id = message.from_user.id
    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])

    # Фильтруем ремонты по выбранному транспорту
    repairs = filter_repairs_by_transport(user_id, repairs)

    # Получаем уникальные категории ремонтов для выбранного транспорта
    categories = {repair['category'] for repair in repairs}  # Сохраняем категории как есть

    if not categories:
        bot.send_message(user_id, "*Нет доступных категорий* для выбранного транспорта", parse_mode="Markdown")
        send_menu1(user_id)  # Возврат в меню трат и ремонтов
        return

    category_buttons = [types.KeyboardButton(category) for category in categories]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*category_buttons)
    item_return_to_repairs = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_return_to_main = types.KeyboardButton("В главное меню")
    markup.add(item_return_to_repairs)
    markup.add(item_return_to_main)

    bot.send_message(user_id, "Выберите категорию для просмотра ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_repair_category_selection)

# Обработчик выбора категории ремонтов
def handle_repair_category_selection(message):
    user_id = message.from_user.id
    selected_category = message.text.strip().lower()  # Преобразуем выбранную категорию в нижний регистр

    # Проверка на пустую строку или "Вернуться в меню"
    if not selected_category or selected_category == "вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return
    if selected_category == "в главное меню":
        return_to_menu(message)
        return

    # Загружаем данные
    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])

    # Фильтруем ремонты по выбранному транспорту
    repairs = filter_repairs_by_transport(user_id, repairs)

    # Преобразуем все категории в нижний регистр для корректного сравнения
    available_categories = {repair['category'].lower() for repair in repairs}

    # Проверяем, существует ли выбранная категория
    if selected_category not in available_categories:
        bot.send_message(user_id, "Выбранная категория не найдена. Пожалуйста, выберите корректную категорию")
        view_repairs_by_category(message)  # Запрашиваем повторный ввод категории
        return

    # Фильтруем ремонты по выбранной категории
    category_repairs = [repair for repair in repairs if repair['category'].lower() == selected_category]

    total_repairs_amount = 0
    repair_details = []

    for index, repair in enumerate(category_repairs, start=1):
        repair_name = repair.get("name", "Без названия")
        repair_date = repair.get("date", "")
        repair_amount = float(repair.get("amount", 0))
        total_repairs_amount += repair_amount

        repair_details.append(
            f"🔧 *№ {index}*\n\n"
            f"📂 *Категория:* {repair['category']}\n"  # Отображаем категорию как есть
            f"📌 *Название:* {repair_name}\n"
            f"📅 *Дата:* {repair_date}\n"
            f"💰 *Сумма:* {repair_amount:.2f} руб.\n"
            f"📝 *Описание:* {repair.get('description', 'Без описания')}\n"
        )

    if repair_details:
        message_text = f"*Ремонты* в категории *{selected_category}*:\n\n\n" + "\n\n".join(repair_details)
        send_message_with_split(user_id, message_text)
        bot.send_message(
            user_id,
            f"Итоговая сумма ремонтов в категории *{selected_category}*: *{total_repairs_amount:.2f}* руб.",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            user_id,
            f"В категории *{selected_category}* ремонтов не найдено",
            parse_mode="Markdown"
        )

    # Возвращаем пользователя в меню выбора категорий
    send_repair_menu(user_id) # Запрашиваем выбор категории заново

# Обработчик ремонтов за месяц
MAX_MESSAGE_LENGTH = 4096

def send_message_with_split(user_id, message_text):
    """Отправляет сообщение пользователю, разбивая на части, если превышена максимальная длина."""
    if len(message_text) <= MAX_MESSAGE_LENGTH:
        bot.send_message(user_id, message_text, parse_mode="Markdown")
    else:
        message_parts = [
            message_text[i:i + MAX_MESSAGE_LENGTH] 
            for i in range(0, len(message_text), MAX_MESSAGE_LENGTH)
        ]
        for part in message_parts:
            bot.send_message(user_id, part, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Ремонты (месяц)")
@restricted
@track_user_activity
def view_repairs_by_month(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main)

    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для просмотра ремонтов за этот период:", reply_markup=markup)
    bot.register_next_step_handler(message, get_repairs_by_month)


def get_repairs_by_month(message):
    user_id = message.from_user.id
    date = message.text.strip() if message.text else None

    # Проверяем, есть ли текст в сообщении
    if not date:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_repairs_by_month)
        return

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_repairs_by_month)
        return

    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):
        bot.send_message(user_id, "Извините, но отправка смайликов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_repairs_by_month)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    # Проверка формата и диапазонов месяца и года
    if "." in date:
        parts = date.split(".")
        if len(parts) == 2:
            month, year = parts
            if month.isdigit() and year.isdigit() and 1 <= int(month) <= 12 and 2000 <= int(year) <= 3000:
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
                                f"🔧 *№ {index}*\n\n"
                                f"📂 *Категория:* {category}\n"
                                f"📌 *Название:* {repair_name}\n"
                                f"📅 *Дата:* {repair_date}\n"
                                f"💰 *Сумма:* {amount} руб.\n"
                                f"📝 *Описание:* {description}\n"
                            )

                if repair_details:
                    message_text = f"Ремонты за *{date}* месяц:\n\n\n" + "\n\n".join(repair_details)
                    send_message_with_split(user_id, message_text)
                    bot.send_message(user_id, f"Итоговая сумма ремонтов за *{date}* месяц: *{total_repairs}* руб.", parse_mode="Markdown")
                else:
                    bot.send_message(user_id, f"За *{date}* месяц ремонтов не найдено", parse_mode="Markdown")

                send_repair_menu(user_id)  # Возвращаемся в меню после отображения информации
            else:
                bot.send_message(user_id, "Пожалуйста, введите корректный месяц и год в формате ММ.ГГГГ")
                bot.register_next_step_handler(message, get_repairs_by_month)
                return
        else:
            bot.send_message(user_id, "Пожалуйста, введите дату в формате ММ.ГГГГ")
            bot.register_next_step_handler(message, get_repairs_by_month)
            return
    else:
        bot.send_message(user_id, "Пожалуйста, введите дату в формате ММ.ГГГГ")
        bot.register_next_step_handler(message, get_repairs_by_month)
        return

# Обработчик ремонтов за год
MAX_MESSAGE_LENGTH = 4096

def send_message_with_split(user_id, message_text):
    """Отправляет сообщение пользователю, разбивая на части, если превышена максимальная длина."""
    if len(message_text) <= MAX_MESSAGE_LENGTH:
        bot.send_message(user_id, message_text, parse_mode="Markdown")
    else:
        message_parts = [
            message_text[i:i + MAX_MESSAGE_LENGTH] 
            for i in range(0, len(message_text), MAX_MESSAGE_LENGTH)
        ]
        for part in message_parts:
            bot.send_message(user_id, part, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Ремонты (год)")
@restricted
@track_user_activity
def view_repairs_by_year(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main)

    bot.send_message(user_id, "Введите год в формате (ГГГГ) для просмотра ремонтов за этот год:", reply_markup=markup)
    bot.register_next_step_handler(message, get_repairs_by_year)

def get_repairs_by_year(message):
    user_id = message.from_user.id

    # Проверяем, что сообщение содержит текст
    if not message.text:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_repairs_by_year)
        return

    year_input = message.text.strip()

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_repairs_by_year)
        return

    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, get_repairs_by_year)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    # Проверка, что введено четырехзначное число
    if not year_input.isdigit() or len(year_input) != 4:
        bot.send_message(user_id, "Пожалуйста, введите год в формате ГГГГ.")
        bot.register_next_step_handler(message, get_repairs_by_year)
        return

    # Преобразуем год в число и проверяем диапазон
    year = int(year_input)
    if year < 2000 or year > 3000:
        bot.send_message(user_id, "Введите год в формате ГГГГ.")
        bot.register_next_step_handler(message, get_repairs_by_year)
        return

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
                        f"🔧 *№ {index}*\n\n"
                        f"📂 *Категория:* {category}\n"
                        f"📌 *Название:* {repair_name}\n"
                        f"📅 *Дата:* {repair_date}\n"
                        f"💰 *Сумма:* {amount} руб.\n"
                        f"📝 *Описание:* {description}\n"
                    )

    if repair_details:
        message_text = f"Ремонты за *{year}* год:\n\n\n" + "\n\n".join(repair_details)
        send_message_with_split(user_id, message_text)
        bot.send_message(user_id, f"Итоговая сумма ремонтов за *{year}* год: *{total_repairs}* руб.", parse_mode="Markdown")
    else:
        bot.send_message(user_id, f"За *{year}* год ремонтов не найдено", parse_mode="Markdown")

    # Возвращаемся в меню после отображения информации
    send_repair_menu(user_id)
    
# Обработчик всех ремонтов
MAX_MESSAGE_LENGTH = 4096

def send_message_with_split(user_id, message_text):
    """Отправляет сообщение пользователю, разбивая на части, если превышена максимальная длина."""
    if len(message_text) <= MAX_MESSAGE_LENGTH:
        bot.send_message(user_id, message_text, parse_mode="Markdown")
    else:
        message_parts = [
            message_text[i:i + MAX_MESSAGE_LENGTH] 
            for i in range(0, len(message_text), MAX_MESSAGE_LENGTH)
        ]
        for part in message_parts:
            bot.send_message(user_id, part, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Ремонты (все время)")
@restricted
@track_user_activity
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
            f"🔧 *№ {index}*\n\n"
            f"📂 *Категория:* {category}\n"
            f"📌 *Название:* {repair_name}\n"
            f"📅 *Дата:* {repair_date}\n"
            f"💰 *Сумма:* {amount} руб.\n"
            f"📝 *Описание:* {description}\n"
        )

    if repair_details:
        message_text = "*Все* ремонты:\n\n\n" + "\n\n".join(repair_details)
        send_message_with_split(user_id, message_text)
        bot.send_message(user_id, f"Итоговая сумма всех ремонтов: *{total_repairs}* руб.", parse_mode="Markdown")
    else:
        bot.send_message(user_id, "Ремонтов не найдено", parse_mode="Markdown")

    # Возвращаемся в меню после отображения информации
    send_repair_menu(user_id)

# (11.9) --------------- КОД ДЛЯ "РЕМОНТОВ" (ОБРАБОТЧИК "УДАЛИТЬ РЕМОНТЫ") ---------------

selected_repair_transports = {}



# Сохранение выбранного транспорта для ремонтов
def save_selected_repair_transport(user_id, selected_transport):
    user_data = load_repair_data(user_id).get(str(user_id), {})
    user_data["selected_transport"] = selected_transport
    save_repair_data(user_id, {str(user_id): user_data})

@bot.message_handler(func=lambda message: message.text == "Удалить ремонты")
@restricted
@track_user_activity
def delete_repairs_menu(message):
    user_id = message.from_user.id

    # Загружаем данные о транспорте
    transport_data = load_transport_data(user_id)
    if not transport_data:
        # Если транспортов нет, предлагаем добавить
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_add_transport = types.KeyboardButton("Добавить транспорт")
        item_cancel = types.KeyboardButton("Вернуться в меню трат и ремонтов")
        markup.add(item_add_transport)
        markup.add(item_cancel)
        bot.send_message(user_id, "У вас нет сохраненного транспорта. Хотите добавить транспорт?", reply_markup=markup)
        bot.register_next_step_handler(message, ask_add_transport)
        return

    # Формируем клавиатуру с транспортами
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    transport_buttons = [
        types.KeyboardButton(f"{transport['brand']} {transport['model']} ({transport['license_plate']})")
        for transport in transport_data
    ]
    for i in range(0, len(transport_buttons), 2):
        markup.add(*transport_buttons[i:i+2])  # Группировка по 2 кнопки в строке

    # Добавляем кнопки возврата
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Выберите транспорт для удаления ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_repair_transport_selection_for_deletion)


def handle_repair_transport_selection_for_deletion(message):
    user_id = message.from_user.id
    selected_transport = message.text.strip()

    # Проверка на возврат в меню
    if selected_transport == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return
    if selected_transport == "В главное меню":
        return_to_menu(message)
        return

    # Сохраняем выбранный транспорт
    selected_repair_transports[user_id] = selected_transport
    save_selected_repair_transport(user_id, selected_transport)

    # Меню выбора опции удаления
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_month = types.KeyboardButton("Del ремонты (месяц)")
    item_license_plate = types.KeyboardButton("Del ремонты (год)")
    item_all_time = types.KeyboardButton("Del ремонты (все время)")
    item_del_category_rep = types.KeyboardButton("Del ремонты (категория)")
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")

    markup.add(item_del_category_rep, item_month)
    markup.add(item_license_plate, item_all_time)
    markup.add(item_return)
    markup.add(item_main_menu)
    bot.send_message(user_id, "Выберите вариант удаления ремонтов:", reply_markup=markup)

repairs_to_delete_dict = {}
selected_repair_categories = {}
user_repairs_to_delete = {}

@bot.message_handler(func=lambda message: message.text == "Del ремонты (категория)")
@restricted
@track_user_activity
def delete_repairs_by_category(message):
    user_id = message.from_user.id
    selected_transport = selected_repair_transports.get(user_id)

    if not selected_transport:
        selected_transport = load_repair_data(user_id).get("selected_transport")
        if not selected_transport:
            bot.send_message(user_id, "Не выбран транспорт")
            send_menu(user_id)
            return

    selected_transport_info = selected_transport.strip().lower().replace('(', '').replace(')', '')

    user_data = load_repair_data(user_id).get(str(user_id), {})
    repairs = user_data.get("repairs", [])

    categories = list({
        repair.get("category")
        for repair in repairs
        if f"{repair.get('transport', {}).get('brand', '').strip().lower()} {repair.get('transport', {}).get('model', '').strip().lower()} {str(repair.get('transport', {}).get('license_plate', '')).strip().lower()}" == selected_transport_info
    })

    if not categories:
        bot.send_message(user_id, "Нет категорий ремонтов для выбранного транспорта")
        send_menu(user_id)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(*[types.KeyboardButton(category) for category in categories])
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))

    bot.send_message(user_id, "Выберите категорию для удаления ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_repair_category_selection_for_deletion)


def handle_repair_category_selection_for_deletion(message):
    user_id = message.from_user.id
    selected_category = message.text.strip()

    if selected_category in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if selected_category == "Вернуться в меню трат и ремонтов":
            send_menu(user_id)
        else:
            return_to_menu(message)
        return

    selected_repair_categories[user_id] = selected_category

    user_data = load_repair_data(user_id).get(str(user_id), {})
    repairs = user_data.get("repairs", [])

    selected_transport = selected_repair_transports.get(user_id)
    if not selected_transport:
        selected_transport = load_repair_data(user_id).get("selected_transport")
        if not selected_transport:
            bot.send_message(user_id, "Не выбран транспорт")
            send_menu(user_id)
            return

    selected_transport_info = selected_transport.strip().lower().replace('(', '').replace(')', '')

    repairs_to_delete = [
        repair for repair in repairs
        if repair.get("category") == selected_category and
           f"{repair.get('transport', {}).get('brand', '').strip().lower()} {repair.get('transport', {}).get('model', '').strip().lower()} {str(repair.get('transport', {}).get('license_plate', '')).strip().lower()}" == selected_transport_info
    ]

    if not repairs_to_delete:
        bot.send_message(user_id, f"Нет ремонтов в категории *{selected_category.lower()}* для выбранного транспорта", parse_mode="Markdown")
        send_menu(user_id)
        return

    user_repairs_to_delete[user_id] = repairs_to_delete

    repair_list_text = f"Список ремонтов в категории *{selected_category.lower()}*:\n\n\n"
    for index, repair in enumerate(repairs_to_delete, start=1):
        repair_name = repair.get("name", "Без названия")
        repair_date = repair.get("date", "Неизвестно")
        repair_list_text += f"🔧 №{index}. {repair_name} - ({repair_date})\n\n"

    repair_list_text += "\nВведите номер ремонта для удаления или вернитесь в меню:"

    send_long_message(user_id, repair_list_text)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")

    bot.register_next_step_handler(message, delete_repair_confirmation)


def delete_repair_confirmation(message):
    user_id = message.from_user.id

    selected_option = message.text.strip()

    if selected_option in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if selected_option == "Вернуться в меню трат и ремонтов":
            send_menu(user_id)
        else:
            return_to_menu(message)
        return

    if not selected_option.isdigit():
        bot.send_message(user_id, "Введите корректный номер ремонта из списка")
        bot.register_next_step_handler(message, delete_repair_confirmation)
        return

    repair_index = int(selected_option) - 1
    repairs_to_delete = user_repairs_to_delete.get(user_id, [])

    if 0 <= repair_index < len(repairs_to_delete):
        user_data = load_repair_data(user_id).get(str(user_id), {})
        user_repairs = user_data.get("repairs", [])

        deleted_repair = repairs_to_delete.pop(repair_index)
        user_repairs.remove(deleted_repair)
        user_data["repairs"] = user_repairs
        save_repair_data(user_id, {str(user_id): user_data})

        bot.send_message(
            user_id,
            f"Ремонт *{deleted_repair.get('name', 'Без названия')}* успешно удален", parse_mode="Markdown"
        )

        send_menu(user_id)
    else:
        bot.send_message(user_id, "Неверный номер ремонта. Попробуйте снова")
        bot.register_next_step_handler(message, delete_repair_confirmation)

# Удаление ремонтов за месяц
@bot.message_handler(func=lambda message: message.text == "Del ремонты (месяц)")
@restricted
@track_user_activity
def delete_repair_by_month(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)
    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для удаления ремонтов за этот месяц:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_repairs_by_month_handler)

def delete_repairs_by_month_handler(message):
    user_id = message.from_user.id
    month_year = message.text.strip() if message.text else None

    if not month_year:
        bot.send_message(user_id, "Извините, отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_repairs_by_month_handler)
        return

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_repairs_by_month_handler)
        return

    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', month_year):
        bot.send_message(user_id, "Извините, отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_repairs_by_month_handler)
        return

    # Проверка формата месяца и года
    match = re.match(r"^(0[1-9]|1[0-2])\.(20[0-9]{2})$", month_year)
    if not match:
        bot.send_message(user_id, "Введен неверный месяц или год. Пожалуйста, введите корректные данные (ММ.ГГГГ)")
        bot.register_next_step_handler(message, delete_repairs_by_month_handler)
        return

    selected_month, selected_year = match.groups()

    # Проверка выбранного транспорта
    selected_transport = selected_repair_transports.get(user_id)
    if not selected_transport:
        bot.send_message(user_id, "Транспорт не выбран. Пожалуйста, выберите транспорт")
        send_menu(user_id)
        return

    transport_info = selected_transport.split(" ")
    selected_brand = transport_info[0].strip()
    selected_model = transport_info[1].strip()
    selected_license_plate = transport_info[2].strip().replace("(", "").replace(")", "")

    user_data = load_repair_data(user_id).get(str(user_id), {})
    repairs = user_data.get("repairs", [])

    if not repairs:
        bot.send_message(user_id, f"У вас нет сохраненных ремонтов за *{month_year}* месяц", parse_mode="Markdown")
        send_menu(user_id)
        return

    repairs_to_delete = []
    for index, repair in enumerate(repairs, start=1):
        repair_date = repair.get("date", "")

        if not repair_date or len(repair_date.split(".")) != 3:
            continue

        repair_day, repair_month, repair_year = repair_date.split(".")

        if repair_month == selected_month and repair_year == selected_year:
            repair_license_plate = repair.get("transport", {}).get("license_plate", "").strip()
            repair_brand = repair.get("transport", {}).get("brand", "").strip()
            repair_model = repair.get("transport", {}).get("model", "").strip()

            if (repair_license_plate == selected_license_plate and
                repair_brand == selected_brand and
                repair_model == selected_model):
                repairs_to_delete.append((index, repair))

    if repairs_to_delete:
        repairs_to_delete_dict[user_id] = repairs_to_delete

        repair_list_text = f"Список ремонтов для удаления за *{month_year}* месяц:\n\n\n"
        for index, repair in repairs_to_delete:
            repair_name = repair.get("name", "Без названия")
            repair_date = repair.get("date", "Неизвестно")
            repair_list_text += f"🔧 №{index}. {repair_name} - ({repair_date})\n\n"

        repair_list_text += "\nВведите номер ремонта для удаления или вернитесь в меню:"

        send_long_message(user_id, repair_list_text)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.register_next_step_handler(message, confirm_delete_repair_month)
    else:
        bot.send_message(user_id, f"Нет ремонтов для удаления за *{month_year}* месяц", parse_mode="Markdown")
        send_menu(user_id)

def confirm_delete_repair_month(message):
    user_id = message.from_user.id

    if not message.text:
        bot.send_message(user_id, "Извините, отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_repair_month)
        return

    selected_option = message.text.strip()

    if selected_option == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if selected_option == "В главное меню":
        return_to_menu(message)
        return

    if selected_option.isdigit():
        repair_index = int(selected_option) - 1
        repairs_to_delete = repairs_to_delete_dict.get(user_id, [])

        if 0 <= repair_index < len(repairs_to_delete):
            _, deleted_repair = repairs_to_delete.pop(repair_index)

            user_data = load_repair_data(user_id).get(str(user_id), {})
            if "repairs" in user_data and deleted_repair in user_data["repairs"]:
                user_data["repairs"].remove(deleted_repair)
                save_repair_data(user_id, {str(user_id): user_data})

            bot.send_message(
                user_id,
                f"Ремонт *{deleted_repair.get('name', 'Без названия').lower()}* успешно удален",
                parse_mode="Markdown"
            )

            repairs_to_delete_dict[user_id] = repairs_to_delete
            send_menu(user_id)
        else:
            bot.send_message(user_id, "Неверный выбор. Пожалуйста, попробуйте снова")
            bot.register_next_step_handler(message, confirm_delete_repair_month)
    else:
        bot.send_message(user_id, "Некорректный ввод. Пожалуйста, введите номер ремонта")
        bot.register_next_step_handler(message, confirm_delete_repair_month)

# Удаление ремонтов за год
MAX_MESSAGE_LENGTH = 4096

def send_long_message(user_id, message_text):
    """Отправляет сообщение пользователю, разбивая на части, если оно слишком длинное."""
    if len(message_text) <= MAX_MESSAGE_LENGTH:
        bot.send_message(user_id, message_text, parse_mode="Markdown")
    else:
        message_parts = [
            message_text[i:i + MAX_MESSAGE_LENGTH] 
            for i in range(0, len(message_text), MAX_MESSAGE_LENGTH)
        ]
        for part in message_parts:
            bot.send_message(user_id, part, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Del ремонты (год)")
@restricted
@track_user_activity
def delete_repairs_by_year(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)
    bot.send_message(user_id, "Введите год (ГГГГ) для удаления ремонтов за этот год:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_repairs_by_year_handler)

def delete_repairs_by_year_handler(message):
    user_id = message.from_user.id
    year = message.text.strip() if message.text else None

    if not year:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_repairs_by_year_handler)
        return

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_repairs_by_year_handler)
        return

    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', year):  
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, delete_repairs_by_year_handler)
        return

    if year == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if year == "В главное меню":
        return_to_menu(message)
        return

    # Проверка формата года (от 2000 до 3000)
    if not re.match(r"^(20[0-9]{2}|2[1-9][0-9]{2}|3000)$", year):
        bot.send_message(user_id, "Введен неверный год. Пожалуйста, введите корректный год")
        bot.register_next_step_handler(message, delete_repairs_by_year_handler)
        return

    user_data = load_repair_data(user_id).get(str(user_id), {})
    repairs = user_data.get("repairs", [])

    # Получаем данные выбранного транспорта
    selected_transport = selected_repair_transports.get(user_id, None)

    if selected_transport:
        transport_info = selected_transport.split(" ")
        selected_brand = transport_info[0].strip()
        selected_model = transport_info[1].strip()
        selected_license_plate = str(transport_info[2].strip())
    else:
        selected_brand = selected_model = selected_license_plate = None

    if not repairs:
        bot.send_message(user_id, f"У вас пока нет сохраненных ремонтов за *{year}* год для удаления", parse_mode="Markdown")
        send_menu(user_id)
        return

    repairs_to_delete = []
    for index, repair in enumerate(repairs, start=1):
        repair_date = repair.get("date", "")
        repair_year = repair_date.split(".")[2]

        repair_brand = repair.get("transport", {}).get("brand", "").strip()
        repair_model = repair.get("transport", {}).get("model", "").strip()

        if (repair_year == year and
           repair_brand == selected_brand and
           repair_model == selected_model):
            repairs_to_delete.append((index, repair))

    if repairs_to_delete:
        repairs_to_delete_dict[user_id] = repairs_to_delete

        repair_list_text = f"Список ремонтов для удаления за *{year}* год:\n\n\n"
        for index, repair in repairs_to_delete:
            repair_name = repair.get("name", "Без названия")
            repair_date = repair.get("date", "Неизвестно")
            repair_list_text += f"🔧 №{index}. {repair_name} - ({repair_date})\n\n"

        repair_list_text += "\nВведите номер ремонта для удаления или вернитесь в меню:"
        send_long_message(user_id, repair_list_text)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.register_next_step_handler(message, confirm_delete_repair)
    else:
        bot.send_message(user_id, f"За *{year}* год ремонтов не найдено для удаления", parse_mode="Markdown")
        send_menu(user_id)

def confirm_delete_repair(message):
    user_id = message.from_user.id

    if not message.text:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_repair)
        return

    selected_option = message.text.strip()

    if re.search(r'[^\w\s,.?!]', selected_option):
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_repair)
        return

    if selected_option == "Вернуться в меню трат и ремонтов":
        return_to_menu_2(message)
        return

    if selected_option == "В главное меню":
        return_to_menu(message)
        return

    repairs_to_delete = repairs_to_delete_dict.get(user_id, [])

    if selected_option.isdigit():
        repair_index = int(selected_option) - 1

        if 0 <= repair_index < len(repairs_to_delete):
            _, deleted_repair = repairs_to_delete.pop(repair_index)

            user_data = load_repair_data(user_id).get(str(user_id), {})
            user_data["repairs"].remove(deleted_repair)
            save_repair_data(user_id, {str(user_id): user_data})

            bot.send_message(user_id, f"Ремонт *{deleted_repair.get('name', 'Без названия').lower()}* успешно удален", parse_mode="Markdown")

            repairs_to_delete_dict[user_id] = repairs_to_delete
            send_menu(user_id)
        else:
            bot.send_message(user_id, "Неверный выбор. Пожалуйста, попробуйте снова")
            bot.register_next_step_handler(message, confirm_delete_repair)
    else:
        bot.send_message(user_id, "Некорректный ввод. Пожалуйста, введите номер ремонта")
        bot.register_next_step_handler(message, confirm_delete_repair)

# Удаление всех ремонтов
@bot.message_handler(func=lambda message: message.text == "Del ремонты (все время)")
@restricted
@track_user_activity
def delete_all_repairs_for_selected_transport(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    # Запрашиваем подтверждение
    bot.send_message(user_id,
                     "Вы уверены, что хотите удалить все ремонты для выбранного транспорта?\n\n"
                     "Пожалуйста, введите *ДА* для подтверждения или *НЕТ* для отмены.",
                     reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler(message, confirm_delete_all_repairs)
    

def confirm_delete_all_repairs(message):
    user_id = message.from_user.id

    # Проверка на мультимедиа
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_all_repairs)
        return

    # Проверка на смайлики
    if re.search(r'[^\w\s,.?!]', message.text):
        bot.send_message(user_id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_all_repairs)
        return

    # Возврат в меню
    if message.text == "Вернуться в меню трат и ремонтов":
        send_menu(user_id)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    response = message.text.strip().lower()

    # Загружаем данные пользователя
    user_data = load_repair_data(user_id).get(str(user_id), {})
    repairs = user_data.get("repairs", [])

    # Получаем выбранный транспорт
    selected_transport = user_data.get("selected_transport")
    if selected_transport:
        transport_info = selected_transport.split()
        selected_brand = transport_info[0].strip()
        selected_model = transport_info[1].strip()
        selected_license_plate = transport_info[2].strip()
    else:
        selected_brand = selected_model = selected_license_plate = None

    if not repairs:
        bot.send_message(user_id, "У вас пока нет сохраненных ремонтов для удаления")
        send_menu(user_id)
        return

    if response == "да":
        # Фильтруем ремонты для удаления
        repairs_to_keep = []
        for repair in repairs:
            repair_brand = repair.get("transport", {}).get("brand", "").strip()
            repair_model = repair.get("transport", {}).get("model", "").strip()

            # Сравниваем с выбранным транспортом
            if not (repair_brand == selected_brand and repair_model == selected_model):
                repairs_to_keep.append(repair)

        # Обновляем список ремонтов пользователя
        user_data["repairs"] = repairs_to_keep
        save_repair_data(user_id, {str(user_id): user_data})

        update_repairs_excel_file(user_id)

        # Сообщение об успешном удалении
        bot.send_message(user_id, f"Все ремонты для транспорта *{selected_brand} {selected_model} {selected_license_plate}* успешно удалены", parse_mode="Markdown")
    elif response == "нет":
        bot.send_message(user_id, "Удаление ремонтов отменено")
    else:
        # Ответ для неподходящих сообщений
        bot.send_message(user_id, "Пожалуйста, введите *ДА* для подтверждения или *НЕТ* для отмены.", parse_mode='Markdown')
        bot.register_next_step_handler(message, confirm_delete_all_repairs)
        return

    send_menu(user_id)

def delete_repairs(user_id, deleted_repair):
    # Удаляем ремонт из базы данных
    user_data = load_repair_data(user_id).get(str(user_id), {})
    repairs = user_data.get("repairs", [])

    # Удаляем ремонт из списка ремонтов
    repairs = [repair for repair in repairs if not (
        repair["transport"]["brand"] == deleted_repair["transport"]["brand"] and
        repair["transport"]["model"] == deleted_repair["transport"]["model"] and
        repair["transport"]["license_plate"] == deleted_repair["transport"]["license_plate"] and
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

    # Путь к Excel файлу пользователя
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
    if summary_sheet.max_row == 0:  # Если лист пустой
        summary_sheet.append(headers)
        for cell in summary_sheet[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")

    # Заполняем общий лист новыми данными
    for repair in repairs:
        transport = repair["transport"]
        row_data = [
            f"{transport['brand']} {transport['model']} {transport['license_plate']}",
            repair["category"],
            repair["name"],
            repair["date"],
            float(repair["amount"]),  # Сохраняем сумму как число
            repair["description"],
        ]
        summary_sheet.append(row_data)

    # Обновление индивидуальных листов для каждого транспорта
    unique_transports = set((rep["transport"]["brand"], rep["transport"]["model"], rep["transport"]["license_plate"]) for rep in repairs)

    # Удаляем старые листы для уникальных транспортов
    for sheet_name in workbook.sheetnames:
        if sheet_name != "Summary" and (sheet_name.split('_')[0], sheet_name.split('_')[1], sheet_name.split('_')[2]) not in unique_transports:
            del workbook[sheet_name]

    for brand, model, license_plate in unique_transports:
        sheet_name = f"{brand}_{model}_{license_plate}"
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
            if (repair["transport"]["brand"], repair["transport"]["model"], repair["transport"]["license_plate"]) == (brand, model, license_plate):
                row_data = [
                    f"{brand} {model} {license_plate}",
                    repair["category"],
                    repair["name"],
                    repair["date"],
                    float(repair["amount"]),  # Сохраняем сумму как число
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
@restricted
@track_user_activity
def send_welcome(message):

    if not function_states['Поиск мест']:
        bot.send_message(message.chat.id, "Эта функция временно недоступна.")
        return  # Завершаем выполнение функции, если функция деактивирована

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
@restricted
@track_user_activity
def handle_reset_category(message):
    global selected_category
    selected_category = None
    send_welcome(message)

selected_category = None 

# Обработчик для выбора категории
@bot.message_handler(func=lambda message: message.text in {"АЗС", "Автомойки", "Автосервисы", "Парковки", "Эвакуация", "ГИБДД", "Комиссары", "Штрафстоянка"})
@restricted
@track_user_activity
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
        bot.send_message(message.chat.id, f"Отправьте свою геолокацию. Вам будет выдан список ближайших мест по категории - {selected_category.lower()}", reply_markup=keyboard)
    else:
        selected_category = None
        bot.send_message(message.chat.id, "Пожалуйста, выберите категорию из меню.")

# Обработчик для получения геолокации
@bot.message_handler(content_types=['location'])
def handle_location(message):
    global selected_category  # Указываем, что selected_category является глобальной переменной
    user_id = message.chat.id
    latitude = message.location.latitude
    longitude = message.location.longitude

    # Проверяем, включен ли режим анти-радара
    if user_tracking.get(user_id, {}).get('tracking', False):
        # Обновляем местоположение пользователя для анти-радара
        user_tracking[user_id]['location'] = message.location

        # Запускаем трекинг камер для анти-радара, если он не был запущен
        if not user_tracking[user_id].get('started', False):
            user_tracking[user_id]['started'] = True
            track_user_location(user_id, message.location)

        # Прерываем обработку, так как анти-радар активен
        return
    elif selected_category:
        # Логика обработки геолокации для поиска мест
        try:
            location = geolocator.reverse((latitude, longitude), language='ru', timeout=10)
            address = location.address

            # Создание ссылки на Yandex.Карты
            search_url = get_yandex_maps_search_url(latitude, longitude, selected_category)
            short_search_url = shorten_url(search_url)

            # Формирование сообщения
            message_text = f"🏙️ *Ближайшие {selected_category.lower()} по адресу:* \n\n{address}\n\n"
            message_text += f"🗺️ [Ссылка на карту]({short_search_url})"

            # Отправка сообщения
            bot.send_message(message.chat.id, message_text, parse_mode='Markdown')

            # Сброс категории после использования
            selected_category = None

            # Клавиатура для выбора новой категории или возврата в главное меню
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button_reset_category = types.KeyboardButton("Выбрать категорию заново")
            item1 = types.KeyboardButton("В главное меню")
            keyboard.add(button_reset_category)
            keyboard.add(item1)
            bot.send_message(message.chat.id, "Выберите категорию заново или вернитесь в главное меню", reply_markup=keyboard)

        except Exception as e:
            bot.send_message(message.chat.id, f"Произошла ошибка при обработке вашего запроса: {e}")
    else:
        # Если ни анти-радар, ни категория не выбраны, отправляем сообщение о выборе категории
        bot.send_message(message.chat.id, "Пожалуйста, выберите категорию из меню")


#------------------- (НАЧАЛО) КОД ДЛЯ ПОИСКА МЕСТ, РАБОЧИЙ, НЕДОДЕЛАННЫЙ В ПЛАНЕ КАТЕГОРИЙ И ПРОВЕРКИ ВЫДАЧИ, НУЖЕН API------------------------


# geolocator = Nominatim(user_agent="geo_bot")

# user_locations = {}

# def calculate_distance(origin, destination):
#     return geodesic(origin, destination).kilometers

# # (12.2) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (СОКРАЩЕНИЕ ССЫЛОК) ---------------

# def shorten_url(original_url):
#     endpoint = 'https://clck.ru/--'
#     response = requests.get(endpoint, params={'url': original_url})
#     return response.text

# # (12.3) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (АЗС) ---------------

# def get_nearby_fuel_stations(latitude, longitude, user_coordinates):
#     api_url = "https://search-maps.yandex.ru/v1/"
#     params = {
#         "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
#         "text": "АЗС",
#         "lang": "ru_RU",
#         "ll": f"{longitude},{latitude}",
#         "spn": "0.045,0.045", 
#         "type": "biz"
#     }
#     response = requests.get(api_url, params=params)
#     data = response.json()

#     fuel_stations = []
#     for feature in data["features"]:
#         coordinates = feature["geometry"]["coordinates"]
#         name = feature["properties"]["name"]
#         address = feature["properties"]["description"]
#         fuel_stations.append({"name": name, "coordinates": coordinates, "address": address})

#     return fuel_stations

# # (12.4) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (АВТОМОЙКИ) ---------------

# def get_nearby_car_washes(latitude, longitude, user_coordinates):
#     api_url = "https://search-maps.yandex.ru/v1/"
#     params = {
#         "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
#         "text": "Автомойка",
#         "lang": "ru_RU",
#         "ll": f"{longitude},{latitude}",
#         "spn": "0.045,0.045", 
#         "type": "biz"
#     }
#     response = requests.get(api_url, params=params)
#     data = response.json()

#     car_washes = []
#     for feature in data["features"]:
#         coordinates = feature["geometry"]["coordinates"]
#         name = feature["properties"]["name"]
#         address = feature["properties"]["description"]
#         car_washes.append({"name": name, "coordinates": coordinates, "address": address})

#     return car_washes

# # (12.5) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (АВТОСЕРВИС) ---------------

# def get_nearby_auto_services(latitude, longitude, user_coordinates):
#     api_url = "https://search-maps.yandex.ru/v1/"
#     params = {
#         "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
#         "text": "Автосервис",
#         "lang": "ru_RU",
#         "ll": f"{longitude},{latitude}",
#         "spn": "0.045,0.045",
#         "type": "biz"
#     }
#     response = requests.get(api_url, params=params)
#     data = response.json()

#     auto_services = []
#     for feature in data.get("features", []):
#         coordinates = feature.get("geometry", {}).get("coordinates")
#         name = feature.get("properties", {}).get("name")
#         address = feature.get("properties", {}).get("description", "Адрес не указан")
#         if coordinates and name:
#             auto_services.append({"name": name, "coordinates": coordinates, "address": address})

#     return auto_services

# # (12.6) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ПАРКОВКИ) ---------------

# def get_nearby_parking(latitude, longitude, user_coordinates):
#     api_url = "https://search-maps.yandex.ru/v1/"
#     params = {
#         "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
#         "text": "Парковки",
#         "lang": "ru_RU",
#         "ll": f"{longitude},{latitude}",
#         "spn": "0.045,0.045",
#         "type": "biz"
#     }
#     response = requests.get(api_url, params=params)
#     data = response.json()

#     parking_places = []
#     for feature in data["features"]:
#         coordinates = feature["geometry"]["coordinates"]
#         name = feature["properties"]["name"]
#         address = feature["properties"]["description"]
#         parking_places.append({"name": name, "coordinates": coordinates, "address": address})

#     return parking_places

# # (12.7) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ЭВАКУАТОР) ---------------

# def get_nearby_evacuation_services(latitude, longitude, user_coordinates):
#     api_url = "https://search-maps.yandex.ru/v1/"
#     params = {
#         "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
#         "text": "Эвакуация",
#         "lang": "ru_RU",
#         "ll": f"{longitude},{latitude}",
#         "spn": "0.045,0.045",
#         "type": "biz"
#     }
#     response = requests.get(api_url, params=params)
#     data = response.json()

#     evacuation_services = []
#     for feature in data["features"]:
#         coordinates = feature["geometry"]["coordinates"]
#         name = feature["properties"]["name"]
#         address = feature["properties"]["description"]
#         evacuation_services.append({"name": name, "coordinates": coordinates, "address": address})

#     return evacuation_services

# # (12.8) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ГИБДД) ---------------

# def get_nearby_gibdd_mreo(latitude, longitude, user_coordinates):
#     api_url = "https://search-maps.yandex.ru/v1/"
#     params = {
#         "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
#         "text": "ГИБДД",
#         "lang": "ru_RU",
#         "ll": f"{longitude},{latitude}",
#         "spn": "0.045,0.045",
#         "type": "biz"
#     }
#     response = requests.get(api_url, params=params)
#     data = response.json()

#     gibdd_mreo_offices = []
#     for feature in data["features"]:
#         coordinates = feature["geometry"]["coordinates"]
#         name = feature["properties"]["name"]
#         address = feature["properties"]["description"]
#         gibdd_mreo_offices.append({"name": name, "coordinates": coordinates, "address": address})

#     return gibdd_mreo_offices

# # (12.9) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (КОМИССАРЫ) ---------------

# def get_nearby_accident_commissioner(latitude, longitude, user_coordinates):
#     api_url = "https://search-maps.yandex.ru/v1/"
#     params = {
#         "apikey": "af145d41-4168-430b-b7d5-392df4d232cc",
#         "text": "Комиссары",
#         "lang": "ru_RU",
#         "ll": f"{longitude},{latitude}",
#         "spn": "0.045,0.045",
#         "type": "biz"
#     }
#     response = requests.get(api_url, params=params)
#     data = response.json()

#     accident_commissioners = []
#     for feature in data["features"]:
#         coordinates = feature["geometry"]["coordinates"]
#         name = feature["properties"]["name"]
#         address = feature["properties"]["description"]
#         accident_commissioners.append({"name": name, "coordinates": coordinates, "address": address})

#     return accident_commissioners

# # (12.10) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ОБРАБОТЧИК "ПОИСК МЕСТ") ---------------

# @bot.message_handler(func=lambda message: message.text == "Поиск мест")
# def send_welcome(message):
#     user_id = message.chat.id
#     markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

#     button_azs = types.KeyboardButton("АЗС")
#     button_car_wash = types.KeyboardButton("Автомойки")
#     button_auto_service = types.KeyboardButton("Автосервисы")
#     button_parking = types.KeyboardButton("Парковки")
#     button_evacuation = types.KeyboardButton("Эвакуация")
#     button_gibdd_mreo = types.KeyboardButton("ГИБДД")
#     button_accident_commissioner = types.KeyboardButton("Комиссары")

#     item1 = types.KeyboardButton("В главное меню")

#     markup.add(button_azs, button_car_wash, button_auto_service)
#     markup.add(button_parking, button_evacuation, button_gibdd_mreo, button_accident_commissioner)
#     markup.add(item1)

#     bot.send_message(user_id, "Выберите категорию для ближайшего поиска:", reply_markup=markup)

# # (12.11) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ОБРАБОТЧИК "ВЫБОР КАТЕГОРИИ ЗАНОВО") ---------------

# @bot.message_handler(func=lambda message: message.text == "Выбрать категорию заново")
# def handle_reset_category(message):
#     global selected_category
#     selected_category = None
#     send_welcome(message)

# selected_category = None 

# # (12.12) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ОБРАБОТЧИК "ДЛЯ ВЫБОРА КАТЕГОРИИ") ---------------

# @bot.message_handler(func=lambda message: message.text in {"АЗС", "Автомойки", "Автосервисы", "Парковки", "Эвакуация", "ГИБДД", "Комиссары"})
# def handle_menu_buttons(message):
#     global selected_category 
#     if message.text in {"АЗС", "Автомойки", "Автосервисы", "Парковки", "Эвакуация", "ГИБДД", "Комиссары"}:
#         selected_category = message.text 
#         keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
#         button_send_location = types.KeyboardButton("Отправить геолокацию", request_location=True)
#         button_reset_category = types.KeyboardButton("Выбрать категорию заново")
#         item1 = types.KeyboardButton("В главное меню")
#         keyboard.add(button_send_location)
#         keyboard.add(button_reset_category)
#         keyboard.add(item1)
#         bot.send_message(message.chat.id, f"Отправьте свою геолокацию. Вам будет выдан список ближайших {selected_category.lower()}.", reply_markup=keyboard)
#     else:
#         selected_category = None
#         bot.send_message(message.chat.id, "Пожалуйста, выберите категорию из меню.")

# # (12.13) --------------- КОД ДЛЯ "ПОИСКА МЕСТ" (ОБРАБОТЧИК "ГЕОЛОКАЦИЯ") ---------------

# @bot.message_handler(content_types=['location'])
# def handle_location(message):
#     global selected_category, selected_location, user_locations
#     latitude = message.location.latitude
#     longitude = message.location.longitude
#     user_id = message.from_user.id

#     try:
#         location = geolocator.reverse((latitude, longitude), language='ru', timeout=10)
#         address = location.address

#         if selected_category is None:
#             bot.send_message(message.chat.id, "Пожалуйста, выберите категорию из меню.")
#             return

#         user_locations[user_id] = {"address": address, "coordinates": (latitude, longitude)}

#         if selected_category == "АЗС":
#             locations = get_nearby_fuel_stations(latitude, longitude, user_locations[user_id]["coordinates"])
#         elif selected_category == "Автомойки":
#             locations = get_nearby_car_washes(latitude, longitude, user_locations[user_id]["coordinates"])
#         elif selected_category == "Автосервисы":
#             locations = get_nearby_auto_services(latitude, longitude, user_locations[user_id]["coordinates"])
#         elif selected_category == "Парковки":
#             locations = get_nearby_parking(latitude, longitude, user_locations[user_id]["coordinates"])
#         elif selected_category == "Эвакуация":
#             locations = get_nearby_evacuation_services(latitude, longitude, user_locations[user_id]["coordinates"])
#         elif selected_category == "ГИБДД":
#             locations = get_nearby_gibdd_mreo(latitude, longitude, user_locations[user_id]["coordinates"])
#         elif selected_category == "Комиссары":
#             locations = get_nearby_accident_commissioner(latitude, longitude, user_locations[user_id]["coordinates"])

#         selected_location = {"address": address, "coordinates": (latitude, longitude)}

#         # Формирование текста сообщения с использованием смайлов, гиперссылок и Markdown
#         message_text = f"📍 *Ближайшие объекты по адресу:*\n\n🏠 *{address}*\n\n"
#         message_text += f"🔍 *{selected_category}:*\n\n"

#         for location in locations:
#             name = location["name"]
#             coordinates = location["coordinates"]
#             address = location["address"]

#             # Создание ссылки на Яндекс.Карты
#             yandex_maps_url = f"https://yandex.ru/maps/?rtext={user_locations[user_id]['coordinates'][0]},{user_locations[user_id]['coordinates'][1]}~{coordinates[1]},{coordinates[0]}&l=map&rtt=auto&ruri=~ymapsbm1%3A%2F%2Forg%3Foid%3D1847883008%26name%3D{quote(name)}%26address%3D{quote(address)}\n\n"
#             short_yandex_maps_url = shorten_url(yandex_maps_url)

#             # Форматирование каждого пункта с гиперссылкой
#             message_text += f"🚗 *{name}* ({address}):\n[Посмотреть на карте]({short_yandex_maps_url})\n\n"

#         # Отправка отформатированного сообщения с Markdown
#         bot.send_message(message.chat.id, message_text, parse_mode='Markdown')

#         selected_category = None

#         keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
#         button_reset_category = types.KeyboardButton("Выбрать категорию заново")
#         item1 = types.KeyboardButton("В главное меню")
#         keyboard.add(button_reset_category)
#         keyboard.add(item1)
#         bot.send_message(message.chat.id, "Выберите категорию заново или вернитесь в главное меню.", reply_markup=keyboard)

#     except Exception as e:
#         bot.send_message(message.chat.id, f"Произошла ошибка при обработке вашего запроса: {e}")


#-------------------(КОНЕЦ) КОД ДЛЯ ПОИСКА МЕСТ, РАБОЧИЙ, НЕДОДЕЛАННЫЙ В ПЛАНЕ КАТЕГОРИЙ И ПРОВЕРКИ ВЫДАЧИ, НУЖЕН API------------------------

#-----------------------------------------------------------------------------------------------------------------------------------

def delete_repairs(user_id, deleted_repair):
    # Удаляем ремонт из базы данных
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

    # Путь к Excel файлу пользователя
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
    if summary_sheet.max_row == 0:  # Если лист пустой
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


# (13) --------------- КОД ДЛЯ "ПОИСКА ТРАНСПОРТА" ---------------

# (13.1) --------------- КОД ДЛЯ "ПОИСКА ТРАНСПОРТА" (СОХРАНЕНИЕ И ЗАГРУЗКА ГЕОЛОКАЦИИ) ---------------

LATITUDE_KEY = 'latitude'
LONGITUDE_KEY = 'longitude'

def save_location_data(location_data):
    folder_path = "data base/findtransport"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Сохраняем JSON с отступами для удобства чтения
    with open(os.path.join(folder_path, "location_data.json"), "w") as json_file:
        json.dump(location_data, json_file, indent=4)

def load_location_data():
    try:
        with open(os.path.join("data base/findtransport", "location_data.json"), "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

location_data = load_location_data()

# (13.2) --------------- КОД ДЛЯ "ПОИСКА ТРАНСПОРТА" (ОБРАБОТЧИК "НАЙТИ ТРАНСПОРТ") ---------------

# Обработчик для команды "Найти транспорт"
@bot.message_handler(func=lambda message: message.text == "Найти транспорт")
@restricted
@track_user_activity
def start_transport_search(message):

    if not function_states['Найти транспорт']:
        bot.send_message(message.chat.id, "Эта функция временно недоступна.")
        return  # Завершаем выполнение функции, если функция деактивирована

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
@restricted
@track_user_activity
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
            bot.send_message(message.chat.id, "Вы можете найти транспорт еще раз", reply_markup=markup)
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
    map_url = f"https://yandex.ru/maps/?rtext={end_location['latitude']},{end_location['longitude']}~{start_location['latitude']},{start_location['longitude']}&rtt=pd"
    short_url = shorten_url(map_url)
    bot.send_message(chat_id, f"📍 *Маршрут для поиска:* [ссылка]({short_url})", parse_mode='Markdown')
    
# (14) --------------- КОД ДЛЯ "ПОИСК РЕГИОНА ПО ГОСНОМЕРУ" ---------------

ALLOWED_LETTERS = "АВЕКМНОРСТУХABEKMHOPCTYX"  # Допустимые буквы для российских госномеров

def is_valid_car_number(car_number):
    """
    Проверяет, соответствует ли введенный госномер формату:
    1 буква, 3 цифры, 2 буквы, 2 или 3 цифры.
    """
    # Регулярное выражение для формата А123АА12 или А123АА123
    pattern = rf"^[{ALLOWED_LETTERS}]\d{{3}}[{ALLOWED_LETTERS}]{{2}}\d{{2,3}}$"
    return bool(re.match(pattern, car_number))

@bot.message_handler(func=lambda message: message.text == "Код региона")
@restricted
@track_user_activity
def handle_start4(message):
    if not function_states['Код региона']:
        bot.send_message(message.chat.id, "Эта функция временно недоступна.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    bot.send_message(
        message.chat.id,
        "Отправьте один или несколько государственных номеров (8 - 9 символов) или кодов региона (2 - 3 цифры), разделенных запятой:",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, process_input)

def process_input(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(message.chat.id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, process_input)
        return

    text = message.text.strip()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Ввести еще")
    item2 = types.KeyboardButton("В главное меню")
    markup.add(item1)
    markup.add(item2)

    inputs = [i.strip() for i in text.split(',')]
    responses = []

    for input_item in inputs:
        if input_item.isdigit() and (2 <= len(input_item) <= 3):
            region_code = input_item
            if region_code in regions:
                region_name = regions[region_code]
                response = f"🔍 *Регион для кода {region_code}:*\n{region_name}\n\n\n"
            else:
                response = f"❌ Не удалось определить регион для кода: *{region_code}*\n\n\n"
        
        elif 8 <= len(input_item) <= 9 and is_valid_car_number(input_item.upper()):
            car_number = input_item.upper()
            region_code = car_number[-3:] if len(car_number) == 9 else car_number[-2:]

            if region_code in regions:
                region_name = regions[region_code]
                avtocod_url = f"https://avtocod.ru/proverkaavto/{car_number}?rd=GRZ"
                short_url = shorten_url(avtocod_url)
                
                response = (
                    f"🔍 Регион для номера `{car_number}`: {region_name}\n\n"
                    f"🔗 [Ссылка на AvtoCod с поиском]({short_url})\n\n\n"
                )
            else:
                response = f"❌ Не удалось определить регион для номера: `{car_number}`\n\n\n"
        
        else:
            response = f"❌ Неверный формат для `{input_item}`. Пожалуйста, введите правильный госномер или код региона\n\n\n"

        responses.append(response)

    final_response = "".join(responses)
    bot.send_message(message.chat.id, final_response, reply_markup=markup, parse_mode="Markdown")
    bot.send_message(message.chat.id, "Вы можете ввести еще или выйти в главное меню")
    bot.register_next_step_handler(message, handle_action_after_response)

def handle_action_after_response(message):
    if message.text == "Ввести еще":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("В главное меню")
        markup.add(item1)
        bot.send_message(
            message.chat.id,
            "Отправьте один или несколько государственных номеров (8 - 9 символов) или кодов региона (2 - 3 цифры), разделённых запятой:",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, process_input)
    elif message.text == "В главное меню":
        return_to_menu(message)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите действие из меню:")
        bot.register_next_step_handler(message, handle_action_after_response)


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
@restricted
@track_user_activity
def handle_start_5(message):

    if not function_states['Погода']:
        bot.send_message(message.chat.id, "Эта функция временно недоступна.")
        return  # Завершаем выполнение функции, если функция деактивирована
    
    try:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(telebot.types.KeyboardButton("Отправить геопозицию", request_location=True))
        markup.row(telebot.types.KeyboardButton("В главное меню"))

        bot.send_message(message.chat.id, "Отправьте свою геопозицию для отображения погоды", reply_markup=markup)
        bot.register_next_step_handler(message, handle_location_5)
    
    except Exception as e:
        print(f"Ошибка в обработчике 'Погода': {e}")
        traceback.print_exc()
        bot.send_message(message.chat.id, "Произошла ошибка при обработке вашего запроса. Попробуйте позже")

@bot.message_handler(content_types=['location'])
@restricted
@track_user_activity
def handle_location_5(message):
    try:
        if message.location:
            latitude = message.location.latitude
            longitude = message.location.longitude

            # Сохраняем координаты пользователя
            save_user_location(message.chat.id, latitude, longitude, None)  # city_code пока None

            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
            markup.row('Сегодня', 'Завтра')
            markup.row('Неделя', 'Месяц')
            markup.row('Другое место')
            markup.row('В главное меню')

            bot.send_message(message.chat.id, "Выберите период или действие:", reply_markup=markup)
        elif message.text == "В главное меню":
            return_to_menu(message)
        else:
            bot.send_message(message.chat.id, "Не удалось получить данные о местоположении. Пожалуйста, отправьте местоположение еще раз")
            bot.register_next_step_handler(message, handle_location_5)
    except Exception as e:
        print(f"Ошибка в обработчике 'Геолокация': {e}")
        traceback.print_exc()
        bot.send_message(message.chat.id, "Произошла ошибка при обработке местоположения. Попробуйте позже")


import telebot
import threading
import schedule
import time
import json
import requests
import traceback
from datetime import datetime

# Путь к файлу notifications.json
notifications_file_path = 'data base/notifications/notifications.json'

def save_user_location(chat_id, latitude, longitude, city_code):
    # Загрузка существующих данных
    try:
        with open('data base/notifications/notifications.json', 'r') as f:
            notifications = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        notifications = {}

    # Проверка, существует ли запись для пользователя
    if str(chat_id) not in notifications:
        notifications[str(chat_id)] = {
            "latitude": None,
            "longitude": None,
            "city_code": None
        }

    # Обновление данных
    if latitude is not None:
        notifications[str(chat_id)]["latitude"] = latitude
    if longitude is not None:
        notifications[str(chat_id)]["longitude"] = longitude
    if city_code is not None:
        notifications[str(chat_id)]["city_code"] = city_code

    # Сохранение обратно в файл
    with open('data base/notifications/notifications.json', 'w') as f:
        json.dump(notifications, f, ensure_ascii=False, indent=4)

# Функции для загрузки координат и получения погоды
def load_user_locations():
    file_path = 'data base/notifications/notifications.json'
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки файла с координатами: {e}")
        return {}

import traceback

def get_city_name(latitude, longitude):
    try:
        geocode_url = "https://eu1.locationiq.com/v1/reverse.php"
        params = {
            'key': 'pk.fa5c52bb6b9e1b801d72b75d151aea63',  # Ваш API ключ LocationIQ
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'accept-language': 'ru'
        }
        response = requests.get(geocode_url, params=params)
        data = response.json()

        if response.status_code == 200:
            city = data.get("address", {}).get("city", None)
            return city if city else f"неизвестное место ({latitude}, {longitude})"
        else:
            print(f"Ошибка геокодирования: {data.get('error', 'Нет описания ошибки')}")
            return None
    except Exception as e:
        print(f"Произошла ошибка при запросе названия города: {e}")
        return None

def get_current_weather(coords):
    try:
        # Получаем название города
        city_name = get_city_name(coords['latitude'], coords['longitude'])

        params = {
            'lat': coords['latitude'],
            'lon': coords['longitude'],
            'appid': API_KEY,
            'units': 'metric',
            'lang': 'ru'
        }
        response = requests.get(WEATHER_URL, params=params, timeout=30)
        
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
            
            # Формируем сообщение
            return (
                f"*Вам пришло новое уведомление!*🔔\n\n\n"
                f"*Погода на {current_date} в {current_time}*:\n"
                f"*(г. {city_name}; {coords['latitude']}, {coords['longitude']})*\n\n"
                f"🌡️ *Температура:* {temperature}°C\n"
                f"🌬️ *Ощущается как:* {feels_like}°C\n"
                f"💧 *Влажность:* {humidity}%\n"
                f"〽️ *Давление:* {pressure} мм рт. ст.\n"
                f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                f"☁️ *Описание:* {description}\n\n"
            )
        else:
            print(f"Ошибка запроса погоды: код {response.status_code}, сообщение: {data.get('message', 'Нет описания ошибки')}")
            return None
    except requests.exceptions.Timeout:
        print("Ошибка: Время ожидания ответа от сервера истекло")
    except requests.exceptions.ConnectionError as e:
        print(f"Ошибка подключения: {e}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        traceback.print_exc()
    return None

def get_average_fuel_prices(city_code):
    fuel_prices = {}
    file_path = f'data base/azs/{city_code}_table_azs_data.json'

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            prices_data = json.load(f)

            for entry in prices_data:
                fuel_type = entry[1]  # Тип топлива
                price = entry[2]  # Цена топлива

                try:
                    price = float(price)  # Преобразуем цену в число (если это возможно)
                except ValueError:
                    print(f"Ошибка преобразования цены для {fuel_type}: {price}")
                    continue  # Пропускаем этот элемент, если цена не может быть преобразована

                if fuel_type not in fuel_prices:
                    fuel_prices[fuel_type] = []

                fuel_prices[fuel_type].append(price)

    except FileNotFoundError:
        print(f"Файл с ценами на топливо для города '{city_code}' не найден")
        return None
    except json.JSONDecodeError:
        print("Ошибка при декодировании JSON")
        return None

    # Вычисление средних цен
    average_prices = {fuel: sum(prices) / len(prices) for fuel, prices in fuel_prices.items()}

    return average_prices

def load_city_names(file_path):
    city_names = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                # Разделяем строку на название города и его код
                city_data = line.strip().split(' - ')
                if len(city_data) == 2:
                    city_name, city_code = city_data
                    city_names[city_code] = city_name  # Добавляем в словарь
    except FileNotFoundError:
        print(f"Файл с названиями городов '{file_path}' не найден")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    
    return city_names


def send_weather_notifications():
    user_locations = load_user_locations()
    city_names = load_city_names('files/combined_cities.txt')  # Загружаем названия городов
    
    for chat_id, coords in user_locations.items():
        weather_message = get_current_weather(coords)
        
        if weather_message:
            city_code = coords.get('city_code')
            city_name = city_names.get(city_code, city_code)  # Получаем название города
            average_prices = get_average_fuel_prices(city_code)

             # Получаем текущую дату и время
            current_time = datetime.now().strftime("%d.%m.%Y в %H:%M") 

            fuel_prices_message = ""
            if average_prices:
                fuel_prices_message = "\n*Актуальные цены на топливо (г. {}) на дату {}:*\n\n".format(city_name, current_time)
                for fuel_type, price in average_prices.items():
                    fuel_prices_message += f"⛽ *{fuel_type}:* {price:.2f} руб./л.\n"

            try:
                bot.send_message(chat_id, weather_message + fuel_prices_message, parse_mode="Markdown")
            except Exception as e:
                print(f"Ошибка отправки уведомления пользователю {chat_id}: {e}")
                traceback.print_exc()

# Настройка расписания для отправки уведомлений
schedule.every().day.at("07:30").do(send_weather_notifications)
schedule.every().day.at("13:00").do(send_weather_notifications)
schedule.every().day.at("17:00").do(send_weather_notifications)
schedule.every().day.at("20:00").do(send_weather_notifications)

@bot.message_handler(func=lambda message: message.text in ['Сегодня', 'Завтра', 'Неделя', 'Месяц', 'Другое место'])
@restricted
@track_user_activity
def handle_period_5(message):
    period = message.text.lower()
    chat_id = message.chat.id
    user_locations = load_user_locations()  # Загрузите пользовательские местоположения
    coords = user_locations.get(str(chat_id))  # Получите координаты для текущего пользователя

    if coords is None:
        bot.send_message(chat_id, "Не удалось получить координаты. Пожалуйста, отправьте местоположение еще раз")
        return

    if period == 'Другое место':
        user_data.pop(chat_id, None)
        handle_start_5(message)
        return

    if message.text == "Другое место":
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
                f"🌡️ *Температура:* {temperature}°C\n"
                f"🌬️ *Ощущается как:* {feels_like}°C\n"
                f"💧 *Влажность:* {humidity}%\n"
                f"〽️ *Давление:* {pressure} мм рт. ст.\n"
                f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                f"☁️ *Описание:* {description}\n"
            )
            bot.send_message(chat_id, message, parse_mode="Markdown")
            send_forecast_remaining_day(chat_id, coords, FORECAST_URL)
        else:
            bot.send_message(chat_id, "Не удалось получить текущую погоду. Проверьте, правильно ли указаны координаты")
    except Exception as e:
        print(f"Ошибка при отправке текущей погоды: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе текущей погоды. Попробуйте позже")

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
                        f"🌡️ *Температура:* {temperature}°C\n"
                        f"🌬 *Ощущается как:* {feels_like}°C\n"
                        f"💧 *Влажность:* {humidity}%\n"
                        f"〽️ *Давление:* {pressure} мм рт. ст.\n"
                        f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                        f"☁️ *Описание:* {description}\n\n"
                    )

            if message == "*Прогноз на оставшуюся часть дня:*\n\n":
                message = "Нет доступного прогноза на оставшуюся часть дня"

            bot.send_message(chat_id, message, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "Не удалось получить прогноз на оставшуюся часть дня")
    except Exception as e:
        print(f"Ошибка при отправке прогноза на оставшуюся часть дня: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на оставшуюся часть дня. Попробуйте позже")


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
                    f"🌡️ *Температура:* {temperature}°C\n"
                    f"🌬️ *Ощущается как:* {feels_like}°C\n"
                    f"💧 *Влажность:* {humidity}%\n"
                    f"〽️ *Давление:* {pressure} мм рт. ст\n"
                    f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                    f"☁️ *Описание:* {description}\n\n"
                )

            message_chunks = [message[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]

            for chunk in message_chunks:
                bot.send_message(chat_id, chunk, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "Не удалось получить прогноз погоды на завтра")
    except Exception as e:
        print(f"Ошибка при отправке прогноза на завтра: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на завтра. Попробуйте позже")

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
                f"🌡️ *Температура:* {temperature}°C\n"
                f"🌬️ *Ощущается как:* {feels_like}°C\n"
                f"💧 *Влажность:* {humidity}%\n"
                f"〽️ *Давление:* {pressure} мм рт. ст.\n"
                f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                f"☁️ *Описание:* {description}\n"
            )
            bot.send_message(chat_id, message, parse_mode="Markdown")

            send_hourly_forecast_tomorrow(chat_id, coords, url)
        else:
            bot.send_message(chat_id, "Не удалось получить прогноз на завтра")
    except Exception as e:
        print(f"Ошибка при отправке прогноза на завтра: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на завтра. Попробуйте позже")

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
            message = "*Почасовой прогноз на завтра:*\n\n\n"  # Добавлен жирный шрифт и пустая строка

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
                        f"🌡️ *Температура:* {temperature}°C\n"
                        f"🌬️ *Ощущается как:* {feels_like}°C\n"
                        f"💧 *Влажность:* {humidity}%\n"
                        f"〽️ *Давление:* {pressure} мм рт. ст.\n"
                        f"💨 *Скорость ветра:* {wind_speed} м/с\n"
                        f"☁️ *Описание:* {description}\n\n"  # Пустая строка
                    )

            if message == "*Почасовой прогноз на завтра:*\n\n":
                message = "Нет доступного почасового прогноза на завтра"

            message_chunks = [message[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]
            for chunk in message_chunks:
                bot.send_message(chat_id, chunk, parse_mode="Markdown")  # Убедитесь, что используется Markdown
        else:
            bot.send_message(chat_id, "Не удалось получить почасовой прогноз на завтра")
    except Exception as e:
        print(f"Ошибка при отправке почасового прогноза на завтра: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе почасового прогноза на завтра. Попробуйте позже")
        
# (15.9) --------------- КОД ДЛЯ "ПОГОДЫ" (ФУНКЦИЯ ПОГОДЫ НА НЕДЕЛЮ) ---------------


# ---------- ПРОГНОЗ НА НЕДЕЛЮ -----------

from datetime import datetime, timedelta
from collections import defaultdict

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
        message = "*Прогноз на неделю:*\n\n\n"

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
                            f"🌡️ *Температура:* {avg_temp}°C\n"
                            f"🌬️ *Ощущается как:* {avg_feels_like}°C\n"
                            f"💧 *Влажность:* {forecasts[0]['humidity']}%\n"
                            f"〽️ *Давление:* {forecasts[0]['pressure']} мм рт. ст.\n"
                            f"💨 *Скорость ветра:* {forecasts[0]['wind_speed']} м/с\n"
                            f"☁️ *Описание:* {forecasts[0]['description']}\n\n"
                        )

                    bot.send_message(chat_id, message, parse_mode="Markdown")
                    break
                else:
                    bot.send_message(chat_id, "Не удалось получить прогноз на неделю")
                    break
            except Exception as e:
                print(f"Ошибка в попытке запроса: {e}")
                if attempt == retries - 1:
                    bot.send_message(chat_id, "Не удалось получить прогноз на неделю после нескольких попыток")
    except Exception as e:
        print(f"Ошибка в send_forecast_weekly: {e}")
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на неделю. Попробуйте позже")

# ---------- ПРОГНОЗ НА МЕСЯЦ -----------
from collections import defaultdict
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
            message = "*Прогноз на месяц:*\n\n\n"

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
                    f"🌡️ *Температура:* {values['temperature']}°C\n"
                    f"🌬️ *Ощущается как:* {values['feels_like']}°C\n\n"
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
                             f"Данные недоступны из-за ограничений_\n\n")  # Курсив

            if message == "*Прогноз на месяц:*\n\n":
                message = "Нет доступного прогноза на месяц"

            bot.send_message(chat_id, message, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "Не удалось получить прогноз на месяц")
    except Exception as e:
        print(f"Ошибка при отправке прогноза на месяц: {e}")
        traceback.print_exc()
        bot.send_message(chat_id, "Произошла ошибка при запросе прогноза на месяц. Попробуйте позже")

# ЦЕНЫ НА ТОПЛИВО

import threading

# Переменные для состояния пользователя и данных
user_state = {}
user_data = {}

# Создаём необходимые папки
os.makedirs(os.path.join('data base', 'azs'), exist_ok=True)
os.makedirs(os.path.join('data base', 'cityforprice'), exist_ok=True)

# Путь к файлу для сохранения данных
DATA_FILE_PATH = os.path.join('data base', 'cityforprice', 'city_for_the_price.json')

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
@restricted
@track_user_activity
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
def process_city_selection(message):
    chat_id = message.chat.id
    str_chat_id = str(chat_id)

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if user_state.get(chat_id) != "choosing_city":
        bot.send_message(chat_id, "Пожалуйста, используйте доступные кнопки для навигации.")
        return

    city_name = message.text.strip().lower()
    city_code = get_city_code(city_name)

    if city_code:
        if str_chat_id not in user_data:
            user_data[str_chat_id] = {'recent_cities': [], 'city_code': None}

        update_recent_cities(str_chat_id, city_name)
        user_data[str_chat_id]['city_code'] = city_code  # Сохраняем код города

        # Получаем координаты пользователя
        notifications = load_user_locations()  # Функция для загрузки notifications.json
        user_info = notifications.get(str_chat_id)

        latitude = None
        longitude = None

        if user_info:
            latitude = user_info.get('latitude')
            longitude = user_info.get('longitude')

        # Сохраняем city_code и координаты в notifications.json, если координаты есть
        save_user_location(chat_id, latitude, longitude, city_code)

        # Сохранение данных города
        save_citys_users_data()

        # Показываем меню с ценами на топливо
        show_fuel_price_menu(chat_id, city_code)
    else:
        bot.send_message(chat_id, "Город не найден. Пожалуйста, попробуйте еще раз.")
        
        # Создаем клавиатуру
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)  # row_width=3 — города в строку

        # Добавляем кнопки с последними городами, если они есть
        recent_cities = user_data.get(str_chat_id, {}).get('recent_cities', [])
        if recent_cities:
            markup.add(*[types.KeyboardButton(city.title()) for city in recent_cities])  # Добавляем города в одну строку

        # Добавляем кнопку "В главное меню" в конце
        markup.add(types.KeyboardButton("В главное меню"))

        bot.send_message(chat_id, "Введите город или выберите из последних:", reply_markup=markup)

        # Повторный вызов обработчика для ввода города
        bot.register_next_step_handler(message, process_city_selection)

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

        prices_message = "\n\n".join([f"⛽ {i + 1}. {brand} - {avg_price:.2f} руб./л." for i, (brand, avg_price) in enumerate(sorted_prices)])
        bot.send_message(chat_id, f"*Актуальные цены на {actual_fuel_type.upper()}:*\n\n\n{prices_message}", parse_mode='Markdown')

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
        bot.send_message(chat_id, f"Ошибка получения цен!\n\nНе найдена таблица с ценами.\nПопробуйте выбрать другой город или тип топлива")
        show_fuel_price_menu(chat_id, city_code)

# Обработчик следующих действий (посмотреть другое топливо или выбрать другой город)
def process_next_action(message):
    chat_id = message.chat.id
    text = message.text.strip().lower()

    if text == "выбрать другой город":
        user_state[chat_id] = "choosing_city"  # Устанавливаем состояние выбора города

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        # Загружаем последние города для пользователя
        recent_cities = user_data.get(str(chat_id), {}).get('recent_cities', [])

        # Если есть последние города, создаем кнопки
        city_buttons = [types.KeyboardButton(city.capitalize()) for city in recent_cities]
        if city_buttons:
            markup.row(*city_buttons)

        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(chat_id, "Введите название города или выберите из последних:", reply_markup=markup)
        
        # Передаем управление process_city_selection для выбора города
        bot.register_next_step_handler(message, process_city_selection)
    elif text == "в главное меню":
        return_to_menu(message)
    else:
        bot.send_message(chat_id, "Пожалуйста, выберите одно из предложенных действий.")
        bot.register_next_step_handler(message, process_next_action)

# Функция для обработки данных по всем видам топлива и их сохранения
# Обработка данных по всем видам топлива и их сохранение
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
                try:
                    fuel_prices = get_fuel_prices_from_site(fuel_type, city_code)
                except ValueError:
                    # Если таблица не найдена, возвращаем последние сохраненные данные
                    if saved_data:
                        return [
                            item for item in saved_data
                            if item[1].lower() == selected_fuel_type.lower() or
                            (selected_fuel_type.lower() == "газ" and item[1].lower() == "газ спбт")
                        ]
                    # Если данных нет, вызываем ту же ошибку
                    raise ValueError("Ошибка получения цен!\n\nНе найдена таблица с ценами.\nПопробуйте выбрать другой город или тип топлива")

                fuel_prices = remove_duplicate_prices(fuel_prices)
                all_fuel_prices.extend(fuel_prices)

            # Сохраняем новые данные
            save_data(city_code, all_fuel_prices)
            saved_data = all_fuel_prices  # Обновляем saved_data

    # Если данных нет, пытаемся их получить
    if not saved_data:
        all_fuel_prices = []
        for fuel_type in fuel_types:
            try:
                fuel_prices = get_fuel_prices_from_site(fuel_type, city_code)
            except ValueError:
                # Если таблица не найдена и файла тоже нет, вызываем ту же ошибку
                raise ValueError("Ошибка получения цен!\n\nНе найдена таблица с ценами.\nПопробуйте выбрать другой город или тип топлива")

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
        raise ValueError("Не найдена таблица с ценами")

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


# !!!!!!!!!!!!!!!!!!!ЭТО ОБЩИЙ ПЛАНИРОВЩИК ЗАДАЧ!!!!!!!!!!!!!!!!!!!!!
# Общий планировщик задач с объединенной логикой для уведомлений и парсинга
def schedule_tasks():
    while True:
        now = datetime.now()
        
        # Запуск функции парсинга цен на топливо в 00:00
        if now.hour == 0 and now.minute == 0:
            parse_fuel_prices()
            time.sleep(60 * 5)  # Ожидание 5 минут перед следующим городом

        # Проверка запланированных уведомлений (запускает все задачи, добавленные в schedule)
        schedule.run_pending()
        
        # Ожидание перед следующей проверкой расписания
        time.sleep(1)

# Запуск объединенного потока
threading.Thread(target=schedule_tasks, daemon=True).start()



# Ваш транспорт


# Определение состояний
class States:
    ADDING_TRANSPORT = 1
    CONFIRMING_DELETE = 2

# Хранение данных о транспорте в памяти
user_transport = {}

# Функции для работы с файлами
def save_transport_data(user_id, user_data):
    folder_path = "data base/transport"  # Изменено на подкаталог transport
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # Сохраняем данные о транспорте
    with open(os.path.join(folder_path, f"{user_id}_transport.json"), "w", encoding="utf-8") as file:
        json.dump(user_data, file, ensure_ascii=False, indent=4)

def load_transport_data(user_id):
    folder_path = "data base/transport"  # Изменено на подкаталог transport
    try:
        with open(os.path.join(folder_path, f"{user_id}_transport.json"), "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = []
    return data

# Загрузка данных о транспорте при старте бота
def load_all_transport():
    folder_path = "data base/transport"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    users = os.listdir(folder_path)
    for user_file in users:
        if user_file.endswith("_transport.json"):
            user_id = user_file.split("_")[0]
            user_transport[user_id] = load_transport_data(user_id)

# Пример вызова для загрузки данных
load_all_transport()

# Команда для управления транспортом
@bot.message_handler(func=lambda message: message.text == "Ваш транспорт")
@restricted
@track_user_activity
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
@restricted
@track_user_activity
def add_transport(message):
    user_id = str(message.chat.id)
    if check_media(message, user_id): return
    bot.send_message(user_id, "Введите марку транспорта:", reply_markup=create_transport_keyboard())
    bot.register_next_step_handler(message, process_brand)

def format_brand_model(text):
    """Приводит марку и модель к формату 'Первое слово с большой буквы, остальное с маленькой'."""
    return " ".join(word.capitalize() for word in text.split())

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

    # Форматируем бренд
    brand = format_brand_model(message.text)
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

    # Форматируем модель
    model = format_brand_model(message.text)
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
        bot.send_message(user_id, "Ошибка! Пожалуйста, введите корректный год (диапазон от 1960 г. до 3000 г.). Попробуйте снова", reply_markup=create_transport_keyboard())
        bot.register_next_step_handler(message, process_year, brand, model)
        return

    bot.send_message(user_id, "Введите госномер:", reply_markup=create_transport_keyboard())
    bot.register_next_step_handler(message, process_license_plate, brand, model, year)

def process_license_plate(message, brand, model, year):
    user_id = str(message.chat.id)
    if check_media(message, user_id, process_license_plate, brand, model, year): 
        return

    # Обработка кнопок
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    # Приведение госномера к верхнему регистру
    license_plate = message.text.upper()

    # Проверка длины и формата госномера
    import re
    pattern = r'^[АВЕКМНОРСТУХABEKMHOPCTYX]\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\d{2,3}$'
    if not re.match(pattern, license_plate):
        bot.send_message(user_id, "Ошибка! Госномер должен соответствовать формату госномеров РФ. Попробуйте снова", reply_markup=create_transport_keyboard())
        bot.register_next_step_handler(message, process_license_plate, brand, model, year)
        return

    # Проверка уникальности госномера
    if any(t["license_plate"] == license_plate for t in user_transport.get(user_id, [])):
        bot.send_message(user_id, "Ошибка! Такой госномер уже существует. Попробуйте снова", reply_markup=create_transport_keyboard())
        bot.register_next_step_handler(message, process_license_plate, brand, model, year)
        return

    # Сохраняем транспорт в память
    if user_id not in user_transport:
        user_transport[user_id] = []
    
    user_transport[user_id].append({"brand": brand, "model": model, "year": year, "license_plate": license_plate})
    save_transport_data(user_id, user_transport[user_id])  # Сохранение данных о транспорте

    bot.send_message(user_id, f"🚗 *Транспорт добавлен 🚗*\n\n*{brand} - {model} - {year} - {license_plate}*", parse_mode="Markdown", reply_markup=create_transport_keyboard())

    # Переход в меню "Ваш транспорт"
    manage_transport(message)

def delete_expenses_related_to_transport(user_id, transport, selected_transport=""):
    expenses_data = load_expense_data(user_id)
    if user_id in expenses_data:
        updated_expenses = []
        for expense in expenses_data[user_id]['expenses']:
            if expense['transport']['brand'] != transport['brand'] or \
               expense['transport']['model'] != transport['model'] or \
               expense['transport']['year'] != transport['year']:
                updated_expenses.append(expense)

        expenses_data[user_id]['expenses'] = updated_expenses
        save_expense_data(user_id, expenses_data, selected_transport)

def delete_repairs_related_to_transport(user_id, transport):
    repair_data = load_repair_data(user_id)
    if user_id in repair_data:
        updated_repairs = []
        for repair in repair_data[user_id].get("repairs", []):
            if repair['transport']['brand'] != transport['brand'] or \
               repair['transport']['model'] != transport['model'] or \
               repair['transport']['year'] != transport['year']:
                updated_repairs.append(repair)

        repair_data[user_id]["repairs"] = updated_repairs
        save_repair_data(user_id, repair_data, selected_transport="")


# @bot.message_handler(func=lambda message: message.text == "Изменить транспорт")
# @restricted
# @track_user_activity
# def edit_transport(message):
#     user_id = str(message.chat.id)
#     if user_id not in user_transport or not user_transport[user_id]:
#         bot.send_message(user_id, "У вас нет добавленного транспорта.", reply_markup=create_transport_keyboard())
#         return

#     # Отправляем список транспорта для выбора
#     transport_list = user_transport[user_id]
#     response = "\n".join([f"№{index + 1}. {item['brand']} - {item['model']} - {item['year']} - {item['license_plate']}" for index, item in enumerate(transport_list)])
#     bot.send_message(user_id, f"Выберите номер транспорта для изменения:\n\n{response}", reply_markup=create_transport_keyboard())
#     bot.register_next_step_handler(message, select_transport_for_editing)

# def select_transport_for_editing(message):
#     user_id = str(message.chat.id)
#     try:
#         index = int(message.text) - 1
#         if index < 0 or index >= len(user_transport[user_id]):
#             raise ValueError
#         selected_transport = user_transport[user_id][index]
#         bot.send_message(user_id, f"Вы выбрали:\n{selected_transport['brand']} - {selected_transport['model']} - {selected_transport['year']} - {selected_transport['license_plate']}\n\nЧто вы хотите изменить? (Марка/Модель/Год/Госномер)", reply_markup=create_transport_keyboard())
#         bot.register_next_step_handler(message, edit_transport_field, index)
#     except ValueError:
#         bot.send_message(user_id, "Ошибка! Введите корректный номер транспорта.", reply_markup=create_transport_keyboard())
#         bot.register_next_step_handler(message, select_transport_for_editing)

# def edit_transport_field(message, index):
#     user_id = str(message.chat.id)
#     field = message.text.lower()
#     valid_fields = {"марка": "brand", "модель": "model", "год": "year", "госномер": "license_plate"}
#     if field not in valid_fields:
#         bot.send_message(user_id, "Ошибка! Выберите одно из: Марка, Модель, Год, Госномер.", reply_markup=create_transport_keyboard())
#         bot.register_next_step_handler(message, edit_transport_field, index)
#         return

#     bot.send_message(user_id, f"Введите новое значение для поля '{field.capitalize()}':", reply_markup=create_transport_keyboard())
#     bot.register_next_step_handler(message, update_transport_field, index, valid_fields[field])

# def update_transport_field(message, index, field):
#     user_id = str(message.chat.id)
#     new_value = message.text.strip()

#     # Проверка нового значения
#     if field == "license_plate":
#         # Приведение госномера к верхнему регистру
#         new_value = new_value.upper()

#         # Проверка формата госномера
#         import re
#         pattern = r'^[АВЕКМНОРСТУХABEKMHOPCTYX]\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\d{2,3}$'
#         if not re.match(pattern, new_value):
#             bot.send_message(user_id, "Ошибка! Госномер должен соответствовать формату.", reply_markup=create_transport_keyboard())
#             bot.register_next_step_handler(message, update_transport_field, index, field)
#             return

#         # Проверка уникальности госномера
#         if any(t["license_plate"] == new_value for t in user_transport[user_id] if t != user_transport[user_id][index]):
#             bot.send_message(user_id, "Ошибка! Такой госномер уже существует.", reply_markup=create_transport_keyboard())
#             bot.register_next_step_handler(message, update_transport_field, index, field)
#             return

#     elif field == "year":
#         # Проверка корректности года
#         try:
#             new_value = int(new_value)
#             if new_value < 1960 or new_value > 3000:
#                 raise ValueError
#         except ValueError:
#             bot.send_message(user_id, "Ошибка! Введите корректный год (диапазон от 1960 до 3000).", reply_markup=create_transport_keyboard())
#             bot.register_next_step_handler(message, update_transport_field, index, field)
#             return

#     # Обновление данных
#     user_transport[user_id][index][field] = new_value
#     save_transport_data(user_id, user_transport[user_id])

#     bot.send_message(user_id, "Данные транспорта успешно обновлены.", reply_markup=create_transport_keyboard())

#     # Обновление данных о тратах и ремонтах
#     update_expense_repair_data(user_id, user_transport[user_id][index])

# def update_expense_repair_data(user_id, updated_transport):
#     # Обновляем данные в расходах
#     expense_data = load_expense_data(user_id)
#     for expense in expense_data.get("expenses", []):
#         if expense.get("transport", {}).get("license_plate") == updated_transport["license_plate"]:
#             expense["transport"] = updated_transport
#     save_expense_data(user_id, expense_data)

#     # Обновляем данные в ремонтах
#     repair_data = load_repair_data(user_id)
#     for repair in repair_data.get("repairs", []):
#         if repair.get("transport", {}).get("license_plate") == updated_transport["license_plate"]:
#             repair["transport"] = updated_transport
#     save_repair_data(user_id, repair_data)

@bot.message_handler(func=lambda message: message.text == "Удалить транспорт")
@restricted
@track_user_activity
def delete_transport(message):
    user_id = str(message.chat.id)
    if user_id in user_transport and user_transport[user_id]:
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        transport_list = user_transport[user_id]
        
        # Формируем список транспорта для удаления
        for index, item in enumerate(transport_list, start=1):
            keyboard.add(f"№{index}. {item['brand']} - {item['model']} - {item['year']} - {item['license_plate']}")
        
        # Кнопки "В главное меню" и "Вернуться в ваш транспорт"
        item_main_menu = types.KeyboardButton("В главное меню")
        item_return_transport = types.KeyboardButton("Вернуться в ваш транспорт")
        keyboard.add("Удалить весь транспорт")
        keyboard.add(item_return_transport)
        keyboard.add(item_main_menu)
        
        bot.send_message(user_id, "Выберите транспорт для удаления или вернитесь:", reply_markup=keyboard)
        bot.register_next_step_handler(message, process_transport_selection)
    else:
        bot.send_message(user_id, "У вас нет добавленного транспорта")

def process_transport_selection(message):
    user_id = str(message.chat.id)
    selected_transport = message.text.strip()

    # Проверяем, выбрал ли пользователь транспорт из списка или другую опцию
    if selected_transport == "В главное меню":
        return_to_menu(message)
        return

    if selected_transport == "Удалить весь транспорт":
        delete_all_transports(message)  # Переход к удалению всех транспортов
        return

    if message.text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    transport_list = user_transport.get(user_id, [])
    if transport_list:
        # Проверяем, начинается ли текст с номера транспорта
        try:
            index = int(selected_transport.split('.')[0].replace("№", "").strip()) - 1
            if 0 <= index < len(transport_list):
                transport_to_delete = transport_list[index]
                bot.send_message(
    user_id,
    f"*Вы точно хотите удалить данный транспорт?\n\n{transport_to_delete['brand']} - {transport_to_delete['model']} - {transport_to_delete['year']} - {transport_to_delete['license_plate']}*\n\n"
    "Удаление транспорта приведет к удалению всех трат и ремонтов!\n\n"
    "Пожалуйста, введите *ДА* для подтверждения или *НЕТ* для отмены",
    parse_mode="Markdown",
    reply_markup=get_return_menu_keyboard()
)
                bot.register_next_step_handler(message, lambda msg: process_confirmation(msg, transport_to_delete))
            else:
                raise ValueError("Индекс вне диапазона")
        except ValueError:
            bot.send_message(user_id, "Ошибка! Пожалуйста, выберите транспорт для удаления из списка")
            delete_transport(message)
    else:
        bot.send_message(user_id, "У вас нет добавленного транспорта")

def process_confirmation(message, transport_to_delete):
    user_id = str(message.chat.id)
    confirmation = message.text.strip().upper()

    # Проверка на "В главное меню" или "Вернуться в ваш транспорт"
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    elif message.text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    # Проверка подтверждения на "ДА" или "НЕТ"
    if confirmation == "ДА":
        if user_id in user_transport and transport_to_delete in user_transport[user_id]:
            user_transport[user_id].remove(transport_to_delete)
            delete_expenses_related_to_transport(user_id, transport_to_delete)
            delete_repairs_related_to_transport(user_id, transport_to_delete)
            save_transport_data(user_id, user_transport[user_id])
            update_excel_file(user_id)
            update_repairs_excel_file(user_id)
            bot.send_message(user_id, "Транспорт и связанные с ним траты и ремонты успешно удалены")
            manage_transport(message)  # Возвращаем в меню транспорта
        else:
            bot.send_message(user_id, "Ошибка удаления: транспорт не найден")
    elif confirmation == "НЕТ":
        bot.send_message(user_id, "Удаление отменено")
        manage_transport(message)  # Возвращаем в меню транспорта
    else:
        bot.send_message(user_id, "Ошибка! Пожалуйста, введите *ДА* для подтверждения или *НЕТ* для отмены", parse_mode="Markdown")
        bot.register_next_step_handler(message, lambda msg: process_confirmation(msg, transport_to_delete))

# Функция для создания клавиатуры с кнопками возврата
def get_return_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    item_main_menu = types.KeyboardButton("В главное меню")
    item_return_transport = types.KeyboardButton("Вернуться в ваш транспорт")
    markup.add(item_return_transport)
    markup.add(item_main_menu)
    return markup

@bot.message_handler(func=lambda message: message.text == "Удалить весь транспорт")
@restricted
@track_user_activity
def delete_all_transports(message):
    user_id = str(message.chat.id)
    if user_id in user_transport and user_transport[user_id]:
        # Подтверждение удаления всех транспортов
        bot.send_message(
    user_id,
    "*Вы уверены, что хотите удалить весь транспорт?*\n\n"
    "Удаление транспорта приведет к удалению всех трат и ремонтов!\n\n"
    "Введите *ДА* для подтверждения или *НЕТ* для отмены",
    parse_mode="Markdown",
    reply_markup=get_return_menu_keyboard()
)
        bot.register_next_step_handler(message, process_delete_all_confirmation)
    else:
        bot.send_message(user_id, "У вас нет добавленного транспорта")

def process_delete_all_confirmation(message):
    user_id = str(message.chat.id)
    confirmation = message.text.strip().upper()

    # Проверка на "В главное меню" или "Вернуться в ваш транспорт"
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    elif message.text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    # Проверка подтверждения на "ДА" или "НЕТ"
    if confirmation == "ДА":
        if user_id in user_transport:
            # Удаляем все транспорты
            transports = user_transport[user_id]
            user_transport[user_id] = []  # Очищаем список
            save_transport_data(user_id, user_transport[user_id])

            for transport in transports:
                delete_expenses_related_to_transport(user_id, transport)
                delete_repairs_related_to_transport(user_id, transport)

            bot.send_message(user_id, "Весь транспорт и связанные с ним траты и ремонты успешно удалены")
            manage_transport(message)  # Возвращаем в меню транспорта
        else:
            bot.send_message(user_id, "У вас нет добавленного транспорта")
    elif confirmation == "НЕТ":
        bot.send_message(user_id, "Удаление отменено")
        manage_transport(message)  # Возвращаем в меню транспорта
    else:
        bot.send_message(user_id, "Ошибка! Пожалуйста, введите *ДА* для подтверждения или *НЕТ* для отмены", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_delete_all_confirmation)

@bot.message_handler(func=lambda message: message.text == "Посмотреть транспорт")
@restricted
@track_user_activity
def view_transport(message):
    user_id = str(message.chat.id)
    if user_id in user_transport and user_transport[user_id]:
        transport_list = user_transport[user_id]
        response = "\n\n".join([f"№{index + 1}. {item['brand']} - {item['model']} - {item['year']} - `{item['license_plate']}`" for index, item in enumerate(transport_list)])
        bot.send_message(user_id, f"🚙 *Ваш транспорт* 🚙\n\n{response}", parse_mode="Markdown", reply_markup=create_transport_keyboard())
    else:
        bot.send_message(user_id, "У вас нет добавленного транспорта")

@bot.message_handler(func=lambda message: message.text == "Вернуться в ваш транспорт")
@restricted
@track_user_activity
def return_to_transport_menu(message):
    manage_transport(message)  # Возвращаем пользователя в меню транспорта


# АНТИ-РАДАР 


# 📂 Загрузка данных о камерах из файла
camera_data = []
coordinates = []
try:
    with open('files/milestones.csv', mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=';')
        for row in reader:
            latitude = float(row['gps_y'])
            longitude = float(row['gps_x'])
            camera_data.append({
                'id': row['camera_id'],
                'latitude': latitude,
                'longitude': longitude,
                'description': row['camera_place'],
            })
            coordinates.append((latitude, longitude))
except Exception as e:
    print(f"Ошибка при загрузке данных о камерах: {e}")

# 🌳 Создание KD-дерева для поиска ближайших камер
camera_tree = cKDTree(coordinates)
user_tracking = {}

# Обработчик команды для старта анти-радара
@bot.message_handler(func=lambda message: message.text == "Анти-радар")
@restricted
@track_user_activity
def start_antiradar(message):
    user_id = message.chat.id
    user_tracking[user_id] = {'tracking': True, 'notification_ids': [], 'last_notified_camera': {}, 'location': None, 'started': False}

    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button_geo = telebot.types.KeyboardButton(text="Отправить геопозицию", request_location=True)
    button_off_geo = telebot.types.KeyboardButton(text="Выключить анти-радар")
    keyboard.add(button_geo)
    keyboard.add(button_off_geo)
    bot.send_message(user_id, "Пожалуйста, разрешите доступ к геопозиции для запуска анти-радара. Нажмите кнопку, чтобы отправить геопозицию", reply_markup=keyboard)

    # Отправка сообщения с камерами
    message_text = "⚠️ Внимание! Камеры впереди:\n\n"  # Заголовок сообщения
    sent_message = bot.send_message(user_id, message_text, parse_mode="Markdown")
    
    # Закрепляем сообщение
    bot.pin_chat_message(user_id, sent_message.message_id)  # Закрепляем сообщение
    user_tracking[user_id]['last_camera_message'] = sent_message.message_id  # Сохраняем ID сообщения для дальнейшего использования

# Обработчик для получения геопозиции при активированном анти-радаре
@bot.message_handler(content_types=['location'])
@restricted
@track_user_activity
def handle_antiradar_location(message):
    user_id = message.chat.id
    
    # Проверка на наличие геолокации
    if message.location:
        latitude = message.location.latitude
        longitude = message.location.longitude
    else:
        bot.send_message(user_id, "Геолокация недоступна. Попробуйте снова")
        return

    # Проверка: если анти-радар включен
    if user_tracking.get(user_id, {}).get('tracking', False):
        # Обновляем только координаты пользователя
        user_tracking[user_id]['location'] = message.location
        
        # Запускаем трекинг, если он еще не был запущен
        if not user_tracking[user_id].get('started', False):
            user_tracking[user_id]['started'] = True
            track_user_location(user_id, message.location)
    else:
        bot.send_message(user_id, "Пожалуйста, выберите категорию из меню")

# Обработчик для выключения анти-радара
@bot.message_handler(func=lambda message: message.text == "Выключить анти-радар")
@restricted
@track_user_activity
def stop_antiradar(message):
    user_id = message.chat.id
    if user_id in user_tracking:
        user_tracking[user_id]['tracking'] = False
        bot.send_message(user_id, "Анти-радар остановлен")

        # Удаление закрепленного сообщения с камерами
        if user_tracking[user_id].get('last_camera_message'):
            bot.unpin_chat_message(user_id, user_tracking[user_id]['last_camera_message'])  # Убираем закрепление
            bot.delete_message(user_id, user_tracking[user_id]['last_camera_message'])  # Удаляем сообщение

        # Возврат в главное меню
        return_to_main_menu(message)

    else:
        bot.send_message(user_id, "Анти-радар не был запущен")

def delete_messages(user_id, message_id):
    time.sleep(6)
    try:
        bot.delete_message(chat_id=user_id, message_id=message_id)
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")

MAX_CAMERAS_IN_MESSAGE = 5  # Максимальное количество камер в одном сообщении
ALERT_DISTANCE = 150  # Расстояние для уведомления о приближении к камере
EXIT_DISTANCE = 50  # Расстояние для уведомления о выходе из зоны камеры
IN_ZONE_DISTANCE = 15  # Расстояние, при котором показывается сообщение "в зоне камеры"

def track_user_location(user_id, initial_location):
    def monitor():
        while user_tracking.get(user_id, {}).get('tracking', False):
            user_location = user_tracking[user_id]['location']
            user_position = (user_location.latitude, user_location.longitude)
            
            # Обновляем last_position каждый раз, чтобы отслеживать изменения
            last_position = user_position

            distances, indices = camera_tree.query(user_position, k=len(camera_data))
            nearest_cameras = []
            unique_addresses = set()

            for i, distance in enumerate(distances[:MAX_CAMERAS_IN_MESSAGE]):
                if distance <= 1000:  # Ограничиваем радиус поиска
                    camera = camera_data[indices[i]]
                    actual_distance = int(geodesic(user_position, (camera['latitude'], camera['longitude'])).meters)
                    camera_address = camera['description']

                    # Проверяем, нужно ли отправить уведомление
                    if camera_address not in user_tracking[user_id]['last_notified_camera']:
                        nearest_cameras.append((actual_distance, camera))
                        unique_addresses.add(camera_address)
                        user_tracking[user_id]['last_notified_camera'][camera_address] = {
                            'entered': False,
                            'exited': False,
                            'in_zone': False
                        }

                    if actual_distance <= ALERT_DISTANCE and not user_tracking[user_id]['last_notified_camera'][camera_address]['entered']:
                        notification_message = (
                            f"⚠️ Вы приближаетесь к камере!\n\n"
                            f"📷 Расстояние - *{actual_distance} м.*\n"
                            f"🗺️ *{camera_address}*"
                        )
                        try:
                            sent_message = bot.send_message(user_id, notification_message, parse_mode="Markdown")
                            user_tracking[user_id]['notification_ids'].append(sent_message.message_id)
                            user_tracking[user_id]['last_notified_camera'][camera_address]['entered'] = True
                        except Exception as e:
                            print(f"Ошибка при отправке уведомления о приближении: {e}")

                    if actual_distance <= IN_ZONE_DISTANCE and not user_tracking[user_id]['last_notified_camera'][camera_address]['in_zone']:
                        in_zone_message = (
                            f"📍 Вы находитесь в зоне действия камеры!\n\n"
                            f"🗺️ *{camera_address}*"
                        )
                        try:
                            in_zone_sent = bot.send_message(user_id, in_zone_message, parse_mode="Markdown")
                            user_tracking[user_id]['notification_ids'].append(in_zone_sent.message_id)
                            user_tracking[user_id]['last_notified_camera'][camera_address]['in_zone'] = True
                        except Exception as e:
                            print(f"Ошибка при отправке уведомления о зоне действия: {e}")

                    if actual_distance > EXIT_DISTANCE and user_tracking[user_id]['last_notified_camera'][camera_address]['entered']:
                        exit_message = (
                            f"🔔 Вы вышли из зоны действия камеры!\n\n"
                            f"🗺️ *{camera_address}*"
                        )
                        try:
                            exit_sent_message = bot.send_message(user_id, exit_message, parse_mode="Markdown")
                            user_tracking[user_id]['notification_ids'].append(exit_sent_message.message_id)
                            user_tracking[user_id]['last_notified_camera'][camera_address]['exited'] = True
                        except Exception as e:
                            print(f"Ошибка при отправке уведомления о выходе из зоны: {e}")

            # Формируем текст сообщения о ближайших камерах
            message_text = "⚠️ Внимание! Камеры впереди:\n\n"
            for distance, camera in nearest_cameras:
                message_text += f"📷 Камера через *{distance} м.*\n🗺️ Адрес: *{camera['description']}*\n\n"

            # Обновляем сообщение с камерами
            if nearest_cameras:
                try:
                    if user_tracking[user_id].get('last_camera_message'):
                        bot.edit_message_text(chat_id=user_id, message_id=user_tracking[user_id]['last_camera_message'], text=message_text, parse_mode="Markdown")
                    else:
                        sent_message = bot.send_message(user_id, message_text, parse_mode="Markdown")
                        user_tracking[user_id]['last_camera_message'] = sent_message.message_id
                except Exception as e:
                    print(f"Ошибка при обновлении сообщения: {e}")

            time.sleep(3)

    # Запуск потока для мониторинга
    threading.Thread(target=monitor, daemon=True).start()


# ----------------------------------КОД ДЛЯ НАПОМИНАНИЙ---------------------------------------

# Путь к файлу базы данных
DB_PATH = 'data base/reminders/reminders.json'

# Функция для загрузки данных
def load_data():
    # Проверка существования папки и файла базы данных
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        with open(DB_PATH, 'w', encoding='utf-8') as file:  # Указываем кодировку при записи нового файла
            # Если файл не существует, создаем пустую структуру данных
            json.dump({"users": {}}, file, indent=4, ensure_ascii=False)

    # Загружаем данные из файла с указанием кодировки utf-8
    with open(DB_PATH, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Убедимся, что ключ 'users' существует в данных
    if 'users' not in data:
        data['users'] = {}

    return data

# Функция для сохранения данных
def save_data(data):
    # Проверка на наличие ключа 'users'
    if 'users' not in data:
        data['users'] = {}

    with open(DB_PATH, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

# Функция для возврата в меню напоминаний
@bot.message_handler(func=lambda message: message.text == "Вернуться в меню напоминаний")
def return_to_reminders_menu(message):
    reminders_menu(message)

# Функция для возврата в главное меню
@bot.message_handler(func=lambda message: message.text == "В главное меню")
def return_to_main_menu(message):
    start(message)

# Функция для отправки напоминаний
def send_reminders():
    data = load_data()
    current_time = datetime.now()

    for user_id, user_data in data["users"].items():
        reminders = user_data.get("reminders", [])
        for reminder in reminders:
            reminder_datetime = datetime.strptime(reminder["date"] + " " + reminder["time"], "%d.%m.%Y %H:%M")
            
            # Если время напоминания наступило и оно активно
            if reminder["status"] == "active" and reminder_datetime <= current_time:
                bot.send_message(user_id, f"⏰ *У вас напоминание!* ⏰\n\n\n📝 Название: {reminder['title']} \n\n📅 Дата: {reminder['date']} \n\n🕒 Время: {reminder['time']}", parse_mode='Markdown')
                reminder["status"] = "expired"  # Меняем статус на "истекший"

        save_data(data)

# Функция для фонового планировщика
def run_scheduler():
    while True:
        send_reminders()  # Проверяем напоминания каждую минуту
        time.sleep(15)  # Задержка на 15 секунд для следующей проверки

# Запуск фона в отдельном потоке
threading.Thread(target=run_scheduler, daemon=True).start()

# Обработка кнопки "Напоминания"
@bot.message_handler(func=lambda message: message.text == "Напоминания")
def reminders_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Добавить', 'Посмотреть', 'Удалить')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

# Обработка кнопки "Добавить напоминание"
@bot.message_handler(func=lambda message: message.text == "Добавить")
def add_reminder(message):
    # Кнопки на этапе ввода названия
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, "Введите название напоминания:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_title_step)

def process_title_step(message):
    user_id = str(message.from_user.id)
    data = load_data()

    # Проверка на мультимедийные файлы
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(message.chat.id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, process_title_step)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text == "Вернуться в меню напоминаний":
        reminders_menu(message)
        return	

    if user_id not in data["users"]:
        data["users"][user_id] = {"reminders": []}

    reminder = {"title": message.text}
    data["users"][user_id]["current_reminder"] = reminder
    save_data(data)

    # Кнопки на этапе ввода даты
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, "Введите дату напоминания в формате ДД.ММ.ГГГГ:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_date_step_2)

def process_date_step_2(message):
    user_id = str(message.from_user.id)
    data = load_data()
    reminder = data["users"][user_id]["current_reminder"]

    # Проверка на мультимедийные файлы
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(message.chat.id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, process_date_step_2)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return
        
    if message.text == "Вернуться в меню напоминаний":
        reminders_menu(message)
        return	

    date_input = message.text

    # Проверка на формат и диапазоны даты
    if re.match(r"^\d{2}\.\d{2}\.\d{4}$", date_input):
        try:
            day, month, year = map(int, date_input.split('.'))
            # Проверка на корректность значений дня, месяца и года
            if 1 <= month <= 12 and 1 <= day <= 31 and 2000 <= year <= 3000:
                datetime.strptime(date_input, "%d.%m.%Y")
                reminder["date"] = date_input
            else:
                raise ValueError
        except ValueError:
            msg = bot.send_message(message.chat.id, "Неверный формат даты или значения. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")
            bot.register_next_step_handler(msg, process_date_step_2)
            return
    else:
        msg = bot.send_message(message.chat.id, "Неверный формат даты. Попробуйте еще раз в формате ДД.ММ.ГГГГ.")
        bot.register_next_step_handler(msg, process_date_step_2)
        return

    save_data(data)
    # Кнопки на этапе ввода времени
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')
    msg = bot.send_message(message.chat.id, "Введите время напоминания в формате ЧЧ:ММ:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_time_step)

def process_time_step(message):
    user_id = str(message.from_user.id)
    data = load_data()
    reminder = data["users"][user_id]["current_reminder"]

    # Проверка на мультимедийные файлы
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(message.chat.id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, process_time_step)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return
        
    if message.text == "Вернуться в меню напоминаний":
        reminders_menu(message)
        return	

    time_input = message.text

    # Проверка на формат и диапазоны времени
    if re.match(r"^\d{2}:\d{2}$", time_input):
        try:
            hour, minute = map(int, time_input.split(':'))
            # Проверка на корректность значений времени
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                reminder["time"] = time_input
                reminder["status"] = "active"
            else:
                raise ValueError
        except ValueError:
            msg = bot.send_message(message.chat.id, "Неверный формат времени. Попробуйте еще раз в формате ЧЧ:ММ")
            bot.register_next_step_handler(msg, process_time_step)
            return
    else:
        msg = bot.send_message(message.chat.id, "Неверный формат времени. Попробуйте еще раз в формате ЧЧ:ММ")
        bot.register_next_step_handler(msg, process_time_step)
        return

    data["users"][user_id]["reminders"].append(reminder)
    del data["users"][user_id]["current_reminder"]
    save_data(data)

    # Сообщение о добавлении напоминания и возврат в меню
    bot.send_message(message.chat.id, "Напоминание добавлено!")
    reminders_menu(message)  # Возврат в меню напоминаний

# Обработка кнопки "Посмотреть напоминания"
@bot.message_handler(func=lambda message: message.text == "Посмотреть")
def view_reminders(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Активные', 'Истекшие')
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите тип напоминаний:", reply_markup=markup)

# Обработка выбора "Активные" напоминания
@bot.message_handler(func=lambda message: message.text == "Активные")
def view_active_reminders(message):
    user_id = str(message.from_user.id)
    data = load_data()
    reminders = data["users"].get(user_id, {}).get("reminders", [])
    current_date = datetime.now()
    
    active = []
    for i, reminder in enumerate(reminders, 1):
        reminder_date = datetime.strptime(reminder["date"] + ' ' + reminder["time"], "%d.%m.%Y %H:%M")
        if reminder_date >= current_date and reminder["status"] == "active":
            active.append(
                f"\n⭐ №{i} ⭐\n\n\n"
                f"📝 Название: {reminder['title']}\n\n"
                f"📅 Дата: {reminder['date']}\n"
                f"🕒 Время: {reminder['time']}\n"
                f"✅ Статус: Активное"
            )
    
    if active:
        response = "*Активные напоминания:*\n\n" + "\n\n".join(active)
    else:
        response = "*Активные напоминания:*\n\nНет активных напоминаний"
    
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

# Обработка выбора "Истекшие" напоминания
@bot.message_handler(func=lambda message: message.text == "Истекшие")
def view_expired_reminders(message):
    user_id = str(message.from_user.id)
    data = load_data()
    reminders = data["users"].get(user_id, {}).get("reminders", [])
    current_date = datetime.now()

    expired = []
    for i, reminder in enumerate(reminders, 1):
        reminder_date = datetime.strptime(reminder["date"] + ' ' + reminder["time"], "%d.%m.%Y %H:%M")
        if reminder_date < current_date and reminder["status"] == "expired":
            expired.append(
                f"\n❌ №{i} ❌\n\n\n"
                f"📝 Название: {reminder['title']}\n\n"
                f"📅 Дата: {reminder['date']}\n"
                f"🕒 Время: {reminder['time']}\n"
                f"✅ Статус: Истекло"
            )

    if expired:
        response = "*Истекшие напоминания:*\n\n" + "\n\n".join(expired)
    else:
        response = "*Истекшие напоминания:*\n\nНет истекших напоминаний"

    bot.send_message(message.chat.id, response, parse_mode="Markdown")

# Обработка кнопки "Удалить"
@bot.message_handler(func=lambda message: message.text == "Удалить")
def delete_reminder(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Удалить напоминание', 'Удалить все напоминания')
    markup.add("Вернуться в меню напоминаний")
    markup.add('В главное меню')
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

# Обработка кнопки "Удалить напоминание"
@bot.message_handler(func=lambda message: message.text == "Удалить напоминание")
def delete_single_reminder(message):
    user_id = str(message.from_user.id)
    data = load_data()
    reminders = data["users"].get(user_id, {}).get("reminders", [])

    if not reminders:
        bot.send_message(message.chat.id, "У вас нет напоминаний")
    else:
        # Разделяем напоминания на активные и истекшие
        active_reminders = []
        expired_reminders = []
        
        for i, reminder in enumerate(reminders, 1):
            if reminder["status"] == "active":
                active_reminders.append(f'⭐️ №{i}. {reminder["title"]} - *(активно)*')
            else:
                expired_reminders.append(f'❌ №{i}. {reminder["title"]} - *(истекшее)*')
        
        # Формируем итоговое сообщение с разделением по статусам
        reminder_text = "*Напишите номер для удаления напоминания:*\n\n"
        
        if active_reminders:
            reminder_text += "\n*Активные напоминания:*\n\n\n" + "\n\n".join(active_reminders) + "\n\n"
        if expired_reminders:
            reminder_text += "\n*Истекшие напоминания:*\n\n\n" + "\n\n".join(expired_reminders) + "\n\n"
        
        # Разделение текста на части, если длина превышает 4096 символов
        while len(reminder_text) > 4096:
            part = reminder_text[:4096]
            reminder_text = reminder_text[4096:]
            bot.send_message(message.chat.id, part, parse_mode='Markdown')

        # Отправляем оставшуюся часть сообщения с клавиатурой и parse_mode='Markdown'
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в меню напоминаний')
        markup.add('В главное меню')
        bot.send_message(message.chat.id, reminder_text, reply_markup=markup, parse_mode='Markdown')
        bot.register_next_step_handler(message, confirm_delete_single_step)

def confirm_delete_single_step(message):
    user_id = str(message.from_user.id)
    data = load_data()
    reminders = data["users"].get(user_id, {}).get("reminders", [])

    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(message.chat.id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_single_step)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if message.text == "Вернуться в меню напоминаний":
        reminders_menu(message)
        return

    try:
        reminder_index = int(message.text) - 1
        if 0 <= reminder_index < len(reminders):
            removed = reminders.pop(reminder_index)
            save_data(data)
            bot.send_message(message.chat.id, f"Напоминание '№{reminder_index + 1}' удалено", parse_mode='Markdown')
            reminders_menu(message)
        else:
            raise IndexError
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Неверный номер напоминания. Пожалуйста, введите правильный номер")
        bot.register_next_step_handler(message, confirm_delete_single_step)

@bot.message_handler(func=lambda message: message.text == "Удалить все напоминания")
def delete_all_reminders(message):
    # Оставляем только одну отправку сообщения
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Вернуться в меню напоминаний')
    markup.add('В главное меню')

    # Отправляем сообщение с кнопками
    bot.send_message(message.chat.id, "Вы уверены, что хотите удалить все напоминания? Напишите *ДА* или *НЕТ*", reply_markup=markup, parse_mode='Markdown')

    # Регистрируем следующий шаг
    bot.register_next_step_handler(message, confirm_delete_all_step)

def confirm_delete_all_step(message):
    user_id = str(message.from_user.id)
    data = load_data()

    # Проверка на мультимедийные сообщения
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        bot.send_message(message.chat.id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        bot.register_next_step_handler(message, confirm_delete_all_step)
        return

    # Обработка кнопок возврата
    if message.text == "В главное меню":
        return_to_menu(message)  # Функция для возвращения в главное меню
        return

    if message.text == "Вернуться в меню напоминаний":
        reminders_menu(message)  # Функция для возвращения в меню напоминаний
        return

    user_reminders = data["users"].get(user_id, {}).get("reminders", [])

    # Проверка на наличие напоминаний
    if not user_reminders and message.text.strip().upper() == "ДА":
        bot.send_message(message.chat.id, "У вас нет напоминаний", parse_mode='Markdown')
        reminders_menu(message)  # Возврат в меню напоминаний
        return

    if message.text.strip().upper() == "ДА":
        # Удаляем все напоминания
        data["users"][user_id]["reminders"] = []
        save_data(data)
        bot.send_message(message.chat.id, "Все напоминания удалены", parse_mode='Markdown')
        reminders_menu(message)  # Возвращаем в меню после удаления всех напоминаний
    elif message.text.strip().upper() == "НЕТ":
        # Возвращаем в меню напоминаний
        bot.send_message(message.chat.id, "Вы вернулись в меню напоминаний", parse_mode='Markdown')
        reminders_menu(message)
    else:
        # Некорректный ответ
        bot.send_message(message.chat.id, "Пожалуйста, напишите *ДА* или *НЕТ*", parse_mode='Markdown')
        bot.register_next_step_handler(message, confirm_delete_all_step)

#----------------------------------------- КОДЫ OBD2-------------------------------

# Загрузка кодов ошибок OBD-II из файла
def load_error_codes():
    error_codes = {}
    with open("files/codes_obd2.txt", "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                code, description = parts
                error_codes[code] = description
    return error_codes

# Загружаем коды ошибок
error_codes = load_error_codes()

# Обработчик нажатия кнопки "OBD2"
@bot.message_handler(func=lambda message: message.text == "Коды OBD2")
def obd2_request(message):
    # Проверка на мультимедийные файлы
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        # Сообщение об ошибке
        bot.send_message(message.chat.id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        # Повторный запрос на ввод, но без отправки повторного текста
        msg = bot.send_message(message.chat.id, "Введите код ошибки (или несколько через запятую):")
        bot.register_next_step_handler(msg, process_error_codes)
        return
    
    # Устанавливаем клавиатуру с кнопкой "В главное меню"
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("В главное меню"))
    
    # Запрашиваем ввод кода ошибки
    msg = bot.send_message(message.chat.id, "Введите код ошибки (или несколько через запятую):", reply_markup=markup)
    bot.register_next_step_handler(msg, process_error_codes)

# Обработка введенных кодов ошибок
def process_error_codes(message):
    # Проверка на мультимедийные файлы
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        # Сообщение об ошибке
        bot.send_message(message.chat.id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        # Не отправляем повторное сообщение, а только регистрируем следующий шаг
        bot.register_next_step_handler(message, process_error_codes)
        return
    
    # Проверка, если пользователь нажал "В главное меню"
    if message.text == "В главное меню":
        return_to_menu(message)
        return

    # Разделение и поиск описания для введенных кодов
    codes = [code.strip().upper() for code in message.text.split(",")]
    response = ""
    
    for code in codes:
        if code in error_codes:
            response += f"🔧 *КОД ОШИБКИ*: {code}\n\n📋 *ОПИСАНИЕ*: {error_codes[code]}\n\n\n"
        else:
            response += f"🔧 *КОД ОШИБКИ*: {code}\n\n❌ *ОПИСАНИЕ*: Не найдено\n\n\n"
    # Отправляем ответ пользователю
    bot.send_message(message.chat.id, response, parse_mode='Markdown')

    # Кнопки для повторного ввода кода ошибки или возврата в главное меню
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("Посмотреть другие ошибки"))
    markup.add(telebot.types.KeyboardButton("В главное меню"))
    bot.send_message(message.chat.id, "Вы можете посмотреть другие ошибки или вернуться в меню", reply_markup=markup)

# Обработчик кнопки "Посмотреть другие ошибки"
@bot.message_handler(func=lambda message: message.text == "Посмотреть другие ошибки")
def another_error_request(message):
    # Проверка на мультимедийные файлы
    if message.photo or message.video or message.document or message.animation or message.sticker or message.location or message.audio or message.contact or message.voice or message.video_note:
        # Сообщение об ошибке
        bot.send_message(message.chat.id, "Извините, но отправка мультимедийных файлов не разрешена. Пожалуйста, введите текстовое сообщение.")
        # Не отправляем повторное сообщение, а только регистрируем следующий шаг
        bot.register_next_step_handler(message, process_error_codes)
        return

    obd2_request(message)




# (ADMIN) ----------------------------------------------- КОД ДЛЯ "АНМИН-ПАНЕЛИ" ------------------------------------------------------

# (ADMIN 1) -------------------------------------------------"ВХОД ДЛЯ АДМИНА" --------------------------------------------------------

ADMIN_USERNAME = "Alex"
ADMIN_PASSWORD = "lox"

admin_sessions = set()

ADMIN_SESSIONS_PATH = 'data base/admin/admin_sessions.json'

# Функции для работы с единой базой данных
# В функции load_admin_data добавляем загрузку удалённых админов
def load_admin_data():
    if os.path.exists(ADMIN_SESSIONS_PATH):
        with open(ADMIN_SESSIONS_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return {
                "admin_sessions": set(data.get("admin_sessions", [])),
                "admins_data": data.get("admins_data", {}),
                "removed_admins": set(data.get("removed_admins", [])),
                "login_password_hash": data.get("login_password_hash", "")
            }
    return {
        "admin_sessions": set(),
        "admins_data": {},
        "removed_admins": set(),
        "login_password_hash": ""
    }

def save_admin_data(admin_sessions, admins_data, login_password_hash, removed_admins=None):
    with open(ADMIN_SESSIONS_PATH, 'w', encoding='utf-8') as file:
        json.dump({
            "admin_sessions": list(admin_sessions),
            "admins_data": admins_data,
            "removed_admins": list(removed_admins or set()),
            "login_password_hash": login_password_hash
        }, file, ensure_ascii=False, indent=4)

# Загрузка данных из единой базы
data = load_admin_data()
admin_sessions = data["admin_sessions"]
admins_data = data["admins_data"]
login_password_hash = data["login_password_hash"]

login_password_hash = hashlib.sha256(f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}".encode()).hexdigest()

# Функция для получения хеша
def get_login_password_hash():
    return hashlib.sha256(f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}".encode()).hexdigest()

# Функция для обновления данных входа
def update_login_password(new_username=None, new_password=None):
    global ADMIN_USERNAME, ADMIN_PASSWORD, login_password_hash
    
    # Обновляем логин, если он изменился
    if new_username:
        ADMIN_USERNAME = new_username
    
    # Обновляем пароль, если он изменился
    if new_password:
        ADMIN_PASSWORD = new_password
    
    # Пересчитываем хеш с актуальными данными
    login_password_hash = get_login_password_hash()

    # Выводим обновлённые данные (для проверки)
    print(f"Новый логин: {ADMIN_USERNAME}, Новый пароль: {ADMIN_PASSWORD}, Новый хеш: {login_password_hash}")

def verify_login_password_hash():
    global admin_sessions, login_password_hash
    current_hash = get_login_password_hash()
    if current_hash != login_password_hash:
        admin_sessions.clear()
        save_admin_data(admin_sessions, admins_data, current_hash)
    else:
        login_password_hash = current_hash

verify_login_password_hash()

# Функция изменения логина и пароля
def change_admin_credentials(new_username=None, new_password=None):
    global ADMIN_USERNAME, ADMIN_PASSWORD, login_password_hash
    
    # Меняем логин, если это требуется
    if new_username:
        ADMIN_USERNAME = new_username
    
    # Меняем пароль, если это требуется
    if new_password:
        ADMIN_PASSWORD = new_password
    
    # Генерация хеша с актуальными данными логина и пароля
    login_password_hash = get_login_password_hash()
    
    # Обновляем данные в базе
    save_admin_data(admin_sessions, admins_data, login_password_hash)

# Функции управления администраторами. Добавление администратора
def add_admin(admin_id, username, permissions):
    admin_id = str(admin_id)
    user_data = {
        "user_id": admin_id,
        "first_name": " ",
        "last_name": " ",
        "username": username,
        "phone": " ",
        "permissions": permissions
    }
    admins_data[admin_id] = user_data
    admin_sessions.add(admin_id)  # Добавляем в текущие сессии
    save_admin_data(admin_sessions, admins_data, login_password_hash)
    bot.send_message(admin_id, "Вы стали администратором! Быстрый вход доступен.")

# Удаление администратора
def remove_admin(admin_id):
    admin_id = str(admin_id)
    if admin_id in admins_data:
        # Добавляем в список удалённых администраторов
        removed_admins.add(admin_id)
        
        # Удаляем данные администратора
        del admins_data[admin_id]
        admin_sessions.discard(admin_id)
        
        # Сохраняем изменения
        save_admin_data(admin_sessions, admins_data, login_password_hash)
        bot.send_message(admin_id, "Вас удалили из администраторов.")
    else:
        bot.send_message(admin_id, "Администратор с таким ID не найден.")

def check_permission(admin_id, permission):
    return permission in admins_data.get(str(admin_id), {}).get("permissions", [])

# Функция для получения данных о пользователе Telegram
def get_user_data(message):
    user = message.from_user
    return {
        "user_id": user.id,
        "first_name": user.first_name if user.first_name else " ",
        "last_name": user.last_name if user.last_name else " ",
        "username": f"@{user.username}" if user.username else " ",
        "phone": user.phone_number if hasattr(user, 'phone_number') else " "
    }

# Функция обновления данных администратора в базе
def update_admin_data(user_data):
    admin_id = str(user_data["user_id"])
    
    # Проверяем, не находится ли администратор в списке удалённых
    if admin_id in removed_admins:
        print(f"Пользователь с ID {admin_id} был ранее удалён и не может быть добавлен обратно.")
        return
    
    if admin_id in admins_data:
        existing_data = admins_data[admin_id]
        # Обновляем только если данные изменились
        if (existing_data.get("first_name") != user_data["first_name"] or
            existing_data.get("last_name") != user_data["last_name"] or
            existing_data.get("username") != user_data["username"] or
            existing_data.get("phone") != user_data["phone"]):
            admins_data[admin_id].update(user_data)
            save_admin_data(admin_sessions, admins_data, login_password_hash)
    else:
        # Если пользователя нет в базе и он не удалён, добавляем его
        admins_data[admin_id] = user_data
        save_admin_data(admin_sessions, admins_data, login_password_hash)

# Обработчик входа в админ-панель
@bot.message_handler(commands=['admin'])
def handle_admin_login(message):
    user_data = get_user_data(message)
    
    # Проверяем, есть ли пользователь в сессиях
    if str(user_data["user_id"]) in admin_sessions:  # Если сессия активна
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add('Быстрый вход')
        markup.add('Ввести логин и пароль заново')
        markup.add('В главное меню')
        bot.send_message(
            user_data["user_id"], 
            "Выберите способ входа:", 
            reply_markup=markup
        )
        bot.register_next_step_handler(message, process_login_choice)
    else:
        # Предлагаем авторизоваться заново
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_main = types.KeyboardButton("В главное меню")
        markup.add(item_main)
        bot.send_message(message.chat.id, "Введите логин:", reply_markup=markup)
        bot.register_next_step_handler(message, verify_username)

def process_login_choice(message):
    user_id = str(message.chat.id)
    
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    
    if message.text == "Быстрый вход":
        if user_id in admin_sessions:
            session_data = admins_data.get(user_id, {})
            bot.send_message(message.chat.id, f"Добро пожаловать в админ-панель, {session_data.get('username', 'Админ')}!")
            show_admin_panel(message)
        else:
            bot.send_message(message.chat.id, "Сессия недействительна. Пожалуйста, авторизуйтесь заново.")
            handle_admin_login(message)
    elif message.text == "Ввести логин и пароль заново":
        bot.send_message(message.chat.id, "Введите логин:")
        bot.register_next_step_handler(message, verify_username)
    else:
        bot.send_message(message.chat.id, "Неверный выбор. Попробуйте снова.")
        handle_admin_login(message)

def verify_username(message):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    username = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_main)
    bot.send_message(message.chat.id, "Введите пароль:", reply_markup=markup)
    bot.register_next_step_handler(message, verify_password, username)

def verify_password(message, username):
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    password = message.text
    admin_id = str(message.chat.id)
    
    # Проверяем, удалён ли администратор
    if admin_id in removed_admins:
        bot.send_message(message.chat.id, "Ваш доступ был отключён. Обратитесь к корневому администратору.")
        return

    # Проверяем общий логин/пароль
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        # Добавляем админа в активные сессии
        admin_sessions.add(admin_id)
        save_admin_data(admin_sessions, admins_data, login_password_hash, removed_admins)
        
        # Обновляем данные администратора в базе
        user_data = get_user_data(message)
        update_admin_data(user_data)
        
        bot.send_message(message.chat.id, "Добро пожаловать в админ-панель!")
        show_admin_panel(message)
        return
    
    # Проверяем индивидуальный хеш
    admin_hash = admins_data.get(admin_id, {}).get("login_password_hash_for_user_id", "")
    if generate_login_password_hash(username, password) == admin_hash:
        # Добавляем админа в активные сессии
        admin_sessions.add(admin_id)
        save_admin_data(admin_sessions, admins_data, login_password_hash, removed_admins)
        
        # Обновляем данные администратора в базе
        user_data = get_user_data(message)
        update_admin_data(user_data)
        
        bot.send_message(message.chat.id, "Добро пожаловать в админ-панель!")
        show_admin_panel(message)
    else:
        bot.send_message(message.chat.id, "Неверные логин или пароль. Попробуйте снова.")
        handle_admin_login(message)

# Функция выхода из админ-панели
@bot.message_handler(func=lambda message: message.text == 'Выход' and str(message.chat.id) in admin_sessions)
def admin_logout(message):
    # Админ-сессия сохраняется, просто информируем о выходе
    bot.send_message(message.chat.id, "Вы вышли из админ-панели. Быстрый вход сохранен.")
    return_to_menu(message)

# (ADMIN 2) ---------------------------------------------- "МЕНЮ ДЛЯ АДМИН-ПАНЕЛИ" ------------------------------------------------

# Показ админ-панели
def show_admin_panel(message):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(
        'Админ',
        'Вкл/выкл функций',
        'Бан',
        'Оповещения',
        'Чат',
        'Файлы',
        'Статистика',
        'Диалоги',
        'Резервная копия',
        'Выход'
    )
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

# Обработчик для кнопки "В меню админ-панели"
@bot.message_handler(func=lambda message: message.text == 'В меню админ-панели')
def handle_return_to_admin_panel(message):
    show_admin_panel(message)


# (ADMIN 3) --------------------------------- " ФУНКЦИЯ "АДМИН" " --------------------------------------------- 

# Обработчик для кнопки "Настройка"
@bot.message_handler(func=lambda message: message.text == 'Админ')
def show_settings_menu(message):
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(
        'Смена данных входа',
        'Добавить админа',
        'Удалить админа',
        'В меню админ-панели'
    )
    bot.send_message(message.chat.id, "Выберите настройку:", reply_markup=markup)


# Функция для генерации хеша логина и пароля
def generate_login_password_hash(username, password):
    return hashlib.sha256(f"{username}:{password}".encode()).hexdigest()

# Функция для изменения данных входа для конкретного admin_id
def update_admin_login_credentials(admin_id, new_username=None, new_password=None):
    admin_id = str(admin_id)
    if admin_id not in admins_data:
        bot.send_message(admin_id, "Администратор не найден.")
        return
    
    # Получаем текущие данные
    current_username = ADMIN_USERNAME if new_username is None else new_username
    current_password = ADMIN_PASSWORD if new_password is None else new_password

    # Генерируем новый хеш
    new_hash = generate_login_password_hash(current_username, current_password)

    # Обновляем данные в базе
    admins_data[admin_id]["login_password_hash_for_user_id"] = new_hash
    save_admin_data(admin_sessions, admins_data, login_password_hash)
    bot.send_message(admin_id, "Данные входа обновлены.")

# Обработчики смены логина и пароля
@bot.message_handler(func=lambda message: message.text == 'Смена данных входа' and str(message.chat.id) in admin_sessions)
def handle_change_credentials(message):
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(
        'Сменить логин',
        'Сменить пароль',
        'Сменить логин и пароль',
        'Назад'
    )
    bot.send_message(message.chat.id, "Выберите, что хотите изменить:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Сменить логин')
def handle_change_login(message):
    bot.send_message(message.chat.id, "Введите новый логин:")
    bot.register_next_step_handler(message, process_new_login)

def process_new_login(message):
    new_login = message.text
    update_admin_login_credentials(message.chat.id, new_username=new_login)

@bot.message_handler(func=lambda message: message.text == 'Сменить пароль')
def handle_change_password(message):
    bot.send_message(message.chat.id, "Введите новый пароль:")
    bot.register_next_step_handler(message, process_new_password)

def process_new_password(message):
    new_password = message.text
    update_admin_login_credentials(message.chat.id, new_password=new_password)

@bot.message_handler(func=lambda message: message.text == 'Сменить логин и пароль')
def handle_change_login_and_password(message):
    bot.send_message(message.chat.id, "Введите новый логин:")
    bot.register_next_step_handler(message, process_new_login_and_password_step1)

def process_new_login_and_password_step1(message):
    new_login = message.text
    bot.send_message(message.chat.id, "Введите новый пароль:")
    bot.register_next_step_handler(message, process_new_login_and_password_step2, new_login)

def process_new_login_and_password_step2(message, new_login):
    new_password = message.text
    update_admin_login_credentials(message.chat.id, new_username=new_login, new_password=new_password)


# Добавление и удаление администраторов
@bot.message_handler(func=lambda message: message.text == 'Добавить админа' and str(message.chat.id) in admin_sessions)
def handle_add_admin(message):
    # Проверяем, является ли текущий пользователь корневым администратором
    root_admin_id = list(admins_data.keys())[0]  # Первый ID в списке `admins_data`
    if str(message.chat.id) != root_admin_id:
        bot.send_message(message.chat.id, "Недостаточно прав. Только корневой администратор может добавлять администраторов.")
        return

    bot.send_message(message.chat.id, "Введите ID нового администратора:")
    bot.register_next_step_handler(message, process_new_admin_id, root_admin_id)

def process_new_admin_id(message, root_admin_id):
    admin_id = message.text.strip()
    if not admin_id.isdigit():
        bot.send_message(message.chat.id, "ID администратора должен быть числом. Попробуйте снова.")
        return
    
    admin_id = int(admin_id)
    bot.send_message(message.chat.id, "Введите username нового администратора:")
    bot.register_next_step_handler(message, process_new_admin_username, admin_id, root_admin_id)

def process_new_admin_username(message, admin_id, root_admin_id):
    username = message.text.strip()

    # Проверяем, существует ли администратор с таким ID
    if str(admin_id) in admins_data:
        bot.send_message(message.chat.id, "Администратор с таким ID уже существует. Добавление отменено.")
        return

    # Добавляем администратора
    add_admin(admin_id, username, permissions=["view_stats", "manage_users"])
    bot.send_message(message.chat.id, f"Администратор {username} с ID {admin_id} успешно добавлен.")

# Добавляем список для хранения удалённых администраторов
removed_admins = set()

data = load_admin_data()
admin_sessions = data["admin_sessions"]
admins_data = data["admins_data"]
removed_admins = data["removed_admins"]  # Загружаем список удалённых админов
login_password_hash = data["login_password_hash"]

@bot.message_handler(func=lambda message: message.text == 'Удалить админа' and str(message.chat.id) in admin_sessions)
def handle_remove_admin(message):
    # Проверяем, является ли текущий пользователь корневым администратором
    root_admin_id = list(admins_data.keys())[0]  # Первый ID в списке `admins_data`
    if str(message.chat.id) != root_admin_id:
        bot.send_message(message.chat.id, "Недостаточно прав. Только корневой администратор может удалять администраторов.")
        return

    bot.send_message(message.chat.id, "Введите ID или username администратора для удаления:")
    bot.register_next_step_handler(message, process_remove_admin, root_admin_id)

def process_remove_admin(message, root_admin_id):
    input_data = message.text.strip()

    # Проверяем, вводится ли ID
    if input_data.isdigit():
        admin_id = input_data
    else:
        # Проверяем, вводится ли username
        admin_id = next(
            (admin_id for admin_id, data in admins_data.items() if data.get("username") == input_data),
            None
        )
        if not admin_id:
            bot.send_message(message.chat.id, "Администратор с таким username не найден. Попробуйте снова.")
            return
    
    # Проверка: нельзя удалить самого себя
    if str(message.chat.id) == admin_id:
        bot.send_message(message.chat.id, "Невозможно удалить самого себя!")
        return

    # Проверка: нельзя удалить корневого администратора
    if admin_id == root_admin_id:
        bot.send_message(message.chat.id, "Невозможно удалить корневого администратора!")
        return

    if admin_id in admins_data:
        # Удаляем администратора из базы данных
        del admins_data[admin_id]
        admin_sessions.discard(admin_id)
        removed_admins.add(admin_id)  # Добавляем в список удалённых
        save_admin_data(admin_sessions, admins_data, login_password_hash, removed_admins)
        bot.send_message(message.chat.id, f"Администратор {input_data} успешно удалён.")
    else:
        bot.send_message(message.chat.id, "Администратор с таким ID или username не найден.")

# Пример использования прав
@bot.message_handler(commands=['some_command'])
def some_command(message):
    if check_permission(message.chat.id, "some_permission"):
        bot.send_message(message.chat.id, "Команда выполнена.")
    else:
        bot.send_message(message.chat.id, "У вас нет прав на выполнение этой команды.")


# (ADMIN 3) ------------------------------------------ "БАН ПОЛЬЗОВАТЕЛЙ ДЛЯ АДМИН-ПАНЕЛИ" ---------------------------------------------------

BLOCKED_USERS_PATH = 'data base/admin/blocked_users.json'

# Декоратор для ограничения доступа
def restricted(func):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        if is_user_blocked(user_id):
            bot.send_message(message.chat.id, "Вы заблокированы и не можете выполнять это действие.")
            return
        return func(message, *args, **kwargs)
    return wrapper

def save_blocked_users(blocked_users):
    with open(BLOCKED_USERS_PATH, 'w', encoding='utf-8') as file:
        json.dump(list(blocked_users), file)

# Загрузка и сохранение данных заблокированных пользователей
def load_blocked_users():
    if os.path.exists(BLOCKED_USERS_PATH):
        with open(BLOCKED_USERS_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)  # Вернем данные как список
    return []  # Пустой список, если файл не существует

# Получаем ID пользователя по никнейму
def get_user_id_by_username(username):
    user_data = load_user_data()
    for user_id, data in user_data.items():
        if data['username'] == username:
            return user_id
    return None

# Обработка команд админа
@bot.message_handler(func=lambda message: message.text == 'Бан' and message.chat.id in admin_sessions)
def ban_user_prompt(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Заблокировать", "Разблокировать", "В меню админ-панели")
    bot.send_message(message.chat.id, "Выберите действие для пользователя:", reply_markup=markup)
    bot.register_next_step_handler(message, choose_ban_action)

def choose_ban_action(message):
    if message.text == "Заблокировать":
        choose_block_method(message)
    elif message.text == "Разблокировать":
        choose_unblock_method(message)
    elif message.text == "В меню админ-панели":
        show_admin_panel(message)

def choose_block_method(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("По ID", "По никнейму (@username)", "В меню админ-панели")
    bot.send_message(message.chat.id, "Выберите способ блокировки:", reply_markup=markup)
    bot.register_next_step_handler(message, process_block_method)

def process_block_method(message):
    if message.text == "По ID":
        bot.send_message(message.chat.id, "Введите ID пользователя для блокировки:")
        bot.register_next_step_handler(message, block_user_by_id)
    elif message.text == "По никнейму (@username)":
        bot.send_message(message.chat.id, "Введите никнейм пользователя для блокировки (например, @username):")
        bot.register_next_step_handler(message, block_user_by_username)
    elif message.text == "В меню админ-панели":
        show_admin_panel(message)

# Блокировка пользователя по ID
def block_user(user_id, username):
    blocked_users = load_blocked_users()
    if any(user['id'] == user_id for user in blocked_users):
        return "Этот пользователь уже заблокирован."
    blocked_users.append({'id': user_id, 'username': username})
    save_blocked_users(blocked_users)
    return f"Пользователь с ID {user_id} заблокирован."

def block_user_by_username(message):
    username = message.text.strip().lstrip('@')
    user_id = get_user_id_by_username(username)

    if user_id is not None:
        if is_user_blocked(user_id):
            bot.send_message(message.chat.id, "Этот пользователь уже заблокирован.")
        else:
            block_user(user_id, username)  # Передайте оба аргумента
            bot.send_message(message.chat.id, f"Пользователь с никнеймом {username} заблокирован.")
    else:
        bot.send_message(message.chat.id, f"Пользователь с никнеймом {username} не найден.")

def block_user_by_id(message):
    user_id = message.text
    if user_id.isdigit():
        user_id = int(user_id)
        if is_user_blocked(user_id):
            bot.send_message(message.chat.id, "Этот пользователь уже заблокирован.")
        else:
            username = get_username_by_id(user_id)  # Добавьте функцию для получения username по ID
            block_user(user_id, username)  # Передайте оба аргумента
            bot.send_message(message.chat.id, f"Пользователь с ID {user_id} заблокирован.")
    else:
        bot.send_message(message.chat.id, "Некорректный ID. Попробуйте снова.")

def is_user_blocked(user_id):
    blocked_users = load_blocked_users()
    for user in blocked_users:
        if user['id'] == str(user_id):
            return True
    return False

def choose_unblock_method(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("По ID", "По никнейму (@username)", "В меню админ-панели")
    bot.send_message(message.chat.id, "Выберите способ разблокировки:", reply_markup=markup)
    bot.register_next_step_handler(message, process_unblock_method)

def process_unblock_method(message):
    if message.text == "По ID":
        bot.send_message(message.chat.id, "Введите ID пользователя для разблокировки:")
        bot.register_next_step_handler(message, unblock_user_by_id)
    elif message.text == "По никнейму (@username)":
        bot.send_message(message.chat.id, "Введите никнейм пользователя для разблокировки (например, @username):")
        bot.register_next_step_handler(message, unblock_user_by_username)
    elif message.text == "В меню админ-панели":
        show_admin_panel(message)

# Разблокировка пользователя по ID
def unblock_user(user_id):
    blocked_users = load_blocked_users()
    updated_blocked_users = [user for user in blocked_users if user['id'] != str(user_id)]
    if len(blocked_users) == len(updated_blocked_users):
        return "Этот пользователь уже разблокирован."
    save_blocked_users(updated_blocked_users)
    return f"Пользователь с ID {user_id} разблокирован."

# Функции для разблокировки по ID или никнейму
def unblock_user_by_id(message):
    user_id = message.text
    if user_id.isdigit():
        user_id = int(user_id)
        if not is_user_blocked(user_id):
            bot.send_message(message.chat.id, "Этот пользователь уже разблокирован.")
        else:
            unblock_user(user_id)
            bot.send_message(message.chat.id, f"Пользователь с ID {user_id} разблокирован.")
    else:
        bot.send_message(message.chat.id, "Некорректный ID. Попробуйте снова.")
    show_admin_panel(message)

def unblock_user_by_username(message):
    username = message.text.strip().lstrip('@')
    user_id = get_user_id_by_username(username)

    if user_id is not None:
        if not is_user_blocked(user_id):
            bot.send_message(message.chat.id, "Этот пользователь уже разблокирован.")
        else:
            unblock_user(user_id)
            bot.send_message(message.chat.id, f"Пользователь с никнеймом {username} разблокирован.")
    else:
        bot.send_message(message.chat.id, f"Пользователь с никнеймом {username} не найден.")
    show_admin_panel(message)

# (ADMIN 4) ------------------------------------------ "СТАТИСТИКА ДЛЯ АДМИН-ПАНЕЛИ" ---------------------------------------------------

active_users = {}
total_users = set()

USER_DATA_PATH = 'data base/admin/users.json'
INACTIVE_TIME = timedelta(minutes=5)


USER_DATA_PATH = 'data base/admin/users.json'
function_usage = {'Статистика': 0, 'Отзывы': 0, 'Просмотр файлов БД': 0, 'Просмотр всех файлов': 0}
INACTIVE_TIME = timedelta(minutes=1)

def save_user_data(user_data):
    with open(USER_DATA_PATH, 'w', encoding='utf-8') as file:
        json.dump(user_data, file, ensure_ascii=False, indent=4)

# Функции для загрузки и сохранения данных
def load_user_data():
    if os.path.exists(USER_DATA_PATH):
        with open(USER_DATA_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

# Пример обработчика для команды статистики
@bot.message_handler(func=lambda message: message.text == 'Статистика' and message.chat.id in admin_sessions)
def show_statistics(message):
    """Показать статистику пользователей."""
    online_count, total_count, function_usage = get_statistics()  # Получаем статистику

    # Получаем список активных пользователей
    active_user_list = list_active_users()  # Получаем список активных пользователей

    response_message = (
        f"Пользователи онлайн: {online_count}\n"
        f"Всего пользователей: {total_count}\n\n"
        f"Использование функций:\n"
        f"Статистика: {function_usage['Статистика']}\n"
        f"Отзывы: {function_usage['Отзывы']}"
    )

    bot.send_message(message.chat.id, response_message)

    if active_user_list:
        bot.send_message(message.chat.id, "Пользователи онлайн:\n" + active_user_list)
    else:
        bot.send_message(message.chat.id, "Нет активных пользователей.")

# Проверка и загрузка статистики пользователей
def get_statistics():
    online_count = sum(1 for last_active in active_users.values() if datetime.now() - last_active <= INACTIVE_TIME)
    total_count = len(total_users)
    return online_count, total_count, function_usage

# Функция обновления активности пользователя
def update_user_activity(user_id, username=None):
    active_users[user_id] = datetime.now()
    total_users.add(user_id)

    user_data = load_user_data()
    if user_id in user_data:
        user_data[user_id]['username'] = username
        user_data[user_id]['last_active'] = datetime.now().isoformat()
    else:
        user_data[user_id] = {
            'username': username,
            'last_active': datetime.now().isoformat()
        }
    save_user_data(user_data)

def add_or_update_user(user_id, username):
    """Добавить нового пользователя или обновить существующего."""
    users_data = load_user_data()  # Загрузка текущих данных пользователей
    current_time = datetime.now().isoformat()  # Получаем текущее время

    # Обновляем или добавляем пользователя
    users_data[user_id] = {"username": username, "last_active": current_time}
    save_user_data(users_data)  # Сохраняем обновленные данные

def is_user_active(last_active):
    """Проверить, активен ли пользователь."""
    active_threshold = 1 * 60  # 1(5) минут
    last_active_time = datetime.fromisoformat(last_active)
    active = (datetime.now() - last_active_time).total_seconds() < active_threshold
    print(f"Пользователь активен: {active}, последний актив: {last_active}, текущее время: {datetime.now().isoformat()}")  # Отладочная информация
    return active

def get_statistics():
    """Получить статистику пользователей."""
    users_data = load_user_data()  # Загрузка данных пользователей
    online_users = len([user for user in users_data.values() if is_user_active(user["last_active"])])
    total_users = len(users_data)

    function_usage = {
        "Статистика": 0,
        "Отзывы": 0
    }

    print(f"Всего пользователей: {total_users}, Онлайн пользователей: {online_users}")  # Отладочная информация

    return online_users, total_users, function_usage

def list_active_users():
    """Получить список активных пользователей с их ID и нумерацией."""
    users_data = load_user_data()  # Загрузка данных пользователей
    active_users = [
        f"{index + 1}) {user_id}: @{user['username']}" 
        for index, (user_id, user) in enumerate(users_data.items())
        if is_user_active(user["last_active"])
    ]
    return "\n".join(active_users) if active_users else None


# (ADMIN 5) ------------------------------------------ "РЕЗЕРВНАЯ КОПИЯ ДЛЯ АДМИН-ПАНЕЛИ" ---------------------------------------------------

import zipfile

# Путь к директории для бэкапов и текущего исполняемого файла
BACKUP_DIR = 'backups'
SOURCE_DIR = '.'
EXECUTABLE_FILE = '(59 update ) CAR MANAGER TG BOT (official) v0924.py'

def normalize_name(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name)

# Обработчик для кнопки "Резервная копия"
@bot.message_handler(func=lambda message: message.text == 'Резервная копия')
def show_backup_menu(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Создать копию', 'Восстановить данные')
    markup.add('В меню админ-панели')

    bot.send_message(message.chat.id, "Выберите действие с резервной копией:", reply_markup=markup)

# Обработчик для кнопки "Создать копию"
@bot.message_handler(func=lambda message: message.text == 'Создать копию')
def handle_create_backup(message):
    backup_path = create_backup()
    bot.send_message(message.chat.id, f"Резервная копия создана!\n\nПуть к резвервной копии: _{backup_path}_", parse_mode="Markdown")
    show_admin_panel(message)

# Обработчик для кнопки "Восстановить данные"
@bot.message_handler(func=lambda message: message.text == 'Восстановить данные')
def handle_restore_backup(message):
    success = restore_latest_backup()
    if success:
        bot.send_message(message.chat.id, "Данные успешно восстановлены из последнего бэкапа!")
    else:
        bot.send_message(message.chat.id, "Ошибка: последний бэкап не найден")
    show_admin_panel(message)

# Функция для создания резервной копии
def create_backup():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f'backup_{timestamp}.zip')

    os.makedirs(BACKUP_DIR, exist_ok=True)

    with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(SOURCE_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, SOURCE_DIR)

                # Пропускаем папку "backups" и исполняемый файл
                if BACKUP_DIR in arcname or EXECUTABLE_FILE in arcname:
                    continue

                zipf.write(file_path, arcname)

    return backup_file

# Функция для восстановления из последнего бэкапа
def restore_latest_backup():
    backups = sorted(os.listdir(BACKUP_DIR), reverse=True)
    if not backups:
        print("Нет бэкапов для восстановления")
        return False

    latest_backup = os.path.join(BACKUP_DIR, backups[0])

    if not os.path.exists(latest_backup):
        print(f"Ошибка: Бэкап {latest_backup} не найден")
        return False

    with zipfile.ZipFile(latest_backup, 'r') as zipf:
        zipf.extractall(SOURCE_DIR)

    print("Восстановление завершено")
    return True



# (ADMIN n) ------------------------------------------ "ВКЛ/ВЫКЛ ФУУНКЦИЙ ДЛЯ АДМИН-ПАНЕЛИ" ---------------------------------------------------

# Путь к файлу с состоянием функций
FUNCTIONS_STATE_PATH = 'data base/admin/functions_state.json'

# Функция загрузки состояния функций из файла
def load_function_states():
    if os.path.exists(FUNCTIONS_STATE_PATH):
        with open(FUNCTIONS_STATE_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    else:
        save_function_states()  # Создаем файл с начальным состоянием
        return function_states

# Сохранение состояния функций в файл
def save_function_states():
    with open(FUNCTIONS_STATE_PATH, 'w', encoding='utf-8') as file:
        json.dump(function_states, file, ensure_ascii=False, indent=4)

# Загрузка состояний функций при старте
function_states = load_function_states()

def set_function_state(function_name, state):
    if function_name in function_states:
        function_states[function_name] = state
        save_function_states()  # Сохраняем изменения
        return f"Функция '{function_name}' успешно {'активирована' if state else 'деактивирована'}."
    else:
        return "Ошибка: Функция не найдена."

def activate_function(function_name):
    return set_function_state(function_name, True)

def deactivate_function(function_name):
    return set_function_state(function_name, False)

# Функция для активации функции через некоторое время
def activate_function_later(function_name, delay):
    threading.Timer(delay.total_seconds(), activate_function, args=[function_name]).start()

# Обработчик временной деактивации
def handle_time_deactivation(time_spec, function_name):
    try:
        end_time = datetime.strptime(time_spec, "%H:%M %d.%m.%Y")
        now = datetime.now()
        
        # Проверяем, что время в будущем
        if end_time > now:
            deactivate_function(function_name)  # Деактивируем сразу
            delay = end_time - now  # Вычисляем задержку
            activate_function_later(function_name, delay)  # Запускаем активацию позже
        else:
            print("Указанное время уже прошло.")
    except ValueError:
        print("Неверный формат времени. Используйте 'ЧЧ:ММ ДД.ММ.ГГГГ'.")

# Ваша команда для настройки функций
@bot.message_handler(func=lambda message: message.text == 'Вкл/выкл функций' and message.chat.id in admin_sessions)
@bot.message_handler(commands=['set_function'])
def set_function(message):
    if message.chat.id in admin_sessions:  # Проверяем, является ли пользователь администратором
        command_parts = message.text.split()
        if len(command_parts) >= 3:
            action = command_parts[1]  # activate или deactivate
            function_name = " ".join(command_parts[2:-2])  # Название функции
            time_spec = " ".join(command_parts[-2:])  # Временной аргумент

            if action == "activate":
                response = activate_function(function_name)
            elif action == "deactivate":
                if time_spec:  # Если указан временной аргумент
                    handle_time_deactivation(time_spec, function_name)
                    response = f"{function_name} будет деактивирована до {time_spec}."
                else:
                    response = deactivate_function(function_name)
            else:
                response = "Недопустимое действие. Используйте 'activate' или 'deactivate'."
        else:
            response = "Используйте команду в формате:\n\n /set_function <activate/deactivate> <function_name> [time]\n\n Например:\n\n /set_function deactivate Траты и ремонты 00:00 01.01.2025."
        
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

# (ADMIN n) ------------------------------------------ "ОПОВЕЩЕНИЯ ДЛЯ АДМИН-ПАНЕЛИ" ---------------------------------------------------

USER_DATA_PATH = 'data base/admin/users.json'
SENT_MESSAGES_PATH = 'data base/admin/sent_messages.json'
NOTIFICATIONS_PATH = 'data base/admin/notifications.json'
notifications = []  # Список для хранения уведомлений по времени
sent_messages = []  # Список для хранения отправленных сообщений

# Загрузка пользователей
def load_users():
    if os.path.exists(USER_DATA_PATH):
        with open(USER_DATA_PATH, 'r') as file:
            return json.load(file)
    return {}

# Загрузка отправленных сообщений
def load_sent_messages():
    if os.path.exists(SENT_MESSAGES_PATH):
        with open(SENT_MESSAGES_PATH, 'r') as file:
            return json.load(file)
    return []

# Загрузка уведомлений
def load_notifications():
    if os.path.exists(NOTIFICATIONS_PATH):
        with open(NOTIFICATIONS_PATH, 'r') as file:
            loaded_notifications = json.load(file)
            # Преобразование строк обратно в datetime
            for notification in loaded_notifications:
                notification['time'] = datetime.strptime(notification['time'], "%d.%m.%Y, %H:%M")
            return loaded_notifications
    return []

# Сохранение отправленных сообщений
def save_sent_messages():
    with open(SENT_MESSAGES_PATH, 'w') as file:
        json.dump(sent_messages, file)

# Сохранение уведомлений
def save_notifications():
    # Преобразование datetime в строку для сохранения
    notifications_to_save = [
        {
            'text': n['text'],
            'time': n['time'].strftime("%d.%m.%Y, %H:%M"),
            'status': n['status']
        } for n in notifications
    ]
    with open(NOTIFICATIONS_PATH, 'w') as file:
        json.dump(notifications_to_save, file)

# Инициализация отправленных сообщений и уведомлений при запуске
sent_messages = load_sent_messages()
notifications = load_notifications()

def check_notifications():
    while True:
        now = datetime.now()
        for n in notifications:
            if n['status'] == 'active' and n['time'] <= now:
                # Отправка уведомления
                for user_id in load_users().keys():
                    bot.send_message(user_id, n['text'])
                n['status'] = 'sent'  # Обновляем статус
        save_notifications()  # Сохраняем уведомления
        time.sleep(60)  # Проверяем каждую минуту

# Запускаем проверку уведомлений в отдельном потоке
threading.Thread(target=check_notifications, daemon=True).start()

# Показ меню оповещений
@bot.message_handler(func=lambda message: message.text == 'Оповещения' and message.chat.id in admin_sessions)
def show_notifications_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('По времени', 'Всем', 'Отдельно', 'В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите тип оповещения:", reply_markup=markup)

# Обработчик для "По времени"
@bot.message_handler(func=lambda message: message.text == 'По времени' and message.chat.id in admin_sessions)
def handle_time_notifications(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Отправить по времени', 'Активные', 'Остановленные', 'В меню админ-панели')
    bot.send_message(message.chat.id, "Управление оповещениями по времени:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Отправить по времени' and message.chat.id in admin_sessions)
def schedule_notification(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите текст уведомления:", reply_markup=markup)
    bot.register_next_step_handler(message, set_time_for_notification)

def set_time_for_notification(message):
    notification_text = message.text
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите дату (ДД.ММ.ГГГГ):", reply_markup=markup)
    bot.register_next_step_handler(message, process_notification_date, notification_text)

def process_notification_date(message, notification_text):
    date_str = message.text
    if not validate_date_format(date_str):
        bot.send_message(message.chat.id, "Неверный формат даты. Введите дату в формате ДД.ММ.ГГГГ:")
        bot.register_next_step_handler(message, process_notification_date, notification_text)
        return

    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите время (ЧЧ:ММ):", reply_markup=markup)
    bot.register_next_step_handler(message, process_notification_time, notification_text, date_str)

def validate_date_format(date_str):
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False

def process_notification_time(message, notification_text, date_str):
    time_str = message.text
    if not validate_time_format(time_str):
        bot.send_message(message.chat.id, "Неверный формат времени. Введите время в формате ЧЧ:ММ:")
        bot.register_next_step_handler(message, process_notification_time, notification_text, date_str)
        return

    try:
        notification_time = datetime.strptime(f"{date_str}, {time_str}", "%d.%m.%Y, %H:%M")
        notifications.append({
            'text': notification_text,
            'time': notification_time,
            'status': 'active'
        })
        save_notifications()
        bot.send_message(message.chat.id, f"Уведомление '{notification_text}' запланировано на {notification_time}.")
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат. Попробуйте снова.")
        schedule_notification(message)

def validate_time_format(time_str):
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

@bot.message_handler(func=lambda message: message.text == 'Активные' and message.chat.id in admin_sessions)
def show_active_notifications(message):
    if notifications:
        active_notifications = [f"{i + 1}. {n['text']} - {n['time']}" for i, n in enumerate(notifications) if n['status'] == 'active']
        if active_notifications:
            bot.send_message(message.chat.id, "\n".join(active_notifications))
        else:
            bot.send_message(message.chat.id, "Нет активных уведомлений.")
    else:
        bot.send_message(message.chat.id, "Нет уведомлений.")

@bot.message_handler(func=lambda message: message.text == 'Остановленные' and message.chat.id in admin_sessions)
def show_stopped_notifications(message):
    stopped_notifications = [f"{i + 1}. {n['text']} - {n['time']}" for i, n in enumerate(notifications) if n['status'] == 'stopped']
    if stopped_notifications:
        bot.send_message(message.chat.id, "\n".join(stopped_notifications))
    else:
        bot.send_message(message.chat.id, "Нет остановленных уведомлений.")

# Обработчик для "Всем"
@bot.message_handler(func=lambda message: message.text == 'Всем' and message.chat.id in admin_sessions)
def handle_broadcast_notifications(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Отправить сообщение', 'Отправленные', 'Удалить отправленные', 'В меню админ-панели')
    bot.send_message(message.chat.id, "Управление оповещениями для всех:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Отправить сообщение' and message.chat.id in admin_sessions)
def send_message_to_all(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите текст сообщения или отправьте мультимедийный файл:", reply_markup=markup)
    bot.register_next_step_handler(message, process_broadcast_message)
    
def process_broadcast_message(message):
    broadcast_text = message.text
    users = load_users()
    for user_id in users.keys():
        if message.content_type == 'text':
            bot.send_message(user_id, broadcast_text)
        else:
            # Отправляем мультимедийные файлы
            if message.photo:
                bot.send_photo(user_id, message.photo[-1].file_id)  # Отправляем фото
            elif message.video:
                bot.send_video(user_id, message.video.file_id)  # Отправляем видео
            elif message.document:
                bot.send_document(user_id, message.document.file_id)  # Отправляем документ
            elif message.animation:
                bot.send_animation(user_id, message.animation.file_id)  # Отправляем анимацию
            elif message.sticker:
                bot.send_sticker(user_id, message.sticker.file_id)  # Отправляем стикер
            elif message.audio:
                bot.send_audio(user_id, message.audio.file_id)  # Отправляем аудио
            elif message.contact:
                bot.send_contact(user_id, message.contact.phone_number, message.contact.first_name)  # Отправляем контакт
            elif message.voice:
                bot.send_voice(user_id, message.voice.file_id)  # Отправляем голосовое сообщение
            elif message.video_note:
                bot.send_video_note(user_id, message.video_note.file_id)  # Отправляем видеозаметку
            # Важно сохранять информацию о отправленных сообщениях
            sent_messages.append({'user_id': user_id, 'text': broadcast_text, 'timestamp': datetime.now().isoformat()})
    save_sent_messages()
    bot.send_message(message.chat.id, "Сообщение отправлено всем пользователям.")

@bot.message_handler(func=lambda message: message.text == 'Отправленные' and message.chat.id in admin_sessions)
def show_sent_messages(message):
    if sent_messages:  # Используем загруженный список отправленных сообщений
        sent_messages_list = [f"Пользователь ID: {msg['user_id']} - Сообщение: {msg['text']} - Время: {msg['timestamp']}" for msg in sent_messages]
        bot.send_message(message.chat.id, "\n".join(sent_messages_list))
    else:
        bot.send_message(message.chat.id, "Нет отправленных сообщений.")

@bot.message_handler(func=lambda message: message.text == 'Удалить отправленные' and message.chat.id in admin_sessions)
def delete_sent_messages(message):
    bot.send_message(message.chat.id, "Введите номер сообщения для удаления (например, '1' для первого):")
    bot.register_next_step_handler(message, process_delete_message)

def process_delete_message(message):
    try:
        index = int(message.text) - 1
        if 0 <= index < len(sent_messages):
            deleted_message = sent_messages.pop(index)
            save_sent_messages()  # Сохраняем изменения после удаления
            bot.send_message(message.chat.id, f"Сообщение от пользователя ID: {deleted_message['user_id']} удалено.")
        else:
            bot.send_message(message.chat.id, "Неверный номер сообщения. Попробуйте снова.")
            delete_sent_messages(message)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер сообщения.")
        delete_sent_messages(message)

# Обработчик для "Отдельно"
@bot.message_handler(func=lambda message: message.text == 'Отдельно' and message.chat.id in admin_sessions)
def handle_individual_notifications(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите ID или username пользователя:", reply_markup=markup)
    bot.register_next_step_handler(message, process_individual_user)

def process_individual_user(message):
    user_input = message.text
    users = load_users()
    if user_input in users:
        bot.send_message(message.chat.id, "Введите текст сообщения или отправьте мультимедийный файл:")
        bot.register_next_step_handler(message, send_individual_message, user_input)
    else:
        bot.send_message(message.chat.id, "Пользователь не найден. Попробуйте снова.")
        handle_individual_notifications(message)

def send_individual_message(message, user_id):
    if message.content_type == 'text':
        bot.send_message(user_id, message.text)
    else:
        # Отправляем мультимедийные файлы
        if message.photo:
            bot.send_photo(user_id, message.photo[-1].file_id)
        elif message.video:
            bot.send_video(user_id, message.video.file_id)
        elif message.document:
            bot.send_document(user_id, message.document.file_id)
        elif message.animation:
            bot.send_animation(user_id, message.animation.file_id)
        elif message.sticker:
            bot.send_sticker(user_id, message.sticker.file_id)
        elif message.audio:
            bot.send_audio(user_id, message.audio.file_id)
        elif message.contact:
            bot.send_contact(user_id, message.contact.phone_number, message.contact.first_name)
        elif message.voice:
            bot.send_voice(user_id, message.voice.file_id)
        elif message.video_note:
            bot.send_video_note(user_id, message.video_note.file_id)

    bot.send_message(message.chat.id, f"Сообщение отправлено пользователю ID: {user_id}.")

# (ADMIN n) ------------------------------------------ "ЧАТ АДМИНА И ПОЛЬЗОВАТЕЛЯ ФУУНКЦИЙ ДЛЯ АДМИН-ПАНЕЛИ" ---------------------------------------------------

# Пути к файлам
USER_DB_PATH = 'data base/admin/users.json'
ADMIN_DB_PATH = 'data base/admin/admin_sessions.json'

# Переменные для хранения состояния чата
active_chats = {}

# Пути к файлам
CHAT_HISTORY_PATH = 'data base/admin/chat_history.json'  # Новый путь для истории переписки

# Загрузка истории чата
def load_chat_history():
    if os.path.exists(CHAT_HISTORY_PATH):
        with open(CHAT_HISTORY_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

# Сохранение сообщения в историю чата
def save_message_to_history(admin_id, user_id, message_text, message_type):
    chat_history = load_chat_history()
    
    # Создаем уникальный ключ для чата
    chat_key = f"{admin_id}_{user_id}"
    if chat_key not in chat_history:
        chat_history[chat_key] = []

    # Получаем текущее время и форматируем его
    timestamp = datetime.now().strftime("%d.%m.%Y в %H:%M")

    chat_history[chat_key].append({
        "type": message_type,  # 'admin' или 'user'
        "text": message_text,
        "timestamp": timestamp  # Сохраняем дату и время
    })

    with open(CHAT_HISTORY_PATH, 'w', encoding='utf-8') as file:
        json.dump(chat_history, file, ensure_ascii=False, indent=4)

# Загрузка базы данных пользователей
def load_users():
    if os.path.exists(USER_DB_PATH):
        with open(USER_DB_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

# Загрузка базы данных администраторов
def load_admins():
    if os.path.exists(ADMIN_DB_PATH):
        with open(ADMIN_DB_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    return []

# Проверка, является ли пользователь администратором
def is_admin(user_id):
    admins = load_admins()
    return user_id in admins

# Команда для администратора для связи с пользователем
@bot.message_handler(func=lambda message: message.text == 'Чат' and message.chat.id in admin_sessions)
@bot.message_handler(commands=['chat'])
def initiate_chat(message):
    admin_id = message.chat.id

    # Проверка, является ли отправитель администратором
    if not is_admin(admin_id):
        bot.send_message(admin_id, "У вас нет прав для выполнения этой команды.")
        return

    # Проверка наличия ID пользователя в команде
    command_parts = message.text.split()
    if len(command_parts) != 2:
        bot.send_message(admin_id, "Укажите ID пользователя в формате: /chat user_id")
        return

    try:
        user_id = int(command_parts[1])

        # Проверка, существует ли пользователь в базе данных
        users = load_users()
        if str(user_id) not in users:
            bot.send_message(admin_id, "Пользователь с таким ID не найден в базе данных.")
            return

        # Проверка, если чат уже активен
        if user_id in active_chats:
            bot.send_message(admin_id, "Этот пользователь уже находится в активном чате.")
            return

        # Отправляем запрос пользователю
        bot.send_message(user_id, "Администратор хочет связаться с вами. Напишите 'да' для принятия или 'нет' для отклонения.")
        bot.send_message(admin_id, f"Запрос отправлен пользователю {user_id}. Ожидаем ответа...")
        
        # Сохраняем запрос в active_chats
        active_chats[user_id] = {"admin_id": admin_id, "status": "pending"}

    except ValueError:
        bot.send_message(admin_id, "ID пользователя должен быть числом. Пример: /chat 123456789")
    except Exception as e:
        bot.send_message(admin_id, f"Ошибка при выполнении команды: {e}")

# Структуры для хранения активных чатов
active_user_chats = {}  # Хранит, какой администратор общается с пользователем
active_admin_chats = {}  # Хранит, с каким пользователем общается администратор

# Обработка ответов пользователя на запрос чата
# Обработка ответов пользователя на запрос чата
@bot.message_handler(func=lambda message: message.text.lower() in ["да", "нет"])
def handle_chat_response(message):
    user_id = message.from_user.id

    if user_id in active_chats and active_chats[user_id]["status"] == "pending":
        admin_id = active_chats[user_id]["admin_id"]
        if message.text.lower() == "да":
            bot.send_message(user_id, "Вы на связи с администратором.")
            bot.send_message(admin_id, f"Пользователь {user_id} принял запрос на чат.")
            active_chats[user_id]["status"] = "active"
            active_user_chats[user_id] = admin_id  # Добавляем в активные чаты для пользователя
            active_admin_chats[admin_id] = user_id  # Добавляем в активные чаты для администратора
        else:
            bot.send_message(user_id, "Вы отклонили запрос на чат.")
            bot.send_message(admin_id, f"Пользователь {user_id} отклонил запрос на чат.")
            del active_chats[user_id]
    else:
        bot.send_message(user_id, "Нет активного запроса на чат.")

# Команда для завершения чата
@bot.message_handler(func=lambda message: message.text == 'Стоп' and message.chat.id in admin_sessions)
@bot.message_handler(commands=['stopchat'])

def stop_chat(message):
    admin_id = message.chat.id

    # Проверяем, есть ли у администратора активный чат
    if admin_id in active_admin_chats:
        user_id = active_admin_chats[admin_id]

        # Отправляем уведомления о завершении чата
        bot.send_message(user_id, "Админ прекратил с вами общение.")
        bot.send_message(admin_id, f"Чат с пользователем {user_id} остановлен.")

        # Удаляем чат из всех структур
        if admin_id in active_admin_chats:
            del active_admin_chats[admin_id]
        if user_id in active_user_chats:
            del active_user_chats[user_id]
        if user_id in active_chats:
            del active_chats[user_id]

    else:
        bot.send_message(admin_id, "Нет активного чата для завершения.")

# Изменения в функции handle_chat_messages для сохранения сообщений в историю
@bot.message_handler(func=lambda message: message.from_user.id in active_user_chats or message.from_user.id in active_admin_chats)
def handle_chat_messages(message):
    user_id = message.from_user.id

    # Игнорируем команды, чтобы они не пересылались в чате
    if message.text.startswith('/') or message.text.startswith('Стоп'):
        return

    # Если сообщение от администратора
    if user_id in active_admin_chats:
        target_user_id = active_admin_chats[user_id]
        bot.send_message(target_user_id, f"Админ: {message.text}")
        save_message_to_history(user_id, target_user_id, message.text, 'admin')  # Сохранение сообщения
        print(f"Сообщение от админа {user_id} переслано пользователю {target_user_id}: {message.text}")

    # Если сообщение от пользователя
    elif user_id in active_user_chats:
        target_admin_id = active_user_chats[user_id]
        bot.send_message(target_admin_id, f"Пользователь {user_id}: {message.text}")
        save_message_to_history(target_admin_id, user_id, message.text, 'user')  # Сохранение сообщения
        print(f"Сообщение от пользователя {user_id} переслано администратору {target_admin_id}: {message.text}")

@bot.message_handler(func=lambda message: message.text == 'Диалоги' and message.chat.id in admin_sessions)
def show_user_dialogs(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")
        return

    # Загружаем пользователей
    users = load_users()
    user_ids = list(users.keys())

    # Создаем нумерованный список пользователей
    user_list = "\n".join(f"{i + 1}. ID: {user_id}" for i, user_id in enumerate(user_ids))
    bot.send_message(message.chat.id, f"Выберите пользователя:\n{user_list}\nВведите номер пользователя:")

    # Устанавливаем состояние для обработки выбора пользователя
    active_chats[message.chat.id] = {"state": "select_user", "user_ids": user_ids}

@bot.message_handler(func=lambda message: message.chat.id in active_chats and active_chats[message.chat.id].get("state") == "select_user")
def handle_user_selection(message):
    user_ids = active_chats[message.chat.id]["user_ids"]

    try:
        selected_index = int(message.text) - 1
        if selected_index < 0 or selected_index >= len(user_ids):
            raise IndexError  # Если индекс вне диапазона

        selected_user_id = user_ids[selected_index]

        # Загружаем историю чата с выбранным пользователем
        chat_key = f"{message.chat.id}_{selected_user_id}"
        chat_history = load_chat_history().get(chat_key, [])

        if not chat_history:
            bot.send_message(message.chat.id, "История переписки с этим пользователем пуста.")
            return

        # Создаем информацию о диалоге
        dialogue_info = f"Диалог от {chat_history[0]['timestamp']}"  # Все сообщения имеют одинаковую временную метку
        bot.send_message(message.chat.id, f"Выберите диалог:\n1. {dialogue_info}\nВведите номер диалога:")

        # Устанавливаем состояние для обработки выбора диалога
        active_chats[message.chat.id]["state"] = "select_dialog"
        active_chats[message.chat.id]["selected_user_id"] = selected_user_id
        active_chats[message.chat.id]["chat_history"] = chat_history

    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Неверный ввод. Пожалуйста, введите номер пользователя.")

@bot.message_handler(func=lambda message: message.chat.id in active_chats and active_chats[message.chat.id].get("state") == "select_dialog")
def handle_dialog_selection(message):
    chat_history = active_chats[message.chat.id]["chat_history"]
    selected_user_id = active_chats[message.chat.id]["selected_user_id"]

    try:
        selected_index = int(message.text) - 1
        if selected_index != 0:  # У нас только один диалог, индекс 0
            raise IndexError  # Если индекс не 0, возвращаем ошибку

        # Форматируем полный текст диалога
        full_dialogue = "\n".join(
            f"{entry['timestamp']} - {entry['type']}: {entry['text']}" for entry in chat_history
        )

        # Отправляем полный текст диалога
        bot.send_message(message.chat.id, f"Диалог с пользователем ID {selected_user_id}:\n{full_dialogue}")

    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Неверный ввод. Пожалуйста, введите номер диалога.")

    
# Максимальная длина сообщения в Telegram
TELEGRAM_MESSAGE_LIMIT = 4096

# Путь к основной директории файлов
# Определяем основную директорию файлов относительно директории, где находится текущий скрипт
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_PATH = os.path.join(BASE_DIR, 'data base')

# Словарь для хранения данных о файлах и директориях
bot_data = {}

@bot.message_handler(func=lambda message: message.text == 'Просмотр файлов' and message.chat.id in admin_sessions)
def view_files(message):
    bot.send_message(message.chat.id, "Введите путь к директории для просмотра:")
    bot.register_next_step_handler(message, process_directory_view)

def process_directory_view(message):
    directory = os.path.join(FILES_PATH, message.text.strip())
    if os.path.exists(directory) and os.path.isdir(directory):
        files_list = os.listdir(directory)
        
        if files_list:
            # Нумеруем список файлов
            response = "\n".join([f"{i + 1}. {file_name}" for i, file_name in enumerate(files_list)])
            
            # Сохраняем список файлов и директорию для дальнейшего использования
            bot_data[message.chat.id] = {
                "directory": directory,
                "files_list": files_list
            }
            
            # Разбиваем длинное сообщение на части, если оно превышает лимит
            for start in range(0, len(response), TELEGRAM_MESSAGE_LIMIT):
                bot.send_message(message.chat.id, response[start:start + TELEGRAM_MESSAGE_LIMIT])

            # Запрашиваем у пользователя выбор файла
            bot.send_message(message.chat.id, "Введите номер файла для отправки:")
            bot.register_next_step_handler(message, process_file_selection, files_list)  # Передаем список файлов
        else:
            bot.send_message(message.chat.id, "Директория пуста.")
    else:
        bot.send_message(message.chat.id, "Директория не найдена или доступ запрещен.")

# Обработчик для отправки файла по выбранному номеру
def process_file_selection(message, matched_files):
    try:
        file_number = int(message.text.strip()) - 1
        
        # Проверяем, что номер файла корректный
        if 0 <= file_number < len(matched_files):
            directory = bot_data[message.chat.id]["directory"]
            file_name = matched_files[file_number]
            file_path = os.path.join(directory, file_name)
            
            # Отправляем файл
            with open(file_path, 'rb') as file:
                bot.send_document(message.chat.id, file)
        else:
            bot.send_message(message.chat.id, "Некорректный номер файла.")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите номер файла.")

# Поиск файлов пользователя по ID
@bot.message_handler(func=lambda message: message.text == 'Поиск файлов по ID' and message.chat.id in admin_sessions)
def search_files_by_id(message):
    bot.send_message(message.chat.id, "Введите ID пользователя для поиска файлов:")
    bot.register_next_step_handler(message, process_file_search)

def process_file_search(message):
    user_id = message.text.strip()
    matched_files = []

    for root, dirs, files in os.walk(FILES_PATH):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            # Проверка ID в названии файла
            if user_id in file_name:
                matched_files.append(file_path)
            else:
                # Проверка ID внутри файла только для текстовых файлов
                if file_name.endswith(('.txt', '.log', '.csv')):  # Пропускать бинарные файлы
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if re.search(rf'\b{user_id}\b', content):
                                matched_files.append(file_path)
                    except UnicodeDecodeError:
                        print(f"Не удалось прочитать файл {file_path}, пропуск...")

    # Разбиение длинного ответа на части
    if matched_files:
        response = "\n".join([f"{i + 1}. {os.path.basename(path)}" for i, path in enumerate(matched_files)])
        for start in range(0, len(response), TELEGRAM_MESSAGE_LIMIT):
            bot.send_message(message.chat.id, response[start:start + TELEGRAM_MESSAGE_LIMIT])
        bot.send_message(message.chat.id, "Выберите номер файла для отправки:")
        bot.register_next_step_handler(message, process_file_selection, matched_files)
    else:
        bot.send_message(message.chat.id, "Файлы с указанным ID не найдены.")

def process_file_selection(message, matched_files):
    try:
        file_number = int(message.text.strip()) - 1
        if 0 <= file_number < len(matched_files):
            file_path = matched_files[file_number]
            with open(file_path, 'rb') as file:
                bot.send_document(message.chat.id, file)
        else:
            bot.send_message(message.chat.id, "Некорректный номер файла.")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите номер файла.")

# Замена файла
@bot.message_handler(func=lambda message: message.text == 'Замена файлов' and message.chat.id in admin_sessions)
def handle_file_replacement(message):
    bot.send_message(message.chat.id, "Введите путь к файлу для замены:")
    bot.register_next_step_handler(message, process_file_replacement)

def process_file_replacement(message):
    file_path = os.path.join(FILES_PATH, message.text.strip())
    if os.path.exists(file_path):
        bot.send_message(message.chat.id, "Отправьте новый файл для замены.")
        bot.register_next_step_handler(message, replace_file, file_path)
    else:
        bot.send_message(message.chat.id, "Файл не найден.")

def replace_file(message, file_path):
    if message.document:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        bot.send_message(message.chat.id, "Файл успешно заменен.")
    else:
        bot.send_message(message.chat.id, "Неверный формат. Пожалуйста, отправьте файл в формате документа.")

# (ADMIN 6) ------------------------------------------ "ВЫХОД ДЛЯ АДМИН-ПАНЕЛИ" ---------------------------------------------------

# Функция выхода из админ-панели
@bot.message_handler(func=lambda message: message.text == 'Выход' and message.chat.id in admin_sessions)
def admin_logout(message):
    bot.send_message(message.chat.id, "Вы вышли из админ-панели. Быстрый вход сохранен.")
    return_to_menu(message)


# (FEEDBACK) ------------------------------------------ "ОТЗЫВЫ" ---------------------------------------------------

FEEDBACK_FILE_PATH = 'data base/feedback/feedback.json'
ADMIN_FILE_PATH = 'data base/admin/admin_sessions.json'

# Функции для загрузки и сохранения данных
def load_feedback():
    if os.path.exists(FEEDBACK_FILE_PATH):
        with open(FEEDBACK_FILE_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

def save_feedback_data(feedback_data):
    try:
        with open(FEEDBACK_FILE_PATH, 'w', encoding='utf-8') as file:
            json.dump(feedback_data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")

def load_admins():
    if os.path.exists(ADMIN_FILE_PATH):
        with open(ADMIN_FILE_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    return []

def notify_admins(feedback_entry):
    admins = load_admins()
    feedback_message = f"Новый отзыв:\nТекст: {feedback_entry['text']}\nОценка: {feedback_entry['rating']}\nКатегория: {feedback_entry['category']}\nДата: {feedback_entry['date']}"
    for admin_id in admins:
        bot.send_message(admin_id, feedback_message)

@bot.message_handler(commands=['feedback'])
def get_feedback(message):
    update_user_activity(message.from_user.id)  # Обновляем активность пользователя
    bot.send_message(message.chat.id, "Напишите ваш отзыв (или введите /cancel для отмены):")
    bot.register_next_step_handler(message, ask_category)

def ask_category(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "Вы отменили отправку отзыва.")
        return

    feedback_text = message.text
    bot.send_message(message.chat.id, "Укажите категорию отзыва (например, 'Поддержка', 'Продукт', 'Общий'):")
    bot.register_next_step_handler(message, lambda m: ask_rating(m, feedback_text))

def ask_rating(message, feedback_text):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "Вы отменили отправку отзыва.")
        return

    category = message.text
    bot.send_message(message.chat.id, "Поставьте оценку от 1 до 5:")
    bot.register_next_step_handler(message, lambda m: confirm_feedback(m, feedback_text, category))

def confirm_feedback(message, feedback_text, category):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "Вы отменили отправку отзыва.")
        return

    try:
        rating = int(message.text)
        if rating < 1 or rating > 5:
            raise ValueError("Оценка должна быть от 1 до 5.")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректную оценку от 1 до 5:")
        bot.register_next_step_handler(message, lambda m: confirm_feedback(m, feedback_text, category))
        return

    # Подтверждение отправки
    bot.send_message(message.chat.id, f"Вы оставили отзыв: \"{feedback_text}\" с оценкой {rating} в категории \"{category}\". Подтвердите отправку? (да/нет)")
    bot.register_next_step_handler(message, lambda m: save_feedback(m, feedback_text, rating, category))

def save_feedback(message, feedback_text, rating, category):
    if message.text.lower() == 'нет':
        bot.send_message(message.chat.id, "Вы отменили отправку отзыва.")
        return

    if message.text.lower() != 'да':
        bot.send_message(message.chat.id, "Пожалуйста, ответьте 'да' или 'нет'.")
        bot.register_next_step_handler(message, lambda m: save_feedback(m, feedback_text, rating, category))
        return

    feedback_data = load_feedback()
    user_id = str(message.from_user.id)

    # Проверка на существование пользователя и инициализация, если необходимо
    if user_id not in feedback_data:
        feedback_data[user_id] = []

    # Создание нового отзыва с необходимыми полями
    feedback_entry = {
        'text': feedback_text,
        'rating': rating,
        'category': category,
        'responses': [],
        'helpfulness': 0,
        'date': datetime.now().isoformat(),  # Сохраняем дату отправки отзыва
        'status': 'на рассмотрении'  # Статус отзыва
    }
    feedback_data[user_id].append(feedback_entry)

    save_feedback_data(feedback_data)
    notify_admins(feedback_entry)  # Уведомляем администраторов о новом отзыве
    bot.send_message(message.chat.id, "Спасибо за ваш отзыв!")

@bot.message_handler(commands=['my_feedback'])
def show_my_feedback(message):
    feedback_data = load_feedback()
    user_id = str(message.from_user.id)

    if user_id not in feedback_data or not feedback_data[user_id]:
        bot.send_message(message.chat.id, "У вас нет оставленных отзывов.")
        return

    user_feedback = feedback_data[user_id]
    feedback_messages = [
        f"Отзыв: {entry['text']}, Оценка: {entry['rating']}, Категория: {entry['category']}, Полезность: {entry['helpfulness']}, Дата: {entry['date']}, Статус: {entry['status']}" 
        for entry in user_feedback
    ]
    bot.send_message(message.chat.id, "\n".join(feedback_messages))

@bot.message_handler(commands=['edit_feedback'])
def edit_feedback(message):
    feedback_data = load_feedback()
    user_id = str(message.from_user.id)

    if user_id not in feedback_data or not feedback_data[user_id]:
        bot.send_message(message.chat.id, "У вас нет оставленных отзывов для редактирования.")
        return

    feedback_messages = [f"{i+1}. {entry['text']} (Оценка: {entry['rating']})" for i, entry in enumerate(feedback_data[user_id])]
    bot.send_message(message.chat.id, "Выберите номер отзыва для редактирования:\n" + "\n".join(feedback_messages))
    bot.register_next_step_handler(message, lambda m: confirm_edit_feedback(m, feedback_data))

def confirm_edit_feedback(message, feedback_data):
    try:
        feedback_index = int(message.text) - 1
        user_id = str(message.from_user.id)

        if user_id in feedback_data and 0 <= feedback_index < len(feedback_data[user_id]):
            entry = feedback_data[user_id][feedback_index]
            bot.send_message(message.chat.id, f"Текущий текст отзыва: \"{entry['text']}\". Введите новый текст отзыва:")
            bot.register_next_step_handler(message, lambda m: save_edited_feedback(m, entry, feedback_index, feedback_data))
        else:
            bot.send_message(message.chat.id, "Неправильный номер отзыва.")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер отзыва.")

def save_edited_feedback(message, entry, feedback_index, feedback_data):
    new_text = message.text
    user_id = str(message.from_user.id)
    feedback_data[user_id][feedback_index]['text'] = new_text  # Обновляем текст отзыва
    save_feedback_data(feedback_data)
    bot.send_message(message.chat.id, "Ваш отзыв успешно обновлен!")

@bot.message_handler(commands=['view_feedback'])
def view_all_feedback(message):
    admins = load_admins()
    if message.from_user.id not in admins:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")
        return

    feedback_data = load_feedback()
    if not feedback_data:
        bot.send_message(message.chat.id, "Отзывов еще нет.")
        return

    all_feedback = []
    for user_id, user_feedback in feedback_data.items():
        for entry in user_feedback:
            all_feedback.append(f"Пользователь {user_id}: Отзыв: \"{entry['text']}\", Оценка: {entry['rating']}, Категория: {entry['category']}, Дата: {entry['date']}, Статус: {entry['status']}")

    bot.send_message(message.chat.id, "\n".join(all_feedback))

@bot.message_handler(commands=['delete_feedback'])
def delete_feedback(message):
    feedback_data = load_feedback()
    user_id = str(message.from_user.id)

    if user_id not in feedback_data or not feedback_data[user_id]:
        bot.send_message(message.chat.id, "У вас нет оставленных отзывов для удаления.")
        return

    feedback_messages = [f"{i+1}. {entry['text']}" for i, entry in enumerate(feedback_data[user_id])]
    bot.send_message(message.chat.id, "Выберите номер отзыва для удаления:\n" + "\n".join(feedback_messages))
    bot.register_next_step_handler(message, lambda m: confirm_delete_feedback(m, feedback_data))

def confirm_delete_feedback(message, feedback_data):
    try:
        feedback_index = int(message.text) - 1
        user_id = str(message.from_user.id)

        if user_id in feedback_data and 0 <= feedback_index < len(feedback_data[user_id]):
            del feedback_data[user_id][feedback_index]  # Удаляем отзыв
            save_feedback_data(feedback_data)
            bot.send_message(message.chat.id, "Ваш отзыв успешно удален!")
        else:
            bot.send_message(message.chat.id, "Неправильный номер отзыва.")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер отзыва.")


            
# (16) --------------- КОД ДЛЯ "ФУНКЦИЯ ДЛЯ ОБНОВЛЕНИЙ ОТ TG" ---------------

# Функция для обработки повторных попыток
def start_bot_with_retries(retries=10000000, delay=5):
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
while True:
    schedule.run_pending()
    time.sleep(60)  # Проверка расписания каждые 60 секунд