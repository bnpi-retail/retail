import requests
import logging

from os import getenv
from datetime import datetime
from odoo import models, fields, api

logger = logging.getLogger(__name__)


class Categories(models.Model):
    _name = "ozon.categories"
    _description = "Категории Ozon"

    name_categories = fields.Char(string="Название", readonly=True)
    c_id = fields.Integer(string="Идентификатор", readonly=True, index=True)
    insurance = fields.Float(string="Страховой коэффициент, %")

    category_manager = fields.Many2one("res.users")
    bcg_matrix_last_update = fields.Datetime()
    abc_group_last_update = fields.Datetime()

    category_total_price = fields.Float(string="Сумма цен товаров категории в продаже")
    category_total_marketing_price = fields.Float(string="Сумма цен для покупателя товаров категории в продаже")
    price_difference = fields.Float(
        string="Cоотношение между нашей ценой и ценой для покупателя")
    is_price_difference_computed = fields.Boolean()

    ozon_products_ids = fields.One2many('ozon.products', 'categories')

    @api.model
    def _name_search(
        self, name="", args=None, operator="ilike", limit=10, name_get_uid=None
    ):
        args = list(args or [])
        if name:
            args += [("name_categories", operator, name)]
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    def action_compute_average_prices_difference(self):
        for record in self:
            query = """
                    SELECT
                         SUM(price) as total_price,
                         SUM(marketing_price) as total_marketing_price
                    FROM
                        ozon_products
                    WHERE
                        categories = %s
                        AND
                        is_selling = %s
            """
            self.env.cr.execute(query, (record.id, True))
            result = self.env.cr.fetchone()

            total_price = result[0] if result and result[0] else 0.00001
            total_marketing_price = result[1] if result and result[1] else 0

            if result and (result[0] or result[1]):
                record.price_difference = (total_price - total_marketing_price) / total_price

            record.category_total_price = total_price
            record.category_total_marketing_price = total_marketing_price

            record.is_price_difference_computed = True


class GenerateUrlForDownloadGrpahData(models.Model):
    _inherit = "ozon.categories"

    def get_url(self, model_name, record_id, field_name):
        return f'/web/content_text?model={model_name}&id={record_id}&field={field_name}'

    def get_download_url(self, field_name):
        model_name = self._name
        record_id = self.id
        url = self.get_url(model_name, record_id, field_name)
        return url


class GraphSaleThisYear(models.Model):
    _inherit = "ozon.categories"

    img_data_sale_this_year = fields.Text(string="Json data filed")
    img_url_sale_this_year = fields.Char(string="Ссылка на объект")
    img_html_sale_this_year = fields.Html(
        compute="_compute_img_sale_this_year", string="График продаж за текущий год"
    )

    def download_data_sale_this_year(self):
        field_name = "img_data_sale_this_year"
        url = self.get_download_url(field_name)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


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

    def download_data_sale_last_year(self):
        field_name = "img_data_sale_last_year"
        url = self.get_download_url(field_name)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
    
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

    img_data_analysis_data_this_year = fields.Text(string="Json data filed")
    img_url_analysis_data_this_year = fields.Char(string="Ссылка на объект")
    img_html_analysis_data_this_year = fields.Html(
        compute="_compute_img_analysis_data_this_year",
        string="График интереса тукущий год",
    )

    def download_data_analysis_data_this_year(self):
        field_name = "img_data_analysis_data_this_year"
        url = self.get_download_url(field_name)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

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

class CategoryFees(models.Model):
    _inherit = "ozon.categories"

    def _trading_scheme_fees(self):
        ozon_fee_recs = self.env["ozon.ozon_fee"].search([("category", "=", self.id)])
        return {fee.name: fee.value for fee in ozon_fee_recs}