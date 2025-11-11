FROM python:3.12-slim
# The environment variable ensures that the python output is set straight
# to the terminal with out buffering it first
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

ARG APP_VERSION
ENV APP_VERSION=$APP_VERSION

# locales
RUN apt-get update \
        && apt-get install -y --no-install-recommends locales \
        && sed -i 's/# en_GB.UTF-8 UTF-8/en_GB.UTF-8 UTF-8/' /etc/locale.gen \
        && locale-gen \
        && update-locale LANG en_GB.UTF-8 \
        && rm -rf var/lib/apt/lists/*

ENV LANG=en_GB.UTF-8
ENV LANGUAGE=en_GB:en
ENV LC_ALL=en_GB.UTF-8

COPY requirements.txt /

# build dependencies and pip install
RUN set -ex \
        && BUILD_DEPS=" \
           build-essential \
           curl \
           pkg-config \
           libpq-dev \
        " \
        && apt-get update \
        && apt-get install -y --no-install-recommends $BUILD_DEPS \
        && pip install --no-cache-dir -r /requirements.txt \
        && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false $BUILD_DEPS \
        && rm -rf var/lib/apt/lists/*

RUN mkdir /code

COPY api /code/api
COPY data /code/data
COPY pyproject.toml \
        docker-entrypoint \
        /code/

WORKDIR /code

EXPOSE 8000

ENTRYPOINT ["/code/docker-entrypoint"]

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--workers", "2"]
