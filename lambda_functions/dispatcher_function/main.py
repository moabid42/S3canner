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
WAIT_TIME_SECONDS       = 10
BATCH_SIZE              = 10    # SQS maximum allowable
SQS_QUEUE_URL           = os.getenv('SQS_QUEUE_URL')
MAX_DISPATCHES          = int(os.getenv('MAX_DISPATCHES'))
ANALYZE_LAMBDA_NAME     = os.getenv('ANALYZE_LAMBDA_NAME')
ANALYZE_LAMBDA_QUALIFER = os.getenv('ANALYZE_LAMBDA_QUALIFIER')
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
            'Messages': [
                {
                    'Body': '{"Records": [{"s3": {"object": {"key": "..."}}}, ...]}',
                    'ReceiptHandle': '...'
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
    if 'Messages' not in sqs_messages:
        LOGGER.info('No SQS messages found')
        return

    # The payload consists of S3 object keys and SQS receipts (consumers will delete the message).
    payload = {'S3Objects': [], 'SQSReceipts': []}
    invalid_receipts = []  # List of invalid SQS message receipts to delete.
    for msg in sqs_messages['Messages']:
        try:
            payload['S3Objects'].extend(
                record['s3']['object']['key'] for record in json.loads(msg['Body'])['Records'])
            payload['SQSReceipts'].append(msg['ReceiptHandle'])
        except (KeyError, ValueError):
            LOGGER.warning('Invalid SQS message body: %s', msg['Body'])
            invalid_receipts.append(msg['ReceiptHandle'])
            continue

    # Remove invalid messages from the SQS queue.
    if invalid_receipts:
        LOGGER.warning('Removing %d invalid messages', len(invalid_receipts))
        SQS_CLIENT.delete_message_batch(
            QueueUrl=os.environ['SQS_QUEUE_URL'],
            Entries=[{'Id': str(index), 'ReceiptHandle': receipt}
                     for index, receipt in enumerate(invalid_receipts)]
        )

    # If there were no valid S3 objects, return None.
    if not payload['S3Objects']:
        return

    return payload


def dispatch_lambda_handler(_, lambda_context) -> int:
    invocations = 0

    queue_attributes = SQS_CLIENT.get_queue_attributes(
        QueueUrl=os.environ['SQS_QUEUE_URL'],
        AttributeNames=['ApproximateNumberOfMessages']
    )
    num_messages = int(queue_attributes['Attributes']['ApproximateNumberOfMessages'])

    LOGGER.info('The number of messages is %d', num_messages)

    # The maximum amount of time needed in the execution loop.
    # This allows us to dispatch as long as possible while still staying under the time limit.
    # We need time to wait for sqs messages as well as a few seconds (e.g. 3) to process them.
    loop_execution_time_ms = (WAIT_TIME_SECONDS + 3) * 1000

    # Poll for messages until we either reach our invocation limit or run out of time.
    while (num_messages > invocations and 
           invocations < int(os.environ['MAX_DISPATCHES']) and
           lambda_context.get_remaining_time_in_millis() > loop_execution_time_ms):
        # Long-polling of SQS: Wait up to 10 seconds and receive up to 10 messages.
        sqs_messages = SQS_CLIENT.receive_message(
            QueueUrl=os.environ['SQS_QUEUE_URL'],
            MaxNumberOfMessages=10,  # SQS maximum allowable.
            WaitTimeSeconds=WAIT_TIME_SECONDS
        )

        # Validate the SQS message and construct the payload.
        payload = _build_payload(sqs_messages)
        if not payload:
            continue
        LOGGER.info('Sending %d object(s) to an analyzer: %s',
                    len(payload['S3Objects']), json.dumps(payload['S3Objects']))

        # Asynchronously invoke an analyzer lambda.
        invoke_analysis_lambda(payload)

        # delete_sqs_messages(os.environ['SQS_QUEUE_URL'], payload['S3Objects'])
        invocations += 1

    LOGGER.info('Invoked %d total analyzers', invocations)
    return invocations
