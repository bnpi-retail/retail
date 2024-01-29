from odoo import http


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
        return settings
