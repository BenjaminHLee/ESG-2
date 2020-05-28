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

def create_summary_sheet(demands_df, users_df):
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

    # Note that this is a local variable. As summary_df will constantly be written and read from summary.csv, it is
    # important to load from the True summary.csv file whenever the data is needed, instead of a potentially out-of-
    # date summary_df variable. Whenever possible, functions should interact indirectly through writing to summary.csv
    # and then reading summary.csv, instead of chaining functions directly.
    summary_df = pd.concat([demands_df, pd.DataFrame(columns=(['price'] + summary_player_headers))], axis=1)

    # summary.csv is saved in the /csv/ directory.
    summary_df.to_csv('csv/summary.csv')

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

# CURRENT BID SPREADSHEET:
# Records bids for all hours as submitted by players. Constantly updating according to player form 
# inputs. Not visible to players, only administrators. When an hour is run, the bids in this 
# spreadsheet are recorded in the corresponding round_#_hour_#.csv file.
# -   bids : portfolio_id,portfolio_name,unit_id,unit_name, 
#     [bid_base_{round}_{hour},bid_up_{round}_{hour},bid_down_{round}_{hour}] 
#     : The square brackets indicate that these columns are to be repeated dynamically based on the 
#     number of rounds and hours. Note that this structure enables unit-specific adjustment bids; 
#     whether or not players can specify those values is at the discretion of the bid form creator. 

def create_bids_sheet(demands_df, portfolios_df):
    # a list of (round, hour) pairs, for the purpose of naming the repeated columns
    round_hour_tuples = list(demands_df[['round', 'hour']].itertuples(index=False, name=None))

    # the part of portfolios_df that is used to construct bids_df
    portfolios_headers = ['portfolio_id','portfolio_name','unit_id','unit_name']

    # lambda functions for the header-generating list comprehension
    # each of these functions is equivalent to lambda (r, h): ... , but tuple unpacking was removed
    header_base = lambda r_h: 'bid_base_' + str(r_h[0]) + '_' + str(r_h[1])
    header_up   = lambda r_h: 'bid_up_'   + str(r_h[0]) + '_' + str(r_h[1])
    header_down = lambda r_h: 'bid_down_' + str(r_h[0]) + '_' + str(r_h[1])

    bids_r_h_headers = ([f(r_h) for r_h in round_hour_tuples for f in (header_base, header_up, header_down)])

    bids_df = pd.concat([portfolios_df[portfolios_headers], pd.DataFrame(columns=bids_r_h_headers)], axis=1)

    # bids.csv is saved in the /csv/ directory.
    bids_df.to_csv('csv/bids.csv')


create_summary_sheet(demands_df, users_df)
create_hourly_sheets(demands_df, portfolios_df)
create_bids_sheet(demands_df, portfolios_df)
