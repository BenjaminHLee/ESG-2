# hello world!

# imports
import numpy as np
import pandas as pd

import csv


# read CONFIG SPREADSHEETS from /csv/config files
demands_csv = pd.read_csv('csv/config/demands.csv')
portfolios_csv = pd.read_csv('csv/config/portfolios.csv')
users_csv = pd.read_csv('csv/config/users.csv')

# SUMMARY SPREADSHEET:
# Captures a macroscopic summary of prices over hours.
# -   summary : round,hour,north,south,net,price,
#     [player_{player_id}_revenue,player_{player_id}_cost,player_{player_id}_profit],
#     [player_{player_id}_balance] 

def create_summary_sheet(users_csv, demands_csv):
    user_ids = users_csv['portfolio_id'].tolist()

    header_revenue  = lambda i: 'player_' + str(i) + '_revenue'
    header_cost     = lambda i: 'player_' + str(i) + '_cost'
    header_profit   = lambda i: 'player_' + str(i) + '_profit'
    header_balance  = lambda i: 'player_' + str(i) + '_balance'

    summary_player_headers = ([f(i) for i in user_ids for f in (header_revenue, header_cost, header_profit)] 
                                + [header_balance(i) for i in user_ids])

    summary_csv = pd.concat([demands_csv, pd.DataFrame(columns=(['price'] + summary_player_headers))], axis=1)

    summary_csv.to_csv('csv/summary.csv')

create_summary_sheet(users_csv, demands_csv)