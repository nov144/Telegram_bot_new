import os
import json
import base64
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
rint("📎 Открываем таблицу по ссылке: https://docs.google.com/spreadsheets/d/" + SPREADSHEET_ID)
creds_base64 = os.getenv("GOOGLE_CREDS_BASE64")

print("== Google Sheets Test ==")

try:
    if not creds_base64:
        raise Exception("GOOGLE_CREDS_BASE64 is not set")

    creds_json = json.loads(base64.b64decode(creds_base64))
    credentials = Credentials.from_service_account_info(
        creds_json,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gclient = gspread.authorize(credentials)

    print("✅ Авторизация успешна.")

    if not SPREADSHEET_ID:
        raise Exception("SPREADSHEET_ID is not set")

    sheet = gclient.open_by_key(SPREADSHEET_ID)
    print("✅ Таблица открыта:", sheet.title)

    sheet1 = sheet.sheet1
    print("📄 Первая строка:", sheet1.row_values(1))

except Exception as e:
    print("❌ Ошибка:", e)
