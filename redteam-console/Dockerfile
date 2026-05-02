FROM python:3.9-slim
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpcap-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
# Le conteneur dort par défaut ; utiliser `docker exec -it redteam-attacker python app.py --mode inject`
CMD ["sleep", "infinity"]
