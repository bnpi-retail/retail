from odoo import models, fields, api
from odoo.exceptions import ValidationError

from ...ozon_api import get_product_id_by_sku, set_price


class MassPricing(models.Model):
    _name = "ozon.mass_pricing"
    _description = "Очередь изменения цен"
    _order = "create_date desc"

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
    comment = fields.Text(string="Причина")

    def create(self, values, **kwargs):
        if product := kwargs.get("product"):
            product.mass_pricing_ids.unlink()
        rec = super(MassPricing, self).create(values)
        return rec

    def is_product_in_queue(self, product):
        res = self.env["ozon.mass_pricing"].search([("product", "=", product.id)])
        return res if res else False

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

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append(
                (
                    record.id,
                    f"{record.product.products.name}, {record.price} -> {record.new_price}",
                )
            )
        return result


class PricingStrategy(models.Model):
    _name = "ozon.pricing_strategy"
    _description = "Стратегия назначения цен"

    name = fields.Char(string="Название")
    strategy_id = fields.Char(string="ID стратегии")
    weight = fields.Float(string="Вес")
    value = fields.Float(string="Значение")


class PricingStrategy(models.Model):
    _name = "ozon.calculated_pricing_strategy"
    _description = "Стратегия назначения цен"

    timestamp = fields.Date(string="Дата расчёта")
    pricing_strategy_id = fields.Many2one(
        "ozon.pricing_strategy", string="Стратегия назначения цен"
    )
    strategy_id = fields.Char(
        string="ID стратегии", related="pricing_strategy_id.strategy_id"
    )
    weight = fields.Float(string="Вес")
    value = fields.Float(string="Значение")
    expected_price = fields.Float(string="Цена")
    message = fields.Char(
        string="Цена",
        readonly=True,
        help="Показывает цену либо сообщение об ошибке, если цена не может быть рассчитана",
    )

    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
