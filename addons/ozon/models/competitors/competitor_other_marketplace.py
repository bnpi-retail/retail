import re

from odoo import models, fields, api

class CompetitorOtherMarketplace(models.Model):
    _name = "ozon.competitor_other_mpl"
    _description = "Товар-конкурент на другой площадке"

    product_id = fields.Many2one("ozon.products", string="Наш товар")
    url = fields.Char(string="Ссылка на товар на другой площадке")
    marketplace = fields.Char(string="Площадка", compute='_compute_marketplace', store=True)
    article = fields.Char(string="Артикул товара на другой площадке", compute='_compute_article', store=True)
    price = fields.Float(string="Цена")
    # competitor_other_mpl_price_ids = fields.One2many("ozon.competitor_other_mpl_price", 
    #                                                  "competitor_other_mpl_id", 
    #                                                  string="История цен")
    
    @api.depends("url")
    def _compute_article(self):
        for r in self:
            r.article = r.get_article_from_url()

    @api.depends("url")
    def _compute_marketplace(self):
        for r in self:
            r.marketplace = r.get_marketplace_from_url()

    def get_article_from_url(self):
        self.ensure_one()
        if not isinstance(self.url, str):
            return
        idx = self.url.find('sku')
        if idx > 0:
            s = self.url[idx:]
        else:
            s = self.url
        res = re.findall(r'\d+', s)
        if not res or len(res) > 1:
            return
        return res[0]

    def get_marketplace_from_url(self):
        if not isinstance(self.url, str):
            return
        marketplaces = {
            "wildberries": "Wildberries",
            "yandex": "Яндекс.Маркет",
            "vseinstrumenti": "ВсеИнструменты",
            "citilink": "Citilink"
        }
        for mpl, mpl_name in marketplaces.items():
            if mpl in self.url:
                return mpl_name
        return


class CompetitorOtherMarketplacePrice(models.Model):
    _name = "ozon.competitor_other_mpl_price"
    _description = "Цена товара-конкурента на другой площадке"

    # competitor_other_mpl_id = fields.Many2one("ozon.competitor_other_mpl", 
    #                                           string="Товар-конкурент на другой площадке")
    price = fields.Float(string="Цена")
    timestamp = fields.Date(string="Дата")