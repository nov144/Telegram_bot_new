import os
import json
import base64
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
creds_base64 = os.getenv("GOOGLE_CREDS_BASE64")

print("== Google Sheets Final Debug ==")
print("📎 SPREADSHEET_ID =", SPREADSHEET_ID)

try:
    if not creds_base64:
        raise Exception("GOOGLE_CREDS_BASE64 is not set")
    creds_json = json.loads(base64.b64decode(creds_base64))
    print("🔑 Service Account Email:", creds_json.get("client_email"))

    credentials = Credentials.from_service_account_info(
        creds_json,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gclient = gspread.authorize(credentials)

    print("✅ Авторизация прошла")

    spreadsheet = gclient.open_by_key(SPREADSHEET_ID)
    print("✅ Таблица найдена:", spreadsheet.title)

except Exception as e:
    print("❌ Ошибка:", e)
