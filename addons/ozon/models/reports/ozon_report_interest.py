import base64
import io
import logging
import matplotlib.pyplot as plt
from odoo import models, fields
from odoo.exceptions import UserError
from collections import defaultdict

logger = logging.getLogger(__name__)


class OzonReportInterestData(models.Model):
    _name = "ozon.report.interest.data"
    _description = "Строки данных в отчете по интересам"

    ozon_products_id = fields.Many2one("ozon.products")
    fp_hits_view = fields.Float(digits=(12, 5))
    sp_hits_view = fields.Float(digits=(12, 5))
    fp_qty = fields.Float(digits=(12, 5))
    sp_qty = fields.Float(digits=(12, 5))
    fp_share = fields.Float(digits=(12, 5))
    sp_share = fields.Float(digits=(12, 5))
    product_growth_rate = fields.Float(digits=(12, 5))
    interest_group = fields.Selection([
        ('a', 'Звезда'), ('b', 'Дойная корова'), ('c', 'Проблема'), ('d', 'Собака'), ('e', 'Нет данных'), ('f', '')
    ])
    bcg_group = fields.Selection([
        ('a', 'Звезда'), ('b', 'Дойная корова'), ('c', 'Проблема'), ('d', 'Собака'), ('e', 'Нет данных'), ('f', '')
    ])

    ozon_report_interest_id = fields.Many2one("ozon.report.interest")


class OzonReportInterest(models.Model):
    _name = "ozon.report.interest"
    _description = "Отчет по соотношению интереса к продукту и продажам"

    ozon_categories_id = fields.Many2one('ozon.categories')

    first_period_from = fields.Date()
    first_period_to = fields.Date()

    second_period_from = fields.Date()
    second_period_to = fields.Date()

    threshold_growth = fields.Float(default=20)
    threshold_share = fields.Float(default=10)

    ozon_report_interest_data_ids = fields.One2many(
        "ozon.report.interest.data",
        'ozon_report_interest_id'
    )
    fp_revenue_per_hit_view_per_day = fields.Float(digits=(12, 5))
    sp_revenue_per_hit_view_per_day = fields.Float(digits=(12, 5))
    fp_qty_per_hit_view_per_day = fields.Float(digits=(12, 5))
    sp_qty_per_hit_view_per_day = fields.Float(digits=(12, 5))
    fp_to_cart_per_hit_view_per_day = fields.Float(digits=(12, 5))
    sp_to_cart_per_hit_view_per_day = fields.Float(digits=(12, 5))

    plot = fields.Binary()

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

            category_id = record.ozon_categories_id.id
            all_category_product_ids_groups = self.env["ozon.products"].search([
                ('categories', '=', category_id)
            ]).mapped(lambda r: (r.id, r.bcg_group))

            # calculate data
            res_1 = self._calculate_qty_per_view_daily(
                record.first_period_from, record.first_period_to, fp_data)
            fp_revenue_per_view_per_day_relation, fp_to_cart_per_view_per_day, fp_qty_per_view_per_day = res_1

            res_2 = self._calculate_qty_per_view_daily(
                record.second_period_from, record.second_period_to, sp_data)
            sp_revenue_per_view_per_day_relation, sp_to_cart_per_view_per_day, sp_qty_per_view_per_day = res_2

            # record common values
            record.fp_revenue_per_hit_view_per_day = fp_revenue_per_view_per_day_relation
            record.fp_to_cart_per_hit_view_per_day = fp_to_cart_per_view_per_day

            record.fp_qty_per_hit_view_per_day = fp_qty_per_view_per_day
            record.sp_qty_per_hit_view_per_day = sp_qty_per_view_per_day

            record.sp_revenue_per_hit_view_per_day = sp_revenue_per_view_per_day_relation
            record.sp_to_cart_per_hit_view_per_day = sp_to_cart_per_view_per_day

            # merge periods + all category products
            both_period_data, max_growth_value, max_curr_share = self._merge_fp_sp_data_and_calc_reminds_values(
                fp_data, sp_data, all_category_product_ids_groups
            )

            quadrants, colors = self._assign_groups(record, both_period_data, max_growth_value, max_curr_share)

            # record values
            self._record_data(record, both_period_data)

            # create plot
            self._create_plot_and_save(quadrants, colors, record)

    @staticmethod
    def _assign_groups(record, both_period_data, max_growth_value, max_curr_share):
        threshold_growth = (record.threshold_growth * max_growth_value) / 100
        threshold_share = (record.threshold_share * max_curr_share) / 100
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
        for product, data in both_period_data.items():
            if data['product_growth_rate'] >= threshold_growth and \
                    data['sp_qty_%_per_view_per_day'] >= threshold_share:
                quadrants['Звезды'].append((product, data))
                data['quadrant'] = 'a'
                stars_qty += 1
            elif data['product_growth_rate'] >= threshold_growth and \
                    data['sp_qty_%_per_view_per_day'] < threshold_share:
                quadrants['Проблемы'].append((product, data))
                data['quadrant'] = 'c'
                questions_qty += 1
            elif data['product_growth_rate'] < threshold_growth and \
                    data['sp_qty_%_per_view_per_day'] >= threshold_share:
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

        return quadrants, colors

    @staticmethod
    def _merge_fp_sp_data_and_calc_reminds_values(fp_data, sp_data, ids) -> tuple:
        all_category_product_ids_groups = ids
        both_period_data = defaultdict(dict)
        max_growth_value = float('-inf')
        max_curr_share = float('-inf')
        for product_id, bcg_group in all_category_product_ids_groups:
            vals = {
                "fp_hits_view": 0,
                "sp_hits_view": 0,
                "fp_qty": 0,
                "sp_qty": 0,
                "fp_qty_%_per_view_per_day": 0,
                "sp_qty_%_per_view_per_day": 0,
                "product_growth_rate": 0,
                "quadrant": None,
                "bcg_group": bcg_group,
            }
            fp_product_data: dict = fp_data.get(product_id)
            fp_value = 0
            if fp_product_data:
                vals['fp_hits_view'] = fp_product_data['hits_view']
                vals['fp_qty'] = fp_product_data['qty']
                fp_value = fp_product_data['qty_%_per_view_per_day']
                vals['fp_qty_%_per_view_per_day'] = fp_value

            sp_product_data: dict = sp_data.get(product_id)
            sp_value = 0
            if sp_product_data:
                vals['sp_hits_view'] = sp_product_data['hits_view']
                vals['sp_qty'] = sp_product_data['qty']
                sp_value = sp_product_data['qty_%_per_view_per_day']
                vals['sp_qty_%_per_view_per_day'] = sp_value
                if max_curr_share < sp_value:
                    max_curr_share = sp_value

            # calc growth rate
            if fp_value:
                product_growth_rate = ((sp_value - fp_value) / fp_value) * 100
            elif not fp_value and sp_value:
                product_growth_rate = 100
            else:
                product_growth_rate = 0
            if product_growth_rate > max_growth_value:
                max_growth_value = product_growth_rate
            vals['product_growth_rate'] = product_growth_rate

            both_period_data[product_id] = vals

        return both_period_data, max_growth_value, max_curr_share

    @staticmethod
    def _calculate_qty_per_view_daily(period_from, period_to, data_dict: defaultdict) -> tuple:
        days = (period_to - period_from).days
        if days == 0:
            raise UserError("Количество дней в периоде равно 0")

        period_total_hits_view = 0
        period_total_revenue = 0
        period_total_qty = 0
        period_total_to_cart = 0
        for product_id, data in data_dict.items():
            period_total_hits_view += data['hits_view']
            period_total_revenue += data['revenue']
            period_total_to_cart += data['hits_tocart']
            period_total_qty += data['qty']

        period_total_hits_view /= days
        period_total_revenue /= days
        period_total_to_cart /= days
        period_total_qty /= days

        if period_total_hits_view == 0:
            period_total_hits_view = 0.000001

        period_revenue_per_view_per_day = period_total_revenue / period_total_hits_view
        period_qty_per_view_per_day = period_total_qty / period_total_hits_view
        period_to_cart_per_view_per_day = period_total_to_cart / period_total_hits_view

        for product_id, data in data_dict.items():
            hits_view = data['hits_view']
            qty = data['qty']
            product_qty_per_view = qty / hits_view if hits_view != 0 else 0.000001
            product_qty_per_view_per_day = product_qty_per_view / days
            if period_qty_per_view_per_day:
                qty_per_view_per_day_percent = (
                    product_qty_per_view_per_day * 100) / period_qty_per_view_per_day
            else:
                qty_per_view_per_day_percent = 0
            data['qty_%_per_view_per_day'] = qty_per_view_per_day_percent

        return period_revenue_per_view_per_day, period_to_cart_per_view_per_day, period_qty_per_view_per_day

    def _record_data(self, record, both_period_data):
        query = """
                    DELETE FROM ozon_report_interest_data
                    WHERE id IN %s
                """
        if record.ozon_report_interest_data_ids.ids:
            self.env.cr.execute(query, (tuple(record.ozon_report_interest_data_ids.ids),))
            logger.warning(f"delete from ozon_products_indicator_summary records with ids ")

        record_id = record.id
        values = []
        for product_id, data in both_period_data.items():
            vals = {
                "ozon_products_id": product_id,
                "fp_hits_view": data['fp_hits_view'],
                "sp_hits_view": data['sp_hits_view'],
                "fp_qty": data['fp_qty'],
                "sp_qty": data['sp_qty'],
                "fp_share": data['fp_qty_%_per_view_per_day'],
                "sp_share": data['sp_qty_%_per_view_per_day'],
                "product_growth_rate": data['product_growth_rate'],
                "interest_group": data['quadrant'],
                "bcg_group": data['bcg_group'],
                "ozon_report_interest_id": record_id
            }
            values.append(vals)
        self.env["ozon.report.interest.data"].create(values)

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
            fields=['product', 'revenue', 'qty'],
            groupby=['product']
        )
        for entry in sales:
            product = entry.get('product')
            if product:
                product_id = product[0]
                product_data = data_dict.get(product_id)
                if product_data:
                    product_data['revenue'] += entry['revenue']
                    product_data['qty'] += entry['qty']

    @staticmethod
    def _get_period_data_dict(period_raw_analysis_data) -> tuple:
        data = defaultdict(
            lambda: {
                'hits_view': 0,
                'hits_tocart': 0,
                'revenue': 0,
                'qty': 0,
                'qty_%_per_view_per_day': 0,
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

    @staticmethod
    def _create_plot_and_save(quadrants: dict, colors: dict, record):
        # Plot the BCG matrix
        fig, ax = plt.subplots()
        for quadrant, products in quadrants.items():
            x = [data['sp_qty_%_per_view_per_day'] for _, data in products]
            y = [data['product_growth_rate'] for _, data in products]
            ax.scatter(x, y, label=quadrant, color=colors[quadrant])

        # Add labels and legend
        ax.set_xlabel('Доля в категории (%)')
        ax.set_ylabel('Темпы роста (%)')
        ax.set_title(f'BCG Матрица')
        ax.legend()

        buffer = io.BytesIO()
        fig.savefig(buffer, format='png')
        buffer.seek(0)
        binary_data = base64.b64encode(buffer.read())
        record.plot = binary_data
        plt.close(fig)
