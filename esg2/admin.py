import os
import decimal

import pandas as pd

from flask import (
    Blueprint, flash, g, redirect, render_template, request, send_from_directory, session, url_for
)

from esg2 import CSV_FOLDER, CONFIG_FOLDER
from esg2.db import get_db
from esg2.auth import admin_login_required
from esg2.utilities import bid_base_r_h_to_header, get_game_setting, get_portfolio_names_list, first_incomplete_summary_row
from . import engine

bp = Blueprint('admin', __name__, url_prefix='')


ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/admin/config', methods=['GET'])
@admin_login_required
def config():
    db = get_db()

    initialized = False

    # Check if game has been initialized (if `bids` table exists)
    if db.execute(
        '''SELECT name FROM sqlite_master WHERE type='table' AND name='bids' '''
    ).fetchone() is not None:
        initialized = True

    # dynamically set portfolio dropdown selection options based off of unique values in portfolios.csv
    portfolio_choices = [(portfolio, portfolio) for portfolio in get_portfolio_names_list()]

    players = db.execute(
        'SELECT username, player_id, portfolio, portfolio_id, starting_money'
        ' FROM player p JOIN user u ON p.player_id = u.id'
        ' ORDER BY portfolio_id'
    ).fetchall()
    return render_template('admin/config.html', initialized=initialized, players=players, portfolio_choices=portfolio_choices)

@bp.route('/admin/config/upload', methods=['GET', 'POST'])
@admin_login_required
def config_upload():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        elif not allowed_file(file.filename):
            flash('File is not a .csv type')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = request.form['filename'] + '.csv'
            file.save(os.path.join(CONFIG_FOLDER, filename))
            flash('File uploaded successfully')
            return redirect(url_for('admin.config_upload'))
    return render_template('admin/config_upload.html')

@bp.route('/csv/config/<filename>')
def uploaded_config_file(filename):
    return send_from_directory(CONFIG_FOLDER, filename)

@bp.route('/admin/delete-user', methods=['POST'])
@admin_login_required
def delete_user():
    db = get_db()
    players = db.execute(
        # 'SELECT player_id FROM player'
        'SELECT player_id'
        ' FROM player p JOIN user u ON p.player_id = u.id'
        ' ORDER BY player_id'
    ).fetchall()
    for player in players:
        if str(player['player_id']) in request.form:
            db.execute(
                'DELETE FROM player'
                ' WHERE player_id = ?', (player['player_id'],) 
            )
            db.execute(
                'DELETE FROM user'
                ' WHERE id = ?', (player['player_id'],) 
            )
            db.commit()
    return redirect(url_for('admin.config'))

@bp.route('/admin/set-starting-money', methods=['POST'])
@admin_login_required
def set_starting_money():
    starting_money = request.form['starting-money']
    try:
        starting_money = round(decimal.Decimal(starting_money), 2)
    except decimal.InvalidOperation:
        flash("Invalid initial balance value; perhaps the number is too large?")
        return redirect(url_for('admin.config'))
    except:
        flash("Initial balance must be a decimal value (e.g. -2020.92).")
        return redirect(url_for('admin.config'))
        # isn't it weird that flash and then redirecting works?

    db = get_db()
    players = db.execute(
        # 'SELECT player_id FROM player'
        'SELECT player_id, starting_money'
        ' FROM player'
        ' ORDER BY player_id'
    ).fetchall()
    for player in players:
        if str(player['player_id']) in request.form:
            db.execute(
                'UPDATE player'
                ' SET starting_money = ?'
                ' WHERE player_id = ?', (str(round(starting_money, 2)), player['player_id'],) 
            )
            db.commit()
    return redirect(url_for('admin.config'))

@bp.route('/admin/set-portfolio', methods=['POST'])
@admin_login_required
def set_portfolio():
    portfolio = request.form['portfolio']

    portfolios_df = pd.read_csv(os.path.join(CONFIG_FOLDER, 'portfolios.csv'))
    portfolio_id = int(portfolios_df.loc[portfolios_df['portfolio_name'] == portfolio, 'portfolio_id'].iloc[0])

    db = get_db()
    players = db.execute(
        # 'SELECT player_id FROM player'
        'SELECT player_id, portfolio, portfolio_id'
        ' FROM player'
        ' ORDER BY player_id'
    ).fetchall()
    for player in players:
        if str(player['player_id']) in request.form:

            if db.execute(
                'SELECT player_id FROM player WHERE portfolio = ?', (portfolio,)
            ).fetchone() is not None:
                flash('Portfolio "{}" is already assigned to a player.'.format(portfolio))
                return redirect(url_for('admin.config'))

            db.execute(
                'UPDATE player'
                ' SET portfolio = ?, portfolio_id = ?'
                ' WHERE player_id = ?', (portfolio, portfolio_id, player['player_id'],) 
            )
            db.commit()
    return redirect(url_for('admin.config'))

@bp.route('/admin/start-game', methods=['POST'])
@admin_login_required
def start_game():
    # Initialize game
    # Save player info (from players table) into players.csv
    db = get_db()
    players_df = pd.read_sql_query(
        'SELECT username, portfolio, portfolio_id, starting_money'
        ' FROM player p JOIN user u ON p.player_id = u.id'
        ' ORDER BY portfolio_id',
        db
    )
    players_df = players_df.sort_values(by=['portfolio_id'], ascending=[True])
    players_df.to_csv(os.path.join(CSV_FOLDER, 'players.csv'), index=False)

    # Create summary, hourly, bids sheets
    schedule_df = pd.read_csv(os.path.join(CONFIG_FOLDER, 'schedule.csv'))
    schedule_df = schedule_df.sort_values(by=['round', 'hour'], ascending=[True, True])
    portfolios_df = pd.read_csv(os.path.join(CONFIG_FOLDER, 'portfolios.csv'))
    engine.create_summary_sheet(schedule_df, players_df)
    engine.create_hourly_sheets(schedule_df, portfolios_df)
    engine.create_bids_sheet(schedule_df, portfolios_df)

    # Create bids table
    bids_df = pd.read_csv(os.path.join(CSV_FOLDER, 'bids.csv'))
    bids_df.to_sql('bids', db, index=False, if_exists='replace')
    db.commit()

    flash("Game initialized!")
    return redirect(url_for('admin.config'))

@bp.route('/admin/dashboard', methods=['GET', 'POST'])
@admin_login_required
def admin_dashboard():

    if request.method == 'POST':
        schedule_df = pd.read_csv(os.path.join(CONFIG_FOLDER, 'schedule.csv'))
        portfolios_df = pd.read_csv(os.path.join(CONFIG_FOLDER, 'portfolios.csv'))
        players_df = pd.read_csv(os.path.join(CSV_FOLDER, 'players.csv'))
        summary_df = pd.read_csv(os.path.join(CSV_FOLDER, 'summary.csv'))

        schedule_df = schedule_df.sort_values(by=['round', 'hour'], ascending=[True, True])
        players_df = players_df.sort_values(by=['portfolio_id'], ascending=[True])

        pending_bids_df = get_pending_bids().sort_values(['unit_id'], ascending=True)

        r_h = request.form['hour-select']
        r, h = r_h.split('/')

        commit_bids(pending_bids_df, r, h)

        r = int(r)
        h = int(h)
        bids_df = pd.read_csv(os.path.join(CSV_FOLDER, 'bids.csv'))

        if get_game_setting('adjustment') == 'per portfolio' or get_game_setting('adjustment') == 'per unit':
            adjustment = True
        else:
            adjustment = False

        engine.run_hour(r, h, bids_df, schedule_df, portfolios_df, adjustment)
        engine.update_summary(r, h, summary_df, players_df)

        flash(f"Ran hour {r}/{h}.")
        return redirect(url_for('admin.admin_dashboard'))

    db = get_db()
    if db.execute(
        '''SELECT name FROM sqlite_master WHERE type='table' AND name='bids' '''
    ).fetchone() is None:
        return render_template('/admin/dashboard.html', initialized=False)

    summary_df = pd.read_csv(os.path.join(CSV_FOLDER, 'summary.csv'))
    bids_df = get_pending_bids().sort_values(['unit_id'], ascending=True)
    bids_df = bids_df.where(bids_df.notnull(), None)
    unit_names_df = bids_df[['portfolio_name', 'unit_name', 'unit_id']]
    # ASSUMING NO ADJUSTMENT BIDS — TODO: ADD SUPPORT FOR BY PORTFOLIO/BY PLANT ADJUST
    adjustment = get_game_setting('adjustment')
    base_bids_df = bids_df.filter(regex=("bid_base_.*"))
    name_base_bids_df = pd.concat([unit_names_df, base_bids_df], axis=1, sort=False)
    pretty_headers = [bid_base_r_h_to_header(s) for s in base_bids_df.columns]

    next_r_h = first_incomplete_summary_row(summary_df)

    kwargs = {
        'initialized':True,
        'bids':name_base_bids_df,
        'next_r_h':next_r_h,
        'adjustment':adjustment,
        'pretty_headers':pretty_headers
    }
    return render_template('admin/dashboard.html', **kwargs)

def get_pending_bids():
    """Returns a Pandas DataFrame that represents the bids table (not the committed bids.csv)"""
    db = get_db()
    bids_df = pd.read_sql_query('SELECT * FROM bids', db)
    return bids_df

def commit_bids(pending_bids_df, r, h):
    """Writes bids from the dataframe pending_bids_df corresponding to the particular round/hour
    to the bids.csv file"""
    pending_bids_df = pending_bids_df.reset_index(drop=True)
    selected_bids_columns = pending_bids_df.filter(regex=(".*_" + r + "_" + h))
    selected_bids_columns = selected_bids_columns.fillna(get_game_setting('max bid')) # HACK: Figure out better nan-bid handling
    selected_column_headers = selected_bids_columns.columns
    bids_csv_df = pd.read_csv(os.path.join(CSV_FOLDER, 'bids.csv'))
    for column in selected_column_headers:
        bids_csv_df[column] = selected_bids_columns[column]
    bids_csv_df.to_csv(os.path.join(CSV_FOLDER, 'bids.csv'), index=False)

