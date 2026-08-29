# SZL KHIPU hologram — stdlib HTTP, numpy kernels, no Gradio. No npm ci.
# GCR pin — ECR Public and Docker Hub python: are factory exit 128.
# Flatten payload at Hub root: Dockerfile + server.py + index.html + README + szl_khipu/.
FROM mirror.gcr.io/library/python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=7860
RUN pip install --no-cache-dir "numpy>=1.26"
COPY server.py ./server.py
COPY index.html ./index.html
COPY energy.py ./energy.py
COPY szl_khipu ./szl_khipu
EXPOSE 7860
CMD ["python", "-u", "server.py"]
