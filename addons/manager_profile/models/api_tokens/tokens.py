import requests


from os import getenv
from datetime import datetime
from odoo import models, fields, api


class MainApiTokens(models.Model):
    _name = "manager_profile.api_tokens"
    _description = "Получение API токенов"

    token = fields.Char(string='API токен', readonly=True)
    will_expire = fields.Date(string='Дата истечения API токена', readonly=True, widget='date', options={'datepicker_options': {'format': 'dd.MM.yyyy'}})


class NameGetApiTokens(models.Model):
    _inherit = "manager_profile.api_tokens"

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
    _inherit = "manager_profile.api_tokens"

    def actions_get_api_token(self):
        user_email = self.env.user.email
        payload = {"email": user_email}

        endpoint = "http://django:8000/account/get_api_token/"
        api_token = getenv("API_TOKEN_DJANGO")
        headers = {"Authorization": f"Token {api_token}"}
        response = requests.post(endpoint, json=payload, headers=headers)

        if response.status_code != 200:
            raise ValueError(f"{response.status_code}--{response.text}")
        
        res = response.json()
        record = self[0]
        record.token = res["token"]

        expiration_date = datetime.strptime(res["expiration_date"], '%Y-%m-%d %H:%M:%S')
        record.will_expire = expiration_date