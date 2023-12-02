import os
from datetime import datetime, timedelta

import humanize
import vectorbt as vbt
from pandas import Timestamp

from integrations.integration_news_api import fetch_news
from integrations.integration_openai import analyze_sentiments
from strategy import calculate_order_quantity, determine_trade_actions

NUMBER_OF_BACKTEST_DAYS = 30
INITIAL_BACKTEST_PORTFOLIO_VALUE = 10000
HOURS_BETWEEN_TRADES = 24
BETWEEN_TRADES_TO_STRING = "1d"

vbt.settings['data']['alpaca']['key_id'] = os.environ.get('ALPACA_API_KEY')
vbt.settings['data']['alpaca']['secret_key'] = os.environ.get(
    'ALPACA_SECRET_KEY')


def humanize_time(dt):
  # Custom function to replace 'humanize.naturaltime' for control over the format
  delta = datetime.now() - dt
  if delta.days == 1:
    return "1 day ago"
  else:
    return humanize.naturaltime(dt)


def get_sentiment_data_for_time_period(start_time, end_time):
  articles = fetch_news(from_date=start_time, to_date=end_time)
  sentiment_data = analyze_sentiments(articles)

  return sentiment_data


def fetch_historical_data(symbol, start_date, end_date):
  # Format dates into a human-readable string
  human_readable_start_date = humanize_time(start_date) + " UTC"
  human_readable_end_date = humanize_time(end_date) + " UTC"

  print(
      f"Fetching historical data for {symbol} from {human_readable_start_date} to {human_readable_end_date}"
  )
  try:
    alpacadata = vbt.AlpacaData.download(symbol,
                                         start=human_readable_start_date,
                                         end=human_readable_end_date,
                                         interval=BETWEEN_TRADES_TO_STRING)

    return alpacadata.get()
  except Exception as e:
    print(f"Error fetching historical data for {symbol}: {e}")
    return


async def fetch_historical_data_for_all_symbols(trade_actions_list, start_date,
                                                end_date):
  symbols = set(action['symbol'] for _, action in trade_actions_list)
  symbol_data = {}
  for symbol in symbols:
    historical_data = fetch_historical_data(symbol, start_date, end_date)
    symbol_data[symbol] = historical_data
  return symbol_data


async def run_backtest():
  start_date = datetime.now() - timedelta(days=30)
  backtest_start_date = start_date - timedelta(days=NUMBER_OF_BACKTEST_DAYS)
  backtest_end_date = start_date

  # Creating Sentiment Data and Trade Actions List
  trade_actions_list = await generate_trade_actions_list(
      backtest_start_date, backtest_end_date)
  print(f"trade_actions_list: {trade_actions_list}")

  # Fetching Historical Data and Calculating Portfolio Value
  symbol_data = await fetch_historical_data_for_all_symbols(
      trade_actions_list, backtest_start_date, backtest_end_date)
  print(f"Symbol Data: {symbol_data}")
  final_portfolio_value = await calculate_total_portfolio_value(
      trade_actions_list, symbol_data, INITIAL_BACKTEST_PORTFOLIO_VALUE)

  print(f"Final backtest portfolio value: {final_portfolio_value}")


async def generate_trade_actions_list(start_date, end_date):
  trade_actions_list = []
  portfolio_symbols = set(
  )  # Keeps track of symbols currently in the portfolio

  current_period_start = start_date
  current_period_end = current_period_start + timedelta(
      hours=HOURS_BETWEEN_TRADES)
  while current_period_end <= end_date:
    sentiment_data = await get_sentiment_data_for_time_period(
        current_period_start, current_period_end)

    # Determine trade actions based on the current portfolio and sentiment data
    trade_actions = determine_trade_actions(portfolio_symbols, sentiment_data)
    for action in trade_actions:
      if action['action'] == 'buy':
        # Add symbol to portfolio if it's a buy action
        portfolio_symbols.add(action['symbol'])
      elif action['action'] == 'sell':
        # Remove symbol from portfolio if it's a sell action
        portfolio_symbols.discard(action['symbol'])

    trade_actions_list.extend([(current_period_start , action)
                               for action in trade_actions])
    current_period_start += timedelta(hours=HOURS_BETWEEN_TRADES)
    current_period_end += timedelta(hours=HOURS_BETWEEN_TRADES)

  return trade_actions_list


async def calculate_total_portfolio_value(trade_actions_list, symbol_data,
                                          initial_capital):
  capital = initial_capital
  portfolio = {}

  for trade_date, action in trade_actions_list:
    symbol = action['symbol']
    trade_action = action['action']
    quantity_type = action['quantity']

    # Check if historical data for the symbol is available
    if symbol in symbol_data and symbol_data[symbol] is not None:
      # Convert trade_date to a Timestamp in the correct timezone
      trade_datetime = Timestamp(trade_date).tz_localize('UTC')
      historical_index = symbol_data[symbol].index

      if trade_datetime in historical_index:
        current_price = symbol_data[symbol].loc[trade_datetime]['Open']
      else:
        # Find the next available price if exact trade_date is not available
        available_dates = historical_index[historical_index >= trade_datetime]
        if not available_dates.empty:
          closest_date = available_dates[0]
          current_price = symbol_data[symbol].loc[closest_date]['Open']
          print(f"current_price: {current_price} for symbol: {symbol}")
        else:
          print(
              f"No available trading data for {symbol} on or after {trade_date}"
          )
          continue
    else:
      print(f"No historical data available for {symbol} on {trade_date}")
      continue

    # Handle buy actions  
    if trade_action == 'buy':
      print(f"quanity_type: {quantity_type}, capital: {capital}, current_price: {current_price}")
      quantity_to_buy = calculate_order_quantity(trade_action, capital,
                                                 current_price)
      print(f"trade_action: buy, quantity_to_buy: {quantity_to_buy}")
      if capital >= quantity_to_buy * current_price:
        portfolio[symbol] = portfolio.get(symbol, 0) + quantity_to_buy
        capital -= quantity_to_buy * current_price

    # Handle sell actions
    elif trade_action == 'sell':
      quantity_to_sell = portfolio.get(symbol, 0)
      print(f"trade_action: sell, quantity_to_sell: {quantity_to_sell}")
      if quantity_to_sell > 0:
        capital += quantity_to_sell * current_price
        portfolio[symbol] = 0

  # Calculate total value at the end of the period
  portfolio_value = sum(portfolio[symbol] *
                        (symbol_data[symbol]['Close'].
                         iloc[-1] if symbol_data[symbol] is not None else 0)
                        for symbol in portfolio)
  total_value = capital + portfolio_value
  return capital, total_value, portfolio_value
