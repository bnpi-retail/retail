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
    strategy = fields.Many2one(
        "ozon.pricing_strategy", string="Стратегия назначения цены"
    )
    comment = fields.Text(string="Причина")

    def is_product_in_queue(self, product):
        res = self.env["ozon.mass_pricing"].search([("product", "=", product.id)])
        return res if res else False

    def auto_create_from_strategy_competitors(self):
        strategy_id = "lower_3_percent_min_competitor"
        strategy = self.env["ozon.pricing_strategy"].search(
            [("strategy_id", "=", strategy_id)]
        )
        # search for products which have at least one competitor
        products = self.env["ozon.products"].search(
            [("price_history_ids", "!=", None), ("is_alive", "=", True)],
        )
        data = []
        for prod in products:
            # get competitors prices
            comp_prices = prod.price_history_ids.mapped("price")
            if not comp_prices:
                continue
            # TODO: ??? if this product is already in queue to change price?
            if self.is_product_in_queue(product=prod):
                continue

            min_comp_price = min(comp_prices)
            comp_prod = prod.price_history_ids.search(
                [("price", "=", min_comp_price)]
            ).product_competitors

            new_price = round(min_comp_price * 0.97, 2)
            comment = f"Автоматическое изменение цены по стратегии: '{strategy.name}'"
            data.append(
                {
                    "product": prod.id,
                    "price": prod.price,
                    "new_price": new_price,
                    "competitor_product": comp_prod.id,
                    "competitor_price": min_comp_price,
                    "strategy": strategy.id,
                    "comment": comment,
                }
            )

        self.create(data)
        return f"В очередь на изменение цен по стратегии '{strategy.name}' добавлено {len(data)} товаров."

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

    timestamp = fields.Date(string="Дата расчёта", default=fields.Date.today)
    name = fields.Char(string="Стратегия назначения цен")
    strategy_id = fields.Char(string="ID стратегии")
    value = fields.Float(string="Значение")
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
