import decimal

import pandas as pd

from flask import (
    Blueprint, flash, g, redirect, render_template, request, send_from_directory, url_for
)

from esg2 import CSV_FOLDER, CONFIG_FOLDER
from esg2.db import get_db
from esg2.auth import login_required
from esg2.utilities import bid_base_r_h_to_header, get_game_setting

bp = Blueprint('player', __name__, url_prefix='')


@bp.route('/player/dashboard', methods=['GET', 'POST'])
@login_required
def player_dashboard():
    
    try:
        portfolio_id = g.player['portfolio_id']
    except:
        return render_template('/player/dashboard.html', player_is_valid=False)

    # POST
    if request.method == 'POST':
        bids_df = get_portfolio_bids(portfolio_id)

        if 'place-bids-no-adjust' in request.form:
            # No adjustment bids
            for (key, bid) in request.form.items():
                unit_id, column_header, bid = form_entry_to_tuple(key, bid)
                # Check if bid is a valid decimal; any invalid/empty values will become None
                try:
                    bid = round(decimal.Decimal(bid), 2)
                    bid = min(bid, decimal.Decimal(decimal.Decimal(get_game_setting('max bid'))))
                    bid = max(bid, decimal.Decimal(decimal.Decimal(get_game_setting('min bid'))))
                    # Cast to String because sqlite doesn't like Decimals
                    bid = "{:.2f}".format(bid)
                except:
                    bid = None
                if bid is not None:
                    # Overwrite bid only if form cell is not None 
                    unit = bids_df.loc[bids_df['unit_id'] == int(unit_id)]
                    if unit['portfolio_id'].item() == portfolio_id:
                        bids_df.loc[bids_df['unit_id'] == int(unit_id), column_header] = bid

            # replace instances of nan with None
            bids_df = bids_df.where(bids_df.notnull(), None)

            # Update database: drop rows from `bids` in bids_df, append bids_df
            # Note: this leaves the `bids` table out of order — this gets fixed in the to_csv
            # stage of admin hour-running
            db = get_db()
            # Create temporary table for comparison purposes
            bids_df.to_sql('temporary_bids', db, if_exists='replace', index=False)
            # Drop any rows in `bids` that match a unit_id in `temporary_bids`
            db.execute(
                'DELETE FROM bids WHERE unit_id IN (SELECT unit_id FROM temporary_bids)'
            )
            db.commit()
            # Append bids_df
            bids_df.to_sql('bids', db, if_exists='append', index=False)
            
        return redirect(url_for('player.player_dashboard'))

    # GET
    # Check that `bids` table exists
    db = get_db()
    if db.execute(
        '''SELECT name FROM sqlite_master WHERE type='table' AND name='bids' '''
    ).fetchone() is None:
        return render_template('/player/dashboard.html', initialized=False)
    else: 
        bids_df = get_portfolio_bids(portfolio_id)
        # replace instances of nan with None
        bids_df = bids_df.where(bids_df.notnull(), None)
        unit_names_df = bids_df[['unit_name', 'unit_id']]
        # ASSUMING NO ADJUSTMENT BIDS — TODO: ADD SUPPORT FOR BY PORTFOLIO/BY PLANT ADJUST
        adjustment = get_game_setting('adjustment')
        base_bids_df = bids_df.filter(regex=("bid_base_.*"))
        name_base_bids_df = pd.concat([unit_names_df, base_bids_df], axis=1, sort=False)
        pretty_headers = [bid_base_r_h_to_header(s) for s in base_bids_df.columns]

    kwargs = {
        'player_is_valid':True,
        'initialized':True,
        'bids':name_base_bids_df,
        'adjustment':adjustment,
        'pretty_headers':pretty_headers
    }
    return render_template('/player/dashboard.html', **kwargs)

def get_portfolio_bids(portfolio_id):
    """Returns a Pandas DataFrame that represents a subset of the bids table corresponding to the provided portfolio_id"""
    db = get_db()
    bids_df = pd.read_sql_query('SELECT * FROM bids WHERE portfolio_id=' + str(portfolio_id), db)
    return bids_df

def write_portfolio_bids(bids):
    """Takes a Pandas DataFrame representing bids and writes to the bids table"""
    db = get_db()
    for unit_row in bids.itertuples():
        unit_id = unit_row['unit_id']

def form_entry_to_tuple(key, value):
    """Takes in a key of the form "id-{id}-header-{header}" and a value; 
    returns a tuple ({id}, {header}, value) """
    try:
        s = key.split('-')
        i = s[1]
        h = s[3]
        return (i, h, value)
    except:
        # TODO: LOG ERROR
        return ("bad name string", "bad name string", value)

