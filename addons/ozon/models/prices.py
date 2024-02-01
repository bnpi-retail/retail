# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from email.policy import default
from odoo import models, fields, api

from .indirect_percent_expenses import (
    STRING_FIELDNAMES,
    COEF_FIELDNAMES_STRINGS_WITHOUT_ACQUIRING,
)
from ..ozon_api import (
    MAX_FIX_EXPENSES_FBO,
    MAX_FIX_EXPENSES_FBS,
    FBO_PERCENT_COMMISSIONS,
    FBS_PERCENT_COMMISSIONS,
)


class FixExpenses(models.Model):
    _name = "ozon.fix_expenses"
    _description = "Фиксированные затраты"

    name = fields.Char(string="Наименование")
    price = fields.Float(string="Значение")
    discription = fields.Text(string="Описание")
    price_history_id = fields.Many2one("ozon.price_history", string="История цен")
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")

    def create_from_ozon_product_fee(self, product_fee):
        field_names = [
            field
            for field in product_fee.fields_get_keys()
            if field
            not in [
                "product",
                "sales_percent_fbo",
                "sales_percent_fbs",
                "sales_percent",
                "id",
                "__last_update",
                "display_name",
                "create_uid",
                "create_date",
                "write_uid",
                "write_date",
            ]
        ]
        fieldnames_and_strings = [
            (k, v.string) for k, v in product_fee._fields.items() if k in field_names
        ]
        data = []
        for field, string in fieldnames_and_strings:
            rec = {
                "name": string,
                "price": product_fee[field],
                "discription": "",
            }
            data.append(rec)

        recs = self.create(data)

        return recs


class Costs(models.Model):
    _name = "ozon.cost"
    _description = "Процент от продаж"

    name = fields.Char(string="Наименование")
    price = fields.Float(string="Значение")
    discription = fields.Text(string="Описание")
    price_history_id = fields.Many2one("ozon.price_history", string="История цен")
    product_id = fields.Many2one("ozon.products", string="Товар Ozon")

    def create_from_ozon_product_fee(self, product_fee, price):
        field_names = [
            field
            for field in product_fee.fields_get_keys()
            if field
            in [
                "sales_percent_fbo",
                "sales_percent_fbs",
            ]
        ]
        fieldnames_and_strings = [
            (k, v.string) for k, v in product_fee._fields.items() if k in field_names
        ]
        data = []
        for field, string in fieldnames_and_strings:
            rec = {
                "name": string,
                "price": round(price * product_fee[field] / 100, 2),
                "discription": f"{product_fee[field]}%",
            }
            data.append(rec)

        recs = self.create(data)

        return recs


class PriceHistory(models.Model):
    _name = "ozon.price_history"
    _description = "История цен"

    product = fields.Many2one("ozon.products", string="Товар")
    id_on_platform = fields.Char(string="Product ID", readonly=True)
    provider = fields.Many2one("retail.seller", string="Продавец")
    price = fields.Float(string="Установленная цена", readonly=True)
    competitors = fields.One2many(
        "ozon.name_competitors",
        "pricing_history_id",
        string="Цены конкурентов",
        copy=True,
    )

    previous_price = fields.Float(string="Предыдущая цена", readonly=True)
    timestamp = fields.Date(string="Дата", default=fields.Date.today, readonly=True)

    # @api.model
    def _change_fix_expenses_domain(self):
        for rec in self:
            if rec.product.trading_scheme == "FBS":
                domain = [("name", "in", MAX_FIX_EXPENSES_FBS)]
            elif rec.product.trading_scheme == "FBO":
                domain = [("name", "in", MAX_FIX_EXPENSES_FBO)]
            else:
                domain = []
            return domain

    fix_expenses = fields.One2many(
        "ozon.fix_expenses",
        "price_history_id",
        string="Фиксированные затраты максимальные",
        copy=True,
        readonly=True,
        domain=_change_fix_expenses_domain,
    )

    total_cost_fix = fields.Float(
        string="Итого фикс.затраты",
        compute="_compute_total_cost_fix",
        store=True,
    )

    @api.model
    def _change_costs_domain(self):
        indir_per_expenses = STRING_FIELDNAMES
        if indir_per_expenses.get("Выручка"):
            indir_per_expenses.pop("Выручка")
        for rec in self:
            if rec.product.trading_scheme == "FBS":
                domain = [
                    (
                        "name",
                        "in",
                        [
                            "Процент комиссии за продажу (FBS)",
                            *indir_per_expenses.keys(),
                        ],
                    )
                ]
            elif rec.product.trading_scheme == "FBO":
                domain = [
                    (
                        "name",
                        "in",
                        [
                            "Процент комиссии за продажу (FBO)",
                            *indir_per_expenses.keys(),
                        ],
                    )
                ]
            else:
                domain = []
            return domain

    costs = fields.One2many(
        "ozon.cost",
        "price_history_id",
        string="Процент от продаж",
        copy=True,
        readonly=True,
        domain=_change_costs_domain,
    )
    total_cost_percent = fields.Float(
        string="Итого проц.затраты",
        compute="_compute_total_cost_percent",
        store=True,
    )

    profit = fields.Float(
        string="Прибыль от установленной цены", compute="_compute_profit", store=True
    )
    profit_ideal = fields.Float(
        string="Идеальная прибыль", compute="_compute_profit_ideal", store=True
    )
    profit_delta = fields.Float(
        string="Разница между прибылью и идеальной прибылью",
        compute="_compute_profit_delta",
        store=True,
    )
    coef_profitability = fields.Float(
        string="Коэффициент прибыльности",
        compute="_compute_coef_profitability",
        store=True,
    )

    product_id = fields.Many2one("ozon.products", string="Лот")

    @api.depends("fix_expenses.price")
    def _compute_total_cost_fix(self):
        for record in self:
            record.total_cost_fix = sum(record.fix_expenses.mapped("price"))

    @api.depends("costs.price")
    def _compute_total_cost_percent(self):
        for record in self:
            record.total_cost_percent = sum(record.costs.mapped("price"))

    @api.depends("price", "total_cost_fix", "total_cost_percent")
    def _compute_profit(self):
        for record in self:
            record.profit = (
                record.price - record.total_cost_fix - record.total_cost_percent
            )

    @api.depends("price")
    def _compute_profit_ideal(self):
        for record in self:
            record.profit_ideal = record.price * 0.2

    @api.depends("profit", "profit_ideal")
    def _compute_profit_delta(self):
        for record in self:
            record.profit_delta = record.profit - record.profit_ideal

    @api.depends("profit", "profit_ideal")
    def _compute_coef_profitability(self):
        for record in self:
            record.coef_profitability = record.profit / record.profit_ideal

    @api.model
    def create(self, values):
        if values.get("fix_expenses"):
            ozon_product_id = values["product"]
            cost_price_record = self.env["ozon.fix_expenses"].search(
                [
                    ("product_id", "=", ozon_product_id),
                    ("name", "=", "Себестоимость товара"),
                ],
                order="create_date desc",
                limit=1,
            )
            values["fix_expenses"] = [cost_price_record.id] + values["fix_expenses"]

        record = super(PriceHistory, self).create(values)
        product = record.product
        product.write({"price_our_history_ids": [(4, record.id)]})
        return record

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            id = record.id
            result.append(
                (id, f"{record.timestamp},  " f"{record.product.products.name}")
            )
        return result


class ProfitabilityNorm(models.Model):
    _name = "ozon.profitability_norm"
    _description = "Ожидаемая доходность"

    name = fields.Char(string="Наименование")
    value = fields.Float(string="Значение")


class ProfitabilityNormWizard(models.TransientModel):
    _name = "ozon.profitability_norm.wizard"
    _description = "Wizard Ожидаемая доходность"

    profitability_norm = fields.Many2one(
        "ozon.profitability_norm", string="Ожидаемая доходность"
    )

    def change_profitability_norm(self):
        prod_ids = self._context["active_ids"]
        products = self.env["ozon.products"].browse(prod_ids)
        products.write({"profitability_norm": self.profitability_norm})


class InvestmentExpenses(models.Model):
    _name = "ozon.investment_expenses"
    _description = "Investment"

    name = fields.Char(string="Наименование")
    value = fields.Float(string="Значение")


class InvestmentExpensesWizard(models.TransientModel):
    _name = "ozon.investment_expenses.wizard"
    _description = "Wizard Инвестиционные затраты"

    investment_expenses_id = fields.Many2one(
        "ozon.investment_expenses", string="Investment"
    )

    def change_investment_expenses(self):
        prod_ids = self._context["active_ids"]
        products = self.env["ozon.products"].browse(prod_ids)
        products.write({"investment_expenses_id": self.investment_expenses_id})


class AllExpenses(models.Model):
    _name = "ozon.all_expenses"
    _description = "Все затраты по товару Ozon"

    product_id = fields.Many2one("ozon.products", string="Товар Ozon")
    name = fields.Char(string="Название")
    description = fields.Char(string="Описание")
    kind = fields.Selection(
        [("fix", "Фиксированный"), ("percent", "Процентный")],
        string="Тип затрат",
        readonly=True,
    )
    category = fields.Char(string="Категория затрат", readonly=True)
    percent = fields.Float(string="Процент")
    value = fields.Float(string="Абсолютное значение в руб, исходя из текущей цены")
    expected_value = fields.Float(string="Ожидаемое значение")

    # def _compute_expected_value(self):
    #     # TODO: как рассчитываем затраты исходя из РРЦ?
    #     for rec in self:
    #         if rec.kind == "fix":
    #             rec.expected_value = rec.value
    #         else:
    #             if rec.category == "Investment":
    #                 rec.percent = rec.product_id.investment_expenses_id.value
    #             elif rec.category == "Рентабельность":
    #                 rec.percent = rec.product_id.profitability_norm.value
    #             rec.expected_value = rec.product_id.expected_price * rec.percent

    def create_update_all_product_expenses(self, products, latest_indirect_expenses):
        tax = products[0].seller.tax
        tax_percent = products[0].seller.tax_percent
        tax_description = products[0].seller.tax_description
        data = []
        for idx, prod in enumerate(products):
            total_expenses = 0
            price = prod.price
            expected_price = prod.expected_price
            # себестоимость
            data.append(
                {
                    "product_id": prod.id,
                    "name": "Себестоимость товара",
                    "kind": "fix",
                    "category": "Себестоимость",
                    "value": prod.products.total_cost_price,
                    "expected_value": prod.products.total_cost_price,
                }
            )
            total_expenses += prod.products.total_cost_price
            # услуги озон
            # category = "Услуги Ozon"
            # for k, v in COEF_FIELDNAMES_STRINGS_WITHOUT_ACQUIRING.items():
            #     percent = latest_indirect_expenses[k] / 100
            #     value = price * percent
            #     data.append(
            #         {
            # "product_id": prod.id,
            # "name": v,
            # "description": f"{latest_indirect_expenses[k]}%",
            # "kind": "percent",
            # "category": category,
            # "percent": percent,
            # "value": value,
            #         }
            #     )
            #     total_expenses += value
            coef_total = latest_indirect_expenses.coef_total
            data.append(
                {
                    "product_id": prod.id,
                    "name": "Общий коэффициент косвенных затрат",
                    "description": f"{round(coef_total,2)}%",
                    "kind": "percent",
                    "category": "Услуги Ozon",
                    "percent": coef_total / 100,
                    "value": price * coef_total / 100,
                    "expected_value": expected_price * coef_total / 100,
                    # TODO: убрать после тестов
                    # "percent": 0.05,
                    # "value": price * 0.05,
                }
            )
            # вознаграждение озон, последняя миля, логистика, обработка, эквайринг
            if prod.trading_scheme == "FBO":
                ozon_com = prod.fbo_percent_expenses.filtered(
                    lambda r: r.name.startswith("Процент")
                )
                last_mile = prod.fbo_fix_expenses_max.filtered(
                    lambda r: r.name == "Последняя миля (FBO)"
                )
                logistics = prod.fbo_fix_expenses_max.filtered(
                    lambda r: r.name == "Магистраль до (FBO)"
                )
                processing = prod.fbo_fix_expenses_max.filtered(
                    lambda r: r.name == "Комиссия за сборку заказа (FBO)"
                )
                acquiring = prod.fbo_fix_expenses_max.filtered(
                    lambda r: r.name == "Максимальная комиссия за эквайринг"
                )
            else:
                ozon_com = prod.fbs_percent_expenses.filtered(
                    lambda r: r.name.startswith("Процент")
                )
                last_mile = prod.fbs_fix_expenses_max.filtered(
                    lambda r: r.name == "Последняя миля (FBS)"
                )
                logistics = prod.fbs_fix_expenses_max.filtered(
                    lambda r: r.name == "Магистраль до (FBS)"
                )
                processing = prod.fbs_fix_expenses_max.filtered(
                    lambda r: r.name.startswith("Максимальная комиссия за обработку")
                )
                acquiring = prod.fbs_fix_expenses_max.filtered(
                    lambda r: r.name == "Максимальная комиссия за эквайринг"
                )

            data.extend(
                [
                    {
                        "product_id": prod.id,
                        "name": ozon_com.name,
                        "description": ozon_com.discription,
                        "kind": "percent",
                        "category": "Вознаграждение Ozon",
                        "percent": float(ozon_com.discription.replace("%", "")) / 100,
                        "value": ozon_com.price,
                        "expected_value": expected_price
                        * float(ozon_com.discription.replace("%", ""))
                        / 100,
                    },
                    {
                        "product_id": prod.id,
                        "name": last_mile.name,
                        "kind": "percent",
                        "category": "Последняя миля",
                        "percent": last_mile.price / price,
                        "value": last_mile.price,
                        "expected_value": expected_price * last_mile.price / price,
                    },
                    {
                        "product_id": prod.id,
                        "name": logistics.name,
                        "kind": "fix",
                        "category": "Логистика",
                        "value": logistics.price,
                        "expected_value": logistics.price,
                    },
                    {
                        "product_id": prod.id,
                        "name": processing.name,
                        "kind": "fix",
                        "category": "Обработка",
                        "value": processing.price,
                        "expected_value": processing.price,
                    },
                    {
                        "product_id": prod.id,
                        "name": acquiring.name,
                        "kind": "percent",
                        "category": "Эквайринг",
                        "percent": acquiring.price / price,
                        "value": acquiring.price,
                        "expected_value": expected_price * acquiring.price / price,
                    },
                ]
            )
            total_expenses += (
                ozon_com.price
                + last_mile.price
                + logistics.price
                + processing.price
                + acquiring.price
            )

            # рентабельность
            if prod.profitability_norm:
                prof_norm_percent = prod.profitability_norm.value
            else:
                prof_norm_percent = 0
            prof_norm_value = price * prof_norm_percent
            expected_prof_norm_value = expected_price * prof_norm_percent
            data.append(
                {
                    "product_id": prod.id,
                    "name": "Ожидаемая доходность",
                    "kind": "percent",
                    "category": "Рентабельность",
                    "percent": prof_norm_percent,
                    "value": prof_norm_value,
                    "expected_value": expected_prof_norm_value,
                },
            )
            total_expenses += prof_norm_value
            # инвест.затраты
            if prod.investment_expenses_id:
                inv_exp_percent = prod.investment_expenses_id.value
            else:
                inv_exp_percent = 0
            inv_exp_value = price * inv_exp_percent
            expected_inv_exp_value = expected_price * inv_exp_percent
            data.append(
                {
                    "product_id": prod.id,
                    "name": "Investment",
                    "kind": "percent",
                    "category": "Investment",
                    "percent": inv_exp_percent,
                    "value": inv_exp_value,
                    "expected_value": expected_inv_exp_value,
                },
            )
            total_expenses += inv_exp_value
            # налог
            if tax.startswith("earnings_minus_expenses"):
                tax_value = abs((price - total_expenses) * tax_percent)
            else:
                tax_value = price * tax_percent
            data.append(
                {
                    "product_id": prod.id,
                    "name": "Налог",
                    "description": tax_description,
                    "kind": "percent",
                    "category": "Налоги",
                    "percent": tax_value / price,
                    "value": tax_value,
                    "expected_value": expected_price * tax_value / price,
                },
            )
            print(f"{idx} - All expenses were updated.")

        products.all_expenses_ids.unlink()
        self.create(data)
