# Batcher Function
This file is a Python script that implements batch processing of S3 objects using SQS. The code reads all S3 objects in a given bucket, and then sends the S3 object keys to an SQS queue in batches. Each batch consists of a certain number of messages, and each message contains multiple S3 object keys. The maximum number of objects that can be processed is a runtime limit of AWS Lambda.

## Code Structure
The code is structured as follows:

- import statements
- logging configuration
- boto3 client initialization for Lambda, S3, and SQS
- SQSMessage class that encapsulates a single SQS message containing multiple S3 object keys
- SQSBatcher class that groups S3 object keys into messages and makes a single batch request
- S3BucketEnumerator class that enumerates all of the S3 objects in a given bucket
- batch_lambda_handler function that handles the Lambda function invocation

## Conclusion
This script provides an efficient way to process large amounts of data stored in S3. By batching the S3 object keys into messages and sending them to SQS, the script can handle large amounts of data without running into the runtime limit of AWS Lambda.

# Dispatcher Function
This file is a python script that receives messages from Amazon SQS, transforms them into a specific format :
```
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
    [None] if the SQS message was empty or invalid.
```
and triggers a downstream Lambda function for processing.

## Code Structure
- delete_sqs_messages(queue_url: str, receipt_handles: List[str]) -> None: Deletes a batch of SQS messages from the queue.
- invoke_analysis_lambda(payload: dict) -> None: Invokes an analysis Lambda function asynchronously.
- receive_message_sqs(queue_url: str, wait_time_seconds: int) -> Optional[dict]: Receives a message from the SQS service. This function utilizes long-polling to wait for messages.
- _build_payload(sqs_messages): Converts a batch of SQS messages into an analysis Lambda payload. This function is used by the dispatch_lambda_handler function to convert SQS messages into a payload that can be passed to the invoke_analysis_lambda function.
- dispatch_lambda_handler(_, lambda_context) -> int: This function is the main handler for the Lambda function. It repeatedly polls the SQS queue for messages and dispatches them to the analysis Lambda function using the invoke_analysis_lambda function.

## Conclusion
This script provides a way to process the batched message queured in SQS and trigger the necessary number of analyzers depending on the number of the objects in a batch, in a way it's invoked via cronjob every minute(can be updated via the variables file in terraform).

# Analyzer Function
This file is a Python scrip that implements the analyzing process of the objects queured and dispatched. The code download the dispatched object of the S3 bucket and sanitize these files while comparing there behavior with the predefined YARA compiled rules, and in case of a match, a new column gonna be added to our DynamoDB table and an SNS message gonna be triggered depending on the chosen subscription protocol.

## Code Structure
- _read_in_chunks function: This function reads a file in fixed-size chunks to minimize memory usage for large files. It takes a file object and chunk size as arguments.

- compute_hashes function: This function computes the SHA and MD5 hashes for a specified file object. It takes a file path as an argument.

- YaraAnalyzer class: This class encapsulates YARA analysis and matching functions. It has an __init__ method that initializes the class with prebuilt binary rules. It has a num_rules property that returns the number of YARA rules loaded, and an analyze method that runs YARA analysis on a target file.

- BinaryInfo class: This class organizes the analysis of a single binary blob in S3. It has an __init__ method that sets various attributes such as bucket_name, object_key, and yara_analyzer. It also has a __enter__ method that downloads the binary from S3 and runs YARA analysis, and a __exit__ method that removes the downloaded binary from local disk. It has a matched_rule_ids property that returns a list of 'yara_file:rule_name' for each YARA match, and a save_matches_and_alert method that saves match results to Dynamo and publishes an alert to SNS if appropriate.

`For more info make sure you read the code, it's well commented.`