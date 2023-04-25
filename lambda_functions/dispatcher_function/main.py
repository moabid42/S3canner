import os
import json
import boto3
import logging

from typing import Optional, List

# Configure logger.
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

# Setup boto3 clients.
LAMBDA_CLIENT = boto3.client('lambda')
SQS_CLIENT = boto3.client('sqs')

# Constants
WAIT_TIME_SECONDS               = 10
BATCH_SIZE                      = 10    # SQS maximum allowable
SQS_QUEUE_URL                   = os.getenv('SQS_QUEUE_URL')
MAX_DISPATCHES                  = int(os.getenv('MAX_DISPATCHES'))
ANALYZE_LAMBDA_NAME             = os.getenv('ANALYZE_LAMBDA_NAME')
ANALYZE_LAMBDA_QUALIFER         = os.getenv('ANALYZE_LAMBDA_QUALIFIER')
SECRETS_ANALYZE_LAMBDA_NAME     = os.getenv('SECRETS_ANALYZE_LAMBDA_NAME')
SECRETS_ANALYZE_LAMBDA_QUALIFER = os.getenv('SECRETS_ANALYZE_LAMBDA_QUALIFIER')
WAIT_TIME_SECONDS       = 10    # Maximum amount of time to hold a 
                                # receive_message connection open.

# Delete a batch of SQS messages
def delete_sqs_messages(queue_url: str, receipt_handles: List[str]) -> None:
    SQS_CLIENT.delete_message_batch(
        QueueUrl        = queue_url,
        Entries         = [{'Id': str(index), 'ReceiptHandle': receipt} for index, receipt in enumerate(receipt_handles)]
    )


# Invoke an analysis Lambda asynchronously
def invoke_analysis_lambda(payload: dict) -> None:
    LAMBDA_CLIENT.invoke(
        FunctionName    = ANALYZE_LAMBDA_NAME,
        InvocationType  = 'Event',
        Payload         = json.dumps(payload),
        Qualifier       = ANALYZE_LAMBDA_QUALIFER
    )

# Invoke an analysis Lambda asynchronously
def invoke_secrets_analysis_lambda(payload: dict) -> None:
    LAMBDA_CLIENT.invoke(
        FunctionName    = SECRETS_ANALYZE_LAMBDA_NAME,
        InvocationType  = 'Event',
        Payload         = json.dumps(payload),
        Qualifier       = SECRETS_ANALYZE_LAMBDA_QUALIFER
    )

# Receive a message from the SQS service
def receive_message_sqs(queue_url: str, wait_time_seconds: int) -> Optional[dict]:
    messages = SQS_CLIENT.receive_message(
        QueueUrl = queue_url,
        MaxNumberOfMessages = BATCH_SIZE,
        WaitTimeSeconds = wait_time_seconds
    )

"""Convert a batch of SQS messages into an analysis Lambda payload.

Args:
    sqs_messages: [dict] Response from SQS.receive_message. Expected format:
        {
            'Records': [
                {
                    ...
                    'body': '{"Records": [{"s3": {"object": {"key": "..."}}}, ...]}',
                    'receiptHandle': '...'
                },
                ...
            ]
        }
        There may be multiple SQS messages, each of which may contain multiple S3 keys.
        Each message body is a JSON string, in the format of an S3 object added event.

Returns:
    [dict] Non-empty payload for the analysis Lambda function in the following format:
    {
        'S3Objects': ['key1', 'key2', ...],
        'SQSReceipts': ['receipt1', 'receipt2', ...]
    }
    [None] if the SQS message was empty or invalid."""
def _build_payload(sqs_messages):
    if 'Records' not in sqs_messages:
        LOGGER.info('No SQS messages found')
        return

    # The payload consists of S3 object keys and SQS receipts (consumers will delete the message).
    payload = {'S3Objects': [], 'SQSReceipts': []}
    invalid_receipts = []  # List of invalid SQS message receipts to delete.
    for msg in sqs_messages['Records']:
        try:
            payload['S3Objects'].extend(
                record['s3']['object']['key'] for record in json.loads(msg['body'])['Records'])
            payload['SQSReceipts'].append(msg['receiptHandle'])
        except (KeyError, ValueError):
            LOGGER.warning('Invalid SQS message body: %s', msg['body'])
            invalid_receipts.append(msg['receiptHandle'])
            continue

    # Remove invalid messages from the SQS queue.
    if invalid_receipts:
        LOGGER.warning('Removing %d invalid messages', len(invalid_receipts))
        # SQS_CLIENT.delete_message_batch(
        #     QueueUrl=os.environ['SQS_QUEUE_URL'],
        #     Entries=[{'Id': str(index), 'ReceiptHandle': receipt}
        #              for index, receipt in enumerate(invalid_receipts)]
        # )

    # If there were no valid S3 objects, return None.
    if not payload['S3Objects']:
        return

    return payload


def dispatch_lambda_handler(event, lambda_context) -> int:
    # Validate the SQS message and construct the payload.
    payload = _build_payload(event)
    LOGGER.info('Sending %d object(s) to an analyzer: %s',
                len(payload['S3Objects']), json.dumps(payload['S3Objects']))

    # Asynchronously invoke an analyzer lambda.
    invoke_analysis_lambda(payload)

    LOGGER.info('Sending %d object(s) to an analyzer: %s',
        len(payload['S3Objects']), json.dumps(payload['S3Objects']))

    # Asynchronously invoke an secrets analyzer lambda.
    invoke_secrets_analysis_lambda(payload)

    # delete_sqs_messages(os.environ['SQS_QUEUE_URL'], payload['S3Objects'])

    LOGGER.info('Invoked %d total analyzers', 1)
    return 1
