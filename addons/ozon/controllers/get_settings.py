import json

from odoo import http
from odoo.http import Response


class OzonSettingsCredentials(http.Controller):
    @http.route(
        "/get_settings_credentials",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def get_credentials_from_ozon_settings(self, **kwargs):
        all_settings_recs = http.request.env["ozon.settings"].search([])
        settings = {}
        for rec in all_settings_recs:
            settings[rec.name] = rec.value
        return Response(
            response=json.dumps(settings), status=200, content_type="application/json"
        )
