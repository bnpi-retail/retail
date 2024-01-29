import traceback

from odoo import models, fields
from odoo.exceptions import UserError
import logging
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger()


class AbcAnalysis(models.Model):
    _name = "ozon.abc_analysis"
    _description = "ABC Анализ"

    ozon_categories_id = fields.Many2one('ozon.categories')
    period_from = fields.Date()
    period_to = fields.Date()
    done = fields.Boolean()

    ozon_products_ids = fields.Many2many("ozon.products")

    def action_do_abc_analysis(self):
        # exceptions process
        category = self.ozon_categories_id
        if not category:
            raise UserError('Выберите категорию')
        now = datetime.now().date()
        if not self.period_from or self.period_from > now:
            raise UserError('Выберите правильную дату начала периода.')
        if not self.period_to or self.period_to > now:
            raise UserError('Выберите правильную дату окончания периода.')
        if self.period_from > self.period_to:
            raise UserError('Выберите правильный период.')

        ozon_sales = self.env['ozon.sale'].search([
            ('product.categories', '=', 'ozon_categories_id'),
            ('date', '>', self.period_from),
            ('date', '<', self.period_to),
        ])

        # get products
        products_revenues = defaultdict(float)
        total_period_revenue = 0
        for sale in ozon_sales:
            try:
                products_revenues[sale.product] += sale.revenue
                total_period_revenue += sale.revenue
            except Exception:
                logger.warning(f"abc ananysis error: {traceback.format_exc()}")

        # compute percentage
        products_percentage = [(product, [(revenue * 100) / total_period_revenue]) for product, revenue in
                               products_revenues.items()]
        products_percentage.sort(key=lambda x: x[1])

        # compute cumulative percentage
        prev_percent = 0
        for product in products_percentage:
            percent = product[1][0]
            prev_percent += percent
            product[1].append(prev_percent)

        # set groups
        for product in products_percentage:
            if product[1][1] <= 80:
                product[1].append('A')
            elif product[1][1] <= 95:
                product[1].append('B')
            else:
                product[1].append('C')

        # write data


