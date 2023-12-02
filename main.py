import asyncio

from dev.backtesting import run_backtest
from integrations.integration_alpaca import analyze_portfolio
from integrations.integration_news_api import fetch_news
from integrations.integration_openai import analyze_sentiments
from testing_config import BACKTESTING, TESTING_SENTIMENT


async def main():

  if BACKTESTING:
    await run_backtest()
    return

  articles = []
  if not TESTING_SENTIMENT:
    articles = fetch_news()

  sentiment_data = await analyze_sentiments(articles)

  print(sentiment_data)

  # Analyze the portfolio as usual
  analyze_portfolio(sentiment_data)


if __name__ == "__main__":
  asyncio.run(main())
