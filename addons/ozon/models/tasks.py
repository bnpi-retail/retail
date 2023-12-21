# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Task(models.Model):
    _name = "ozon.tasks"
    _description = "Задачи"

    name = fields.Selection(
        [("low_price", "Низкая цена")], string="Название", required=True
    )
    status = fields.Selection(
        [
            ("new", "Новая"),
            ("in_progress", "В работе"),
            ("done", "Завершена"),
        ],
        string="Статус",
        default="new",
        group_expand="_expand_groups",
    )
    open_datetime = fields.Datetime(string="Дата создания", default=fields.Datetime.now)
    close_datetime = fields.Datetime(string="Дата закрытия")
    next_check_datetime = fields.Datetime(
        string="Дата следующей проверки",
    )
    product = fields.Many2one("ozon.products", string="Товар", required=True)
    decision = fields.Char(string="Решение")
    manager = fields.Char(string="Менеджер")

    @api.model
    def _expand_groups(self, states, domain, order):
        return ["new", "in_progress", "done"]

    @api.model
    def create(self, values):
        name = values["name"]
        ozon_product_id = values["product"]
        ozon_product = self.get_ozon_product(ozon_product_id)
        next_check_datetime = values.get("next_check_datetime")

        """Если по данному товару уже есть задача такого же типа
        и дата след. проверки > сегодняшней даты, то задача не создается."""
        if task := self.env["ozon.tasks"].search(
            [
                ("product", "=", ozon_product_id),
                ("name", "=", name),
                ("next_check_datetime", ">", fields.Datetime.now()),
            ],
        ):
            raise ValidationError(
                f"""
                По товару {ozon_product.products.name} 
                уже есть задача "{dict(task._fields['name'].selection).get(task.name)}" 
                с датой следующей проверки {task.next_check_datetime}
                """
            )

        return super(Task, self).create(values)

    def get_ozon_product(self, ozon_product_id):
        result = self.env["ozon.products"].search([("id", "=", ozon_product_id)])
        return result if result else False
