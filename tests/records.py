import json

# JSON string
json_str = """
{
    "Records": [
        {
            "messageId": "cb289b83-d9d8-4d15-83fa-ea2d79dd82f3",
            "receiptHandle": "AQEBCPMQejIbbxdKAaKFv/c7QjqshCZdIDVPbAq7MJE94La",
            "body": "{\"Records\": [{\"s3\": {\"object\": {\"key\": \"file\"}}}]}",
            "attributes": {
                "ApproximateReceiveCount": "8",
                "AWSTraceHeader": "Root=1-64413306-1eb07cbe4235ba7a39c11a84;Parent=13a30ae854490841;Sampled=0;Lineage=4dad4601:0",
                "SentTimestamp": "1681994503181",
                "SenderId": "AROAVOWAWGTT7ZTGDAU7Y:hg_s3canner_batcher",
                "ApproximateFirstReceiveTimestamp": "1681994503181",
            },
            "messageAttributes": {},
            "md5OfBody": "b346ac8160eb51dba132c2ba4faf1688",
            "eventSource": "aws:sqs",
            "eventSourceARN": "arn:aws:sqs:eu-central-1:375140005095:hg_s3canner_s3_object_queue",
            "awsRegion": "eu-central-1"
        }
    ]
}
"""

# Parse JSON string into a Python object
data = json.loads(json_str)
print(data)

# Retrieve object keys
record = data["Records"][0]
message_id = record["messageId"]
receipt_handle = record["receiptHandle"]
body = json.loads(record["body"])
s3_object_key = body["Records"][0]["s3"]["object"]["key"]
attributes = record["attributes"]
message_attributes = record["messageAttributes"]
md5_of_body = record["md5OfBody"]
event_source = record["eventSource"]
event_source_arn = record["eventSourceARN"]

print(record)
print(message_id)
print(receipt_handle)
print(body)
print(s3_object_key)