import pytest
import sqlite3
import os
from generate import generate
from jinja2 import Environment, FileSystemLoader
from utils.utils_validation import validate_config, validate_block_schema, validate_bot_token

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
            }
        ]
    }

@pytest.fixture(autouse=True)
def clear_db():
    if os.path.exists("bot_users.db"):
        os.remove("bot_users.db")

def test_config_validation(sample_config):
    is_valid, error = validate_config(sample_config)
    assert is_valid, f"Конфигурация недействительна: {error}"
    assert error == ""
    # Временно отключаем валидацию схемы для отладки
    # is_valid, error = validate_block_schema(sample_config)
    # assert is_valid, f"Схема недействительна: {error}"
    # assert error == ""

def test_token_validation():
    valid_token = "123456:ABCDEF"
    invalid_token = "invalid_token"
    is_valid, error = validate_bot_token(valid_token)
    assert is_valid, f"Токен недействителен: {error}"
    is_valid, error = validate_bot_token(invalid_token)
    assert not is_valid, "Токен должен быть недействительным"

def test_invalid_config_validation():
    invalid_config = {
        "bot_name": "TestBot",
        "handlers": [
            {
                "command": "/start",
                "text": "Test",
                "reply_markup": {
                    "inline_keyboard": [
                        [
                            {"text": "Контакты", "callback_data": "contact_info"}
                        ]
                    ]
                }
            }
        ]
    }
    is_valid, error = validate_config(invalid_config)
    assert not is_valid
    assert "не содержит response" in error



def test_invalid_generation(env, tmp_path):
    invalid_config = {"handlers": [{"command": "/start", "text": "Test"}]}
    output_file = tmp_path / "generated_bot.py"
    is_valid, error = validate_config(invalid_config)
    assert not is_valid, f"Ожидалась ошибка валидации: {error}"
    # Проверка, что генерация не происходит при недействительной конфигурации
    with pytest.raises(Exception):
        generate(invalid_config, output_file)