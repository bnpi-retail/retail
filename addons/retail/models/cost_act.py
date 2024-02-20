# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CostAct(models.Model):
    _name = "retail.cost_act"
    _description = "Акт присвоения статьи себестоимости"

    date = fields.Date(string="Дата", default=fields.Date.today)
    status = fields.Selection(
        [
            ("created", "Создан"),
            ("applied", "Применён"),
        ],
        string="Статус",
        default="created",
        readonly=True,
    )
    act_type = fields.Many2one("retail.cost_act_type", string="Тип")
    cost_act_product_ids = fields.One2many(
        "retail.cost_act_product", "act_id", string="Товары"
    )

    def apply(self):
        for prod in self.cost_act_product_ids:
            # есть ли уже себестоимость такого типа по данному товару?
            if cost_price_item := self.env["retail.cost_price"].search(
                [
                    ("cost_type_id", "=", self.act_type.id),
                    ("product_id", "=", prod.product_id.id),
                ]
            ):
                cost_price_item.price = prod.cost
            else:
                # создаем для товара статью себестоимости
                cost_price_item = self.env["retail.cost_price"].create(
                    {
                        "product_id": prod.product_id.id,
                        "cost_type_id": self.act_type.id,
                        "price": prod.cost,
                    }
                )

            # обновляем общую себестоимость в ozon.products
            ozon_products = self.env["ozon.products"].search(
                [("products", "=", prod.product_id.id)]
            )
            for op in ozon_products:
                op.create_update_fix_exp_cost_price()

            print(
                f"Cost price for retail product {prod.product_id.product_id} updated/added."
            )

        self.status = "applied"


class CostActProduct(models.Model):
    _name = "retail.cost_act_product"
    _description = "Запись (товар) в акте себестоимости"

    product_id = fields.Many2one("retail.products", string="Товар")
    act_id = fields.Many2one("retail.cost_act", string="Акт")
    qty = fields.Integer(string="Количество")
    cost = fields.Float(string="Стоимость за ед. товара")
    total = fields.Float(string="Общая стоимость", compute="_compute_total", store=True)

    @api.depends("qty", "cost")
    def _compute_total(self):
        for rec in self:
            rec.total = rec.qty * rec.cost


class CostActType(models.Model):
    _name = "retail.cost_act_type"
    _description = "Тип акта себестоимости"

    name = fields.Char(string="Название")
