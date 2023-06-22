FROM python:3.11.0
WORKDIR /app/
COPY . .
RUN python3.11 -m pip install --no-cache-dir --no-warn-script-location --upgrade pip \
    && python3.11 -m pip install --no-cache-dir --no-warn-script-location --user -r requirements.txt

