import base64
import xml.etree.ElementTree as ET

from odoo import models, fields, api, exceptions


class ImportFile(models.Model):
    _name = 'retail.import_file'
    _description = 'Импорт'

    type = fields.Selection([
        ('local_coeff', 'Индекс локализации, коэффициент'),
        ('local_percent', 'Индекс локализации, проценты'),
        ('cost_price', 'Себестоимость'),
    ], string='Тип')

    file = fields.Binary(
        string='File',
        attachment=True,
        help='Выбрать файл'
    )

    @api.model
    def create(self, values):
        if 'file' in values and values['file']:
            content = base64.b64decode(values['file'])

            try:
                root = ET.fromstring(content)
            except ET.ParseError:
                raise exceptions.ValidationError(
                    'Файл не является XML!'
                )
            
            answer = ''

            seller_model = self.env['retail.seller']
            file_import = self.env['retail.import_file']

            for cost_price in root.findall('cost_price'):
                info_prodct = cost_price.find('product').text

                seller = cost_price.find('seller')
                seller_name = seller.find('name').text
                seller_ogrn = seller.find('ogrn').text
                seller_fee = seller.find('fee').text

                price = cost_price.find('price').text

                obj_seller = seller_model.search([('name', '=', seller_name)])
                if seller:
                    file_import.create({
                    'seller': obj_seller.id,
                    'price': price
                })
                else:
                    seller_model.create({
                        'name': seller_name,
                        'ogrn': seller_ogrn,
                        'fee': seller_fee
                    })
                    file_import.create({
                    'seller': obj_seller.id,
                    'price': price
                })

                # answer += f"name_product: {name_product}, name_seller: {seller_name}, price: {price}\n"
                
            raise exceptions.ValidationError(answer)
    
        raise exceptions.ValidationError('Отсутствует XML файл.')