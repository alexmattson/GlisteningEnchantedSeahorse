import os

from openai import AsyncOpenAI

from testing_config import TESTING_SENTIMENT
from dev.data import test_sentiment_data

openai_api_key = os.environ['OPENAI_API_KEY']

# Set up the OpenAI API
client = AsyncOpenAI(api_key=openai_api_key)


def update_company_sentiment(company_ticker, sentiment_score, sentiment_data):
  # Extract the main ticker symbol without any descriptions or text in parentheses
  normalized_ticker = company_ticker.split(' (')[0]

  # If the company_ticker does not exist in the data, it defaults to 0
  current_score = sentiment_data.get(normalized_ticker, 0)
  sentiment_data[normalized_ticker] = current_score + sentiment_score
  return f"Added {sentiment_score} to {normalized_ticker}'s sentiment score. Current score: {sentiment_data[normalized_ticker]}"


async def analyze_sentiments(articles):
  if TESTING_SENTIMENT:
    return test_sentiment_data

  sentiment_data = {}
  for article in articles:
    analysis = await analyze_sentiment(article, sentiment_data)
    if analysis is not None:
      print(f"Article: {article['title']}\nAnalysis: {analysis}\n\n")
  return sentiment_data


async def analyze_sentiment(article, sentiment_data):
  print(f"article: {article}")
  prompt = f"Read the following article and identify any publicly traded companies mentioned in the text. For each company identified, evaluate the sentiment expressed towards the company in the article on a scale from +10 (extremely positive) to -10 (extremely negative). Format your response as 'TICKER: SENTIMENT' for each company with no other text. If no publicly traded companies are mentioned, respond with 'No Company Found'. Article: {article['content']}"
  response = await client.chat.completions.create(
      model="gpt-4",
      messages=[{
          "role": "system",
          "content": "You are a helpful assistant."
      }, {
          "role": "user",
          "content": prompt
      }])

  openai_response = response.choices[0].message.content if response.choices[
      0].message.content else "No Company Found"

  if openai_response == "No Company Found":
    # Handling the case where no company is found explicitly
    return openai_response
  else:
    # Otherwise, parse the company ticker and sentiment
    try:
      companies_data = openai_response.split("\n")
      update_response = ''
      for company_data in companies_data:
        company_ticker, sentiment_value = company_data.split(": ")
        sentiment_score = float(sentiment_value)
        sentiment_update = update_company_sentiment(company_ticker,
                                                    sentiment_score,
                                                    sentiment_data)
        update_response = sentiment_update + '\n' + update_response
      return update_response
    except ValueError:
      # Handle cases where parsing fails
      print(f"An error occurred with OpenAI response: {openai_response}")
      return None
