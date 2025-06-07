from dotenv import load_dotenv
load_dotenv ()
import os
from openai import OpenAI
import requests
from datetime import datetime
from flask import Flask, request

# ⬇️ Отладочный вывод
print("GROQ_API_KEY:", os.getenv("GROQ_API_KEY"))
print("TELEGRAM_TOKEN:", os.getenv("TELEGRAM_TOKEN"))
print("CHAT_ID:", os.getenv("CHAT_ID"))


# Читаем ключи из окружения
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

app = Flask(__name__)

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

def get_philosophy_drop(detailed=False):
    prompt = (
        "Дай философскую концепцию, объясни её простыми словами и приведи пример."
        if detailed else
        "Дай одну философскую концепцию (1–2 предложения), объясни её простыми словами и приведи пример из повседневной жизни."
    )
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "Ты философ, объясняешь ясно и кратко."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    buttons = {
        "inline_keyboard": [
            [
                {"text": "🔁 Обновить", "callback_data": "refresh"},
                {"text": "📖 Подробнее", "callback_data": "detail"}
            ]
        ]
    }
    payload = {"chat_id": chat_id, "text": text, "reply_markup": buttons}
    return requests.post(url, json=payload)

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    print("📥 Запрос от Telegram:")
    print(request.json)

    data = request.json
    if "message" in data:
        send_message(data["message"]["chat"]["id"], get_philosophy_drop())
    elif "callback_query" in data:
        query = data["callback_query"]
        cid = query["message"]["chat"]["id"]
        callback = query["data"]
        if callback == "refresh":
            send_message(cid, get_philosophy_drop())
        elif callback == "detail":
            send_message(cid, get_philosophy_drop(detailed=True))
    return "ok"

# Запускаем Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
