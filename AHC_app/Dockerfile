FROM python:3.11.3
LABEL authors="AM"
WORKDIR /app
COPY Pipfile Pipfile.lock ./

RUN python -m pip install --upgrade pip &&  \
    pip install --no-cache-dir pipenv &&  \
    pipenv install --dev --system --deploy \

RUN apt-get update &&  \
    apt-get install -y cron \

COPY . .
