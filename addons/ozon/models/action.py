# -*- coding: utf-8 -*-

from odoo import models, fields, api

from ..ozon_api import (
    get_product_info_list_by_sku,
    add_products_to_action,
    delete_products_from_action,
)
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
            "view_mode": "tree",
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
    is_participating = fields.Boolean(string="Участвует")
    price = fields.Float(related="product_id.price", readonly=True)
    max_action_price = fields.Float(
        string="Максимально возможная цена товара по акции", readonly=True
    )
    product_id_on_platform = fields.Char(related="product_id.id_on_platform")
    action_start = fields.Datetime(related="action_id.datetime_start")
    action_end = fields.Datetime(related="action_id.datetime_end")
    action_status = fields.Selection(related="action_id.status")

    def participate_in_action(self):
        """Участвовать в акции."""

        # a_id = self[0].action_id.a_id

        # info = self.read(["product_id_on_platform", "max_action_price"])
        # sku_action_price = {
        #     i["product_id_on_platform"]: i["max_action_price"] for i in info
        # }

        # skus = self.mapped("product_id_on_platform")
        # skus_chunks = split_list_into_chunks_of_size_n(skus, 1000)
        # prod_info_list = []
        # for chunk in skus_chunks:
        #     prod_info_list.extend(get_product_info_list_by_sku(sku_list=chunk))

        # data = []
        # prod_id_sku = {}
        # for i in prod_info_list:
        #     product_id = i["id"]
        #     if i["sku"] != 0:
        #         prod_id_sku[product_id] = [sku]
        #         sku = i["sku"]
        #     else:
        #         prod_id_sku[product_id] = [i["fbs_sku"], i["fbo_sku"]]
        #         sku = i["fbs_sku"]

        #     action_price = sku_action_price[str(sku)]
        #     data.append({"product_id": product_id, "action_price": action_price})

        # response = add_products_to_action(action_id=a_id, prod_list=data)

        # added_skus = []
        # if added_prod_ids := response.get("product_ids"):
        #     for pid in added_prod_ids:
        #         for sku in prod_id_sku[pid]:
        #             added_skus.append(sku)

        # print(added_skus)

        # added_candidates = self.filtered(
        #     lambda r: int(r.product_id_on_platform) in [248853871, 160865253]
        # )
        # added_candidates.is_participating = True
        # print(self)

        self.is_participating = True
