import logging


def init_logging(app):
    logging.basicConfig(level=logging.INFO)
    return app
