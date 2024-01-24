# -*- coding: utf-8 -*-
{
    "name": "ozon",
    "summary": """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    "description": """
        Long description of module's purpose
    """,
    "author": "My Company",
    "website": "https://www.yourcompany.com",
    "category": "Uncategorized",
    "version": "0.2.1",
    "depends": ["base", "retail"],
    # always loaded
    "data": [
        ### security
        "security/price/price_history/ir.model.access.csv",
        "security/price/fix_expenses/ir.model.access.csv",
        "security/price/cost/ir.model.access.csv",
        "security/price/pricing/ir.model.access.csv",
        "security/price/name_competitors/ir.model.access.csv",
        "security/price/profitability_norm/profitability_norm/ir.model.access.csv",
        "security/price/profitability_norm/profitability_norm_wizard/ir.model.access.csv",
        "security/lots/ir.model.access.csv",
        # "security/lots/tracked_search_queries/ir.model.access.csv",
        "security/categories/categories/ir.model.access.csv",
        "security/commissions/local_index/ir.model.access.csv",
        "security/commissions/fee_ozon/ir.model.access.csv",
        "security/commissions/logistics_price/ir.model.access.csv",
        "security/import/import/ir.model.access.csv",
        "security/competitors/products_competitors/ir.model.access.csv",
        "security/competitors/price_competitors/ir.model.access.csv",
        "security/competitors/search_query_queue/ir.model.access.csv",
        "security/competitors/analysis_competitors/ir.model.access.csv",
        "security/competitors/analysis_competitors_record/ir.model.access.csv",
        "security/search_queries/search_queries/ir.model.access.csv",
        "security/transaction/ir.model.access.csv",
        "security/stock/ir.model.access.csv",
        "security/product_fee/ir.model.access.csv",
        "security/sale/ir.model.access.csv",
        "security/tasks/ir.model.access.csv",
        "security/indirect_percent_expenses/ir.model.access.csv",
        "security/supplementary_categories/ir.model.access.csv",
        "security/posting/ir.model.access.csv",
        "security/warehouse/ir.model.access.csv",
        "security/fbo_supply_order/ir.model.access.csv",
        "security/action/ir.model.access.csv",
        ### views
        "views/menu.xml",
        "views/price/menu.xml",
        "views/price/price_history.xml",
        "views/price/our_fix_price.xml",
        "views/price/pricing.xml",
        "views/price/mass_pricing.xml",
        "views/price/profitability_norm.xml",
        "views/price/pricing_strategy.xml",
        "views/lots/menu.xml",
        "views/lots/lots.xml",
        "views/lots/tracked_search_queries.xml",
        "views/lots/lots_for_gpt.xml",
        "views/lots/analysis_data.xml",
        "views/categories/menu.xml",
        "views/categories/categories.xml",
        "views/categories/supplementary_categories.xml",
        "views/commissions/menu.xml",
        "views/commissions/local_index.xml",
        "views/commissions/fee_ozon.xml",
        "views/commissions/logistics_price.xml",
        "views/commissions/product_fee.xml",
        "views/import/import.xml",
        "views/competitors/menu.xml",
        "views/competitors/products_competitors.xml",
        "views/competitors/search_query_queue.xml",
        "views/competitors/price_competitors.xml",
        "views/competitors/analysis_competitors.xml",
        "views/indirect_percent_expenses/indirect_percent_expenses.xml",
        "views/actions/assign_an_insurance_coefficient.xml",
        "views/issue_report/menu.xml",
        "views/search_queries/search_queries.xml",
        "views/transactions/transactions.xml",
        "views/stocks/stocks.xml",
        "views/sale/sale.xml",
        "views/tasks/tasks.xml",
        "views/posting/menu.xml",
        "views/posting/posting.xml",
        "views/posting/warehouse.xml",
        "views/fbo_supply_order/fbo_supply_order.xml",
        "views/fbo_supply_order/fbo_supply_order_product.xml",
        "views/action/action.xml",
        "views/action/action_candidate.xml",
    ],
    "demo": [
        "demo/demo.xml",
    ],
}
