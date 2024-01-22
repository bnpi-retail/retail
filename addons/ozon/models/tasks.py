# -*- coding: utf-8 -*-
from datetime import datetime, time

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
    manager = fields.Many2one(
        "res.users", string="Менеджер", default=lambda self: self.env.user
    )

    @api.model
    def _expand_groups(self, states, domain, order):
        return ["new", "in_progress", "done"]

    @api.model
    def create(self, values):
        name = values["name"]
        ozon_product_id = values["product"]
        ozon_product = self.get_ozon_product(ozon_product_id)

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

    def is_task_day_limit_exhausted(self):
        tasks_day_limit = 50
        today_beginning = datetime.combine(datetime.now(), time.min)
        tasks_created_today = self.env["ozon.tasks"].search(
            [("create_date", ">", today_beginning)]
        )
        if len(tasks_created_today) >= tasks_day_limit:
            return True, 0
        else:
            amount_left = tasks_day_limit - len(tasks_created_today)
            return False, amount_left

    def is_new_tasks_limit_exhausted(self):
        """Returns bool and amount of tasks that yet can be created."""
        limit = 50
        new_tasks = self.env["ozon.tasks"].search([("status", "=", "new")])
        if len(new_tasks) == limit:
            return True, 0
        else:
            amount_left = limit - len(new_tasks)
            return False, amount_left

    def get_ozon_product(self, ozon_product_id):
        result = self.env["ozon.products"].search([("id", "=", ozon_product_id)])
        return result if result else False

    def create_tasks_low_price(self):
        """Если profit < ideal_profit, то создается задача 'Низкая цена'"""
        is_exhaused, amount_left = self.is_new_tasks_limit_exhausted()
        if is_exhaused:
            return "New tasks limit exhausted."
        # взять первые 50шт продуктов с отрицательной profit_delta
        products_records = self.env["ozon.products"].search(
            [("profit_delta", "<=", 0)],
            limit=amount_left,
            order="create_date desc",
        )
        tasks_values = []
        for prod in products_records:
            tasks_values.append(
                {
                    "name": "low_price",
                    "product": prod.id,
                }
            )
        recs = self.create(tasks_values)

        return f"Tasks for {len(products_records)} products were created."

    def create_mass_pricing_from_low_price_task(self):
        if self.name != "low_price":
            raise ValidationError("Для этой задачи невозможно массовое назначение цен.")

        self.env["ozon.mass_pricing"].create_from_product(product=self.product)
