from datetime import datetime
from multiprocessing import Value

from odoo import models, fields, api


class Categories(models.Model):
    _name = 'ozon.categories'
    _description = 'Категории Ozon'

    name_categories = fields.Char(string='Наименование категории')
    insurance = fields.Float(string='Страховой коэффициент, %')


class GraphSaleThisYear(models.Model):
    _inherit = 'ozon.categories'

    img_url_sale_this_year = fields.Char(string="Ссылка на объект")
    img_html_sale_this_year = fields.Html(
        compute="_compute_img_sale_this_year",
        string="График продаж за текущий год"
    )

    def _compute_img_sale_this_year(self):
        for rec in self:
            rec.img_html_sale_this_year = False
            if not rec.img_url_sale_this_year: continue

            rec.img_html_sale_this_year = (
                f"<img src='{rec.img_url_sale_this_year}' width='600'/>"
            )


class GraphSaleLastYear(models.Model):
    _inherit = 'ozon.categories'

    img_url_sale_last_year = fields.Char(string="Ссылка на объект")
    img_html_sale_last_year = fields.Html(
        compute="_compute_img_sale_last_year",
        string="График продаж за прошлый год"
    )

    def _compute_img_sale_last_year(self):
        for rec in self:
            rec.img_html_sale_last_year = False
            if not rec.img_url_sale_last_year: continue

            rec.img_html_sale_last_year = (
                f"<img src='{rec.img_url_sale_last_year}' width='600'/>"
            )


class GraphInterest(models.Model):
    _inherit = 'ozon.categories'

    img_url_analysis_data_this_year = fields.Char(string="Ссылка на объект")
    img_html_analysis_data_this_year = fields.Html(
        compute="_compute_img_analysis_data_this_year",
        string="График интереса тукущий год"
    )

    def _compute_img_analysis_data_this_year(self):
        for rec in self:
            rec.img_html_analysis_data_this_year = False
            if not rec.img_url_analysis_data_this_year: continue

            rec.img_html_analysis_data_this_year = (
                f"<img src='{rec.img_url_analysis_data_this_year}' width='600'/>"
            )


class ActionGraphs(models.Model):
    _inherit = 'ozon.categories'

    def action_draw_graphs(self):
        self.draw_sale_this_year()
        self.draw_sale_last_year()
        self.draw_graph_interest()

    def draw_sale_this_year(self):
        pass

    def draw_sale_last_year(self):
        pass

    def draw_graph_interest(self):
        model_products = self.env["ozon.products"]
        model_analysis_data = self.env["ozon.analysis_data"]
        year = self._get_year()

        data_for_send = {}

        for categorie_record in self:
            data_categorie = data_for_send[categorie_record.id] = {}

            products_records = model_products.search([
                ("categories", "=", categorie_record.id),
                # ("is_alive", "=", True),
                # ("is_selling", "=", True),
            ])

            for product_record in products_records:

                analysis_data_records = model_analysis_data.search([
                    ("product", "=", product_record.id),
                    ("timestamp_from", ">=", f"{year}-01-01"),
                    ("timestamp_to", "<=", f"{year}-12-31"),
                ])

                if not analysis_data_records: continue

                graph_data = {"dates": [], "num": []}

                for analysis_data_record in analysis_data_records:
                    start_date = analysis_data_record.timestamp_from
                    end_date = analysis_data_record.timestamp_to
                    average_date = start_date + (end_date - start_date) / 2

                    graph_data["dates"].append(average_date.strftime("%Y-%m-%d"))
                    graph_data["num"].append(analysis_data_record.hits_view)

                data_categorie[product_record.id] = graph_data

        raise ValueError(data_for_send)
    
    def _get_year(self) -> str:
        return datetime.now().year
    
class NameGetCustom(models.Model):
    _inherit = 'ozon.categories'

    def name_get(self):
        """
        Rename name records 
        """
        result = []
        for record in self:
            result.append((record.id, record.name_categories))
        return result