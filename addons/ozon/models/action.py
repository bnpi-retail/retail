# -*- coding: utf-8 -*-

from odoo import models, fields, api


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
        "ozon.action_candidate", "action_id", string="Товары, которые могут участвовать"
    )

    def _compute_status(self):
        now = fields.Datetime.now()
        for rec in self:
            if now < rec.datetime_start:
                rec.status = "not_started"
            elif now > rec.datetime_end:
                rec.status = "ended"
            else:
                rec.status = "started"


class ActionCandidate(models.Model):
    _name = "ozon.action_candidate"
    _description = "Кандидат для участия в акции"

    action_id = fields.Many2one("ozon.action", string="Акция Ozon", readonly=True)
    product_id = fields.Many2one("ozon.products", string="Товар Ozon", readonly=True)
    is_participating = fields.Boolean(string="Участвует")
    max_action_price = fields.Float(
        string="Максимально возможная цена товара по акции", readonly=True
    )
    product_id_on_platform = fields.Char(related="product_id.id_on_platform")
    action_start = fields.Datetime(related="action_id.datetime_start")
    action_end = fields.Datetime(related="action_id.datetime_end")
    action_status = fields.Selection(related="action_id.status")
