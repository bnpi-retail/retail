import logging

from collections import defaultdict
from datetime import datetime, timedelta, date
from odoo import models, fields, api
from odoo.exceptions import UserError
from .drawing_graphs import DrawGraph as df
from ..helpers import delete_records

logger = logging.getLogger(__name__)


class Categories(models.Model):
    _name = "ozon.categories"
    _description = "Категории Ozon"

    name_categories = fields.Char(string="Название", readonly=True)
    c_id = fields.Integer(string="Идентификатор", readonly=True, index=True)
    insurance = fields.Float(string="Страховой коэффициент, %")

    category_manager = fields.Many2one("res.users")
    bcg_matrix_last_update = fields.Datetime()
    abc_group_last_update = fields.Datetime()

    category_total_price = fields.Float(string="Сумма цен товаров категории в продаже")
    category_total_marketing_price = fields.Float(string="Сумма цен для покупателя товаров категории в продаже")
    price_difference = fields.Float(
        string="Cоотношение между нашей ценой и ценой для покупателя")
    is_price_difference_computed = fields.Boolean()

    ozon_products_ids = fields.One2many('ozon.products', 'categories')

    # revenue and expenses
    ozon_report_products_revenue_expenses_ids = fields.One2many(
        'ozon.report.products_revenue_expenses',
        'ozon_categories_id',
    )
    ozon_report_products_revenue_expenses_theory_ids = fields.One2many(
        'ozon.report.products_revenue_expenses_theory',
        'ozon_categories_id',
    )
    period_start = fields.Date(string="Период с", default=date.today() - timedelta(days=31))
    period_finish = fields.Date(string="по", default=date.today() - timedelta(days=1))
    period_preset = fields.Selection([
        ('month', '1 месяц'), ('2month', '2 месяца'), ('3month', '3 месяца')
    ])
    is_promotion_data_correct = fields.Boolean()

    ozon_reward = fields.Float(string="Вознаграждение Озон (процент)")
    acquiring = fields.Float(string="Эквайринг (процент)")
    promo = fields.Float(string="Расходы на продвижение (процент)")
    return_logistics = fields.Float(string="Обратная логистика (процент)")

    ozon_name_value_ids = fields.One2many(
        "ozon.name_value",
        "ozon_categories_id",
        compute="compute_products_states",
        domain=["|", ("domain", '=', 'a'), ("domain", '=', False)]
    )
    ozon_name_value_ids_templates = fields.One2many(
        "ozon.name_value",
        "ozon_categories_id",
        domain=["|", ("domain", '=', 'b'), ("domain", '=', False)]
    )

    @api.depends(
        "ozon_products_ids.avg_value_to_use",
        "ozon_products_ids.base_calculation_template_id",
        "ozon_products_ids",
    )
    def compute_products_states(self):
        ids = self.ozon_name_value_ids.ids + self.ozon_name_value_ids_templates.ids
        delete_records("ozon_name_value", ids, self.env)

        avg_value_to_use_state = defaultdict(int)
        template_state = defaultdict(int)
        for product in self.ozon_products_ids:
            avg_value_to_use_state[product.avg_value_to_use] += 1
            template = product.base_calculation_template_id
            template_name = template.name if template else False
            template_state[template_name] += 1

        vals_to_create = [{
            "name": "Всего товаров категории", "value": len(self.ozon_products_ids), "ozon_categories_id": self.id}]

        for name, value in avg_value_to_use_state.items():
            display_name = name
            if name == "report":
                display_name = "Используются значения из последнего отчета по выплатам"
            elif name == "input":
                display_name = "Используются значения введенные вручную в товаре"
            elif name == "category":
                display_name = "Используются значения введенные вручную в категории"
            elif not name:
                display_name = "Опция не выбрана"
            vals_to_create.append({
                "name": f"{display_name}", "value": value, "ozon_categories_id": self.id, "domain": 'a'
            })

        ids = self.env["ozon.name_value"].create(vals_to_create).ids

        for name, value in template_state.items():
            if name is False:
                display_name = "Шаблон не выбран"
            else:
                display_name = name
            self.env["ozon.name_value"].create({
                "name": f"{display_name}", "value": value, "ozon_categories_id": self.id, "domain": 'b'
            })

        self.ozon_name_value_ids = ids

    @api.onchange('period_preset')
    def _onchange_period_preset(self):
        preset = self.period_preset
        period_to = date.today() - timedelta(days=1)
        period_from = period_from = period_to - timedelta(days=30.5)
        if preset:
            if preset == 'month':
                period_from = period_to - timedelta(days=30.5)
            elif preset == '2month':
                period_from = period_to - timedelta(days=61)
            elif preset == '3month':
                period_from = period_to - timedelta(days=91.5)

        self.period_start = period_from
        self.period_finish = period_to

    def action_calculate_revenue_returns_promotion_for_period(self):
        delete_records(
            'ozon_report_products_revenue_expenses',
            self.ozon_report_products_revenue_expenses_ids.ids, self.env)
        delete_records(
            'ozon_report_products_revenue_expenses_theory',
            self.ozon_report_products_revenue_expenses_theory_ids.ids, self.env)
        vals_to_write_table_1 = []
        vals_to_write_table_2 = []
        # revenue
        res = self.calculate_sales_revenue_for_period()
        vals_table_1, vals_table_2, category_revenue, total_revenue = res
        vals_to_write_table_1.append(vals_table_1)
        vals_to_write_table_2.append(vals_table_2)

        # promotion_expenses
        vals_to_write_table_1.append(
            self.calculate_promotion_expenses_for_period(total_revenue, category_revenue))

        # returns
        vals_to_write_table_1.append(
            self.calculate_expenses_row(
                total_revenue=total_revenue,
                category_revenue=category_revenue,
                identifier=3,
                plan_name='Обратная логистика',
            )
        )
        # commission
        vals_to_write_table_2.append(
            self.calculate_commissions_row(
                category_revenue=category_revenue,
                identifier=2,
                plan_name='Вознаграждение Ozon',
            )
        )
        # equiring
        vals_to_write_table_2.append(
            self.calculate_commissions_row(
                category_revenue=category_revenue,
                identifier=3,
                plan_name='Эквайринг',
            )
        )

        self.env['ozon.report.products_revenue_expenses'].create(vals_to_write_table_1)
        self.env['ozon.report.products_revenue_expenses_theory'].create(vals_to_write_table_2)

    def calculate_sales_revenue_for_period(self) -> tuple[dict, dict, float, float]:
        ozon_products_model = self.env['ozon.products']
        category_products_ids = self.ozon_products_ids.ids
        category_revenue, cat_qty = ozon_products_model.get_sum_value_and_qty_from_transaction_value_by_product(
            name='Сумма за заказы',
            ids=category_products_ids,
            start=self.period_start,
            finish=self.period_finish
        )
        total_revenue = ozon_products_model.calc_total_sum(
            'Сумма за заказы', self.period_start, self.period_finish)
        vals_table_1 = {
            'identifier': 1,
            'ozon_categories_id': self.id,
            'name': 'Выручка за период',
            'comment': 'Рассчитывается сложением значений поля "Значение" записей в меню '
                       '"Декомпозированные транзакции" '
                       'за искомый период, соответствующих продуктам категории и с названием '
                       '"Сумма за заказы".',
            'qty': cat_qty,
            'percent_from_total': 100,
            'percent_from_total_category': 100,
            'total_value_category': category_revenue,
            'total_value': total_revenue,
        }
        vals_table_2 = {
            'identifier': 1,
            'ozon_categories_id': self.id,
            'name': 'Выручка за период',
            'comment': 'Рассчитывается сложением значений поля "Значение" записей в меню '
                       '"Декомпозированные транзакции" '
                       'за искомый период, соответствующих продуктам категории и с названием '
                       '"Сумма за заказы".',
            'qty': cat_qty,
            'percent_from_total_category': 100,
            'total_value_category': category_revenue,
            'theoretical_value': '',
        }

        return vals_table_1, vals_table_2, category_revenue, total_revenue

    def calculate_promotion_expenses_for_period(
            self, total_revenue: float, category_revenue: float
    ) -> dict:

        category_products = self.ozon_products_ids
        category_pe_for_period = 0
        qty = 0
        for product in category_products:
            pes = product.promotion_expenses_ids
            for pe in pes:
                if self.period_finish >= pe.date >= self.period_start:
                    qty += 1
                    category_pe_for_period += pe.expense

        ozon_products_model = self.env['ozon.products']
        percent_category = (category_pe_for_period * 100) / category_revenue if category_revenue else 0
        total_promotion_expenses = ozon_products_model.calc_total_sum(
            'Услуги продвижения товаров', self.period_start, self.period_finish)
        percent_from_total = (abs(total_promotion_expenses) * 100) / total_revenue if total_revenue else 0

        accuracy = self.calc_accuracy(self.period_start, self.period_finish)
        self.is_promotion_data_correct = True if accuracy == 'a' else False
        name = 'Расходы на продвижение продукта за период'
        if accuracy == 'c':
            name = 'Расходы на продвижение продукта за период*'

        return {
            'identifier': 2,
            'ozon_categories_id': self.id,
            'name': name,
            'comment': 'Рассчитывается сложением суммы значений поля "Расход" '
                       'затрат на продвижение текущего товара за искомый период.\n',
            'qty': qty,
            'percent_from_total': percent_from_total,
            'total_value': total_promotion_expenses,
            'percent_from_total_category': percent_category,
            'total_value_category': -category_pe_for_period,
            'accuracy': accuracy,
        }

    def calc_accuracy(self, period_start, period_finish) -> str:
        ps = period_start
        pf = period_finish
        query = """
                SELECT
                    period_start_date,
                    period_end_date
                FROM 
                    ozon_import_file
                WHERE 
                    data_for_download = %s
                    AND
                    period_start_date IS NOT NULL
                    AND
                    period_end_date IS NOT NULL
                ORDER BY
                    period_start_date
                """
        self.env.cr.execute(query, ('ozon_ad_campgaign_search_promotion_report', ))
        imports_periods = self.env.cr.fetchall()
        is_covered = False
        if imports_periods:
            joined_periods = []
            start = end = None
            for s, e in imports_periods:
                if not start:
                    start = s
                    end = e
                if start <= s <= end + timedelta(days=1):
                    end = max(end, e)
                else:
                    joined_periods.append((start, end))
                    start = s
                    end = e
                if s == imports_periods[-1][0] and e == imports_periods[-1][1]:
                    joined_periods.append((start, end))

            joined_periods.reverse()

            for start, end in joined_periods:
                if start <= ps <= end:
                    if start <= pf <= end:
                        is_covered = True
                        break

        accuracy = 'a' if is_covered else 'c'

        return accuracy

    def calculate_expenses_row(
            self, total_revenue: float, category_revenue: float, identifier: int,
            plan_name: str) -> dict:

        ozon_price_component_id = self.env["ozon.price_component"].search([('name', '=', plan_name)]).id
        if not ozon_price_component_id:
            raise UserError("Создайте справочник фактических и плановых статей затрат в Планировании"
                            f" в котором плановым будет запись {plan_name}")
        ozon_price_component_match = self.env["ozon.price_component_match"].search([
            ('price_component_id', '=', ozon_price_component_id)
        ])

        qty = []
        category_amount = 0
        all_products_amount = 0
        components = []
        category_products_ids = self.ozon_products_ids.ids
        for record in ozon_price_component_match:
            name = record.name
            category_value, cat_qty = self.env['ozon.products'].get_sum_value_and_qty_from_transaction_value_by_product(
                name=name,
                ids=category_products_ids,
                start=self.period_start,
                finish=self.period_finish
            )
            category_amount += category_value
            qty.append(cat_qty)
            components.append(f"{name}: количество- {cat_qty}, значение-{category_value}\n")

            all_products_amount += self.env['ozon.products'].calc_total_sum(
                name, self.period_start, self.period_finish)

        qty = max(qty) if qty else 0
        components = ''.join(components)
        percent_category = (abs(category_amount) * 100) / category_revenue if category_revenue else 0
        percent_from_total = (abs(all_products_amount) * 100) / total_revenue if total_revenue else 0
        vals = {
            'identifier': identifier,
            'ozon_categories_id': self.id,
            'name': plan_name,
            'comment': 'Рассчитывается суммированием значений записей "Декомпозированые транзакции" '
                       'с названиями указанными в поле "Фактическая статья затрат Ozon" напротив '
                       f'которых указано значение {plan_name} '
                       '(в меню Планирование > Фактические/плановые статьи). '
                       'Суммируются "Декомпозированые транзакции" соответствующие искомому периоду и '
                       f' продуктам категории\n\n{components}',
            'qty': qty,
            'percent_from_total': percent_from_total,
            'total_value': all_products_amount,
            'percent_from_total_category': percent_category,
            'total_value_category': category_amount,
        }
        return vals

    def calculate_commissions_row(
            self, category_revenue: float, identifier: int, plan_name: str) -> dict:

        ozon_price_component_id = self.env["ozon.price_component"].search([('name', '=', plan_name)]).id
        if not ozon_price_component_id:
            raise UserError("Создайте справочник фактических и плановых статей затрат в Планировании"
                            f" в котором плановым будет запись {plan_name}")
        ozon_price_component_match = self.env["ozon.price_component_match"].search([
            ('price_component_id', '=', ozon_price_component_id)
        ])
        qty = []
        category_amount = 0
        components = []
        category_products_ids = self.ozon_products_ids.ids
        for record in ozon_price_component_match:
            name = record.name
            category_value, cat_qty = self.env['ozon.products'].get_sum_value_and_qty_from_transaction_value_by_product(
                name=name,
                ids=category_products_ids,
                start=self.period_start,
                finish=self.period_finish
            )
            category_amount += category_value
            qty.append(cat_qty)
            components.append(f"{name}: количество- {cat_qty}, значение-{category_value}\n")

        qty = max(qty) if qty else 0
        components = ''.join(components)
        percent_category = (abs(category_amount) * 100) / category_revenue if category_revenue else 0

        product = self.ozon_products_ids[0] if self.ozon_products_ids else None
        if product:
            theoretical_value = product.get_theoretical_value(plan_name)
            if plan_name == "Эквайринг":
                if qty:
                    theoretical_value = str(round((float(theoretical_value) * 100) / (category_revenue / qty), 2)) + '% максимально'
                else:
                    pass

        vals = {
            'identifier': identifier,
            'ozon_categories_id': self.id,
            'name': plan_name,
            'comment': 'Рассчитывается суммированием значений записей "Декомпозированые транзакции" '
                       'с названиями указанными в поле "Фактическая статья затрат Ozon" напротив '
                       f'которых указано значение {plan_name} '
                       '(в меню Планирование > Фактические/плановые статьи). '
                       'Суммируются "Декомпозированые транзакции" соответствующие искомому периоду и '
                       f'продуктам категории\n\n{components}',
            'qty': qty,
            'percent_from_total_category': percent_category,
            'total_value_category': category_amount,
            'theoretical_value': theoretical_value,
        }
        return vals

    @api.model
    def _name_search(
        self, name="", args=None, operator="ilike", limit=10, name_get_uid=None
    ):
        args = list(args or [])
        if name:
            args += [("name_categories", operator, name)]
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    def action_compute_average_prices_difference(self):
        for record in self:
            query = """
                    SELECT
                         SUM(price) as total_price,
                         SUM(marketing_price) as total_marketing_price
                    FROM
                        ozon_products
                    WHERE
                        categories = %s
                        AND
                        is_selling = %s
            """
            self.env.cr.execute(query, (record.id, True))
            result = self.env.cr.fetchone()

            total_price = result[0] if result and result[0] else 0.00001
            total_marketing_price = result[1] if result and result[1] else 0

            if result and (result[0] or result[1]):
                record.price_difference = (total_price - total_marketing_price) / total_price

            record.category_total_price = total_price
            record.category_total_marketing_price = total_marketing_price

            record.is_price_difference_computed = True


class GenerateUrlForDownloadGrpahData(models.Model):
    _inherit = "ozon.categories"

    def get_url(self, model_name, record_id, field_name):
        return f'/web/content_text?model={model_name}&id={record_id}&field={field_name}'

    def get_download_url(self, field_name):
        model_name = self._name
        record_id = self.id
        url = self.get_url(model_name, record_id, field_name)
        return url


class GraphSaleThisYear(models.Model):
    _inherit = "ozon.categories"

    img_data_sale_this_year = fields.Text(string="Json data filed")
    img_sale_this_year = fields.Binary(string="График продаж за текущий год")

    def download_data_sale_this_year(self):
        field_name = "img_data_sale_this_year"
        url = self.get_download_url(field_name)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


class GraphSaleLastYear(models.Model):
    _inherit = "ozon.categories"

    img_data_sale_last_year = fields.Text(string="Json data filed")
    img_sale_last_year = fields.Binary(string="График продаж за прошлый год")

    def download_data_sale_last_year(self):
        field_name = "img_data_sale_last_year"
        url = self.get_download_url(field_name)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


class GraphInterest(models.Model):
    _inherit = "ozon.categories"

    img_data_analysis_data_this_year = fields.Text(string="Json data filed")
    img_analysis_data_this_year = fields.Binary(string="График интереса текущий год")

    def download_data_analysis_data_this_year(self):
        field_name = "img_data_analysis_data_this_year"
        url = self.get_download_url(field_name)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


class ActionGraphs(models.Model):
    _inherit = "ozon.categories"

    def action_draw_graphs_by_categories(self, auto=None):
        logger.info('draw_sale_this_year')
        self.draw_sale_this_year()
        logger.info('draw_sale_last_year')
        self.draw_sale_last_year()
        logger.info('draw_graph_interest')
        self.draw_graph_interest()
        logger.info('draw_graphs_products')

        self.draw_graphs_products(self.ozon_products_ids, auto)

        return True

    def draw_sale_this_year(self):
        year = self._get_year()

        data_for_send = {}

        categorie_record = self[0]

        products_records = self.env["ozon.products"].search(
            [
                ("categories", "=", categorie_record.id),
                # ("is_alive", "=", True),
                # ("is_selling", "=", True),
            ]
        )

        for product_record in products_records:
            sale_records = self.env["ozon.sale"].search(
                [
                    ("product", "=", product_record.id),
                    ("date", ">=", f"{year}-01-01"),
                    ("date", "<=", f"{year}-12-31"),
                ]
            )

            if not sale_records:
                continue

            graph_data = {"dates": [], "values": []}

            for sale_record in sale_records:
                graph_data["dates"].append(sale_record.date.strftime("%Y-%m-%d"))
                graph_data["values"].append(sale_record.qty)

            data_for_send[product_record.id] = graph_data

        payload = {
            "model": "categorie_sale_this_year",
            "categorie_id": categorie_record.id,
            "data": data_for_send,
        }

        bytes_plot, data_current = df().post(payload)
        self.img_sale_this_year, self.img_data_sale_this_year = bytes_plot, data_current

        return products_records

    def draw_sale_last_year(self):
        year = self._get_year() - 1

        data_for_send = {}

        categorie_record = self[0]

        products_records = self.ozon_products_ids

        for product_record in products_records:
            sale_records = self.env["ozon.sale"].search(
                [
                    ("product", "=", product_record.id),
                    ("date", ">=", f"{year}-01-01"),
                    ("date", "<=", f"{year}-12-31"),
                ]
            )

            if not sale_records:
                continue

            graph_data = {"dates": [], "values": []}

            for sale_record in sale_records:
                graph_data["dates"].append(sale_record.date.strftime("%Y-%m-%d"))
                graph_data["values"].append(sale_record.qty)

            data_for_send[product_record.id] = graph_data

        payload = {
            "model": "categorie_sale_last_year",
            "categorie_id": categorie_record.id,
            "data": data_for_send,
        }

        bytes_plot, data_current = df().post(payload)
        self.img_sale_last_year, self.img_data_sale_last_year = bytes_plot, data_current

        return products_records

    def draw_graph_interest(self):
        year = self._get_year()

        data_for_send = defaultdict(lambda: {
            "hits_view": 0,
            "hits_tocart": 0,
        })

        categorie_record = self[0]

        products_ids = self.ozon_products_ids.ids

        analysis_data_records = self.env["ozon.analysis_data"].search(
            [
                ("product", "in", products_ids),
                ("date", ">=", f"{year}-01-01"),
                ("date", "<=", f"{year}-12-31"),
            ]
        )

        graph_data = {"dates": [], "hits_view": [], "hits_tocart": []}

        for analysis_data_record in analysis_data_records:
            average_date = analysis_data_record.date
            data_for_send[average_date.strftime("%Y-%m-%d")]["hits_view"] += analysis_data_record.hits_view
            data_for_send[average_date.strftime("%Y-%m-%d")]["hits_tocart"] += analysis_data_record.hits_tocart

        for date, vals in data_for_send.items():
            graph_data['dates'].append(date)
            graph_data['hits_view'].append(vals['hits_view'])
            graph_data['hits_tocart'].append(vals['hits_tocart'])

        data_ = {1: graph_data}

        payload = {
            "model": "categorie_analysis_data",
            "categorie_id": categorie_record.id,
            "data": data_,
        }

        logger.info("draw_graph_interest: df().post(payload)")
        bytes_plot, data_views, data_tocart = df().post(payload)

        self.img_analysis_data_this_year = bytes_plot
        self.img_data_analysis_data_this_year = {
            "hits_view": data_views,
            "hits_tocart": data_tocart,
        }

    def draw_graphs_products(self, products_records, auto):
        logger.info(f"All records: {len(products_records)}")

        for index, product_record in enumerate(products_records):
            if auto:
                last_plots_update = product_record.last_plots_update
                logger.info(last_plots_update)
                if last_plots_update and last_plots_update + timedelta(hours=12) > datetime.now():
                    continue
            product_record.action_draw_graphs()
            product_record.last_plots_update = datetime.now()

            logger.info(index + 1)

    def _get_year(self) -> str:
        return datetime.now().year


class NameGetCustom(models.Model):
    _inherit = "ozon.categories"

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            result.append((record.id, record.name_categories))
        return result

class CategoryFees(models.Model):
    _inherit = "ozon.categories"

    def _trading_scheme_fees(self):
        ozon_fee_recs = self.env["ozon.ozon_fee"].search([("category", "=", self.id)])
        return {fee.name: fee.value for fee in ozon_fee_recs}