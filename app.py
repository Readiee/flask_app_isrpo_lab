from flask import Flask, jsonify, request, abort, make_response
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
import uuid
import random
import time
import logging
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

app = Flask(__name__)
CORS(app)

# Swagger setup
swagger_url = "/swaggerui"
swaggerui_blueprint = get_swaggerui_blueprint(
    swagger_url,
    f"{swagger_url}/swagger.json",
    config={"app_name": "Library API"}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=swagger_url)

# Prometheus Metrics
BOOKS_API_REQUESTS = Counter('books_api_requests_total', 'Total API requests for Books', ['method', 'endpoint'])

# Logging into file
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# OpenTelemetry configuration
resource = Resource(attributes={"service.name": "flask-library-service"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
otlp_exporter = OTLPSpanExporter(endpoint="tempo:4317", insecure=True)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

# Instrument Flask app with OpenTelemetry
FlaskInstrumentor().instrument_app(app)

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

# Example trace spans with delay and errors
@app.route('/books', methods=['GET'])
def get_books():
    with tracer.start_as_current_span("get_books") as span:
        delay = random.uniform(0.1, 0.5)
        time.sleep(delay)  # Random delay for testing
        span.set_attribute("delay", delay)
        if random.choice([True, False]):
            span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, "Randomly triggered error"))
            abort(500, description="Randomly triggered error for tracing")
        logger.info("GET /books request received")
        BOOKS_API_REQUESTS.labels(method='GET', endpoint='/books').inc()
        return jsonify(list(books.values())), 200

@app.route('/books', methods=['POST'])
def add_book():
    with tracer.start_as_current_span("add_book") as span:
        data = request.get_json()
        book_id = str(uuid.uuid4())
        book = {
            'id': book_id,
            'title': data.get('title'),
            'author': data.get('author'),
            'genre': data.get('genre'),
            'year': data.get('year')
        }
        logger.info("POST /books request received")
        BOOKS_API_REQUESTS.labels(method='POST', endpoint='/books').inc()
        books[book_id] = book
        return jsonify(book), 201

@app.route('/books/<book_id>', methods=['GET'])
def get_book(book_id):
    with tracer.start_as_current_span("get_book_by_id") as span:
        logger.info(f"GET /books/{book_id} request received")
        span.set_attribute("book_id", book_id)
        BOOKS_API_REQUESTS.labels(method='GET', endpoint='/books/<book_id>').inc()
        book = books.get(book_id)
        if not book:
            span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, "Book not found"))
            abort(404, description="Book not found")
        return jsonify(book), 200

@app.route('/books/<book_id>', methods=['PUT'])
def update_book(book_id):
    with tracer.start_as_current_span("update_book") as span:
        logger.info(f"PUT /books/{book_id} request received")
        span.set_attribute("book_id", book_id)
        BOOKS_API_REQUESTS.labels(method='PUT', endpoint='/books/<book_id>').inc()
        if book_id not in books:
            span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, "Book not found"))
            abort(404, description="Book not found")

        data = request.get_json()
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
    with tracer.start_as_current_span("delete_book") as span:
        logger.info(f"DELETE /books/{book_id} request received")
        span.set_attribute("book_id", book_id)
        BOOKS_API_REQUESTS.labels(method='DELETE', endpoint='/books/<book_id>').inc()
        if book_id not in books:
            span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, "Book not found"))
            abort(404, description="Book not found")

        del books[book_id]
        return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
