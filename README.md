# aws-objalert



## Overview
This project is about creating a serverless AWS pipeline where any object added to an S3 bucket is scanned with YARA rules + Sensitive information detector. If a match is found an alert will be fired, for fast incident response.


## Chart Flow
![smth](./img/chartflow.png)

## Terraform Config
This configuration file provides various settings that define the behavior and performance of BinaryAlert, a system for detecting malicious files using Amazon Web Services (AWS) resources. Here's a breakdown of the individual settings:

1. ***sqs_retention_minutes***: This setting specifies the duration for which messages should be retained in the Simple Queue Service (SQS) before they are dropped. SQS is used as an intermediary between S3 Events and the Analyzer Lambda function. Messages that are dispatched to analyzers will continue to be processed until they time out. In this case, messages are retained for 30 minutes.

2. ***lambda_batch_objects_per_message***: This setting determines the number of S3 object keys to pack into a single SQS message. Each downstream analyzer will process up to 10 SQS messages, each with this many objects. Higher values allow for higher throughput, but are constrained by analyzer execution time limit. In this case, 20 objects are packed into a single message.

3. ***lambda_batch_memory_mb***: This setting specifies the memory limit (in MB) for the batching Lambda function. The minimum allowed by Lambda is 128 MB.

4. ***lambda_dispatch_frequency_minutes***: This setting specifies how often the Lambda dispatcher will be invoked. To ensure that only one dispatcher is running, this rate should be greater than the lambda dispatch timeout. In this case, the dispatcher is invoked every 1 minute.

5. ***lambda_dispatch_limit***: This setting specifies the maximum number of analyzers that can be asynchronously invoked during one dispatcher run. Higher values allow for more throughput, but if too many analyzers are invoked too quickly, Lambda invocations may be throttled. In this case, 50 analyzers can be invoked during one dispatcher run.

6. ***lambda_dispatch_memory_mb***: This setting specifies the memory limit (in MB) for the dispatching function. The minimum allowed by Lambda is 128 MB.

7. ***lambda_dispatch_timeout_sec***: This setting specifies the time limit (in seconds) for the dispatching function. If the function exceeds this limit, it will be terminated. In this case, the dispatching function has a timeout of 40 seconds.

8. ***lambda_analyze_memory_mb***: This setting specifies the memory limit (in MB) for the analyzer functions. The minimum allowed by Lambda is 128 MB.

9. ***lambda_analyze_timeout_sec***: This setting specifies the time limit (in seconds) for the analyzer functions. If the function exceeds this limit, it will be terminated. In this case, the analyzer functions have a timeout of 240 seconds (4 minutes).

10. ***expected_analysis_frequency_minutes***: This setting specifies the time period (in minutes) after which an alarm should be raised if no binaries are analyzed. This is a measure to ensure that the system is functioning properly. In this case, an alarm will be raised if no binaries are analyzed for 30 minutes.

11. ***dynamo_read_capacity and dynamo_write_capacity***: These settings specify the provisioned capacity for the Dynamo table which stores match results. Capacity is (very roughly) the maximum number of operations per second. The numbers can be quite low since there will likely be very few matches. In this case, the read capacity is set to 10 operations per second and the write capacity is set to 5 operations per second.

12. ***s3_log_bucket***: A pre-existing bucket in which to store S3 access logs. If not specified, one will be created.

13. ***s3_log_prefix***: A prefix used for all S3 access logs stored in the bucket.

14. ***s3_log_expiration_days***: The number of days after which S3 access logs will expire. This has no effect if using a pre-existing bucket for logs.

15. ***lambda_log_retention_days***: The number of days to retain Lambda function logs.

## Recourses
### Lambda Base Module
This module consists of several resources, including an IAM policy document, an IAM execution role, an IAM policy attachment, a CloudWatch log group, a Lambda function, a Lambda alias, and two CloudWatch alarms.

### Services used:
- CloudWatch
- DynamoDB
- SQS
- SNS
- S3Buckets
- Lambda functions