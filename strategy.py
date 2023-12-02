# Constants to define strategy behavior and thresholds
NEGATIVE_THRESHOLD = 0
LOW_POSITIVE_THRESHOLD = 0
HIGH_POSITIVE_THRESHOLD = 15.0
PERCENTAGE_BUYING_POWER_PER_STOCK = 0.05


def determine_trade_actions(portfolio_symbols, sentiment_data):
  # Generate actions based on sentiment scores
  actions = []
  for symbol, sentiment_score in sentiment_data.items():
    if sentiment_score < NEGATIVE_THRESHOLD:
      if symbol in portfolio_symbols:
        # Decision to sell the shares
        actions.append({'symbol': symbol, 'action': 'sell', 'quantity': 'all'})
    elif LOW_POSITIVE_THRESHOLD <= sentiment_score < HIGH_POSITIVE_THRESHOLD:
      if symbol not in portfolio_symbols:
        # Decision to buy shares with low positive sentiment
        actions.append({
            'symbol': symbol,
            'action': 'buy',
            'quantity': 'low_positive'
        })
    elif sentiment_score >= HIGH_POSITIVE_THRESHOLD:
      # Decision to buy shares with high positive sentiment
      actions.append({
          'symbol': symbol,
          'action': 'buy',
          'quantity': 'high_positive'
      })
  return actions


def calculate_order_quantity(action, buying_power, current_price):
  # Ensure buying_power is a float
  buying_power = float(buying_power)
  allocated_amount = buying_power * PERCENTAGE_BUYING_POWER_PER_STOCK

  if action == 'sell':
    return 'all'  # When selling, the strategy intends to sell all shares
  elif action == 'buy':
    quantity_to_buy = int(
        allocated_amount /
        current_price)  # Calculate the number of shares to buy
    return quantity_to_buy
  return 0  # Default case if neither buy nor sell
