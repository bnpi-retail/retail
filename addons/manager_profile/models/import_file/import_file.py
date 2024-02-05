import base64

from odoo import models, fields, api, exceptions


class ImportFile(models.Model):
    _name = "parser.import_file"
    _description = "Импорт"

    timestamp = fields.Date(
        string="Дата импорта", default=fields.Date.today, readonly=True
    )
    data_for_download = fields.Selection(
        [
            ("parser_plugin", "Товары Ozon (Chrome Extension)"),
        ],
        string="Данные для загрузки",
    )
    worker = fields.Char(string="Сотрудник")

    file = fields.Binary(
        attachment=True, string="Файл для загрузки своих данных", help="Выбрать файл"
    )


class CreateMethod(models.Model):
    _inherit = "parser.import_file"

    @api.model
    def create(self, values):
        if not "file" in values or not values["file"]:
            raise exceptions.ValidationError("Отсутствует файл.")

        if not "data_for_download" in values or not values["data_for_download"]:
            raise exceptions.ValidationError("Необходимо выбрать 'данные для загрузки'")
        
        content = base64.b64decode(values["file"])
        content = content.decode("utf-8")
        lines = content.split("\n")

        if values["data_for_download"] == "parser_plugin":
            self.import_products_plugin(lines)

        return super(ImportFile, self).create(values)


class ImportProductsPlugin(models.Model):
    _inherit = "parser.import_file"
    
    def import_products_plugin(self, lines):
        our_product_record = self.find_our_product(lines)

        model_competitors_products = self.env["parser.products_competitors"]

        for line in lines[1:]:
            values_list = line.split(",")
            if len(values_list) != 9: continue

            (
                number, search, seller, sku, price, price_without_sale,
                price_with_card, href, name,
            ) = values_list

            if price_with_card == 'None': price_with_card = 0
            if price_without_sale == 'None': price_without_sale = 0
            if price == 'None': price = 0

            value = {
                "number": str(number),
                "search_query": str(search),
                "seller": str(seller),
                "id_product": str(sku),
                "price": float(price),
                "price_without_sale": float(price_without_sale),
                "price_with_card": float(price_with_card),
                "url": str(href),
                "name": str(name),
            }

            if our_product_record:
                value["product"] = our_product_record.id

            model_competitors_products.create(value)

    def find_our_product(self, lines):
        model_products = self.env["ozon.products"]
        for line in lines[1:]:
            values = line.split(",")
            if len(values) != 9: continue
            
            sku = str(values[3])
            record = model_products.search([
                # ("sku", "=", sku),
                # ("fbo_sku", "=", sku),
                ("fbs_sku", "=", sku), 
            ])
            if record:
                return record


class NameGet(models.Model):
    _inherit = "parser.import_file"

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
