from flask import Flask, request, jsonify, render_template
from model import predict_fda_code
import os

app = Flask(__name__, static_folder='static')


@app.route('/')
def serve_frontend():
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    event_desc = data.get("event_description")
    prod_id = data.get("product_id")

    if not event_desc or not prod_id:
        return jsonify({"error": "Missing required fields"}), 400

    result = predict_fda_code(event_desc, prod_id)
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
