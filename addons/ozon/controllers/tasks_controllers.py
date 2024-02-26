import json
from odoo import http


class OzonCreateDailyTasks(http.Controller):
    @http.route(
        "/tasks/create_daily_tasks",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def create_daily_tasks(self):
        tasks_response = http.request.env["ozon.tasks"].create_tasks_low_price()
        response_json = json.dumps(tasks_response)
        return response_json
