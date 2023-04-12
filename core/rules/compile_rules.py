import os
import yara
import shutil
import tempfile
import subprocess

# This directory
RULES_DIR = os.path.dirname(os.path.realpath(__file__))

# Remote URLs (To be updated)
REMOTE_RULE_SOURCES = {
    'https://github.com/YARA-Rules/rules.git' : ['cve_rules']
}

def _find_yara_files():
    """Find all .yar[a] files in the rules directory.

    Returns:
        List of YARA rule filepaths, relative to the rules root directory.
    """
    yara_files = [os.path.relpath(os.path.join(root, filename), start=RULES_DIR)
                  for root, _, files in os.walk(RULES_DIR)
                  for filename in files
                  if filename.lower().endswith(('.yar', '.yara'))]
    return yara_files

def compile_rules(target_path):
    
    #Remove existing github rules
    if os.path.exists(os.path.join(RULES_DIR, 'github.com')):
        shutil.rmtree(os.path.join(RULES_DIR, 'github.com'))
    
    if os.path.exists('/tmp/rules.git'):
        exists = True
    else:
        exists = False

    for url, folders in REMOTE_RULE_SOURCES.items():
        # Clone repo into a temp directory
        print('Cloning YARA rules from {}/{}...'.format(url, folders))
        cloned_repo_rule = os.path.join(tempfile.gettempdir(), os.path.basename(url))
        if exists == True:
            shutil.rmtree(cloned_repo_rule)
            exists = False
        subprocess.check_call(['git', 'clone', '--quiet', url, cloned_repo_rule])

        # Copy each specified folder into the target rules directory
        for folder in folders:
            source = os.path.join(cloned_repo_rule, folder)
            dest = os.path.join(RULES_DIR, url.split('//')[1], folder)
            shutil.copytree(source, dest)

        print("The YARA RULE path is : ", RULES_DIR)
        # Copy all the .yar files from the test_rules folder to the same folder as other .yar files
        test_rules_path = os.path.join(RULES_DIR, 'test_rules')
        for dirpath, dirnames, filenames in os.walk(test_rules_path):
            for filename in filenames:
                if filename.endswith('.yar'):
                    source = os.path.join(dirpath, filename)
                    dest = os.path.join(RULES_DIR, url.split('//')[1], filename)
                    shutil.copy2(source, dest)

        shutil.rmtree(cloned_repo_rule)

    yara_filepaths = {relative_path: os.path.join(RULES_DIR, relative_path)
            for relative_path in _find_yara_files()}
    print('yara_filepaths:', yara_filepaths)

    rules = yara.compile(
        filepaths = yara_filepaths,
        externals = {'extension': '', 'filename' : '', 'filepath': '', 'filetype': ''}
    )
    rules.save(target_path)
