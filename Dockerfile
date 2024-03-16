FROM python:3.10

RUN pip3 install pillow \
                 flask \
                 pyyaml \
                 qrcode \
                 uwsgi

COPY ./src/ /app/
COPY ./uwsgi.yaml /
COPY ./entrypoint.bash /

RUN cd /app/; touch __init__.py

RUN useradd -ms /bin/bash app; \
    chown -R app:app /app

USER app

WORKDIR /app

RUN cd /app/

ENTRYPOINT /entrypoint.bash

