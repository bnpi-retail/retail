# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions

from ..ozon_api import add_products_to_action, delete_products_from_action
from ..helpers import split_list_into_chunks_of_size_n


class Action(models.Model):
    _name = "ozon.action"
    _description = "Акции Ozon"

    a_id = fields.Integer(string="Идентификатор", readonly=True)
    name = fields.Char(string="Название", readonly=True)
    with_targeting = fields.Boolean(string="C целевой аудиторией", readonly=True)
    datetime_start = fields.Datetime(string="Начало")
    datetime_end = fields.Datetime(string="Окончание")
    status = fields.Selection(
        [
            ("not_started", "Не началась"),
            ("started", "Идёт"),
            ("ended", "Закончилась"),
        ],
        string="Статус",
        readonly=True,
        compute="_compute_status",
    )
    is_participating = fields.Boolean(string="Участвуем", readonly=True)
    description = fields.Text(string="Описание", readonly=True)
    action_type = fields.Char(string="Тип акции", readonly=True)
    discount_type = fields.Char(string="Тип скидки", readonly=True)
    discount_value = fields.Float(string="Размер скидки", readonly=True)
    potential_products_count = fields.Integer(string="Кол-во кандидатов", readonly=True)
    participating_products_count = fields.Integer(
        string="Кол-во участников", readonly=True
    )
    action_candidate_ids = fields.One2many(
        "ozon.action_candidate",
        "action_id",
        domain=[("is_participating", "=", False)],
        string="Товары, которые могут участвовать",
    )
    action_participants_ids = fields.One2many(
        "ozon.action_candidate",
        "action_id",
        domain=[("is_participating", "=", True)],
        string="Товары, которые участвуют",
    )
    ids_on_platform = fields.Text(string="Список Product ID товаров")

    def _compute_status(self):
        now = fields.Datetime.now()
        for rec in self:
            if now < rec.datetime_start:
                rec.status = "not_started"
            elif now > rec.datetime_end:
                rec.status = "ended"
            else:
                rec.status = "started"

    def get_action_add_products_to_action(self):
        """Возвращает action с tree view ozon.action_candidate для данной акции"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Добавить товары в акцию",
            "view_mode": "tree,form",
            "res_model": "ozon.action_candidate",
            "domain": [("action_id", "=", self.id)],
            "context": {"create": False},
        }


class ActionCandidate(models.Model):
    _name = "ozon.action_candidate"
    _description = "Кандидат для участия в акции"

    action_id = fields.Many2one("ozon.action", string="Акция Ozon", readonly=True)
    product_id = fields.Many2one("ozon.products", string="Товар Ozon", readonly=True)
    id_on_platform = fields.Char(string="Product ID", readonly=True)
    is_participating = fields.Boolean(string="Участвует", readonly=True)
    price = fields.Float(related="product_id.price", readonly=True)
    max_action_price = fields.Float(
        string="Максимально возможная цена товара по акции", readonly=True
    )
    product_id_on_platform = fields.Char(related="product_id.id_on_platform")
    action_start = fields.Datetime(related="action_id.datetime_start")
    action_end = fields.Datetime(related="action_id.datetime_end")
    action_status = fields.Selection(related="action_id.status")
    action_candidate_movement_ids = fields.One2many(
        "ozon.action_candidate_movement",
        "action_candidate_id",
        string="Добавление/удаление из акции",
    )

    def participate_in_action(self):
        """Участвовать в акции."""
        a_id = self[0].action_id.a_id
        data = []
        for rec in self:
            data.append(
                {
                    "product_id": rec.product_id_on_platform,
                    "action_price": rec.max_action_price,
                }
            )

        response = add_products_to_action(action_id=a_id, prod_list=data)
        if added_prod_ids := response.get("product_ids"):
            added_candidates = self.filtered(
                lambda r: int(r.product_id_on_platform) in added_prod_ids
            )
            added_candidates.is_participating = True
            candidate_movement_data = []
            for can in added_candidates:
                candidate_movement_data.append(
                    {"action_candidate_id": can["id"], "operation": "added"}
                )
            self.env["ozon.action_candidate_movement"].create(candidate_movement_data)
        if rejected_products := response.get("rejected"):
            raise exceptions.ValidationError(
                f"Товары не были добавлены в акцию.\nОшибка:\n{rejected_products}"
            )

    def remove_from_action(self):
        a_id = self[0].action_id.a_id
        prod_ids = self.mapped("product_id_on_platform")
        response = delete_products_from_action(action_id=a_id, product_ids=prod_ids)
        if removed_prod_ids := response.get("product_ids"):
            removed_candidates = self.filtered(
                lambda r: int(r.product_id_on_platform) in removed_prod_ids
            )
            removed_candidates.is_participating = False
            candidate_movement_data = []
            for can in removed_candidates:
                candidate_movement_data.append(
                    {"action_candidate_id": can["id"], "operation": "removed"}
                )
            self.env["ozon.action_candidate_movement"].create(candidate_movement_data)
        if rejected_products := response.get("rejected"):
            raise exceptions.ValidationError(
                f"Товары не были удалены из акции.\nОшибка:\n{rejected_products}"
            )


class ActionCandidateMovement(models.Model):
    _name = "ozon.action_candidate_movement"
    _description = "История участия/удаления товара из акции"

    timestamp = fields.Datetime(string="Дата", default=fields.Datetime.now)
    action_candidate_id = fields.Many2one(
        "ozon.action_candidate", string="Кандидат в акцию"
    )
    operation = fields.Selection(
        [("added", "Добавлен в акцию"), ("removed", "Удалён из акции")],
        string="Операция",
    )
