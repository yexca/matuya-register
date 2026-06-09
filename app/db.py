def init_app(app):
    app.teardown_appcontext(close_db)


def close_db(exc=None):
    return None
