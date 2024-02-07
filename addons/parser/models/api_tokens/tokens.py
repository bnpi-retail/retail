import requests


from os import getenv
from datetime import datetime
from odoo import models, fields, api


class MainApiTokens(models.Model):
    _name = "parser.api_tokens"
    _description = "Получение API токенов"

    token = fields.Char(string='API токен', readonly=True)
    will_expire = fields.Date(string='Дата истечения API токена', readonly=True)
    worker = fields.Many2one('res.users', string='Сотрудник')
    download_link = fields.Char(
        string='Ссылка на актуальную версию Chrome Extension'
    )


class NameGetApiTokens(models.Model):
    _inherit = "parser.api_tokens"

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            id = record.id
            result.append((id, record.will_expire))
        return result


class ActionsApiTokens(models.Model):
    _inherit = "parser.api_tokens"

    def actions_get_api_token(self):
        email = self.worker.email

        payload = {"email": email}

        endpoint = "http://django:8000/account/get_api_token/"
        api_token = getenv("API_TOKEN_DJANGO")
        headers = {"Authorization": f"Token {api_token}"}
        response = requests.post(endpoint, json=payload, headers=headers)

        if response.status_code != 200:
            raise ValueError(f"{response.status_code}--{response.text}")
        
        res = response.json()
        record = self[0]
        record.token = res["token"]
        record.download_link = res["download_link"]


        expiration_date = datetime.strptime(res["expiration_date"], '%Y-%m-%d %H:%M:%S')
        record.will_expire = expiration_date