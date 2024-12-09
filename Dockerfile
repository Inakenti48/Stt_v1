FROM python:3.12.4

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["sh", "-c", "gunicorn test_v5:app --bind 0.0.0.0:8000 & python orders_db_v1_5.py"]
