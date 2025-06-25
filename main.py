from flask import Flask, jsonify
from google_play_scraper import reviews, Sort
from transformers import pipeline
from datetime import datetime, timedelta
import os

app = Flask(__name__)
last_review_id = None

# Inicializa o pipeline de análise de sentimento do Hugging Face
sentiment_model = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")

def classify_sentiment(text):
    prediction = sentiment_model(text)[0]
    stars = int(prediction['label'].split()[0])  # Nota de 1 a 5

    if stars <= 2:
        return "negativo", stars
    elif stars == 3:
        return "neutro", stars
    else:
        return "positivo", stars

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

            sentiment, polarity = classify_sentiment(r["content"])

            all_reviews.append({
                "reviewId": r["reviewId"],
                "date": r["at"].isoformat(),
                "content": r["content"],
                "sentiment": sentiment,
                "polarity": polarity
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

        sentiment, polarity = classify_sentiment(r["content"])

        output.append({
            "reviewId": r["reviewId"],
            "date": r["at"].isoformat(),
            "content": r["content"],
            "sentiment": sentiment,
            "polarity": polarity
        })

    if result:
        last_review_id = result[0]['reviewId']

    return jsonify(output)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
