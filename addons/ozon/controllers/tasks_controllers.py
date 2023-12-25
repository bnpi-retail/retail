from odoo import http


class OzonCreateDailyTasks(http.Controller):
    @http.route(
        "/tasks/create_daily_tasks",
        auth="user",
        csrf=False,
        methods=["POST"],
    )
    def create_daily_tasks(self):
        response = http.request.env["ozon.tasks"].create_tasks_low_price()
        return response
