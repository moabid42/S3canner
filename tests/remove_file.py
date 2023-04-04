import boto3
import os

# Configure the S3 bucket and object key
bucket_name = "hg.objalert-binaries.eu-central-1"
file_path = "./file"  # Replace with your local file path
object_key = os.path.basename(file_path)

# Create an S3 client object
s3 = boto3.client("s3")

# Delete the file from S3
s3.delete_object(Bucket=bucket_name, Key=object_key)

# Print confirmation message
print(f"Deleted file {object_key} from bucket {bucket_name}")
