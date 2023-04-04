import os
import json
import boto3
import logging

from typing import List


LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

# Clients
LAMBDA_CLIENT   = boto3.client('lambda')
S3_CLIENT       = boto3.client('s3')
SQS_CLIENT      = boto3.client('sqs')


# Encapsulates a single SQS message (which will contain multiple S3 keys)
class SQSMessage(object):

    def __init__(self, msg_id):
        self._id = msg_id
        self._keys = []

    @property
    def num_keys(self) -> int:
        """Returns [int] the number of keys stored in the SQS message so far."""
        return len(self._keys)

    def add_key(self, key: str) -> None:
        """Add another S3 key (string) to the message."""
        self._keys.append(key)

    def sqs_entry(self) -> dict:
        # The message body matches the structure of an S3 added event. This gives all
        # messages in the SQS the same format and enables the dispatcher to parse them consistently.
        return {
            'Id': str(self._id),
            'MessageBody': json.dumps({
                'Records': [{'s3': {'object': {'key': key}}} for key in self._keys]
            })
        }

    def reset(self) -> None:
        # Remove the stored list of S3 keys
        self._keys = []


# Collect groups of S3 keys and batch them into as few SQS requests as possible
class SQSBatcher(object):

    def __init__(self, queue_url: str, objects_per_message: int, messages_per_batch: int = 10):
        # Note that the downstream analyzer Lambdas will each process at most
        #(objects_per_message * messages_per_batch) binaries. The analyzer runtime limit is the
        # ultimate constraint on the size of each batch.
        self._queue_url = queue_url
        self._objects_per_message = objects_per_message
        self._messages_per_batch = messages_per_batch

        self._messages = [SQSMessage(i) for i in range(messages_per_batch)]
        self._msg_index = 0  # The index of the SQS message where keys are currently being added.

        # The first and last keys added to this batch.
        self._first_key = None
        self._last_key = None

    # Group keys into messages and make a single batch request.
    def _send_batch(self) -> None:
        LOGGER.info('Sending SQS batch of %d keys: %s ... %s',
                    sum(msg.num_keys for msg in self._messages), self._first_key, self._last_key)
        response = SQS_CLIENT.send_message_batch(
            QueueUrl=self._queue_url,
            Entries=[msg.sqs_entry() for msg in self._messages if msg.num_keys > 0]
        )

        failures = response.get('Failed', [])
        if failures:
            for failure in failures:
                LOGGER.error('Unable to enqueue S3 key %s: %s',
                             self._messages[int(failure['Id'])], failure['Message'])
            boto3.client('cloudwatch').put_metric_data(Namespace='BinaryAlert', MetricData=[{
                'MetricName': 'BatchEnqueueFailures',
                'Value': len(failures),
                'Unit': 'Count'
            }])

        for msg in self._messages:
            msg.reset()
        self._first_key = None

    def add_key(self, key) -> None:
        # Add a new S3 key [string] to the message batch and send to SQS if necessary.
        if not self._first_key:
            self._first_key = key
        self._last_key = key

        msg = self._messages[self._msg_index]
        msg.add_key(key)

        # If the current message is full, move to the next one.
        if msg.num_keys == self._objects_per_message:
            self._msg_index += 1

            # If all of the messages are full, fire off to SQS.
            if self._msg_index == self._messages_per_batch:
                self._send_batch()
                self._msg_index = 0

    def flash(self) -> None:
        """After all messages have been added, send the remaining as a last batch to SQS."""
        if self._first_key:
            LOGGER.info('flash: sending last batch of keys')
            self._send_batch()


# Enumerates all of the S3 objects in a given bucket.
class S3BucketEnumerator(object):
    def __init__(self, bucket_name, continuation_token=None):
        self.bucket_name: str = bucket_name
        self.continuation_token: str = continuation_token
        self.finished = False  # Have we finished enumerating all of the S3 bucket?

    def next_page(self) -> List[str]:
        # Get the next page of S3 objects.
        if self.continuation_token:
            response = S3_CLIENT.list_objects_v2(
                Bucket=self.bucket_name, ContinuationToken=self.continuation_token)
        else:
            response = S3_CLIENT.list_objects_v2(Bucket=self.bucket_name)

        self.continuation_token = response.get('NextContinuationToken')
        if not response['IsTruncated']:
            self.finished = True

        return [obj['Key'] for obj in response['Contents']]


def batch_lambda_handler(event, lambda_context) -> int:
    LOGGER.info('Invoked with event %s', json.dumps(event))
    LOGGER.info('The SQS Queue Url is : %s', os.environ['SQS_QUEUE_URL'])

    s3_enumerator = S3BucketEnumerator(
        os.environ['S3_BUCKET_NAME'], event.get('S3ContinuationToken'))
    sqs_batcher = SQSBatcher(os.environ['SQS_QUEUE_URL'], int(os.environ['OBJECTS_PER_MESSAGE']))

    # As long as there are at least 10 seconds remaining, enumerate S3 objects into SQS.
    num_keys = 0
    while lambda_context.get_remaining_time_in_millis() > 10000 and not s3_enumerator.finished:
        keys = s3_enumerator.next_page()
        num_keys += len(keys)
        for key in keys:
            sqs_batcher.add_key(key)
    LOGGER.info('Enumerated %d keys into %d batches', num_keys, sqs_batcher._msg_index)
    # Send the last batch of keys.
    sqs_batcher.flash()

    # If the enumerator has not yet finished but we're low on time, invoke this function again.
    if not s3_enumerator.finished:
        LOGGER.info('Invoking another batcher')
        LAMBDA_CLIENT.invoke(
            FunctionName=os.environ['BATCH_LAMBDA_NAME'],
            InvocationType='Event',  # Asynchronous invocation.
            Payload=json.dumps({'S3ContinuationToken': s3_enumerator.continuation_token}),
            Qualifier=os.environ['BATCH_LAMBDA_QUALIFIER']
        )

    return num_keys