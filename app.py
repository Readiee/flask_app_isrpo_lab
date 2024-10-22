from flask import Flask, jsonify, request, abort, make_response
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
import uuid
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
CORS(app)

swagger_url = "/swaggerui"
swaggerui_blueprint = get_swaggerui_blueprint(
    swagger_url,
    f"{swagger_url}/swagger.json",
    config={"app_name": "Library API"}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=swagger_url)

# Prometheus Metrics
BOOKS_API_REQUESTS = Counter('books_api_requests_total', 'Total API requests for Books', ['method', 'endpoint'])

@app.route(f'{swagger_url}/swagger.json')
def swagger_json():
    with open('oas.yaml', 'r') as file:
        swagger_json = file.read()
    response = make_response(swagger_json)
    response.headers['Content-Type'] = 'application/yaml'
    return response

# In-memory book storage
books = {}

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# API Endpoints with metrics tracking
@app.route('/books', methods=['GET'])
def get_books():
    """Получить список всех книг"""
    BOOKS_API_REQUESTS.labels(method='GET', endpoint='/books').inc()
    return jsonify(list(books.values())), 200

@app.route('/books', methods=['POST'])
def add_book():
    """Добавить новую книгу"""
    BOOKS_API_REQUESTS.labels(method='POST', endpoint='/books').inc()
    data = request.get_json()
    if 'title' not in data or 'author' not in data or 'genre' not in data or 'year' not in data:
        abort(400, description="Invalid input")

    book_id = str(uuid.uuid4())
    book = {
        'id': book_id,
        'title': data.get('title'),
        'author': data.get('author'),
        'genre': data.get('genre'),
        'year': data.get('year')
    }
    books[book_id] = book
    return jsonify(book), 201

@app.route('/books/<book_id>', methods=['GET'])
def get_book(book_id):
    """Получить книгу по ID"""
    BOOKS_API_REQUESTS.labels(method='GET', endpoint='/books/<book_id>').inc()
    book = books.get(book_id)
    if not book:
        abort(404, description="Book not found")
    return jsonify(book), 200

@app.route('/books/<book_id>', methods=['PUT'])
def update_book(book_id):
    """Обновить информацию о книге"""
    BOOKS_API_REQUESTS.labels(method='PUT', endpoint='/books/<book_id>').inc()
    if book_id not in books:
        abort(404, description="Book not found")

    data = request.get_json()
    if 'title' not in data or 'author' not in data or 'genre' not in data or 'year' not in data:
        abort(400, description="Invalid input")

    books[book_id] = {
        'id': book_id,
        'title': data['title'],
        'author': data['author'],
        'genre': data['genre'],
        'year': data['year']
    }
    return jsonify(books[book_id]), 200

@app.route('/books/<book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Удалить книгу по ID"""
    BOOKS_API_REQUESTS.labels(method='DELETE', endpoint='/books/<book_id>').inc()
    if book_id not in books:
        abort(404, description="Book not found")

    del books[book_id]
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
