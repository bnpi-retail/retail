from odoo import models, fields, api
from odoo.exceptions import ValidationError

from ...ozon_api import get_product_id_by_sku, set_price


class MassPricing(models.Model):
    _name = "ozon.mass_pricing"
    _description = "Очередь изменения цен"

    status = fields.Selection(
        [
            ("created", "Создано"),
            ("applied", "Применено"),
        ],
        string="Статус",
        default="created",
        readonly=True,
    )
    product = fields.Many2one("ozon.products", string="Товар Ozon")
    price = fields.Float(string="Текущая цена")
    new_price = fields.Float(string="Новая цена")
    competitor_product = fields.Many2one(
        "ozon.products_competitors", string="Товар конкурента"
    )
    competitor_price = fields.Float(string="Цена товара конкурента")
    comment = fields.Text(string="Причина")
    strategy = fields.Many2one(
        "ozon.pricing_strategy", string="Стратегия назначения цены"
    )

    def auto_create_from_product(self, product):
        """Новая цена назначается автоматически."""
        price = round(product.price, 2)
        profit = round(product.profit, 2)
        profit_delta = round(product.profit_delta, 2)
        profit_ideal = round(product.profit_ideal, 2)
        if profit < 0:
            comment = f"Торгуем в убыток: прибыль от актуальной цены {profit}"
        elif profit_delta < 0:
            comment = f"Прибыль от актуальной цены {profit} меньше, чем идеальная прибыль {profit_ideal}"
        else:
            comment = "Причина назначения цены не обнаружена"
        new_price = product.price + abs(profit_delta)

        self.create(
            {
                "product": product.id,
                "price": price,
                "new_price": new_price,
                "comment": comment,
            }
        )

    def set_price_in_ozon_and_update_price(self):
        for rec in self:
            if rec.status == "applied":
                raise ValidationError(
                    f"Цена для товара {rec.product.products.name} уже изменена"
                )
            sku = rec.product.id_on_platform
            product_id = get_product_id_by_sku([sku])[0]
            response = set_price(
                [{"product_id": product_id, "price": str(int(rec.new_price))}]
            )
            if isinstance(response, dict) and response.get("code"):
                raise ValidationError(f"Ошибка в Ozon. Попробуйте позже.\n{response}")

            if response[0]["updated"]:
                rec.status = "applied"
                rec.product.price = rec.new_price
            else:
                raise ValidationError(
                    f"Не смог изменить цену товара {rec.product.products.name}.\n{response['errors']}"
                )


class PricingStrategy(models.Model):
    _name = "ozon.pricing_strategy"
    _description = "Стратегия назначения цен"

    name = fields.Char(string="Стратегия назначения цен")
