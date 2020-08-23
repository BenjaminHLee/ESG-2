import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


@click.command('add-admin')
@click.argument('username')
@click.argument('password')
@with_appcontext
def add_admin_command(username, password):
    db = get_db()

    if db.execute(
        'SELECT id FROM user WHERE username = ?', (username,)
    ).fetchone() is not None:
        click.echo(f"User {username} is already registered")
    else:
        db.execute(
            'INSERT INTO user (username, password, usertype) VALUES (?, ?, ?)',
            (username, generate_password_hash(password), "admin")
        )
        db.commit()
        click.echo(f"Added administrator account \"{username}\"")

@click.command('set-password')
@click.argument('username')
@click.argument('password')
@with_appcontext
def set_password_command(username, password):
    db = get_db()

    if db.execute(
        'SELECT id FROM user WHERE username = ?', (username,)
    ).fetchone() is  None:
        click.echo(f"User {username} not found")
    else:
        db.execute(
            'UPDATE user'
            ' SET password = ?'
            ' WHERE username = ?',
            (generate_password_hash(password), username)
        )
        db.commit()
        click.echo(f"Reset password for account \"{username}\"")


@click.command('init-db')
@with_appcontext
def init_db_command():
    # Clear the existing data and create new tables
    init_db()
    click.echo("Initialized database.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(add_admin_command)
    app.cli.add_command(set_password_command)
    app.cli.add_command(init_db_command)
