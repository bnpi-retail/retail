import json

from odoo import http
from odoo.http import request


class UserController(http.Controller):

    @http.route('/get_users', auth='user', type='http', csrf=False)
    def get_users(self):
        if not request.env.user.has_group('base.group_user'):
            return http.Response('Unauthorized', status=401)

        users = request.env['res.users'].search([])

        user_data = []
        for user in users:
            user_data.append(user.email)
            # user_data.append({
            #     # 'name': user.name,
            #     # 'login': user.login,
            #     'email': user.email,
            # })

        json_data = json.dumps(user_data, ensure_ascii=False).encode('utf-8')

        return http.request.make_response(
            json_data,
            headers=[('Content-Type', 'application/json')],
        )
