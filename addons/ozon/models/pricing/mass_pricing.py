from odoo import models, fields, api


class MassPricing(models.Model):
    _name = "ozon.mass_pricing"
    _description = "Массовое назначение цен"

    status = fields.Selection(
        [
            ("created", "Создано"),
            ("applied", "Применено"),
        ],
        string="Статус",
        default="created",
    )
    product = fields.Many2one("ozon.products", string="Товар Ozon")
    price = fields.Float(string="Текущая цена")
    new_price = fields.Float(string="Новая цена")
    comment = fields.Text(string="Причина")

    def create_from_product(self, product):
        price = round(product.price, 2)
        profit = round(product.profit, 2)
        profit_delta = round(product.profit_delta, 2)
        profit_ideal = round(product.profit_ideal, 2)
        if profit < 0:
            comment = f"Торгуем в убыток: прибыль от актуальной цены {profit}"
        elif profit_delta < 0:
            comment = f"Прибыль от актуальной цены {profit} меньше, чем идеальная прибыль {profit_ideal}"
        new_price = product.price + abs(profit_delta)

        self.create(
            {
                "product": product.id,
                "price": price,
                "new_price": new_price,
                "comment": comment,
            }
        )

    def update_price_in_ozon(sefl):
        # TODO
        pass
