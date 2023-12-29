FROM odoo:16

COPY ./requirements.txt /odoo/
RUN cd /odoo && pip install -r requirements.txt
RUN cd /odoo && pip install plotly==5.18.0