import base64
from datetime import datetime
import io
from collections import defaultdict
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import matplotlib.pyplot as plt

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
    ozon_report_task_ids = fields.One2many("ozon.report.task", "ozon_report_id")


class OzonReportTask(models.Model):
    _name = "ozon.report.task"
    _description = "Напоминания и задачи в отчете для менеджера"

    task = fields.Char(string="Задача")
    ozon_report_id = fields.Many2one("ozon.report")
    ozon_categories_id = fields.Many2one("ozon.categories")
    type = fields.Selection([
        ('abc_reminder', 'Напоминание провести ABC анализ'),
        ('abc_expired', 'ABC анализ просрочен'),
        ('bcg_reminder', 'Напоминание создать BCG матрицу'),
        ('bcg_expired', 'BCG матрица просрочена'),
    ])
    sequence = fields.Integer()
    active = fields.Boolean(default=True)


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
    is_calculated = fields.Boolean()

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, f"Доля рынка: {record.ozon_categories_id.name_categories} с "
                                   f"{record.period_from} по {record.period_to}"))
        return res

    def action_do_report_category_market_share(self):
        for record in self:
            if not record.ozon_categories_id:
                raise UserError("Выберите категорию")
            known_share_percentage = 0
            total_amount = 0
            has_null = 0
            for competitor_category_share in record.ozon_report_competitor_category_share_ids:
                if competitor_category_share.category_share == 0:
                    has_null = 1
                known_share_percentage += competitor_category_share.category_share
                total_amount += competitor_category_share.turnover

            if total_amount == 0:
                raise UserError('Суммарная стоимость всех продаж = 0. Не могу посчитать доли рынка.')
            if known_share_percentage == 0:
                raise UserError('Суммарная доля в категории всех продавцов = 0. Не могу посчитать доли рынка.')

            for sale in record.ozon_products_competitors_sale_ids:
                revenue_share_percentage = (sale.orders_sum * known_share_percentage) / total_amount
                sale.revenue_share_percentage = revenue_share_percentage
                sale.orders_avg_price = sale.orders_sum / sale.orders_qty

                ozon_products_competitors_id = sale.ozon_products_competitors_id
                ozon_products_id = sale.ozon_products_id
                if ozon_products_id:
                    sale.ozon_products_id.market_share = revenue_share_percentage
                    if not sale.ozon_products_id.market_share_is_computed:
                        sale.ozon_products_id.market_share_is_computed = True
                elif ozon_products_competitors_id:
                    sale.ozon_products_competitors_id.market_share = revenue_share_percentage
                    if not sale.ozon_products_competitors_id.market_share_is_computed:
                        sale.ozon_products_competitors_id.market_share_is_computed = True

            record.is_calculated = True

            if has_null:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': f'Один из продавцов имеет 0 в столбце Доля в категории. Убедитесь что данные точны.',
                        'type': 'warning',
                        'sticky': True,
                    }
                }


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
    threshold_growth = fields.Float(default=20)
    threshold_market_share = fields.Float(default=10)

    plot = fields.Binary()

    ozon_report_bcg_matrix_product_data_ids = fields.One2many(
        "ozon.report.bcg_matrix.product_data", 'ozon_report_bcg_matrix_id'
    )
    is_applied = fields.Boolean()

    @api.onchange('ozon_report_bcg_matrix_product_data_ids')
    def _onchange_ozon_report_bcg_matrix_product_data_ids(self):
        self.is_applied = False

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

            for period in record.period_prev, record.period_curr:
                check_list = 0
                period_is_calculated = 1
                for seller in period.ozon_report_competitor_category_share_ids:
                    check_list += seller.category_share
                    if not period.is_calculated:
                        period_is_calculated = 0

            if check_list == 0 or not period_is_calculated:
                raise UserError("Перед тем, как рассчитать BCG матрицу, зайдите в 'Отчеты по рынку' "
                                "которые будете использовать как 'Первый период' и 'Период'. "
                                "Заполните данные в столбце 'Доля в категории' для каждого продавца "
                                "(данные можно получить в личном кабинете Ozon), затем кликните "
                                "'Операции' > 'Рассчитать долю рынка товаров'")

            # Market growth rate
            # products growth rate
            products_with_turnovers = defaultdict(lambda: {
                'prev_daily_share': 0,
                'curr_daily_share': 0,
                'curr_market_share': 0,
                'product_growth_rate': 0,
                'in_both_periods': 0,
                'quadrant': None
            })
            # fill the start values
            days_prev = (record.period_prev.period_to - record.period_prev.period_from).days
            for sale in record.period_prev.ozon_products_competitors_sale_ids:
                if sale.ozon_products_id:
                    products_with_turnovers[sale.ozon_products_id][
                        'prev_daily_share'] += sale.revenue_share_percentage / days_prev
                    products_with_turnovers[sale.ozon_products_id]['in_both_periods'] += 1

            days_curr = (record.period_curr.period_to - record.period_curr.period_from).days
            for sale in record.period_curr.ozon_products_competitors_sale_ids:
                if sale.ozon_products_id:
                    products_with_turnovers[sale.ozon_products_id][
                        'curr_daily_share'] += sale.revenue_share_percentage / days_curr
                    products_with_turnovers[sale.ozon_products_id]['in_both_periods'] += 1
                    products_with_turnovers[sale.ozon_products_id]['curr_market_share'] = sale.revenue_share_percentage

            # get computed values
            max_growth_value = float('-inf')
            max_curr_market_share = float('-inf')
            for product, turnovers in products_with_turnovers.items():
                prev_value = turnovers.get('prev_daily_share')
                curr_value = turnovers.get('curr_daily_share')
                if prev_value:
                    # product_growth_rate = ((100 * curr_value) / prev_value) - 100
                    product_growth_rate = ((curr_value - prev_value) / prev_value) * 100
                    turnovers['product_growth_rate'] = product_growth_rate
                    # find max values
                    if product_growth_rate > max_growth_value:
                        max_growth_value = product_growth_rate
                    if turnovers.get('curr_market_share') > max_curr_market_share:
                        max_curr_market_share = turnovers.get('curr_market_share')
                else:
                    if curr_value:
                        turnovers['product_growth_rate'] = 100
                        # find max values
                        if 100 > max_growth_value:
                            max_growth_value = 100
                        if turnovers.get('curr_market_share') > max_curr_market_share:
                            max_curr_market_share = turnovers.get('curr_market_share')

            # create report
            quadrants, products_data, colors = self._get_quadrants__products_data__colors(
                products_with_turnovers, record, max_growth_value, max_curr_market_share
            )
            products_data = self._create_plot_and_save(quadrants, products_data, colors, record)

            self._write_bcg_data_to_models(record, products_data)
            # update
            record.ozon_categories_id.bcg_matrix_last_update = datetime.now()

    @staticmethod
    def _get_quadrants__products_data__colors(
            products_data: defaultdict, record, max_growth: float, max_share: float
    ) -> tuple:
        threshold_growth = (record.threshold_growth * max_growth) / 100
        threshold_market_share = (record.threshold_market_share * max_share) / 100

        quadrants = {
            'Звезды': [],
            'Дойные коровы': [],
            'Проблемы': [],
            'Собаки': []
        }

        stars_qty = 0
        questions_qty = 0
        cows_qty = 0
        dogs_qty = 0
        for product, data in products_data.items():
            if data['product_growth_rate'] >= threshold_growth and \
                    data['curr_market_share'] >= threshold_market_share:
                quadrants['Звезды'].append((product, data))
                data['quadrant'] = 'a'
                stars_qty += 1
            elif data['product_growth_rate'] >= threshold_growth and \
                    data['curr_market_share'] < threshold_market_share:
                quadrants['Проблемы'].append((product, data))
                data['quadrant'] = 'c'
                questions_qty += 1
            elif data['product_growth_rate'] < threshold_growth and \
                    data['curr_market_share'] >= threshold_market_share:
                quadrants['Дойные коровы'].append((product, data))
                data['quadrant'] = 'b'
                cows_qty += 1
            else:
                quadrants['Собаки'].append((product, data))
                data['quadrant'] = 'd'
                dogs_qty += 1

        colors = {
            f'Звезды ({stars_qty})': 'blue',
            f'Проблемы ({questions_qty})': 'orange',
            f'Дойные коровы ({cows_qty})': 'green',
            f'Собаки ({dogs_qty})': 'red'
        }
        quadrants[f'Звезды ({stars_qty})'] = quadrants.pop('Звезды')
        quadrants[f'Дойные коровы ({cows_qty})'] = quadrants.pop('Дойные коровы')
        quadrants[f'Проблемы ({questions_qty})'] = quadrants.pop('Проблемы')
        quadrants[f'Собаки ({dogs_qty})'] = quadrants.pop('Собаки')

        return quadrants, products_data, colors

    @staticmethod
    def _create_plot_and_save(quadrants: dict, products_data: defaultdict, colors: dict, record) -> defaultdict:
        # Plot the BCG matrix
        fig, ax = plt.subplots()
        for quadrant, products in quadrants.items():
            x = [data['curr_market_share'] for _, data in products]
            y = [data['product_growth_rate'] for _, data in products]
            ax.scatter(x, y, label=quadrant, color=colors[quadrant])

        # Add labels and legend
        ax.set_xlabel('Доля рынка (%)')
        ax.set_ylabel('Темпы роста (%)')
        ax.set_title(f'BCG Матрица')
        ax.legend()

        buffer = io.BytesIO()
        fig.savefig(buffer, format='png')
        buffer.seek(0)
        binary_data = base64.b64encode(buffer.read())
        record.plot = binary_data
        plt.close(fig)

        return products_data

    def _write_bcg_data_to_models(self, record, products_data: defaultdict):
        for data in record.ozon_report_bcg_matrix_product_data_ids:
            record.ozon_report_bcg_matrix_product_data_ids = [(2, data.id, 0)]

        products_of_category = self.env['ozon.products'].search([
            ('categories', '=', record.ozon_categories_id.id)
        ])

        for product in products_of_category:
            new_product_data = products_data.get(product)
            bcg_group_val = 'f'
            if new_product_data and new_product_data.get('quadrant'):
                if new_product_data.get('quadrant') != product.bcg_group:
                    bcg_group_val = new_product_data.get('quadrant')
            if not new_product_data and product.bcg_group != 'e':
                bcg_group_val = 'e'
            self.env["ozon.report.bcg_matrix.product_data"].create({
                'ozon_report_bcg_matrix_id': record.id,
                'ozon_products_id': product.id,
                'bcg_group_curr': product.bcg_group,
                'prev_daily_share': new_product_data.get('prev_daily_share') if new_product_data else False,
                'curr_daily_share': new_product_data.get('curr_daily_share') if new_product_data else False,
                'curr_market_share': new_product_data.get('curr_market_share') if new_product_data else False,
                'product_growth_rate': new_product_data.get('product_growth_rate') if new_product_data else False,
                'bcg_group': bcg_group_val
            })
        record.is_applied = False

    def action_write_updated_bcg_group_to_products(self):
        for product_data in self.ozon_report_bcg_matrix_product_data_ids:
            logger.warning(product_data.bcg_group)
            product = product_data.ozon_products_id
            if product_data.bcg_group != 'f':
                product.bcg_group = product_data.bcg_group
                if not product.bcg_group_is_computed:
                    product_data.ozon_products_id.bcg_group_is_computed = True
                product_data.bcg_group_curr = product_data.bcg_group
            product._touch_bcg_group_indicator(product)

        self.is_applied = True


class OzonReportBcgMatrixProductData(models.Model):
    _name = "ozon.report.bcg_matrix.product_data"
    _description = "Данные по товарам для вывода в отчет BCG матрицы"

    ozon_report_bcg_matrix_id = fields.Many2one("ozon.report.bcg_matrix")
    ozon_products_id = fields.Many2one("ozon.products")
    prev_daily_share = fields.Float(digits=(12, 5))
    curr_daily_share = fields.Float(digits=(12, 5))
    curr_market_share = fields.Float(digits=(12, 5))
    product_growth_rate = fields.Float(digits=(12, 5))
    bcg_group_curr = fields.Selection([
        ('a', 'Звезда'), ('b', 'Дойная корова'), ('c', 'Проблема'), ('d', 'Собака'), ('e', 'Нет данных'), ('f', '')
    ])
    bcg_group = fields.Selection([
        ('a', 'Звезда'), ('b', 'Дойная корова'), ('c', 'Проблема'), ('d', 'Собака'), ('e', 'Нет данных'), ('f', '')
    ])


