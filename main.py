import random
import string
import time

from google.cloud import pubsub_v1
import sys
# Configuration
project_id = "iron-wave-434723-e4"
topic_id = "my-topic"

# Create a Publisher client
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_id)

def generate_random_message():
    """Generate a random string message."""
    length = random.randint(1, 5)  # Random length between 10 and 100
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

def publish_messages():
    """Publish random messages to the Pub/Sub topic."""
    while True:
        message = generate_random_message()
        data = message.encode("utf-8")  # Data must be a bytestring
        future = publisher.publish(topic_path, data)
        print(f'Published message: {message}')
        future.result()  # Wait for the publish call to complete
        time.sleep(30)  # Publish every 5 seconds

if __name__ == "__main__":
    publish_messages()
