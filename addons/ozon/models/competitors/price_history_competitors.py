from odoo import models, fields, api


class PriceHistoryCompetitors(models.Model):
    _name = "ozon.price_history_competitors"
    _description = "История цен конкурентов"

    product_id = fields.Many2one("ozon.products", string="Лот")

    timestamp = fields.Date(string="Дата", default=fields.Date.today)

    product_competitors = fields.Many2one(
        "ozon.products_competitors", string="Товар конкурента"
    )

    price = fields.Float(string="Цена")
    price_with_card = fields.Float(string="Цена по карте Ozon")
    price_without_sale = fields.Float(string="Цена без скидки")

    sales = fields.Integer(string="Продажи")
    balance = fields.Integer(string="Остатки")
    revenue = fields.Float(string="Выручка", compute="_compute_revenue")

    rating = fields.Integer(string="Рейтинг")
    comments = fields.Integer(string="Комментарии")

    @api.depends("price_with_card", "sales")
    def _compute_revenue(self):
        for record in self:
            record.revenue = record.price * record.sales

    @api.model
    def create(self, values):
        record = super(PriceHistoryCompetitors, self).create(values)

        model_products = self.env["ozon.products"]
        model_price_history_competitors = self.env["ozon.price_history_competitors"]

        if not record.product_competitors.product.id:
            return record

        # product = model_products.search(
        #     [("id", "=", record.product_competitors.product.id)]
        # )

        # new = True
        # for price_history_id in product.competitors_with_price_ids:
        #     price_history_record = model_price_history_competitors.browse(price_history_id)
        #     if (
        #         record.product_competitors.id == price_history_record.product_competitors.id
        #     ):
        #         product.write({"competitors_with_price_ids": [(3, price_history_id)]})
        #         product.write({"competitors_with_price_ids": [(4, record.id)]})
        #         new = False

        # if new == True:
        #     product.write({"competitors_with_price_ids": [(4, record.id)]})

        return record

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append(
                (
                    record.id,
                    f"{record.timestamp},  "
                    f"{record.product_competitors.product.products.name}",
                )
            )
        return result
