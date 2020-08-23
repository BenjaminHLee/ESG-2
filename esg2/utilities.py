import os
import pandas as pd

from esg2 import CSV_FOLDER, CONFIG_FOLDER, HOURLY_FOLDER


def bid_base_r_h_to_header(bid_base_r_h):
    """Takes in a string of the form "bid_base_{r}_{h}" and converts it to "{r}/{h}" """
    try:
        s = bid_base_r_h.split('_')
        r = s[2]
        h = s[3]
        return r + "/" + h
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