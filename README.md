# WB/OZON GPT Bot

Телеграм-бот, подключённый к OpenAI API.  
Помогает продавцам на Wildberries и Ozon:  
- анализ конкурентов,  
- оптимизация карточек,  
- ответы на отзывы (3 стиля),  
- ответы на вопросы покупателей.  

## Команды бота
- `/start`   — приветствие и подсказки  
- `/analyze` — анализ конкурентов  
- `/review`  — ответы на отзывы  
- `/faq`     — ответы на вопросы покупателей  

## Переменные окружения
Нужно указать два ключа в настройках Render (Environment → Add Variable):  
- `OPENAI_API_KEY` — ключ OpenAI (формат `sk-...`)  
- `TELEGRAM_BOT_TOKEN` — токен Телеграм-бота (из BotFather)  

## Запуск локально
```bash
pip install -r requirements.txt
python bot.py
