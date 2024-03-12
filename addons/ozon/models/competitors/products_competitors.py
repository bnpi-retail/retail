import requests

from os import getenv
from datetime import datetime, timedelta
from odoo import models, fields, api
from ..drawing_graphs import DrawGraph as df


class ProductCompetitors(models.Model):
    _name = "ozon.products_competitors"
    _description = "Товары конкуренты"

    id_product = fields.Char(string="Id товара на Ozon")
    article = fields.Char(string="Артикул")
    name = fields.Char(string="Наименование товара")
    competitor_seller_id = fields.Many2one("ozon.competitor_seller", string="Продавец")
    ozon_products_competitors_sale_ids = fields.One2many('ozon.products_competitors.sale', 'ozon_products_competitors_id')
    url = fields.Char(string="URL товара", help="Укажите ссылку на товар в поле")
    product = fields.Many2one("ozon.products", string="Наш товар")
    market_share = fields.Float(string='Доля рынка', digits=(12, 5))
    market_share_is_computed = fields.Boolean()
    tracked_search_query_ids = fields.Many2many(
        'ozon.tracked_search_queries', 
        'product_competitor_tracked_search_rel', 
        'product_competitor_id', 
        'tracked_search_query_id', 
        string="Отслеживаемые поисковые запросы"
    )
    price_competitors_count = fields.One2many(
        "ozon.price_history_competitors",
        "product_competitors",
        string="Количество цен товара конкурента",
    )
    get_price_competitors_count = fields.Integer(
        compute="compute_count_price_competitors"
    )
    imgs_data_graph_this_year = fields.Text()
    imgs_graph_this_year = fields.Binary(
        string="График истории цен"
    )

    def download_data_graph_this_year(self):
        field_name = "imgs_data_graph_this_year"
        url = self.get_download_url(field_name)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

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

            payload = {
                "model": "competitors_products",
                "product_id": rec.id,
                "current": records_current_year,
            }
            bytes_plot, data_current = df().post(payload)
            rec.imgs_graph_this_year = bytes_plot
            rec.imgs_data_graph_this_year = data_current

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


class GenerateUrlForDownloadGrpahData(models.Model):
    _inherit = "ozon.products_competitors"

    def get_url(self, model_name, record_id, field_name):
        return f'/web/content_text?model={model_name}&id={record_id}&field={field_name}'

    def get_download_url(self, field_name):
        model_name = self._name
        record_id = self.id
        url = self.get_url(model_name, record_id, field_name)
        return url