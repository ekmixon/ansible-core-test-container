#!/usr/bin/env python
"""Update requirements from the ansible/ansible repository."""

import json
import os
import re
import subprocess
import sys
import urllib.request


def main():
    """Main program entry point."""
    with open('Dockerfile') as dockerfile:
        docker_from = dockerfile.readline()

    image = re.search('^FROM (?P<image>.*)$', docker_from)['image']

    result = subprocess.run(['docker', 'run', '-it', image, 'cat', '/usr/share/container-setup/ansible-test-ref.txt'],
                            check=True, capture_output=True, text=True)

    ref = result.stdout.strip()

    source_requirements = {
        'https://api.github.com/repos/ansible/ansible/contents/test/units/': 'units',
        'https://api.github.com/repos/ansible/ansible/contents/test/integration/': 'integration',
        'https://api.github.com/repos/ansible/ansible/contents/test/lib/ansible_test/_data/requirements/': '',
    }

    files = []
    untouched_mappings = {}

    for url, label in source_requirements.items():
        with urllib.request.urlopen(f'{url}?ref={ref}') as response:
            content = json.loads(response.read().decode())

            if not isinstance(content, list):
                content = [content]

            for item in content:
                if label and item['name'].endswith('requirements.txt'):
                    item['name'] = f"{label}.{item['name']}"
                elif (
                    label
                    and not item['name'].endswith('requirements.txt')
                    or not label
                    and item['name'] != 'constraints.txt'
                ):
                    continue

                files.append(item)

    requirements_dir = 'requirements'

    untouched_paths = {
        os.path.join(requirements_dir, file)
        for file in os.listdir(requirements_dir)
    }


    for item in files:
        name = item['name']
        download_url = item['download_url']

        path = os.path.join(requirements_dir, name)

        if path in untouched_paths:
            untouched_paths.remove(path)

        with urllib.request.urlopen(download_url) as response:
            latest_contents = response.read().decode()

        if os.path.exists(path):
            with open(path, 'r') as contents_fd:
                current_contents = contents_fd.read()
        else:
            current_contents = ''

        if latest_contents == current_contents:
            print(f'{path}: current')
            continue

        with open(path, 'w') as contents_fd:
            contents_fd.write(latest_contents)

        print(f'{path}: updated')

    for path in untouched_paths:
        os.unlink(path)

        print(f'{path}: deleted')

    # Error on any rename mappings that were not used to catch typos in the mapping or files that no longer exist
    for url, value in untouched_mappings.items():
        for m in value:
            print(f'ERROR: Unable to rename {m} from {url}')

    if any(untouched_mappings[url] for url in untouched_mappings):
        sys.exit(1)


if __name__ == '__main__':
    main()
