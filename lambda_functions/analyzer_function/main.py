import os
import time
import yara
import uuid
import hashlib
import logging
import newobjalert.lambda_functions.analyzer_function.aws_lib as aws_lib

from botocore.exceptions import ClientError as BotoError

# Loggger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

# Consts
THIS_DIRECTORY          = os.path.dirname(os.path.realpath(__file__))
COMPILED_RULES_FILENAME = 'binary_yara_rules.bin'
COMPILED_RULES_FILEPATH = os.path.join(THIS_DIRECTORY, COMPILED_RULES_FILENAME)

MB = 2 ** 20  # ~ relativly 1 million bytes

def _read_in_chunks(file_object, chunk_size=2*MB):
    """Read a file in fixed-size chunks (to minimize memory usage for large files).
    Args:
        file_object: An opened file-like object supporting read().
        chunk_size: [int] Max size (in bytes) of each file chunk.
    Yields:
        [string] file chunks, each of size at most chunk_size.
    """
    while True:
        chunk = file_object.read(chunk_size)
        if chunk:
            yield chunk
        else:
            return  # End of file.


def compute_hashes(file_path):
    """Compute SHA and MD5 hashes for the specified file object.
    The MD5 is only included to be compatible with other security tools.
    Args:
        file_path: [string] File path to be analyzed.
    Returns:
        String tuple (sha_hash, md5_hash).
    """
    sha = hashlib.sha256()
    md5 = hashlib.md5()
    with open(file_path, mode='rb') as file_object:
        for chunk in _read_in_chunks(file_object):
            sha.update(chunk)
            md5.update(chunk)
    return sha.hexdigest(), md5.hexdigest()

class YaraAnalyzer(object):
    # Encapsulates YARA analysis and matching functions

    def __init__(self, rules_file):
        # Init with prebuilt binary rules
        self._rules = yara.load(rules_file)

    @property
    def num_rules(self):
        # Num of yara rules loaded (inlined cuz it's fast)
        return sum(1 for _ in self._rules)

    @staticmethod
    def _yara_variables(original_target_path):
        # Compute external variables needed for some YARA rules and map the string var name into a dict of string values.
        file_name = os.path.basename(original_target_path)
        file_suffix = file_name.split('.')[-1] if '.' in file_name else ''  # e.g. "exe" or "rar".
        return {
            'extension': '.' + file_suffix if file_suffix else '',
            'filename': file_name,
            'filepath': original_target_path,
            'filetype': file_suffix.upper()  # Used in only one rule (checking for "GIF").
            # can still add here some more informations; e.g: Network connection details.
        }

    def analyze(self, target_file, original_target_path=''):
        # Run YARA analysis on a file and return a list of yara match objects
        return self._rules.match(target_file, externals=self._yara_variables(original_target_path))

class BinaryInfo(object):
    # Organizes the analysis of a single binary block in S3

    def __init__(self, bucket_name, object_key, yara_analyzer):
        self.bucket_name = bucket_name
        self.object_key = object_key
        self.s3_identifier = 'S3:{}:{}'.format(bucket_name, object_key)

        self.download_path = '/tmp/binaryalert_{}'.format(str(uuid.uuid4()))
        self.yara_analyzer = yara_analyzer

        # Computed after file download and analysis.
        self.download_time_ms = 0
        self.reported_md5 = self.observed_path = ''
        self.computed_sha = self.computed_md5 = None
        self.yara_matches = []  # List of yara.Match objects.

    @property
    def matched_rule_ids(self):
        # A list of 'yara_file:rule_name' for each YARA match
        return ['{}:{}'.format(match.namespace, match.rule) for match in self.yara_matches]

    def __str__(self):
        # Use the S3 identifier as the string representation of the binary
        return self.s3_identifier

    def __enter__(self):
        # Download the binary from S3 and run YARA analysis
        self._download_from_s3()
        self.computed_sha, self.computed_md5 = compute_hashes(self.download_path)

        LOGGER.debug('Running YARA analysis')
        self.yara_matches = self.yara_analyzer.analyze(
            self.download_path, original_target_path=self.observed_path)

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        # Remove the downloaded binary from local disk
        # In Lambda, "os.remove" does not actually remove the file as expected.
        # Thus, we first truncate the file to set its size to 0 before removing it.
        if os.path.isfile(self.download_path):
            with open(self.download_path, 'wb') as file:
                file.truncate()
            os.remove(self.download_path)

    def _download_from_s3(self):
        # Download binary from S3 and measure elapsed time
        LOGGER.debug('Downloading to %s', self.download_path)

        start_time = time.time()
        s3_metadata = aws_lib.download_from_s3(
            self.bucket_name, self.object_key, self.download_path)
        self.download_time_ms = (time.time() - start_time) * 1000

        self.reported_md5 = s3_metadata.get('reported_md5', '')
        self.observed_path = s3_metadata.get('observed_path', '')

    def save_matches_and_alert(self, lambda_version, dynamo_table_name, sns_topic_arn):
        # Save match results to Dynamo and publish an alert to SNS if appropriate.
        # still have some probelms with dynamo DB
        table = aws_lib.DynamoMatchTable(dynamo_table_name)
        needs_alert = table.save_matches(self, lambda_version)

        # Send alert if appropriate.
        if needs_alert:
            LOGGER.info('Publishing an SNS alert')
            aws_lib.publish_alert_to_sns(self, sns_topic_arn)

    def summary(self):
        # Generate a summary dictionary of binary attributes
        return {
            'FileInfo': {
                'ComputedMD5': self.computed_md5,
                'ComputedSHA256': self.computed_sha,
                'ReportedMD5': self.reported_md5,
                'S3Location': self.s3_identifier,
                'SamplePath': self.observed_path
            },
            'MatchedRules': [
                {
                    # YARA string IDs, e.g. "$string1"
                    'MatchedStrings': list(sorted(set(t[1] for t in match.strings))),
                    'Meta': match.meta,
                    'RuleFile': match.namespace,
                    'RuleName': match.rule,
                    'RuleTags': match.tags
                }
                for match in self.yara_matches
            ]
        }


def analyze_lambda_handler(event_data, lambda_context):
    result = {}
    binaries = []  # List of the BinaryInfo data.

    # Build the analyzer calss out of the rules binary
    ANALYZER = YaraAnalyzer(COMPILED_RULES_FILEPATH)
    NUM_YARA_RULES = ANALYZER.num_rules

    # The Lambda version must be an integer.
    try:
        lambda_version = int(lambda_context.function_version)
    except ValueError:
        lambda_version = -1

    LOGGER.info('Processing %d record(s)', len(event_data['S3Objects']))
    for s3_key in event_data['S3Objects']:
        LOGGER.info('Analyzing %s', s3_key)

        with BinaryInfo(os.environ['S3_BUCKET_NAME'], s3_key, ANALYZER) as binary:
            result[binary.s3_identifier] = binary.summary()
            binaries.append(binary)

            if binary.yara_matches:
                LOGGER.warning('%s matched YARA rules: %s', binary, binary.matched_rule_ids)
                binary.save_matches_and_alert(
                    lambda_version, os.environ['YARA_MATCHES_DYNAMO_TABLE_NAME'],
                    os.environ['YARA_ALERTS_SNS_TOPIC_ARN'])
            else:
                LOGGER.info('%s did not match any YARA rules', binary)

    # Delete all of the SQS receipts (mark them as completed).
    aws_lib.delete_sqs_messages(os.environ['SQS_QUEUE_URL'], event_data['SQSReceipts'])

    # Publish metrics.
    try:
        aws_lib.put_metric_data(NUM_YARA_RULES, binaries)
    except BotoError:
        LOGGER.exception('Error saving metric data')

    return result
