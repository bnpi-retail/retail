import traceback
import logging

from odoo import models, fields
from odoo.exceptions import UserError
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger()


class AbcAnalysis(models.Model):
    _name = "ozon.abc_analysis"
    _description = "ABC Анализ"

    ozon_categories_id = fields.Many2one('ozon.categories')
    period_from = fields.Date()
    period_to = fields.Date()

    ozon_products_ids = fields.Many2many("ozon.products")

    def action_do_abc_analysis(self):
        for record in self:
            # exceptions process
            category = record.ozon_categories_id
            if not category:
                raise UserError('Выберите категорию')
            now = datetime.now().date()
            if not record.period_from or record.period_from > now:
                raise UserError('Выберите правильную дату начала периода.')
            if not record.period_to:
                raise UserError('Выберите дату окончания периода.')
            if record.period_from > record.period_to:
                raise UserError('Выберите правильный период.')

            ozon_sales = record.env['ozon.sale'].search([
                ('product.categories', '=', category.id),
                ('date', '>', record.period_from),
                ('date', '<', record.period_to),
            ])
            all_category_products = record.env['ozon.products'].search([
                ('categories', '=', category.id)
            ])

            # get products
            products_revenues = defaultdict(float)
            total_period_revenue = 0
            for product in all_category_products:
                products_revenues[product] = 0
            for sale in ozon_sales:
                try:
                    products_revenues[sale.product] += sale.revenue
                    total_period_revenue += sale.revenue
                except Exception:
                    logger.warning(f"abc ananysis error: {traceback.format_exc()}")

            # compute percentage
            if total_period_revenue:
                products_percentage = [(product, [(revenue * 100) / total_period_revenue]) for product, revenue in
                                       products_revenues.items()]
                products_percentage.sort(key=lambda x: x[1][0], reverse=True)
            else:
                products_percentage = [(product, [0]) for product, revenue in
                                       products_revenues.items()]

            # compute cumulative percentage
            prev_percent = 0
            for product in products_percentage:
                percent = product[1][0]
                prev_percent += percent
                product[1].append(prev_percent)

            # set groups
            product_ids = []
            for product in products_percentage:
                if 0 < product[1][1] <= 80:
                    product[1].append('A')
                elif 80 < product[1][1] <= 95:
                    product[1].append('B')
                else:
                    product[1].append('C')
                product_ids.append(product[0].id)

            # write data
            record.ozon_products_ids = product_ids
            for product in products_percentage:
                product[0].revenue_share_temp = product[1][0]
                product[0].revenue_cumulative_share_temp = product[1][1]
                product[0].abc_group = product[1][2]
                product[0]._touch_abc_group_indicator(product[0])

            category.abc_group_last_update = datetime.now()
