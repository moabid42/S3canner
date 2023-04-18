import boto3

client = boto3.client('lambda')

response = client.get_supported_function_version()

runtimes = response['Runtimes']

print("The following AWS Lambda runtimes are supported:")
for runtime in runtimes:
        print(runtime)

