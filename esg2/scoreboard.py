# SCOREBOARD
# Communicates common data: summary.csv info, hourly recaps
# Everything should be publicly sharable

import decimal
import json
import os
import re
from collections import defaultdict

import numpy as np

import pandas as pd

from flask import (
    Blueprint, render_template, request, url_for, send_from_directory, current_app
)

from bokeh.embed import json_item
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.palettes import magma, viridis
from bokeh.plotting import figure
from bokeh.resources import CDN

from esg2 import CSV_FOLDER, HOURLY_FOLDER, CONFIG_FOLDER
from esg2.db import get_db
from esg2.utilities import get_game_setting, last_filled_summary_row, round_hour_names


bp = Blueprint('scoreboard', __name__, url_prefix='')

@bp.route('/scoreboard', methods=['GET', 'POST'])
def scoreboard():

    db = get_db()
    if db.execute(
        '''SELECT name FROM sqlite_master WHERE type='table' AND name='bids' '''
    ).fetchone() is None:
        return render_template('scoreboard.html', initialized=False)

    summary_df = pd.read_csv(os.path.join(CSV_FOLDER, 'summary.csv'))
    schedule_df = pd.read_csv(os.path.join(CONFIG_FOLDER, 'schedule.csv'))

    if request.args.get('sort', ''):
        suffix = request.args.get('sort', '')
        (headings, table) = create_summary_subtable(summary_df, suffix)
        view_names = {"balance": "Balance", "revenue": "Revenue", "cost": "Losses", "profit": "Profit"}
        current_view_name = view_names.get(suffix, '')
        current_r = request.args.get('current_r')
        current_h = request.args.get('current_h')
        current_r_h = (int(current_r), int(current_h))
        kwargs = {
            'initialized':True,
            'chart_r_h':current_r_h,
            'hours':round_hour_names(schedule_df),
            'resources':CDN.render(),
            'summary_table_headers':headings,
            'summary_table':table, 
            'current_summary_view':current_view_name
        }
        return render_template('scoreboard.html', **kwargs)
    elif request.args.get('hour-select', ''):
        r_h_name = request.args.get('hour-select', '')
        r, h = r_h_name.split('/')
        chart_r_h = (int(r), int(h))
        current_view_name = request.args.get('current-summary-view')
        inverse_view_names = {"Balance": "balance", "Revenue": "revenue", "Losses": "cost", "Profit": "profit"}
        current_view = inverse_view_names.get(current_view_name, '')
        (headings, table) = create_summary_subtable(summary_df, current_view)
        kwargs = {
            'initialized':True,
            'chart_r_h':chart_r_h,
            'hours':round_hour_names(schedule_df),
            'resources':CDN.render(),
            'summary_table_headers':headings,
            'summary_table':table,
            'current_summary_view':current_view_name
        }
        return render_template('scoreboard.html', **kwargs)

    default_r_h = last_filled_summary_row(summary_df)
    (balances_heading, balances_table) = create_summary_subtable(summary_df, "balance")

    kwargs = {
        'initialized':True,
        'chart_r_h':default_r_h,
        'hours':round_hour_names(schedule_df),
        'resources':CDN.render(),
        'summary_table_headers':balances_heading,
        'summary_table':balances_table, 
        'current_summary_view':'Balance'
    }
    return render_template('scoreboard.html', **kwargs)

def create_summary_subtable(summary_df, header_suffix):
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

@bp.route('/chart/hourly/r<r>h<h>')
def hourly_chart(r, h):
    try:
        p = create_hour_chart(int(r), int(h))
        return json.dumps(json_item(p, "hourly-chart"))
    except(FileNotFoundError):
        return "Bad request"

def create_hour_chart(r, h):
    """Create a Bokeh chart of the supply and demand curves given a round and hour"""

    colors = ['#57BCCD', '#3976AF', '#F08636', '#529D3F', '#C63A33', '#8D6AB8', '#85594E', '#D57EBF']
    # colors = magma(7)
    # colors = viridis(7)

    # Read corresponding hourly csv (assume it exists)
    hourly_df = pd.read_csv(os.path.join(HOURLY_FOLDER, "round_" + str(r) + "_hour_" + str(h) + ".csv"))
    # Sort by base_bid, secondary sort by unit_id
    hourly_df = hourly_df.sort_values(by=['bid_base', 'unit_id'], ascending=[True, True])

    supply_curve_data = defaultdict(list)

    mwh_running_total = 0
    for _, row in hourly_df.iterrows():
        x_left = mwh_running_total
        x_right = x_left + float(row['unit_capacity'])
        y = float(row['bid_base'])
        supply_curve_data['xs'].append([x_left, x_right])
        supply_curve_data['ys'].append([y, y])
        supply_curve_data['portfolio_name'].append(row['portfolio_name'])
        supply_curve_data['unit_name'].append(row['unit_name'])
        supply_curve_data['bid'].append("{:0.2f}".format(y))
        supply_curve_data['color'].append(colors[int(row['portfolio_id']) - 1 % len(colors)])
        mwh_running_total += float(row['unit_capacity'])

    cds = ColumnDataSource(supply_curve_data)

    chart_title = "Day " + str(r) + " hour " + str(h) + " supply and demand"

    min_bid = float(get_game_setting('min bid'))
    max_bid = float(get_game_setting('max bid'))
    bid_range = max_bid - min_bid
    y_min = min_bid - bid_range * 0.1
    y_max = max_bid + bid_range * 0.1

    chart = figure(title=chart_title, x_axis_label='MWh', y_axis_label='Price ($/MWh)', y_range=[y_min, y_max],
                   sizing_mode='stretch_width', height=300, title_location='above')

    supply_curve = chart.multi_line(xs='xs', ys='ys', line_width=4, line_color='color', line_alpha=0.6,
                                    hover_line_color='color', hover_line_alpha=1.0, source=cds)

    chart.add_tools(HoverTool(renderers=[supply_curve], show_arrow=False, line_policy='interp',
                              point_policy='follow_mouse', attachment='above', tooltips=[
                                  ('Portfolio', '@portfolio_name'),
                                  ('Unit', '@unit_name'),
                                  ('$/MWh', '@bid')
                              ]))

    # read schedule.csv (assume it exists)
    schedule_df = pd.read_csv(os.path.join(CONFIG_FOLDER, 'schedule.csv'))

    current_row = schedule_df[schedule_df['round'] == r][schedule_df['hour'] == h]
    net = current_row.iloc[0]['net']
    slope = current_row.iloc[0]['slope']

    if slope == 0:
        def demand_y_to_x(y):
            return net
    else:
        def demand_y_to_x(y):
            return (float(y) / float(slope)) + net

    demand_y_min = min_bid - bid_range * 0.05
    demand_y_max = max_bid + bid_range * 0.05

    demand_ys = [demand_y_min, demand_y_max]
    demand_xs = [demand_y_to_x(demand_y_min), demand_y_to_x(demand_y_max)]

    chart.line(x=demand_xs, y=demand_ys, line_width=4, color='black')

    (intercept_x, intercept_y) = get_supply_demand_intercept(hourly_df, schedule_df, r, h)

    intercept = {'x': [float("{:0.2f}".format(intercept_x))], 'y': [float("{:0.2f}".format(intercept_y))]}

    intercept_circle = chart.circle('x', 'y', color='black', size=6, source=intercept)

    chart.add_tools(HoverTool(renderers=[intercept_circle], point_policy='snap_to_data', attachment='below',
                              tooltips=[("", "(@x{(0.00)} MWh, @y{(0.00)} $/MWh)"),]))


    chart.toolbar.active_drag = None

    return chart
    
def get_supply_demand_intercept(hourly_df, schedule_df, r, h):
    """Returns the intersection of the supply and demand curves in the form (quantity, price)."""
    
    current_row = schedule_df[schedule_df['round'] == r][schedule_df['hour'] == h]
    net = current_row.iloc[0]['net']
    slope = current_row.iloc[0]['slope']

    if (slope == 0): # NOTE: 0 slope is interpreted as perfect inelasticity, not perfect elasticity
        def demand_fn(quantity):
            if (quantity < net): 
                # quantity is insufficient, will pay any price (remember inelasticity!)
                return np.inf # CONCERNING
            else: 
                # quantity is sufficient, will pay nothing
                return -np.inf # WORRYING
    else:
        def demand_fn(quantity):
            return (slope * (quantity - net)) # price-giving function in [slope * (x - x_intercept)] form

    running_production = 0
    intercept_price = 0

    for _, unit in hourly_df.iterrows(): # HACK this is an antipattern
        unit_capacity = unit['unit_capacity']
        bid = unit['bid_base'] 

        if (demand_fn(running_production) < bid):
            # unit's bid price is too high, market is not interested
            return (running_production, intercept_price)
        else:
            # update uniform price (recall that list of bids is sorted)
            intercept_price = bid
            # check if unit produces entire capacity or if demand curve intersects production step
            if (demand_fn(running_production + unit_capacity) > bid):
                # step fits entirely below curve
                running_production += unit_capacity
            else:
                # step intersects
                # with nonzero slope:
                intersect_quantity = 0
                if (slope != 0):
                    # algebra gives quantity produced = bid/demand_slope + demand_base
                    intersect_quantity = bid/slope + net
                else:
                    # vertical line
                    intersect_quantity = net
                unit_production = intersect_quantity - running_production
                running_production += unit_production

    return (running_production, intercept_price)
