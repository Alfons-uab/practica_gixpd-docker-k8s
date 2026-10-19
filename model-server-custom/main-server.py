import os

import joblib
from flask import Flask, request


MODEL_PATH = os.environ["MODEL_PATH"]

app = Flask(__name__)


@app.route("/")
def model_documentation():
    return """
    <h1>Welcome to custom Decision Tree prediction model</h1>

    <p>Please use our API:</p>
    <p>curl localhost:8000/model?minutes=5</p>
    """


@app.route("/model")
def model():
    minutes = request.args.get("minutes")

    trained_model = joblib.load(MODEL_PATH)

    prediction = trained_model.predict([[float(minutes)]])[0]

    return {"spent": float(prediction)}
