FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
    git \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    cron \
    nano \
    && rm -rf /var/lib/apt/lists/*

COPY . /podcast.py

ENV TZ="America/Chicago"

WORKDIR /podcast.py

RUN touch podcast.log

RUN sh docker-sh/install.sh

CMD service cron start && tail -f /podcast.py/podcast.log