from odoo import models, fields
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

    def action_do_report_category_market_share(self):
        for record in self:
            known_share_percentage = 0
            total_amount = 0
            for competitor_category_share in record.ozon_report_competitor_category_share_ids:
                known_share_percentage += competitor_category_share.category_share
                total_amount += competitor_category_share.turnover

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
    retail_seller_id = fields.Many2one('retail.seller', string="Продавец")
    category_share = fields.Float()
    turnover = fields.Float()
    turnover_growth = fields.Float()

    ozon_report_category_market_share = fields.Many2one("ozon.report_category_market_share")

