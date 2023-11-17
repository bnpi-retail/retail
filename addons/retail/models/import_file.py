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
        file_import = self.env['retail.import_file']

        for offer in root.findall('.//offer'):
            id = offer.find('id').text
            artikul = offer.find('artikul').text
            name = offer.find('name').text
            price_base = offer.find('priceOzoneBase').text
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

            products.create({
                'name': name,
                'description': description,
                'length': depth,
                'width': width,
                'height': height,
                'weight': weight,
            })

        return super(ImportFile, self).create(values)

