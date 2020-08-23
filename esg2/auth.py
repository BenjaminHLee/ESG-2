import functools
import os
import csv
import decimal

import pandas as pd

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import abort

from wtforms import (
    Form, SelectField, DecimalField, StringField, PasswordField, validators
)

from esg2 import CONFIG_FOLDER
from esg2.db import get_db
from esg2.utilities import get_portfolio_names_list

bp = Blueprint('auth', __name__, url_prefix='')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()
        if g.user is None:
            g.player = None
        elif (g.user['usertype'] == "player"):
            g.player = get_db().execute(
                'SELECT * FROM player WHERE player_id = ?', (user_id,)
            ).fetchone()
        else:
            g.player = None

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view

def admin_login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        elif (g.user['usertype'] == "admin"):
            return view(**kwargs)
        else:
            abort(403)
    return wrapped_view
class RegistrationForm(Form):
    # New user registration form template
    username = StringField('Username', [
        validators.InputRequired(message='Username must be between 1 and 16 characters long.'),
        validators.Length(min=1, max=16, message='Username must be between 1 and 16 characters long.')
    ])
    password = PasswordField('Password', [
        validators.InputRequired(),
        validators.EqualTo('confirm', message='Passwords must match.')
    ])
    confirm = PasswordField('Confirm Password', [validators.InputRequired()])
    portfolio = SelectField('Portfolio', [validators.InputRequired()], coerce=str)
    starting_money = DecimalField('Initial Balance', [validators.InputRequired(message='Initial balance must be a decimal value (e.g. -2020.92).')], places=2, rounding=decimal.ROUND_UP)

@bp.route('/register', methods=('GET', 'POST'))
@admin_login_required
def register():
    form = RegistrationForm(request.form)
    # dynamically set portfolio dropdown selection options based off of unique values in portfolios.csv
    portfolios_df = pd.read_csv(os.path.join(CONFIG_FOLDER, 'portfolios.csv'))
    form.portfolio.choices = [(portfolio, portfolio) for portfolio in get_portfolio_names_list()]
    
    if request.method == 'POST' and form.validate():
        username = form.username.data
        password = form.password.data
        portfolio = form.portfolio.data
        portfolio_id = int(portfolios_df.loc[portfolios_df['portfolio_name'] == portfolio, 'portfolio_id'].iloc[0])
        starting_money = form.starting_money.data
        db = get_db()
        error = None

        if db.execute(
            'SELECT id FROM user WHERE username = ?', (username,)
        ).fetchone() is not None:
            error = 'User {} is already registered.'.format(username)
        elif db.execute(
            'SELECT player_id FROM player WHERE portfolio = ?', (portfolio,)
        ).fetchone() is not None:
            error = 'Portfolio "{}" is already assigned to another player.'.format(portfolio)

        try:
            round(starting_money, 2)
        except:
            error = 'Invalid initial balance value; perhaps the number is too large?'

        if error is None:
            db.execute(
                'INSERT INTO user (username, password, usertype) VALUES (?, ?, ?)',
                (username, generate_password_hash(password), "player")
            )
            db.execute(
                'INSERT INTO player (player_id, portfolio, portfolio_id, starting_money) VALUES (last_insert_rowid(), ?, ?, ?)',
                (portfolio, portfolio_id, str(round(starting_money, 2)))
            )
            db.commit()
            return redirect(url_for('admin.config'))

        flash(error)
    elif request.method == 'POST' and not form.validate():
        for field, error_messages in form.errors.items():
            for error in error_messages:
                flash(error)

    return render_template('auth/register.html', form=form)

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username or password.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect username or password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('scoreboard.scoreboard'))

        flash(error)

    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

