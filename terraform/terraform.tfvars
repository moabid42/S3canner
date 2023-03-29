/* Configuration File */

#####     Base Config      #####
// Deployment Region
aws_region = "eu-central-1"

// Haufe Prefix
name_prefix = "hg"

#####   ADvanced Config    #####
// Retention in SQS
sqs_retention_minutes = 30

# Batch config #
// Number of S3 object keys to pack into a single SQS Message
lambda_batch_objects_per_message = 20

// Memory limit for the batching
lambda_batch_memory_mb = 128 # 123 MB is the minimum allowed by Lambda

# Dispatch config #
// Lambda Dispatch invoke rate
lambda_dispatch_frequency_minutes = 1

// Lambda Dispatch limit
lambda_dispatch_limit = 50

// Memory limit for dispatching
lambda_dispatch_memory_mb = 128

// Time limit for dispatching
lambda_dispatch_timeout_sec = 40

# Analyzer config #
// Expected invoke frequency
expected_analysis_frequency_minutes = 30

// Memory limit for analyzing
lambda_analyze_memory_mb = 512

// Time limit for analyzing
lambda_analyze_timeout_sec = 240

# DynamoDB config #
// Read capacity
dynamo_read_capacity = 10

// Write capacity
dynamo_write_capacity = 5 // low cuz there will be very few matches

# Log config #
//  Logs bucket
s3_log_bucket = "" // Idk if it exists if not one will be created.

// Log folder
s3_log_prefix = "s3-access-logs/"

// Expected expiration of the logs
s3_log_expiration_days = 60 # This is not used when existing S3 bucket is used

// Lambda functions logs
lambda_log_retention_days = 90