FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install runpod

CMD ["python", "handler.py"]