FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY api/requirements-public.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"
COPY api /app/api
COPY web /app/web
COPY examples /app/examples
WORKDIR /app/api
USER 1000:1000
EXPOSE 8080
CMD ["python","-m","uvicorn","app.methods_main:app","--host","0.0.0.0","--port","8080"]
