from urlshortener.config import settings
import yaml
from yaml import SafeLoader
import logging


log = logging.getLogger("urlshortener")
logging.basicConfig(level=logging.DEBUG)


class DB:

    def __init__(self):
        self.data = {"urls": []}

        if not settings.DB_FILE.exists():
            log.debug(settings.DB_FILE.absolute())
            settings.DB_FILE.touch()

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
        if not settings.DB_FILE.exists():
            settings.DB_FILE.touch()
        with settings.DB_FILE.open("r") as fobj:
            data = yaml.load(fobj, Loader=SafeLoader)
            if data is not None:
                self.data = data
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with settings.DB_FILE.open("w") as fobj:
            yaml.dump(self.data, fobj, default_flow_style=False)
