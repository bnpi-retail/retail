from odoo import models, fields
from odoo.exceptions import UserError
import logging


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

