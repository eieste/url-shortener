import logging
import threading
import uuid
from datetime import datetime
from flask import send_file

from flask import Flask, session, request, render_template, redirect
from urlshortener.contrib.db import DB
from urlshortener.config import settings
from urlshortener.contrib.generator import get_random_string, get_qrcode

log = logging.getLogger()

dblock = threading.Lock()

app = Flask(__name__)
app.secret_key = settings.SECRET_KEY


# create the Flask app

@app.route('/')
def home():
    return render_template('index.html', URLSHORTNER_URL=settings.DOMAIN)



@app.route('/api/qrcode/<slug>', methods=['GET'])
def show_qrcode(slug):
        return send_file(
            get_qrcode(settings.DOMAIN + "/" + slug),
            mimetype='image/jpeg',
            as_attachment=False,
            download_name='%s.jpg' % pid)



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
        }, 400

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
                    }, 400
                elif not x:
                    log.info(f"{target_slug} is unique => {target_url}")
                    break
                else:
                    log.info("Retry to generate random string. Attempt: ",
                             3 - _)
                    target_slug = get_random_string(5 + _)

            item = db.register(target_slug, target_url)

        dblock.release()

        item["qrcode"] = get_qrcode(settings.DOMAIN + "/" + item.get("target_slug"))
        item["short_url"] = settings.DOMAIN + "/" + item.get("target_slug")
        return item
    else:
        dblock.release()
        return {
            "state": "err",
            "msg": "db_timeout"
        }, 400

@app.route('/<slug>')
def short_redirect(slug):
    if slug is not None:

        if "urlshortner_uid" not in session:
            session["urlshortner_uid"] = uuid.uuid4().hex

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
        return "Invalid Short link", 400


def start(*args, **kwargs):
    # run app in debug mode on port 5000
    app.run(debug=settings.FLASK_DEBUG, port=8000)


if __name__ == '__main__':
    start()
