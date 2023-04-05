import os
import logging
from yara import Error as YaraError
from botocore.exceptions import ClientError as BotoError

# Loggger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

THIS_DIRECTORY          = os.path.dirname(os.path.realpath(__file__))
COMPILED_RULES_FILENAME = 'binary_yara_rules.bin'
COMPILED_RULES_FILEPATH = os.path.join(THIS_DIRECTORY, COMPILED_RULES_FILENAME)

