import base64
import io
from collections import defaultdict
from odoo import models, fields
from odoo.exceptions import UserError
import logging
import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)


class OzonReport(models.Model):
    _name = "ozon.report"
    _description = "Отчеты для менеджеров"

    # create_date
    active = fields.Boolean(default=True)
    res_users_id = fields.Many2one('res.users')
    lots_quantity = fields.Integer()
    ozon_products_ids = fields.Many2many("ozon.products")
    type = fields.Selection([('indicators', 'Indicators')])


class OzonReportCategoryMarketShare(models.Model):
    _name = "ozon.report_category_market_share"
    _description = "Отчет из файла по продажам товаров ближайших конкурентов и доле рынка занимаемой товарами"

    ozon_categories_id = fields.Many2one('ozon.categories')
    period_from = fields.Date()
    period_to = fields.Date()

    ozon_products_competitors_sale_ids = fields.One2many(
        "ozon.products_competitors.sale", 'ozon_report_category_market_share')
    ozon_report_competitor_category_share_ids = fields.One2many(
        "ozon.report.competitor_category_share", 'ozon_report_category_market_share'
    )

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, f"Доля рынка: {record.ozon_categories_id.name_categories} с "
                       f"{record.period_from} по {record.period_to}"))
        return res

    def action_do_report_category_market_share(self):
        for record in self:
            known_share_percentage = 0
            total_amount = 0
            for competitor_category_share in record.ozon_report_competitor_category_share_ids:
                known_share_percentage += competitor_category_share.category_share
                total_amount += competitor_category_share.turnover

            if total_amount == 0:
                raise UserError('Суммарная стоимость всех продаж = 0. Нельзя посчитать доли рынка.')

            for sale in record.ozon_products_competitors_sale_ids:
                revenue_share_percentage = (sale.orders_sum * known_share_percentage) / total_amount
                sale.revenue_share_percentage = revenue_share_percentage
                sale.orders_avg_price = sale.orders_sum / sale.orders_qty

                ozon_products_competitors_id = sale.ozon_products_competitors_id
                ozon_products_id = sale.ozon_products_id
                if ozon_products_id:
                    sale.ozon_products_id.market_share = revenue_share_percentage
                elif ozon_products_competitors_id:
                    sale.ozon_products_competitors_id.market_share = revenue_share_percentage


class OzonReportCompetitorCategoryShare(models.Model):
    _name = "ozon.report.competitor_category_share"
    _description = "Место и доля продаж конкурентов в категории"

    place = fields.Integer()
    seller_name = fields.Char()
    category_share = fields.Float()
    turnover = fields.Float()
    turnover_growth = fields.Float()

    ozon_report_category_market_share = fields.Many2one("ozon.report_category_market_share")


class OzonReportCompetitorBCGMatrix(models.Model):
    _name = "ozon.report.bcg_matrix"
    _description = "Модель для создания BCG матрицы по категории"

    ozon_categories_id = fields.Many2one('ozon.categories')
    period_prev = fields.Many2one("ozon.report_category_market_share")
    period_curr = fields.Many2one("ozon.report_category_market_share")

    plot = fields.Binary()

    def action_run_bcg_matrix_calculation(self):
        for record in self:
            if not record.ozon_categories_id:
                raise UserError('Выберите категорию')
            if not record.period_prev:
                raise UserError('Выберите период')
            if not record.period_curr:
                raise UserError('Выберите период')
            if record.period_prev == record.period_curr:
                raise UserError('Выберите разные периоды')
            if (
                    record.period_prev.period_from > record.period_curr.period_from or
                    record.period_prev.period_to > record.period_curr.period_to
            ):
                raise UserError('Проверьте даты выбранных периодов')

            # Market growth rate
            # products growth rate
            products_with_turnovers = defaultdict(lambda: {
                'prev_turnover': 0,
                'curr_turnover': 0,
                'curr_market_share': 0,
                'product_growth_rate': 0,
                'in_both_periods': 0
            })
            days_prev = (record.period_prev.period_to - record.period_prev.period_from).days
            for sale in record.period_prev.ozon_products_competitors_sale_ids:
                if sale.ozon_products_id:
                    products_with_turnovers[sale.ozon_products_id]['prev_turnover'] = sale.orders_sum / days_prev
                    products_with_turnovers[sale.ozon_products_id]['in_both_periods'] += 1

            days_curr = (record.period_curr.period_to - record.period_curr.period_from).days
            for sale in record.period_curr.ozon_products_competitors_sale_ids:
                if sale.ozon_products_id:
                    products_with_turnovers[sale.ozon_products_id]['curr_turnover'] = sale.orders_sum / days_curr
                    products_with_turnovers[sale.ozon_products_id]['in_both_periods'] += 1
                    products_with_turnovers[sale.ozon_products_id]['curr_market_share'] = sale.revenue_share_percentage

            max_growth_value = float('-inf')
            max_curr_market_share = float('-inf')
            for product, turnovers in products_with_turnovers.items():
                if turnovers.get('in_both_periods'):
                    prev_value = turnovers.get('prev_turnover')
                    curr_value = turnovers.get('curr_turnover')
                    if prev_value:
                        # product_growth_rate = ((100 * curr_value) / prev_value) - 100
                        product_growth_rate = ((curr_value - prev_value) / prev_value) * 100
                        turnovers['product_growth_rate'] = product_growth_rate
                        if product_growth_rate > max_growth_value:
                            max_growth_value = product_growth_rate
                        if turnovers.get('curr_market_share') > max_curr_market_share:
                            max_curr_market_share = turnovers.get('curr_market_share')
                    else:
                        logger.warning("Can't calculate product_growth_rate because zero division")
                        # prev_value += 0.00000001
                        # product_growth_rate = ((curr_value - prev_value) / prev_value) * 100
                        # turnovers['product_growth_rate'] = product_growth_rate

            # growth rate to standard values
            # max_growth_value = float('-inf')
            # min_growth_value = float('inf')
            # for product, turnovers in products_with_turnovers.items():
            #     product_growth_rate = turnovers.get('product_growth_rate')
            #     if product_growth_rate > max_growth_value:
            #         max_growth_value = product_growth_rate
            #     if product_growth_rate < min_growth_value:
            #         min_growth_value = product_growth_rate
            #
            # for product, turnovers in products_with_turnovers.items():
            #     product_growth_rate = turnovers.get('product_growth_rate')
            #     turnovers['product_growth_rate'] = (product_growth_rate * 10) / max_growth_value

            # curr_market_share to standard values
            # max_curr_market_share = float('-inf')
            # for product, turnovers in products_with_turnovers.items():
            #     curr_market_share = turnovers.get('curr_market_share')
            #     if curr_market_share > max_curr_market_share:
            #         max_curr_market_share = curr_market_share
            #
            # for product, turnovers in products_with_turnovers.items():
            #     curr_market_share = turnovers.get('curr_market_share')
            #     turnovers['curr_market_share'] = curr_market_share / max_curr_market_share

            self._create_plot_and_save(products_with_turnovers, max_growth_value, max_curr_market_share)

    def _create_plot_and_save(self, products_data: defaultdict, max_growth, max_share):
        quadrants = {
            'Звезды': [],
            'Проблемы': [],
            'Дойные коровы': [],
            'Собаки': []
        }

        threshold_growth = (20 * max_growth) / 100
        threshold_market_share = (10 * max_share) / 100

        for product, data in products_data.items():
            if data['product_growth_rate'] >= threshold_growth and data['curr_market_share'] >= threshold_market_share:
                quadrants['Звезды'].append((product, data))
            elif data['product_growth_rate'] >= threshold_growth and data['curr_market_share'] < threshold_market_share:
                quadrants['Проблемы'].append((product, data))
            elif data['product_growth_rate'] < threshold_growth and data['curr_market_share'] >= threshold_market_share:
                quadrants['Дойные коровы'].append((product, data))
            else:
                quadrants['Собаки'].append((product, data))

        # Plot the BCG matrix
        fig, ax = plt.subplots()

        for quadrant, products in quadrants.items():
            x = [data['curr_market_share'] for _, data in products]
            y = [data['product_growth_rate'] for _, data in products]
            ax.scatter(x, y, label=quadrant)

        # Add labels and legend
        ax.set_xlabel('Доля рынка (%)')
        ax.set_ylabel('Темпы роста (%)')
        ax.set_title('BCG Матрица')
        ax.legend()

        buffer = io.BytesIO()
        fig.savefig(buffer, format='png')
        buffer.seek(0)
        # Convert plot to a byte string
        binary_data = base64.b64encode(buffer.read())
        # Save the byte string to the binary field
        self.plot = binary_data
        # Close the plot to prevent displaying it
        plt.close(fig)
