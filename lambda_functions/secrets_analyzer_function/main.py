import os
import uuid
import logging

from botocore.exceptions import ClientError as BotoError

if __package__:
    import lambda_functions.secrets_analyzer_function.aws_lib as aws_lib
else:
    import aws_lib

# LOGGER
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

class SecretsAnalyzer():
    def __init__(self):
        return
    def analyze(filepath):
        return
    
class FileInfo(object):
    def __init__(self, bucket_name, object_key, analyzer):
        self.bucket_name = bucket_name
        self.object_key = object_key
        self.s3_identifier = 'S3:{}{}'.format(bucket_name, object_key)
        self.download_path = '/tmp/s3canner_{}'.format(str(uuid.uuid4()))
        self.secrets_analzyer = analyzer

        self.download_time_ms = 0
        self.secrets_matches = []

    @property
    def matched_ruls_ids(self):
        #still have to check how this thrufflhog return the findings
        return
    
    def __str__(self):
        return self.s3_identifier
    
    def __enter__(self):
        # Download the binary from S3 and run the thrufflhog analyzer
        self._download_from_s3()

        LOGGER.debug('Running the analyzer!')
        self.secrets_matches = self.secrets_analzyer.analyze( # do i need to keep track of the file hash? i don't think so
            self.download_path
        ),
        return self
    
    def __exit__(self, exception_type, exception_value, traceback):
        # Remove the downloaded binary from local disk
        if os.path.isfile(self.download_path):
            with open(self.download_path, 'wb') as file:
                file.truncate()
            os.remove(self.download_path)
    
    def save_matches_and_alert(self, lambda_version, dynamo_table_name, sns_topic_arn):
        # save match results to Dynamo and publish an alert to SNS if appropriate
        table = aws_lib.DynamoMatchTable(dynamo_table_name)
        needs_alert = table.save_matches(self, lambda_version)

        # Send alert if appropriate.
        if needs_alert:
            LOGGER.info('Publishing an SNS alert')
            aws_lib.publish_alert_to_sns(self, sns_topic_arn)

    
    def findings(self):
        # generate the findings in a form or summary
        return 



def secrets_analyze_lambda_handler(event_data, lambda_context):
    result = {}
    files = []

    NUM_SECRETS_RULES = -1
    ANALYZER = SecretsAnalyzer() # still not sure about this one 

    # The lambda version must be an integer
    try:
        lambda_version = int(lambda_context.function_version)
    except ValueError:
        lambda_version = -1

    LOGGER.info('Processing %d record(s)', len(event_data['S3Objects']))
    for s3_key in event_data['S3Objects']:
        LOGGER.info('Analyzing %s', s3_key)
    
        with FileInfo(os.environ['S3_BUCKET_NAME'], s3_key, ANALYZER) as file:
            result[file.s3_identifier] = file.findings()
            files.append(file)

            if file.secrets_matches:
                LOGGER.warning('%s secret found: %s', file, file.matched_ruls_ids)
                file.save_matches_and_alert(
                    lambda_version, os.environ['SECRETS_MATCHES_DYNAMO_TABLE_NAME'],
                    os.environ['SECRETS_ALERTS_SNS_TOPIC_ARN']
                )
            else:
                LOGGER.info("%s doen't contain any matches", file)
        

    aws_lib.delete_sqs_messages(os.environ['SQS_QUEUE_URL'], event_data['SQSReceipts'])
    
    # Publish to metrics
    try:
        aws_lib.put_metric_data(NUM_SECRETS_RULES, files)
    except BotoError:
        LOGGER.exception('Error saving metric data')