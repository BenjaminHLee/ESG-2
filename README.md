# ESG-2
Flask app is at MVP status. Supports ESG-1 games. Pretty hourly charts!

FEATURES:
- Full web app
- SQLite database
- Account management via command line
- Player management via web app
- Configurable setting files
- Admin dashboard
- Player dashboard
- Scoreboard
- Pretty charts

TODO:
- Frontend adjustment bidding (required for full ESG-2 support)
- Fix instancing — move instance-specific .csv files to instance folder
- Documentation
- Inline documentation
- Restyle code (consistently)
- Improve logging
- Add guide for building/deploying

## Admin guide

### Installation

Currently, the only way to install this project is by cloning the repository to your web server of choice. More installation methods will come soon^tm. 
Until then, take the following steps:
1. Clone the repository
2. [Spin up a virtual environment](https://flask.palletsprojects.com/en/1.1.x/installation/#virtual-environments)
3. Install dependencies
  * `pip install Flask`
  * `pip install pandas`
  * `pip install WTForms`
 4. Set FLASK-APP
  * `export FLASK-APP=ESG-2`
 5. Run the app!
  * `python3 -m flask run`

### Administration

Having installed and started the app, there are a few steps before you can run the game.
1. Initialize the database
  * `python3 -m flask init-db`
2. Add an administrator account
  * `python3 -m flask add-admin [username] [password]`
  * If you mistype the password (or need to change any user's password at any point), simply run `python3 -m flask set-password [username] [new password]`.
3. Examine and configure your config files
  * Log into your admin account and go to the config page to edit these files. The repository comes with some presets, but you're welcome to change these to better suit your needs.
4. Add user accounts
  * Once you've provided the `porfolios.csv` configuration file, you'll be ready to start adding user accounts. Go to your config page and scroll down to 'Add Player.' There you'll be able to create accounts, set portfolios, and set (post-portfolio auction) starting balances.
5. Initialize the game
  * When you've set the configuration files and added all of the player accounts, go to your config page and click the 'Initialize Game' button.
6. Play!
  * You'll be able to see the pending bids from each player for each unit for each hour via your dashboard page. When you're ready to run an hour, select the round/hour from the dropdown menu and click 'Run Hour.' This will commit the bids, run the hourly calculations, and send the results to the scoreboard page.
  
### Configuration

There are three configuration files that expect to see certain values that satisfy certain criteria. Unexpected behavior may ensue if these files are malformed or missing. Generally speaking, you should be fine so long as you stick to the pattern presented by the default files.

#### game_settings.csv

Contains a few basic settings that are invariant over the course of the game. To be set prior to initialization. Two-column csv; effectively constructs a (key, value) structure. 
  * `interest rate`: Any float. Default: `0.05`. At the start of each day, each player's balance is multiplied by `(1 + interest rate)`.
  * `min bid`: Any float less than `max bid`. Default: `0.00`. Determines the minimum bid value. If adjustment is enabled, also determines the minimum downwards and upwards adjustment bid values. Any bids less than `min bid` will be set to `min bid`. 
  * `max bid`: Any float greater than `min bid`. Default: `500.00`. Determines the minimum bid value. If adjustment is enabled, also determines the minimum downwards and upwards adjustment bid values. Any bids greater than `max bid` will be set to `max bid`. If a player does not submit a bid for a unit during an hour, it will default to `max bid`. This applies to adjustment bids as well.
  * `adjustment`: `disabled`, `per portfolio`, or `per unit`. Default: `disabled`. Determines whether adjustment bidding and calculations are enabled or disabled. If not `disabled`, adjustment will be taken into consideration. If set to `per portfolio`, players will be given the option to hourly up/down adjust bids for all units in their portfolio; if set to `per unit` players will be able to set hourly up/down adjust bids on a per-unit basis.
  * `carbon`: `enabled` or `disabled`. Default: `disabled`. Determines whether or not carbon incurs costs.
  * `carbon tax rate`: Any float. Default: `0.00`. Determines how many dollars to charge per ton of carbon. Only applies if `carbon` is `enabled`.
  
#### portfolios.csv

Details every unit, including what portfolio it belongs to, its identifying information, and its power generation traits.
  * `portfolio_id`: Integer. Must match `porfolio_name` — there must be one name per `portfolio_id` number. Each portfolio must have a unique `portfolio_id`. 
  * `portfolio_name`: String. Must match `porfolio_id` — there must be one ID per `portfolio_name`. Each portfolio must have a unique `portfolio_name`.
  * `unit_id`: Integer. Must be unique. This number can have an actual impact upon the game: if two units have the same bid price, the one with the lower `unit_id` will be considered for production before the other.
  * `unit_name`: String. Must be unique.
  * `unit_location`: `North` or `South`. Determines which region the unit produces in. Only applies if adjustment is enabled.
  * `unit_capacity`: Float. Must be greater than zero. Determines the unit's production capacity in MWh. 
  * `cost_per_mwh`: Float. Determines the unit's variable cost (cost per MWh produced). 
  * `cost_daily_om`: Float. Determines the unit's fixed O&M cost, incurred daily (regardless of MWh produced). 
  * `carbon_per_mwh`: Float. Determines how many tons of carbon the unit produces per MWh generated.

#### schedule.csv

Sets variable parameters on an hourly basis.
  * `round,hour`: Integer, integer. Each `round,hour` pair should be unique. Interest is incurred whenever `hour` is equal to `1`.
  * `n_to_s_capacity`: Float. Determines the north-to-south transmission capacity (in MWh). Only relevant if adjustment is enabled. 
  * `s_to_n_capacity`: Float. Determines the south-to-north transmission capacity (in MWh). Only relevant if adjustment is enabled. 
  * `north`: Float. Determines the northern zone's demand (in MWh). Only relevant if adjustment is enabled. 
  * `south`: Float. Determines the southern zone's demand (in MWh). Only relevant if adjustment is enabled. 
  * `net`: Float. Determines the net demand (in MWh) at price = 0. Used in non-adjustment activation. Also used in pre-adjustment activation (if adjustment is enabled). 
  * `slope`: Float. Should be negative. Determines the slope of the demand curve. If `slope` is `0`, the engine assumes that demand should be perfectly inelastic.     Note: demand curves are defined as follows: `Price = slope * (Quantity - base demand)`, where `base demand` is `net`, `north`, or `south`, depending on the context.
  * `auction_type`: `uniform` or `discrete`. Determines whether the hour's price is uniform across all producing unit or each unit receives its bidded price.

  
## About the game

In the Electricity Strategy Game, (teams of) players play as Scheduling Coordinators, entities responsible for supplying the market with electricity. Their primary goal is to make more money than the other players.

The game has two primary phases: the portfolio auction and the hourly spot markets. Each team owns one portfolio of power generation units. Portfolios are usually asymmetric; the number of units per portfolio varies, and the units themselves are usually unique. Portfolios are assigned through a portfolio auction (traditionally a live English auction). Players finance this initial acquisition by taking on debt (effectively a negative starting balance).

After all the portfolios have been auctioned off, the hourly spot markets begin. Players now have the opportunity to make money selling their generated electricity to the market. The hourly spot markets occur over the course of a set number of days, with a set number of hours scheduled to occur each day. During each hour, players submit bid prices on a per-unit basis. These prices represent the price per megawatt-hour (MWh) the player would have to be paid in order to activate that unit's power generation capabilities. Once all players have submitted their bids for an hour, the administrator 'runs' the hour.

A supply curve is constructed from the market-wide bids (from all players), and the market-wide demand curve is constructed from the parameters provided in the game schedule file. Units 'below' the demand curve are activated; units 'above' the demand curve are 'too expensive' and are not activated, as the market will not pay for those bids. Activated units incur their variable production costs; all units incur operations and maintenance costs regardless of their activation status. Units that are activated sell their electricity. The price they receive depends on the hour's auction type: in a discrete price hour, the unit receives its bidded price per MWh; in a uniform price hour, the highest activated price per MWh will be paid for all active units, regardless of their submitted bid price. The revenues and costs are then recorded for each player. An additional interest factor is incurred at the start of each day. The interest rate, among other settings, is set in the game settings file.

The game engine also supports an additional feature: adjustment bidding. Based on the California Independent System Operator (CAISO) adjustment bidding procedure, this feature reflects the geographic realities of power transmission and the importance of location-specific production and demand. More details regarding adjustment bidding can be found [here](https://github.com/BenjaminHLee/ESG-2/blob/esg2-csv-tool/README.md). If adjustment bids are not enabled, disregard this section.

## About the app

This app was designed and implemented by Benjamin Lee. The app is written with [Flask](https://flask.palletsprojects.com/) in Python 3. The frontend style is derived from [Skeleton](http://getskeleton.com/). The app was preceded by [Ethan Knight's implementation](https://github.com/ehknight/ESG) of the ESG, which in turn was based on the [UC Berkeley Electricity Strategy Game by Severin Borenstein and Jim Bushnell](https://esg.haas.berkeley.edu/). Specifications were drawn from that implementation as well as conversations with Patrick Berger. Adjustment bidding mechanics were implemented according to designs by Christopher Martin, Steven Raanes, Merritt Vassallo, and Aidan Wen, who in turn referenced numerous CAISO documents and resources in their design process.

dm me @benjamin\_lee on Telegram.
