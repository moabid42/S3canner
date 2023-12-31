import os
import hcl
import boto3
import shutil
import zipfile
import logging
import argparse
import subprocess

from lambda_functions.analyzer_function.main import COMPILED_RULES_FILENAME
from core.rules.compile_rules import compile_rules

# LOGGER 
LOGGER = logging.getLogger(__name__)

# Root dir
PROJ_DIR = os.path.dirname(os.path.realpath(__file__))

# Core dir
CORE_DIR = os.path.join(PROJ_DIR, 'core')

# Terraform dir
TERRAFORM_DIR = os.path.join(PROJ_DIR, 'terraform')

# Terraform config
TERRAFORM_CONFIG = os.path.join(TERRAFORM_DIR, 'terraform.tfvars')

# Analyzer Lambda function source and zip package
ANALYZE_LAMBDA_DIR = os.path.join(PROJ_DIR, 'lambda_functions', 'analyzer_function')
ANALYZE_LAMBDA_PACKAGE = os.path.join(TERRAFORM_DIR, 'lambda_analyzer') 

# Secrets Analyzer Lambda function source and zip package
SECRETS_ANALYZE_LAMBDA_DIR = os.path.join(PROJ_DIR, 'lambda_functions', 'secrets_analyzer_function', 'main.py')
SECRETS_ANALYZE_LAMBDA_PACKAGE = os.path.join(TERRAFORM_DIR, 'secrets_lambda_analyzer.zip') 

# Yara Analyzer dependencies
YARA_DIR = os.path.join(CORE_DIR, 'rules')
ANALYZE_LAMBDA_DEPENDENCIES =  os.path.join(ANALYZE_LAMBDA_DIR, 'yara_python_3.6.3.zip')

# Batch Lambda function source and zip package
BATCH_LAMBDA_SOURCE = os.path.join(PROJ_DIR, 'lambda_functions', 'batcher_function', 'main.py')
BATCH_LAMBDA_PACKAGE = os.path.join(TERRAFORM_DIR, 'lambda_batcher.zip')

# Dispatch Lambda function source and zip package
DISPATCH_LAMBDA_SOURCE = os.path.join(PROJ_DIR, 'lambda_functions', 'dispatcher_function', 'main.py')
DISPATCH_LAMBDA_PACKAGE = os.path.join(TERRAFORM_DIR, 'lambda_dispatcher.zip')

# NAME_PREFIX
NAME_PREFIX = 'hg-'

# YARA Directory
LAYER_DIR = os.path.join(CORE_DIR, 'rules', 'python')

# Lambda alias terraform targets, to be updated separately.
LAMBDA_ALIASES_TERRAFORM_TARGETS = [
    '-target=module.{}s3canner_{}.aws_lambda_alias.production_alias'.format(NAME_PREFIX, name)
    for name in ['analyzer', 'batcher', 'dispatcher', 'secrets_analyzer']
]

''' Core function '''

def banner() -> None:
    print("""
    .oOOOo.                                                 
    o     o  .oOOo.                                         
    O.            O                                         
     `OOoo.       o                                         
          `O   .oO  .oOo  .oOoO' 'OoOo. 'OoOo. .oOo. `OoOo. 
           o      o O     O   o   o   O  o   O OooO'  o     
    O.    .O      O o     o   O   O   o  O   o O      O     
     `oooO'  `OooO' `OoO' `OoO'o  o   O  o   O `OoO'  o     v1.0\n""")

def deploy() -> None:
    # Deploy S3canner. Equivalent to test + build + apply
    test()
    build()
    apply()

def test() -> None:
    # Run all uni tests and exit 1 if tests failed  
    return 

def build_batcher_():
    # Build the batcher Lambda deployment package
    print('Creating batcher deploy package...')
    with zipfile.ZipFile(BATCH_LAMBDA_PACKAGE, 'w') as pkg:
        pkg.write(BATCH_LAMBDA_SOURCE, os.path.basename(BATCH_LAMBDA_SOURCE))


def build_dispatcher_():
    # Build the dispatcher Lambda deployment package
    print('Creating dispatcher deploy package...')
    with zipfile.ZipFile(DISPATCH_LAMBDA_PACKAGE, 'w') as pkg:
        pkg.write(DISPATCH_LAMBDA_SOURCE, os.path.basename(DISPATCH_LAMBDA_SOURCE))

def build_yara_server():
    # Clone the YARA-rules repo and compile the YARA rules
    compile_rules(os.path.join(ANALYZE_LAMBDA_DIR, COMPILED_RULES_FILENAME))

    # here we can call the manager and init an instance of central yara project which
    # should serve and update the s3 bucket with the latest yara rules as a server

def build_analyser_():
    # Build central yara bucket
    build_yara_server()

    # Build the YARA analyser Lambda deplyment package
    print('Creating analyzer deploy package...')
    with zipfile.ZipFile(ANALYZE_LAMBDA_DEPENDENCIES, 'r') as deps:
        deps.extractall(ANALYZE_LAMBDA_DIR)

    print('We did extract the nessecary depends and now gonna zip everything', ANALYZE_LAMBDA_DEPENDENCIES)

    # Zip up the package
    shutil.make_archive(ANALYZE_LAMBDA_PACKAGE, 'zip', ANALYZE_LAMBDA_DIR)

def build_secrets_analyser_():
    # Build the SECRETS analyzer Lambda deployment package
    print('Creating secrets analyzer deploy package...')
    with zipfile.ZipFile(SECRETS_ANALYZE_LAMBDA_PACKAGE, 'w') as pkg:
        pkg.write(SECRETS_ANALYZE_LAMBDA_DIR, os.path.basename(SECRETS_ANALYZE_LAMBDA_DIR))

def build() -> None:
    # Build the Lambda deployment packages
    build_secrets_analyser_()
    build_analyser_()
    build_batcher_()
    build_dispatcher_() # I use _ in the end based on google standards 
    return 

def apply() -> None:
    # Run Terraform apply. Raises an exception if the Terraform is invalid
    
    # VAlidate the format
    os.chdir(TERRAFORM_DIR)
    
    # Setup the backend if needed and reload modules ?
    subprocess.check_call(['terraform', 'init'])

    subprocess.check_call(['terraform', 'validate'])
    subprocess.check_call(['terraform', 'fmt'])
    # subprocess.check_call(['terraform', 'plan'])

    # APPLY
    subprocess.check_call(['terraform', 'apply', '-auto-approve'])

    # Second apply to update the lambda aliases still needed
    subprocess.check_call(['terraform', 'apply', '-auto-approve'])

'''---------------'''


def config_to_dic():
    # Parse the terraform config gile and return the config as a dict
    with open(TERRAFORM_CONFIG) as config_file:
        return hcl.load(config_file) # Dict[str, Union[int, str]]


def main() -> None:
    # Arg parsing
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter) # Here we are using the formatter class for more help output readability
    parser.add_argument(
        'command',
        choices =   ['deploy', 'banner', 'test', 'build', 'apply']
    )
    args = parser.parse_args()

    # Config load
    config_data = config_to_dic()

    # Setting up the region
    boto3.setup_default_session(region_name=config_data['aws_region'])

    # Call the appropriate function
    globals()[args.command]()


if __name__ == '__main__':
    main()
