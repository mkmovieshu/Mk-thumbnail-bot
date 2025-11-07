# Use slim Python
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080

# Expose port for health
EXPOSE 8080

# Run bot (webserver thread + polling)
CMD ["python", "bot/main.py"]
