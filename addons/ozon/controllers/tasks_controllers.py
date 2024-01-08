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
        mass_pricing_response = http.request.env[
            "ozon.mass_pricing"
        ].auto_create_from_strategy_competitors()
        return f"{tasks_response}\n{mass_pricing_response}"
