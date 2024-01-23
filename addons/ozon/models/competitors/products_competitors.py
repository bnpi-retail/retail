import requests

from os import getenv
from datetime import datetime, timedelta
from odoo import models, fields, api


class ProductCompetitors(models.Model):
    _name = "ozon.products_competitors"
    _description = "Товары конкуренты"

    id_product = fields.Char(string="Id товара на Ozon")
    article = fields.Char(string="Артикул", unique=True)
    
    name = fields.Char(string="Наименование товара")

    url = fields.Char(
        string="URL товара", widget="url", help="Укажите ссылку на товар в поле"
    )

    product = fields.Many2one("ozon.products", string="Лот")

    price_competitors_count = fields.One2many(
        "ozon.price_history_competitors",
        "product_competitors",
        string="Количество цен товара конкурента",
    )
    get_price_competitors_count = fields.Integer(
        compute="compute_count_price_competitors"
    )

    imgs_html_graph_this_year = fields.Html(
        compute="_compute_imgs_analysis_data_this_year",
        string="График истории цен"
    )
    imgs_url_this_year = fields.Char(
        string="Ссылка на объект аналитический данных за этот год"
    )
    def _compute_imgs_analysis_data_this_year(self):
        for rec in self:
            rec.imgs_html_graph_this_year = False
            if rec.imgs_url_this_year:
                rec.imgs_html_graph_this_year = (
                    f"<img src='{rec.imgs_url_this_year}' width='600'/>"
                )

    def draw_plot(self):
        model_price_history_competitors = self.env["ozon.price_history_competitors"]

        time_now = datetime.now()

        records_current_year = {"dates": [], "num": []}

        for rec in self:
            records = model_price_history_competitors.search([("product_competitors", "=", rec.id)])

            for record in records:
                if record.timestamp.year == time_now.year:
                    records_current_year["dates"].append(
                        record.timestamp.strftime("%Y-%m-%d")
                    )
                    records_current_year["num"].append(record.price)

            endpoint = "http://django:8000/api/v1/draw_graph"
            payload = {
                "model": "competitors_products",
                "product_id": rec.id,
                "current": records_current_year,
            }
            api_token = getenv("API_TOKEN_DJANGO")
            headers = {"Authorization": f"Token {api_token}"}
            response = requests.post(endpoint, json=payload, headers=headers)

            if response.status_code != 200:
                raise ValueError(f"{response.status_code}--{response.text}")
            
    @api.depends("price_competitors_count")
    def compute_count_price_competitors(self):
        current_time = datetime.now()
        three_months_ago = current_time - timedelta(days=90)

        for record in self:
            record.get_price_competitors_count = self.env[
                "ozon.price_history_competitors"
            ].search_count(
                [
                    ("product_competitors", "=", record.id),
                    ("timestamp", ">=", three_months_ago.strftime("%Y-%m-%d %H:%M:%S")),
                ]
            )

    def get_price_competitors(self):
        self.ensure_one()

        current_time = datetime.now()
        three_months_ago = current_time - timedelta(days=90)

        return {
            "type": "ir.actions.act_window",
            "name": "История цен конкурентов",
            "view_mode": "tree,graph",
            "res_model": "ozon.price_history_competitors",
            "domain": [
                ("product_competitors", "=", self.id),
                ("timestamp", ">=", three_months_ago.strftime("%Y-%m-%d %H:%M:%S")),
            ],
            "context": {
                "create": False,
                "views": [(False, "tree"), (False, "form"), (False, "graph")],
                "graph_mode": "line",
                "measure": "price_with_card",
                "interval": "day",
            },
        }

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result

    def get_last_price(self):
        self.ensure_one()
        price_history = self.price_competitors_count.search(
            [], limit=1, order="create_date desc"
        )
        return price_history.price if price_history else None
