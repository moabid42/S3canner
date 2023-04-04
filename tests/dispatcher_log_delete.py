import boto3

# Create a CloudWatch Logs client
client = boto3.client('logs')

# Get the log group name
log_group_name = '/aws/lambda/hg_objalert_dispatcher'

# Get the list of log streams in the log group
log_streams = client.describe_log_streams(logGroupName=log_group_name)['logStreams']

# Iterate over the log streams and delete each one
for stream in log_streams:
    stream_name = stream['logStreamName']
    client.delete_log_stream(logGroupName=log_group_name, logStreamName=stream_name)

print('All logs in log group {} have been deleted.'.format(log_group_name))
