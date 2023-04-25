import base64
import logging
import os
import pathlib
import random
import string
import threading
import uuid
from datetime import datetime
from io import BytesIO

import qrcode
import yaml
from flask import Flask, session, request, render_template, redirect
from yaml.loader import SafeLoader

log = logging.getLogger()
OWN_URL = os.environ.get("URLSHORTNER_URL", "https://short.flatos")

FILE_DB = pathlib.Path("urls.yaml")
dblock = threading.Lock()

app = Flask(__name__)
app.secret_key = os.environ.get("URLSHORTNER_SECRET_KEY")


class DB:

    def __init__(self):
        self.data = {"urls": []}

        if not FILE_DB.exists():
            FILE_DB.touch()

    def find(self, **kwargs):

        for item in self.data.get("urls", []):
            found = len(kwargs)
            for key, value in kwargs.items():
                if item.get(key) == value:
                    found = found - 1
            if found == 0:
                return item
        return False

    def add_statistic(self, target_slug, statistic):
        for urlitem in self.data.get("urls", []):
            if urlitem.get("target_slug") == target_slug:
                if "statistics" not in urlitem:
                    urlitem["statistics"] = []
                urlitem["statistics"].append(statistic)

    def register(self, target_slug, target_url):
        item = {
            "target_url": target_url,
            "target_slug": target_slug
        }
        self.data["urls"].append(item)
        return item

    def __enter__(self):
        with FILE_DB.open("r") as fobj:
            data = yaml.load(fobj, Loader=SafeLoader)
            if data is not None:
                self.data = data
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with FILE_DB.open("w") as fobj:
            yaml.dump(self.data, fobj, default_flow_style=False)


def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase + string.digits
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


# create the Flask app

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/short/', methods=['POST'])
def create_short():
    content = request.get_json(silent=True)

    initial_target_slug = content.get("target_slug", "")
    if initial_target_slug.strip() == "":
        initial_target_slug = None

    target_slug = initial_target_slug or get_random_string(5)
    target_url = content.get("target_url")

    if target_url is None:
        return {
            "state": "err",
            "msg": "no_target_url"
        }

    if dblock.acquire(blocking=True, timeout=5):
        with DB() as db:
            for _ in range(3):
                x = db.find(target_slug=target_slug)

                if x and initial_target_slug is not None:
                    dblock.release()
                    log.warning(f"{target_slug} is already in use")
                    return {
                        "state": "err",
                        "msg": "slug_already_exists"
                    }
                elif not x:
                    log.info(f"{target_slug} is unique => {target_url}")
                    break
                else:
                    log.info("Retry to generate random string. Attempt: ",
                             3 - _)
                    target_slug = get_random_string(5 + _)

            item = db.register(target_slug, target_url)
        dblock.release()

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(OWN_URL + "/" + item.get("target_slug"))
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue())
        item["qrcode"] = img_str.decode("utf-8")
        item["short_url"] = OWN_URL + "/" + item.get("target_slug")
        return item
    else:
        dblock.release()
        return {
            "state": "err",
            "msg": "db_timeout"
        }


@app.route('/<slug>')
def short_redirect(slug):
    if slug is not None:

        if "urlshortner_uid" not in session:
            session["urlshortner_uid"] = uuid.uuid4().hex()

        if dblock.acquire(blocking=True, timeout=5):
            with DB() as db:
                item = db.find(target_slug=slug)
                db.add_statistic(target_slug=slug, statistic={
                    "timestamp": datetime.now().isoformat(),
                    "uid": session["urlshortner_uid"],
                    "ip": request.remote_addr,
                    "agent": request.user_agent.string,
                    "platform": request.user_agent.platform,
                    "browser": request.user_agent.browser,
                    "version": request.user_agent.version,
                    "language": request.user_agent.language,
                })
            dblock.release()
        if item:
            return redirect(item.get("target_url", ""))
        return "Invalid Short link"


def start(*args, **kwargs):
    # run app in debug mode on port 5000
    app.run(debug=True, port=5000)


if __name__ == '__main__':
    start()
