import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class OzonReportInterestData(models.Model):
    _name = "ozon.report.interest.data"
    _description = "Строки данных в отчете по интересам"

    ozon_products_id = fields.Many2one("ozon.products")
    fp_hits_view = fields.Float(digits=(12, 5))
    sp_hits_view = fields.Float(digits=(12, 5))
    fp_revenue = fields.Float(digits=(12, 5))
    sp_revenue = fields.Float(digits=(12, 5))
    fp_share = fields.Float(digits=(12, 5))
    sp_share = fields.Float(digits=(12, 5))

    ozon_report_interest_id = fields.Many2one("ozon.report.interest")


class OzonReportInterest(models.Model):
    _name = "ozon.report.interest"
    _description = "Отчет по соотношению интереса к продукту и продажам"

    ozon_categories_id = fields.Many2one('ozon.categories')

    first_period_from = fields.Date()
    first_period_to = fields.Date()

    second_period_from = fields.Date()
    second_period_to = fields.Date()

    ozon_report_interest_data_ids = fields.One2many(
        "ozon.report.interest.data",
        'ozon_report_interest_id'
    )
    fp_revenue_per_hit_view_per_day = fields.Float(digits=(12, 5))
    sp_revenue_per_hit_view_per_day = fields.Float(digits=(12, 5))

    def action_calculate_interest_report(self):
        for record in self:
            if not record.ozon_categories_id:
                raise UserError("Выберите категорию")
            if (
                    not record.first_period_from or
                    not record.first_period_to or
                    not record.second_period_from or
                    not record.second_period_to
            ):
                raise UserError('Выберите периоды')
            if (
                    record.first_period_from >= record.first_period_to or
                    record.second_period_from >= record.second_period_to
            ):
                raise UserError("Проверьте правильность периодов")
            if record.first_period_to > record.second_period_from:
                raise UserError("Периоды не должны пересекаться")

            # collect data first period
            first_period_analysis_data = self._get_period_analysis_data(
                record.ozon_categories_id.id,
                record.first_period_from,
                record.first_period_to
            )
            fp_data, fp_product_ids = self._get_period_data_dict(first_period_analysis_data)
            del first_period_analysis_data

            self._add_sales_data(
                record.first_period_from, record.first_period_to, fp_product_ids, fp_data
            )

            # collect data second period
            second_period_analysis_data = self._get_period_analysis_data(
                record.ozon_categories_id.id,
                record.second_period_from,
                record.second_period_to
            )
            sp_data, sp_product_ids = self._get_period_data_dict(second_period_analysis_data)
            del second_period_analysis_data

            self._add_sales_data(record.second_period_from, record.second_period_to, sp_product_ids, sp_data)

            fp_revenue_per_view_per_day_relation = self._calc_product_revenue_per_view_per_day(
                record.first_period_from, record.first_period_to, fp_data
            )

            sp_revenue_per_view_per_day_relation = self._calc_product_revenue_per_view_per_day(
                record.second_period_from, record.second_period_to, sp_data
            )

            record.fp_revenue_per_hit_view_per_day = fp_revenue_per_view_per_day_relation
            record.sp_revenue_per_hit_view_per_day = sp_revenue_per_view_per_day_relation

            self._record_data(record, fp_data, sp_data)

    @staticmethod
    def _calc_product_revenue_per_view_per_day(period_from, period_to, data_dict: defaultdict) -> float:
        days = (period_to - period_from).days
        if days == 0:
            raise UserError("Количество дней в периоде равно 0")

        period_total_hits_view = sum(data['hits_view'] for data in data_dict.values())
        period_total_revenue = sum(data['revenue'] for data in data_dict.values())

        period_total_hits_view /= days
        period_total_revenue /= days

        if period_total_hits_view == 0:
            period_revenue_per_view_per_day = 0.000001
        else:
            period_revenue_per_view_per_day = period_total_revenue / period_total_hits_view

        for product_id, data in data_dict.items():
            hits_view = data['hits_view']
            revenue = data['revenue']
            product_revenue_per_view = revenue / hits_view if hits_view != 0 else 0
            product_revenue_per_view_per_day = product_revenue_per_view / days
            data['revenue_%_per_view_per_day'] = (
                product_revenue_per_view_per_day * 100) / period_revenue_per_view_per_day

        return period_revenue_per_view_per_day

    def _record_data(self, record, fp_data, sp_data):
        query = """
                    DELETE FROM ozon_report_interest_data
                    WHERE id IN %s
                """
        if record.ozon_report_interest_data_ids.ids:
            self.env.cr.execute(query, (tuple(record.ozon_report_interest_data_ids.ids),))
            logger.warning(f"delete from ozon_products_indicator_summary records with ids ")

        all_category_product_ids = self.env["ozon.products"].search([
            ('categories', '=', record.ozon_categories_id.id)
        ]).ids

        values = []
        for product_id in all_category_product_ids:
            vals = {
                "ozon_products_id": product_id,
                "fp_hits_view": 0,
                "sp_hits_view": 0,
                "fp_revenue": 0,
                "sp_revenue": 0,
                "fp_share": 0,
                "sp_share": 0,
                "ozon_report_interest_id": record.id
            }
            fp_product_data: dict = fp_data.get(product_id)
            if fp_product_data:
                vals['fp_hits_view'] = fp_product_data['hits_view']
                vals['fp_revenue'] = fp_product_data['revenue']
                vals['fp_share'] = fp_product_data['revenue_%_per_view_per_day']

            sp_product_data: dict = sp_data.get(product_id)
            if sp_product_data:
                vals['sp_hits_view'] = sp_product_data['hits_view']
                vals['sp_revenue'] = sp_product_data['revenue']
                vals['sp_share'] = sp_product_data['revenue_%_per_view_per_day']

            values.append(vals)
        self.env["ozon.report.interest.data"].create(values)

    def _get_period_analysis_data(self, category_id, period_from, period_to) -> dict:
        period_analysis_data = self.env['ozon.analysis_data'].read_group(
            domain=[
                ('product.categories', '=', category_id),
                ('date', '>=', period_from),
                ('date', '<=', period_to),
            ],
            fields=['product', 'hits_view'],
            groupby=['product']
        )
        return period_analysis_data

    def _add_sales_data(self, period_from, period_to, ids_list, data_dict):
        sales = self.env['ozon.sale'].read_group(
            domain=[
                ('product', 'in', ids_list),
                ('date', '>=', period_from),
                ('date', '<=', period_to),
            ],
            fields=['product', 'revenue'],
            groupby=['product']
        )
        for entry in sales:
            product = entry.get('product')
            if product:
                product_id = product[0]
                product_data = data_dict.get(product_id)
                if product_data:
                    product_data['revenue'] += entry['revenue']

    @staticmethod
    def _get_period_data_dict(period_raw_analysis_data) -> tuple:
        data = defaultdict(
            lambda: {
                'hits_view': 0,
                'revenue': 0,
                'revenue_%_per_view_per_day': 0,
            }
        )
        product_ids = []
        for entry in period_raw_analysis_data:
            product = entry.get('product')
            if product:
                product_id = product[0]
                product_ids.append(product_id)
                data[product_id]['hits_view'] += entry.get('hits_view')
            else:
                logger.warning(f"Missing product while action_calculate_interest_report")

        return data, product_ids

