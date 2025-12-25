FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir flask jupyter_client ipykernel pandas matplotlib scikit-learn numpy seaborn plotly psycopg2-binary langchain-community sqlalchemy shap mlflow

COPY server.py /app/server.py

EXPOSE 5000

CMD ["python", "server.py"]