import os
import json
import base64
import gspread
from google.oauth2.service_account import Credentials

creds_base64 = os.getenv("GOOGLE_CREDS_BASE64")
creds_json = json.loads(base64.b64decode(creds_base64))

# ✅ Добавлен доступ к Google Drive
credentials = Credentials.from_service_account_info(
    creds_json,
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)

gclient = gspread.authorize(credentials)

try:
    sheet = gclient.create("Таблица от бота")
    print("✅ Таблица создана:", sheet.url)
except Exception as e:
    print("❌ Ошибка при создании таблицы:", e)
