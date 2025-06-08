import random
import os
from dotenv import load_dotenv
load_dotenv()

import requests
from flask import Flask, request
from openai import OpenAI

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Google Drive папка (указан твой ID)
GOOGLE_DRIVE_FOLDER_ID = '1tN21ABCNrFNo4PIRN7ROp8pW_EYIlmoO'

# Инициализация Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'credentials.json'
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

# Загрузка переменных окружения
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

def get_random_drive_image_link(folder_id):
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false",
        pageSize=100,
        fields="files(id, name, webContentLink)"
    ).execute()

    files = results.get("files", [])
    if not files:
        return None

    file = random.choice(files)
    file_id = file["id"]

    # Делает файл общедоступным
    drive_service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"},
    ).execute()

    return file["webContentLink"].replace("&export=download", "")

def upload_to_drive(local_file_path, drive_folder_id):
    file_metadata = {
        "name": os.path.basename(local_file_path),
        "parents": [drive_folder_id]
    }
    media = MediaFileUpload(local_file_path, resumable=True)
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    return uploaded_file.get("id")

def download_photo(file_id):
    file_info = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
    ).json()

    file_path = file_info["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"

    os.makedirs("images", exist_ok=True)
    saved_path = os.path.join("images", os.path.basename(file_path))

    response = requests.get(file_url)
    with open(saved_path, "wb") as f:
        f.write(response.content)

    upload_to_drive(saved_path, GOOGLE_DRIVE_FOLDER_ID)
    os.remove(saved_path)

    return saved_path

def send_message(chat_id, text):
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

    image_url = get_random_drive_image_link(GOOGLE_DRIVE_FOLDER_ID)
    if image_url:
        url_photo = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        payload_photo = {
            "chat_id": chat_id,
            "photo": image_url
        }
        requests.post(url_photo, data=payload_photo)

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    print("📥 Запрос от Telegram:")
    print(request.json)

    data = request.json

    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]

        if "photo" in message:
            file_id = message["photo"][-1]["file_id"]
            saved_path = download_photo(file_id)
            send_message(chat_id, f"✅ Фото сохранено в архив: {saved_path}")
        else:
            send_message(chat_id, get_philosophy_drop())

    elif "callback_query" in data:
        query = data["callback_query"]
        cid = query["message"]["chat"]["id"]
        callback = query["data"]
        if callback == "refresh":
            send_message(cid, get_philosophy_drop())
        elif callback == "detail":
            send_message(cid, get_philosophy_drop(detailed=True))

    return "ok"
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    try:
        print("📥 Запрос от Telegram:")
        print(request.json)

        data = request.json

        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]

            if "photo" in message:
                file_id = message["photo"][-1]["file_id"]
                saved_path = download_photo(file_id)
                send_message(chat_id, f"✅ Фото сохранено в архив: {saved_path}")
            else:
                send_message(chat_id, get_philosophy_drop())

        elif "callback_query" in data:
            query = data["callback_query"]
            cid = query["message"]["chat"]["id"]
            callback = query["data"]
            if callback == "refresh":
                send_message(cid, get_philosophy_drop())
            elif callback == "detail":
                send_message(cid, get_philosophy_drop(detailed=True))

        return "ok"

    except Exception as e:
        print("❌ Ошибка в webhook():", e)
        return "error", 500
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)