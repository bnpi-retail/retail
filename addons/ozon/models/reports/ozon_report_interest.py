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

    first_period = fields.Many2one("ozon.analysis_data.period")
    second_period = fields.Many2one("ozon.analysis_data.period")

    @api.onchange('ozon_categories_id')
    def _onchange_ozon_categories_id(self):
        if self.ozon_categories_id:
            interests = self.env['ozon.analysis_data'].search([])
            unique_periods = {rec.timestamp_from: rec.timestamp_to for rec in interests}
            ozon_analysis_data_period_from = set(self.env["ozon.analysis_data.period"].search([]).mapped('period_from'))
            for from_, to in unique_periods.items():
                if from_ in ozon_analysis_data_period_from:
                    pass
                else:
                    self.env["ozon.analysis_data.period"].create(
                        {
                            'period_from': from_,
                            'period_to': to,
                        }
                    )

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

            first_period_interest_data = self.env["ozon.analysis_data"].search([
                ('product.categories', '=', record.ozon_categories_id.id),
                ('timestamp_from', '<=', record.first_period_from),
                ('timestamp_to', '>=', record.first_period_from),
            ])
            logger.warning(first_period_interest_data)

            second_period_interest_data = self.env["ozon.analysis_data"].search([
                ('product.categories', '=', record.ozon_categories_id.id),
                ('timestamp_from', '<=', record.second_period_from),
                ('timestamp_to', '>=', record.second_period_to),
            ])
            logger.warning(second_period_interest_data)

            # for rec in second_period_interest_data:
            #     new = self.env["ozon.analysis_data"].create({
            #         'product': rec.product.id,
            #         'timestamp_from': rec.timestamp_from - timedelta(days=10),
            #         'timestamp_to': rec.timestamp_to - timedelta(days=10),
            #         'hits_view': rec.hits_view * random.choice((0.9, 0.8, 0.7, 0.6)),
            #         'hits_tocart': rec.hits_tocart * random.choice((0.9, 0.8, 0.7, 0.6)),
            #     })
            #     logger.warning(new)
