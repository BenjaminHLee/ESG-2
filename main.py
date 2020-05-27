# """
# PROGRAM EXPLANATION

# This text specifies this implementation of the Electricity Strategy Game 2 ("ESG 2"). The ideas 
# that went into this work can be found in Vassallo et al's specification and Ethan Knight's original 
# implementation of the UC Berkeley Electricity Strategy Game by Severin Bornstein. Program logic is 
# by Benjamin Lee. 


# DATA

# The program is centered around a set of .csv files. {value} denotes a header that will be filled 
# dynamically on the creation of the spreadsheet.

# CONFIG SPREADSHEETS:
# Initial program setup. This does not change during the game.
# -   demand : round,hour,north,south,net : demand in mwh for each hour of each round.
# -   portfolios : portfolio_id,portfolio_name,unit_id,unit_name,unit_location,unit_capacity,
#     cost_per_mwh,cost_daily_om,carbon_per_mwh : unit info for each unit in each portfolio.
# -   users : player_name,portfolio_owned,portfolio_id,starting_money,password : initial player 
#     account setup, to be configured based on results from auction.
# -   config : TODO add things as they appear necessary

# SUMMARY SPREADSHEET:
# Captures a macroscopic summary of prices over hours.
# -   summary : round,hour,north,south,net,price,
#     [player_{player_id}_revenue,player_{player_id}_cost,player_{player_id}_profit],
#     [player_{player_id}_balance] 
#     : market price, cost of adjustments, and balances for each hour of each round. Note: the square 
#     brackets indicate that these columns are to be repeated dynamically based on the number of 
#     players.

# HOURLY SPREADSHEETS:
# A set of spreadsheets (one per hour) recording bids, production, and revenue/cost for each unit. 
# -   round_{round}_hour_{hour} : portfolio_id,portfolio_name,unit_id,unit_name,unit_location,
#     unit_capacity,
#     cost_per_mwh,cost_daily_om,carbon_per_mwh, 
#     bid_base,bid_up,bid_down, 
#     activated,mwh_produced,mwh_adjusted_down,carbon_produced,price, 
#     revenue,adjust_down_revenue,cost_var,cost_om,profit 
#     : activated is a boolean variable indicating whether or not the unit was activated. cost_om 
#     will be zero except during hour 4, when the daily cost will be incurred. 

# CURRENT BID SPREADSHEET:
# Records bids for all hours as submitted by players. Constantly updating according to player form 
# inputs. Not visible to players, only administrators. When an hour is run, the bids in this 
# spreadsheet are recorded in the corresponding round_#_hour_#.csv file.
# -   bids : portfolio_id,portfolio_name,unit_id,unit_name, 
#     [bid_base_{round}_{hour},bid_up_{round}_{hour},bid_down_{round}_{hour}] 
#     : The square brackets indicate that these columns are to be repeated dynamically based on the 
#     number of rounds and hours. Note that this structure enables unit-specific adjustment bids; 
#     whether or not players can specify those values is at the discretion of the bid form creator. 


# PROGRAM FLOW

# Before running the game, the administrator provides the demand.csv, portfolios.csv, and users.csv 
# files. This defines the number of rounds, number of players, portfolio contents, unit attributes, 
# starting balances (based off of portfolio auction results), and hourly demand conditions. This also 
# defines player login credentials. Yes, the notion of security is foreign and the concept of a hash 
# function unfamiliar. (Players should understand that this game is not a technical exercise.)

# All of the .csv files are created at the start of the game — this means that all of the 
# spreadsheets exist for the entirety of the game. Spreadsheet data is never overwritten, except at 
# the discretion of the game administrator. As such, reviewing prior states/reverting to a prior 
# state is fairly painless.

# At any point in time, the game will be in one of two states: in a round or over. 

# DURING A ROUND

# Players submit bids. This updates the bids spreadsheet.

# The administrator runs the hour. This takes in the hour's demand (from demand.csv) and the player 
# bids (from the current bids.csv file), and determines which units will activate at which price. See 
# "ACTIVATING UNITS" for specific information on how this is determined, including adjustment. This 
# information is used to update the current round_#_hour_#.csv file as well as the summary.csv file. 
# The information is also used to draw three charts representing the net market, the south market, 
# the north market, and the adjustments made. The hour is then advanced.

# The PLAYER VIEW will consist of:
# -   A means through which the player can read the data in the summary.csv file, the past charts, 
#     and the past hourly spreadsheets
# -   A BIDDING FORM through which players can submit production bids for upcoming hours. 
#     Rough visualization:
#     — BIDDING FORM ———————————————————————————————————————————————————————————————————————————————    
#     | Day/Hour      Unit_1 bid  Unit_2 bid  Unit_3 bid  Unit_4 bid  Up adjust bid  Down adjust bid
#     | Day 2 hour 1: [        ]  [        ]  [        ]  [        ]     [        ]       [        ]
#     | Day 2 hour 2: [        ]  [        ]  [        ]  [        ]     [        ]       [        ]
#     | Day 2 hour 3: [        ]  [        ]  [        ]  [        ]     [        ]       [        ]
#     | Day 2 hour 4: [        ]  [        ]  [        ]  [        ]     [        ]       [        ]
#     | Day 3 hour 1: [        ]  [        ]  [        ]  [        ]     [        ]       [        ]
#     | Day 3 hour 2: [        ]  [        ]  [        ]  [        ]     [        ]       [        ]
#     | ...

# The ADMIN VIEW will consist of:
# -   A means through which the admin can read the data in the summary.csv file, the past charts, the 
#     past hourly spreadsheets, the bids spreadsheet, and the config spreadsheets.
# -   A button that runs the current hour and advances to the next hour.
# -   A means through which the admin can edit the summary, bids, and config spreadsheets.
# -   A means through which the admin can change the current round/hour (to revert to a prior state)

# GAME OVER

# When the current round/hour is equal to the last round/hour in the demand.csv spreadsheet, running 
# the hour will compute the hour and then advance the hour. As there will not be a specified demand 
# for this new hour, the administrator will not be able to run the hour. Additionally, the 
# player-side bidding form will be empty, as there will be no future bids to specify. This has the 
# effect of ending the game. 


# ACTIVATING UNITS

# This procedure is based on the work by Vassallo et al. and features the most significant departure 
# from prior iterations of the ESG. The core change: the market has been partitioned into two "zones" 
# ("NP-15" and "SP-15", or "north" and "south", respectively), joined by a transmission line. The 
# line has a finite and asymmetric transmission capacity (north to south 2500 MWh, south to north 
# 5000 MWh). As such, congestion occurs, requiring the ISO (this program) to adjust production so as 
# to avoid under- or overproducing. For more info, see the detailed specification by Vassallo et al.

# Unit activation is done as follows:

# First, construct a supply curve for the entire market, comparing market-wide supply and market-wide 
# demand. The supplying units below the demand curve are preliminarily activated at the price given 
# by the intersection of the market-wide supply and demand curves. 

# Next, calculate the net production (MWh) of each zone, and compare it to the zone-specific demand. 
# If demand is met in both zones, then no transmission is needed, and the activated units are 
# sufficiently producing. Note that if one zone is overproducing, then the other zone must be 
# underproducing by the same amount. If the north has a deficit less than or equal to 5000 MWh or the 
# south has a deficit less than or equal to 2500 MWh, then transmission resolves the deficit. 
# However, if the deficit is larger than these figures, then the ISO must adjust which units are 
# activated. This is determined using the adjustment bids. 

# In the underproducing region, additional units will have to be activated. The units are filtered to 
# select for units within the underproducing zone that are currently inactivated. The units within 
# the zone are then sorted by upwards adjustment bid. The set of units with the highest adjustment 
# bid is selected. Within this set, the unit with the lowest base bid is selected (if multiple units 
# have the same adjustment bid and the same base bid, the unit with the lower unit_id is selected). 
# This unit is then activated at price (bid_base - bid_up). It produces electricity until the deficit 
# is either exactly 5000/2500 MWh or the unit is at capacity. If the unit is at capacity and the 
# deficit is still too high, then this process is repeated with additional units until the deficit is 
# exactly 5000/2500 MWh.

# In the overproducing region, some activated units will have to be ramped down. The units are 
# filtered to select units within the overproducing zone that are currently activated. The units 
# within the zone are then sorted by downwards adjustment bid. The set of units with the lowest 
# downwards adjustment bid is selected. Within this set, the unit with the highest base bid is 
# selected (if multiple units have the same adjustment bid and the same base bid, the unit with the 
# higher unit_id is selected). This unit is then ramped down until the surplus is either exactly 
# 5000/2500 MWh or the unit is deactivated. The required compensation is recorded in the hourly 
# spreadsheet. If the unit is deactivated and the surplus is still too large, then this process is 
# repeated with additional units until the surplus is exactly 5000/2500 MWh. 

# This concludes the activation procedure. At this point, each plant has a determined MWh produced, 
# price received per MWh, and downwards adjustment compensation value. The costs of production are 
# calculated, the revenue calculated, and the figures recorded in the hourly spreadsheet. The hourly 
# spreadsheet now completed, the results are summarized and the summary.csv file updated. 
# """

