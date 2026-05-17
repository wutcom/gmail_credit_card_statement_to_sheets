import os
import time
from typing import List

import gspread
from oauth2client.service_account import ServiceAccountCredentials


SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def get_sheet():
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEET_ID is missing")

    credentials_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        credentials_file,
        SCOPES,
    )

    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(sheet_id)

    # First worksheet
    return spreadsheet.sheet1


def append_row_with_retry(row: List, max_retry: int = 3):
    sheet = get_sheet()

    last_error = None
    for attempt in range(1, max_retry + 1):
        try:
            sheet.append_row(row, value_input_option="USER_ENTERED")
            return
        except Exception as ex:
            last_error = ex
            time.sleep(attempt * 2)

    raise last_error
