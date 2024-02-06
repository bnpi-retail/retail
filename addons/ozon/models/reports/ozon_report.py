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
            # common
            total_category_growth_rate = 0
            period_prev_category_market_turnover = 0
            seller_prev = record.period_prev.ozon_report_competitor_category_share_ids[0]
            if seller_prev.category_share != 0:
                period_prev_category_market_turnover = (100 * seller_prev.turnover) / seller_prev.category_share

            period_curr_category_market_turnover = 0
            seller_curr = record.period_curr.ozon_report_competitor_category_share_ids[0]
            if seller_curr.category_share != 0:
                period_curr_category_market_turnover = (100 * seller_curr.turnover) / seller_curr.category_share

            if period_prev_category_market_turnover == 0:
                raise UserError('Оборот за предыдущий период равен 0- '
                                'нельзя посчитать темп роста рынка категории.')
            total_category_growth_rate = ((period_curr_category_market_turnover * 100) /
                                          period_prev_category_market_turnover) - 100

            # products growth rate
            products_with_turnovers = defaultdict(lambda: {
                'prev_turnover': 0,
                'curr_turnover': 0,
                'curr_market_share': 0,
                'product_growth_rate': 0,
                'in_both_periods': 0
            })
            for sale in record.period_prev.ozon_products_competitors_sale_ids:
                if sale.ozon_products_id:
                    products_with_turnovers[sale.ozon_products_id]['prev_turnover'] = sale.orders_sum
                    products_with_turnovers[sale.ozon_products_id]['in_both_periods'] += 1
            for sale in record.period_curr.ozon_products_competitors_sale_ids:
                if sale.ozon_products_id:
                    products_with_turnovers[sale.ozon_products_id]['curr_turnover'] = sale.orders_sum
                    products_with_turnovers[sale.ozon_products_id]['in_both_periods'] += 1
                    products_with_turnovers[sale.ozon_products_id]['curr_market_share'] = sale.revenue_share_percentage

            for product, turnovers in products_with_turnovers.items():
                if turnovers.get('in_both_periods'):
                    prev_value = turnovers.get('prev_turnover')
                    curr_value = turnovers.get('curr_turnover')
                    if prev_value:
                        product_growth_rate = ((100 * curr_value) / prev_value) - 100
                        turnovers['product_growth_rate'] = product_growth_rate
                    else:
                        logger.warning("Can't calculate product_growth_rate because zero division")

            self._create_plot_and_save(products_with_turnovers)

    def _create_plot_and_save(self, products_data: defaultdict):
        # Classify products into quadrants based on growth rate and market share
        quadrants = {
            'Star': [],
            'Question Mark': [],
            'Cash Cow': [],
            'Dog': []
        }

        for product, data in products_data.items():
            if data['product_growth_rate'] >= 10 and data['curr_market_share'] >= 10:
                quadrants['Star'].append((product, data))
            elif data['product_growth_rate'] >= 10 and data['curr_market_share'] < 10:
                quadrants['Question Mark'].append((product, data))
            elif data['product_growth_rate'] < 10 and data['curr_market_share'] >= 10:
                quadrants['Cash Cow'].append((product, data))
            else:
                quadrants['Dog'].append((product, data))

        # Plot the BCG matrix
        fig, ax = plt.subplots()

        for quadrant, products in quadrants.items():
            x = [data['curr_market_share'] for _, data in products]
            y = [data['product_growth_rate'] for _, data in products]
            ax.scatter(x, y, label=quadrant)

        # Add labels and legend
        ax.set_xlabel('Market Share (%)')
        ax.set_ylabel('Market Growth Rate (%)')
        ax.set_title('BCG Matrix')
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
