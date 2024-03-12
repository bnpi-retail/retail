from odoo import models, fields, api

class CompetitorOtherMarketplace(models.Model):
    _name = "ozon.competitor_other_mpl"
    _description = "Товар-конкурент на другой площадке"

    product_id = fields.Many2one("ozon.products", string="Наш товар")
    url = fields.Char(string="Ссылка на товар на другой площадке")
    marketplace = fields.Char(string="Площадка")
    article = fields.Char(string="Артикул товара на другой площадке")
    competitor_other_mpl_price_ids = fields.One2many("ozon.competitor_other_mpl_price", 
                                                     "competitor_other_mpl_id", 
                                                     string="История цен")

class CompetitorOtherMarketplacePrice(models.Model):
    _name = "ozon.competitor_other_mpl_price"
    _description = "Цена товара-конкурента на другой площадке"

    competitor_other_mpl_id = fields.Many2one("ozon.competitor_other_mpl", 
                                              string="Товар-конкурент на другой площадке")
    price = fields.Float(string="Цена")
    timestamp = fields.Date(string="Дата")