FROM odoo:16

USER root

COPY ./requirements.txt /etc/odoo/

RUN pip3 install --no-cache-dir -r /etc/odoo/requirements.txt

# RUN mkdir /var/lib/odoo/.local

RUN chown -R odoo:odoo /var/lib/odoo/.local

USER odoo