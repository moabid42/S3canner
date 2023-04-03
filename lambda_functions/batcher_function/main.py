import os
import json
import boto3
import logging
from typing import List
from botocore.exceptions import ClientError


LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

LAMBDA_CLIENT = boto3.client('lambda')
S3_CLIENT = boto3.client('s3')
SQS_CLIENT = boto3.client('sqs')

# Encapsulates a single SQS message (which will contain multiple S3 keys)
class SQSMessage:
    def __init__(self, message_id: int) -> None:
        self.message_id_: int = message_id
        self.keys_: List[str] = []

    # Returns [int] the number of keys stored in the SQS message so far
    @property
    def num_keys(self) -> int:
        return len(self.keys_)

    # Add another S3 key (string) to the message
    def add_key(self, key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("S3 key must be a string")
        self.keys_.append(key)

    # Returns a message entry [dict], as required by sqs_client.send_message_batch()
    def to_dict(self) -> dict:
        # The message body matches the structure of an S3 added event. This gives all
        # messages in the SQS the same format and enables the dispatcher to parse them consistently.
        return {
            'Id': str(self.message_id_),
            'MessageBody': json.dumps({
                'Records': [{'s3': {'object': {'key': key}}} for key in self.keys_]
            })
        } 

    # Remove the stored list of S3 keys
    def reset(self) -> None:
        self.keys_ = []


# Collect groups of S3 keys and batch them into as few SQS requests as possible
class SQSBatcher:
    def __init__(self, queue_url: str, objects_per_message: int, messages_per_batch: int = 10):
        # Note that the downstream analyzer Lambdas will each process at most
        # (objects_per_message * messages_per_batch) binaries. The analyzer runtime limit is the
        # ultimate constraint on the size of each batch.
        self.queue_url_ = queue_url
        self._objects_per_message = objects_per_message
        self._messages_per_batch = messages_per_batch

        self._messages: List[SQSMessage] = [SQSMessage(i) for i in range(messages_per_batch)]
        self._msg_index: int = 0  # The index of the SQS message where keys are currently being added.

        # The first and last keys added to this batch.
        self._first_key: str = None
        self._last_key: str = None

    def _send_batch(self) -> None:
        # Group keys into messages and make a single batch request
        LOGGER.info('Sending SQS batch of %d keys: %s ... %s',
                    sum(msg.num_keys for msg in self._messages), self._first_key, self._last_key)
        sqs_entries = [msg.sqs_entry() for msg in self._messages if msg.num_keys > 0]
        response = boto3.client('sqs').send_message_batch(
            QueueUrl=self.queue_url_,
            Entries=sqs_entries
        )

        failures = response.get('Failed', [])
        if failures:
            for failure in failures:
                LOGGER.error('Unable to enqueue S3 key %s: %s',
                             self._messages[int(failure['Id'])], failure['Message'])
            boto3.client('cloudwatch').put_metric_data(Namespace='ObjAlert', MetricData=[{
                'MetricName': 'BatchEnqueueFailures',
                'Value': len(failures),
                'Unit': 'Count'
            }])

        for msg in self._messages:
            msg.reset()
        self._first_key = None

    # Add a new S3 key to the message batch and send to SQS if necessary.
    def add_key(self, key: str) -> None:
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

    # After all messages have been added, send the remaining as a last batch to SQS
    def flush(self) -> None:
        if self._first_key:
            LOGGER.info('Flush: sending last batch of keys')
            self._send_batch()


# Enumerates all of the S3 objects in a given bucket.
class S3BucketEnumerator:
    def __init__(self, bucket_name: str, continuation_token: str = None):
        self.bucket_name: str = bucket_name
        self.continuation_token: str = continuation_token
        self.keys: List[str] = []

    # Get the next page of S3 objects.
    def get_keys_list(self) -> List[str]:
        try:
            while True:
                if self.continuation_token:
                    response = boto3.client('s3').list_objects_v2(
                        Bucket=self.bucket_name, ContinuationToken=self.continuation_token)
                else:
                    response = boto3.client('s3').list_objects_v2(Bucket=self.bucket_name)

                self.continuation_token = response.get('NextContinuationToken')
                if not response['IsTruncated']:
                    self.continuation_token = None

                for obj in response['Contents']:
                    self.keys.append(obj['Key'])

                if not self.continuation_token:
                    return self.keys
        
        except ClientError as e:
            raise Exception(f"Failed to list objects in bucket {self.bucket_name}: {e}") from e


def batch_lambda_handler(event, lambda_context):
    LOGGER.info('Invoked with event %s', json.dumps(event))
    s3_enumerator = S3BucketEnumerator(
        os.environ['S3_BUCKET_NAME'], event.get('S3ContinuationToken'))
    sqs_batcher = SQSBatcher(os.environ['SQS_QUEUE_URL'], int(os.environ['OBJECTS_PER_MESSAGE']))

    # As long as there are at least 10 seconds remaining, enumerate S3 objects into SQS.
    num_keys = 0
    while lambda_context.get_remaining_time_in_millis() > 10000 and s3_enumerator.continuation_token is not None:
        keys = s3_enumerator.get_keys_generator()
        num_keys += len(keys)
        for key in keys:
            sqs_batcher.add_key(key)
    
    LOGGE.info('Enumerated %d keys into %d batches', num_keys, sqs_batcher._msg_index)

    # Send the last batch of keys.
    sqs_batcher.flush()

    # If the enumerator has not yet finished but we're low on time, invoke this function again.
    if s3_enumerator.continuation_token is not None:
        LOGGER.info('Invoking another batcher')
        LAMBDA_CLIENT.invoke(
            FunctionName=os.environ['BATCH_LAMBDA_NAME'],
            InvocationType='Event',  # Asynchronous invocation.
            Payload=json.dumps({'S3ContinuationToken': s3_enumerator.continuation_token}),
            Qualifier=os.environ['BATCH_LAMBDA_QUALIFIER']
        )

    return num_keys
