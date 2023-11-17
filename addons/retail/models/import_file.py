import base64
import xml.etree.ElementTree as ET

from odoo import models, fields, api, exceptions


class ImportFile(models.Model):
    _name = 'retail.import_file'
    _description = 'Импорт'

    data_for_download = fields.Selection(
        [
            ('cost_price', 'Себестоимость из 1C'),
        ], 
        string='Данные для загрузки'
    )

    file = fields.Binary(
        string='File',
        attachment=True,
        help='Выбрать файл'
    )

    def download_sample(self):
        pass

    @api.model
    def create(self, values):
        if not 'file' in values or not values['file']:
            raise exceptions.ValidationError('Отсутствует XML файл.')

        content = base64.b64decode(values['file'])

        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            raise exceptions.ValidationError('Файл не является XML!')

        products = self.env['retail.products']
        seller_model = self.env['retail.seller']
        cost_price_model = self.env['retail.cost_price']
        products_ozon_model = self.env['ozon.products']

        for offer in root.findall('.//offer'):
            id = offer.find('id').text
            artikul = offer.find('artikul').text
            name = offer.find('name').text
            price_base = offer.find('priceOzoneBase').text.replace(',', '.')
            price_old = offer.find('priceOzoneOld').text
            cost_price = offer.find('CostPrice').text
            picture = offer.find('picture').text
            height = offer.find('height').text
            width = offer.find('width').text
            depth = offer.find('depth').text
            weight = offer.find('weight').text
            description = offer.find('description').text
            vid_tovara = offer.find('VidTovara').text
            ozon_category_id = offer.find('ozon_category_id').text
            ozon_title = offer.find('ozon_title').text
            ozon_fulltitle = offer.find('ozon_fulltitle').text
            
            product = products.search([('product_id', '=', id)])
            if not product:
                product = products.create({
                    'name': name,
                    'product_id': id,
                    'description': description,
                    'length': float(depth),
                    'width': float(width),
                    'height': float(height),
                    'weight': float(weight),
                })
            seller = seller_model.search([('ogrn', '=', 2433445653456)])

            cost_price_model.create({
                'products': product.id,
                'seller': seller.id,
                'price': float(price_base),
            })

            localization_index = self.env['ozon.localization_index'] \
                .search([], limit=1)

            products_ozon_model.create({
                'categories': ozon_title,
                'full_categories': ozon_fulltitle,
                'id_on_platform': ozon_category_id,
                'index_localization': localization_index.id,
                'products': product.id,
                'seller': seller.id,
                'trading_scheme': 'FBS',
                'delivery_location': 'ППЦ',

            })

        return super(ImportFile, self).create(values)

