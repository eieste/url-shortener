#!/bin/bash

cd /app/src/urlshortener/



if [ "$FLASK_DEBUG" == "true" ]
then
    python3 main.py 
else
    uwsgi --yaml /app/uwsgi.yaml
fi



