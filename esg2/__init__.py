import os, errno
from os.path import dirname, realpath, join
from shutil import copy

from flask import Flask, render_template

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'esg2.sqlite'),
        UPLOAD_FOLDER=os.path.join(app.instance_path, 'csv'),
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
        # set up csv subfolders
        os.makedirs(os.path.join(app.instance_path, 'csv', 'config'))
        os.makedirs(os.path.join(app.instance_path, 'csv', 'hourly'))
    except OSError as e:
        # directories already exist?
        if e.errno != errno.EEXIST:
            raise

    # Copy default game config files
    copy(os.path.join(dirname(realpath(__file__)), 'default_config', 'game_settings.csv'), 
         os.path.join(app.instance_path, 'csv', 'config', 'game_settings.csv'))
    copy(os.path.join(dirname(realpath(__file__)), 'default_config', 'portfolios.csv'), 
         os.path.join(app.instance_path, 'csv', 'config', 'portfolios.csv'))
    copy(os.path.join(dirname(realpath(__file__)), 'default_config', 'schedule.csv'), 
         os.path.join(app.instance_path, 'csv', 'config', 'schedule.csv'))

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
