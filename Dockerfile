FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create config from example if the operator hasn't provided one
RUN test -f config.yaml || cp config.example.yaml config.yaml

CMD ["python", "bot.py"]
