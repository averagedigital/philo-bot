import random
import os
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
def get_random_image_path():
    folder = "images"
    files = [f for f in os.listdir(folder) if f.endswith(('.png', '.jpg', '.jpeg'))]
    return os.path.join(folder, random.choice(files)) if files else None
def download_photo(file_id):
    file_info = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
    ).json()

    file_path = file_info["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"

    os.makedirs("images", exist_ok=True)
    local_filename = os.path.join("images", os.path.basename(file_path))

    response = requests.get(file_url)
    with open(local_filename, "wb") as f:
        f.write(response.content)

    return local_filename

def send_message(chat_id, text):
    # Сначала отправляем текст с кнопками
    url_text = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    buttons = {
        "inline_keyboard": [
            [
                {"text": "🔁 Обновить", "callback_data": "refresh"},
                {"text": "📖 Подробнее", "callback_data": "detail"}
            ]
        ]
    }
    payload_text = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": buttons
    }
    requests.post(url_text, json=payload_text)

    # Затем отправляем случайное изображение (если есть)
    image_path = get_random_image_path()
    if image_path:
        url_photo = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open(image_path, 'rb') as photo:
            payload_photo = {
                "chat_id": chat_id
            }
            files = {"photo": photo}
            requests.post(url_photo, data=payload_photo, files=files)

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    print("📥 Запрос от Telegram:")
    print(request.json)

    data = request.json
    if "message" in data:
    if "photo" in message:
    file_id = message["photo"][-1]["file_id"]
    saved_path = download_photo(file_id)
    send_message(chat_id, f"✅ Фото сохранено в архив: {saved_path}")
    return "ok"
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
