# Dockerfile
FROM python:3.9

WORKDIR /app
RUN useradd -ms /bin/bash user

RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "main.py"]
