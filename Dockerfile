FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
  apt-get install -y \
  python3 \
  python3-pip \
  python3-venv \
  nano \
  && rm -rf /var/lib/apt/lists/*

    
ENV TZ="America/Chicago"

WORKDIR /podcast.py

COPY . .

RUN python3 -m venv .venv && \
  .venv/bin/pip install --no-cache-dir -r requirements.txt

RUN ln -sf /podcast.py/docker-sh/podcast.sh /usr/local/bin/podcast.py && \
  chmod +x /podcast.py/docker-sh/*.sh

RUN touch podcast.log

CMD tail -f /podcast.py/podcast.log