import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

__THIS__ = os.path.dirname(os.path.abspath(__file__))

KNOWN_FILES = [
    # relative to the toplevel directory of the git repo.
    ('src/config.yaml.j2', 'src/config.yaml'),
    ('.zuul.yaml.j2', '.zuul.yaml'),
]

OPENSTACK_INFO = {
    'origin': 'zed'
}

def main():
    env = Environment(
        loader=FileSystemLoader(["./", os.path.join(__THIS__, 'templates')]),
        autoescape=select_autoescape()
    )

    for in_file, out_file in KNOWN_FILES:

        print(f'Using {in_file} template')
        template = env.get_template(in_file)

        result = template.stream({'openstack': OPENSTACK_INFO})

        print(f'Writing {out_file}...', end='')
        with open(out_file, 'w') as f:
            result.dump(f)
            f.write('\n')
        print('done')
