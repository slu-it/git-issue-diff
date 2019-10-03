import argparse
import json
import os
import os.path
import re
import shutil
import uuid
from pathlib import Path

from git import Repo


class RepositoryDefinition:
    def __init__(self, data: dict):
        self.name = str(data['name'])
        self.url = str(data['url'])
        self.active = bool(data['active'])
        if self.active:
            self.start = str(dict(data.get('diff')).get('start'))
            self.end = str(dict(data.get('diff')).get('end', 'HEAD'))


def execute(configuration: dict):
    working_directory = create_working_directory()
    for definition in map(RepositoryDefinition, configuration['repositories']):
        if not definition.active:
            continue

        print('\n### PROCESSING {} ###\n'.format(definition.name))

        repository = clone(working_directory, definition)

        relevant_messages = []
        for commit in commits_between_start_and_end(repository, definition):
            relevant_messages.append(commit.message)

        issue_keys = set([])
        for message in relevant_messages:
            for found in re.findall(configuration['issueKeyPattern'], message):
                issue_keys.add(found)
        print('Issue Keys: {}'.format(', '.join(issue_keys)))

    shutil.rmtree(working_directory)


def clone(working_directory: Path, repository: RepositoryDefinition) -> Repo:
    os.system('cd {} && git clone {} {}'.format(working_directory, repository.url, repository.name))
    return Repo('{}/{}'.format(working_directory, repository.name))


def commits_between_start_and_end(repository: Repo, definition: RepositoryDefinition, ) -> list:
    start_commit = repository.commit(definition.start)
    print('start [{}]: {} - {}'.format(definition.start, start_commit, start_commit.message))
    end_commit = repository.commit(definition.end)
    print('  end [{}]: {} - {}'.format(definition.end, end_commit, end_commit.message))
    print()

    relevant_commits = []
    for commit in repository.iter_commits(end_commit.hexsha):
        relevant_commits.append(commit)
        if commit.hexsha == start_commit.hexsha:
            break
    relevant_commits.reverse()

    for commit in relevant_commits:
        print('{}: {}'.format(commit.hexsha, commit.message))
    print()

    return relevant_commits


def get_base_directory() -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', default='.', help='name of the directory to use')
    args = parser.parse_args()
    return Path(str(args.d))


def create_working_directory() -> Path:
    directory = base_directory.joinpath(str(uuid.uuid4()))
    directory.mkdir()
    return directory


# SCRIPT START

base_directory = get_base_directory()
assert base_directory.is_dir()

with base_directory.joinpath('config.json').open('r') as jsonFile:
    execute(json.load(jsonFile))

# SCRIPT END
