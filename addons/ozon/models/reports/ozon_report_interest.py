import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class OzonReportInterest(models.Model):
    _name = "ozon.report.interest"
    _description = "Отчет по соотношению интереса к продукту и продажам"

    ozon_categories_id = fields.Many2one('ozon.categories')

    first_period_from = fields.Date()
    first_period_to = fields.Date()

    second_period_from = fields.Date()
    second_period_to = fields.Date()

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

            logger.warning(fp_data)
            # logger.warning(sp_data)


    def _get_period_analysis_data(self, category_id, period_from, period_to) -> dict:
        period_analysis_data = self.env['ozon.analysis_data'].read_group(
            domain=[
                ('product.categories', '=', category_id),
                ('date', '>=', period_from),
                ('date', '<=', period_to),
            ],
            fields=['product', 'hits_view', 'hits_tocart'],
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
            fields=['product', 'qty', 'revenue'],
            groupby=['product']
        )
        for entry in sales:
            product = entry.get('product')
            if product:
                product_id = product[0]
                product_data = data_dict.get(product_id)
                if product_data:
                    product_data['sale_qty'] += entry['qty']
                    product_data['revenue'] += entry['revenue']

    @staticmethod
    def _get_period_data_dict(period_raw_analysis_data) -> tuple:
        data = defaultdict(
            lambda: {
                'hits_view': 0,
                'hits_tocart': 0,
                'sale_qty': 0,
                'revenue': 0,
            }
        )
        product_ids = []
        for entry in period_raw_analysis_data:
            product = entry.get('product')
            if product:
                product_id = product[0]
                product_ids.append(product_id)
                data[product_id]['hits_view'] += entry.get('hits_view')
                data[product_id]['hits_tocart'] += entry.get('hits_tocart')
            else:
                logger.warning(f"Missing product while action_calculate_interest_report")

        return data, product_ids
