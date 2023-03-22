import argparse
import os
import sys
import subprocess

import boto3
import hcl

# Root dir
PROJ_DIR = os.path.dirname(os.path.realpath(__file__))

# Core dir
CORE_DIR = os.path.join(PROJ_DIR, 'core')

# Terraform dir
TERRAFORM_DIR = os.path.join(CORE_DIR, 'terraform')

# Terraform config
TERRAFORM_CONFIG = os.path.join(TERRAFORM_DIR, 'terraform.tfvars')

''' Core function '''

def deploy() -> None:
    # Deploy ObjAlert. Equivalent to test + build + apply
    test()
    build()
    apply()

def test() -> None:
    # Run all uni tests and exit 1 if tests failed
    return 

def build_dispatcher_():
    # Build the dispatcher Lambda deployment package
    return

def build_analyser_():
    # Build the YARA analyser Lambda deplyment package
    return

def build() -> None:
    # Build the Lambda deployment packages
    build_dispatcher_() # I use _ in the end based on google standards 
    build_analyser_()
    return 

def apply() -> None:
    # Run Terraform apply. Raises an exception if the Terraform is invalid
    
    # VAlidate the format
    os.chdir(TERRAFORM_DIR)
    subprocess.check_call(['terraform', 'validate'])
    subprocess.check_call(['terraform', 'fmt'])

    # Setup the backend if needed and reload modules ?
    subprocess.check_call(['terraform', 'init'])

    # APPLY
    subprocess.check_call(['terraform', 'apply'])

    # Second apply to update the lambda aliases still needed

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
        choices =   ['deploy', 'test', 'build', 'apply'],
        help    =   'deploy        Deploy ObjAlert. Equivalent to test + build + apply.\n'
                    'test          Run unit tests.\n'
                    'build         Build Lambda packages (saves *.zip files in terraform/).\n'
                    'apply         Terraform validate and apply any configuration/package changes.\n')
    args = parser.parse_args()

    # Config load
    config_data = config_to_dic()

    # Setting up the region
    boto3.setup_default_session(region_name=config_data['aws_region'])

    # Call the appropriate function
    globals()[args.command]()


if __name__ = '__main__':
    main()