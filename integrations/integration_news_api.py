import os

import requests

news_api_key = os.environ['NEWS_API_KEY']

def fetch_news(query='Business', language='en', from_date=None, to_date=None):
  url = f"https://newsapi.org/v2/everything?q={query}&language={language}&apiKey={news_api_key}"

  # Add time period to the API request if provided
  if from_date:
    url += f"&from={from_date}"
  if to_date:
    url += f"&to={to_date}"

  response = requests.get(url)
  if response.status_code == 200:  # Success
    articles = response.json()['articles']
    print(f"Number of articles: {len(articles)}")
    return articles
  else:
    raise Exception(f"Error fetching news: {response.status_code} - {response.text}")