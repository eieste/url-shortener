#!/bin/bash

cd /app/



if [ "$FLASK_DEBUG" == "true" ]
then
    cd /app/;
    ls -lah;
    python3 -m urlshortener main.py
else
    uwsgi --yaml /uwsgi.yaml
fi



