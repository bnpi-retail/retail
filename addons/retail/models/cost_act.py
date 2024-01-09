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
        pass


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
