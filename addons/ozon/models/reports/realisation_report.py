from odoo import models, fields, api


class RealisationReport(models.Model):
    _name = "ozon.realisation_report"
    _description = "Месячный отчет Ozon о реализации товаров"
    _order = "create_date desc"

    realisation_report_product_ids = fields.One2many("ozon.realisation_report_product", 
        "realisation_report_id", string="Товары в отчете", readonly=True)

    num = fields.Char(string="Номер отчёта о реализации")
    doc_date = fields.Date(string="Дата формирования отчёта")
    contract_date = fields.Date(string="Дата заключения договора оферты")
    contract_num = fields.Char(string="Номер договора оферты")
    currency_code = fields.Char(string="Валюта ваших цен")
    doc_amount = fields.Float(string="Сумма к начислению")
    vat_amount = fields.Float(string="Сумма к начислению с НДС")
    payer_inn = fields.Char(string="ИНН плательщика")
    payer_kpp = fields.Char(string="КПП плательщика")
    payer_name = fields.Char(string="Название плательщика")
    rcv_inn = fields.Char(string="ИНН получателя")
    rcv_kpp = fields.Char(string="КПП получателя")
    rcv_name = fields.Char(string="Название получателя")
    start_date = fields.Date(string="Начало периода в отчёте")
    stop_date = fields.Date(string="Конец периода в отчёте")

    def name_get(self):
        result = []
        for r in self:
            result.append((r.id, f"Отчёт №{r.num} с {r.start_date} по {r.stop_date}"))
        return result

    def open_tree_view_realisation_report_product(self):
        return {
            "name": "Товары в отчёте о реализации",
            "type": "ir.actions.act_window",
            "res_model": "ozon.realisation_report_product",
            "view_mode": "tree,form",
            "res_id": self.id,
            "target": "current",
        }

class RealisationReportProduct(models.Model):
    _name = "ozon.realisation_report_product"
    _description = "Продукт в месячном отчете Ozon о реализации товаров"

    realisation_report_id = fields.Many2one("ozon.realisation_report", string="Отчет")
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")

    row_number = fields.Integer(string="Номер строки в отчёте")
    product_id_on_platform = fields.Char(string="Product ID")
    product_name = fields.Char(string="Название")
    barcode = fields.Char(string="Штрихкод")
    offer_id = fields.Char(string="Артикул")
    commission_percent = fields.Float(string="Комиссия за продажу по категории")
    price = fields.Float(string="Цена продавца с учётом его скидки")
    price_sale = fields.Float(
        string="Цена реализации", help="Цена, по которой покупатель приобрёл товар. Для реализованных товаров")
    sale_amount = fields.Float(
        string="Реализовано на сумму", help="Стоимость реализованного товара с учётом количества "
        "и региональных коэффициентов. Расчёт осуществляется по цене sale_amount")
    sale_commission = fields.Float(
        string="Комиссия", help="Комиссия за реализованный товар с учётом скидок и наценки")
    sale_discount = fields.Float(
        string="Доплата за счёт Ozon", help="Сумма, которую Ozon компенсирует продавцу, "
        "если скидка Ozon больше или равна комиссии за продажу.")
    sale_price_seller = fields.Float(
        string="Итого к начислению за реализованный товар", 
        help="Сумма после вычета комиссии за продажу, применения скидок и установленных наценок.")
    sale_qty = fields.Integer(string="Количество реализованного товара", 
                              help="Количество товара, реализованного по цене price_sale.")
    return_sale = fields.Float(
        string="Цена реализации при возврате", 
        help="Цена, по которой покупатель приобрёл товар. Для возвращённых товаров.")
    return_amount = fields.Float(
        string="Возвращено на сумму", help="Стоимость возвращённого товара с учётом количества и "
        "региональных коэффициентов. Расчёт осуществляется по цене return_sale.")
    return_commission = fields.Float(
        string="Комиссия в случае возврата", 
        help="Комиссия с учётом количества товара, предоставленных скидок и установленных наценок. "
        "Ozon компенсирует её в случае возврата товара.")
    return_discount = fields.Float(
        string="Доплата за счёт Ozon при возврате", help="Сумма скидки за счёт Ozon по возвращённому товару, "
        "которую Ozon компенсирует продавцу, если скидка Ozon больше или равна комиссии за продажу.")
    return_price_seller = fields.Float(
        string="Итого возвращено", help="Сумма, начисляемая продавцу за возвращённый товар "
        "после вычета комиссии за продажу, применения скидок и установленных наценок.")
    return_qty = fields.Integer(string="Количество возвращённого товара")