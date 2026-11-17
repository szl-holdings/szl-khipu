FROM python:3.12.7-slim
# Research preview only: resolve and verify an exact base-image digest at release admission.
# Image tag is mutable; this file alone is not a supply-chain qualification.
ENV PORT=7860 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY . /app
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user
EXPOSE 7860
CMD ["python", "space/app.py"]
