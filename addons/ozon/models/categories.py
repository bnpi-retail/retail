import requests

from time import sleep
from os import getenv
from datetime import datetime
from odoo import models, fields, api


class Categories(models.Model):
    _name = "ozon.categories"
    _description = "Категории Ozon"

    name_categories = fields.Char(string="Название", readonly=True)
    c_id = fields.Integer(string="Идентификатор", readonly=True)
    insurance = fields.Float(string="Страховой коэффициент, %")

    category_manager = fields.Many2one("res.users")


class GraphSaleThisYear(models.Model):
    _inherit = "ozon.categories"

    img_data_sale_this_year = fields.Text(string="Json data filed")
    img_url_sale_this_year = fields.Char(string="Ссылка на объект")
    img_html_sale_this_year = fields.Html(
        compute="_compute_img_sale_this_year", string="График продаж за текущий год"
    )

    def _compute_img_sale_this_year(self):
        for rec in self:
            rec.img_html_sale_this_year = False
            if not rec.img_url_sale_this_year:
                continue

            rec.img_html_sale_this_year = (
                f"<img src='{rec.img_url_sale_this_year}' width='600'/>"
            )


class GraphSaleLastYear(models.Model):
    _inherit = "ozon.categories"

    img_data_sale_last_year = fields.Text(string="Json data filed")
    img_url_sale_last_year = fields.Char(string="Ссылка на объект")
    img_html_sale_last_year = fields.Html(
        compute="_compute_img_sale_last_year", string="График продаж за прошлый год"
    )

    def _compute_img_sale_last_year(self):
        for rec in self:
            rec.img_html_sale_last_year = False
            if not rec.img_url_sale_last_year:
                continue

            rec.img_html_sale_last_year = (
                f"<img src='{rec.img_url_sale_last_year}' width='600'/>"
            )


class GraphInterest(models.Model):
    _inherit = "ozon.categories"

    img_data_analysis_data_this_year_hits = fields.Text(string="Json data filed")
    img_data_analysis_data_this_year_to_cart = fields.Text(string="Json data filed")

    img_url_analysis_data_this_year = fields.Char(string="Ссылка на объект")
    img_html_analysis_data_this_year = fields.Html(
        compute="_compute_img_analysis_data_this_year",
        string="График интереса тукущий год",
    )

    def _compute_img_analysis_data_this_year(self):
        for rec in self:
            rec.img_html_analysis_data_this_year = False
            if not rec.img_url_analysis_data_this_year:
                continue

            rec.img_html_analysis_data_this_year = (
                f"<img src='{rec.img_url_analysis_data_this_year}' width='600'/>"
            )


class ActionGraphs(models.Model):
    _inherit = "ozon.categories"

    def action_draw_graphs_by_categories(self):
        products_records = self.draw_sale_this_year()
        products_records += self.draw_sale_last_year()
        products_records += self.draw_graph_interest()
        self.draw_graphs_products(list(set(products_records)))

    def draw_sale_this_year(self):
        year = self._get_year()

        data_for_send = {}

        categorie_record = self[0]

        products_records = self.env["ozon.products"].search(
            [
                ("categories", "=", categorie_record.id),
                # ("is_alive", "=", True),
                # ("is_selling", "=", True),
            ]
        )

        for product_record in products_records:
            sale_records = self.env["ozon.sale"].search(
                [
                    ("product", "=", product_record.id),
                    ("date", ">=", f"{year}-01-01"),
                    ("date", "<=", f"{year}-12-31"),
                ]
            )

            if not sale_records:
                continue

            graph_data = {"dates": [], "values": []}

            for sale_record in sale_records:
                graph_data["dates"].append(sale_record.date.strftime("%Y-%m-%d"))
                graph_data["values"].append(sale_record.qty)

            data_for_send[product_record.id] = graph_data

        payload = {
            "model": "categorie_sale_this_year",
            "categorie_id": categorie_record.id,
            "data": data_for_send,
        }

        # categorie_record.img_data_sale_this_year = data_for_send

        self._send_request(payload)

        return products_records

    def draw_sale_last_year(self):
        year = self._get_year() - 1

        data_for_send = {}

        categorie_record = self[0]

        products_records = self.env["ozon.products"].search(
            [
                ("categories", "=", categorie_record.id),
                # ("is_alive", "=", True),
                # ("is_selling", "=", True),
            ]
        )

        for product_record in products_records:
            sale_records = self.env["ozon.sale"].search(
                [
                    ("product", "=", product_record.id),
                    ("date", ">=", f"{year}-01-01"),
                    ("date", "<=", f"{year}-12-31"),
                ]
            )

            if not sale_records:
                continue

            graph_data = {"dates": [], "values": []}

            for sale_record in sale_records:
                graph_data["dates"].append(sale_record.date.strftime("%Y-%m-%d"))
                graph_data["values"].append(sale_record.qty)

            data_for_send[product_record.id] = graph_data

        payload = {
            "model": "categorie_sale_last_year",
            "categorie_id": categorie_record.id,
            "data": data_for_send,
        }

        # categorie_record.img_data_sale_last_year = data_for_send
        print(data_for_send)

        self._send_request(payload)

        return products_records

    def draw_graph_interest(self):
        year = self._get_year()

        data_for_send = {}

        categorie_record = self[0]

        products_records = self.env["ozon.products"].search(
            [
                ("categories", "=", categorie_record.id),
                # ("is_alive", "=", True),
                # ("is_selling", "=", True),
            ]
        )

        for product_record in products_records:
            analysis_data_records = self.env["ozon.analysis_data"].search(
                [
                    ("product", "=", product_record.id),
                    ("timestamp_from", ">=", f"{year}-01-01"),
                    ("timestamp_to", "<=", f"{year}-12-31"),
                ]
            )

            if not analysis_data_records:
                continue

            graph_data = {"dates": [], "hits_view": [], "hits_tocart": []}

            for analysis_data_record in analysis_data_records:
                start_date = analysis_data_record.timestamp_from
                end_date = analysis_data_record.timestamp_to
                average_date = start_date + (end_date - start_date) / 2

                graph_data["dates"].append(average_date.strftime("%Y-%m-%d"))
                graph_data["hits_view"].append(analysis_data_record.hits_view)
                graph_data["hits_tocart"].append(analysis_data_record.hits_tocart)

            data_for_send[product_record.id] = graph_data

        payload = {
            "model": "categorie_analysis_data",
            "categorie_id": categorie_record.id,
            "data": data_for_send,
        }

        # categorie_record.img_data_analysis_data_this_year = data_for_send

        self._send_request(payload)

        return products_records

    def draw_graphs_products(self, products_records):
        print(f"All records: {len(products_records)}")

        for index, product_record in enumerate(products_records):
            product_record.action_draw_graphs()
            print(index + 1)

    def _send_request(self, payload):
        endpoint = "http://django:8000/api/v1/draw_graph"
        api_token = getenv("API_TOKEN_DJANGO")
        headers = {"Authorization": f"Token {api_token}"}
        response = requests.post(endpoint, json=payload, headers=headers)

        if response.status_code != 200:
            raise ValueError(f"{response.status_code}--{response.text}")

    def _get_year(self) -> str:
        return datetime.now().year


class NameGetCustom(models.Model):
    _inherit = "ozon.categories"

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.name_categories))
        return result
