import configparser
import os
import yaml

K8S = 'k8s'
UNKNOWN = 'UNKNOWN'

def read_gitreview():
    cwd = os.getcwd()
    gitreview_path = os.path.join(cwd, '.gitreview')
    if not os.path.isfile(gitreview_path):
        return None

    config = configparser.ConfigParser()
    config.read(gitreview_path)
    return config

def read_metadata_file():
    with open('metadata.yaml', 'r') as f:
        contents = yaml.load(f, Loader=yaml.SafeLoader)
    return contents

def get_gitreview_line(key):
    return read_gitreview()['gerrit'][key]

def is_k8s_charm():
    metadata = read_metadata_file()
    return metadata and 'containers' in metadata.keys()

def get_charm_type():
    if is_k8s_charm():
        return K8S
    return UNKNOWN

def get_branch_name():
    return get_gitreview_line('defaultbranch') or UNKNOWN
