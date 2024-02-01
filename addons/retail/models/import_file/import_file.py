import base64
from importlib.metadata import requires
import os
import xml.etree.ElementTree as ET

from odoo import models, fields, api


class ImportFile(models.Model):
    """
    Model for import all files in 'Retail' app
    """

    _name = "retail.import_file"
    _description = "Импорт"

    file = fields.Binary(
        string="Загрузить свой файл",
        requires=False,
        attachment=True,
        help="Выбрать файл",
    )
    timestamp = fields.Date(
        string="Дата импорта", default=fields.Date.today, readonly=True
    )
    data_for_download = fields.Selection(
        [("cost_price", "Себестоимость 1C")],
        string="Данные для загрузки",
        help="Выберите данные для загрузки",
    )

    def name_get(self):
        """
        Rename name records
        """
        result = []
        for record in self:
            id = record.id
            name = f"Загруженный файл № {id}"
            result.append((id, name))
        return result

    def get_seller(self):
        """
        Get seller record from
        """
        model_seller = self.env["retail.seller"]

        ogrn = 2433445653456

        seller = model_seller.search([("ogrn", "=", ogrn)])

        if not seller:
            seller = model_seller.create(
                {
                    "name": "Seller",
                    "ogrn": ogrn,
                    "fee": 5,
                }
            )

        return seller

    def fill_product_from_1C(self):
        """
        Fill data from 1C ./files/products.xml
        """
        content = self.open_file()

        root = ET.fromstring(content)

        model_products = self.env["retail.products"]

        seller = self.get_seller()

        for offer in root.findall(".//offer"):
            id = offer.find("id").text
            name = offer.find("name").text
            price_base = offer.find("priceOzoneBase").text.replace(",", ".")
            height = offer.find("height").text
            width = offer.find("width").text
            depth = offer.find("depth").text
            weight = offer.find("weight").text
            description = offer.find("description").text
            ozon_category_id = offer.find("ozon_category_id").text
            ozon_title = offer.find("ozon_title").text
            ozon_fulltitle = offer.find("ozon_fulltitle").text

            artikul = offer.find("artikul").text
            price_old = offer.find("priceOzoneOld").text
            cost_price = offer.find("CostPrice").text
            picture = offer.find("picture").text
            vid_tovara = offer.find("VidTovara").text

            product = model_products.search([("product_id", "=", ozon_category_id)])

            if not product:
                product = model_products.create(
                    {
                        "name": name,
                        "product_id": ozon_category_id,
                        "description": description,
                        "length": float(depth),
                        "width": float(width),
                        "height": float(height),
                        "weight": float(weight),
                    }
                )

            self.env["retail.cost_price"].create(
                {
                    "products": product.id,
                    "seller": seller.id,
                    "price": float(price_base),
                }
            )

            if vid_tovara:
                model_categories = self.env["ozon.categories"]
                obj_vid_tovara = model_categories.search(
                    [("name_categories", "=", vid_tovara)], limit=1
                )
                if not obj_vid_tovara:
                    obj_vid_tovara = model_categories.create(
                        {"name_categories": vid_tovara}
                    )

            values = {
                "full_categories": ozon_fulltitle,
                "id_on_platform": id,
                "products": product.id,
                "seller": seller.id,
                "trading_scheme": "FBS",
                "delivery_location": "PC",
            }

            if obj_vid_tovara:
                values["categories"] = obj_vid_tovara.id

            self.env["ozon.products"].create(values)

    def is_retail_product_exists(self, product_id):
        result = self.env["retail.products"].search(
            [("product_id", "=", product_id)],
            limit=1,
        )
        return result if result else False

    def is_cost_price_exists(self, product_id, cost_type_id):
        result = self.env["retail.cost_price"].search(
            [("product_id", "=", product_id), ("cost_type_id", "=", cost_type_id)],
            limit=1,
        )
        return result if result else False

    def import_cost_price(self, content):
        root = ET.fromstring(content)
        cost_type_id = (
            self.env["retail.cost_act_type"]
            .search([("name", "=", "Себестоимость 1С")])
            .id
        )
        cost_act_data = {"act_type": cost_type_id}

        cost_act_prod_ids_data = []
        for offer in root.findall("offer"):
            artikul = offer.find("artikul").text
            print(artikul)
            if retail_product := self.is_retail_product_exists(product_id=artikul):
                cp = float(offer.find("CostPrice").text)
                prod_data = {"product_id": retail_product.id, "cost": cp}
                cost_act_prod_ids_data.append(prod_data)
            else:
                print(f"Товар с артикулом {artikul} не найден")

        cost_act_prod_ids = (
            self.env["retail.cost_act_product"].create(cost_act_prod_ids_data).ids
        )
        cost_act_data["cost_act_product_ids"] = cost_act_prod_ids

        self.env["retail.cost_act"].create(cost_act_data)

    @api.model
    def create(self, values):
        """
        1) Fill database different data
        """
        content = base64.b64decode(values["file"])
        content = content.decode("utf-8")
        if values["data_for_download"] == "cost_price":
            self.import_cost_price(content)

        return super(ImportFile, self).create(values)
