import boto3
import os
import time  # Configure the S3 bucket and object key

bucket_name = "hg.objalert-binaries.eu-central-1"
file_path = "./file.txt"  # Replace with your local file path
object_key = os.path.basename(file_path)  # Upload the file to S3
s3 = boto3.client("s3")
s3.upload_file(file_path, bucket_name, object_key)
print(
    f"Uploaded file {file_path} to bucket {bucket_name} with key {object_key}"
)  # Configure the Lambda function name
# lambda_function_name = (
#     "hg-objalert-batcher"  # Replace with your Lambda function name
# )
# # Create a test event to simulate the S3 PUT event
# test_event = {
#     "Records": [
#         {
#             "eventVersion": "2.1",
#             "eventSource": "aws:s3",
#             "awsRegion": "eu-central-1",
#             "eventTime": "2023-03-30T09:31:16.765Z",
#             "eventName": "ObjectCreated:Put",
#             "userIdentity": {"principalId": "EXAMPLE"},
#             "requestParameters": {"sourceIPAddress": "127.0.0.1"},
#             "responseElements": {
#                 "x-amz-request-id": "EXAMPLE",
#                 "x-amz-id-2": "EXAMPLE",
#             },
#             "s3": {
#                 "s3SchemaVersion": "1.0",
#                 "configurationId": "test-event",
#                 "bucket": {
#                     "name": bucket_name,
#                     "ownerIdentity": {"principalId": "EXAMPLE"},
#                     "arn": f"arn:aws:s3:::{bucket_name}",
#                 },
#                 "object": {
#                     "key": object_key,
#                     "size": 15,
#                     "eTag": "EXAMPLE",
#                     "sequencer": "EXAMPLE",
#                 },
#             },
#         }
#     ]
# }
# # Invoke the Lambda function with the test event
# lambda_client = boto3.client("lambda")
# response = lambda_client.invoke(
#     FunctionName=lambda_function_name,
#     InvocationType="RequestResponse",
#     Payload=bytes(json.dumps(test_event), encoding="utf-8"),
# )
# # Read the Lambda function output
# output = json.loads(
#     response["Payload"].read().decode("utf-8")
# )  # Print the output and check the Lambda function's functionality
# print(f"Lambda function output: {output}")
