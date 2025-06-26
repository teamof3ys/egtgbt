import pytest
import json
import os
from unittest.mock import AsyncMock, patch
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from generate import generate
from jinja2 import Environment, FileSystemLoader
from utils.utils_validation import validate_config, validate_block_schema
import sqlite3

pytestmark = pytest.mark.asyncio

@pytest.fixture
def env():
    return Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def sample_config():
    return {
        "bot_name": "TestBot",
        "handlers": [
            {
                "command": "/start",
                "text": "Привет, это тестовый бот!\n📞 Телефон: +1234567890\n📧 Email: user@example.com",
                "reply_markup": {
                    "inline_keyboard": [
                        [
                            {"text": "Посетить сайт", "url": "https://example.com"},
                            {"text": "Контакты", "callback_data": "contact_info", "response": "Email: user@example.com"}
                        ]
                    ]
                }
            },
            {
                "command": "/faq",
                "text": "Часто задаваемые вопросы:",
                "reply_markup": {
                    "inline_keyboard": [
                        [
                            {"text": "Вопрос 1", "callback_data": "faq_q1", "response": "Ответ на вопрос 1"}
                        ]
                    ]
                }
            }
        ]
    }

@pytest.fixture
async def bot():
    bot = AsyncMock(spec=Bot)
    return bot

@pytest.fixture
async def dp(bot):
    dp = Dispatcher()
    return dp

@pytest.fixture
def message():
    message = AsyncMock(spec=Message)
    message.from_user.id = 12345
    message.from_user.username = "testuser"
    message.answer = AsyncMock()
    return message

@pytest.fixture
def callback_query():
    callback = AsyncMock(spec=CallbackQuery)
    callback.from_user.id = 12345
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    return callback

@pytest.fixture
def state():
    return AsyncMock(spec=FSMContext)

@pytest.fixture(autouse=True)
def clear_db():
    if os.path.exists("bot_users.db"):
        os.remove("bot_users.db")

async def test_bot_generation(env, sample_config, tmp_path):
    output_file = tmp_path / "generated_bot.py"
    generate(sample_config, output_file)
    
    with open(output_file, 'r', encoding='utf-8') as f:
        generated_code = f.read()
    
    assert "Bot" in generated_code
    assert "Dispatcher" in generated_code
    assert "start_handler" in generated_code
    
    exec_globals = {}
    exec(generated_code, exec_globals)
    exec_globals['init_db']()
    
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    assert c.fetchone()[0] == "users"
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_configs'")
    assert c.fetchone()[0] == "bot_configs"
    conn.close()

async def test_start_command(dp, bot, message, state, tmp_path):
    output_file = tmp_path / "generated_bot.py"
    generate(sample_config, output_file)
    
    with open(output_file, 'r', encoding='utf-8') as f:
        generated_code = f.read()
    
    exec_globals = {}
    exec(generated_code, exec_globals)
    
    message.text = "/start"
    await exec_globals['start_handler'](message)
    message.answer.assert_called_with(
        "Привет, это тестовый бот!\\n📞 Телефон: +1234567890\\n📧 Email: user@example.com",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Посетить сайт", url="https://example.com"),
                InlineKeyboardButton(text="Контакты", callback_data="contact_info")
            ]
        ])
    )

async def test_faq_command(dp, bot, message, callback_query, tmp_path):
    output_file = tmp_path / "generated_bot.py"
    generate(sample_config, output_file)
    
    with open(output_file, 'r', encoding='utf-8') as f:
        generated_code = f.read()
    
    exec_globals = {}
    exec(generated_code, exec_globals)
    
    message.text = "/faq"
    await exec_globals['faq_handler'](message)
    message.answer.assert_called_with(
        "Часто задаваемые вопросы:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Вопрос 1", callback_data="faq_q1")]
        ])
    )
    
    callback_query.data = "faq_q1"
    handler_name = f"callback_{callback_query.data}_handler"
    assert handler_name in exec_globals, f"Обработчик {handler_name} не найден"
    await exec_globals[handler_name](callback_query)
    callback_query.message.answer.assert_called_with("Ответ на вопрос 1")
    callback_query.answer.assert_called_once()

async def test_business_card_creation(dp, bot, message, state, tmp_path, sample_config):
    from target_bot_code import process_bot_name, process_bot_token, process_welcome_text, process_phone, process_email, process_website, process_help_text, process_faq_count, process_faq_question, process_faq_answer, finalize_business_card

    message.from_user.id = 12345
    await state.update_data(template="business_card", config={"bot_name": "", "handlers": []}, faq_list=[])

    # Имя бота
    message.text = "MyTestBot"
    await process_bot_name(message, state)
    assert (await state.get_data())['bot_name'] == "MyTestBot"

    # Токен
    message.text = "123456:ABCDEF"
    await process_bot_token(message, state)
    assert (await state.get_data())['bot_token'] == "123456:ABCDEF"

    # Приветственный текст
    message.text = "Welcome to my bot!"
    await process_welcome_text(message, state)
    assert (await state.get_data())['welcome_text'] == "Welcome to my bot!"

    # Телефон
    message.text = "+1234567890"
    await process_phone(message, state)
    assert (await state.get_data())['phone'] == "+1234567890"

    # Email
    message.text = "test@example.com"
    await process_email(message, state)
    assert (await state.get_data())['email'] == "test@example.com"

    # Сайт
    message.text = "https://example.com"
    await process_website(message, state)
    assert (await state.get_data())['website'] == "https://example.com"

    # Текст помощи
    message.text = "Use /start to view my card."
    await process_help_text(message, state)
    assert (await state.get_data())['help_text'] == "Use /start to view my card."

    # Количество FAQ
    message.text = "2"
    await process_faq_count(message, state)
    assert (await state.get_data())['faq_count'] == 2

    # Первый вопрос FAQ
    message.text = "What do you do?"
    await process_faq_question(message, state)
    assert (await state.get_data())['faq_question'] == "What do you do?"

    # Первый ответ FAQ
    message.text = "I help users!"
    await process_faq_answer(message, state)
    assert (await state.get_data())['faq_list'] == [{"question": "What do you do?", "answer": "I help users!"}]

    # Второй вопрос FAQ
    message.text = "How to contact?"
    await process_faq_question(message, state)
    assert (await state.get_data())['faq_question'] == "How to contact?"

    # Второй ответ FAQ и финализация
    message.text = "Email me!"
    with patch('target_bot_code.generate_and_run_bot', AsyncMock()) as mock_run:
        await process_faq_answer(message, state)
        await finalize_business_card(message, state)
        mock_run.assert_called_once_with(
            {"bot_name": "MyTestBot", "handlers": mock_run.call_args[0][0]["handlers"]},
            "123456:ABCDEF",
            mock_run.call_args[0][2]
        )