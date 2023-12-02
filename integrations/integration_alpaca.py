import os

from alpaca_trade_api import REST
from alpaca_trade_api.rest import APIError
from requests.exceptions import HTTPError

from strategy import calculate_order_quantity, determine_trade_actions
from testing_config import USE_ALPACA_PAPER

# Alpaca API credentials
ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY')
ALPACA_SECRET_KEY = os.environ.get('ALPACA_SECRET_KEY')
ALPACA_ENDPOINT = 'https://api.alpaca.markets'

ALPACA_PAPER_API_KEY = os.environ.get('ALPACA_PAPER_API_KEY')
ALPACA_PAPER_SECRET_KEY = os.environ.get('ALPACA_PAPER_SECRET_KEY')
ALPACA_PAPER_ENDPOINT = 'https://paper-api.alpaca.markets'

# Choose the correct set of credentials and endpoint based on USE_PAPER
KEY = ALPACA_PAPER_API_KEY if USE_ALPACA_PAPER else ALPACA_API_KEY
SECRET = ALPACA_PAPER_SECRET_KEY if USE_ALPACA_PAPER else ALPACA_SECRET_KEY
ENDPOINT = ALPACA_PAPER_ENDPOINT if USE_ALPACA_PAPER else ALPACA_ENDPOINT

# Initialize the Alpaca API
api = REST(KEY, SECRET, ENDPOINT)


def execute_trade_actions(api, actions):
  for action in actions:
    symbol = action['symbol']
    trade_action = action['action']
    quantity = action['quantity']
    message = f"{trade_action.capitalize()}ing {quantity} of {symbol}"
    not_enough_funds = (not isinstance(quantity, int) or quantity <= 0)
    try:
      if trade_action == 'sell':
        api.submit_order(symbol=symbol,
                         qty=quantity,
                         side='sell',
                         type='market',
                         time_in_force='gtc')
      elif trade_action == 'buy' and not_enough_funds:
        print(f"Not enough funds to buy shares in {symbol}.")
      elif trade_action == 'buy':
        api.submit_order(symbol=symbol,
                         qty=quantity,
                         side='buy',
                         type='market',
                         time_in_force='gtc')
        print(f"Order submitted: {message}")
    except APIError as e:
      print(f"An error occurred while submitting the order: {e}")


def analyze_portfolio(sentiment_data):
  try:
    portfolio = api.list_positions()
    portfolio_symbols = [position.symbol for position in portfolio]
    account = api.get_account()
    buying_power = float(account.buying_power)
  except (HTTPError, APIError) as e:
    print(f"An error occurred: {e}")
    return
  # Get trade actions from the strategy logic
  trade_actions = determine_trade_actions(portfolio_symbols, sentiment_data)
  # Update trade_actions with the actual quantity to buy/sell based on the current market prices
  updated_trade_actions = []
  for action in trade_actions:
    if action['action'] == 'buy':
      try:
        symbol = action['symbol']
        latest_trade = api.get_latest_trade(symbol)
        if latest_trade:
          current_price = latest_trade.price
          action['quantity'] = calculate_order_quantity(
              action['action'], buying_power, current_price)
          updated_trade_actions.append(action)
      except HTTPError as e:
        print(f"Could not fetch latest trade for {symbol}")
  # Execute updated trade actions
  if updated_trade_actions:
    execute_trade_actions(api, updated_trade_actions)
  else:
    print("No trade actions to execute.")
