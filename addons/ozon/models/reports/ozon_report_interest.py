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

    # @api.onchange('ozon_categories_id')
    # def _onchange_ozon_categories_id(self):
    #     if self.ozon_categories_id:
    #         interests = self.env['ozon.analysis_data'].search([])
    #         unique_periods = {rec.timestamp_from: rec.timestamp_to for rec in interests}
    #         ozon_analysis_data_period_from = set(self.env["ozon.analysis_data.period"].search([]).mapped('period_from'))
    #         for from_, to in unique_periods.items():
    #             if from_ in ozon_analysis_data_period_from:
    #                 pass
    #             else:
    #                 self.env["ozon.analysis_data.period"].create(
    #                     {
    #                         'period_from': from_,
    #                         'period_to': to,
    #                     }
    #                 )

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

            first_period_analysis_data = self.env['ozon.analysis_data'].search(
                domain=[
                    ('product.categories', '=', record.ozon_categories_id.id),
                    ('timestamp_from', '>=', record.first_period_from - timedelta(days=7)),
                    ('timestamp_to', '<=', record.first_period_to + timedelta(days=7)),
                ],
            )

            first_period_data_per_day = defaultdict(lambda: defaultdict(dict))
            for data in first_period_analysis_data:
                day = data.timestamp_from
                days_qty = (data.timestamp_to - data.timestamp_from).days
                product_id = data.product.id
                avg_hits_view = data.hits_view / days_qty
                avg_hits_tocart = data.hits_tocart / days_qty
                for i in range(days_qty):
                    day += timedelta(days=i)
                    first_period_data_per_day[day][product_id].append(
                        {
                            'product_id': product_id,
                            'date': day,
                            'hits_view': avg_hits_view,
                            'hits_tocart': avg_hits_tocart,
                            'sale_qty': 0,
                            'revenue': 0,
                        }
                    )
            del first_period_analysis_data
            logger.warning(first_period_data_per_day)


            # first_period_data = {
            #     entry['product'][0]: {
            #         'hits_view': entry['hits_view'],
            #         'hits_tocart': entry['hits_tocart'],
            #         'qty': 0,
            #         'revenue': 0,
            #     } for entry in first_period_analysis_data
            # }

            # first_period_sales = self.env["ozon.sale"].read_group(
            #     domain=[
            #         ('product', 'in', list(first_period_data.keys()))
            #     ],
            #     fields=['product', 'qty', 'revenue'],
            #     groupby=['product']
            # )
            # count = 0
            # for entry in first_period_sales:
            #     logger.warning(entry)
            #     count += 1
            #     if count == 2:
            #         break


            # second_period_analysis_data = self.env['ozon.analysis_data'].read_group(
            #     domain=[
            #         ('product.categories', '=', record.ozon_categories_id.id),
            #         ('timestamp_from', '=', record.second_period.period_from),
            #         ('timestamp_to', '=', record.second_period.period_to),
            #     ],
            #     fields=['product', 'hits_view', 'hits_tocart'],
            #     groupby=['product']
            # )
            # second_period_data = {
            #     entry['product'][0]: [entry['hits_view'], entry['hits_tocart']] for entry in second_period_analysis_data
            # }

