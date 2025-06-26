import os
import requests
from flask import Flask, jsonify
from google_play_scraper import reviews, Sort
from datetime import datetime, timedelta

app = Flask(__name__)
last_review_id = None

# Seu token da Hugging Face (definido como variável de ambiente no Render)
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_MODEL = "nlptown/bert-base-multilingual-uncased-sentiment"

def classify_sentiment(text):
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN ausente no ambiente")
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": text}
    
    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and len(data) > 0 and "label" in data[0]:
            stars = int(data[0]["label"].split()[0])
        else:
            app.logger.error(f"Resposta inesperada da Hugging Face: {data}")
            return "erro", 0
        
    except Exception as e:
        app.logger.error(f"Erro na Inference API: {e}")
        return "erro", 0

    if stars <= 2:
        return "negativo", stars
    elif stars == 3:
        return "neutro", stars
    else:
        return "positivo", stars

@app.route('/')
def home():
    return "✅ API rodando — use /get-reviews ou /backfill", 200

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
            # r["at"] é naïve em UTC, assim como cutoff
            if r["at"] < cutoff:
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
        if r["reviewId"] == last_review_id:
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
        last_review_id = result[0]["reviewId"]

    return jsonify(output)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
