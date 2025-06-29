# Шаблоны

## Визитка
Шаблон для представления информации о пользователе или компании с inline-кнопками (сайт, email, телефон).

## FAQ
Шаблон для ответов на часто задаваемые вопросы с использованием callback-кнопок.

Пример конфигурации FAQ:
```json
{
  "command": "/faq",
  "text": "Часто задаваемые вопросы:",
  "reply_markup": {
    "inline_keyboard": [[{ "text": "Вопрос 1", "callback_data": "faq_q1" }]],
    "faq_responses": {
      "faq_q1": "Ответ на вопрос 1"
    }
  }
}
```

## Опросник
Шаблон для создания опросов с вопросами и вариантами ответов. Пользователь может выбрать опрос через команду `/poll`, а данные сохраняются в базе данных SQLite (`polls` таблица).

Пример конфигурации опросника:
```json
{
  "command": "/poll",
  "text": "Опросы:",
  "reply_markup": {
    "inline_keyboard": [[{ "text": "Какой ваш любимый цвет?", "callback_data": "poll_1" }]],
    "poll_responses": {
      "poll_1": "Вопрос: Какой ваш любимый цвет?\nВарианты ответа:\n- Красный\n- Синий\n- Зеленый"
    }
  }
}
```

### Создание опроса через Telegram-интерфейс
1. Введите `/create_bot` и выберите шаблон "Опросник".
2. Укажите имя бота и токен от @BotFather.
3. Введите количество опросов (1-4).
4. Для каждого опроса:
   - Введите вопрос.
   - Укажите количество вариантов ответа (2-4).
   - Введите текст каждого варианта ответа.
5. Данные сохраняются в базе данных, и бот генерируется.

### Создание опроса через CLI
Пример команды:
```bash
python cli.py poll --name MyPollBot --token your_token --polls "Какой ваш любимый цвет?:Красный,Синий,Зеленый" "Какой ваш любимый сезон?:Лето,Зима"
```

## Конструктор блоков
Шаблон поддерживает динамическое создание блоков через команды `/add_block` и `/edit_block`.

### /add_block
Позволяет добавить новый блок (сообщение, команда, клавиатура) через интерактивный интерфейс:
1. Выберите тип блока (сообщение, команда, клавиатура).
2. Укажите команду (для типа "команда").
3. Введите текст блока.
4. Добавьте inline-кнопки в формате JSON (или пропустите с помощью `/skip`).

### /edit_block
Позволяет редактировать существующий блок:
1. Выберите блок из списка.
2. Обновите команду, текст или кнопки (или пропустите с помощью `/skip`).

Пример добавления блока через `/add_block`:
1. Введите `/add_block`.
2. Выберите "Команда".
3. Введите `/mycommand`.
4. Введите текст: "Это мой новый блок!".
5. Введите JSON для кнопок: `[ [{"text": "Кнопка", "callback_data": "test"}] ]`.