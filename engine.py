# hello world!

# imports
import numpy as np
import pandas as pd

import csv


# read CONFIG SPREADSHEETS from /csv/config files
demands_df = pd.read_csv('csv/config/demands.csv')
portfolios_df = pd.read_csv('csv/config/portfolios.csv')
users_df = pd.read_csv('csv/config/users.csv')

# SUMMARY SPREADSHEET:
# Captures a macroscopic summary of prices over hours.
# -   summary : round,hour,north,south,net,price,
#     [player_{player_id}_revenue,player_{player_id}_cost,player_{player_id}_profit],
#     [player_{player_id}_balance] 

def create_summary_sheet(users_df, demands_df):
    user_ids = users_df['portfolio_id'].tolist()

    # lambda functions for the header-generating list comprehension
    header_revenue  = lambda i: 'player_' + str(i) + '_revenue'
    header_cost     = lambda i: 'player_' + str(i) + '_cost'
    header_profit   = lambda i: 'player_' + str(i) + '_profit'
    header_balance  = lambda i: 'player_' + str(i) + '_balance'

    # Generates headers [player_{player_id}_revenue,player_{player_id}_cost,player_{player_id}_profit],
    # [player_{player_id}_balance] for each {player_id} in the users.csv file.
    summary_player_headers = ([f(i) for i in user_ids for f in (header_revenue, header_cost, header_profit)] 
                                + [header_balance(i) for i in user_ids])

    # Note that this is a local variable. As summary_csv will constantly be written and read from summary.csv, it is
    # important to load from the True summary.csv file whenever the data is needed, instead of a potentially out-of-
    # date summary_csv variable. Whenever possible, functions should interact indirectly through writing to summary.csv
    # and then reading summary.csv, instead of chaining functions directly.
    summary_csv = pd.concat([demands_df, pd.DataFrame(columns=(['price'] + summary_player_headers))], axis=1)

    # summary.csv is saved in the /csv/ directory.
    summary_csv.to_csv('csv/summary.csv')

# HOURLY SPREADSHEETS:
# A set of spreadsheets (one per hour) recording bids, production, and revenue/cost for each unit. 
# -   round_{round}_hour_{hour} : portfolio_id,portfolio_name,unit_id,unit_name,unit_location,
#     unit_capacity,
#     cost_per_mwh,cost_daily_om,carbon_per_mwh, 
#     bid_base,bid_up,bid_down, 
#     activated,mwh_produced,mwh_adjusted_down,carbon_produced,price, 
#     revenue,adjust_down_revenue,cost_var,cost_om,profit 

def create_hourly_sheets(demands_df, portfolios_df):
    # a list of (round, hour) pairs, for the purpose of naming each sheet
    round_hour_tuples = list(demands_df[['round', 'hour']].itertuples(index=False, name=None))

    hourly_additional_headers = ['bid_base','bid_up','bid_down','activated','mwh_produced',
                                 'mwh_adjusted_down','carbon_produced','price','revenue',
                                 'adjust_down_revenue','cost_var','cost_om','profit']

    for (r, h) in round_hour_tuples:
        hourly_df = pd.concat([portfolios_df, pd.DataFrame(columns=(hourly_additional_headers))], axis=1)

        # round_r_hour_h.csv is saved in the /csv/hourly/ directory.
        hourly_df.to_csv('csv/hourly/round_' + str(r) + '_hour_' + str(h) + '.csv')

create_summary_sheet(users_df, demands_df)
create_hourly_sheets(demands_df, portfolios_df)
