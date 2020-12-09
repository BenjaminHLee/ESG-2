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
from bokeh.models import ColumnDataSource, HoverTool, NumeralTickFormatter, FuncTickFormatter
from bokeh.palettes import magma, viridis
from bokeh.plotting import figure
from bokeh.resources import CDN
from bokeh.themes import Theme, built_in_themes

from esg2 import CSV_FOLDER, HOURLY_FOLDER, CONFIG_FOLDER
from esg2.db import get_db
from esg2.utilities import (
    get_game_setting, last_filled_summary_row, round_hour_names, get_portfolio_name_by_id, 
    get_starting_money_by_portfolio_id
)

bp = Blueprint('scoreboard', __name__, url_prefix='')

DARK_THEME_JSON = {
    "attrs": {
        "Figure" : {
            "background_fill_color": "#202010",
            "border_fill_color": "#000000",
            "outline_line_color": "#E0E0E0",
            "outline_line_alpha": 0.25
        },

        "Grid": {
            "grid_line_color": "#E0E0E0",
            "grid_line_alpha": 0.25
        },

        "Axis": {
            "major_tick_line_color": "#A0A0A0",
            "minor_tick_line_color": "#A0A0A0",
            "axis_line_color": "#A0A0A0",

            "major_label_text_color": "#A0A0A0",
            "axis_label_text_color": "#A0A0A0",
        },

        "Title": {
            "text_color": "#A0A0A0",
        }
    }
}

@bp.route('/scoreboard', methods=['GET', 'POST'])
def scoreboard():

    db = get_db()
    if db.execute(
        '''SELECT name FROM sqlite_master WHERE type='table' AND name='bids' '''
    ).fetchone() is None:
        return render_template('scoreboard.html', initialized=False)

    summary_df = pd.read_csv(os.path.join(CSV_FOLDER, 'summary.csv'))
    schedule_df = pd.read_csv(os.path.join(CONFIG_FOLDER, 'schedule.csv'))

    # Default value if request args are not provided
    r, h = last_filled_summary_row(summary_df)
    chart_r_h = f'{r}/{h}'
    (headings, table) = create_summary_subtable(summary_df, "balance")
    current_view_name = 'Balance'
    scroll_to_id = None

    if request.args.get('summary-view', ''):
        current_view_name = request.args.get('summary-view', '')
        suffix_lookup = {"Balance": "balance", "Revenue": "revenue", "Losses": "cost", "Profit": "profit"}
        suffix = suffix_lookup.get(current_view_name, 'balance')
        (headings, table) = create_summary_subtable(summary_df, suffix)

    if request.args.get('hour-r-h', ''):
        chart_r_h = request.args.get('hour-r-h', '')

    # if request.args.get('scroll-to', ''):
    #     scroll_to_id = request.args.get('scroll-to', '')

    kwargs = {
        'initialized':True,
        'chart_r_h':chart_r_h,
        'hours':round_hour_names(schedule_df),
        'resources':CDN.render(),
        'summary_table_headers':headings,
        'summary_table':table, 
        'current_summary_view':current_view_name,
        'scroll_to_id':scroll_to_id
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
        return '<br><span style="font-weight: normal;">' + get_portfolio_name_by_id(portfolio_id)

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
        hourly_df = pd.read_csv(os.path.join(HOURLY_FOLDER, "round_" + str(r) + "_hour_" + str(h) + ".csv"))
        schedule_df = pd.read_csv(os.path.join(CONFIG_FOLDER, 'schedule.csv'))
        if request.args.get('theme') == 'dark': 
            alpha_boost = 0.2
        else: 
            alpha_boost = 0.0
        if get_game_setting('adjustment') == 'per unit' or get_game_setting('adjustment') == 'per portfolio': 
            p = create_hour_chart(schedule_df, hourly_df, int(r), int(h), True, alpha_boost=alpha_boost)
        else: 
            p = create_hour_chart(schedule_df, hourly_df, int(r), int(h), False, alpha_boost=alpha_boost)
        if request.args.get('theme') == 'dark':
            return json.dumps(json_item(p, "hourly-chart", theme=Theme(json=DARK_THEME_JSON)))
        else:
            return json.dumps(json_item(p, "hourly-chart"))
    except(FileNotFoundError):
        return "Bad request. Has the game been initialized?"

def create_hour_chart(schedule_df, hourly_df, r, h, adjustment=False, alpha_boost=0):
    """Creates a Bokeh chart of the supply and demand curves given a round and hour"""

    colors = ['#57BCCD', '#3976AF', '#F08636', '#529D3F', '#C63A33', '#8D6AB8', '#85594E', 
              '#D57EBF', '#81E5D9', '#ECA5C8', '#BD9DDA', '#D6C849', '#F2A175']
    # colors = magma(7)
    # colors = viridis(7)

    # Read corresponding hourly csv (assume it exists)
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
        supply_curve_data['mwh_produced'].append(row['mwh_produced'])
        supply_curve_data['color'].append(colors[int(row['portfolio_id']) - 1 % len(colors)])
        mwh_running_total += float(row['unit_capacity'])

    base_cds = ColumnDataSource(supply_curve_data)

    chart_title = "Day " + str(r) + " hour " + str(h) + " supply and demand"

    min_bid = float(get_game_setting('min bid'))
    max_bid = float(get_game_setting('max bid'))
    bid_range = max_bid - min_bid
    y_min = min_bid - bid_range * 0.1
    y_max = max_bid + bid_range * 0.1

    chart = figure(title=chart_title, x_axis_label='MWh', y_axis_label='Price ($/MWh)', y_range=[y_min, y_max],
                   sizing_mode='stretch_width', height=300, title_location='above')

    supply_curve = chart.multi_line(xs='xs', ys='ys', line_width=4, line_color='color', line_alpha=0.6,
                                    hover_line_color='color', hover_line_alpha=1.0, source=base_cds)

    chart.add_tools(HoverTool(renderers=[supply_curve], show_arrow=False, line_policy='interp',
                              point_policy='follow_mouse', attachment='above', tooltips=[
                                  ('Portfolio', '@portfolio_name'),
                                  ('Unit', '@unit_name'),
                                  ('$/MWh', '@bid'),
                                  ('MWh Produced', '@mwh_produced')
                              ]))

    if adjustment:
        def fill_multiline_data(curve_dict, x_left, x_right, y, row, adj_dir, alpha, hover_alpha):
            """Adds another line to curve_dict at height y from x_left to x_right with display information
            drawn from row and adj_dir ('up' or 'down').
            """
            curve_dict['xs'].append([x_left, x_right])
            curve_dict['ys'].append([y, y])
            curve_dict['portfolio_name'].append(row['portfolio_name'])
            curve_dict['unit_name'].append(row['unit_name'])
            curve_dict['adj_bid'].append("{:0.2f}".format(y))
            curve_dict['mwh_adjusted'].append(row['mwh_adjusted_' + adj_dir])
            curve_dict['color'].append(colors[int(row['portfolio_id']) - 1 % len(colors)])
            curve_dict['alpha'].append(alpha)
            curve_dict['hover_alpha'].append(hover_alpha)
            return curve_dict

        up_adjust_curve_data = defaultdict(list)
        mwh_running_total = 0
        for _, row in hourly_df.iterrows():
            x_left = mwh_running_total
            x_right = x_left + float(row['unit_capacity'])
            adj_left = x_right - float(row['mwh_adjusted_up'])
            y = float(row['bid_up'])
            if float(row['mwh_adjusted_up']) > 0:
                fill_multiline_data(
                    up_adjust_curve_data, adj_left, x_right, y, row, 'up', 0.8, 1.0)
            if float(row['mwh_produced_initially']) < float(row['unit_capacity']):
                fill_multiline_data(
                    up_adjust_curve_data, x_left, adj_left, y, row, 'up', 0.2 + alpha_boost, 0.4 + alpha_boost)
            mwh_running_total += float(row['unit_capacity'])
        up_adj_cds = ColumnDataSource(up_adjust_curve_data)

        down_adjust_curve_data = defaultdict(list)
        mwh_running_total = 0
        for _, row in hourly_df.iterrows():
            x_left = mwh_running_total
            x_right = x_left + float(row['unit_capacity'])
            adj_left = x_right - float(row['mwh_adjusted_down'])
            y = float(row['bid_down'])
            if float(row['mwh_adjusted_down']) > 0:
                fill_multiline_data(
                    down_adjust_curve_data, adj_left, x_right, y, row, 'down', 0.8, 1.0)
            if float(row['mwh_produced_initially']) > 0:
                fill_multiline_data(
                    down_adjust_curve_data, x_left, adj_left, y, row, 'down', 0.2 + alpha_boost, 0.4 + alpha_boost)
            mwh_running_total += float(row['unit_capacity'])
        down_adj_cds = ColumnDataSource(down_adjust_curve_data)

        up_adj_curve = chart.multi_line(xs='xs', ys='ys', line_width=2.5, line_color='color', line_alpha='alpha', 
                                        line_dash='solid', hover_line_color='color', hover_line_alpha='hover_alpha', 
                                        source=up_adj_cds)

        chart.add_tools(HoverTool(renderers=[up_adj_curve], show_arrow=False, line_policy='interp',
                                point_policy='follow_mouse', attachment='below', tooltips=[
                                    ('Portfolio', '@portfolio_name'),
                                    ('Unit', '@unit_name'),
                                    ('Up Adj. $/MWh', '@adj_bid'),
                                    ('MWh Adjusted Up', '@mwh_adjusted')
                                ]))

        down_adj_curve = chart.multi_line(xs='xs', ys='ys', line_width=2.5, line_color='color', line_alpha='alpha', 
                                        line_dash='solid', hover_line_color='color', hover_line_alpha='hover_alpha', 
                                        source=down_adj_cds)

        chart.add_tools(HoverTool(renderers=[down_adj_curve], show_arrow=False, line_policy='interp',
                                point_policy='follow_mouse', attachment='below', tooltips=[
                                    ('Portfolio', '@portfolio_name'),
                                    ('Unit', '@unit_name'),
                                    ('Down Adj. $/MWh', '@adj_bid'),
                                    ('MWh Adjusted Down', '@mwh_adjusted')
                                ]))

    current_row = schedule_df[schedule_df['round'] == r][schedule_df['hour'] == h]
    net = current_row.iloc[0]['net_base_demand']
    slope = current_row.iloc[0]['slope']

    if slope == 0:
        def demand_y_to_x(y):
            return net
    else:
        def demand_y_to_x(y):
            return (float(y) * float(slope)) + net

    demand_y_min = min_bid - bid_range * 0.05
    demand_y_max = max_bid + bid_range * 0.05

    demand_ys = [demand_y_min, demand_y_max]
    demand_xs = [demand_y_to_x(demand_y_min), demand_y_to_x(demand_y_max)]

    chart.line(x=demand_xs, y=demand_ys, line_width=4, color='gray')

    (intercept_x, intercept_y) = get_supply_demand_intercept(hourly_df, schedule_df, r, h)

    intercept = {'x': [float("{:0.2f}".format(intercept_x))], 'y': [float("{:0.2f}".format(intercept_y))]}

    intercept_circle = chart.circle('x', 'y', color='gray', size=6, source=intercept)

    chart.add_tools(HoverTool(renderers=[intercept_circle], point_policy='snap_to_data', attachment='below',
                              tooltips=[("", "(@x{0.00} MWh, @y{0.00} $/MWh)"),]))


    chart.toolbar.active_drag = None

    return chart
    
def get_supply_demand_intercept(hourly_df, schedule_df, r, h):
    """Returns the intersection of the supply and demand curves in the form (quantity, price)."""
    
    current_row = schedule_df[schedule_df['round'] == r][schedule_df['hour'] == h]
    net = current_row.iloc[0]['net_base_demand']
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
            return ((1 / slope) * (quantity - net)) # price-giving function: inverse of Q = mP + b

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
                    # algebra gives quantity produced = demand_slope * bid + demand_base
                    intersect_quantity = (bid * slope) + net
                else:
                    # vertical line
                    intersect_quantity = net
                unit_production = intersect_quantity - running_production
                running_production += unit_production

    return (running_production, intercept_price)

@bp.route('/chart/summary')
def summary_chart():
    try:
        summary_df = pd.read_csv(os.path.join(CSV_FOLDER, 'summary.csv'))
        p = create_summary_chart(summary_df)
        if request.args.get('theme') == 'dark':
            return json.dumps(json_item(p, "summary-chart", theme=Theme(json=DARK_THEME_JSON)))
        else:
            return json.dumps(json_item(p, "summary-chart"))
    except(FileNotFoundError):
        return "Bad request. Has the game been initialized?"

def create_summary_chart(summary_df):
    """Creates a Bokeh chart of the current standings in summary.csv"""

    summary_df = summary_df.sort_values(by=['round', 'hour'], ascending=[True, True])
    header_suffix = 'balance' # I suppose this could change if we wanted summary charts of other things?
    selected_columns = summary_df.filter(regex=(".*_" + header_suffix))
    colors = ['#57BCCD', '#3976AF', '#F08636', '#529D3F', '#C63A33', '#8D6AB8', '#85594E', 
              '#D57EBF', '#81E5D9', '#ECA5C8', '#BD9DDA', '#D6C849', '#F2A175']
    r_h = summary_df[['round', 'hour']]

    extract_id = lambda header: int(re.search('player_(.*)_' + header_suffix, header).group(1))

    summary_lines_data = defaultdict(list)

    # When no hours have been run, lines will not appear (as they won't have a second point to be
    # defined with, so we create a series of points as well)
    draw_starting_points = False
    starting_money_points_data = defaultdict(list)

    for column in selected_columns.columns:
        portfolio_id = extract_id(column)
        starting_money = get_starting_money_by_portfolio_id(portfolio_id)

        # Add initial balance datapoint to lines (post-auction pre-spot markets)
        ys = [starting_money] + selected_columns[column].tolist()
        xs = list(range(len(ys)))
        name = get_portfolio_name_by_id(portfolio_id)
        summary_lines_data['xs'].append(xs)
        summary_lines_data['ys'].append(ys)
        summary_lines_data['id'].append(name)
        summary_lines_data['color'].append(colors[portfolio_id - 1 % len(colors)])

        # If there aren't enough values in the column to draw a line, add it to the points dict
        if selected_columns[column].isnull().all():
            draw_starting_points = True
            starting_money_points_data['x'].append(0)
            starting_money_points_data['y'].append(starting_money)
            starting_money_points_data['id'].append(name)
            starting_money_points_data['color'].append(colors[portfolio_id - 1 % len(colors)])


    cds = ColumnDataSource(summary_lines_data)

    chart_title = "Net balance by portfolio"

    chart = figure(title=chart_title, x_axis_label='Day/Hour', y_axis_label='Net Balance',
                   sizing_mode='stretch_width', height=300, title_location='above')

    summary_lines = chart.multi_line(xs='xs', ys='ys', line_width=4, line_color='color', line_alpha=0.6,
                                     hover_line_color='color', hover_line_alpha=1.0, source=cds)

    chart.add_tools(HoverTool(renderers=[summary_lines], show_arrow=False, line_policy='nearest',
                              point_policy='follow_mouse', attachment='above', tooltips=[
                                  ('Portfolio', '@id'),
                                  ('Balance', '$data_y{0,0.00}')
                              ]))

    if draw_starting_points:
        cds_circles = ColumnDataSource(starting_money_points_data)

        starting_circles = chart.circle('x', 'y', size=4, color='color', alpha=0.6, hover_color='color', hover_alpha=1.0, source=cds_circles)

        chart.add_tools(HoverTool(renderers=[starting_circles], show_arrow=False,
                                point_policy='follow_mouse', attachment='above', tooltips=[
                                    ('Portfolio', '@id'),
                                    ('Balance', '$data_y{0,0.00}')
                                ]))


    chart.yaxis[0].formatter = NumeralTickFormatter(format="0[.]0 a")
    # For more on Bokeh formatting, see 
    # https://docs.bokeh.org/en/latest/docs/reference/models/formatters.html#bokeh.models.formatters.NumeralTickFormatter
    
    # Add 1 for initial balance datapoint (post-auction pre-spot markets)
    chart.xaxis.ticker = list(range(len(r_h) + 1)) 
    r_h_names = ['0'] + round_hour_names(r_h)
    formatter_code = '''
        var tick_labels = {labels};
        return tick_labels[tick]
    '''.format(labels=r_h_names)
    chart.xaxis.formatter = FuncTickFormatter(code=formatter_code)

    chart.toolbar.active_drag = None

    return chart
