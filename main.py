from flask import Flask, jsonify
from google_play_scraper import Sort, reviews
from textblob import TextBlob
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# Parâmetros
APP_ID = "com.google.android.youtube"  # substitua pelo ID do app desejado
DAYS = 30
LIMIT = 100  # número máximo de avaliações para buscar

# Função de análise de sentimentos com TextBlob
def classify_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.1:
        sentiment = "positivo"
    elif polarity < -0.1:
        sentiment = "negativo"
    else:
        sentiment = "neutro"
    return sentiment, polarity

# Rota raiz
@app.route("/")
def index():
    return "✅ API rodando — use /get-reviews ou /backfill"

# Rota para buscar e analisar avaliações recentes
@app.route("/get-reviews")
def get_reviews():
    result, _ = reviews(
        APP_ID,
        lang="pt",
        country="br",
        sort=Sort.NEWEST,
        count=LIMIT
    )

    processed = []
    for r in result:
        sentiment, polarity = classify_sentiment(r["content"])
        processed.append({
            "userName": r["userName"],
            "score": r["score"],
            "content": r["content"],
            "at": r["at"].isoformat(),
            "sentiment": sentiment,
            "polarity": polarity
        })

    return jsonify(processed)

# Rota para avaliações mais antigas (simulando backfill)
@app.route("/backfill")
def backfill():
    cutoff = datetime.now(pytz.UTC) - timedelta(days=DAYS)

    result, _ = reviews(
        APP_ID,
        lang="pt",
        country="br",
        sort=Sort.NEWEST,
        count=LIMIT
    )

    filtered = []
    for r in result:
        if r["at"] < cutoff:
            sentiment, polarity = classify_sentiment(r["content"])
            filtered.append({
                "userName": r["userName"],
                "score": r["score"],
                "content": r["content"],
                "at": r["at"].isoformat(),
                "sentiment": sentiment,
                "polarity": polarity
            })

    return jsonify(filtered)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
