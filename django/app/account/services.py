import os
import requests

username = os.getenv('username_odoo')
password = os.getenv('password_odoo')
db_odoo = os.getenv('db_odoo')
 

def connect_to_odoo_api_with_auth():
    url = "http://odoo-web:8069/"

    session_url = f"{url}/web/session/authenticate"
    data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": db_odoo,
            "login": username,
            "password": password,
        },
    }
    session_response = requests.post(session_url, json=data)
    session_data = session_response.json()

    if session_data.get("result") and session_response.cookies.get("session_id"):
        session_id = session_response.cookies["session_id"]
        return session_id
    else:
        print(f'Error: Failed to authenticate - {session_data.get("error")}')
        return False