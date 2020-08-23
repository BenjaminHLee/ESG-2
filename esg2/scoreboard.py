# SCOREBOARD
# Communicates common data: summary.csv info, hourly recaps
# Everything should be publicly sharable

import re

import pandas as pd

from flask import (
    Blueprint, render_template, request, url_for, send_from_directory
)

from esg2 import CSV_FOLDER, HOURLY_FOLDER
from esg2.db import get_db


bp = Blueprint('scoreboard', __name__, url_prefix='')

@bp.route('/scoreboard', methods=['GET', 'POST'])
def scoreboard():
    if request.args.get('sort', ''):
        suffix = request.args.get('sort', '')
        (headings, table) = create_summary_subtable(suffix)
        view_names = {"balance": "Balance", "revenue": "Revenue", "cost": "Losses", "profit": "Profit"}
        current_view_name = view_names.get(suffix, "")
        return render_template('scoreboard.html', initialized=True, summary_table_headers=headings, summary_table=table, current_summary_view=current_view_name)

    db = get_db()
    if db.execute(
        '''SELECT name FROM sqlite_master WHERE type='table' AND name='bids' '''
    ).fetchone() is None:
        return render_template('scoreboard.html', initialized=False)


    (balances_heading, balances_table) = create_summary_subtable("balance")
    return render_template('scoreboard.html', initialized=True, summary_table_headers=balances_heading, summary_table=balances_table, current_summary_view="Balance")

def create_summary_subtable(header_suffix):
    summary_df = pd.read_csv(CSV_FOLDER + '/summary.csv')

    # Information to display: round, hour, [header_suffix (balance/profit/cost/revenue)] for each player
    r_h = summary_df[['round', 'hour']]
    selected_columns = summary_df.filter(regex=(".*_" + header_suffix))
    r_h_selected = pd.concat([r_h, selected_columns], axis=1, sort=False)

    # Headers: Day, Hour, player name\nPortfolio
    selected_headers = list(selected_columns.columns)
    extract_id = lambda header: int(re.search('player_(.*)_' + header_suffix, header).group(1))
    ids = list(map(extract_id, selected_headers))    

    table_headers = ["Day", "Hour"] + [id_to_header(i) for i in ids]
    r_h_selected.columns = table_headers

    r_h_selected.insert(0, "Day/Hour", r_h_selected.apply(lambda row: r_h_column_to_linked_html(row), axis=1))
    r_h_selected = r_h_selected.drop(columns=["Day", "Hour"])

    return (list(r_h_selected.columns), r_h_selected.values.tolist())

def id_to_header(portfolio_id):
    db = get_db()
    try:
        (username, portfolio) = db.execute(
            'SELECT username, portfolio'
            ' FROM player p JOIN user u ON p.player_id = u.id'
            ' WHERE p.portfolio_id = ?', (portfolio_id,)
        ).fetchone()
        return username + '<br><span style="font-weight: normal;">' + portfolio + '</span>'
    except:
        return portfolio_id

def r_h_column_to_linked_html(row):
    r = str(int(row["Day"]))
    h = str(int(row["Hour"]))
    # HACK: This isn't a dynamic link. Ideally there should be a way to do this with url_for
    a_element = '<a href="' + url_for('scoreboard.hourly_file', r=r, h=h) + '">'
    html = a_element + r + '/' + h + '</a>'
    return html
            
@bp.route('/csv/<filename>')
def engine_file(filename):
    return send_from_directory(CSV_FOLDER, filename)

@bp.route('/csv/hourly/r<r>h<h>.csv')
def hourly_file(r, h):
    return send_from_directory(HOURLY_FOLDER, "round_" + r + "_hour_" + h + ".csv")