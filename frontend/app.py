import flask
import requests
import pyodbc
import os

app = flask.Flask(__name__)

# Use environment variables for sensitive data
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')  # Make sure to use an actual secret in production

# SQL Server connection details
server = os.getenv('DB_SERVER', '34.27.168.219')  # IP of Cloud SQL instance with port
database = os.getenv('DB_NAME', 'myappdb')  # Database name
username = os.getenv('DB_USER', 'sqlserver')  # SQL Server username
password = os.getenv('DB_PASSWORD', 'Tn50@4669')  # SQL Server password

# Connection string
conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
print("Connection String:", conn_str)

def get_all_logins():
    """Fetches all login entries from the database."""
    try:
        # Connect to SQL Server
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print("Connected to the database")

        # Query to fetch all login entries
        cursor.execute("SELECT * FROM Login")
        results = cursor.fetchall()

        # Close the connection
        cursor.close()
        conn.close()

        return results

    except pyodbc.Error as e:
        print(f"Database error: {e}")
        return []  # Return an empty list if there's an error

@app.route('/')
def index():
    return flask.render_template('login.html')  # Render the login form

@app.route('/login', methods=['POST'])
def login():
    username = flask.request.form['username']
    password = flask.request.form['password']

    try:
        # Make POST request to the validation service with a timeout
        response = requests.post(
            '/validate',
            json={'username': username, 'password': password},
            timeout=10  # Set a 10-second timeout
        )

        # Check if the response was successful and JSON formatted
        response.raise_for_status()

        # Ensure the response is JSON before parsing
        if response.headers.get('Content-Type') == 'application/json':
            response_data = response.json()
            print(f"Response from database service: {response_data}")

            # Check if login is valid
            if response_data.get('valid'):
                flask.flash('Login successful!', 'success')
                return flask.redirect(flask.url_for('welcome'))  # Redirect to the welcome page
            else:
                flask.flash('Invalid credentials, please try again.', 'danger')
                return flask.redirect(flask.url_for('index'))  # Reload the login page with an error

        else:
            flask.flash('Unexpected response format from the server.', 'danger')
            return flask.redirect(flask.url_for('index'))  # Handle unexpected response format

    except requests.exceptions.Timeout:
        flask.flash('The request timed out. Please try again later.', 'danger')
        return flask.redirect(flask.url_for('index'))

    except requests.exceptions.ConnectionError:
        flask.flash('Failed to connect to the server. Please check your network or server status.', 'danger')
        return flask.redirect(flask.url_for('index'))

    except requests.exceptions.RequestException as e:
        flask.flash(f'An error occurred: {str(e)}', 'danger')
        return flask.redirect(flask.url_for('index'))

@app.route('/welcome')
def welcome():
    return "Welcome to your dashboard!"  # This is a placeholder page for successful login

@app.route('/logins', methods=['GET'])
def display_logins():
    """Fetches and displays all login entries."""
    logins = get_all_logins()
    return flask.render_template('logins.html', logins=logins)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)  # Run the UserInterface microservice on port 5000
