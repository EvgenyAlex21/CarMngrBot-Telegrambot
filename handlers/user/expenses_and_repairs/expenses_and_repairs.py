from core.imports import wraps, telebot, types, os, json, re, shutil, datetime, openpyxl, Workbook, load_workbook, Font, Alignment, get_column_letter, partial
from core.bot_instance import bot, BASE_DIR
from handlers.user.user_main_menu import return_to_menu
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha, check_function_state_decorator, track_usage, check_subscription
)

# --------------------------------------------------------- ТРАТЫ И РЕМОНТЫ ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Траты и ремонты")
@check_function_state_decorator('Траты и ремонты')
@track_usage('Траты и ремонты')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_expense_and_repairs(message, show_description=True):
    user_id = message.from_user.id

    expense_data = load_expense_data(user_id).get(str(user_id), {})
    repair_data = load_repair_data(user_id).get(str(user_id), {})

    description = (
        "ℹ️ *Краткая справка для трат и ремонтов*\n\n"
        "📌 *Выбор транспорта:*\n"
        "Выберите *ваш транспорт*, по которому хотите проводить операции "
        "В случае если транспорт не существует, то нужно добавить его через \"ваш транспорт\"\n\n"
        "📌 *Выбор категории записи:*\n"
        "Выбираете *категорию*, по которой у вас возникла трата/ремонт для записи. "
        "Изначально даются несколько системных категорий, которые можно расширить\n\n"
        "📌 *Ввод данных:*\n"
        "Вводите данные для трат/ремонтов - *название, описание, дата, сумма*\n\n"
        "📌 *Другие операции:*\n"
        "У вас есть возможность посмотреть или удалить свои записи по конкретному транспорту\n\n"
    )

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

    if show_description:
        bot.send_message(user_id, description, parse_mode='Markdown')

    bot.send_message(user_id, "Выберите действие из учета трат и ремонтов:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Вернуться в меню трат и ремонтов")
@check_function_state_decorator('Вернуться в меню трат и ремонтов')
@track_usage('Вернуться в меню трат и ремонтов')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_expense_and_repairs(message):
    handle_expense_and_repairs(message, show_description=False)

# --------------------------------------------------- ТРАТЫ И РЕМОНТЫ (ваш транспорт) ---------------------------------------------------

TRANSPORT_DIR = os.path.join(BASE_DIR, "data", "user", "expenses_and_repairs", "transport")
REPAIRS_DIR = os.path.join(BASE_DIR, "data", "user", "expenses_and_repairs", "repairs")
EXPENSES_DIR = os.path.join(BASE_DIR, "data", "user", "expenses_and_repairs", "expenses")

def ensure_transport_directory():
    os.makedirs(TRANSPORT_DIR, exist_ok=True)
    os.makedirs(os.path.join(REPAIRS_DIR, "excel"), exist_ok=True)
    os.makedirs(os.path.join(EXPENSES_DIR, "excel"), exist_ok=True)

ensure_transport_directory()

def migrate_legacy_local_data_dir():
    local_data_root = os.path.join(os.path.dirname(__file__), "data", "user", "expenses_and_repairs")
    if not os.path.exists(local_data_root):
        return
    try:
        print("[migrate] Обнаружен устаревший каталог данных в handlers. Переносим в корневой data/...")
        for sub in ("transport", "expenses", "repairs"):
            src = os.path.join(local_data_root, sub)
            dst = os.path.join(BASE_DIR, "data", "user", "expenses_and_repairs", sub)
            if not os.path.exists(src):
                continue
            os.makedirs(dst, exist_ok=True)
            for root, dirs, files in os.walk(src):
                rel = os.path.relpath(root, src)
                dst_root = os.path.join(dst, rel) if rel != "." else dst
                os.makedirs(dst_root, exist_ok=True)
                for fname in files:
                    try:
                        shutil.replace(os.path.join(root, fname), os.path.join(dst_root, fname))
                    except Exception:
                        pass
        try:
            shutil.rmtree(os.path.join(os.path.dirname(__file__), "data"))
        except Exception:
            pass
        print("[migrate] Перенос завершён.")
    except Exception:
        pass

migrate_legacy_local_data_dir()

class States:
    ADDING_TRANSPORT = 1
    CONFIRMING_DELETE = 2

user_transport = {}

def save_transport_data(user_id, transport_data):
    file_path = os.path.join(TRANSPORT_DIR, f"{user_id}_transport.json")
    data = {"user_id": int(user_id), "transport": {}}
    for index, item in enumerate(transport_data, start=1):
        data["transport"][str(index)] = item
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def load_transport_data(user_id):
    file_path = os.path.join(TRANSPORT_DIR, f"{user_id}_transport.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                if isinstance(data, dict) and "transport" in data:
                    return list(data["transport"].values())
                elif isinstance(data, list):
                    return data  
                else:
                    return []
        except json.JSONDecodeError as e:
            return []
        except Exception as e:
            return []
    return []

def reload_transport_data(user_id):
    user_id = str(user_id)
    try:
        user_transport[user_id] = load_transport_data(user_id)
    except Exception as e:
        user_transport[user_id] = []

def load_all_transport():
    user_transport.clear()
    for user_file in os.listdir(TRANSPORT_DIR):
        if user_file.endswith("_transport.json"):
            try:
                user_id = user_file.split("_")[0]
                user_transport[user_id] = load_transport_data(user_id)
            except Exception as e:
                pass

load_all_transport()

@bot.message_handler(func=lambda message: message.text == "Ваш транспорт")
@check_function_state_decorator('Ваш транспорт')
@track_usage('Ваш транспорт')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def manage_transport(message):
    user_id = str(message.chat.id)

    keyboard = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    keyboard.add("Добавить транспорт", "Посмотреть транспорт", "Удалить транспорт")
    keyboard.add("Изменить транспорт")
    keyboard.add("Вернуться в меню трат и ремонтов")
    keyboard.add("В главное меню")

    bot.send_message(user_id, "Выберите действие для транспорта:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "Вернуться в ваш транспорт")
@check_function_state_decorator('Вернуться в ваш транспорт')
@track_usage('Вернуться в ваш транспорт')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def return_to_transport_menu(message):
    manage_transport(message)

def create_transport_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(types.KeyboardButton("Вернуться в ваш транспорт"))
    markup.add(types.KeyboardButton("В главное меню"))
    return markup

# --------------------------------------------------- ТРАТЫ И РЕМОНТЫ (добавить трансорт) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Добавить транспорт")
@check_function_state_decorator('Добавить транспорт')
@track_usage('Добавить транспорт')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def add_transport(message):
    user_id = str(message.chat.id)
    bot.send_message(user_id, "Введите марку транспорта:", reply_markup=create_transport_keyboard())
    bot.register_next_step_handler(message, process_brand)

def format_brand_model(text):
    return " ".join(word.capitalize() for word in text.strip().split())

@text_only_handler
def process_brand(message):
    user_id = str(message.chat.id)

    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    brand = format_brand_model(message.text)
    bot.send_message(user_id, "Введите модель транспорта:", reply_markup=create_transport_keyboard())
    bot.register_next_step_handler(message, process_model, brand)

@text_only_handler
def process_model(message, brand):
    user_id = str(message.chat.id)

    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    model = format_brand_model(message.text)
    bot.send_message(user_id, "Введите год транспорта:", reply_markup=create_transport_keyboard())
    bot.register_next_step_handler(message, process_year, brand, model)

@text_only_handler
def process_year(message, brand, model):
    user_id = str(message.chat.id)

    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    try:
        year = int(message.text)
        if year < 1960 or year > 3000:
            raise ValueError("Год должен быть от 1960 г. до 3000 г.")
    except ValueError:
        bot.send_message(user_id, "Ошибка при введении года!\nПожалуйста, введите корректный год от 1960 г. до 3000 г.", reply_markup=create_transport_keyboard())
        bot.register_next_step_handler(message, process_year, brand, model)
        return

    bot.send_message(user_id, "Введите госномер:", reply_markup=create_transport_keyboard())
    bot.register_next_step_handler(message, process_license_plate, brand, model, year)

@text_only_handler
def process_license_plate(message, brand, model, year):
    user_id = str(message.chat.id)
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    if message.text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    license_plate = message.text.upper()
    pattern = r'^[АВЕКМНОРСТУХABEKMHOPCTYX]\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\d{2,3}$'
    if not re.match(pattern, license_plate):
        bot.send_message(user_id, "Ошибка при введении госномера!\nГосномер должен соответствовать формату госномеров РФ (А121АА21 или А121АА121)", reply_markup=create_transport_keyboard())
        bot.register_next_step_handler(message, process_license_plate, brand, model, year)
        return

    if any(t["license_plate"] == license_plate for t in user_transport.get(user_id, [])):
        bot.send_message(user_id, "Ошибка при введении госномера!\nТакой госномер уже существует", reply_markup=create_transport_keyboard())
        bot.register_next_step_handler(message, process_license_plate, brand, model, year)
        return

    if user_id not in user_transport:
        user_transport[user_id] = []

    user_transport[user_id].append({"brand": brand, "model": model, "year": year, "license_plate": license_plate})
    save_transport_data(user_id, user_transport[user_id])

    bot.send_message(user_id, f"✅ *Транспорт добавлен*\n\n*{brand} - {model} - {year} - {license_plate}*", parse_mode="Markdown", reply_markup=create_transport_keyboard())
    manage_transport(message)

# ----------------------------------------------- ТРАТЫ И РЕМОНТЫ (посмотреть транспорт) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Посмотреть транспорт")
@check_function_state_decorator('Посмотреть транспорт')
@track_usage('Посмотреть транспорт')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_transport(message):
    user_id = str(message.chat.id)
    
    reload_transport_data(user_id)
    
    if user_id in user_transport and user_transport[user_id]:
        transport_list = user_transport[user_id]
        response = "\n\n".join([
            f"№{index + 1}. {item['brand']} - {item['model']} - {item['year']} - `{item['license_plate']}`"
            for index, item in enumerate(transport_list)
        ])
        bot.send_message(
            user_id,
            f"🚙 *Ваш транспорт*\n\n{response}",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(user_id, "❌ У вас нет добавленного транспорта!")
    manage_transport(message)

# ----------------------------------------------- ТРАТЫ И РЕМОНТЫ (удалить транспорт) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Удалить транспорт")
@check_function_state_decorator('Удалить транспорт')
@track_usage('Удалить транспорт')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_transport(message):
    user_id = str(message.chat.id)
    
    reload_transport_data(user_id)
    
    if user_id in user_transport and user_transport[user_id]:
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        transport_list = user_transport[user_id]

        for index, item in enumerate(transport_list, start=1):
            keyboard.add(f"№{index}. {item['brand']} - {item['model']} - {item['year']} - {item['license_plate']}")

        keyboard.add("Удалить весь транспорт")
        keyboard.add("Вернуться в ваш транспорт")
        keyboard.add("В главное меню")

        bot.send_message(user_id, "Выберите транспорт для удаления:", reply_markup=keyboard)
        bot.register_next_step_handler(message, process_transport_selection_for_deletion)
    else:
        bot.send_message(user_id, "❌ У вас нет добавленного транспорта!")
        manage_transport(message)

def get_return_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add("Вернуться в ваш транспорт")
    markup.add("В главное меню")
    return markup

@text_only_handler
def process_transport_selection_for_deletion(message):
    user_id = str(message.chat.id)
    selected_transport = message.text.strip()

    if selected_transport == "В главное меню":
        return_to_menu(message)
        return
    if selected_transport == "Вернуться в ваш транспорт":
        manage_transport(message)
        return
    if selected_transport == "Удалить весь транспорт":
        delete_all_transports(message)
        return

    transport_list = user_transport.get(user_id, [])
    if transport_list:
        try:
            index = int(selected_transport.split('.')[0].replace("№", "").strip()) - 1
            if 0 <= index < len(transport_list):
                transport_to_delete = transport_list[index]
                bot.send_message(
                    user_id,
                    f"⚠️ *Вы точно хотите удалить данный транспорт?*\n\n{transport_to_delete['brand']} - {transport_to_delete['model']} - {transport_to_delete['year']} - {transport_to_delete['license_plate']}\n\n"
                    "Удаление транспорта приведет к удалению всех трат и ремонтов!\n\n"
                    "Пожалуйста, введите *да* для подтверждения или *нет* для отмены",
                    parse_mode="Markdown",
                    reply_markup=get_return_menu_keyboard()
                )
                bot.register_next_step_handler(message, partial(process_confirmation, transport_to_delete=transport_to_delete))
            else:
                raise ValueError("Индекс вне диапазона")
        except ValueError:
            bot.send_message(user_id, "Ошибка выбора!\nПожалуйста, выберите транспорт для удаления из списка")
            delete_transport(message)
    else:
        bot.send_message(user_id, "❌ У вас нет добавленного транспорта!")
        manage_transport(message)

def delete_expense_related_to_transport(user_id, transport, selected_transport=""):
    expense_data = load_expense_data(user_id)
    if str(user_id) in expense_data:
        updated_expense = [
            expense for expense in expense_data[str(user_id)].get('expense', [])
            if not (
                expense.get('transport', {}).get('brand') == transport.get('brand') and
                expense.get('transport', {}).get('model') == transport.get('model') and
                expense.get('transport', {}).get('license_plate') == transport.get('license_plate')
            )
        ]
        expense_data[str(user_id)]['expense'] = updated_expense
        if expense_data.get('selected_transport') == f"{transport['brand']} {transport['model']} ({transport['license_plate']})":
            expense_data['selected_transport'] = ""
        save_expense_data(user_id, expense_data, selected_transport)
    update_excel_file_expense(user_id)

def delete_repairs_related_to_transport(user_id, transport):
    repair_data = load_repair_data(user_id)
    if str(user_id) in repair_data:
        updated_repairs = [
            repair for repair in repair_data[str(user_id)].get("repairs", [])
            if not (
                repair.get('transport', {}).get('brand') == transport.get('brand') and
                repair.get('transport', {}).get('model') == transport.get('model') and
                repair.get('transport', {}).get('license_plate') == transport.get('license_plate')
            )
        ]
        repair_data[str(user_id)]["repairs"] = updated_repairs
        if repair_data.get('selected_transport') == f"{transport['brand']} {transport['model']} ({transport['license_plate']})":
            repair_data['selected_transport'] = ""
        save_repair_data(user_id, repair_data, selected_transport="")
    update_repairs_excel_file(user_id)

@text_only_handler
def process_confirmation(message, transport_to_delete):
    user_id = str(message.chat.id)
    confirmation = message.text.strip().lower()

    if confirmation == "в главное меню":
        return_to_menu(message)
        return
    if confirmation == "вернуться в ваш транспорт":
        manage_transport(message)
        return

    if confirmation == "да":
        if user_id in user_transport and transport_to_delete in user_transport[user_id]:
            user_transport[user_id].remove(transport_to_delete)
            delete_expense_related_to_transport(user_id, transport_to_delete)
            delete_repairs_related_to_transport(user_id, transport_to_delete)
            save_transport_data(user_id, user_transport[user_id])
            bot.send_message(user_id, "✅ Транспорт и связанные с ним траты и ремонты успешно удалены!", parse_mode="Markdown")
        else:
            bot.send_message(user_id, "⚠️ Ошибка удаления: транспорт не найден!", parse_mode="Markdown")
    elif confirmation == "нет":
        bot.send_message(user_id, "✅ Удаление отменено!", parse_mode="Markdown")
    else:
        bot.send_message(user_id, "Ошибка подтверждения!\nПожалуйста, введите *да* для подтверждения или *нет* для отмены", parse_mode="Markdown")
        bot.register_next_step_handler(message, partial(process_confirmation, transport_to_delete=transport_to_delete))
    manage_transport(message)

@bot.message_handler(func=lambda message: message.text == "Удалить весь транспорт")
@check_function_state_decorator('Удалить весь транспорт')
@track_usage('Удалить весь транспорт')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_all_transports(message):
    user_id = str(message.chat.id)
    if user_id in user_transport and user_transport[user_id]:
        bot.send_message(
            user_id,
            "⚠️ *Вы уверены, что хотите удалить весь транспорт?*\n\n"
            "Удаление транспорта приведет к удалению всех трат и ремонтов!\n\n"
            "Введите *да* для подтверждения или *нет* для отмены",
            parse_mode="Markdown",
            reply_markup=get_return_menu_keyboard()
        )
        bot.register_next_step_handler(message, process_delete_all_confirmation)
    else:
        bot.send_message(user_id, "❌ У вас нет добавленного транспорта!")
        manage_transport(message)

@text_only_handler
def process_delete_all_confirmation(message):
    user_id = str(message.chat.id)
    confirmation = message.text.strip().lower()

    if confirmation == "в главное меню":
        return_to_menu(message)
        return
    if confirmation == "вернуться в ваш транспорт":
        manage_transport(message)
        return

    if confirmation == "да":
        if user_id in user_transport and user_transport[user_id]:
            transports = user_transport[user_id]
            user_transport[user_id] = []
            for transport in transports:
                delete_expense_related_to_transport(user_id, transport)
                delete_repairs_related_to_transport(user_id, transport)
            save_transport_data(user_id, user_transport[user_id])
            bot.send_message(user_id, "✅ Весь транспорт и связанные с ним траты и ремонты успешно удалены!", parse_mode="Markdown")
        else:
            bot.send_message(user_id, "❌ У вас нет добавленного транспорта!", parse_mode="Markdown")
    elif confirmation == "нет":
        bot.send_message(user_id, "✅ Удаление отменено!", parse_mode="Markdown")
    else:
        bot.send_message(user_id, "Ошибка подтверждения!\nПожалуйста, введите *да* для подтверждения или *нет* для отмены", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_delete_all_confirmation)
    manage_transport(message)

# ----------------------------------------------- ТРАТЫ И РЕМОНТЫ (изменить транспорт) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Изменить транспорт")
@check_function_state_decorator('Изменить транспорт')
@track_usage('Изменить транспорт')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def edit_transport(message):
    user_id = str(message.chat.id)
    
    reload_transport_data(user_id)
    
    transports = user_transport.get(user_id, [])
    if not transports:
        bot.send_message(user_id, "❌ У вас нет добавленного транспорта!", reply_markup=create_transport_keyboard())
        manage_transport(message)
        return

    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for index, transport in enumerate(transports, start=1):
        keyboard.add(f"№{index}. {transport['brand']} - {transport['model']} - {transport['year']} - {transport['license_plate']}")
    keyboard.add("Вернуться в ваш транспорт")
    keyboard.add("В главное меню")
    bot.send_message(user_id, "Выберите транспорт для изменения:", reply_markup=keyboard)
    bot.register_next_step_handler(message, process_transport_selection_for_edit)

@text_only_handler
def process_transport_selection_for_edit(message):
    user_id = str(message.chat.id)
    selected_transport_text = message.text.strip()

    if selected_transport_text == "В главное меню":
        return_to_menu(message)
        return
    if selected_transport_text == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    transports = user_transport.get(user_id, [])
    try:
        index = int(selected_transport_text.split('.')[0].replace("№", "").strip()) - 1
        if 0 <= index < len(transports):
            selected_transport = transports[index]
            keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            keyboard.add("Марка", "Модель", "Год", "Госномер")
            keyboard.add("Вернуться в ваш транспорт")
            keyboard.add("В главное меню")
            bot.send_message(user_id, "Что вы хотите изменить?", reply_markup=keyboard)
            bot.register_next_step_handler(message, partial(process_field_selection, selected_transport=selected_transport))
        else:
            raise ValueError("Индекс вне диапазона")
    except ValueError:
        bot.send_message(user_id, "Неверный выбор транспорта!\nПожалуйста, выберите номер из списка", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_transport_selection_for_edit)

@text_only_handler
def process_field_selection(message, selected_transport):
    user_id = str(message.chat.id)
    field = message.text.strip()

    if field == "В главное меню":
        return_to_menu(message)
        return
    if field == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    if field not in ["Марка", "Модель", "Год", "Госномер"]:
        bot.send_message(user_id, "Неверное поле!\nПожалуйста, выберите из предложенных", parse_mode="Markdown")
        keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        keyboard.add("Марка", "Модель", "Год", "Госномер")
        keyboard.add("Вернуться в ваш транспорт")
        keyboard.add("В главное меню")
        bot.register_next_step_handler(message, partial(process_field_selection, selected_transport=selected_transport))
        return

    current = {
        "Марка": selected_transport['brand'],
        "Модель": selected_transport['model'],
        "Год": str(selected_transport['year']),
        "Госномер": selected_transport['license_plate']
    }
    bot.send_message(user_id, f'Текущий(-ая) *{field.lower()}* транспорта - {current[field]}\n\nВведите новую информацию:', reply_markup=create_transport_keyboard(), parse_mode="Markdown")
    bot.register_next_step_handler(message, partial(process_new_value, selected_transport=selected_transport, field=field))

@text_only_handler
def process_new_value(message, selected_transport, field):
    user_id = str(message.chat.id)
    new_value = message.text.strip()

    if new_value == "В главное меню":
        return_to_menu(message)
        return
    if new_value == "Вернуться в ваш транспорт":
        manage_transport(message)
        return

    if field == "Год":
        try:
            new_value = int(new_value)
            if new_value < 1960 or new_value > 3000:
                raise ValueError
        except ValueError:
            bot.send_message(user_id, "Ошибка при введении года!\nПожалуйста, введите корректный год от 1960 г. до 3000 г.", reply_markup=create_transport_keyboard())
            bot.register_next_step_handler(message, partial(process_new_value, selected_transport=selected_transport, field=field))
            return
    elif field == "Госномер":
        pattern = r'^[АВЕКМНОРСТУХABEKMHOPCTYX]\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\d{2,3}$'
        if not re.match(pattern, new_value.upper()):
            bot.send_message(user_id, "Ошибка при введении госномера!\nГосномер должен соответствовать формату госномеров РФ (А121АА21 или А121АА121)", reply_markup=create_transport_keyboard())
            bot.register_next_step_handler(message, partial(process_new_value, selected_transport=selected_transport, field=field))
            return
        if any(t['license_plate'] == new_value.upper() and t != selected_transport for t in user_transport.get(user_id, [])):
            bot.send_message(user_id, "Ошибка при введении госномера!\nТакой госномер уже существует", reply_markup=create_transport_keyboard())
            bot.register_next_step_handler(message, partial(process_new_value, selected_transport=selected_transport, field=field))
            return
        new_value = new_value.upper()
    elif field in ["Марка", "Модель"]:
        new_value = format_brand_model(new_value)

    old_transport = selected_transport.copy()
    field_key = "license_plate" if field == "Госномер" else field.lower()
    selected_transport[field_key] = new_value
    save_transport_data(user_id, user_transport.get(user_id, []))

    update_related_data(user_id, old_transport, selected_transport, field_key, new_value)
    update_excel_files_after_transport_change(user_id, old_transport, selected_transport)

    bot.send_message(user_id, f'✅ *{field}* транспорта изменен(-а)!', parse_mode="Markdown", reply_markup=create_transport_keyboard())
    manage_transport(message)

def update_related_data(user_id, old_transport, new_transport, field_key, new_value):
    updated = False

    expense_data = load_expense_data(user_id)
    if str(user_id) in expense_data and (expense_data[str(user_id)].get('expense') or expense_data.get('selected_transport')):
        old_selected = f"{old_transport['brand']} {old_transport['model']} ({old_transport['license_plate']})"
        new_selected = f"{new_transport['brand']} {new_transport['model']} ({new_transport['license_plate']})"
        if expense_data.get('selected_transport') == old_selected:
            expense_data['selected_transport'] = new_selected
        for expense in expense_data[str(user_id)].get('expense', []):
            transport_data = expense.get('transport', {})
            if (
                transport_data.get('brand') == old_transport['brand'] and
                transport_data.get('model') == old_transport['model'] and
                transport_data.get('license_plate') == old_transport['license_plate']
            ):
                transport_data[field_key] = new_value
        save_expense_data(user_id, expense_data, new_selected)
        updated = True

    repair_data = load_repair_data(user_id)
    if str(user_id) in repair_data and (repair_data[str(user_id)].get('repairs') or repair_data.get('selected_transport')):
        old_selected = f"{old_transport['brand']} {old_transport['model']} ({old_transport['license_plate']})"
        new_selected = f"{new_transport['brand']} {new_transport['model']} ({new_transport['license_plate']})"
        if repair_data.get('selected_transport') == old_selected:
            repair_data['selected_transport'] = new_selected
        for repair in repair_data[str(user_id)].get('repairs', []):
            transport_data = repair.get('transport', {})
            if (
                transport_data.get('brand') == old_transport['brand'] and
                transport_data.get('model') == old_transport['model'] and
                transport_data.get('license_plate') == old_transport['license_plate']
            ):
                transport_data[field_key] = new_value
        save_repair_data(user_id, repair_data, new_selected)
        updated = True

    if not updated:
        pass

def update_excel_files_after_transport_change(user_id, old_transport, new_transport):
    expense_excel_path = os.path.join(EXPENSES_DIR, "excel", f"{user_id}_expenses.xlsx")
    expense_data = load_expense_data(user_id)
    expenses = expense_data.get(str(user_id), {}).get('expense', [])

    if expenses:
        try:
            if os.path.exists(expense_excel_path):
                workbook = load_workbook(expense_excel_path)
            else:
                workbook = Workbook()
                workbook.remove(workbook.active)

            if "Summary" not in workbook.sheetnames:
                summary_sheet = workbook.create_sheet("Summary")
            else:
                summary_sheet = workbook["Summary"]
                summary_sheet.delete_rows(2, summary_sheet.max_row)

            headers = ["Транспорт", "Категория", "Название", "Дата", "Сумма", "Описание"]
            if summary_sheet.max_row == 0:
                summary_sheet.append(headers)
                for cell in summary_sheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal="center")

            for expense in expenses:
                transport = expense.get('transport', {})
                row_data = [
                    f"{transport.get('brand', '')} {transport.get('model', '')} ({transport.get('license_plate', '')})",
                    expense.get("category", ""),
                    expense.get("name", ""),
                    expense.get("date", ""),
                    float(expense.get("amount", 0)),
                    expense.get("description", ""),
                ]
                summary_sheet.append(row_data)

            unique_transports = set(
                (exp.get("transport", {}).get("brand", ""), exp.get("transport", {}).get("model", ""), exp.get("transport", {}).get("license_plate", ""))
                for exp in expenses
            )

            for sheet_name in workbook.sheetnames[:]:
                if sheet_name == "Summary":
                    continue
                parts = sheet_name.split("_")
                if len(parts) != 3 or (parts[0], parts[1], parts[2]) not in unique_transports:
                    del workbook[sheet_name]

            for brand, model, license_plate in unique_transports:
                sheet_name = f"{brand}_{model}_{license_plate}"[:31]
                if sheet_name not in workbook.sheetnames:
                    transport_sheet = workbook.create_sheet(sheet_name)
                    transport_sheet.append(headers)
                    for cell in transport_sheet[1]:
                        cell.font = Font(bold=True)
                        cell.alignment = Alignment(horizontal="center")
                else:
                    transport_sheet = workbook[sheet_name]
                    transport_sheet.delete_rows(2, transport_sheet.max_row)

                for expense in expenses:
                    if (
                        expense.get("transport", {}).get("brand", "") == brand and
                        expense.get("transport", {}).get("model", "") == model and
                        expense.get("transport", {}).get("license_plate", "") == license_plate
                    ):
                        row_data = [
                            f"{brand} {model} ({license_plate})",
                            expense.get("category", ""),
                            expense.get("name", ""),
                            expense.get("date", ""),
                            float(expense.get("amount", 0)),
                            expense.get("description", ""),
                        ]
                        transport_sheet.append(row_data)

            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                for col in sheet.columns:
                    max_length = max(len(str(cell.value)) for cell in col if cell.value)
                    sheet.column_dimensions[get_column_letter(col[0].column)].width = max_length + 2

            workbook.save(expense_excel_path)
            workbook.close()
        except Exception as e:
            bot.send_message(user_id, "❌ Ошибка при обновлении данных трат в Excel!", parse_mode="Markdown")
    else:
        if os.path.exists(expense_excel_path):
            os.remove(expense_excel_path)

    repair_excel_path = os.path.join(REPAIRS_DIR, "excel", f"{user_id}_repairs.xlsx")
    repair_data = load_repair_data(user_id)
    repairs = repair_data.get(str(user_id), {}).get('repairs', [])

    if repairs:
        try:
            if os.path.exists(repair_excel_path):
                workbook = load_workbook(repair_excel_path)
            else:
                workbook = Workbook()
                workbook.remove(workbook.active)

            if "Summary" not in workbook.sheetnames:
                summary_sheet = workbook.create_sheet("Summary")
            else:
                summary_sheet = workbook["Summary"]
                summary_sheet.delete_rows(2, summary_sheet.max_row)

            headers = ["Транспорт", "Категория", "Название", "Дата", "Сумма", "Описание"]
            if summary_sheet.max_row == 0:
                summary_sheet.append(headers)
                for cell in summary_sheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal="center")

            for repair in repairs:
                transport = repair.get('transport', {})
                row_data = [
                    f"{transport.get('brand', '')} {transport.get('model', '')} ({transport.get('license_plate', '')})",
                    repair.get("category", ""),
                    repair.get("name", ""),
                    repair.get("date", ""),
                    float(repair.get("amount", 0)),
                    repair.get("description", ""),
                ]
                summary_sheet.append(row_data)

            unique_transports = set(
                (rep.get("transport", {}).get("brand", ""), rep.get("transport", {}).get("model", ""), rep.get("transport", {}).get("license_plate", ""))
                for rep in repairs
            )

            for sheet_name in workbook.sheetnames[:]:
                if sheet_name == "Summary":
                    continue
                parts = sheet_name.split("_")
                if len(parts) != 3 or (parts[0], parts[1], parts[2]) not in unique_transports:
                    del workbook[sheet_name]

            for brand, model, license_plate in unique_transports:
                sheet_name = f"{brand}_{model}_{license_plate}"[:31]
                if sheet_name not in workbook.sheetnames:
                    transport_sheet = workbook.create_sheet(sheet_name)
                    transport_sheet.append(headers)
                    for cell in transport_sheet[1]:
                        cell.font = Font(bold=True)
                        cell.alignment = Alignment(horizontal="center")
                else:
                    transport_sheet = workbook[sheet_name]
                    transport_sheet.delete_rows(2, transport_sheet.max_row)

                for repair in repairs:
                    if (
                        repair.get("transport", {}).get("brand", "") == brand and
                        repair.get("transport", {}).get("model", "") == model and
                        repair.get("transport", {}).get("license_plate", "") == license_plate
                    ):
                        row_data = [
                            f"{brand} {model} ({license_plate})",
                            repair.get("category", ""),
                            repair.get("name", ""),
                            repair.get("date", ""),
                            float(repair.get("amount", 0)),
                            repair.get("description", ""),
                        ]
                        transport_sheet.append(row_data)

            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                for col in sheet.columns:
                    max_length = max(len(str(cell.value)) for cell in col if cell.value)
                    sheet.column_dimensions[get_column_letter(col[0].column)].width = max_length + 2

            workbook.save(repair_excel_path)
            workbook.close()
        except Exception as e:
            bot.send_message(user_id, "❌ Ошибка при обновлении данных ремонтов в Excel!", parse_mode="Markdown")
    else:
        if os.path.exists(repair_excel_path):
            os.remove(repair_excel_path)

# ----------------------------------------------- ТРАТЫ И РЕМОНТЫ (траты) ---------------------------------------------------

DATA_BASE_DIR = os.path.join(BASE_DIR, "data", "user", "expenses_and_repairs")
EXPENSE_DIR = os.path.join(DATA_BASE_DIR, "expenses")

def ensure_directories():
    os.makedirs(EXPENSE_DIR, exist_ok=True)

ensure_directories()

user_transport = {}

def save_expense_data(user_id, user_data, selected_transport=None):
    ensure_directories() 

    file_path = os.path.join(EXPENSE_DIR, f"{user_id}_expenses.json")

    current_data = load_expense_data(user_id)

    user_data["user_categories"] = user_data.get("user_categories", current_data.get("user_categories", []))
    user_data["expense"] = current_data.get("expense", [])

    if selected_transport is not None:
        user_data["selected_transport"] = selected_transport

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(user_data, file, ensure_ascii=False, indent=4)

def load_expense_data(user_id):
    ensure_directories() 

    file_path = os.path.join(EXPENSE_DIR, f"{user_id}_expenses.json")

    if not os.path.exists(file_path):
        return {"user_categories": [], "selected_transport": "", "expense": []}

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, ValueError) as e:
        data = {"user_categories": [], "selected_transport": "", "expense": []}

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
    if new_category not in data["user_categories"]:
        data["user_categories"].append(new_category)

    save_expense_data(user_id, data)

def remove_user_category(user_id, category_to_remove, selected_transport=""):
    data = load_expense_data(user_id)
    if "user_categories" in data and category_to_remove in data["user_categories"]:
        data["user_categories"].remove(category_to_remove)
        save_expense_data(user_id, data, selected_transport)

def get_user_transport_keyboard(user_id):
    transports = load_transport_data(user_id) 
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    for i in range(0, len(transports), 2):
        transport_buttons = [
            types.KeyboardButton(f"{transport['brand']} {transport['model']} ({transport['license_plate']})")
            for transport in transports[i:i+2]
        ]
        markup.row(*transport_buttons)

    markup.add(types.KeyboardButton("Добавить транспорт"))
    return markup

# ----------------------------------------------- ТРАТЫ И РЕМОНТЫ (записать трату) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Записать трату")
@check_function_state_decorator('Записать трату')
@track_usage('Записать трату')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def record_expense(message):
    user_id = str(message.from_user.id)

    transports = load_transport_data(user_id) 

    if not transports:
        bot.send_message(user_id, "⚠️ У вас нет сохраненного транспорта!\nХотите добавить транспорт?", reply_markup=create_transport_options_markup(), parse_mode="Markdown")
        bot.register_next_step_handler(message, ask_add_transport)
        return

    markup = get_user_transport_keyboard(user_id)
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))

    bot.send_message(user_id, "Выберите транспорт для записи траты:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, handle_transport_selection_for_expense)
    
@text_only_handler
def handle_transport_selection_for_expense(message):
    user_id = str(message.from_user.id)  
    selected_transport = message.text.strip()

    if selected_transport == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
        return
    elif selected_transport == "В главное меню":
        return_to_menu(message)
        return
    elif selected_transport == "Добавить транспорт":
        add_transport(message)
        return

    transports = load_transport_data(user_id)
    selected_brand, selected_model, selected_license_plate = None, None, None

    for transport in transports:
        formatted_transport = f"{transport['brand']} {transport['model']} ({transport['license_plate']})"
        if formatted_transport == selected_transport:
            selected_brand = transport['brand']
            selected_model = transport['model']
            selected_license_plate = transport['license_plate']
            break
    else:
        markup = get_user_transport_keyboard(user_id)
        markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(user_id, "Не удалось найти указанный транспорт!\nПожалуйста, выберите снова", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, handle_transport_selection_for_expense)
        return

    process_category_selection(user_id, selected_brand, selected_model, selected_license_plate)

def process_category_selection(user_id, brand, model, license_plate, prompt_message=None):
    categories = get_user_categories(user_id)

    system_emoji = "🔹"
    user_emoji = "🔸"

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

@text_only_handler
def get_expense_category(message, brand, model, license_plate):
    user_id = message.from_user.id

    selected_index = message.text.strip()

    if selected_index == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
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
            bot.send_message(user_id, "Неверный номер категории!\nПопробуйте снова")
            bot.register_next_step_handler(message, get_expense_category, brand, model, license_plate)
    else:
        bot.send_message(user_id, "Пожалуйста, введите номер категории!")
        bot.register_next_step_handler(message, get_expense_category, brand, model, license_plate)

@text_only_handler
def add_new_category(message, brand, model, license_plate):
    user_id = message.from_user.id

    new_category = message.text.strip().lower()

    if new_category in ["вернуться в меню трат и ремонтов", "в главное меню"]:
        if new_category == "вернуться в меню трат и ремонтов":
            return_to_expense_and_repairs(message)
        else:
            return_to_menu(message)
        return

    if not new_category:
        bot.send_message(user_id, "Название категории не может быть пустым!\nПожалуйста, введите корректное название")
        bot.register_next_step_handler(message, add_new_category, brand, model, license_plate)
        return

    user_categories = [cat.lower() for cat in get_user_categories(user_id)]
    if new_category in user_categories:
        bot.send_message(user_id, "Такая категория уже существует!\nПожалуйста, введите уникальное название")
        bot.register_next_step_handler(message, add_new_category, brand, model, license_plate)
        return

    add_user_category(user_id, new_category)
    bot.send_message(user_id, f"✅ Категория *{new_category}* успешно добавлена!", parse_mode="Markdown")
    process_category_selection(user_id, brand, model, license_plate)

@bot.message_handler(func=lambda message: message.text == "Удалить категорию")
@check_function_state_decorator('Удалить категорию')
@track_usage('Удалить категорию')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_category_removal(message, brand=None, model=None, license_plate=None):
    user_id = message.from_user.id
    categories = get_user_categories(user_id)

    system_emoji = "🔹"
    user_emoji = "🔸"

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

@text_only_handler
def remove_selected_category(message, brand, model, license_plate):
    user_id = message.from_user.id

    selected_index = message.text.strip()

    if selected_index == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
        return
    elif selected_index == "В главное меню":
        return_to_menu(message)
        return

    if selected_index == '0':
        bot.send_message(user_id, "✅ Удаление категории отменено!")
        return process_category_selection(user_id, brand, model, license_plate)

    if selected_index.isdigit():
        index = int(selected_index) - 1
        categories = get_user_categories(user_id)
        default_categories = ["без категории", "азс", "мойка", "парковка", "платная дорога", "страховка", "штрафы"]

        if 0 <= index < len(categories):
            category_to_remove = categories[index].lower()
            if category_to_remove in default_categories:
                bot.send_message(user_id, f"⚠️ Нельзя удалить системную категорию *{categories[index]}*!", parse_mode="Markdown")
                return bot.register_next_step_handler(message, remove_selected_category, brand, model, license_plate)

            remove_user_category(user_id, categories[index]) 
            bot.send_message(user_id, f"✅ Категория *{categories[index]}* успешно удалена!", parse_mode="Markdown")
        else:
            bot.send_message(user_id, "Неверный номер категории!\nПопробуйте снова")
            return bot.register_next_step_handler(message, remove_selected_category, brand, model, license_plate)
    else:
        bot.send_message(user_id, "Пожалуйста, введите номер категории!")
        return bot.register_next_step_handler(message, remove_selected_category, brand, model, license_plate)

    return process_category_selection(user_id, brand, model, license_plate)

@text_only_handler
def proceed_to_expense_name(message, selected_category, brand, model, license_plate):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите название траты:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expense_name, selected_category, brand, model, license_plate)

@text_only_handler
def get_expense_name(message, selected_category, brand, model, license_plate):
    user_id = message.from_user.id

    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_expense_and_repairs(message)
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

@text_only_handler
def get_expense_description(message, selected_category, expense_name, brand, model, license_plate):
    user_id = message.from_user.id

    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_expense_and_repairs(message)
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

@text_only_handler
def get_expense_date(message, selected_category, expense_name, description, brand, model, license_plate):
    user_id = message.from_user.id

    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_expense_and_repairs(message)
        else:
            return_to_menu(message)
        return

    expense_date = message.text

    if re.match(r"^\d{2}\.\d{2}\.\d{4}$", expense_date):
        try:
            day, month, year = map(int, expense_date.split('.'))
            if 1 <= month <= 12 and 1 <= day <= 31 and 2000 <= year <= 3000:
                datetime.strptime(expense_date, "%d.%m.%Y")
            else:
                raise ValueError
        except ValueError:
            bot.send_message(user_id, "Неверный формат даты или значения!\nПожалуйста, введите дату в формате ДД.ММ.ГГГГ")
            bot.register_next_step_handler(message, get_expense_date, selected_category, expense_name, description, brand, model, license_plate)
            return
    else:
        bot.send_message(user_id, "Неверный формат даты!\nПопробуйте еще раз в формате ДД.ММ.ГГГГ")
        bot.register_next_step_handler(message, get_expense_date, selected_category, expense_name, description, brand, model, license_plate)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Введите сумму траты:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expense_amount, selected_category, expense_name, description, expense_date, brand, model, license_plate)

def is_numeric(s):
    if s is not None:
        try:
            float(s)
            return True
        except ValueError:
            return False
    return False

@text_only_handler
def get_expense_amount(message, selected_category, expense_name, description, expense_date, brand, model, license_plate):
    user_id = message.from_user.id

    expense_amount = message.text.replace(",", ".")
    if not is_numeric(expense_amount):
        bot.send_message(user_id, "Пожалуйста, введите сумму траты в числовом формате!")
        bot.register_next_step_handler(message, get_expense_amount, selected_category, expense_name, description, expense_date, brand, model, license_plate)
        return

    data = load_expense_data(user_id)
    if str(user_id) not in data:
        data[str(user_id)] = {"expense": []}

    selected_transport = f"{brand} {model} {license_plate}"
    expense = data[str(user_id)].get("expense", [])
    new_expense = {
        "category": selected_category,
        "name": expense_name,
        "date": expense_date,
        "amount": expense_amount,
        "description": description,
        "transport": {"brand": brand, "model": model, "license_plate": license_plate}
    }
    expense.append(new_expense)
    data[str(user_id)]["expense"] = expense
    save_expense_data(user_id, data, selected_transport)

    save_expense_to_excel(user_id, new_expense)

    bot.send_message(user_id, "✅ Трата успешно записана!")
    return_to_expense_and_repairs(message)

def save_expense_to_excel(user_id, expense):
    excel_path = os.path.join(BASE_DIR, "data", "user", "expenses_and_repairs", "expenses", "excel", f"{user_id}_expenses.xlsx")

    directory = os.path.dirname(excel_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    try:
        if os.path.exists(excel_path):
            workbook = load_workbook(excel_path)
        else:
            workbook = Workbook()
            workbook.remove(workbook.active)

        summary_sheet = workbook["Summary"] if "Summary" in workbook.sheetnames else workbook.create_sheet("Summary")

        transport_sheet_name = f"{expense['transport']['brand']}_{expense['transport']['model']}_{expense['transport']['license_plate']}"
        transport_sheet = workbook[transport_sheet_name] if transport_sheet_name in workbook.sheetnames else workbook.create_sheet(transport_sheet_name)

        headers = ["Транспорт", "Категория", "Название", "Дата", "Сумма", "Описание"]

        def setup_sheet(sheet):
            if sheet.max_row == 1:
                sheet.append(headers)
                for cell in sheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal="center")

        for sheet in [summary_sheet, transport_sheet]:
            setup_sheet(sheet)
            row_data = [
                f"{expense['transport']['brand']} {expense['transport']['model']} {expense['transport']['license_plate']}",
                expense["category"],
                expense["name"],
                expense["date"],
                float(expense["amount"]),
                expense["description"],
            ]
            sheet.append(row_data)

        for sheet in [summary_sheet, transport_sheet]:
            for col in sheet.columns:
                max_length = max(len(str(cell.value)) for cell in col)
                sheet.column_dimensions[get_column_letter(col[0].column)].width = max_length + 2

        workbook.save(excel_path)
    except Exception as e:
        raise

# ----------------------------------------------- ТРАТЫ И РЕМОНТЫ (посмотреть траты) ---------------------------------------------------

selected_transport_dict = {}

MAX_MESSAGE_LENGTH = 4096

def send_message_with_split(user_id, message_text, parse_mode=None):

    MAX_MESSAGE_LENGTH = 4096
    try:
        if len(message_text) <= MAX_MESSAGE_LENGTH:
            bot.send_message(user_id, message_text, parse_mode=parse_mode)
        else:
            message_parts = [message_text[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message_text), MAX_MESSAGE_LENGTH)]
            for part in message_parts:
                bot.send_message(user_id, part, parse_mode=parse_mode)
    except Exception as e:
        bot.send_message(user_id, "Произошла ошибка при отправке сообщения!\nПопробуйте позже", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Посмотреть траты")
@check_function_state_decorator('Посмотреть траты')
@track_usage('Посмотреть траты')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_expense(message):
    user_id = str(message.from_user.id)

    transport_list = load_transport_data(user_id)

    if not transport_list:
        bot.send_message(user_id, "⚠️ У вас нет сохраненного транспорта!\nХотите добавить транспорт?", reply_markup=create_transport_options_markup())
        bot.register_next_step_handler(message, ask_add_transport)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    for i in range(0, len(transport_list), 2):
        transport_buttons = []
        for j in range(i, min(i + 2, len(transport_list))):
            transport = transport_list[j]
            transport_name = f"{transport['brand']} {transport['model']} ({transport['license_plate']})"
            transport_buttons.append(types.KeyboardButton(transport_name))

        markup.add(*transport_buttons)

    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main)

    bot.send_message(user_id, "Выберите ваш транспорт:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection)

def ask_add_transport(message):
    user_id = str(message.from_user.id)

    if message.text == "Добавить транспорт":
        add_transport(message)
        return
    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
        return
    if message.text == "В главное меню":
        return_to_menu(message)
        return
    else:
        bot.send_message(user_id, "Пожалуйста, выберите вариант!", reply_markup=create_transport_options_markup())
        bot.register_next_step_handler(message, ask_add_transport)

def create_transport_options_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_add_transport = types.KeyboardButton("Добавить транспорт")
    item_cancel = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_add_transport)
    markup.add(item_cancel)
    markup.add(item_main)
    return markup

def filter_expense_by_transport(user_id, expense):
    selected_transport = selected_transport_dict.get(user_id)
    if not selected_transport:
        return expense

    filtered_expense = []
    for exp in expense:
        transport = exp.get('transport', {})
        if not all(k in transport for k in ['brand', 'model', 'license_plate']):
            continue
        if f"{transport['brand']} {transport['model']} ({transport['license_plate']})" == selected_transport:
            filtered_expense.append(exp)
    return filtered_expense

@text_only_handler
def handle_transport_selection(message):
    user_id = message.from_user.id
    selected_transport = message.text

    if selected_transport == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
        return

    if selected_transport == "В главное меню":
        return_to_menu(message)
        return

    selected_transport_dict[user_id] = selected_transport

    bot.send_message(user_id, f"Показываю траты для транспорта: *{selected_transport}*", parse_mode="Markdown")
    send_menu1(user_id)

def send_menu1(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Траты (по категориям)")
    item2 = types.KeyboardButton("Траты (месяц)")
    item3 = types.KeyboardButton("Траты (год)")
    item4 = types.KeyboardButton("Траты (все время)")
    item_excel = types.KeyboardButton("Посмотреть траты в EXCEL")
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main_menu = types.KeyboardButton("В главное меню")
    markup.add(item1, item2)
    markup.add(item3, item4)
    markup.add(item_excel)
    markup.add(item_return)
    markup.add(item_main_menu)

    bot.send_message(user_id, "Выберите вариант просмотра трат:", reply_markup=markup)

# ----------------------------------------------- ТРАТЫ И РЕМОНТЫ (посмотреть траты в excel) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Посмотреть траты в EXCEL")
@check_function_state_decorator('Посмотреть траты в EXCEL')
@track_usage('Посмотреть траты в EXCEL')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_expense_excel(message):
    user_id = str(message.from_user.id)

    excel_path = os.path.join(BASE_DIR, "data", "user", "expenses_and_repairs", "expenses", "excel", f"{user_id}_expenses.xlsx")

    try:
        if not os.path.exists(excel_path):
            bot.send_message(user_id, "❌ Файл с вашими тратами не найден!")
            return_to_expense_and_repairs(message)
            return
        with open(excel_path, 'rb') as excel_file:
            bot.send_document(user_id, excel_file)
    except Exception as e:
        bot.send_message(user_id, "Произошла ошибка при отправке файла!\nПопробуйте позже")
        return_to_expense_and_repairs(message)

# ----------------------------------------------- ТРАТЫ И РЕМОНТЫ (траты по категориям) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Траты (по категориям)")
@check_function_state_decorator('Траты (по категориям)')
@track_usage('Траты (по категориям)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_expense_by_category(message):
    user_id = str(message.from_user.id)
    user_data = load_expense_data(user_id)
    expense = user_data.get(str(user_id), {}).get("expense", [])

    expense = filter_expense_by_transport(user_id, expense)

    categories = set(exp.get('category', 'Без категории') for exp in expense)
    if not categories:
        bot.send_message(user_id, "❌ Нет доступных категорий для выбранного транспорта!", parse_mode="Markdown")
        send_menu1(user_id)
        return

    category_buttons = [types.KeyboardButton(category) for category in categories]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*category_buttons)
    item_return_to_expense = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_return_to_main = types.KeyboardButton("В главное меню")
    markup.add(item_return_to_expense)
    markup.add(item_return_to_main)

    bot.send_message(user_id, "Выберите категорию для просмотра трат:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, handle_category_selection)

@text_only_handler
def handle_category_selection(message):
    user_id = str(message.from_user.id)
    selected_category = message.text

    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    user_data = load_expense_data(user_id)
    expense = user_data.get(str(user_id), {}).get("expense", [])

    expense = filter_expense_by_transport(user_id, expense)

    if selected_category not in {exp.get('category', 'Без категории') for exp in expense}:
        bot.send_message(user_id, "Выбранная категория не найдена!\nПожалуйста, выберите корректную категорию", parse_mode="Markdown")
        view_expense_by_category(message)
        return

    category_expense = [exp for exp in expense if exp.get('category', 'Без категории') == selected_category]

    total_expense = 0
    expense_details = []

    for index, exp in enumerate(category_expense, start=1):
        expense_name = exp.get("name", "Без названия")
        expense_date = exp.get("date", "")
        amount = float(exp.get("amount", 0))
        total_expense += amount

        expense_details.append(
            f"💸 *№{index}*\n\n"
            f"📂 *Категория:* {selected_category}\n"
            f"📌 *Название:* {expense_name}\n"
            f"📅 *Дата:* {expense_date}\n"
            f"💰 *Сумма:* {amount} руб.\n"
            f"📝 *Описание:* {exp.get('description', 'Без описания')}\n"
        )

    if expense_details:
        message_text = f"Траты в категории *{selected_category.lower()}*:\n\n" + "\n\n".join(expense_details)
        send_message_with_split(user_id, message_text, parse_mode="Markdown")
        bot.send_message(user_id, f"Итоговая сумма трат в категории *{selected_category.lower()}*: *{total_expense}* руб.", parse_mode="Markdown")
    else:
        bot.send_message(user_id, f"❌ В категории *{selected_category.lower()}* трат не найдено!", parse_mode="Markdown")

    send_menu1(user_id)

# ----------------------------------------------- ТРАТЫ И РЕМОНТЫ (траты по месяцу) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Траты (месяц)")
@check_function_state_decorator('Траты (месяц)')
@track_usage('Траты (месяц)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_expense_by_month(message):
    user_id = str(message.from_user.id)  

    transports = load_transport_data(user_id)
    if not transports:
        bot.send_message(user_id, "⚠️ У вас нет сохраненного транспорта!\nХотите добавить транспорт?", reply_markup=create_transport_options_markup(), parse_mode="Markdown")
        bot.register_next_step_handler(message, ask_add_transport)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main)

    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для просмотра трат за этот период:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, get_expense_by_month)

@text_only_handler
def get_expense_by_month(message):
    user_id = str(message.from_user.id)
    date = message.text.strip() if message.text else None

    if not date:
        bot.send_message(user_id, "Пожалуйста, введите текстовое сообщение!", parse_mode="Markdown")
        bot.register_next_step_handler(message, get_expense_by_month)
        return

    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if not re.match(r"^(0[1-9]|1[0-2])\.(20[0-9]{2}|2[1-9][0-9]{2}|3000)$", date):
        bot.send_message(user_id, "Пожалуйста, введите корректный месяц и год в формате ММ.ГГГГ!", parse_mode="Markdown")
        bot.register_next_step_handler(message, get_expense_by_month)
        return

    try:
        month, year = map(int, date.split("."))
    except ValueError as e:
        bot.send_message(user_id, "Некорректный формат даты!\nПопробуйте снова", parse_mode="Markdown")
        bot.register_next_step_handler(message, get_expense_by_month)
        return

    user_data = load_expense_data(user_id).get(user_id, {})
    expense = user_data.get("expense", [])

    expense = filter_expense_by_transport(user_id, expense)

    total_expense = 0
    expense_details = []

    for index, exp in enumerate(expense, start=1):
        expense_date = exp.get("date", "")
        if not expense_date or len(expense_date.split(".")) != 3:
            continue

        try:
            expense_day, expense_month, expense_year = map(int, expense_date.split("."))
            if expense_month == month and expense_year == year:
                amount = float(exp.get("amount", 0))
                total_expense += amount

                expense_name = exp.get("name", "Без названия")
                description = exp.get("description", "Без описания")
                category = exp.get("category", "Без категории")

                expense_details.append(
                    f"💸 *№{index}*\n\n"
                    f"📂 *Категория:* {category}\n"
                    f"📌 *Название:* {expense_name}\n"
                    f"📅 *Дата:* {expense_date}\n"
                    f"💰 *Сумма:* {amount} руб.\n"
                    f"📝 *Описание:* {description}\n"
                )
        except (ValueError, TypeError) as e:
            continue

    if expense_details:
        message_text = f"Траты за *{date}* месяц:\n\n" + "\n\n".join(expense_details)
        send_message_with_split(user_id, message_text, parse_mode="Markdown")
        bot.send_message(user_id, f"Итоговая сумма трат за *{date}* месяц: *{total_expense}* руб.", parse_mode="Markdown")
    else:
        bot.send_message(user_id, f"❌ За *{date}* месяц трат не найдено!", parse_mode="Markdown")

    send_menu1(user_id)

# ----------------------------------------------- ТРАТЫ И РЕМОНТЫ (траты по году) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Траты (год)")
@check_function_state_decorator('Траты (год)')
@track_usage('Траты (год)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_expense_by_license_plate(message):
    user_id = message.from_user.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_return = types.KeyboardButton("Вернуться в меню трат и ремонтов")
    item_main = types.KeyboardButton("В главное меню")
    markup.add(item_return)
    markup.add(item_main)

    bot.send_message(user_id, "Введите год в формате (ГГГГ) для просмотра трат за этот год:", reply_markup=markup)
    bot.register_next_step_handler(message, get_expense_by_license_plate)

@text_only_handler
def get_expense_by_license_plate(message):
    user_id = message.from_user.id

    year_input = message.text.strip()

    if message.text == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
        return

    if message.text == "В главное меню":
        return_to_menu(message)
        return

    if not year_input.isdigit() or len(year_input) != 4:
        bot.send_message(user_id, "Пожалуйста, введите год в формате ГГГГ!")
        bot.register_next_step_handler(message, get_expense_by_license_plate)
        return

    year = int(year_input)
    if year < 2000 or year > 3000:
        bot.send_message(user_id, "Введите год в формате ГГГГ!")
        bot.register_next_step_handler(message, get_expense_by_license_plate)
        return

    user_data = load_expense_data(user_id)
    expense = user_data.get(str(user_id), {}).get("expense", [])

    expense = filter_expense_by_transport(user_id, expense)

    total_expense = 0
    expense_details = []

    for index, expense in enumerate(expense, start=1):
        expense_date = expense.get("date", "")
        if "." in expense_date:
            date_parts = expense_date.split(".")
            if len(date_parts) >= 3:
                expense_year = int(date_parts[2])
                if expense_year == year:
                    amount = float(expense.get("amount", 0))
                    total_expense += amount

                    expense_name = expense.get("name", "Без названия")
                    description = expense.get("description", "")
                    category = expense.get("category", "Без категории")

                    expense_details.append(
                        f"💸 *№{index}*\n\n"
                        f"📂 *Категория:* {category}\n"
                        f"📌 *Название:* {expense_name}\n"
                        f"📅 *Дата:* {expense_date}\n"
                        f"💰 *Сумма:* {amount} руб.\n"
                        f"📝 *Описание:* {description}\n"
                    )

    if expense_details:
        message_text = f"Траты за *{year}* год:\n\n" + "\n\n".join(expense_details)
        send_message_with_split(user_id, message_text, parse_mode="Markdown")
        bot.send_message(user_id, f"Итоговая сумма трат за *{year}* год: *{total_expense}* руб.", parse_mode="Markdown")
    else:
        bot.send_message(user_id, f"❌ За *{year}* год трат не найдено!", parse_mode="Markdown")

    send_menu1(user_id)

# ----------------------------------------------- ТРАТЫ И РЕМОНТЫ (все время) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Траты (все время)")
@check_function_state_decorator('Траты (все время)')
@track_usage('Траты (все время)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_all_expense(message):
    user_id = message.from_user.id

    user_data = load_expense_data(user_id)
    expense = user_data.get(str(user_id), {}).get("expense", [])

    expense = filter_expense_by_transport(user_id, expense)

    total_expense = 0
    expense_details = []

    for index, expense in enumerate(expense, start=1):
        amount = float(expense.get("amount", 0))
        total_expense += amount

        expense_name = expense.get("name", "Без названия")
        expense_date = expense.get("date", "")
        description = expense.get("description", "")
        category = expense.get("category", "Без категории")

        expense_details.append(
            f"💸 *№{index}*\n\n"
            f"📂 *Категория:* {category}\n"
            f"📌 *Название:* {expense_name}\n"
            f"📅 *Дата:* {expense_date}\n"
            f"💰 *Сумма:* {amount} руб.\n"
            f"📝 *Описание:* {description}\n"
        )

    if expense_details:
        message_text = "*Все* траты:\n\n" + "\n\n".join(expense_details)
        send_message_with_split(user_id, message_text, parse_mode="Markdown")
        bot.send_message(user_id, f"Итоговая сумма всех трат: *{total_expense}* руб.", parse_mode="Markdown")
    else:
        bot.send_message(user_id, "❌ Трат не найдено!", parse_mode="Markdown")

    send_menu1(user_id)

# ----------------------------------------------- ТРАТЫ И РЕМОНТЫ (удалить траты) ---------------------------------------------------

selected_transports = {}
expense_to_delete_dict = {}
selected_categories = {}
user_expense_to_delete = {}

MAX_MESSAGE_LENGTH = 4096

def send_long_message(user_id, text):
    while len(text) > MAX_MESSAGE_LENGTH:
        bot.send_message(user_id, text[:MAX_MESSAGE_LENGTH], parse_mode="Markdown")
        text = text[MAX_MESSAGE_LENGTH:]
    bot.send_message(user_id, text, parse_mode="Markdown")

def save_selected_transport(user_id, selected_transport):
    user_data = load_expense_data(user_id)
    user_data["selected_transport"] = selected_transport
    save_expense_data(user_id, user_data)

@bot.message_handler(func=lambda message: message.text == "Удалить траты")
@check_function_state_decorator('Удалить траты')
@track_usage('Удалить траты')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def initiate_delete_expenses(message):
    user_id = str(message.from_user.id)

    transport_data = load_transport_data(user_id)
    if not transport_data:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Добавить транспорт")
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.send_message(user_id, "⚠️ У вас нет сохраненного транспорта!\nХотите добавить транспорт?", reply_markup=markup)
        bot.register_next_step_handler(message, ask_add_transport)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    transport_buttons = [
        f"{transport['brand']} {transport['model']} ({transport['license_plate']})"
        for transport in transport_data
    ]
    for i in range(0, len(transport_buttons), 2):
        markup.row(*transport_buttons[i:i + 2])
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")

    bot.send_message(user_id, "Выберите транспорт для удаления трат:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection_for_deletion)

@text_only_handler
def handle_transport_selection_for_deletion(message):
    user_id = str(message.from_user.id)
    selected_transport = message.text.strip()

    if selected_transport == "Вернуться в меню трат и ремонтов":
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if selected_transport == "В главное меню":
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_menu(message)
        return

    transport_data = load_transport_data(user_id)
    transport_found = any(
        f"{transport['brand']} {transport['model']} ({transport['license_plate']})" == selected_transport
        for transport in transport_data
    )
    if not transport_found:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        transport_buttons = [
            f"{transport['brand']} {transport['model']} ({transport['license_plate']})"
            for transport in transport_data
        ]
        for i in range(0, len(transport_buttons), 2):
            markup.row(*transport_buttons[i:i + 2])
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.send_message(user_id, "Выбранный транспорт не найден!\nПожалуйста, выберите снова", parse_mode="Markdown", reply_markup=markup)
        bot.register_next_step_handler(message, handle_transport_selection_for_deletion)
        return

    selected_transports[user_id] = selected_transport
    save_selected_transport(user_id, selected_transport)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Del траты (категория)", "Del траты (месяц)")
    markup.add("Del траты (год)", "Del траты (все время)")
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")

    bot.send_message(user_id, "Выберите вариант удаления трат:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, handle_deletion_option)

@text_only_handler
def handle_deletion_option(message):
    user_id = str(message.from_user.id)
    option = message.text.strip()

    if option == "Вернуться в меню трат и ремонтов":
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if option == "В главное меню":
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_menu(message)
        return

    selected_transport = selected_transports.get(user_id, "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_expenses(message)
        return

    if option == "Del траты (категория)":
        delete_expense_by_category(message)
    elif option == "Del траты (месяц)":
        delete_expense_by_month(message)
    elif option == "Del траты (год)":
        delete_expense_by_year(message)
    elif option == "Del траты (все время)":
        delete_all_expense_for_selected_transport(message)
    else:
        bot.send_message(user_id, "Неверный вариант удаления!\nПопробуйте снова", parse_mode="Markdown")
        initiate_delete_expenses(message)

# ------------------------------------------- ТРАТЫ И РЕМОНТЫ (удалить траты по категории) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Del траты (категория)")
@check_function_state_decorator('Del траты (категория)')
@track_usage('Del траты (категория)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_expense_by_category(message):
    user_id = str(message.from_user.id)

    user_data = load_expense_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_expenses(message)
        return

    try:
        transport_info = selected_transport.split(" ")
        if len(transport_info) < 3:
            raise ValueError("Некорректный формат транспорта")
        selected_brand = transport_info[0].strip()
        selected_model = transport_info[1].strip()
        selected_license_plate = transport_info[2].strip().replace("(", "").replace(")", "")
    except (ValueError, IndexError) as e:
        bot.send_message(user_id, "Некорректный формат выбранного транспорта!", parse_mode="Markdown")
        initiate_delete_expenses(message)
        return

    expense = user_data.get(str(user_id), {}).get("expense", [])

    categories = list({
        exp.get("category", "Без категории")
        for exp in expense
        if all(k in exp.get("transport", {}) for k in ['brand', 'model', 'license_plate'])
        and exp["transport"]["brand"] == selected_brand
        and exp["transport"]["model"] == selected_model
        and exp["transport"]["license_plate"] == selected_license_plate
    })

    if not categories:
        bot.send_message(user_id, f"❌ Нет категорий для удаления трат по транспорту *{selected_transport}*!", parse_mode="Markdown")
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(*[types.KeyboardButton(category) for category in categories])
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")

    bot.send_message(user_id, "Выберите категорию для удаления:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, handle_category_selection_for_deletion)

@text_only_handler
def handle_category_selection_for_deletion(message):
    user_id = str(message.from_user.id)
    selected_category = message.text.strip()

    if selected_category == "Вернуться в меню трат и ремонтов":
        if user_id in selected_categories:
            del selected_categories[user_id]
        if user_id in user_expense_to_delete:
            del user_expense_to_delete[user_id]
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if selected_category == "В главное меню":
        if user_id in selected_categories:
            del selected_categories[user_id]
        if user_id in user_expense_to_delete:
            del user_expense_to_delete[user_id]
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_menu(message)
        return

    selected_transport = selected_transports.get(user_id)
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        if user_id in selected_categories:
            del selected_categories[user_id]
        return_to_expense_and_repairs(message)
        return

    try:
        transport_info = selected_transport.split(" ")
        if len(transport_info) < 3:
            raise ValueError("Некорректный формат транспорта")
        selected_brand = transport_info[0].strip()
        selected_model = transport_info[1].strip()
        selected_license_plate = transport_info[2].strip().replace("(", "").replace(")", "")
    except (ValueError, IndexError) as e:
        bot.send_message(user_id, "Некорректный формат выбранного транспорта!", parse_mode="Markdown")
        if user_id in selected_categories:
            del selected_categories[user_id]
        return_to_expense_and_repairs(message)
        return

    selected_categories[user_id] = selected_category

    user_data = load_expense_data(user_id).get(user_id, {})
    expense = user_data.get("expense", [])

    expense_to_delete = [
        exp for exp in expense
        if exp.get("category", "Без категории") == selected_category
        and all(k in exp.get("transport", {}) for k in ['brand', 'model', 'license_plate'])
        and exp["transport"]["brand"] == selected_brand
        and exp["transport"]["model"] == selected_model
        and exp["transport"]["license_plate"] == selected_license_plate
    ]

    if not expense_to_delete:
        bot.send_message(user_id, f"❌ Нет трат для удаления в категории *{selected_category.lower()}* по транспорту *{selected_transport}*!", parse_mode="Markdown")
        if user_id in selected_categories:
            del selected_categories[user_id]
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return

    user_expense_to_delete[user_id] = expense_to_delete

    expense_list_text = f"Список трат для удаления по категории *{selected_category.lower()}*:\n\n"
    for index, exp in enumerate(expense_to_delete, start=1):
        expense_name = exp.get("name", "Без названия")
        expense_date = exp.get("date", "Неизвестно")
        expense_list_text += f"📄 №{index}. {expense_name} - ({expense_date})\n\n"

    expense_list_text += "Введите номер траты для удаления:"
    send_long_message(user_id, expense_list_text)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")

    bot.register_next_step_handler(message, delete_expense_confirmation)

@text_only_handler
def delete_expense_confirmation(message):
    user_id = str(message.from_user.id)
    selected_option = message.text.strip()

    if selected_option == "Вернуться в меню трат и ремонтов":
        if user_id in selected_categories:
            del selected_categories[user_id]
        if user_id in user_expense_to_delete:
            del user_expense_to_delete[user_id]
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if selected_option == "В главное меню":
        if user_id in selected_categories:
            del selected_categories[user_id]
        if user_id in user_expense_to_delete:
            del user_expense_to_delete[user_id]
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_menu(message)
        return

    expense_to_delete = user_expense_to_delete.get(user_id, [])
    if not expense_to_delete:
        bot.send_message(user_id, "❌ Нет трат для удаления по категории!", parse_mode="Markdown")
        if user_id in selected_categories:
            del selected_categories[user_id]
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return

    try:
        indices = [int(num.strip()) - 1 for num in selected_option.split(',')]
        valid_indices = []
        invalid_indices = []

        for index in indices:
            if 0 <= index < len(expense_to_delete):
                valid_indices.append(index)
            else:
                invalid_indices.append(index + 1)

        if not valid_indices and invalid_indices:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add("Вернуться в меню трат и ремонтов")
            markup.add("В главное меню")
            msg = bot.send_message(user_id, "Некорректные номера!\nПожалуйста, выберите существующие траты из списка", reply_markup=markup, parse_mode="Markdown")
            bot.register_next_step_handler(msg, delete_expense_confirmation)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(user_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode="Markdown")

        valid_indices.sort(reverse=True)
        deleted_expense_names = []
        user_data = load_expense_data(user_id).get(user_id, {})
        user_expense = user_data.get("expense", [])

        for index in valid_indices:
            deleted_expense = expense_to_delete.pop(index)
            deleted_expense_names.append(deleted_expense.get('name', 'Без названия').lower())
            if deleted_expense in user_expense:
                user_expense.remove(deleted_expense)

        user_data["expense"] = user_expense
        save_expense_data(user_id, {user_id: user_data})
        update_excel_file_expense(user_id)

        bot.send_message(user_id, f"✅ Траты *{', '.join(deleted_expense_names)}* успешно удалены!", parse_mode="Markdown")

        if not expense_to_delete:
            if user_id in user_expense_to_delete:
                del user_expense_to_delete[user_id]
            if user_id in selected_categories:
                del selected_categories[user_id]
            if user_id in selected_transports:
                del selected_transports[user_id]

        return_to_expense_and_repairs(message)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        msg = bot.send_message(user_id, "Некорректный ввод!\nПожалуйста, введите номера трат через запятую", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, delete_expense_confirmation)

# ------------------------------------------- ТРАТЫ И РЕМОНТЫ (удалить траты по месяцу) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Del траты (месяц)")
@check_function_state_decorator('Del траты (месяц)')
@track_usage('Del траты (месяц)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_expense_by_month(message):
    user_id = str(message.from_user.id)

    user_data = load_expense_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_expenses(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")
    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для удаления трат за этот месяц:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_delete_expense_by_month)

@text_only_handler
def process_delete_expense_by_month(message):
    user_id = str(message.from_user.id)
    month_year = message.text.strip()

    if month_year == "Вернуться в меню трат и ремонтов":
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if month_year == "В главное меню":
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_menu(message)
        return

    match = re.match(r"^(0[1-9]|1[0-2])\.(20[0-9]{2}|2[1-9][0-9]{2}|3000)$", month_year)
    if not match:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.send_message(user_id, "Введен неверный месяц или год!\nПожалуйста, введите корректные данные (ММ.ГГГГ)", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_delete_expense_by_month)
        return

    selected_month, selected_year = map(int, match.groups())

    user_data = load_expense_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_expenses(message)
        return

    try:
        transport_info = selected_transport.split(" ")
        if len(transport_info) < 3:
            raise ValueError("Некорректный формат транспорта")
        selected_brand = transport_info[0].strip()
        selected_model = transport_info[1].strip()
        selected_license_plate = transport_info[2].strip().replace("(", "").replace(")", "")
    except (ValueError, IndexError) as e:
        bot.send_message(user_id, "Некорректный формат выбранного транспорта!", parse_mode="Markdown")
        initiate_delete_expenses(message)
        return

    expense = user_data.get(str(user_id), {}).get("expense", [])

    if not expense:
        bot.send_message(user_id, f"❌ У вас нет сохраненных трат за *{month_year}* месяц!", parse_mode="Markdown")
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return

    expense_to_delete = []
    for index, exp in enumerate(expense, start=1):
        expense_date = exp.get("date", "")
        if not expense_date or len(expense_date.split(".")) != 3:
            continue
        try:
            expense_day, expense_month, expense_year = map(int, expense_date.split("."))
            transport = exp.get("transport", {})
            if not all(k in transport for k in ['brand', 'model', 'license_plate']):
                continue
            if (expense_month == selected_month and
                expense_year == selected_year and
                transport['brand'] == selected_brand and
                transport['model'] == selected_model and
                transport['license_plate'] == selected_license_plate):
                expense_to_delete.append((index, exp))
        except (ValueError, TypeError) as e:
            continue

    if expense_to_delete:
        expense_to_delete_dict[user_id] = expense_to_delete
        expense_list_text = f"Список трат для удаления за *{month_year}* месяц:\n\n"
        for index, exp in expense_to_delete:
            expense_name = exp.get("name", "Без названия")
            expense_date = exp.get("date", "Неизвестно")
            expense_list_text += f"📄 №{index}. {expense_name} - ({expense_date})\n\n"
        expense_list_text += "Введите номер траты для удаления:"
        send_long_message(user_id, expense_list_text)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.register_next_step_handler(message, confirm_delete_expense_month)
    else:
        bot.send_message(user_id, f"❌ Нет трат для удаления за *{month_year}* месяц!", parse_mode="Markdown")
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)

@text_only_handler
def confirm_delete_expense_month(message):
    user_id = str(message.from_user.id)
    selected_option = message.text.strip()

    if selected_option == "Вернуться в меню трат и ремонтов":
        if user_id in expense_to_delete_dict:
            del expense_to_delete_dict[user_id]
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if selected_option == "В главное меню":
        if user_id in expense_to_delete_dict:
            del expense_to_delete_dict[user_id]
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_menu(message)
        return

    expense_to_delete = expense_to_delete_dict.get(user_id, [])
    if not expense_to_delete:
        bot.send_message(user_id, "❌ Нет трат для удаления по месяцу!", parse_mode="Markdown")
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return

    try:
        indices = [int(num.strip()) - 1 for num in selected_option.split(',')]
        valid_indices = []
        invalid_indices = []

        for index in indices:
            if 0 <= index < len(expense_to_delete):
                valid_indices.append(index)
            else:
                invalid_indices.append(index + 1)

        if not valid_indices and invalid_indices:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Вернуться в меню трат и ремонтов")
            markup.add("В главное меню")
            msg = bot.send_message(user_id, "Некорректные номера!\nПожалуйста, выберите существующие траты из списка", reply_markup=markup, parse_mode="Markdown")
            bot.register_next_step_handler(msg, confirm_delete_expense_month)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(user_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode="Markdown")

        valid_indices.sort(reverse=True)
        deleted_expense_names = []
        user_data = load_expense_data(user_id).get(str(user_id), {})
        user_expense = user_data.get("expense", [])

        for index in valid_indices:
            _, deleted_expense = expense_to_delete.pop(index)
            deleted_expense_names.append(deleted_expense.get('name', 'Без названия').lower())
            if deleted_expense in user_expense:
                user_expense.remove(deleted_expense)

        user_data["expense"] = user_expense
        save_expense_data(user_id, {str(user_id): user_data})
        update_excel_file_expense(user_id)

        bot.send_message(user_id, f"✅ Траты *{', '.join(deleted_expense_names)}* успешно удалены!", parse_mode="Markdown")

        if not expense_to_delete:
            if user_id in expense_to_delete_dict:
                del expense_to_delete_dict[user_id]
            if user_id in selected_transports:
                del selected_transports[user_id]
        else:
            expense_to_delete_dict[user_id] = expense_to_delete

        return_to_expense_and_repairs(message)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        msg = bot.send_message(user_id, "Некорректный ввод!\nПожалуйста, введите номера трат через запятую", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, confirm_delete_expense_month)

# ------------------------------------------- ТРАТЫ И РЕМОНТЫ (удалить траты по году) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Del траты (год)")
@check_function_state_decorator('Del траты (год)')
@track_usage('Del траты (год)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_expense_by_year(message):
    user_id = str(message.from_user.id)

    user_data = load_expense_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    if not selected_transport:
        bot.send_message(user_id, "❌ ❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_expenses(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")
    bot.send_message(user_id, "Введите год (ГГГГ) для удаления трат за этот год:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_delete_expense_by_year)

@text_only_handler
def process_delete_expense_by_year(message):
    user_id = str(message.from_user.id)
    year_input = message.text.strip()

    if year_input == "Вернуться в меню трат и ремонтов":
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if year_input == "В главное меню":
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_menu(message)
        return

    if not year_input.isdigit() or len(year_input) != 4 or not (2000 <= int(year_input) <= 3000):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.send_message(user_id, "Пожалуйста, введите корректный год в формате ГГГГ (2000-3000)!", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_delete_expense_by_year)
        return

    year = int(year_input)

    user_data = load_expense_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_expenses(message)
        return

    try:
        transport_info = selected_transport.split(" ")
        if len(transport_info) < 3:
            raise ValueError("Некорректный формат транспорта")
        selected_brand = transport_info[0].strip()
        selected_model = transport_info[1].strip()
        selected_license_plate = transport_info[2].strip().replace("(", "").replace(")", "")
    except (ValueError, IndexError) as e:
        bot.send_message(user_id, "Некорректный формат выбранного транспорта!", parse_mode="Markdown")
        initiate_delete_expenses(message)
        return

    expense = user_data.get(str(user_id), {}).get("expense", [])

    if not expense:
        bot.send_message(
            user_id, f"❌ У вас нет сохраненных трат за *{year}* год!",parse_mode="Markdown")
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return

    expense_to_delete = []
    for index, exp in enumerate(expense, start=1):
        expense_date = exp.get("date", "")
        if not expense_date or len(expense_date.split(".")) != 3:
            continue
        try:
            expense_day, expense_month, expense_year = map(int, expense_date.split("."))
            transport = exp.get("transport", {})
            if not all(k in transport for k in ['brand', 'model', 'license_plate']):
                continue
            if (expense_year == year and
                transport['brand'] == selected_brand and
                transport['model'] == selected_model and
                transport['license_plate'] == selected_license_plate):
                expense_to_delete.append((index, exp))
        except (ValueError, TypeError) as e:
            continue

    if expense_to_delete:
        expense_to_delete_dict[user_id] = expense_to_delete
        expense_list_text = f"Список трат для удаления за *{year}* год:\n\n"
        for index, exp in expense_to_delete:
            expense_name = exp.get("name", "Без названия")
            expense_date = exp.get("date", "Неизвестно")
            expense_list_text += f"📄 №{index}. {expense_name} - ({expense_date})\n\n"
        expense_list_text += "Введите номер траты для удаления:"
        send_long_message(user_id, expense_list_text)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.register_next_step_handler(message, confirm_delete_expense_year)
    else:
        bot.send_message(
            user_id, f"❌ За *{year}* год трат не найдено для удаления!", parse_mode="Markdown")
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)

@text_only_handler
def confirm_delete_expense_year(message):
    user_id = str(message.from_user.id)
    selected_option = message.text.strip()

    if selected_option == "Вернуться в меню трат и ремонтов":
        if user_id in expense_to_delete_dict:
            del expense_to_delete_dict[user_id]
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if selected_option == "В главное меню":
        if user_id in expense_to_delete_dict:
            del expense_to_delete_dict[user_id]
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_menu(message)
        return

    expense_to_delete = expense_to_delete_dict.get(user_id, [])
    if not expense_to_delete:
        bot.send_message(user_id, "❌ Нет трат для удаления по году!", parse_mode="Markdown")
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return

    try:
        indices = [int(num.strip()) - 1 for num in selected_option.split(',')]
        valid_indices = []
        invalid_indices = []

        for index in indices:
            if 0 <= index < len(expense_to_delete):
                valid_indices.append(index)
            else:
                invalid_indices.append(index + 1)

        if not valid_indices and invalid_indices:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Вернуться в меню трат и ремонтов")
            markup.add("В главное меню")
            msg = bot.send_message(user_id, "Некорректные номера!\nПожалуйста, выберите существующие траты из списка", reply_markup=markup, parse_mode="Markdown")
            bot.register_next_step_handler(msg, confirm_delete_expense_year)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(user_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode="Markdown")

        valid_indices.sort(reverse=True)
        deleted_expense_names = []
        user_data = load_expense_data(user_id).get(str(user_id), {})
        user_expense = user_data.get("expense", [])

        for index in valid_indices:
            _, deleted_expense = expense_to_delete.pop(index)
            deleted_expense_names.append(deleted_expense.get('name', 'Без названия').lower())
            if deleted_expense in user_expense:
                user_expense.remove(deleted_expense)

        user_data["expense"] = user_expense
        save_expense_data(user_id, {str(user_id): user_data})
        update_excel_file_expense(user_id)

        bot.send_message(user_id, f"✅ Траты *{', '.join(deleted_expense_names)}* успешно удалены!", parse_mode="Markdown")

        if not expense_to_delete:
            if user_id in expense_to_delete_dict:
                del expense_to_delete_dict[user_id]
            if user_id in selected_transports:
                del selected_transports[user_id]
        else:
            expense_to_delete_dict[user_id] = expense_to_delete

        return_to_expense_and_repairs(message)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        msg = bot.send_message(user_id, "Некорректный ввод!\nПожалуйста, введите номера трат через запятую", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, confirm_delete_expense_year)

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (удалить траты по все время) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Del траты (все время)")
@check_function_state_decorator('Del траты (все время)')
@track_usage('Del траты (все время)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_all_expense_for_selected_transport(message):
    user_id = str(message.from_user.id)

    user_data = load_expense_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_expenses(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Да", "Нет")
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")

    bot.send_message(user_id, f"⚠️ Вы уверены, что хотите удалить все траты для транспорта *{selected_transport}*?\n\n"
        "Пожалуйста, введите *да* для подтверждения или *нет* для отмены", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, confirm_delete_all_expense)

@text_only_handler
def confirm_delete_all_expense(message):
    user_id = str(message.from_user.id)
    response = message.text.strip().lower()

    if response == "вернуться в меню трат и ремонтов":
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if response == "в главное меню":
        if user_id in selected_transports:
            del selected_transports[user_id]
        return_to_menu(message)
        return

    user_data = load_expense_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_expenses(message)
        return

    try:
        transport_info = selected_transport.split(" ")
        if len(transport_info) < 3:
            raise ValueError("Некорректный формат транспорта")
        selected_brand = transport_info[0].strip()
        selected_model = transport_info[1].strip()
        selected_license_plate = transport_info[2].strip().replace("(", "").replace(")", "")
    except (ValueError, IndexError) as e:
        bot.send_message(user_id, "Некорректный формат выбранного транспорта!", parse_mode="Markdown")
        initiate_delete_expenses(message)
        return

    if response == "да":
        expense = user_data.get(str(user_id), {}).get("expense", [])
        if not expense:
            bot.send_message(user_id, "❌ У вас нет сохраненных трат для удаления!", parse_mode="Markdown")
            if user_id in selected_transports:
                del selected_transports[user_id]
            return_to_expense_and_repairs(message)
            return

        expense_to_keep = []
        for exp in expense:
            transport = exp.get("transport", {})
            if not all(k in transport for k in ['brand', 'model', 'license_plate']):
                expense_to_keep.append(exp)
                continue
            if not (transport['brand'] == selected_brand and
                    transport['model'] == selected_model and
                    transport['license_plate'] == selected_license_plate):
                expense_to_keep.append(exp)

        user_data[str(user_id)] = user_data.get(str(user_id), {})
        user_data[str(user_id)]["expense"] = expense_to_keep
        save_expense_data(user_id, user_data)
        update_excel_file_expense(user_id)

        bot.send_message(user_id, f"✅ Все траты для транспорта *{selected_transport}* успешно удалены!", parse_mode="Markdown")
    elif response == "нет":
        bot.send_message(user_id, "✅ Удаление трат отменено!", parse_mode="Markdown")
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Да", "Нет")
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.send_message(user_id, "Пожалуйста, введите *да* для подтверждения или *нет* для отмены", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, confirm_delete_all_expense)
        return

    if user_id in selected_transports:
        del selected_transports[user_id]
    return_to_expense_and_repairs(message)

def update_excel_file_expense(user_id):
    user_id = str(user_id)
    user_data = load_expense_data(user_id).get(user_id, {})
    expense = user_data.get("expense", [])
    excel_file_path = os.path.join(BASE_DIR, "data", "user", "expenses_and_repairs", "expenses", "excel", f"{user_id}_expenses.xlsx")

    try:
        if not os.path.exists(excel_file_path):
            workbook = openpyxl.Workbook()
            workbook.remove(workbook.active)
        else:
            workbook = load_workbook(excel_file_path)

        headers = ["Транспорт", "Категория", "Название", "Дата", "Сумма", "Описание"]
        summary_sheet = workbook["Summary"] if "Summary" in workbook.sheetnames else workbook.create_sheet("Summary")

        if summary_sheet.max_row > 1:
            summary_sheet.delete_rows(2, summary_sheet.max_row - 1)
        if summary_sheet.max_row == 0:
            summary_sheet.append(headers)
            for cell in summary_sheet[1]:
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal="center")

        unique_transports = set()
        valid_expenses = []
        for exp in expense:
            transport = exp.get("transport", {})
            if not all(k in transport for k in ['brand', 'model', 'license_plate']):
                continue
            unique_transports.add((transport["brand"], transport["model"], transport["license_plate"]))
            valid_expenses.append(exp)

        for exp in valid_expenses:
            transport = exp["transport"]
            row_data = [
                f"{transport['brand']} {transport['model']} ({transport['license_plate']})",
                exp.get("category", "Без категории"),
                exp.get("name", "Без названия"),
                exp.get("date", ""),
                float(exp.get("amount", 0)),
                exp.get("description", "Без описания"),
            ]
            summary_sheet.append(row_data)

        for sheet_name in workbook.sheetnames:
            if sheet_name != "Summary":
                try:
                    brand, model, license_plate = sheet_name.split('_')
                    if (brand, model, license_plate) not in unique_transports:
                        del workbook[sheet_name]
                except ValueError:
                    continue

        for brand, model, license_plate in unique_transports:
            sheet_name = f"{brand}_{model}_{license_plate}"[:31]
            transport_sheet = workbook[sheet_name] if sheet_name in workbook.sheetnames else workbook.create_sheet(sheet_name)

            if transport_sheet.max_row > 1:
                transport_sheet.delete_rows(2, transport_sheet.max_row - 1)
            if transport_sheet.max_row == 0:
                transport_sheet.append(headers)
                for cell in transport_sheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal="center")

            for exp in valid_expenses:
                transport = exp["transport"]
                if (transport["brand"], transport["model"], transport["license_plate"]) == (brand, model, license_plate):
                    row_data = [
                        f"{brand} {model} ({license_plate})",
                        exp.get("category", "Без категории"),
                        exp.get("name", "Без названия"),
                        exp.get("date", ""),
                        float(exp.get("amount", 0)),
                        exp.get("description", "Без описания"),
                    ]
                    transport_sheet.append(row_data)

        for sheet in workbook:
            for col in sheet.columns:
                max_length = max(len(str(cell.value)) for cell in col if cell.value) + 2
                sheet.column_dimensions[get_column_letter(col[0].column)].width = max_length

        workbook.save(excel_file_path)
        workbook.close()

    except Exception as e:
        bot.send_message(user_id, "Ошибка при обновлении Excel-файла трат!", parse_mode="Markdown")

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (ремонты) ---------------------------------------------------

DATA_BASE_DIR = os.path.join(BASE_DIR, "data", "user", "expenses_and_repairs")
REPAIRS_DIR = os.path.join(DATA_BASE_DIR, "repairs")

def ensure_directories():
    os.makedirs(REPAIRS_DIR, exist_ok=True)
    os.makedirs(os.path.join(REPAIRS_DIR, "excel"), exist_ok=True)

ensure_directories()

user_transport = {}  

def format_transport_string(transport):
    if isinstance(transport, dict):
        return f"{transport.get('brand', '').strip()} {transport.get('model', '').strip()} ({transport.get('license_plate', '').strip()})".lower()
    return transport.strip().lower()

def save_repair_data(user_id, user_data, selected_transport=None):
    ensure_directories()
    
    file_path = os.path.join(REPAIRS_DIR, f"{user_id}_repairs.json")
    
    current_data = load_repair_data(user_id)
    
    if selected_transport:
        current_data["selected_transport"] = selected_transport
    else:
        current_data.setdefault("selected_transport", "")
    
    current_data.setdefault("user_categories", [])
    if "user_categories" in user_data:
        current_data["user_categories"] = user_data["user_categories"]
    
    current_data[str(user_id)] = user_data.get(str(user_id), {"repairs": []})
    
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(current_data, file, ensure_ascii=False, indent=4)

def load_repair_data(user_id):
    ensure_directories()
    
    file_path = os.path.join(REPAIRS_DIR, f"{user_id}_repairs.json")
    
    if not os.path.exists(file_path):
        return {"user_categories": [], "selected_transport": "", str(user_id): {"repairs": []}}
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            data.setdefault("user_categories", [])
            data.setdefault("selected_transport", "")
            data.setdefault(str(user_id), {"repairs": []})
            return data
    except Exception as e:
        return {"user_categories": [], "selected_transport": "", str(user_id): {"repairs": []}}

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (записать ремонт) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Записать ремонт")
@check_function_state_decorator('Записать ремонт')
@track_usage('Записать ремонт')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def record_repair(message):
    user_id = message.from_user.id
    
    markup = get_user_transport_keyboard(user_id)
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Выберите транспорт для записи ремонта:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection_for_repair)

@text_only_handler
def handle_transport_selection_for_repair(message):
    user_id = message.from_user.id
    selected_transport = message.text.strip()
    
    if selected_transport == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
        return
    if selected_transport == "В главное меню":
        return_to_menu(message)
        return
    if selected_transport == "Добавить транспорт":
        add_transport(message)
        return
    
    transports = load_transport_data(user_id)
    for transport in transports:
        formatted_transport = f"{transport['brand']} {transport['model']} ({transport['license_plate']})"
        if formatted_transport == selected_transport:
            brand, model, license_plate = transport['brand'], transport['model'], transport['license_plate']
            save_repair_data(user_id, load_repair_data(user_id), selected_transport)
            process_category_selection_repair(user_id, brand, model, license_plate)
            return
    
    bot.send_message(user_id, "❌ Не удалось найти указанный транспорт! Пожалуйста, выберите снова.", parse_mode="Markdown")
    markup = get_user_transport_keyboard(user_id)
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    bot.send_message(user_id, "Выберите транспорт или добавьте новый:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection_for_repair)

def process_category_selection_repair(user_id, brand, model, license_plate):
    categories = get_user_repair_categories(user_id)
    
    system_emoji = "🔹"
    user_emoji = "🔸"
    
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
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    message = bot.send_message(user_id, category_list, reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, partial(get_repair_category, brand=brand, model=model, license_plate=license_plate))

def get_user_repair_categories(user_id):
    data = load_repair_data(user_id)
    system_categories = ["Без категории", "ТО", "Ремонт", "Запчасть", "Диагностика", "Электрика", "Кузов"]
    user_categories = data.get("user_categories", [])
    return system_categories + user_categories

def add_repair_category(user_id, new_category):
    data = load_repair_data(user_id)
    data.setdefault("user_categories", [])
    if new_category not in data["user_categories"]:
        data["user_categories"].append(new_category)
        save_repair_data(user_id, data)
        return True
    return False

def remove_repair_category(user_id, category_to_remove):
    data = load_repair_data(user_id)
    if "user_categories" in data and category_to_remove in data["user_categories"]:
        data["user_categories"].remove(category_to_remove)
        save_repair_data(user_id, data)
        return True
    return False

@text_only_handler
def get_repair_category(message, brand, model, license_plate):
    user_id = message.from_user.id
    selected_index = message.text.strip()
    
    if selected_index == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
        return
    if selected_index == "В главное меню":
        return_to_menu(message)
        return
    if selected_index == "Добавить категорию":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.send_message(user_id, "Введите название новой категории:", reply_markup=markup)
        bot.register_next_step_handler(message, partial(add_new_repair_category, brand=brand, model=model, license_plate=license_plate))
        return
    if selected_index == "Удалить категорию":
        handle_repair_category_removal(message, brand, model, license_plate)
        return
    
    if selected_index.isdigit():
        index = int(selected_index) - 1
        categories = get_user_repair_categories(user_id)
        if 0 <= index < len(categories):
            selected_category = categories[index]
            proceed_to_repair_name(message, selected_category, brand, model, license_plate)
        else:
            bot.send_message(user_id, "❌ Неверный номер категории! Попробуйте снова.", parse_mode="Markdown")
            process_category_selection_repair(user_id, brand, model, license_plate)
    else:
        bot.send_message(user_id, "❌ Пожалуйста, введите номер категории!", parse_mode="Markdown")
        process_category_selection_repair(user_id, brand, model, license_plate)

@text_only_handler
def add_new_repair_category(message, brand, model, license_plate):
    user_id = message.from_user.id
    new_category = message.text.strip()
    
    if new_category in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if new_category == "Вернуться в меню трат и ремонтов":
            return_to_expense_and_repairs(message)
        else:
            return_to_menu(message)
        return
    
    if not new_category:
        bot.send_message(user_id, "❌ Пожалуйста, введите название категории!", parse_mode="Markdown")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.register_next_step_handler(message, partial(add_new_repair_category, brand=brand, model=model, license_plate=license_plate))
        return
    
    system_categories = ["Без категории", "ТО", "Ремонт", "Запчасть", "Диагностика", "Электрика", "Кузов"]
    if new_category in system_categories or new_category in get_user_repair_categories(user_id):
        bot.send_message(user_id, f"❌ Категория *{new_category}* уже существует!", parse_mode="Markdown")
    else:
        if add_repair_category(user_id, new_category):
            bot.send_message(user_id, f"✅ Категория *{new_category}* успешно добавлена!", parse_mode="Markdown")
        else:
            bot.send_message(user_id, f"❌ Ошибка при добавлении категории *{new_category}*!", parse_mode="Markdown")
    
    process_category_selection_repair(user_id, brand, model, license_plate)

@text_only_handler
def handle_repair_category_removal(message, brand, model, license_plate):
    user_id = message.from_user.id
    categories = get_user_repair_categories(user_id)
    system_categories = ["Без категории", "ТО", "Ремонт", "Запчасть", "Диагностика", "Электрика", "Кузов"]
    user_categories = [cat for cat in categories if cat not in system_categories]
    
    if not user_categories:
        bot.send_message(user_id, "❌ Нет пользовательских категорий для удаления!", parse_mode="Markdown")
        process_category_selection_repair(user_id, brand, model, license_plate)
        return
    
    user_emoji = "🔸"
    
    category_list = "\n".join(
        f"{user_emoji} {i + 1}. {category}"
        for i, category in enumerate(user_categories)
    )
    bot.send_message(user_id, f"Выберите категорию для удаления или 0 для отмены:\n\n{category_list}", parse_mode="Markdown")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("0"))
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
    bot.register_next_step_handler(message, partial(remove_repair_category_handler, user_categories=user_categories, brand=brand, model=model, license_plate=license_plate))

@text_only_handler
def remove_repair_category_handler(message, user_categories, brand, model, license_plate):
    user_id = message.from_user.id
    selected_index = message.text.strip()
    
    if selected_index == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
        return
    if selected_index == "В главное меню":
        return_to_menu(message)
        return
    if selected_index == "0":
        process_category_selection_repair(user_id, brand, model, license_plate)
        return
    
    if selected_index.isdigit():
        index = int(selected_index) - 1
        if 0 <= index < len(user_categories):
            category_to_remove = user_categories[index]
            if remove_repair_category(user_id, category_to_remove):
                bot.send_message(user_id, f"✅ Категория *{category_to_remove}* успешно удалена!", parse_mode="Markdown")
            else:
                bot.send_message(user_id, f"❌ Ошибка при удалении категории *{category_to_remove}*!", parse_mode="Markdown")
            process_category_selection_repair(user_id, brand, model, license_plate)
        else:
            bot.send_message(user_id, "❌ Неверный номер категории! Попробуйте снова.", parse_mode="Markdown")
            handle_repair_category_removal(message, brand, model, license_plate)
    else:
        bot.send_message(user_id, "❌ Пожалуйста, введите номер категории или 0!", parse_mode="Markdown")
        handle_repair_category_removal(message, brand, model, license_plate)

@text_only_handler
def proceed_to_repair_name(message, selected_category, brand, model, license_plate):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Введите название ремонта:", reply_markup=markup)
    bot.register_next_step_handler(message, partial(get_repair_name, selected_category=selected_category, brand=brand, model=model, license_plate=license_plate))

@text_only_handler
def get_repair_name(message, selected_category, brand, model, license_plate):
    user_id = message.from_user.id
    repair_name = message.text.strip()
    
    if repair_name in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if repair_name == "Вернуться в меню трат и ремонтов":
            return_to_expense_and_repairs(message)
        else:
            return_to_menu(message)
        return
    
    if not repair_name:
        bot.send_message(user_id, "❌ Пожалуйста, введите название ремонта!", parse_mode="Markdown")
        proceed_to_repair_name(message, selected_category, brand, model, license_plate)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Пропустить описание"))
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Введите описание ремонта или пропустите этот шаг:", reply_markup=markup)
    bot.register_next_step_handler(message, partial(get_repair_description, selected_category=selected_category, repair_name=repair_name, brand=brand, model=model, license_plate=license_plate))

@text_only_handler
def get_repair_description(message, selected_category, repair_name, brand, model, license_plate):
    user_id = message.from_user.id
    repair_description = message.text.strip() if message.text != "Пропустить описание" else ""
    
    if message.text in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if message.text == "Вернуться в меню трат и ремонтов":
            return_to_expense_and_repairs(message)
        else:
            return_to_menu(message)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Введите дату ремонта (ДД.ММ.ГГГГ):", reply_markup=markup)
    bot.register_next_step_handler(message, partial(get_repair_date, selected_category=selected_category, repair_name=repair_name, repair_description=repair_description, brand=brand, model=model, license_plate=license_plate))

def is_valid_date(date_str):
    pattern = r'^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.(2000|20[0-2][0-9])$'
    return bool(re.match(pattern, date_str))

@text_only_handler
def get_repair_date(message, selected_category, repair_name, repair_description, brand, model, license_plate):
    user_id = message.from_user.id
    repair_date = message.text.strip()
    
    if repair_date in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if repair_date == "Вернуться в меню трат и ремонтов":
            return_to_expense_and_repairs(message)
        else:
            return_to_menu(message)
        return
    
    if not is_valid_date(repair_date):
        bot.send_message(user_id, "❌ Неверный формат даты! Введите дату в формате ДД.ММ.ГГГГ.", parse_mode="Markdown")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        markup.add(types.KeyboardButton("В главное меню"))
        bot.register_next_step_handler(message, partial(get_repair_date, selected_category=selected_category, repair_name=repair_name, repair_description=repair_description, brand=brand, model=model, license_plate=license_plate))
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Введите сумму ремонта:", reply_markup=markup)
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
            selected_transport=f"{brand} {model} ({license_plate})"
        )
    )

@text_only_handler
def save_repair_data_final(message, selected_category, repair_name, repair_description, repair_date, brand, model, license_plate, selected_transport):
    user_id = message.from_user.id
    repair_amount = message.text.strip()
    
    if repair_amount in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if repair_amount == "Вернуться в меню трат и ремонтов":
            return_to_expense_and_repairs(message)
        else:
            return_to_menu(message)
        return
    
    try:
        repair_amount = float(repair_amount)
        if repair_amount < 0:
            raise ValueError("Сумма не может быть отрицательной")
        
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
        
        user_data = load_repair_data(user_id)
        user_data.setdefault(str(user_id), {"repairs": []})
        user_data[str(user_id)]["repairs"].append(repair_data)
        
        save_repair_data(user_id, user_data, selected_transport)
        save_repair_to_excel(user_id, repair_data)
        
        bot.send_message(user_id, f"✅ Ремонт *{repair_name}* успешно записан!", parse_mode="Markdown")
        return_to_expense_and_repairs(message)
    
    except ValueError:
        bot.send_message(user_id, "❌ Пожалуйста, введите корректную сумму!", parse_mode="Markdown")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        markup.add(types.KeyboardButton("В главное меню"))
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
    excel_path = os.path.join(REPAIRS_DIR, "excel", f"{user_id}_repairs.xlsx")
    
    try:
        if os.path.exists(excel_path):
            try:
                workbook = load_workbook(excel_path)
            except Exception:
                workbook = Workbook()
                workbook.remove(workbook.active)
        else:
            workbook = Workbook()
            workbook.remove(workbook.active)
        
        if "Summary" not in workbook.sheetnames:
            summary_sheet = workbook.create_sheet("Summary")
        else:
            summary_sheet = workbook["Summary"]
        
        transport_sheet_name = f"{repair_data['transport']['brand']}_{repair_data['transport']['model']}_{repair_data['transport']['license_plate']}"[:31]
        if transport_sheet_name not in workbook.sheetnames:
            transport_sheet = workbook.create_sheet(transport_sheet_name)
        else:
            transport_sheet = workbook[transport_sheet_name]
        
        headers = ["Транспорт", "Категория", "Название", "Дата", "Сумма", "Описание"]
        
        def setup_sheet(sheet):
            if sheet.max_row == 0 or sheet[1][0].value != headers[0]:
                sheet.append(headers)
                for cell in sheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal="center")
        
        for sheet in [summary_sheet, transport_sheet]:
            setup_sheet(sheet)
            row_data = [
                f"{repair_data['transport']['brand']} {repair_data['transport']['model']} ({repair_data['transport']['license_plate']})",
                repair_data["category"],
                repair_data["name"],
                repair_data["date"],
                float(repair_data["amount"]),
                repair_data["description"],
            ]
            sheet.append(row_data)
        
        for sheet in [summary_sheet, transport_sheet]:
            for col in sheet.columns:
                max_length = max(len(str(cell.value)) for cell in col if cell.value)
                sheet.column_dimensions[get_column_letter(col[0].column)].width = max_length + 2
        
        workbook.save(excel_path)
        workbook.close()
    
    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка при сохранении данных в Excel!\nПопробуйте снова", parse_mode="Markdown")

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (посмотреть ремонты) ---------------------------------------------------

selected_repair_transport_dict = {}

def filter_repairs_by_transport(user_id, repairs):
    selected_transport = selected_repair_transport_dict.get(user_id, load_repair_data(user_id).get("selected_transport", ""))
    if not selected_transport:
        return repairs
    
    selected_transport = format_transport_string(selected_transport)
    
    filtered_repairs = [
        repair for repair in repairs
        if format_transport_string(repair.get("transport", {})) == selected_transport
    ]
    return filtered_repairs

def send_repair_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Ремонты (по категориям)"), types.KeyboardButton("Ремонты (месяц)"))
    markup.add(types.KeyboardButton("Ремонты (год)"), types.KeyboardButton("Ремонты (все время)"))
    markup.add(types.KeyboardButton("Посмотреть ремонты в EXCEL"))
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Выберите вариант просмотра ремонтов:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Посмотреть ремонты")
@check_function_state_decorator('Посмотреть ремонты')
@track_usage('Посмотреть ремонты')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_repairs(message):
    user_id = message.from_user.id
    transport_list = load_transport_data(user_id)
    
    if not transport_list:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Добавить транспорт"))
        markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
        bot.send_message(user_id, "⚠️ У вас нет сохраненного транспорта! Хотите добавить транспорт?", reply_markup=markup)
        bot.register_next_step_handler(message, ask_add_transport)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    transport_buttons = [
        types.KeyboardButton(f"{transport['brand']} {transport['model']} ({transport['license_plate']})")
        for transport in transport_list
    ]
    for i in range(0, len(transport_buttons), 2):
        markup.add(*transport_buttons[i:i+2])
    
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Выберите ваш транспорт для просмотра ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_transport_selection_for_repairs)

@text_only_handler
def handle_transport_selection_for_repairs(message):
    user_id = message.from_user.id
    selected_transport = message.text.strip()
    
    if selected_transport == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
        return
    if selected_transport == "В главное меню":
        return_to_menu(message)
        return
    
    transport_list = load_transport_data(user_id)
    if selected_transport not in [f"{t['brand']} {t['model']} ({t['license_plate']})" for t in transport_list]:
        bot.send_message(user_id, "❌ Выбранный транспорт не найден! Попробуйте снова.", parse_mode="Markdown")
        view_repairs(message)
        return
    
    selected_repair_transport_dict[user_id] = selected_transport
    save_repair_data(user_id, load_repair_data(user_id), selected_transport)
    
    bot.send_message(user_id, f"Показываю ремонты для транспорта: *{selected_transport}*", parse_mode="Markdown")
    send_repair_menu(user_id)

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (посмотреть ремонты в excel) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Посмотреть ремонты в EXCEL")
@check_function_state_decorator('Посмотреть ремонты в EXCEL')
@track_usage('Посмотреть ремонты в EXCEL')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def send_repairs_excel(message):
    user_id = message.from_user.id
    excel_path = os.path.join(REPAIRS_DIR, "excel", f"{user_id}_repairs.xlsx")
    
    if not os.path.exists(excel_path):
        bot.send_message(user_id, "❌ Файл с вашими ремонтами не найден!", parse_mode="Markdown")
        return
    
    try:
        with open(excel_path, 'rb') as excel_file:
            bot.send_document(user_id, excel_file)
    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка при отправке файла Excel!\nПопробуйте снова", parse_mode="Markdown")

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (посмотреть ремонты по категории) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Ремонты (по категориям)")
@check_function_state_decorator('Ремонты (по категориям)')
@track_usage('Ремонты (по категориям)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_repairs_by_category(message):
    user_id = message.from_user.id
    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])
    
    filtered_repairs = filter_repairs_by_transport(user_id, repairs)
    categories = sorted(set(repair["category"] for repair in filtered_repairs))
    
    if not categories:
        bot.send_message(user_id, "❌ Нет доступных категорий для выбранного транспорта!", parse_mode="Markdown")
        send_repair_menu(user_id)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*[types.KeyboardButton(category) for category in categories])
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Выберите категорию для просмотра ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_repair_category_selection)

@text_only_handler
def handle_repair_category_selection(message):
    user_id = message.from_user.id
    selected_category = message.text.strip()
    
    if selected_category in ["Вернуться в меню трат и ремонтов", "В главное меню"]:
        if selected_category == "Вернуться в меню трат и ремонтов":
            return_to_expense_and_repairs(message)
        else:
            return_to_menu(message)
        return
    
    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])
    filtered_repairs = filter_repairs_by_transport(user_id, repairs)
    
    category_repairs = [repair for repair in filtered_repairs if repair["category"] == selected_category]
    
    if not category_repairs:
        bot.send_message(user_id, f"❌ В категории *{selected_category}* ремонтов не найдено!", parse_mode="Markdown")
        send_repair_menu(user_id)
        return
    
    total_repairs_amount = 0
    repair_details = []
    
    for index, repair in enumerate(category_repairs, start=1):
        repair_name = repair.get("name", "Без названия")
        repair_date = repair.get("date", "Неизвестно")
        repair_amount = float(repair.get("amount", 0))
        total_repairs_amount += repair_amount
        
        repair_details.append(
            f"🔧 *№{index}*\n\n"
            f"📂 *Категория:* {repair['category']}\n"
            f"📌 *Название:* {repair_name}\n"
            f"📅 *Дата:* {repair_date}\n"
            f"💰 *Сумма:* {repair_amount:.2f} руб.\n"
            f"📝 *Описание:* {repair.get('description', 'Без описания')}\n"
        )
    
    message_text = f"*Ремонты* в категории *{selected_category}*:\n\n" + "\n\n".join(repair_details)
    send_message_with_split(user_id, message_text, parse_mode="Markdown")
    bot.send_message(
        user_id,
        f"Итоговая сумма ремонтов в категории *{selected_category}*: *{total_repairs_amount:.2f}* руб.",
        parse_mode="Markdown"
    )
    
    send_repair_menu(user_id)

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (посмотреть ремонты по месяцу) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Ремонты (месяц)")
@check_function_state_decorator('Ремонты (месяц)')
@track_usage('Ремонты (месяц)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_repairs_by_month(message):
    user_id = message.from_user.id
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для просмотра ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, get_repairs_by_month)

@text_only_handler
def get_repairs_by_month(message):
    user_id = message.from_user.id
    date = message.text.strip()
    
    if date == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
        return
    if date == "В главное меню":
        return_to_menu(message)
        return
    
    match = re.match(r"^(0[1-9]|1[0-2])\.(20[0-9]{2})$", date)
    if not match:
        bot.send_message(user_id, "❌ Введите корректный месяц и год в формате ММ.ГГГГ!", parse_mode="Markdown")
        bot.register_next_step_handler(message, get_repairs_by_month)
        return
    
    month, year = match.groups()
    
    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])
    filtered_repairs = filter_repairs_by_transport(user_id, repairs)
    
    total_repairs = 0
    repair_details = []
    
    for index, repair in enumerate(filtered_repairs, start=1):
        repair_date = repair.get("date", "")
        if repair_date and repair_date.split(".")[1:3] == [month, year]:
            amount = float(repair.get("amount", 0))
            total_repairs += amount
            
            repair_name = repair.get("name", "Без названия")
            description = repair.get("description", "Без описания")
            category = repair.get("category", "Без категории")
            
            repair_details.append(
                f"🔧 *№{index}*\n\n"
                f"📂 *Категория:* {category}\n"
                f"📌 *Название:* {repair_name}\n"
                f"📅 *Дата:* {repair_date}\n"
                f"💰 *Сумма:* {amount:.2f} руб.\n"
                f"📝 *Описание:* {description}\n"
            )
    
    if repair_details:
        message_text = f"*Ремонты* за *{date}* месяц:\n\n" + "\n\n".join(repair_details)
        send_message_with_split(user_id, message_text, parse_mode="Markdown")
        bot.send_message(user_id, f"Итоговая сумма ремонтов за *{date}* месяц: *{total_repairs:.2f}* руб.", parse_mode="Markdown")
    else:
        bot.send_message(user_id, f"❌ За *{date}* месяц ремонтов не найдено!", parse_mode="Markdown")
    
    send_repair_menu(user_id)

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (посмотреть ремонты по году) ---------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Ремонты (год)")
@check_function_state_decorator('Ремонты (год)')
@track_usage('Ремонты (год)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_repairs_by_year(message):
    user_id = message.from_user.id
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Вернуться в меню трат и ремонтов"))
    markup.add(types.KeyboardButton("В главное меню"))
    
    bot.send_message(user_id, "Введите год (ГГГГ) для просмотра ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, get_repairs_by_year)

@text_only_handler
def get_repairs_by_year(message):
    user_id = message.from_user.id
    year = message.text.strip()
    
    if year == "Вернуться в меню трат и ремонтов":
        return_to_expense_and_repairs(message)
        return
    if year == "В главное меню":
        return_to_menu(message)
        return
    
    if not re.match(r"^(20[0-9]{2})$", year):
        bot.send_message(user_id, "❌ Введите корректный год в формате ГГГГ!", parse_mode="Markdown")
        bot.register_next_step_handler(message, get_repairs_by_year)
        return
    
    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])
    filtered_repairs = filter_repairs_by_transport(user_id, repairs)
    
    total_repairs = 0
    repair_details = []
    
    for index, repair in enumerate(filtered_repairs, start=1):
        repair_date = repair.get("date", "")
        if repair_date and repair_date.split(".")[-1] == year:
            amount = float(repair.get("amount", 0))
            total_repairs += amount
            
            repair_name = repair.get("name", "Без названия")
            description = repair.get("description", "Без описания")
            category = repair.get("category", "Без категории")
            
            repair_details.append(
                f"🔧 *№{index}*\n\n"
                f"📂 *Категория:* {category}\n"
                f"📌 *Название:* {repair_name}\n"
                f"📅 *Дата:* {repair_date}\n"
                f"💰 *Сумма:* {amount:.2f} руб.\n"
                f"📝 *Описание:* {description}\n"
            )
    
    if repair_details:
        message_text = f"*Ремонты* за *{year}* год:\n\n" + "\n\n".join(repair_details)
        send_message_with_split(user_id, message_text, parse_mode="Markdown")
        bot.send_message(user_id, f"Итоговая сумма ремонтов за *{year}* год: *{total_repairs:.2f}* руб.", parse_mode="Markdown")
    else:
        bot.send_message(user_id, f"❌ За *{year}* год ремонтов не найдено!", parse_mode="Markdown")
    
    send_repair_menu(user_id)

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (посмотреть ремонты по все время) -------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Ремонты (все время)")
@check_function_state_decorator('Ремонты (все время)')
@track_usage('Ремонты (все время)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_all_repairs(message):
    user_id = message.from_user.id
    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])
    filtered_repairs = filter_repairs_by_transport(user_id, repairs)
    
    total_repairs = 0
    repair_details = []
    
    for index, repair in enumerate(filtered_repairs, start=1):
        amount = float(repair.get("amount", 0))
        total_repairs += amount
        
        repair_name = repair.get("name", "Без названия")
        repair_date = repair.get("date", "Неизвестно")
        description = repair.get("description", "Без описания")
        category = repair.get("category", "Без категории")
        
        repair_details.append(
            f"🔧 *№{index}*\n\n"
            f"📂 *Категория:* {category}\n"
            f"📌 *Название:* {repair_name}\n"
            f"📅 *Дата:* {repair_date}\n"
            f"💰 *Сумма:* {amount:.2f} руб.\n"
            f"📝 *Описание:* {description}\n"
        )
    
    if repair_details:
        message_text = "*Все ремонты*:\n\n" + "\n\n".join(repair_details)
        send_message_with_split(user_id, message_text, parse_mode="Markdown")
        bot.send_message(user_id, f"Итоговая сумма всех ремонтов: *{total_repairs:.2f}* руб.", parse_mode="Markdown")
    else:
        bot.send_message(user_id, "❌ Ремонтов не найдено!", parse_mode="Markdown")
    
    send_repair_menu(user_id)

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (удалить ремонты) -------------------------------------------------

selected_repair_transports = {}
repairs_to_delete_dict = {}
selected_repair_categories = {}
user_repairs_to_delete = {}

MAX_MESSAGE_LENGTH = 4096

def send_message_with_split(user_id, text, parse_mode=None):
    while len(text) > MAX_MESSAGE_LENGTH:
        bot.send_message(user_id, text[:MAX_MESSAGE_LENGTH], parse_mode=parse_mode)
        text = text[MAX_MESSAGE_LENGTH:]
    bot.send_message(user_id, text, parse_mode=parse_mode)

def format_transport_string(transport):
    if isinstance(transport, dict):
        return f"{transport.get('brand', '')} {transport.get('model', '')} ({transport.get('license_plate', '')})"
    parts = transport.split(" ")
    if len(parts) < 3:
        return None
    brand = parts[0]
    model = parts[1]
    license_plate = parts[2].strip("()")
    return {"brand": brand, "model": model, "license_plate": license_plate}

def filter_repairs_by_transport(user_id, repairs):
    selected_transport = selected_repair_transports.get(user_id) or load_repair_data(user_id).get("selected_transport", "")
    if not selected_transport:
        return []
    transport_dict = format_transport_string(selected_transport)
    if not transport_dict:
        return []
    return [
        repair for repair in repairs
        if all(
            repair.get("transport", {}).get(key) == transport_dict[key]
            for key in ["brand", "model", "license_plate"]
        )
    ]

@bot.message_handler(func=lambda message: message.text == "Удалить ремонты")
@check_function_state_decorator('Удалить ремонты')
@track_usage('Удалить ремонты')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def initiate_delete_repairs(message):
    user_id = str(message.from_user.id)
    
    transport_data = load_transport_data(user_id)
    if not transport_data:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Добавить транспорт")
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.send_message(user_id, "⚠️ У вас нет сохраненного транспорта! Хотите добавить транспорт?", reply_markup=markup)
        bot.register_next_step_handler(message, ask_add_transport)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    transport_buttons = [
        f"{transport['brand']} {transport['model']} ({transport['license_plate']})"
        for transport in transport_data
    ]
    for i in range(0, len(transport_buttons), 2):
        markup.row(*transport_buttons[i:i + 2])
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")
    
    bot.send_message(user_id, "Выберите транспорт для удаления ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_repair_transport_selection_for_deletion)

@text_only_handler
def handle_repair_transport_selection_for_deletion(message):
    user_id = str(message.from_user.id)
    selected_transport = message.text.strip()
    
    if selected_transport == "Вернуться в меню трат и ремонтов":
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if selected_transport == "В главное меню":
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_menu(message)
        return
    
    transport_data = load_transport_data(user_id)
    transport_exists = any(
        f"{t['brand']} {t['model']} ({t['license_plate']})" == selected_transport
        for t in transport_data
    )
    if not transport_exists:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        transport_buttons = [
            f"{t['brand']} {t['model']} ({t['license_plate']})"
            for t in transport_data
        ]
        for i in range(0, len(transport_buttons), 2):
            markup.row(*transport_buttons[i:i + 2])
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.send_message(user_id, "Выбранный транспорт не найден!\nПопробуйте снова", parse_mode="Markdown", reply_markup=markup)
        bot.register_next_step_handler(message, handle_repair_transport_selection_for_deletion)
        return
    
    selected_repair_transports[user_id] = selected_transport
    user_data = load_repair_data(user_id)
    user_data["selected_transport"] = selected_transport
    save_repair_data(user_id, user_data)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Del ремонты (категория)", "Del ремонты (месяц)")
    markup.add("Del ремонты (год)", "Del ремонты (все время)")
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")
    
    bot.send_message(user_id, "Выберите вариант удаления ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_repair_deletion_option)

@text_only_handler
def handle_repair_deletion_option(message):
    user_id = str(message.from_user.id)
    option = message.text.strip()
    
    if option == "Вернуться в меню трат и ремонтов":
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if option == "В главное меню":
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_menu(message)
        return
    
    selected_transport = selected_repair_transports.get(user_id, "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_repairs(message)
        return
    
    if option == "Del ремонты (категория)":
        delete_repairs_by_category(message)
    elif option == "Del ремонты (месяц)":
        delete_repairs_by_month(message)
    elif option == "Del ремонты (год)":
        delete_repairs_by_year(message)
    elif option == "Del ремонты (все время)":
        delete_all_repairs_for_selected_transport(message)
    else:
        bot.send_message(user_id, "Неверный вариант удаления!\nПопробуйте снова", parse_mode="Markdown")
        initiate_delete_repairs(message)

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (удалить ремонты по категории) -------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Del ремонты (категория)")
@check_function_state_decorator('Del ремонты (категория)')
@track_usage('Del ремонты (категория)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_repairs_by_category(message):
    user_id = str(message.from_user.id)
    user_data = load_repair_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_repairs(message)
        return
    
    try:
        transport_dict = format_transport_string(selected_transport)
        if not transport_dict:
            raise ValueError("Некорректный формат транспорта")
        selected_brand = transport_dict["brand"]
        selected_model = transport_dict["model"]
        selected_license_plate = transport_dict["license_plate"]
    except (ValueError, IndexError) as e:
        bot.send_message(user_id, "Некорректный формат выбранного транспорта!", parse_mode="Markdown")
        initiate_delete_repairs(message)
        return
    
    repairs = user_data.get(str(user_id), {}).get("repairs", [])
    filtered_repairs = filter_repairs_by_transport(user_id, repairs)
    
    if not filtered_repairs:
        bot.send_message(user_id, f"❌ Нет ремонтов для транспорта *{selected_transport}*!", parse_mode="Markdown")
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    
    categories = sorted(set(repair.get("category", "Без категории") for repair in filtered_repairs))
    
    if not categories:
        bot.send_message(user_id, f"❌ Нет категорий ремонтов для транспорта *{selected_transport}*!", parse_mode="Markdown")
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(*[types.KeyboardButton(category) for category in categories])
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")
    
    bot.send_message(user_id, "Выберите категорию для удаления ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_repair_category_selection_for_deletion)

@text_only_handler
def handle_repair_category_selection_for_deletion(message):
    user_id = str(message.from_user.id)
    selected_category = message.text.strip()
    
    if selected_category == "Вернуться в меню трат и ремонтов":
        if user_id in selected_repair_categories:
            del selected_repair_categories[user_id]
        if user_id in user_repairs_to_delete:
            del user_repairs_to_delete[user_id]
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if selected_category == "В главное меню":
        if user_id in selected_repair_categories:
            del selected_repair_categories[user_id]
        if user_id in user_repairs_to_delete:
            del user_repairs_to_delete[user_id]
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_menu(message)
        return
    
    user_data = load_repair_data(user_id)
    repairs = user_data.get(str(user_id), {}).get("repairs", [])
    filtered_repairs = filter_repairs_by_transport(user_id, repairs)
    
    if not any(repair.get("category", "Без категории") == selected_category for repair in filtered_repairs):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        categories = sorted(set(repair.get("category", "Без категории") for repair in filtered_repairs))
        markup.add(*[types.KeyboardButton(category) for category in categories])
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.send_message(user_id, f"❌ Категория *{selected_category}* не найдена!", parse_mode="Markdown", reply_markup=markup)
        bot.register_next_step_handler(message, handle_repair_category_selection_for_deletion)
        return
    
    selected_repair_categories[user_id] = selected_category
    repairs_to_delete = [
        (index + 1, repair) for index, repair in enumerate(filtered_repairs)
        if repair.get("category", "Без категории") == selected_category
    ]
    
    if not repairs_to_delete:
        bot.send_message(user_id, f"❌ Нет ремонтов в категории *{selected_category}* для транспорта!", parse_mode="Markdown")
        if user_id in selected_repair_categories:
            del selected_repair_categories[user_id]
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    
    repairs_to_delete_dict[user_id] = repairs_to_delete
    
    repair_list_text = f"Список ремонтов в категории *{selected_category}*:\n\n"
    for index, repair in repairs_to_delete:
        repair_name = repair.get("name", "Без названия")
        repair_date = repair.get("date", "Неизвестно")
        repair_list_text += f"🔧 №{index}. {repair_name} - ({repair_date})\n"
    
    repair_list_text += "Введите номер ремонта для удаления:"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")
    
    send_message_with_split(user_id, repair_list_text, parse_mode="Markdown")
    bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_delete_repair_category)

@text_only_handler
def confirm_delete_repair_category(message):
    user_id = str(message.from_user.id)
    selected_option = message.text.strip()

    if selected_option == "Вернуться в меню трат и ремонтов":
        if user_id in repairs_to_delete_dict:
            del repairs_to_delete_dict[user_id]
        if user_id in selected_repair_categories:
            del selected_repair_categories[user_id]
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if selected_option == "В главное меню":
        if user_id in repairs_to_delete_dict:
            del repairs_to_delete_dict[user_id]
        if user_id in selected_repair_categories:
            del selected_repair_categories[user_id]
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_menu(message)
        return
    if selected_option == "0":
        bot.send_message(user_id, "✅ Удаление отменено!", parse_mode="Markdown")
        if user_id in repairs_to_delete_dict:
            del repairs_to_delete_dict[user_id]
        if user_id in selected_repair_categories:
            del selected_repair_categories[user_id]
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return

    repairs_to_delete = repairs_to_delete_dict.get(user_id, [])
    if not repairs_to_delete:
        bot.send_message(user_id, "❌ Нет ремонтов для удаления по категории!", parse_mode="Markdown")
        if user_id in selected_repair_categories:
            del selected_repair_categories[user_id]
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return

    try:
        indices = [int(num.strip()) for num in selected_option.split(',')]
        valid_indices = []
        invalid_indices = []

        for index in indices:
            if any(i == index for i, _ in repairs_to_delete):
                valid_indices.append(index)
            else:
                invalid_indices.append(index)

        if not valid_indices and invalid_indices:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Вернуться в меню трат и ремонтов")
            markup.add("В главное меню")
            msg = bot.send_message(user_id, "Некорректные номера!\nПожалуйста, выберите существующие ремонты из списка", reply_markup=markup, parse_mode="Markdown")
            bot.register_next_step_handler(msg, confirm_delete_repair_category)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(user_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode="Markdown")

        deleted_repair_names = []
        user_data = load_repair_data(user_id)
        user_repairs = user_data.get(str(user_id), {}).get("repairs", [])

        for index in sorted(valid_indices, reverse=True):
            selected_repair = next((r for i, r in repairs_to_delete if i == index), None)
            if selected_repair:
                _, deleted_repair = selected_repair
                deleted_repair_names.append(deleted_repair.get('name', 'Без названия'))
                if deleted_repair in user_repairs:
                    user_repairs.remove(deleted_repair)
                repairs_to_delete.remove((index, deleted_repair))

        user_data[str(user_id)]["repairs"] = user_repairs
        save_repair_data(user_id, user_data)
        update_repairs_excel_file(user_id)

        bot.send_message(user_id, f"✅ Ремонты *{', '.join(deleted_repair_names)}* успешно удалены!", parse_mode="Markdown")

        if not repairs_to_delete:
            if user_id in repairs_to_delete_dict:
                del repairs_to_delete_dict[user_id]
            if user_id in selected_repair_categories:
                del selected_repair_categories[user_id]
            if user_id in selected_repair_transports:
                del selected_repair_transports[user_id]
        else:
            repairs_to_delete_dict[user_id] = repairs_to_delete

        return_to_expense_and_repairs(message)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        msg = bot.send_message(user_id, "Некорректный ввод!\nПожалуйста, введите номера ремонтов через запятую", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, confirm_delete_repair_category)

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (удалить ремонты по месяцу) -------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Del ремонты (месяц)")
@check_function_state_decorator('Del ремонты (месяц)')
@track_usage('Del ремонты (месяц)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_repairs_by_month(message):
    user_id = str(message.from_user.id)
    
    user_data = load_repair_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_repairs(message)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")
    
    bot.send_message(user_id, "Введите месяц и год (ММ.ГГГГ) для удаления ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_repairs_by_month_handler)

@text_only_handler
def delete_repairs_by_month_handler(message):
    user_id = str(message.from_user.id)
    month_year = message.text.strip()
    
    if month_year == "Вернуться в меню трат и ремонтов":
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if month_year == "В главное меню":
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_menu(message)
        return
    
    match = re.match(r"^(0[1-9]|1[0-2])\.(20[0-9]{2}|2[1-9][0-9]{2}|3000)$", month_year)
    if not match:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.send_message(user_id,"Введите корректный месяц и год в формате ММ.ГГГГ!", parse_mode="Markdown", reply_markup=markup)
        bot.register_next_step_handler(message, delete_repairs_by_month_handler)
        return
    
    selected_month, selected_year = map(int, match.groups())
    
    user_data = load_repair_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_repairs(message)
        return
    
    try:
        transport_dict = format_transport_string(selected_transport)
        if not transport_dict:
            raise ValueError("Некорректный формат транспорта")
        selected_brand = transport_dict["brand"]
        selected_model = transport_dict["model"]
        selected_license_plate = transport_dict["license_plate"]
    except (ValueError, IndexError) as e:
        bot.send_message(user_id, "Некорректный формат выбранного транспорта!", parse_mode="Markdown")
        initiate_delete_repairs(message)
        return
    
    repairs = user_data.get(str(user_id), {}).get("repairs", [])
    
    if not repairs:
        bot.send_message(user_id, f"❌ Нет ремонтов для транспорта *{selected_transport}*!", parse_mode="Markdown")
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    
    repairs_to_delete = []
    for index, repair in enumerate(repairs, start=1):
        repair_date = repair.get("date", "")
        if not repair_date or len(repair_date.split(".")) != 3:
            continue
        try:
            day, month, year = map(int, repair_date.split("."))
            transport = repair.get("transport", {})
            if not all(k in transport for k in ["brand", "model", "license_plate"]):
                continue
            if (month == selected_month and
                year == selected_year and
                transport["brand"] == selected_brand and
                transport["model"] == selected_model and
                transport["license_plate"] == selected_license_plate):
                repairs_to_delete.append((index, repair))
        except (ValueError, TypeError) as e:
            continue
    
    if not repairs_to_delete:
        bot.send_message(user_id, f"❌ Нет ремонтов за *{month_year}* для транспорта *{selected_transport}*!", parse_mode="Markdown")
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    
    repairs_to_delete_dict[user_id] = repairs_to_delete
    
    repair_list_text = f"Список ремонтов за *{month_year}*:\n\n"
    for index, repair in repairs_to_delete:
        repair_name = repair.get("name", "Без названия")
        repair_date = repair.get("date", "Неизвестно")
        repair_list_text += f"🔧 №{index}. {repair_name} - ({repair_date})\n"
    
    repair_list_text += "Введите номер ремонта для удаления:"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")
    
    send_message_with_split(user_id, repair_list_text, parse_mode="Markdown")
    bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_delete_repair_month)

@text_only_handler
def confirm_delete_repair_month(message):
    user_id = str(message.from_user.id)
    selected_option = message.text.strip()

    if selected_option == "Вернуться в меню трат и ремонтов":
        if user_id in repairs_to_delete_dict:
            del repairs_to_delete_dict[user_id]
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if selected_option == "В главное меню":
        if user_id in repairs_to_delete_dict:
            del repairs_to_delete_dict[user_id]
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_menu(message)
        return
    if selected_option == "0":
        bot.send_message(user_id, "✅ Удаление отменено!", parse_mode="Markdown")
        if user_id in repairs_to_delete_dict:
            del repairs_to_delete_dict[user_id]
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return

    repairs_to_delete = repairs_to_delete_dict.get(user_id, [])
    if not repairs_to_delete:
        bot.send_message(user_id, "❌ Нет ремонтов для удаления по месяцу!", parse_mode="Markdown")
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return

    try:
        indices = [int(num.strip()) for num in selected_option.split(',')]
        valid_indices = []
        invalid_indices = []

        for index in indices:
            if any(i == index for i, _ in repairs_to_delete):
                valid_indices.append(index)
            else:
                invalid_indices.append(index)

        if not valid_indices and invalid_indices:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Вернуться в меню трат и ремонтов")
            markup.add("В главное меню")
            msg = bot.send_message(user_id, "Некорректные номера!\nПожалуйста, выберите существующие ремонты из списка", reply_markup=markup, parse_mode="Markdown")
            bot.register_next_step_handler(msg, confirm_delete_repair_month)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(user_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode="Markdown")

        deleted_repair_names = []
        user_data = load_repair_data(user_id)
        user_repairs = user_data.get(str(user_id), {}).get("repairs", [])

        for index in sorted(valid_indices, reverse=True):
            selected_repair = next((r for i, r in repairs_to_delete if i == index), None)
            if selected_repair:
                _, deleted_repair = selected_repair
                deleted_repair_names.append(deleted_repair.get('name', 'Без названия'))
                if deleted_repair in user_repairs:
                    user_repairs.remove(deleted_repair)
                repairs_to_delete.remove((index, deleted_repair))

        user_data[str(user_id)]["repairs"] = user_repairs
        save_repair_data(user_id, user_data)
        update_repairs_excel_file(user_id)

        bot.send_message(user_id, f"✅ Ремонты *{', '.join(deleted_repair_names)}* успешно удалены!", parse_mode="Markdown")

        if not repairs_to_delete:
            if user_id in repairs_to_delete_dict:
                del repairs_to_delete_dict[user_id]
            if user_id in selected_repair_transports:
                del selected_repair_transports[user_id]
        else:
            repairs_to_delete_dict[user_id] = repairs_to_delete

        return_to_expense_and_repairs(message)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        msg = bot.send_message(user_id, "Некорректный ввод!\nПожалуйста, введите номера ремонтов через запятую", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, confirm_delete_repair_month)

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (удалить ремонты по году) -------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Del ремонты (год)")
@check_function_state_decorator('Del ремонты (год)')
@track_usage('Del ремонты (год)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_repairs_by_year(message):
    user_id = str(message.from_user.id)
    
    user_data = load_repair_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_repairs(message)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")
    
    bot.send_message(user_id, "Введите год (ГГГГ) для удаления ремонтов:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_repairs_by_year_handler)

@text_only_handler
def delete_repairs_by_year_handler(message):
    user_id = str(message.from_user.id)
    year = message.text.strip()
    
    if year == "Вернуться в меню трат и ремонтов":
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if year == "В главное меню":
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_menu(message)
        return
    
    if not re.match(r"^(20[0-9]{2}|2[1-9][0-9]{2}|3000)$", year):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.send_message(user_id, "Введите корректный год в формате ГГГГ!", parse_mode="Markdown", reply_markup=markup)
        bot.register_next_step_handler(message, delete_repairs_by_year_handler)
        return
    
    user_data = load_repair_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_repairs(message)
        return
    
    try:
        transport_dict = format_transport_string(selected_transport)
        if not transport_dict:
            raise ValueError("Некорректный формат транспорта")
        selected_brand = transport_dict["brand"]
        selected_model = transport_dict["model"]
        selected_license_plate = transport_dict["license_plate"]
    except (ValueError, IndexError) as e:
        bot.send_message(user_id, "Некорректный формат выбранного транспорта!", parse_mode="Markdown")
        initiate_delete_repairs(message)
        return
    
    repairs = user_data.get(str(user_id), {}).get("repairs", [])
    
    if not repairs:
        bot.send_message(user_id, f"❌ Нет ремонтов для транспорта *{selected_transport}*!", parse_mode="Markdown")
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    
    repairs_to_delete = []
    for index, repair in enumerate(repairs, start=1):
        repair_date = repair.get("date", "")
        if not repair_date or len(repair_date.split(".")) != 3:
            continue
        try:
            day, month, repair_year = map(int, repair_date.split("."))
            transport = repair.get("transport", {})
            if not all(k in transport for k in ["brand", "model", "license_plate"]):
                continue
            if (repair_year == int(year) and
                transport["brand"] == selected_brand and
                transport["model"] == selected_model and
                transport["license_plate"] == selected_license_plate):
                repairs_to_delete.append((index, repair))
        except (ValueError, TypeError) as e:
            continue
    
    if not repairs_to_delete:
        bot.send_message(user_id, f"❌ Нет ремонтов за *{year}* для транспорта *{selected_transport}*!", parse_mode="Markdown")
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    
    repairs_to_delete_dict[user_id] = repairs_to_delete
    
    repair_list_text = f"Список ремонтов за *{year}*:\n\n"
    for index, repair in repairs_to_delete:
        repair_name = repair.get("name", "Без названия")
        repair_date = repair.get("date", "Неизвестно")
        repair_list_text += f"🔧 №{index}. {repair_name} - ({repair_date})\n"
    
    repair_list_text += "Введите номер ремонта для удаления:"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")
    
    send_message_with_split(user_id, repair_list_text, parse_mode="Markdown")
    bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_delete_repair_year)

@text_only_handler
def confirm_delete_repair_year(message):
    user_id = str(message.from_user.id)
    selected_option = message.text.strip()

    if selected_option == "Вернуться в меню трат и ремонтов":
        if user_id in repairs_to_delete_dict:
            del repairs_to_delete_dict[user_id]
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if selected_option == "В главное меню":
        if user_id in repairs_to_delete_dict:
            del repairs_to_delete_dict[user_id]
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_menu(message)
        return
    if selected_option == "0":
        bot.send_message(user_id, "✅ Удаление отменено!", parse_mode="Markdown")
        if user_id in repairs_to_delete_dict:
            del repairs_to_delete_dict[user_id]
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return

    repairs_to_delete = repairs_to_delete_dict.get(user_id, [])
    if not repairs_to_delete:
        bot.send_message(user_id, "❌ Нет ремонтов для удаления по году!", parse_mode="Markdown")
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return

    try:
        indices = [int(num.strip()) for num in selected_option.split(',')]
        valid_indices = []
        invalid_indices = []

        for index in indices:
            if any(i == index for i, _ in repairs_to_delete):
                valid_indices.append(index)
            else:
                invalid_indices.append(index)

        if not valid_indices and invalid_indices:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Вернуться в меню трат и ремонтов")
            markup.add("В главное меню")
            msg = bot.send_message(user_id, "Некорректные номера!\nПожалуйста, выберите существующие ремонты из списка", reply_markup=markup, parse_mode="Markdown")
            bot.register_next_step_handler(msg, confirm_delete_repair_year)
            return

        if invalid_indices:
            invalid_str = ",".join(map(str, invalid_indices))
            bot.send_message(user_id, f"❌ Некорректные номера `{invalid_str}`! Они будут пропущены...", parse_mode="Markdown")

        deleted_repair_names = []
        user_data = load_repair_data(user_id)
        user_repairs = user_data.get(str(user_id), {}).get("repairs", [])

        for index in sorted(valid_indices, reverse=True):
            selected_repair = next((r for i, r in repairs_to_delete if i == index), None)
            if selected_repair:
                _, deleted_repair = selected_repair
                deleted_repair_names.append(deleted_repair.get('name', 'Без названия'))
                if deleted_repair in user_repairs:
                    user_repairs.remove(deleted_repair)
                repairs_to_delete.remove((index, deleted_repair))

        user_data[str(user_id)]["repairs"] = user_repairs
        save_repair_data(user_id, user_data)
        update_repairs_excel_file(user_id)

        bot.send_message(user_id, f"✅ Ремонты *{', '.join(deleted_repair_names)}* успешно удалены!", parse_mode="Markdown")

        if not repairs_to_delete:
            if user_id in repairs_to_delete_dict:
                del repairs_to_delete_dict[user_id]
            if user_id in selected_repair_transports:
                del selected_repair_transports[user_id]
        else:
            repairs_to_delete_dict[user_id] = repairs_to_delete

        return_to_expense_and_repairs(message)

    except ValueError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        msg = bot.send_message(user_id, "Некорректный ввод!\nПожалуйста, введите номера ремонтов через запятую", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, confirm_delete_repair_year)

# ----------------------------------------- ТРАТЫ И РЕМОНТЫ (удалить ремонты по все время) -------------------------------------------------

@bot.message_handler(func=lambda message: message.text == "Del ремонты (все время)")
@check_function_state_decorator('Del ремонты (все время)')
@track_usage('Del ремонты (все время)')
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_all_repairs_for_selected_transport(message):
    user_id = str(message.from_user.id)
    
    user_data = load_repair_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_repairs(message)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Да", "Нет")
    markup.add("Вернуться в меню трат и ремонтов")
    markup.add("В главное меню")
    
    bot.send_message(user_id, f"⚠️ Вы уверены, что хотите удалить все ремонты для транспорта *{selected_transport}*?\n\n"
        "Пожалуйста, введите *Да* для подтверждения или *Нет* для отмены", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, confirm_delete_all_repairs)

@text_only_handler
def confirm_delete_all_repairs(message):
    user_id = str(message.from_user.id)
    response = message.text.strip().lower()
    
    if response == "вернуться в меню трат и ремонтов":
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_expense_and_repairs(message)
        return
    if response == "в главное меню":
        if user_id in selected_repair_transports:
            del selected_repair_transports[user_id]
        return_to_menu(message)
        return
    
    user_data = load_repair_data(user_id)
    selected_transport = user_data.get("selected_transport", "")
    if not selected_transport:
        bot.send_message(user_id, "❌ Транспорт не выбран!", parse_mode="Markdown")
        initiate_delete_repairs(message)
        return
    
    try:
        transport_dict = format_transport_string(selected_transport)
        if not transport_dict:
            raise ValueError("Некорректный формат транспорта")
        selected_brand = transport_dict["brand"]
        selected_model = transport_dict["model"]
        selected_license_plate = transport_dict["license_plate"]
    except (ValueError, IndexError) as e:
        bot.send_message(user_id, "Некорректный формат выбранного транспорта!", parse_mode="Markdown")
        initiate_delete_repairs(message)
        return
    
    if response == "да":
        repairs = user_data.get(str(user_id), {}).get("repairs", [])
        if not repairs:
            bot.send_message(user_id, f"❌ Нет ремонтов для транспорта *{selected_transport}*!", parse_mode="Markdown")
            if user_id in selected_repair_transports:
                del selected_repair_transports[user_id]
            return_to_expense_and_repairs(message)
            return
        
        repairs_to_keep = []
        for repair in repairs:
            transport = repair.get("transport", {})
            if not all(k in transport for k in ["brand", "model", "license_plate"]):
                repairs_to_keep.append(repair)
                continue
            if not (transport["brand"] == selected_brand and
                    transport["model"] == selected_model and
                    transport["license_plate"] == selected_license_plate):
                repairs_to_keep.append(repair)
        
        user_data[str(user_id)]["repairs"] = repairs_to_keep
        save_repair_data(user_id, user_data)
        update_repairs_excel_file(user_id)
        
        bot.send_message(user_id, f"✅ Все ремонты для транспорта *{selected_transport}* успешно удалены!", parse_mode="Markdown")
    elif response == "нет":
        bot.send_message(user_id, "✅ Удаление отменено!", parse_mode="Markdown")
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Да", "Нет")
        markup.add("Вернуться в меню трат и ремонтов")
        markup.add("В главное меню")
        bot.send_message(user_id, "Пожалуйста, введите *да* для подтверждения или *нет* для отмены", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(message, confirm_delete_all_repairs)
        return
    
    if user_id in selected_repair_transports:
        del selected_repair_transports[user_id]
    return_to_expense_and_repairs(message)

def update_repairs_excel_file(user_id):
    user_id = str(user_id)
    user_data = load_repair_data(user_id)
    repairs = user_data.get(user_id, {}).get("repairs", [])
    excel_file_path = os.path.join(BASE_DIR, "data", "user", "expenses_and_repairs", "repairs", "excel", f"{user_id}_repairs.xlsx")
    
    try:
        if not os.path.exists(excel_file_path):
            workbook = openpyxl.Workbook()
            workbook.remove(workbook.active)
        else:
            workbook = openpyxl.load_workbook(excel_file_path)
        
        headers = ["Транспорт", "Категория", "Название", "Дата", "Сумма", "Описание"]
        summary_sheet = workbook["Summary"] if "Summary" in workbook.sheetnames else workbook.create_sheet("Summary")
        
        if summary_sheet.max_row > 1:
            summary_sheet.delete_rows(2, summary_sheet.max_row - 1)
        if summary_sheet.max_row == 0:
            summary_sheet.append(headers)
            for cell in summary_sheet[1]:
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal="center")
        
        unique_transports = set()
        valid_repairs = []
        for repair in repairs:
            transport = repair.get("transport", {})
            if not all(k in transport for k in ['brand', 'model', 'license_plate']):
                continue
            unique_transports.add((transport["brand"], transport["model"], transport["license_plate"]))
            valid_repairs.append(repair)
        
        for repair in valid_repairs:
            transport = repair["transport"]
            row_data = [
                f"{transport['brand']} {transport['model']} ({transport['license_plate']})",
                repair.get("category", "Без категории"),
                repair.get("name", "Без названия"),
                repair.get("date", ""),
                float(repair.get("amount", 0)),
                repair.get("description", ""),
            ]
            summary_sheet.append(row_data)
        
        for sheet_name in workbook.sheetnames:
            if sheet_name != "Summary":
                try:
                    brand, model, license_plate = sheet_name.split('_')
                    if (brand, model, license_plate) not in unique_transports:
                        del workbook[sheet_name]
                except ValueError:
                    continue
        
        for brand, model, license_plate in unique_transports:
            sheet_name = f"{brand}_{model}_{license_plate}"[:31]
            transport_sheet = workbook[sheet_name] if sheet_name in workbook.sheetnames else workbook.create_sheet(sheet_name)
            
            if transport_sheet.max_row > 1:
                transport_sheet.delete_rows(2, transport_sheet.max_row - 1)
            if transport_sheet.max_row == 0:
                transport_sheet.append(headers)
                for cell in transport_sheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal="center")
            
            for repair in valid_repairs:
                transport = repair["transport"]
                if (transport["brand"], transport["model"], transport["license_plate"]) == (brand, model, license_plate):
                    row_data = [
                        f"{brand} {model} ({license_plate})",
                        repair.get("category", "Без категории"),
                        repair.get("name", "Без названия"),
                        repair.get("date", ""),
                        float(repair.get("amount", 0)),
                        repair.get("description", ""),
                    ]
                    transport_sheet.append(row_data)
        
        for sheet in workbook:
            for col in sheet.columns:
                max_length = max(len(str(cell.value)) for cell in col if cell.value) + 2
                sheet.column_dimensions[get_column_letter(col[0].column)].width = max_length
        
        workbook.save(excel_file_path)
        workbook.close()
    
    except Exception as e:
        bot.send_message(user_id, "Ошибка при обновлении Excel-файла ремонтов!", parse_mode="Markdown")