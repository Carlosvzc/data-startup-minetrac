FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/ services/
COPY .streamlit/config.toml .streamlit/config.toml
COPY data/clean/ data/clean/
EXPOSE 8501
CMD ["python","-m","streamlit","run","services/tablero/app.py","--server.address=0.0.0.0","--server.headless=true","--browser.gatherUsageStats=false"]


