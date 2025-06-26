
import asyncio
import sys
import sqlite3
import json
import os
import subprocess
import psutil
import aiohttp
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from utils.utils_validation import validate_config, validate_block_schema
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

def init_db():
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bot_configs (
            config_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bot_name TEXT,
            config_json TEXT,
            bot_token TEXT,
            pid INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS polls (
            poll_id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_id INTEGER,
            question TEXT,
            options TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (config_id) REFERENCES bot_configs (config_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS poll_responses (
            response_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            poll_id INTEGER,
            config_id INTEGER,
            option_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (config_id) REFERENCES bot_configs (config_id),
            FOREIGN KEY (poll_id) REFERENCES polls (poll_id)
        )
    ''')
    try:
        c.execute('ALTER TABLE bot_configs ADD COLUMN bot_token TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE bot_configs ADD COLUMN pid INTEGER')
    except sqlite3.OperationalError:
        pass
    c.execute('SELECT config_id, pid FROM bot_configs WHERE pid IS NOT NULL')
    for config_id, pid in c.fetchall():
        try:
            process = psutil.Process(pid)
            process.terminate()
            process.wait(timeout=3)
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            pass
        c.execute('UPDATE bot_configs SET pid = NULL WHERE config_id = ?', (config_id,))
    conn.commit()
    conn.close()

dp = Dispatcher(storage=MemoryStorage())
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2))

class RegistrationForm(StatesGroup):
    name = State()
    confirm = State()

class BotCreationForm(StatesGroup):
    template = State()
    bot_name = State()
    bot_token = State()
    welcome_text = State()
    phone = State()
    email = State()
    website = State()
    help_text = State()

class FAQCreationForm(StatesGroup):
    faq_count = State()
    faq_question = State()
    faq_answer = State()

class PollCreationForm(StatesGroup):
    poll_count = State()
    poll_question = State()
    poll_options_count = State()
    poll_option = State()

class BotDeleteForm(StatesGroup):
    config_id = State()

@dp.message(Command("start"))
async def command_start_handler(message: Message, state: FSMContext) -> None:
    logger.debug("Processing /start command")
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (message.from_user.id,))
    user = c.fetchone()
    conn.close()
    if user:
        keyboard_buttons = [
            [
                InlineKeyboardButton(text="Создать бота", callback_data="menu_create_bot"),
                InlineKeyboardButton(text="Список ботов", callback_data="menu_list_bots"),
            ],
            [
                InlineKeyboardButton(text="Удалить бота", callback_data="menu_delete_bot"),
            ],
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        text = "*Привет\\!* 👋 Добро пожаловать в билдер Telegram\\-ботов\\.\nВыберите действие:"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        text = "*Привет\\!* 👋 Давай зарегистрируем тебя\\.\nВведи свое имя:"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.set_state(RegistrationForm.name)

def escape_markdown(text):
    """Escape all MarkdownV2 special characters for Telegram and ensure Python string safety."""
    if not text:
        return text
    special_chars = r'_[]()*~`>#+-=|{}.!?'
    escaped_text = ''
    for char in text:
        if char in special_chars:
            escaped_text += '\\' + char
        else:
            escaped_text += char
    return escaped_text

@dp.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    text = "*Помощь* ℹ️\nИспользуйте /menu для управления ботами или /start для начала работы\\."
    logger.debug(f"Sending message: {text}")
    await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)

@dp.message(Command("faq"))
async def command_faq_handler(message: Message) -> None:
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="Что вы делаете?", callback_data="faq_what_do_you_do"),
            InlineKeyboardButton(text="Как связаться?", callback_data="faq_contact"),
        ],
        [
            InlineKeyboardButton(text="Где вы находитесь?", callback_data="faq_location"),
            InlineKeyboardButton(text="Вопрос 2", callback_data="faq_q2"),
        ],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    text = "*Часто задаваемые вопросы* ❓\nВыберите интересующий вопрос\\."
    logger.debug(f"Sending message: {text}")
    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)

@dp.callback_query(lambda c: c.data == "faq_what_do_you_do")
async def callback_faq_what_do_you_do_handler(callback: CallbackQuery) -> None:
    text = "Мы создаем *крутые Telegram\\-боты*\\! 🚀"
    logger.debug(f"Sending message: {text}")
    await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "faq_contact")
async def callback_faq_contact_handler(callback: CallbackQuery) -> None:
    text = "Напишите на почту user\\@example\\.com или позвоните \\+1234567890\\."
    logger.debug(f"Sending message: {text}")
    await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "faq_location")
async def callback_faq_location_handler(callback: CallbackQuery) -> None:
    text = "Наш офис находится в *центре города*\\."
    logger.debug(f"Sending message: {text}")
    await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "faq_q2")
async def callback_faq_q2_handler(callback: CallbackQuery) -> None:
    text = "Ответ на вопрос 2"
    logger.debug(f"Sending message: {text}")
    await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await callback.answer()

@dp.message(Command("create_bot"))
async def create_bot_handler(message: Message, state: FSMContext) -> None:
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="Визитка", callback_data="template_business_card"),
            InlineKeyboardButton(text="FAQ", callback_data="template_faq"),
            InlineKeyboardButton(text="Опросник", callback_data="template_poll"),
        ],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    text = "*Создание бота* 🤖\nВыберите шаблон для нового бота:"
    logger.debug(f"Sending message: {text}")
    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)
    await state.set_state(BotCreationForm.template)

@dp.callback_query(lambda c: c.data.startswith("template_"))
async def process_template_selection(callback: CallbackQuery, state: FSMContext) -> None:
    template = callback.data.replace("template_", "")
    if template == "business_card":
        await state.update_data(template=template, config={"bot_name": "", "handlers": []})
        text = "Введите *имя нового бота*:"
        logger.debug(f"Sending message: {text}")
        await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.set_state(BotCreationForm.bot_name)
    elif template == "faq":
        await state.update_data(template=template, config={"bot_name": "", "handlers": []}, faq_list=[])
        text = "Введите *имя нового бота*:"
        logger.debug(f"Sending message: {text}")
        await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.set_state(BotCreationForm.bot_name)
    elif template == "poll":
        await state.update_data(template=template, config={"bot_name": "", "handlers": []}, poll_list=[])
        text = "Введите *имя нового бота*:"
        logger.debug(f"Sending message: {text}")
        await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.set_state(BotCreationForm.bot_name)
    await callback.answer()

@dp.message(BotCreationForm.bot_name)
async def process_bot_name(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    if not is_valid_text(message.text):
        text = "*Ошибка* ⚠️\nИмя бота содержит недопустимые символы\\.\nИспользуйте буквы, цифры, пробелы и знаки препинания \\(кроме \\_\\, \\*\\, \\[\\, \\]\\, \\(\\, \\)\\, \\~\\, \\`\\, \\>\\, \\#\\, \\+\\, \\-\\, \\=\\, \\|\\, \\{\\, \\}\\, \\.\\, \\!\\, \\?\\)\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        return
    await state.update_data(bot_name=message.text)
    user_data = await state.get_data()
    config = user_data['config']
    config['bot_name'] = message.text
    await state.update_data(config=config)
    text = "Введите *токен бота*, полученный от @BotFather \\(или /cancel\\):"
    logger.debug(f"Sending message: {text}")
    await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await state.set_state(BotCreationForm.bot_token)

@dp.message(BotCreationForm.bot_token)
async def process_bot_token(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    bot_token = message.text.strip()
    if not bot_token.count(":") == 1 or not bot_token.split(":")[0].isdigit():
        text = "*Ошибка* ⚠️\nНекорректный формат токена\\.\nПопробуйте снова или /cancel\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        return
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.telegram.org/bot{bot_token}/getMe") as response:
            data = await response.json()
            if not data.get("ok"):
                text = f"*Ошибка* ⚠️\nНедействительный токен: {escape_markdown(str(data.get('description', 'Ошибка')))}\\.\nПопробуйте снова или /cancel\\."
                logger.debug(f"Sending message: {text}")
                await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
                return
    await state.update_data(bot_token=bot_token)
    template = (await state.get_data())['template']
    if template == "business_card":
        text = "Введите *текст приветствия* для команды /start \\(или /skip для значения по умолчанию\\):"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.set_state(BotCreationForm.welcome_text)
    elif template == "faq":
        text = "Сколько вопросов FAQ вы хотите добавить\\? \\(*1\\-4* или /cancel\\):"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.set_state(FAQCreationForm.faq_count)
    elif template == "poll":
        text = "Сколько опросов вы хотите добавить\\? \\(*1\\-4* или /cancel\\):"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.set_state(PollCreationForm.poll_count)
    text = "*Токен принят* ✅"
    logger.debug(f"Sending message: {text}")
    await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)

@dp.message(BotCreationForm.welcome_text)
async def process_welcome_text(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    welcome_text = message.text if message.text != "/skip" else "Привет\\! Я бот\\-визитка\\.\nЗдесь вы можете найти всю необходимую информацию обо мне\\."
    if not is_valid_text(welcome_text):
        text = "*Ошибка* ⚠️\nТекст приветствия содержит недопустимые символы\\.\nИспользуйте буквы, цифры, пробелы и знаки препинания \\(кроме \\_\\, \\*\\, \\[\\, \\]\\, \\(\\, \\)\\, \\~\\, \\`\\, \\>\\, \\#\\, \\+\\, \\-\\, \\=\\, \\|\\, \\{\\, \\}\\, \\.\\, \\!\\, \\?\\)\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        return
    await state.update_data(welcome_text=welcome_text)
    text = "Введите *номер телефона* \\(например, \\+1234567890\\) или /skip:"
    logger.debug(f"Sending message: {text}")
    await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await state.set_state(BotCreationForm.phone)

@dp.message(BotCreationForm.phone)
async def process_phone(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    phone = message.text if message.text != "/skip" else None
    if phone:
        phone = phone.replace(" ", "").replace("tel:", "")
        if not phone.startswith("+") or not phone[1:].isdigit() or len(phone) < 7:
            text = "*Ошибка* ⚠️\nНомер телефона должен начинаться с \\+ и содержать только цифры \\(например, \\+79522046894\\)\\.\nМинимум 6 цифр\\.\nПопробуйте снова или /skip\\."
            logger.debug(f"Sending message: {text}")
            await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
            return
    await state.update_data(phone=phone)
    text = "Введите *email* \\(например, user\\@example\\.com\\) или /skip:"
    logger.debug(f"Sending message: {text}")
    await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await state.set_state(BotCreationForm.email)

@dp.message(BotCreationForm.email)
async def process_email(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    email = message.text if message.text != "/skip" else None
    if email and "@" not in email:
        text = "*Ошибка* ⚠️\nНекорректный формат email\\.\nПопробуйте снова или /skip\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        return
    await state.update_data(email=email)
    text = "Введите *URL сайта* \\(например, https://example\\.com\\) или /skip:"
    logger.debug(f"Sending message: {text}")
    await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await state.set_state(BotCreationForm.website)

@dp.message(BotCreationForm.website)
async def process_website(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    website = message.text if message.text != "/skip" else None
    if website and not website.startswith(('http://', 'https://')):
        text = "*Ошибка* ⚠️\nURL должен начинаться с http:// или https://\\.\nПопробуйте снова или /skip\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        return
    await state.update_data(website=website)
    text = "Введите *текст для команды /help* \\(или /skip для значения по умолчанию\\):"
    logger.debug(f"Sending message: {text}")
    await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await state.set_state(BotCreationForm.help_text)

@dp.message(BotCreationForm.help_text)
async def process_help_text(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    help_text = message.text if message.text != "/skip" else "Используйте /start для просмотра визитки\\."
    if not is_valid_text(help_text):
        text = "*Ошибка* ⚠️\nТекст помощи содержит недопустимые символы\\.\nИспользуйте буквы, цифры, пробелы и знаки препинания \\(кроме \\_\\, \\*\\, \\[\\, \\]\\, \\(\\, \\)\\, \\~\\, \\`\\, \\>\\, \\#\\, \\+\\, \\-\\, \\=\\, \\|\\, \\{\\, \\}\\, \\.\\, \\!\\, \\?\\)\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        return
    await state.update_data(help_text=help_text)
    await finalize_business_card(message, state)

def is_valid_text(text):
    """Validate text to ensure it contains only safe characters for Markdown and Python strings."""
    if not text:
        return False
    allowed_chars = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ,:;@#$%^&" +
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    )
    invalid_chars = set(text) - allowed_chars
    if invalid_chars:
        logger.debug(f"Invalid characters found in text: {invalid_chars}")
        return False
    return len(text.strip()) > 0

@dp.message(FAQCreationForm.faq_count)
async def process_faq_count(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    try:
        faq_count = int(message.text)
        if faq_count < 1 or faq_count > 4:
            text = "*Ошибка* ⚠️\nЧисло вопросов должно быть от *1* до *4*\\.\nПопробуйте снова или /cancel\\."
            logger.debug(f"Sending message: {text}")
            await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
            return
        await state.update_data(faq_count=faq_count, current_faq=1)
        text = "Введите текст *первого вопроса FAQ*:"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.set_state(FAQCreationForm.faq_question)
    except ValueError:
        text = "*Ошибка* ⚠️\nВведите число или /cancel\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)

@dp.message(FAQCreationForm.faq_question)
async def process_faq_question(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    if not is_valid_text(message.text):
        text = "*Ошибка* ⚠️\nВопрос FAQ содержит недопустимые символы\\.\nИспользуйте буквы, цифры, пробелы и знаки препинания \\(кроме \\_\\, \\*\\, \\[\\, \\]\\, \\(\\, \\)\\, \\~\\, \\`\\, \\>\\, \\#\\, \\+\\, \\-\\, \\=\\, \\|\\, \\{\\, \\}\\, \\.\\, \\!\\, \\?\\)\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        return
    await state.update_data(faq_question=message.text)
    text = f"Введите *ответ* на вопрос '{escape_markdown(message.text)}':"
    logger.debug(f"Sending message: {text}")
    await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await state.set_state(FAQCreationForm.faq_answer)

@dp.message(FAQCreationForm.faq_answer)
async def process_faq_answer(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    if not is_valid_text(message.text):
        text = "*Ошибка* ⚠️\nОтвет FAQ содержит недопустимые символы\\.\nИспользуйте буквы, цифры, пробелы и знаки препинания \\(кроме \\_\\, \\*\\, \\[\\, \\]\\, \\(\\, \\)\\, \\~\\, \\`\\, \\>\\, \\#\\, \\+\\, \\-\\, \\=\\, \\|\\, \\{\\, \\}\\, \\.\\, \\!\\, \\?\\)\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        return
    user_data = await state.get_data()
    faq_list = user_data.get('faq_list', [])
    faq_list.append({"question": user_data['faq_question'], "answer": message.text})
    await state.update_data(faq_list=faq_list)
    current_faq = user_data['current_faq']
    faq_count = user_data['faq_count']
    if current_faq < faq_count:
        await state.update_data(current_faq=current_faq + 1)
        text = f"Введите текст вопроса FAQ *{current_faq + 1}*:"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.set_state(FAQCreationForm.faq_question)
    else:
        await finalize_faq(message, state)

@dp.message(PollCreationForm.poll_count)
async def process_poll_count(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    try:
        poll_count = int(message.text)
        if poll_count < 1 or poll_count > 4:
            text = "*Ошибка* ⚠️\nЧисло опросов должно быть от *1* до *4*\\.\nПопробуйте снова или /cancel\\."
            logger.debug(f"Sending message: {text}")
            await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
            return
        await state.update_data(poll_count=poll_count, current_poll=1, current_options=[])
        text = "Введите текст *первого вопроса опроса*:"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.set_state(PollCreationForm.poll_question)
    except ValueError:
        text = "*Ошибка* ⚠️\nВведите число или /cancel\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)

@dp.message(PollCreationForm.poll_question)
async def process_poll_question(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    if not is_valid_text(message.text):
        text = "*Ошибка* ⚠️\nВопрос опроса содержит недопустимые символы\\.\nИспользуйте буквы, цифры, пробелы и знаки препинания \\(кроме \\_\\, \\*\\, \\[\\, \\]\\, \\(\\, \\)\\, \\~\\, \\`\\, \\>\\, \\#\\, \\+\\, \\-\\, \\=\\, \\|\\, \\{\\, \\}\\, \\.\\, \\!\\, \\?\\)\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        return
    await state.update_data(poll_question=message.text)
    text = "Сколько вариантов ответа для этого опроса\\? \\(*2\\-4* или /cancel\\):"
    logger.debug(f"Sending message: {text}")
    await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await state.set_state(PollCreationForm.poll_options_count)

@dp.message(PollCreationForm.poll_options_count)
async def process_poll_options_count(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    try:
        options_count = int(message.text)
        if options_count < 2 or options_count > 4:
            text = "*Ошибка* ⚠️\nЧисло вариантов ответа должно быть от *2* до *4*\\.\nПопробуйте снова или /cancel\\."
            logger.debug(f"Sending message: {text}")
            await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
            return
        await state.update_data(options_count=options_count, current_option=1, current_options=[])
        text = "Введите текст *первого варианта ответа* для опроса:"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.set_state(PollCreationForm.poll_option)
    except ValueError:
        text = "*Ошибка* ⚠️\nВведите число или /cancel\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)

@dp.message(PollCreationForm.poll_option)
async def process_poll_option(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Создание бота отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    if not is_valid_text(message.text):
        text = "*Ошибка* ⚠️\nВариант ответа содержит недопустимые символы\\.\nИспользуйте буквы, цифры, пробелы и знаки препинания \\(кроме \\_\\, \\*\\, \\[\\, \\]\\, \\(\\, \\)\\, \\~\\, \\`\\, \\>\\, \\#\\, \\+\\, \\-\\, \\=\\, \\|\\, \\{\\, \\}\\, \\.\\, \\!\\, \\?\\)\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        return
    user_data = await state.get_data()
    current_options = user_data.get('current_options', [])
    current_options.append(message.text)
    await state.update_data(current_options=current_options)
    current_option = user_data.get('current_option', 1)
    options_count = user_data['options_count']
    if current_option < options_count:
        await state.update_data(current_option=current_option + 1)
        text = f"Введите текст *варианта ответа {current_option + 1}*:"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.set_state(PollCreationForm.poll_option)
    else:
        poll_list = user_data.get('poll_list', [])
        poll_list.append({
            "question": user_data['poll_question'],
            "options": current_options
        })
        await state.update_data(poll_list=poll_list)
        current_poll = user_data['current_poll']
        poll_count = user_data['poll_count']
        if current_poll < poll_count:
            await state.update_data(current_poll=current_poll + 1, current_options=[])
            text = f"Введите текст вопроса опроса *{current_poll + 1}*:"
            logger.debug(f"Sending message: {text}")
            await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
            await state.set_state(PollCreationForm.poll_question)
        else:
            await finalize_poll(message, state)

async def finalize_business_card(message: Message, state: FSMContext):
    user_data = await state.get_data()
    config = user_data['config']
    bot_token = user_data['bot_token']
    welcome_text = escape_markdown(user_data['welcome_text'])
    phone = escape_markdown(user_data.get('phone')) if user_data.get('phone') else None
    email = escape_markdown(user_data.get('email')) if user_data.get('email') else None
    website = escape_markdown(user_data.get('website')) if user_data.get('website') else None
    help_text = escape_markdown(user_data['help_text'])

    config['bot_name'] = escape_markdown(config['bot_name'])

    contact_text = f"*{welcome_text}*\n\n📋 *Контактная информация:*\n"
    if website:
        contact_text += f"🌐 *Website:* {website}\n"
    if email:
        contact_text += f"📧 *Email:* {email}\n"
    if phone:
        contact_text += f"📞 *Phone:* {phone}\n"
    if not any([website, email, phone]):
        contact_text += "ℹ️ Контактная информация не указана\\.\n"

    handlers = [
        {
            "command": "/start",
            "text": contact_text
        },
        {
            "command": "/help",
            "text": help_text
        },
        {
            "command": "/create_bot",
            "text": "Начать создание нового бота\\."
        },
        {
            "command": "/list_bots",
            "text": "Показать список ваших ботов\\."
        },
        {
            "command": "/delete_bot",
            "text": "Удалить бота\\."
        },
        {
            "command": "/menu",
            "text": "Выберите действие:",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": "Создать бота", "callback_data": "menu_create_bot", "response": "Начнем создание бота\\!"},
                        {"text": "Список ботов", "callback_data": "menu_list_bots", "response": "Показываю ваши боты\\."}
                    ],
                    [
                        {"text": "Удалить бота", "callback_data": "menu_delete_bot", "response": "Выберите бота для удаления\\."}
                    ]
                ]
            }
        }
    ]

    config['handlers'] = handlers

    logger.debug(f"Business card config: {json.dumps(config, ensure_ascii=False)}")
    is_valid, error = validate_config(config)
    if not is_valid:
        text = f"*Ошибка* ⚠️\nОшибка в конфигурации: {escape_markdown(str(error))}"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    is_valid, error = validate_block_schema(config)
    if not is_valid:
        text = f"*Ошибка* ⚠️\nОшибка в конфигурации: {escape_markdown(str(error))}"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return

    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute(
        'INSERT INTO bot_configs (user_id, bot_name, config_json, bot_token) VALUES (?, ?, ?, ?)',
        (message.from_user.id, config['bot_name'], json.dumps(config), bot_token)
    )
    config_id = c.lastrowid
    conn.commit()
    conn.close()

    try:
        await generate_and_run_bot(config, bot_token, config_id)
        text = f"*Успех* 🎉\nБот '{escape_markdown(config['bot_name'])}' успешно создан и запущен\\! ID: {config_id}"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        logger.error(f"Error generating bot: {str(e)}")
        text = f"*Ошибка* ⚠️\nОшибка при запуске бота: {escape_markdown(str(e))}"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    finally:
        await state.clear()

async def finalize_faq(message: Message, state: FSMContext):
    user_data = await state.get_data()
    config = user_data['config']
    bot_token = user_data['bot_token']
    faq_list = user_data.get('faq_list', [])

    faq_list = [
        {"question": escape_markdown(faq['question']), "answer": escape_markdown(faq['answer'])}
        for faq in faq_list
    ]
    config['bot_name'] = escape_markdown(config['bot_name'])

    faq_text = "*Часто задаваемые вопросы* ❓\nВыберите интересующий вопрос\\."
    keyboard_buttons = []

    for i, faq in enumerate(faq_list, 1):
        callback_data = f"faq_{i}"
        keyboard_buttons.append([
            {
                "text": faq['question'],
                "callback_data": callback_data,
                "response": faq['answer']
            }
        ])

    handlers = [
        {
            "command": "/start",
            "text": "Добро пожаловать в бот FAQ\\! Используйте /faq для просмотра вопросов\\."
        },
        {
            "command": "/faq",
            "text": faq_text,
            "reply_markup": {"inline_keyboard": keyboard_buttons}
        }
    ]

    config['handlers'] = handlers

    try:
        logger.debug(f"FAQ config: {json.dumps(config, ensure_ascii=False)}")
    except Exception as e:
        logger.error(f"Failed to log config: {str(e)}")

    is_valid, error = validate_config(config)
    if not is_valid:
        logger.error(f"Config validation failed: {error}")
        text = f"*Ошибка* ⚠️\nОшибка в конфигурации: {escape_markdown(str(error))}"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    is_valid, error = validate_block_schema(config)
    if not is_valid:
        logger.error(f"Schema validation failed: {error}")
        text = f"*Ошибка* ⚠️\nОшибка в конфигурации: {escape_markdown(str(error))}"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return

    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute(
        'INSERT INTO bot_configs (user_id, bot_name, config_json, bot_token) VALUES (?, ?, ?, ?)',
        (message.from_user.id, config['bot_name'], json.dumps(config), bot_token)
    )
    config_id = c.lastrowid
    conn.commit()
    conn.close()

    try:
        await generate_and_run_bot(config, bot_token, config_id)
        text = f"*Успех* 🎉\nБот '{escape_markdown(config['bot_name'])}' успешно создан и запущен\\! ID: {config_id}"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        logger.error(f"Error generating bot: {str(e)}")
        text = f"*Ошибка* ⚠️\nОшибка при запуске бота: {escape_markdown(str(e))}"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    finally:
        await state.clear()

async def finalize_poll(message: Message, state: FSMContext):
    user_data = await state.get_data()
    config = user_data['config']
    bot_token = user_data['bot_token']
    poll_list = user_data.get('poll_list', [])

    # Escape all poll questions and options
    poll_list = [
        {
            "question": escape_markdown(poll['question']),
            "options": [escape_markdown(opt) for opt in poll['options']]
        }
        for poll in poll_list
    ]
    config['bot_name'] = escape_markdown(config['bot_name'])

    poll_text = "*Опросы* 📊\nВыберите интересующий опрос\\."
    keyboard_buttons = []

    # Store poll IDs for reference in generated bot
    poll_id_map = {}

    # Insert polls into database and map poll questions to IDs
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    for i, poll in enumerate(poll_list, 1):
        c.execute(
            'INSERT INTO polls (config_id, question, options) VALUES (?, ?, ?)',
            (0, poll['question'], json.dumps(poll['options']))  # config_id set to 0 temporarily
        )
        poll_id_map[f"poll_{i}"] = c.lastrowid
    conn.commit()
    conn.close()

    # Create buttons for poll selection (no response needed)
    for i, poll in enumerate(poll_list, 1):
        callback_data = f"poll_{i}"
        keyboard_buttons.append([
            {
                "text": poll['question'],
                "callback_data": callback_data
            }
        ])

    handlers = [
        {
            "command": "/start",
            "text": "Добро пожаловать в бот опросов\\! Используйте /poll для просмотра опросов\\."
        },
        {
            "command": "/poll",
            "text": poll_text,
            "reply_markup": {
                "inline_keyboard": keyboard_buttons
            }
        }
    ]

    # Add callback handlers for poll selection
    for i, poll in enumerate(poll_list, 1):
        callback_data = f"poll_{i}"
        options_text = "\n".join([f"\\- {opt}" for opt in poll['options']])
        response_text = f"Вопрос: {poll['question']}\nВарианты ответа:\n{options_text}"
        handlers.append({
            "callback_query": callback_data,
            "text": response_text,
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": opt, "callback_data": f"poll_{i}_option_{j}"}]
                    for j, opt in enumerate(poll['options'], 1)
                ]
            }
        })

    # Add callback handlers for option selection
    for i, poll in enumerate(poll_list, 1):
        for j, opt in enumerate(poll['options'], 1):
            callback_data = f"poll_{i}_option_{j}"
            options_text = "\n".join([f"\\- {opt}" for opt in poll['options']])
            response_text = f"Вопрос: {poll['question']}\nВарианты ответа:\n{options_text}"
            handlers.append({
                "callback_query": callback_data,
                "text": response_text,
                "save_response": {
                    "poll_id": poll_id_map[f"poll_{i}"],
                    "option_text": opt,
                    "thank_you_text": f"*Спасибо за ваш ответ\\!* ✅\nВы выбрали: {opt}"
                }
            })

    config['handlers'] = handlers

    try:
        logger.debug(f"Poll config: {json.dumps(config, ensure_ascii=False)}")
    except Exception as e:
        logger.error(f"Failed to log config: {str(e)}")

    is_valid, error = validate_config(config)
    if not is_valid:
        logger.error(f"Config validation failed: {error}")
        text = f"*Ошибка* ⚠️\nОшибка в конфигурации: {escape_markdown(str(error))}"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    is_valid, error = validate_block_schema(config)
    if not is_valid:
        logger.error(f"Schema validation failed: {error}")
        text = f"*Ошибка* ⚠️\nОшибка в конфигурации: {escape_markdown(str(error))}"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return

    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute(
        'INSERT INTO bot_configs (user_id, bot_name, config_json, bot_token) VALUES (?, ?, ?, ?)',
        (message.from_user.id, config['bot_name'], json.dumps(config), bot_token)
    )
    config_id = c.lastrowid
    # Update polls with correct config_id
    c.execute('UPDATE polls SET config_id = ? WHERE config_id = 0', (config_id,))
    conn.commit()
    conn.close()

    try:
        await generate_and_run_bot(config, bot_token, config_id)
        text = f"*Успех* 🎉\nБот '{escape_markdown(config['bot_name'])}' успешно создан и запущен\\! ID: {config_id}"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        logger.error(f"Error generating bot: {str(e)}")
        text = f"*Ошибка* ⚠️\nОшибка при запуске бота: {escape_markdown(str(e))}"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    finally:
        await state.clear()

async def generate_and_run_bot(config, bot_token, config_id):
    from generate import generate
    output_file = f"bots/bot_{config_id}.py"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    generate(config, output_file, config_id)
    env_file = f"bots/bot_{config_id}.env"
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(f"BOT_TOKEN={bot_token}\n")
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('SELECT pid FROM bot_configs WHERE config_id = ?', (config_id,))
    result = c.fetchone()
    if result and result[0]:
        old_pid = result[0]
        try:
            old_process = psutil.Process(old_pid)
            old_process.terminate()
            old_process.wait(timeout=3)
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            pass
    process = subprocess.Popen(
        [sys.executable, os.path.abspath(output_file)],
        cwd=os.path.dirname(os.path.abspath(output_file)),
        env={**os.environ, "BOT_TOKEN": bot_token}
    )
    c.execute('UPDATE bot_configs SET pid = ? WHERE config_id = ?', (process.pid, config_id))
    conn.commit()
    conn.close()

@dp.message(Command("list_bots"))
async def list_bots_handler(message: Message) -> None:
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('SELECT config_id, bot_name FROM bot_configs WHERE user_id = ?', (message.from_user.id,))
    bots = c.fetchall()
    conn.close()
    if bots:
        response = "*Ваши боты* 🤖\n" + "\n".join([f"ID: {bot[0]}, Имя: {escape_markdown(bot[1])}" for bot in bots])
    else:
        response = "У вас пока *нет ботов*\\."
    logger.debug(f"Sending message: {response}")
    await message.answer(response, parse_mode=ParseMode.MARKDOWN_V2)

@dp.message(Command("delete_bot"))
async def delete_bot_handler(message: Message, state: FSMContext) -> None:
    text = "Введите *ID бота* для удаления \\(или /cancel\\):"
    logger.debug(f"Sending message: {text}")
    await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await state.set_state(BotDeleteForm.config_id)

@dp.message(BotDeleteForm.config_id)
async def process_delete_id(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        text = "*Удаление отменено* ❌"
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
        return
    try:
        config_id = int(message.text)
        conn = sqlite3.connect('bot_users.db')
        c = conn.cursor()
        c.execute('DELETE FROM bot_configs WHERE config_id = ? AND user_id = ?', 
                  (config_id, message.from_user.id))
        c.execute('DELETE FROM polls WHERE config_id = ?', (config_id,))
        c.execute('DELETE FROM poll_responses WHERE config_id = ?', (config_id,))
        if c.rowcount > 0:
            text = "*Успех* 🎉\nБот успешно удален\\!"
        else:
            text = "*Ошибка* ⚠️\nБот не найден или вы не владелец\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        conn.commit()
        conn.close()
        await state.clear()
    except ValueError:
        text = "*Ошибка* ⚠️\nID должен быть числом\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()

@dp.message(Command("menu"))
async def command_menu_handler(message: Message) -> None:
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="Создать бота", callback_data="menu_create_bot"),
            InlineKeyboardButton(text="Список ботов", callback_data="menu_list_bots"),
        ],
        [
            InlineKeyboardButton(text="Удалить бота", callback_data="menu_delete_bot"),
        ],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    text = "*Меню* 📋\nВыберите действие:"
    logger.debug(f"Sending message: {text}")
    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)

@dp.callback_query(lambda c: c.data == "menu_create_bot")
async def callback_menu_create_bot_handler(callback: CallbackQuery, state: FSMContext) -> None:
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="Визитка", callback_data="template_business_card"),
            InlineKeyboardButton(text="FAQ", callback_data="template_faq"),
            InlineKeyboardButton(text="Опросник", callback_data="template_poll"),
        ],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    text = "*Создание бота* 🤖\nВыберите шаблон для нового бота:"
    logger.debug(f"Sending message: {text}")
    await callback.message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)
    await state.set_state(BotCreationForm.template)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "menu_list_bots")
async def callback_menu_list_bots_handler(callback: CallbackQuery) -> None:
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute('SELECT config_id, bot_name FROM bot_configs WHERE user_id = ?', (callback.from_user.id,))
    bots = c.fetchall()
    conn.close()
    if bots:
        response = "*Ваши боты* 🤖\n" + "\n".join([f"ID: {bot[0]}, Имя: {escape_markdown(bot[1])}" for bot in bots])
    else:
        response = "У вас пока *нет ботов*\\."
    logger.debug(f"Sending message: {response}")
    await callback.message.answer(response, parse_mode=ParseMode.MARKDOWN_V2)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "menu_delete_bot")
async def callback_menu_delete_bot_handler(callback: CallbackQuery, state: FSMContext) -> None:
    text = "Введите *ID бота* для удаления \\(или /cancel\\):"
    logger.debug(f"Sending message: {text}")
    await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await state.set_state(BotDeleteForm.config_id)
    await callback.answer()

@dp.message(RegistrationForm.name)
async def process_name(message: Message, state: FSMContext) -> None:
    if not is_valid_text(message.text):
        text = "*Ошибка* ⚠️\nИмя содержит недопустимые символы\\.\nИспользуйте буквы, цифры, пробелы и знаки препинания \\(кроме \\_\\, \\*\\, \\[\\, \\]\\, \\(\\, \\)\\, \\~\\, \\`\\, \\>\\, \\#\\, \\+\\, \\-\\, \\=\\, \\|\\, \\{\\, \\}\\, \\.\\, \\!\\, \\?\\)\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        return
    await state.update_data(name=message.text)
    text = f"Ты ввел имя: *{escape_markdown(message.text)}*\\.\nПодтвердить\\? \\(*да/нет*\\)"
    logger.debug(f"Sending message: {text}")
    await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
    await state.set_state(RegistrationForm.confirm)

@dp.message(RegistrationForm.confirm)
async def process_confirm(message: Message, state: FSMContext) -> None:
    if message.text.lower() == "да":
        user_data = await state.get_data()
        name = user_data['name']
        conn = sqlite3.connect('bot_users.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
                  (message.from_user.id, message.from_user.username, name))
        conn.commit()
        conn.close()
        text = "*Регистрация завершена* 🎉\nНажми /start, чтобы продолжить\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()
    else:
        text = "*Регистрация отменена* ❌\nНажми /start, чтобы начать заново\\."
        logger.debug(f"Sending message: {text}")
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        await state.clear()

async def main() -> None:
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())