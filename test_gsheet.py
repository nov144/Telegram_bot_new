import os
import gspread
import json
import base64
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
creds_json = json.loads(base64.b64decode(os.getenv("GOOGLE_CREDS_BASE64")))
credentials = Credentials.from_service_account_info(
    creds_json, scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
client = gspread.authorize(credentials)

print("Авторизация пройдена.")
sheet = client.open_by_key(SPREADSHEET_ID)
print("Таблица открыта:", sheet.title)
