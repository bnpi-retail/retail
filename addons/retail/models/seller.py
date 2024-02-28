from odoo import models, fields, api, exceptions


class Seller(models.Model):
    _name = "retail.seller"
    _description = "Продавец"

    name = fields.Char(string="Название", index=True)
    ogrn = fields.Char(string="ОГРН")
    trade_name = fields.Char(string="Торговое название")
    is_my_shop = fields.Char(default=True)

    tax = fields.Float(string="Налогообложение", default=0.07)
    tax_percent = fields.Float(string="Процент налога", compute="_compute_tax_percent")
    tax_description = fields.Char(
        string="Описание налога", compute="_compute_tax_description"
    )

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result

    def _compute_tax_percent(self):
        for rec in self:
            rec.tax_percent = rec.tax

    def _compute_tax_description(self):
        for rec in self:
            rec.tax_description = f"{round(rec.tax * 100)}% от дохода"
