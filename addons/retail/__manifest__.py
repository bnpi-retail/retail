# -*- coding: utf-8 -*-
{
    "name": "retail",
    "summary": """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    "description": """
        Long description of module's purpose
    """,
    "author": "StrunkGroove",
    "website": "#",
    "category": "Retail",
    "version": "0.1",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        # 'views/views.xml',
        "views/menu.xml",
        "views/cost_price/cost_price.xml",
        "views/import/import.xml",
        "views/products/products.xml",
        "views/seller/seller.xml",
    ],
    "demo": [
        "demo/demo.xml",
    ],
}
