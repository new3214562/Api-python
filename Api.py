from flask import Flask, jsonify

app = Flask(__name__)

products = [
    {"id": 1, "name": "สคริปต์ Python คำนวณภาษี", "description": "ช่วยคำนวณ VAT 7%", "price": 100},
    {"id": 2, "name": "บอท Telegram ด้วย Python", "description": "บอทแจ้งเตือนข่าวสาร", "price": 200}
]

@app.route('/products', methods=['GET'])
def get_products():
    return jsonify(products)

if __name__ == '__main__':
    app.run(debug=True)
