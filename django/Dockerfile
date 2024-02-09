FROM python:3.11

ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip

WORKDIR /app

COPY ./app /app

COPY ./requirements.txt /app

RUN pip install -r requirements.txt