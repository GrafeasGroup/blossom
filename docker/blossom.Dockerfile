FROM python:3-slim as base

# Ensures output from python is sent straight to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

# It's a container and we know pip should be upgraded. Shaddup
ENV PIP_DISABLE_PIP_VERSION_CHECK 1

# hadolint ignore=DL3013,DL3042
RUN pip install --upgrade pip

WORKDIR /app

FROM base as builder

# hadolint ignore=DL3013,DL3042
RUN pip install poetry

COPY ./pyproject.toml /app
COPY ./poetry.lock /app

RUN poetry export --format=requirements.txt --output=requirements.txt

FROM base as runtime

ENV PORT 8080
EXPOSE 8080

COPY . /app

COPY ./docker/blossom-entrypoint.sh /docker-entrypoint.sh

COPY --from=builder /blossom/app/requirements.txt /app/requirements.txt

# hadolint ignore=DL3013,DL3042
RUN pip install -r requirements.txt

ENTRYPOINT ["bash", "/docker-entrypoint.sh"]
CMD ["runserver"]
