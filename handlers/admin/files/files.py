from core.imports import wraps, telebot, types, os, json, re, html
from core.bot_instance import bot, BASE_DIR
from handlers.admin.admin_main_menu import check_permission, show_admin_panel
from ..utils import (
    restricted, track_user_activity, check_chat_state, check_user_blocked,
    log_user_actions, check_subscription_chanal, text_only_handler,
    rate_limit_with_captcha
)

# ------------------------------------------------------- ФАЙЛЫ ----------------------------------------------

TELEGRAM_MESSAGE_LIMIT = 4096
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
FILES_PATH = os.path.join(BASE_DIR, 'data')
ADDITIONAL_FILES_PATH = os.path.join(BASE_DIR, 'files')
EXCLUDED_DIRS = {'.vscode', 'venv', '.venv', '__pycache__'}
ADMIN_SESSIONS_FILE = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'admin_sessions.json')
USER_DATA_PATH = os.path.join(BASE_DIR, 'data', 'admin', 'admin_user_payments', 'users.json')
bot_data = {}
temp_replace_files = {}
temp_add_files = {}


def _is_excluded_dir(name: str) -> bool:
    return name.startswith('.') or name in EXCLUDED_DIRS

def escape_markdown(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def load_user_data():
    with open(USER_DATA_PATH, 'r', encoding='utf-8') as file:
        return json.load(file)

def load_admin_sessions():
    with open(ADMIN_SESSIONS_FILE, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data['admin_sessions']

def check_admin_access(message):
    admin_sessions = load_admin_sessions()
    if str(message.chat.id) in admin_sessions:
        return True
    else:
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return False

@bot.message_handler(func=lambda message: message.text == 'Файлы' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def show_files_menu(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Файлы'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add('Поиск по EXT', 'Поиск по DIR', 'Поиск по ID')
    markup.add('Добавить файлы', 'Замена файлов', 'Удалить файлы')
    markup.add('В меню админ-панели')

    bot.send_message(message.chat.id, "Выберите действие с файлами:", reply_markup=markup)

# ------------------------------------------------------- ФАЙЛЫ (поиск по ext) ----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Поиск по EXT' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def view_files(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Поиск по EXT'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    files_list = []
    extensions = set()

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if not _is_excluded_dir(d)]
        for file_name in files:
            if not file_name.startswith('.'): 
                file_path = os.path.join(root, file_name)
                files_list.append(file_path)
                extension = os.path.splitext(file_name)[1]
                extensions.add(extension)

    if not files_list:
        bot.send_message(message.chat.id, "❌ Файлы не найдены!")
        return

    sorted_extensions = sorted(extensions)
    response = "*Список расширений файлов:*\n\n"
    response += "📁 1. *Отправка всех файлов*\n"
    response += "\n".join([f"📄 {i + 2}. *{ext[1:]}*" for i, ext in enumerate(sorted_extensions)])

    bot_data[message.chat.id] = {
        "files_list": files_list,
        "extensions": sorted_extensions
    }

    for start in range(0, len(response), TELEGRAM_MESSAGE_LIMIT):
        bot.send_message(message.chat.id, response[start:start + TELEGRAM_MESSAGE_LIMIT], parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню файлы')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер для выбора расширения:", reply_markup=markup)
    bot.register_next_step_handler(message, process_extension_selection)

@text_only_handler
def process_extension_selection(message):
    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    try:
        selection = int(message.text.strip())
        if selection == 1:
            files_list = bot_data[message.chat.id]["files_list"]
            selected_extension = None
        else:
            extensions = bot_data[message.chat.id]["extensions"]
            if 1 < selection <= len(extensions) + 1:
                selected_extension = extensions[selection - 2]
                files_list = [file for file in bot_data[message.chat.id]["files_list"] if file.endswith(selected_extension)]
            else:
                bot.send_message(message.chat.id, "Некорректный номер!")
                bot.register_next_step_handler(message, process_extension_selection)
                return

        if files_list:
            if selected_extension:
                response = f"Показаны файлы с расширением {selected_extension[1:]}:\n\n"
            else:
                response = "Показаны все файлы:\n\n"

            response += "\n".join([f"📄 {i + 1}. {os.path.basename(file_path)}" for i, file_path in enumerate(files_list)])
            for start in range(0, len(response), TELEGRAM_MESSAGE_LIMIT):
                bot.send_message(message.chat.id, response[start:start + TELEGRAM_MESSAGE_LIMIT])
            bot.send_message(message.chat.id, "Введите номера файлов через запятую для отправки:")
            bot.register_next_step_handler(message, process_file_selection, files_list)
        else:
            bot.send_message(message.chat.id, "❌ Файлы с выбранным расширением не найдены!")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите номер!")
        bot.register_next_step_handler(message, process_extension_selection)

@text_only_handler
def process_file_selection(message, matched_files):
    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    try:
        file_numbers = [int(num.strip()) - 1 for num in message.text.split(',')]
        valid_files = [matched_files[num] for num in file_numbers if 0 <= num < len(matched_files)]

        if valid_files:
            for file_path in valid_files:
                with open(file_path, 'rb') as file:
                    bot.send_document(message.chat.id, file)
            show_files_menu(message)
        else:
            bot.send_message(message.chat.id, "Некорректные номера файлов!")
            bot.register_next_step_handler(message, process_file_selection, matched_files)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите номера файлов через запятую!")
        bot.register_next_step_handler(message, process_file_selection, matched_files)

# ------------------------------------------------------- ФАЙЛЫ (поиск по dir) ----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Поиск по DIR' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def search_files_in_directory(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Поиск по DIR'):
        bot.send_message(message.chat.id, "⛔️ У вас <b>нет прав доступа</b> к этой функции!", parse_mode="HTML")
        return

    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    directories = [BASE_DIR, FILES_PATH, ADDITIONAL_FILES_PATH, BACKUP_DIR]
    response = "<b>Список директорий:</b>\n\n"
    response += "\n\n".join([f"📁 {i + 1}. {html.escape(os.path.normpath(dir))}" for i, dir in enumerate(directories)])
    bot.send_message(message.chat.id, response, parse_mode="HTML")

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню файлы')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите директорию для просмотра содержимого:", reply_markup=markup, parse_mode="HTML")
    bot.register_next_step_handler(message, process_directory_selection_for_search)

@text_only_handler
def process_directory_selection_for_search(message):
    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    try:
        selection = int(message.text.strip())
        directories = [BASE_DIR, FILES_PATH, ADDITIONAL_FILES_PATH, BACKUP_DIR]
        if 1 <= selection <= len(directories):
            selected_directory = directories[selection - 1]
            bot_data[message.chat.id] = {"directory_history": [selected_directory]}
            display_directory_contents(message, selected_directory)
        else:
            bot.send_message(message.chat.id, "Некорректный номер!", parse_mode="HTML")
            bot.register_next_step_handler(message, process_directory_selection_for_search)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите номер!", parse_mode="HTML")
        bot.register_next_step_handler(message, process_directory_selection_for_search)

def display_directory_contents(message, current_directory):
    files_list = []
    folders_list = []

    for item in os.listdir(current_directory):
        item_path = os.path.join(current_directory, item)
        if not item.startswith('.'):  
            if os.path.isfile(item_path):
                files_list.append(item_path)
            elif os.path.isdir(item_path):
                if not _is_excluded_dir(os.path.basename(item_path)):
                    folders_list.append(item_path)

    if not files_list and not folders_list:
        bot.send_message(message.chat.id, "❌ В этой директории нет файлов или папок!", parse_mode="HTML")
        show_files_menu(message)
        return

    response = f"<b>Содержимое директории <code>{html.escape(os.path.normpath(current_directory))}</code>:</b>\n\n"
    response += "↩️ 0. Назад\n\n"
    combined_list = folders_list + files_list
    for i, item_path in enumerate(combined_list):
        item_name = os.path.basename(item_path)
        if item_path in folders_list:
            response += f"📁 {i + 1}. {html.escape(item_name)}\n"
        else:
            response += f"📄 {i + 1}. {html.escape(item_name)}\n"

    bot_data[message.chat.id]["current_directory"] = current_directory
    bot_data[message.chat.id]["combined_list"] = combined_list
    bot_data[message.chat.id]["folders_list"] = folders_list
    bot_data[message.chat.id]["files_list"] = files_list

    for start in range(0, len(response), TELEGRAM_MESSAGE_LIMIT):
        bot.send_message(message.chat.id, response[start:start + TELEGRAM_MESSAGE_LIMIT], parse_mode="HTML")

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню файлы')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите номер папки или номера файлов для просмотра:", reply_markup=markup, parse_mode="HTML")
    bot.register_next_step_handler(message, process_item_selection)

@text_only_handler
def process_item_selection(message):
    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    try:
        input_text = message.text.strip()
        if input_text == '0':
            directory_history = bot_data[message.chat.id].get("directory_history", [])
            if len(directory_history) > 1:
                directory_history.pop()
                previous_directory = directory_history[-1]
                bot_data[message.chat.id]["directory_history"] = directory_history
                display_directory_contents(message, previous_directory)
            else:
                search_files_in_directory(message)
            return

        if ',' in input_text:
            file_numbers = [int(num.strip()) - 1 for num in input_text.split(',')]
            combined_list = bot_data[message.chat.id]["combined_list"]
            files_list = bot_data[message.chat.id]["files_list"]
            valid_files = [combined_list[num] for num in file_numbers if 0 <= num < len(combined_list) and combined_list[num] in files_list]

            if valid_files:
                for file_path in valid_files:
                    with open(file_path, 'rb') as file:
                        bot.send_document(message.chat.id, file)
                bot.send_message(message.chat.id, "✅ Файлы отправлены!", parse_mode="HTML")
                show_files_menu(message) 
            else:
                bot.send_message(message.chat.id, "Некорректные номера файлов!", parse_mode="HTML")
                bot.register_next_step_handler(message, process_item_selection)
        else:
            selection = int(input_text) - 1
            combined_list = bot_data[message.chat.id]["combined_list"]
            folders_list = bot_data[message.chat.id]["folders_list"]

            if 0 <= selection < len(combined_list):
                selected_item = combined_list[selection]
                if selected_item in folders_list:
                    bot_data[message.chat.id]["directory_history"].append(selected_item)
                    display_directory_contents(message, selected_item)
                else:
                    with open(selected_item, 'rb') as file:
                        bot.send_document(message.chat.id, file)
                    bot.send_message(message.chat.id, "✅ Файл отправлен!", parse_mode="HTML")
                    show_files_menu(message)  
            else:
                bot.send_message(message.chat.id, "Некорректный номер!", parse_mode="HTML")
                bot.register_next_step_handler(message, process_item_selection)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите номер папки или номера файлов!", parse_mode="HTML")
        bot.register_next_step_handler(message, process_item_selection)

# ------------------------------------------------------- ФАЙЛЫ (поиск по id) ----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Поиск по ID' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def search_files_by_id(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Поиск по ID'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню файлы')
    markup.add('В меню админ-панели')
    list_users_for_files(message)

def list_users_for_files(message):
    users_data = load_user_data()
    user_list = []
    for user_id, data in users_data.items():
        username = escape_markdown(data['username'])
        status = " - *заблокирован* 🚫" if data.get('blocked', False) else " - *разблокирован* ✅"
        user_list.append(f"№{len(user_list) + 1}. {username} - `{user_id}`{status}")

    response_message = "📋 Список *всех* пользователей:\n\n" + "\n\n".join(user_list)
    if len(response_message) > 4096:
        bot.send_message(message.chat.id, "📜 Список пользователей слишком большой для отправки в одном сообщении!")
    else:
        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню файлы')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Введите *номер* пользователя, *username* или *id* для поиска файлов:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_user_input_for_file_search)

@text_only_handler
def process_user_input_for_file_search(message):
    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    user_input = message.text.strip()
    users_data = load_user_data()

    user_id = None
    username = None

    if user_input.isdigit():
        if len(user_input) < 4:
            user_index = int(user_input) - 1
            if 0 <= user_index < len(users_data):
                user_id = list(users_data.keys())[user_index]
                username = users_data[user_id]['username']
            else:
                bot.send_message(message.chat.id, "Некорректный номер пользователя!")
                bot.register_next_step_handler(message, process_user_input_for_file_search)
                return
        else:
            if user_input in users_data:
                user_id = user_input
                username = users_data[user_id]['username']
            else:
                bot.send_message(message.chat.id, "Пользователь с таким *id* не найден!", parse_mode="Markdown")
                bot.register_next_step_handler(message, process_user_input_for_file_search)
                return
    elif user_input.startswith('@'):
        username = user_input
        user_id = next((user_id for user_id, data in users_data.items() if data['username'].lower() == username.lower()), None)
        if not user_id:
            bot.send_message(message.chat.id, "Пользователь с таким *username* не найден!", parse_mode="Markdown")
            bot.register_next_step_handler(message, process_user_input_for_file_search)
            return
    else:
        bot.send_message(message.chat.id, "Некорректный ввод! Пожалуйста, введите номер, username или id")
        bot.register_next_step_handler(message, process_user_input_for_file_search)
        return

    bot.send_message(message.chat.id, f"Поиск файлов для пользователя: {escape_markdown(username)} - `{user_id}` ...", parse_mode="Markdown")
    process_file_search(message, user_id)

def search_id_in_json(data, user_id):
    if isinstance(data, dict):
        for key, value in data.items():
            if key == user_id or (isinstance(value, str) and user_id in value):
                return True
            if search_id_in_json(value, user_id):
                return True
    elif isinstance(data, list):
        for item in data:
            if search_id_in_json(item, user_id):
                return True
    return False

def process_file_search(message, user_id):
    matched_files = []

    search_paths = [BASE_DIR, BACKUP_DIR, FILES_PATH, ADDITIONAL_FILES_PATH]

    for search_path in search_paths:
        for root, dirs, files in os.walk(search_path):
            dirs[:] = [d for d in dirs if not _is_excluded_dir(d)]
            for file_name in files:
                if not file_name.startswith('.'):
                    file_path = os.path.join(root, file_name)
                    if user_id in file_name:
                        matched_files.append(file_path)
                    else:
                        if file_name.endswith('.json'):
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = json.load(f)
                                    if search_id_in_json(content, user_id):
                                        matched_files.append(file_path)
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                pass
                        elif file_name.endswith(('.txt', '.log', '.csv')):
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    if re.search(rf'\b{user_id}\b', content):
                                        matched_files.append(file_path)
                            except UnicodeDecodeError:
                                pass

    if matched_files:
        response = "\n".join([f"📄 {i + 1}. {os.path.basename(path)}" for i, path in enumerate(matched_files)])
        for start in range(0, len(response), TELEGRAM_MESSAGE_LIMIT):
            bot.send_message(message.chat.id, response[start:start + TELEGRAM_MESSAGE_LIMIT])
        bot.send_message(message.chat.id, "Выберите номера файлов через запятую для отправки:")
        bot.register_next_step_handler(message, process_file_selection, matched_files)
    else:
        bot.send_message(message.chat.id, "❌ Файлы с указанным id не найдены!")

# ------------------------------------------------------- ФАЙЛЫ (замена файлов) ----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Замена файлов' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def handle_file_replacement(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Замена файлов'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    temp_replace_files[message.chat.id] = []
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню файлы')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Отправьте новый файл для замены:", reply_markup=markup)
    bot.register_next_step_handler(message, process_file_replacement)

def process_file_replacement(message):
    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    if message.document:
        file_name = message.document.file_name
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        temp_replace_files[message.chat.id].append((file_name, downloaded_file))
        bot.send_message(message.chat.id, "Файл добавлен во временное хранилище!")

        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)  
        markup.add('Добавить еще файл', 'Завершить замену файлов')  
        markup.add('В меню файлы')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Выберите действие из замены файлов:", reply_markup=markup)
        bot.register_next_step_handler(message, process_file_replacement_action)
    else:
        bot.send_message(message.chat.id, "Неверный формат! Пожалуйста, отправьте файл в формате документа")
        bot.register_next_step_handler(message, process_file_replacement)

def process_file_replacement_action(message):
    if message.text == 'Добавить еще файл':
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add('В меню файлы')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Отправьте следующий файл для замены:", reply_markup=markup)
        bot.register_next_step_handler(message, process_file_replacement)
    elif message.text == 'Завершить замену файлов':
        search_paths = [BASE_DIR, FILES_PATH, ADDITIONAL_FILES_PATH, BACKUP_DIR]
        replaced_files = []
        not_found_files = []

        for file_name, file_content in temp_replace_files[message.chat.id]:
            file_path = None
            for search_path in search_paths:
                for root, dirs, files in os.walk(search_path):
                    dirs[:] = [d for d in dirs if not _is_excluded_dir(d)]
                    if file_name in files and not file_name.startswith('.'): 
                        file_path = os.path.join(root, file_name)
                        break
                if file_path:
                    break

            if file_path:
                with open(file_path, 'wb') as new_file:
                    new_file.write(file_content)
                replaced_files.append(file_name)
            else:
                not_found_files.append(file_name)

        if replaced_files:
            bot.send_message(message.chat.id, f"✅ Файлы успешно заменены: {', '.join(replaced_files)}")
        if not_found_files:
            bot.send_message(message.chat.id, f"❌ Файлы для замены не найдены: {', '.join(not_found_files)}")

        show_files_menu(message)
    elif message.text == 'В меню админ-панели':
        show_admin_panel(message)
    elif message.text == 'В меню файлы':
        show_files_menu(message)
    else:
        bot.send_message(message.chat.id, "Неверное действие! Пожалуйста, выберите правильное действие")
        bot.register_next_step_handler(message, process_file_replacement_action)

# ------------------------------------------------------- ФАЙЛЫ (добавить файлы) ----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Добавить файлы' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def add_files(message):
    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Добавить файлы'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    directories = [BASE_DIR, FILES_PATH, ADDITIONAL_FILES_PATH, BACKUP_DIR]
    response = "*Список директорий:*\n\n"
    response += "\n\n".join([f"📁 {i + 1}. {escape_markdown(dir)}" for i, dir in enumerate(directories)])
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню файлы')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите директорию для добавления файлов:", reply_markup=markup)
    bot.register_next_step_handler(message, process_add_file_directory_selection)

@text_only_handler
def process_add_file_directory_selection(message):
    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    try:
        selection = int(message.text.strip())
        directories = [BASE_DIR, FILES_PATH, ADDITIONAL_FILES_PATH, BACKUP_DIR]
        if 1 <= selection <= len(directories):
            selected_directory = directories[selection - 1]
            bot_data[message.chat.id] = {
                "directory_history": [selected_directory]
            }
            navigate_and_select_folder(message, selected_directory)
        else:
            bot.send_message(message.chat.id, "Некорректный номер!")
            bot.register_next_step_handler(message, process_add_file_directory_selection)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите номер!")
        bot.register_next_step_handler(message, process_add_file_directory_selection)

def navigate_and_select_folder(message, current_directory):
    folders_list = []
    for item in os.listdir(current_directory):
        item_path = os.path.join(current_directory, item)
        if not item.startswith('.') and os.path.isdir(item_path):
            if not _is_excluded_dir(os.path.basename(item_path)):
                folders_list.append(item_path)

    bot_data[message.chat.id]["current_directory"] = current_directory
    bot_data[message.chat.id]["folders_list"] = folders_list

    response = f"*Текущая директория:* `{escape_markdown(current_directory)}`\n\n"
    response += "↩️ 0. Назад\n\n"
    for i, folder in enumerate(folders_list):
        response += f"📁 {i + 1}. {escape_markdown(os.path.basename(folder))}\n"

    for start in range(0, len(response), TELEGRAM_MESSAGE_LIMIT):
        bot.send_message(message.chat.id, response[start:start + TELEGRAM_MESSAGE_LIMIT], parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('Выбрать эту папку')
    markup.add('В меню файлы')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите папку для добавления:", reply_markup=markup)
    bot.register_next_step_handler(message, process_folder_selection)

@text_only_handler
def process_folder_selection(message):
    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    if message.text == 'Выбрать эту папку':
        current_directory = bot_data[message.chat.id]["current_directory"]
        bot_data[message.chat.id]["selected_directory"] = current_directory
        temp_add_files[message.chat.id] = []

        hide_markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, f"📂 *Вы выбрали директорию:*\n`{escape_markdown(current_directory)}`", parse_mode="Markdown", reply_markup=hide_markup)
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add('В меню файлы')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Отправьте файл для добавления:", reply_markup=markup)
        bot.register_next_step_handler(message, process_add_file)
        return

    try:
        input_text = message.text.strip()
        if input_text == '0':
            history = bot_data[message.chat.id].get("directory_history", [])
            if len(history) > 1:
                history.pop()
                previous_dir = history[-1]
                bot_data[message.chat.id]["directory_history"] = history
                navigate_and_select_folder(message, previous_dir)
            else:
                add_files(message)
            return

        selection = int(input_text) - 1
        folders_list = bot_data[message.chat.id]["folders_list"]
        if 0 <= selection < len(folders_list):
            selected_folder = folders_list[selection]
            bot_data[message.chat.id]["directory_history"].append(selected_folder)
            navigate_and_select_folder(message, selected_folder)
        else:
            bot.send_message(message.chat.id, "Некорректный номер!")
            bot.register_next_step_handler(message, process_folder_selection)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите номер папки или выберите текущую!")
        bot.register_next_step_handler(message, process_folder_selection)

def process_add_file(message):
    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    if message.document:
        file_name = message.document.file_name
        selected_directory = bot_data[message.chat.id]["selected_directory"]
        file_path = os.path.join(selected_directory, file_name)

        if os.path.exists(file_path):
            bot.send_message(message.chat.id, "❌ Файл с таким именем уже существует! Пожалуйста, отправьте файл с другим именем")
            bot.register_next_step_handler(message, process_add_file)
        else:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            temp_add_files[message.chat.id].append((file_name, downloaded_file))
            bot.send_message(message.chat.id, "Файл добавлен во временное хранилище!")

            markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True) 
            markup.add('Добавить еще файл', 'Завершить добавление файлов')  
            markup.add('В меню файлы')
            markup.add('В меню админ-панели')
            bot.send_message(message.chat.id, "Выберите действие из добавления файлов:", reply_markup=markup)
            bot.register_next_step_handler(message, process_add_file_action)
    else:
        bot.send_message(message.chat.id, "Неверный формат! Пожалуйста, отправьте файл в формате документа")
        bot.register_next_step_handler(message, process_add_file)

def process_add_file_action(message):
    if message.text == 'Добавить еще файл':
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add('В меню файлы')
        markup.add('В меню админ-панели')
        bot.send_message(message.chat.id, "Отправьте следующий файл для добавления:", reply_markup=markup)
        bot.register_next_step_handler(message, process_add_file)
    elif message.text == 'Завершить добавление файлов':
        selected_directory = bot_data[message.chat.id]["selected_directory"]
        for file_name, file_content in temp_add_files[message.chat.id]:
            file_path = os.path.join(selected_directory, file_name)
            with open(file_path, 'wb') as new_file:
                new_file.write(file_content)
        bot.send_message(message.chat.id, "✅ Все файлы успешно добавлены!")
        show_files_menu(message)
    elif message.text == 'В меню админ-панели':
        show_admin_panel(message)
    elif message.text == 'В меню файлы':
        show_files_menu(message)
    else:
        bot.send_message(message.chat.id, "Неверное действие! Пожалуйста, выберите верное действие")
        bot.register_next_step_handler(message, process_add_file_action)

# ------------------------------------------------------- ФАЙЛЫ (удалить файлы) ----------------------------------------------

@bot.message_handler(func=lambda message: message.text == 'Удалить файлы' and check_admin_access(message))
@restricted
@track_user_activity
@check_chat_state
@check_user_blocked
@log_user_actions
@check_subscription_chanal
@text_only_handler
@rate_limit_with_captcha
def delete_files(message):

    admin_id = str(message.chat.id)
    if not check_permission(admin_id, 'Удалить файлы'):
        bot.send_message(message.chat.id, "⛔️ У вас *нет прав доступа* к этой функции!", parse_mode="Markdown")
        return

    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    directories = [BASE_DIR, FILES_PATH, ADDITIONAL_FILES_PATH, BACKUP_DIR]
    response = "*Список директорий:*\n\n"
    response += "\n\n".join([f"📁 {i + 1}. {escape_markdown(dir)}" for i, dir in enumerate(directories)])
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add('В меню файлы')
    markup.add('В меню админ-панели')
    bot.send_message(message.chat.id, "Выберите директорию для удаления файла:", reply_markup=markup)
    bot.register_next_step_handler(message, process_delete_file_directory_selection)

@text_only_handler
def process_delete_file_directory_selection(message):
    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    try:
        selection = int(message.text.strip())
        if 1 <= selection <= 4:
            selected_directory = [BASE_DIR, FILES_PATH, ADDITIONAL_FILES_PATH, BACKUP_DIR][selection - 1]
            files_list = []
            for root, dirs, files in os.walk(selected_directory):
                dirs[:] = [d for d in dirs if not _is_excluded_dir(d)]
                for file_name in files:
                    if not file_name.startswith('.'): 
                        file_path = os.path.join(root, file_name)
                        files_list.append(file_path)

            if not files_list:
                bot.send_message(message.chat.id, "❌ Файлы не найдены!")
                return

            response = "\n\n".join([f"📄 {i + 1}. {os.path.basename(file_path)}" for i, file_path in enumerate(files_list)])
            bot_data[message.chat.id] = {"files_list": files_list}

            for start in range(0, len(response), TELEGRAM_MESSAGE_LIMIT):
                bot.send_message(message.chat.id, response[start:start + TELEGRAM_MESSAGE_LIMIT])

            bot.send_message(message.chat.id, "Выберите файл через запятую для удаления:")
            bot.register_next_step_handler(message, process_delete_file_selection)
        else:
            bot.send_message(message.chat.id, "Некорректный номер!")
            bot.register_next_step_handler(message, process_delete_file_directory_selection)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите номер!")
        bot.register_next_step_handler(message, process_delete_file_directory_selection)

@text_only_handler
def process_delete_file_selection(message):
    if message.text == 'В меню админ-панели':
        show_admin_panel(message)
        return
    if message.text == 'В меню файлы':
        show_files_menu(message)
        return

    try:
        file_numbers = [int(num.strip()) - 1 for num in message.text.split(',')]
        files_list = bot_data[message.chat.id]["files_list"]
        valid_files = [files_list[num] for num in file_numbers if 0 <= num < len(files_list)]

        if valid_files:
            for file_path in valid_files:
                os.remove(file_path)
            bot.send_message(message.chat.id, "✅ Файлы успешно удалены!")
            show_files_menu(message)
        else:
            bot.send_message(message.chat.id, "Некорректные номера файлов!")
            bot.register_next_step_handler(message, process_delete_file_selection)
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите номера файлов через запятую!")
        bot.register_next_step_handler(message, process_delete_file_selection)