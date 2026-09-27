# Officiële Playwright-image: Chromium + alle systeemlibs zitten er al in
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy
ENV PYTHONUNBUFFERED=1 TZ=Europe/Amsterdam
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ /app/
EXPOSE 4040
VOLUME ["/config", "/data"]
CMD ["python", "main.py"]
