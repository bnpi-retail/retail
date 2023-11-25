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
    "version": "0.1",
    "depends": ["base", "retail"],
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "views/menu.xml",
        "views/price/menu.xml",
        "views/price/count_price.xml",
        "views/price/price_history.xml",
        # 'views/price/our_price_history.xml',
        "views/price/our_fix_price.xml",
        "views/price/pricing.xml",
        "views/lots/lots.xml",
        "views/categories/categories.xml",
        "views/commissions/menu.xml",
        "views/commissions/local_index.xml",
        "views/commissions/fee_ozon.xml",
        "views/commissions/logistics_price.xml",
        "views/movement_of_funds/movement_of_funds.xml",
        "views/import/import.xml",
        "views/competitors/menu.xml",
        "views/competitors/products_competitors.xml",
        "views/competitors/price_competitors.xml",
    ],
    "demo": [
        "demo/demo.xml",
    ],
}
