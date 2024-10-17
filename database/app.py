import logging
import os
import threading
import time

import pyodbc
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from google.cloud import pubsub_v1

app = Flask(__name__)
CORS(app)

# Configure logging with method name
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')

# SQL Server connection details from environment variables
server = '34.27.168.219'
database = 'myappdb'
username = 'sqlserver'
password = 'Tn50@4669'


# Connection string
# Updated connection string with connection pooling parameters
conn_str = (
    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
    f'SERVER={server};'
    f'DATABASE={database};'
    f'UID={username};'
    f'PWD={password};'
    f'Timeout=30;'
    f'Pooling=True;'
    f'MinPoolSize=5;'  # Minimum number of connections in the pool
    f'MaxPoolSize=20;'  # Maximum number of connections in the pool
)


def get_connection():
    """Gets a connection from the connection pool."""
    try:
        return pyodbc.connect(conn_str)
    except pyodbc.Error as e:
        logging.error(f"Connection pool error: {e}")
        return None


def check_database_connection():
    """Checks the database connection."""
    try:
        conn = get_connection()
        if conn:
            conn.close()
            return True
    except pyodbc.Error as e:
        logging.error(f"Database connection error: {e}")
    return False


def save_message_to_db(message):
    """Saves the received message to the database with retry logic."""
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        conn = get_connection()  # Get a connection from the pool
        if conn is None:
            logging.error("Failed to obtain a connection from the pool.")
            retry_count += 1
            time.sleep(2)  # Wait before retrying
            continue

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO pubsub_messages (message) VALUES (?)", (message,))
            conn.commit()
            logging.info(f"Message saved to DB: {message}")
            return  # Exit the function after successful insert
        except pyodbc.Error as e:
            logging.error(f"Database error: {e}")
            retry_count += 1
            time.sleep(2)  # Wait before retrying
        finally:
            if cursor:
                cursor.close()
            conn.close()  # Return the connection to the pool

    logging.error("Failed to save message to DB after multiple attempts.")


def callback(message):
    """Callback function to handle incoming messages."""
    decoded_message = message.data.decode('utf-8')
    logging.info(f"Received message: {decoded_message}")
    save_message_to_db(decoded_message)
    message.ack()  # Acknowledge the message


def listen_for_messages():
    """Listen for messages from the Pub/Sub subscription."""
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path("iron-wave-434723-e4", "my-sub")

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    logging.info(f"Listening for messages on {subscription_path}...\n")

    # Keep the main thread alive to listen for messages
    try:
        streaming_pull_future.result()
    except Exception as e:
        logging.error(f"Listening failed: {e}")


@app.route('/')
def home():
    """Home route that shows database connection status."""
    if check_database_connection():
        message = "Database connection successful, DB up and running."
    else:
        message = "Database connection failed. Please check the configuration."
    return jsonify(message=message)


@app.route('/validate', methods=['POST'])
def validate_login():
    """Validates the login credentials."""
    username = request.json.get('username')
    password = request.json.get('password')

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Query to check if the username and password match
        cursor.execute("SELECT * FROM Login WHERE username = ? AND password = ?", (username, password))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify(valid=(result is not None))

    except pyodbc.Error as e:
        logging.error(f"Database error: {e}")
        return jsonify(error=str(e)), 500


@app.route('/logins', methods=['GET'])
def get_logins():
    """Fetches all login entries from the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Query to get all users from the Login table
        cursor.execute("SELECT username, password FROM Login")  # Select both username and password
        logins = cursor.fetchall()

        cursor.close()
        conn.close()

        # Format the data to return as JSON
        login_list = [{'username': row[0], 'password': row[1]} for row in logins]  # Convert to a list of dicts
        return jsonify(login_list)

    except pyodbc.Error as e:
        logging.error(f"Database error: {e}")
        return jsonify(error=str(e)), 500


@app.route('/messages', methods=['GET'])
def get_messages():
    """Route to retrieve messages from the database."""
    messages = []
    try:
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pubsub_messages")
            rows = cursor.fetchall()
            for row in rows:
                messages.append({"id": row[0], "message": row[1]})  # Adjust based on your table structure
            cursor.close()
            conn.close()
    except pyodbc.Error as e:
        logging.error(f"Error retrieving messages: {e}")
        return jsonify({"error": "Failed to retrieve messages"}), 500
    return jsonify(messages=messages)


@app.route('/message', methods=['POST'])
def create_message():
    """Route to save a new message to the database."""
    data = request.get_json()
    if 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    message = data['message']
    save_message_to_db(message)
    return jsonify({"success": "Message saved successfully"}), 201


@app.route('/connection')
def connection_status():
    """Checks and renders connection status."""
    if check_database_connection():
        message = "Connection successful"
    else:
        message = "Connection failed"

    return render_template('status.html', message=message)


@app.route('/status', methods=['GET'])
def status():
    """Route to check the status of the application."""
    return jsonify({"status": "Application is running"}), 200


if __name__ == '__main__':
    if check_database_connection():
        logging.info("Database connection successful, DB up and running.")
    threading.Thread(target=listen_for_messages).start()  # Start the listener in a separate thread
    app.run(host='0.0.0.0', port=5001, debug=True)