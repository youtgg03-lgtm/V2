# Alternative to Railway's auto-detected Railpack/mise build.
# If you hit build-system issues with the default builder (e.g. the
# "mise ... GitHub artifact attestations" error), this Dockerfile
# sidesteps it entirely — Railway auto-detects and uses this instead
# once it's present in the repo root.

FROM python:3.11-slim

WORKDIR /app

# System deps for Pillow (qrcode[pil] needs it)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway sets $PORT — main.py already reads it via config.py
CMD ["python", "main.py"]
