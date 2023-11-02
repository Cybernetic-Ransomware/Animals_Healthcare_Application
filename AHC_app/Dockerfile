FROM python:3.11.3
LABEL authors="AM"
WORKDIR /app
COPY Pipfile Pipfile.lock ./
RUN python -m pip install --upgrade pip
RUN pip install pipenv &&  \
    pipenv install --dev --system --deploy
COPY . .
