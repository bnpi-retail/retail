FROM odoo:16

USER root

COPY ./requirements.txt /etc/odoo/

RUN pip install -r /etc/odoo/requirements.txt --no-cache-dir

# RUN mkdir /var/lib/odoo/.local

RUN chown -R odoo:odoo /var/lib/odoo/.local

USER odoo