import os
import boto3
from dotenv import load_dotenv

# Load the environment variables from the .env file in the specified directory
load_dotenv(dotenv_path='../.env')

# Get the SQS queue URL from the environment variables
queue_url = os.getenv('SQS_URL')

# Create an SQS client
sqs = boto3.client('sqs')

# Receive messages from the queue in batches of up to 10
while True:
    response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=10
    )

    # If there are no messages left, break out of the loop
    if 'Messages' not in response:
        break

    # Delete all messages in the batch
    entries = [{'Id': message['MessageId'], 'ReceiptHandle': message['ReceiptHandle']} for message in response['Messages']]
    sqs.delete_message_batch(QueueUrl=queue_url, Entries=entries)

print('All messages have been deleted from the queue.')
