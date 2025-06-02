from google.oauth2.service_account import Credentials
import gspread
import os, json, base64

creds_base64 = os.getenv("GOOGLE_CREDS_BASE64")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
creds_json = json.loads(base64.b64decode(creds_base64))

credentials = Credentials.from_service_account_info(
    creds_json,
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"  # 🔥 обязательно
    ]
)

client = gspread.authorize(credentials)

try:
    print("Авторизация прошла ✅")
    sheet = client.open_by_key(SPREADSHEET_ID)
    print("Открыта таблица:", sheet.title)
except Exception as e:
    print("❌ Ошибка:", e)
