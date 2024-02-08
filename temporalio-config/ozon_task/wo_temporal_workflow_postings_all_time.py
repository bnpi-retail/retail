from datetime import datetime, time, timedelta, timezone
import os

from ozon_api import (
    import_postings_from_ozon_api_to_file,
    convert_datetime_str_to_ozon_date_ver2,
)
from fill_db import (
    authenticate_to_odoo,
    divide_csv_into_chunks,
    send_all_csv_chunks_to_ozon_import_file,
    remove_all_csv_files,
)

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
POSTINGS_PATH = "./postings.csv"


string_date_from = "2024-01-01T00:00:00Z"
string_date_to = "2024-01-28T00:00:00Z"
date_from = datetime(2024, 1, 1, 00, 00, 00, 000000, tzinfo=timezone.utc)
date_to = datetime(2024, 1, 28, 00, 00, 00, 000000, tzinfo=timezone.utc)
today = datetime.now(tz=timezone.utc)
while date_to <= today and date_from != date_to:
    print(f"Postings from {string_date_from} ---------- to {string_date_to}")
    import_postings_from_ozon_api_to_file(
        file_path=POSTINGS_PATH, date_from=string_date_from, date_to=string_date_to
    )
    date_from = date_to
    date_to = date_to + timedelta(days=28)
    if date_to > today:
        date_to = today
    string_date_from = convert_datetime_str_to_ozon_date_ver2(str(date_from))
    string_date_to = convert_datetime_str_to_ozon_date_ver2(str(date_to))


session_id = authenticate_to_odoo(username=USERNAME, password=PASSWORD)
divide_csv_into_chunks(POSTINGS_PATH)
url = "http://0.0.0.0:8070/import/postings_from_ozon_api_to_file"
send_all_csv_chunks_to_ozon_import_file(url=url, session_id=session_id)
remove_all_csv_files()
