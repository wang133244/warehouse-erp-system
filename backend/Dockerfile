FROM python:3.12-slim

WORKDIR /repo
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/repo

COPY backend /repo/backend
RUN pip install --no-cache-dir \
    "fastapi>=0.141,<1" \
    "uvicorn[standard]>=0.52,<1" \
    "sqlalchemy>=2.0,<3" \
    "alembic>=1.19,<2" \
    "pymysql>=1.2,<2" \
    "pydantic-settings>=2.15,<3" \
    "PyJWT>=2.13,<3" \
    "redis>=5,<6" \
    "langgraph>=0.2,<1" \
    && chmod +x /repo/backend/docker-entrypoint.sh

EXPOSE 8000
CMD ["/repo/backend/docker-entrypoint.sh"]
