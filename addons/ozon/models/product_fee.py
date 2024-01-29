# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductFee(models.Model):
    _name = "ozon.product_fee"
    _description = "Комиссии товара Ozon"

    product = fields.Many2one("ozon.products", string="Товар Ozon")
    product_id_on_platform = fields.Char(string="Product ID", readonly=True)

    acquiring = fields.Float(string="Максимальная комиссия за эквайринг")
    fbo_fulfillment_amount = fields.Float(string="Комиссия за сборку заказа (FBO)")
    fbo_direct_flow_trans_min_amount = fields.Float(string="Магистраль от (FBO)")
    fbo_direct_flow_trans_max_amount = fields.Float(string="Магистраль до (FBO)")
    fbo_deliv_to_customer_amount = fields.Float(string="Последняя миля (FBO)")
    fbo_return_flow_amount = fields.Float(string="Комиссия за возврат и отмену (FBO)")
    fbo_return_flow_trans_min_amount = fields.Float(
        string="Комиссия за обратную логистику от (FBO)"
    )
    fbo_return_flow_trans_max_amount = fields.Float(
        string="Комиссия за обратную логистику до (FBO)"
    )
    fbs_first_mile_min_amount = fields.Float(
        string="Минимальная комиссия за обработку отправления (FBS) — 0 рублей"
    )
    fbs_first_mile_max_amount = fields.Float(
        string="Максимальная комиссия за обработку отправления (FBS) — 25 рублей"
    )
    fbs_direct_flow_trans_min_amount = fields.Float(string="Магистраль от (FBS)")
    fbs_direct_flow_trans_max_amount = fields.Float(string="Магистраль до (FBS)")
    fbs_deliv_to_customer_amount = fields.Float(string="Последняя миля (FBS)")
    fbs_return_flow_amount = fields.Float(
        string="Комиссия за возврат и отмену, обработка отправления (FBS)"
    )
    fbs_return_flow_trans_min_amount = fields.Float(
        string="Комиссия за возврат и отмену, магистраль от (FBS)"
    )
    fbs_return_flow_trans_max_amount = fields.Float(
        string="Комиссия за возврат и отмену, магистраль до (FBS)"
    )
    sales_percent_fbo = fields.Float(string="Процент комиссии за продажу (FBO)")
    sales_percent_fbs = fields.Float(string="Процент комиссии за продажу (FBS)")
    sales_percent = fields.Float(
        string="Наибольший процент комиссии за продажу среди FBO и FBS"
    )
