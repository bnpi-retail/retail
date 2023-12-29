# -*- coding: utf-8 -*-
def migrate(cr, installed_version):
    """
    Creating a temporary field to store the percentage data
    """

    cr.execute("ALTER TABLE ozon_tasks DROP COLUMN manager")
    cr.execute("ALTER TABLE ozon_products DROP COLUMN full_categories")
