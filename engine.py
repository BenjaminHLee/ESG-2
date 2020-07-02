# hello world!

# imports
import numpy as np
import pandas as pd


# SUMMARY SPREADSHEET:
# Captures a macroscopic summary of performance over hours.
# -   summary : round,hour,north,south,net,
#     [player_{player_id}_revenue,player_{player_id}_cost,player_{player_id}_profit],
#     [player_{player_id}_balance] 

def create_summary_sheet(schedule_df, users_df):
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
    summary_df = pd.concat([schedule_df, pd.DataFrame(columns=(summary_player_headers))], axis=1)

    # summary.csv is saved in the /csv/ directory.
    summary_df.to_csv('csv/summary.csv', index=False)

# HOURLY SPREADSHEETS:
# A set of spreadsheets (one per hour) recording bids, production, and revenue/cost for each unit. 
# -   round_{round}_hour_{hour} : portfolio_id,portfolio_name,unit_id,unit_name,unit_location,
#     unit_capacity,
#     cost_per_mwh,cost_daily_om,carbon_per_mwh, 
#     bid_base,bid_up,bid_down, 
#     activated,mwh_produced_initially,mwh_produced_base,mwh_adjusted_down,mwh_adjusted_up,mwh_produced,
#     carbon_produced,base_revenue,adjust_down_revenue,adjust_up_revenue,revenue,cost_var,cost_om,profit 

def create_hourly_sheets(schedule_df, portfolios_df):
    # a list of (round, hour) pairs, for the purpose of naming each sheet
    round_hour_tuples = list(schedule_df[['round', 'hour']].itertuples(index=False, name=None))

    hourly_additional_headers = ['bid_base','bid_up','bid_down','base_price','activated','mwh_produced_initially',
                                 'mwh_produced_base','mwh_adjusted_down','mwh_adjusted_up','mwh_produced',
                                 'carbon_produced','base_revenue','adjust_down_revenue','adjust_up_revenue','revenue','cost_var','cost_om','profit']

    for (r, h) in round_hour_tuples:
        hourly_df = pd.concat([portfolios_df, pd.DataFrame(columns=(hourly_additional_headers))], axis=1)
        # round_r_hour_h.csv is saved in the /csv/hourly/ directory.
        hourly_df.to_csv('csv/hourly/round_' + str(r) + '_hour_' + str(h) + '.csv', index=False)

# CURRENT BID SPREADSHEET:
# Records bids for all hours as submitted by players. Constantly updating according to player form 
# inputs. Not visible to players, only administrators. When an hour is run, the bids in this 
# spreadsheet are recorded in the corresponding round_#_hour_#.csv file.
# -   bids : portfolio_id,portfolio_name,unit_id,unit_name, 
#     [bid_base_{round}_{hour},bid_up_{round}_{hour},bid_down_{round}_{hour}] 
#     : The square brackets indicate that these columns are to be repeated dynamically based on the 
#     number of rounds and hours. Note that this structure enables unit-specific adjustment bids; 
#     whether or not players can specify those values is at the discretion of the bid form creator. 

def create_bids_sheet(schedule_df, portfolios_df):
    # a list of (round, hour) pairs, for the purpose of naming the repeated columns
    round_hour_tuples = list(schedule_df[['round', 'hour']].itertuples(index=False, name=None))

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
    bids_df.to_csv('csv/bids.csv',index=False)


def determine_active_units(r, h, bids_df, schedule_df, hourly_df, portfolios_df):
    # Read bids from bids_df into hourly_df
    hourly_df['bid_base'] = bids_df[('bid_base_' + str(r) + '_' + str(h))]
    hourly_df['bid_up']   = bids_df[('bid_up_'   + str(r) + '_' + str(h))]
    hourly_df['bid_down'] = bids_df[('bid_down_' + str(r) + '_' + str(h))]

    # Create market-wide supply curve 
    # net_supply_curve = construct_net_supply_curve(hourly_df) TODO properly

    # Find intersection price, quantity
    # (price, quantity) = intersect_supply_demand(r, h, schedule_df, net_supply_curve) TODO properly

    # Update hourly sheet with preliminary activations at price up unitl demand is fulfilled
    # This means that we're going to be 'working-in-place' on the hourly dataframe while running this function.
    hourly_df = run_initial_activation(r, h, schedule_df, hourly_df) # HACK only works because demand is perfectly inelastic

    # Not all of the plants are going to be checked for adjustment down/up; initializing with 0's avoids later issues
    hourly_df['mwh_adjusted_down'] = 0
    hourly_df['mwh_adjusted_up'] = 0

    # Check zone specific production
    north_production = hourly_df.loc[(hourly_df['unit_location'] == "North")]['mwh_produced_initially'].sum()
    south_production = hourly_df.loc[(hourly_df['unit_location'] == "South")]['mwh_produced_initially'].sum()

    # Compare to zone specific demand
    north_demand = schedule_df.loc[(schedule_df['round'] == r) & (schedule_df['hour'] == h)]['north'].values.item()
    south_demand = schedule_df.loc[(schedule_df['round'] == r) & (schedule_df['hour'] == h)]['south'].values.item()

    # Get interzone transmission capacities
    n_to_s_capacity = schedule_df.loc[(schedule_df['round'] == r) & (schedule_df['hour'] == h)]['n_to_s_capacity'].values.item()
    s_to_n_capacity = schedule_df.loc[(schedule_df['round'] == r) & (schedule_df['hour'] == h)]['s_to_n_capacity'].values.item()

    print("North prod: {} / North demand: {}".format(north_production, north_demand))
    print("South prod: {} / South demand: {}".format(south_production, south_demand))

    if (north_production - north_demand <= n_to_s_capacity and south_production - south_demand <= s_to_n_capacity):
        # then transmission resolves it and we're fine
        print("No adjustment necessary.")
    elif (north_production - north_demand >= n_to_s_capacity):
        print("North overproducing.")
        # north has a surplus, south has a deficit
        # DEACTIVATE north plants
        # filter for activated plants in the north
        active_north_df = hourly_df.loc[(hourly_df['unit_location'] == "North") & (hourly_df['activated'] == 1)]
        # sort by down adjustment bid (ascending), then initial bid (descending), then unit id (descending)
        active_north_df = active_north_df.sort_values(by=['bid_down', 'bid_base', 'unit_id'], ascending=[True, False, False])

        excess = north_production - north_demand - n_to_s_capacity # n_to_s_capacity MWh can go to the south
        print("North excess: {}".format(excess))

        for _, unit in active_north_df.iterrows(): # HACK : iterrows is an antipattern
            unit_production = unit['mwh_produced_initially']
            # Ramp down until excess is resolved or the unit isn't producing any more
            mwh_reduced = min(abs(unit_production), excess)
            # Edit hourly_df to reflect update
            hourly_df.loc[(hourly_df['unit_id'] == unit['unit_id']),'mwh_adjusted_down'] = mwh_reduced
            hourly_df.loc[(hourly_df['unit_id'] == unit['unit_id']),'mwh_produced_base'] -= mwh_reduced
            if (mwh_reduced == unit_production):
                hourly_df.loc[(hourly_df['unit_id'] == unit['unit_id']),'activated'] = 0
            excess -= mwh_reduced
            print("Reduced unit {} (base: {}, down: {}) production by {} MWh to {} MWh. Remaining excess: {}"
                    .format(unit['unit_id'], unit['bid_base'], unit['bid_down'], mwh_reduced, (unit_production - mwh_reduced), excess))

        # ACTIVATE south plants
        # filter for not-fully-activated plants in the south
        inactive_south_df = hourly_df.loc[(hourly_df['unit_location'] == "South") & (hourly_df['mwh_produced_initially'] < hourly_df['unit_capacity'])]
        # sort by up adjustment bid (descending), initial bid (ascending), then unit id (ascending)
        inactive_south_df = inactive_south_df.sort_values(by=['bid_up', 'bid_base', 'unit_id'], ascending=[False, True, True])

        deficit = south_demand - south_production - n_to_s_capacity # n_to_s_capacity MWh from north
        
        for _, unit in inactive_south_df.iterrows(): # HACK : antipattern
            unit_capacity = unit['unit_capacity']
            mwh_produced_initially = unit['mwh_produced_initially']
            # Ramp up until deficit is resolved or unit is at max capacity
            mwh_increased = min(abs(unit_capacity - mwh_produced_initially), deficit)
            # Log increased production
            hourly_df.loc[(hourly_df['unit_id'] == unit['unit_id']),'mwh_adjusted_up'] = mwh_increased
            if (mwh_increased > 0):
                hourly_df.loc[(hourly_df['unit_id'] == unit['unit_id']),'activated'] = 1
            deficit -= mwh_increased
            print("Increased unit {} (base: {}, up: {}) production by {} MWh to {} MWh at price ${}. Remaining deficit: {}"
                    .format(unit['unit_id'], unit['bid_base'], unit['bid_up'], mwh_increased,
                    (mwh_produced_initially + mwh_increased),(unit['bid_base'] - unit['bid_up']), deficit))


    elif (south_production - south_demand >= s_to_n_capacity):
        print("South overproducing.")
        # north has a deficit, south has a surplus
        # DEACTIVATE south plants
        # filter for activated plants in the south
        active_south_df = hourly_df.loc[(hourly_df['unit_location'] == "South") & (hourly_df['activated'] == 1)]
        # sort by down adjustment bid (ascending), then initial bid (descending), then unit id (descending)
        active_south_df = active_south_df.sort_values(by=['bid_down', 'bid_base', 'unit_id'], ascending=[True, False, False])

        excess = south_production - south_demand - s_to_n_capacity # s_to_n_capacity MWh can go to the north
        print("South excess: {}".format(excess))

        for _, unit in active_south_df.iterrows(): # HACK : antipattern
            unit_production = unit['mwh_produced_initially']
            # Ramp down until excess is resolved or the unit isn't producing any more
            mwh_reduced = min(abs(unit_production), excess)
            # Edit hourly_df to reflect update
            hourly_df.loc[(hourly_df['unit_id'] == unit['unit_id']),'mwh_adjusted_down'] = mwh_reduced
            hourly_df.loc[(hourly_df['unit_id'] == unit['unit_id']),'mwh_produced_base'] -= mwh_reduced
            if (mwh_reduced == unit_production):
                hourly_df.loc[(hourly_df['unit_id'] == unit['unit_id']),'activated'] = 0
            excess -= mwh_reduced
            print("Reduced unit {} (base: {}, down: {}) production by {} MWh to {} MWh. Remaining excess: {}"
                    .format(unit['unit_id'], unit['bid_base'], unit['bid_down'], mwh_reduced, (unit_production - mwh_reduced), excess))

        # ACTIVATE north plants
        # filter for not-fully-active plants in the north
        inactive_north_df = hourly_df.loc[(hourly_df['unit_location'] == "North") & (hourly_df['mwh_produced_initially'] < hourly_df['unit_capacity'])]
        # sort by up adjustment bid (descending), initial bid (ascending), then unit id (ascending)
        inactive_north_df = inactive_north_df.sort_values(by=['bid_up', 'bid_base', 'unit_id'], ascending=[False, True, True])

        deficit = north_demand - north_production - s_to_n_capacity # s_to_n_capacity MWh from south
        
        for _, unit in inactive_north_df.iterrows(): # HACK : antipattern
            unit_capacity = unit['unit_capacity']
            mwh_produced_initially = unit['mwh_produced_initially']
            # Ramp up until deficit is resolved or unit is at max capacity
            mwh_increased = min(abs(unit_capacity - mwh_produced_initially), deficit)
            # Log increased production
            hourly_df.loc[(hourly_df['unit_id'] == unit['unit_id']),'mwh_adjusted_up'] = mwh_increased
            if (mwh_increased > 0):
                hourly_df.loc[(hourly_df['unit_id'] == unit['unit_id']),'activated'] = 1
            deficit -= mwh_increased
            print("Increased unit {} (base: {}, up: {}) production by {} MWh to {} MWh at price ${}. Remaining deficit: {}"
                    .format(unit['unit_id'], unit['bid_base'], unit['bid_up'], mwh_increased,
                    (mwh_produced_initially + mwh_increased),(unit['bid_base'] - unit['bid_up']), deficit))

    return hourly_df

# def construct_net_supply_curve(hourly_df):
#     first  = lambda x: x[0]
#     second = lambda x: x[1]

def run_initial_activation(r, h, schedule_df, hourly_df):
    # HACK only works because demand is perfectly inelastic
    net_demand = schedule_df.loc[(schedule_df['round'] == r) & (schedule_df['hour'] == h)]['net'].values.item()

    print("Calculating net curve")
    print("Net demand: {}".format(net_demand))

    hourly_df = hourly_df.sort_values(by=['bid_base', 'unit_id'])

    running_production = 0
    activation_record = []
    production_record = []
    base_price = 0

    for _, unit in hourly_df.iterrows(): # HACK this is an antipattern
        unit_capacity = unit['unit_capacity']
        remaining_demand = net_demand - running_production
        mwh_produced_initially = min(abs(unit_capacity), remaining_demand) 
                        # maybe python can optimize better if it knows capacity is positive?
        running_production += mwh_produced_initially
        remaining_demand -= mwh_produced_initially

        if (mwh_produced_initially == 0):
            activation_record.append(0)
        else:
            activation_record.append(1)
            if (remaining_demand == 0):
                base_price = unit['bid_base']
        production_record.append(mwh_produced_initially)
        print("Unit {} (bid {}) produced {} MWh. Running production: {}. Remaining demand: {}"
                .format(unit['unit_id'], unit['bid_base'], mwh_produced_initially, running_production, remaining_demand))
        
    # To avoid mutating something while iterating over it, we store the production of each plant in an array.
    # Only after we're done iterating do we write to the hourly dataframe.
    # This seems scuffed
    hourly_df['base_price'] = base_price
    hourly_df['activated'] = pd.Series(activation_record, index=hourly_df.index[:len(activation_record)])
    hourly_df['mwh_produced_initially'] = round(pd.Series(production_record, index=hourly_df.index[:len(production_record)]), 2)
    hourly_df['mwh_produced_base'] = round(pd.Series(production_record, index=hourly_df.index[:len(production_record)]), 2)

    return hourly_df

def complete_hourly_sheet(hourly_df, last_hour):
    # mwh_produced
    mwh_record = []
    # carbon_produced
    carbon_record = []
    # base_revenue
    base_revenue_record = []
    # adjust_down_revenue
    adjust_down_rev_record = []
    # adjust_up_revenue
    adjust_up_rev_record = []
    # revenue
    revenue_record = []
    # cost_var
    cost_var_record = []
    # cost_om
    cost_om_record = []
    # profit
    profit_record = []

    for _, unit in hourly_df.iterrows(): # HACK : you need to learn how to avoid this
        (cost_per_mwh,cost_daily_om,carbon_per_mwh,base_price,
        bid_base,bid_up,bid_down,mwh_produced_initially,
        mwh_produced_base,mwh_adjusted_down,mwh_adjusted_up) = unit[['cost_per_mwh','cost_daily_om','carbon_per_mwh',
                                                                    'base_price','bid_base','bid_up','bid_down',
                                                                    'mwh_produced_initially','mwh_produced_base',
                                                                    'mwh_adjusted_down','mwh_adjusted_up']]
        
        mwh_produced = mwh_produced_initially - mwh_adjusted_down + mwh_adjusted_up
        # Assuming uniform auction
        revenue = mwh_produced_base * base_price + mwh_adjusted_down * bid_down + mwh_adjusted_up * (bid_base - bid_up)
        cost_var = mwh_produced * cost_per_mwh
        if last_hour:
            cost_om = cost_daily_om
        else:
            cost_om = 0
        cost = cost_var + cost_om
        profit = revenue - cost

        mwh_record.append(mwh_produced)
        carbon_record.append(mwh_produced * carbon_per_mwh)
        base_revenue_record.append(mwh_produced_base * base_price) # Assuming uniform auction
        adjust_down_rev_record.append(mwh_adjusted_down * bid_down)
        adjust_up_rev_record.append(mwh_adjusted_up * (bid_base - bid_up))
        revenue_record.append(revenue)
        cost_var_record.append(cost_var)
        cost_om_record.append(cost_om)
        profit_record.append(profit)

    # mwh_produced,carbon_produced,base_revenue,adjust_down_revenue,adjust_up_revenue,revenue,cost_var,cost_om,profit
    hourly_df['mwh_produced']        = pd.Series(mwh_record, index=hourly_df.index[:len(mwh_record)])
    hourly_df['carbon_produced']     = pd.Series(carbon_record, index=hourly_df.index[:len(carbon_record)])
    hourly_df['base_revenue']        = pd.Series(base_revenue_record, index=hourly_df.index[:len(base_revenue_record)])
    hourly_df['adjust_down_revenue'] = pd.Series(adjust_down_rev_record, index=hourly_df.index[:len(adjust_down_rev_record)])
    hourly_df['adjust_up_revenue']   = pd.Series(adjust_up_rev_record, index=hourly_df.index[:len(adjust_up_rev_record)])
    hourly_df['revenue']             = pd.Series(revenue_record, index=hourly_df.index[:len(revenue_record)])
    hourly_df['cost_var']            = pd.Series(cost_var_record, index=hourly_df.index[:len(cost_var_record)])
    hourly_df['cost_om']             = pd.Series(cost_om_record, index=hourly_df.index[:len(cost_om_record)])
    hourly_df['profit']              = pd.Series(profit_record, index=hourly_df.index[:len(profit_record)])

    return hourly_df

def last_hour(r, h): # TODO: update this to handle variable numbers of hours
    if (h == 4):
        return True
    else:
        return False

def run_hour(r, h, bids_df):
    print("Running round {} hour {}".format(r, h))
    # read hourly csv
    hourly_df = pd.read_csv('csv/hourly/round_' + str(r) + '_hour_' + str(h) + '.csv')

    # determine active units
    hourly_df = determine_active_units(r, h, bids_df, schedule_df, hourly_df, portfolios_df)

    # check if it's the last hour of the round
    last = last_hour(r, h)

    # complete hourly sheet columns carbon_produced,revenue,adjust_down_revenue,cost_var,cost_om,profit
    hourly_df = complete_hourly_sheet(hourly_df, last)

    hourly_df.to_csv('csv/hourly/round_' + str(r) + '_hour_' + str(h) + '.csv',index=False) 


# SUMMARY SPREADSHEET:
# Captures a macroscopic summary of performance over hours.
# -   summary : round,hour,north,south,net,
#     [player_{player_id}_revenue,player_{player_id}_cost,player_{player_id}_profit],
#     [player_{player_id}_balance] 

def update_summary(r, h, summary_df, users_df):
    hourly_df = pd.read_csv('csv/hourly/round_' + str(r) + '_hour_' + str(h) + '.csv')

    portfolio_ids = users_df['portfolio_id'].tolist()

    print("Hour summary:")

    for portfolio_id in portfolio_ids:
        portfolio_df = hourly_df.loc[hourly_df['portfolio_id'] == portfolio_id]

        revenues = portfolio_df['revenue'].sum()
        costs = portfolio_df['cost_var'].sum() + portfolio_df['cost_om'].sum()
        profits = portfolio_df['profit'].sum()


        prefix = "player_" + str(portfolio_id) + "_"
        revenue_header = prefix + "revenue"
        cost_header    = prefix + "cost"
        profit_header  = prefix + "profit"
        balance_header = prefix + "balance"

        summary_df.loc[(summary_df['round'] == r) & (summary_df['hour'] == h),revenue_header] = round(revenues, 2)
        summary_df.loc[(summary_df['round'] == r) & (summary_df['hour'] == h),cost_header]    = round(costs, 2)
        summary_df.loc[(summary_df['round'] == r) & (summary_df['hour'] == h),profit_header]  = round(profits, 2)

        # update balance: 
        # If it's the first round first hour, then be sure to factor in initial balance, 
        # otherwise use previous balance and new profit

        balance = 0

        if (summary_df.loc[(summary_df['round'] == r) & (summary_df['hour'] == h)].index.values.astype(int)[0] == 0):
            # if the round/hour row is at the top of the table, factor in starting money from users_df
            balance = users_df.loc[(users_df['portfolio_id'] == portfolio_id),'starting_money'].values.astype(int)[0] + profits
        else:
            # otherwise, look at the value above and add profits
            current_row_index = summary_df.loc[(summary_df['round'] == r) & (summary_df['hour'] == h)].index.values.astype(int)[0]
            balance = summary_df.iloc[current_row_index - 1][balance_header] + profits 

        name = portfolio_df['portfolio_name'].iloc[0] 
        # TODO : the portfolio_id,portfolio_name repitition in portfolios.csv is a SPoT violation; rethink structure 
        print("{} Current balance: ${:0.2f} Revenue: ${:0.2f} Cost: ${:0.2f} Profit: ${:0.2f}"
                .format(name, balance, revenues, costs, profits))

        summary_df.loc[(summary_df['round'] == r) & (summary_df['hour'] == h),balance_header] = round(balance, 2)

    summary_df.to_csv('csv/summary.csv', index=False)


# read CONFIG SPREADSHEETS from /csv/config files
schedule_df = pd.read_csv('csv/config/schedule.csv')
portfolios_df = pd.read_csv('csv/config/portfolios.csv')
users_df = pd.read_csv('csv/config/users.csv')

schedule_df = schedule_df.sort_values(by=['round', 'hour'], ascending=[True, True])
users_df = users_df.sort_values(by=['portfolio_id'], ascending=[True])


create_summary_sheet(schedule_df, users_df)
create_hourly_sheets(schedule_df, portfolios_df)

summary_df = pd.read_csv('csv/summary.csv')
bids_df = pd.read_csv('csv/bids.csv')

run_hour(1, 1, bids_df)
print("Hour 1 run; updating summary")
update_summary(1, 1, summary_df, users_df)

run_hour(1, 2, bids_df)
print("Hour 2 run; updating summary")
update_summary(1, 2, summary_df, users_df)

run_hour(1, 3, bids_df)
print("Hour 3 run; updating summary")
update_summary(1, 3, summary_df, users_df)

run_hour(1, 4, bids_df)
print("Hour 4 run; updating summary")
update_summary(1, 4, summary_df, users_df)



# TODO : Fix decimal inconsistencies
# TODO : Design csv imports consistently — 
#   when should csvs be read? Which functions should take in dataframes, and which should read from /csv/?
