FROM python:3.9 
WORKDIR /app
COPY webhook.py /app/
RUN pip install flask && \
    apt-get update && apt-get install -y curl && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && mv kubectl /usr/local/bin/
CMD ["python", "webhook.py"]
