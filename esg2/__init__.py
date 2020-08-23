import os
from os.path import dirname, realpath, join

from flask import Flask, render_template

CSV_FOLDER = os.path.join(dirname(realpath(__file__)), 'csv')
CONFIG_FOLDER = os.path.join(CSV_FOLDER, 'config')
HOURLY_FOLDER = os.path.join(CSV_FOLDER, 'hourly')

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'esg2.sqlite'),
        UPLOAD_FOLDER=CSV_FOLDER,
        SEND_FILE_MAX_AGE_DEFAULT=0,
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # prevent caching
    @app.after_request
    def add_header(r):
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        r.headers["Pragma"] = "no-cache"
        r.headers["Expires"] = "0"
        return r

    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import admin
    app.register_blueprint(admin.bp)
    
    from . import error
    app.register_blueprint(error.bp)

    from . import player
    app.register_blueprint(player.bp)

    from . import scoreboard
    app.register_blueprint(scoreboard.bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.context_processor
    def table_processor():
        def isnan(x):
            import math
            try:
                return math.isnan(x)
            except:
                return False
        return dict(isnan=isnan)


    return app
