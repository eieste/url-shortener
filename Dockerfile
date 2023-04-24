FROM python:3.10

RUN pip3 install pillow \
                 flask \
                 pyyaml \
                 qrcode \
                 uwsgi

COPY ./ /app/
COPY ./entrypoint.bash /

RUN cd /app/; pip3 install .

RUN useradd -ms /bin/bash app; \
    chown -R app:app /app

USER app

WORKDIR /app

RUN cd /app/; pip3 install .

ENTRYPOINT /entrypoint.bash

