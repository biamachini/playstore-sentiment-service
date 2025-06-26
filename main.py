from flask import Flask, jsonify
from google_play_scraper import reviews, Sort
from textblob import TextBlob
from leia import SentimentIntensityAnalyzer as LeiaSentimentAnalyzer
from datetime import datetime, timedelta
import os

app = Flask(__name__)
last_review_id = None

# Inicializa o analisador LeIA (fora da função pra reaproveitar)
leia_analyzer = LeiaSentimentAnalyzer()

# Variável para controlar qual analisador usar: 'leia' ou 'textblob'
ANALYZER = 'leia'  # Troque para 'textblob' para usar o TextBlob normalmente

def analyze_sentiment_leia(text):
    result = leia_analyzer.polarity_scores(text)
    compound = result.get("compound", 0)
    if compound > 0.1:
        sentiment = "positivo"
    elif compound < -0.1:
        sentiment = "negativo"
    else:
        sentiment = "neutro"
    return {"sentiment": sentiment, "polarity": compound, "source": "leia"}

def analyze_sentiment_textblob(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.1:
        sentiment = "positivo"
    elif polarity < -0.1:
        sentiment = "negativo"
    else:
        sentiment = "neutro"
    return {"sentiment": sentiment, "polarity": polarity, "source": "textblob"}

def analyze_sentiment(text):
    if ANALYZER == 'leia':
        try:
            return analyze_sentiment_leia(text)
        except Exception as e:
            print(f"Erro LeIA: {e}. Usando TextBlob como fallback.")
            return analyze_sentiment_textblob(text)
    else:
        return analyze_sentiment_textblob(text)

@app.route('/backfill')
def backfill():
    APP_ID = 'co.stone.banking.mobile.flagship'
    DAYS = 30
    cutoff = datetime.utcnow() - timedelta(days=DAYS)
    token = None
    all_reviews = []

    while True:
        result, token = reviews(
            APP_ID,
            lang='pt_BR',
            sort=Sort.NEWEST,
            count=100,
            continuation_token=token
        )
        for r in result:
            if r['at'] < cutoff:
                return jsonify(all_reviews)

            sentiment_data = analyze_sentiment(r["content"])

            all_reviews.append({
                "reviewId": r["reviewId"],
                "date": r["at"].isoformat(),
                "score": r["score"],  # ✅ Campo adicionado
                "content": r["content"],
                "sentiment": sentiment_data["sentiment"],
                "polarity": sentiment_data["polarity"],
                "analyzer": sentiment_data["source"]
            })
        if not token:
            break

    return jsonify(all_reviews)

@app.route('/get-reviews')
def get_reviews():
    global last_review_id
    APP_ID = 'co.stone.banking.mobile.flagship'

    result, _ = reviews(
        APP_ID,
        lang='pt_BR',
        sort=Sort.NEWEST,
        count=20
    )

    output = []
    for r in result:
        if r['reviewId'] == last_review_id:
            break

        sentiment_data = analyze_sentiment(r["content"])

        output.append({
            "reviewId": r["reviewId"],
            "date": r["at"].isoformat(),
            "score": r["score"],  # ✅ Campo adicionado aqui também
            "content": r["content"],
            "sentiment": sentiment_data["sentiment"],
            "polarity": sentiment_data["polarity"],
            "analyzer": sentiment_data["source"]
        })

    if result:
        last_review_id = result[0]['reviewId']

    return jsonify(output)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
