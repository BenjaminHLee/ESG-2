import os
import pandas as pd

from esg2 import CSV_FOLDER, CONFIG_FOLDER, HOURLY_FOLDER


def make_pretty_header(bid_base_r_h):
    """Takes in a string of the form "bid_{x}_{r}_{h}" and converts it to "{r}/{h}"
    or "{r}/{h} {x}", depending on the value of x"""
    try:
        s = bid_base_r_h.split('_')
        x = s[1]
        r = s[2]
        h = s[3]
        if x == "base":
            return f"{r}/{h}"
        elif x == "up":
            return f"{r}/{h} {x}"
        elif x == "down":
            return f"{r}/{h} dn"
        else:
            return "bad input string!"
    except:
        # TODO: LOG ERROR
        return "bad input string!"

def get_game_setting(setting):
    """Gets the setting value from the game_settings.csv file"""
    game_settings_df = pd.read_csv(os.path.join(CONFIG_FOLDER, 'game_settings.csv'))
    return game_settings_df.loc[game_settings_df['setting'] == setting]['value'].item()

def get_portfolio_names_list():
    """Reads portfolios.csv and returns a list of unique portfolio names"""
    portfolios_df = pd.read_csv(os.path.join(CONFIG_FOLDER, 'portfolios.csv'))
    portfolios = portfolios_df['portfolio_name'].unique()
    return portfolios

def get_portfolio_name_by_id(i):
    """Reads portfolios.csv and returns the portfolio_name with portfolio_id == id"""
    portfolios_df = pd.read_csv(os.path.join(CONFIG_FOLDER, 'portfolios.csv'))
    portfolio_name = portfolios_df.loc[portfolios_df['portfolio_id'] == i]['portfolio_name'].unique().item()
    return portfolio_name

def get_starting_money_by_portfolio_id(i):
    """Reads players.csv and returns the starting_money value where portfolio_id == i"""
    players_df = pd.read_csv(os.path.join(CSV_FOLDER, 'players.csv'))
    return players_df.loc[(players_df['portfolio_id'] == i),'starting_money'].values.astype(float)[0]


def get_initialized_portfolio_names_list():
    """Reads players and returns the list of portfolio names with an initialized player
    (i.e. the list of portfolios that are involved in the initialized game)"""
    players_df = pd.read_csv(os.path.join(CSV_FOLDER, 'players.csv'))
    names = players_df['portfolio'].unique()
    return names

def get_initialized_portfolio_ids_list():
    """Reads players and returns the list of portfolio ids with an initialized player
    (i.e. the list of portfolios that are involved in the initialized game)"""
    players_df = pd.read_csv(os.path.join(CSV_FOLDER, 'players.csv'))
    names = players_df['portfolio_id'].unique()
    return names

def last_filled_summary_row(summary_df):
    """Returns the round and hour of the last fully-completed row in summary_df.
    If a round is not found, default to r=1, h=1"""
    r = 1
    h = 1
    summary_df = summary_df.sort_values(by=['round', 'hour'], ascending=[True, True])
    for _, row in summary_df.iterrows():
        if not row.isnull().values.any():
            r = row['round']
            h = row['hour']
    return r, h

def first_incomplete_summary_row(summary_df):
    """Returns the round and hour of the first not-fully-completed row in summary_df.
    If a round is not found, defaults to the last row and hour"""
    r = 1
    h = 1
    summary_df = summary_df.sort_values(by=['round', 'hour'], ascending=[True, True])
    for _, row in summary_df.iterrows():
        r = row['round']
        h = row['hour']
        if row.isnull().values.any():
            return r, h
    return r, h

def round_hour_names(schedule_df):
    """Returns a list of strings in the form r/h for each r, h in schedule_df"""
    names = []
    for (r, h) in schedule_df[['round', 'hour']].itertuples(index=False):
        names.append(f"{r}/{h}")
    return names
