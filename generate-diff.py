import argparse
import json
import os
import os.path
import re
import shutil
import string
import uuid
from pathlib import Path

from git import Repo
from git import Commit


class RepositoryDefinition:
    def __init__(self, data: dict):
        self.name = str(data['name'])
        self.url = str(data['url'])
        self.active = bool(data['active'])

        diff = data.get('diff')
        self.start = dict(diff).get('start') if diff is not None else None
        self.end = dict(diff).get('end') if diff is not None else None


def execute(working_directory: Path, configuration: dict):
    for definition in map(RepositoryDefinition, configuration['repositories']):
        if not definition.active:
            continue

        print()
        print('### PROCESSING {} ###'.format(definition.name))
        print()

        repository = clone(working_directory, definition)

        relevant_messages = []
        for commit in commits_between_start_and_end(repository, definition):
            relevant_messages.append(commit.message)

        issue_keys = set([])
        for message in relevant_messages:
            for found in re.findall(configuration['issueKeyPattern'], message):
                issue_keys.add(found)

        print()
        print('Issue Keys: {}'.format(', '.join(issue_keys)))


def clone(working_directory: Path, repository: RepositoryDefinition) -> Repo:
    os.system('cd {} && git clone {} {}'.format(working_directory, repository.url, repository.name))
    return Repo('{}/{}'.format(working_directory, repository.name))


def commits_between_start_and_end(repository: Repo, definition: RepositoryDefinition, ) -> list:
    start_commit_hexsha = None
    if definition.start is not None:
        start_commit = repository.commit(definition.start)
        start_commit_hexsha = start_commit.hexsha
        print('start [{}]: {} - {}'.format(definition.start, short_sha(start_commit), start_commit.message))
    else:
        print('start [None]')

    end_commit_hexsha = None
    if definition.end is not None:
        end_commit = repository.commit(definition.end)
        end_commit_hexsha = end_commit.hexsha
        print('  end [{}]: {} - {}'.format(definition.end, short_sha(end_commit), end_commit.message))
    else:
        print('  end [None]')

    print()

    relevant_commits = []
    for commit in repository.iter_commits(end_commit_hexsha):
        relevant_commits.append(commit)
        if commit.hexsha == start_commit_hexsha:
            break
    relevant_commits.reverse()

    for commit in relevant_commits:
        print('{} - {}'.format(short_sha(commit), commit.message))

    return relevant_commits


def short_sha(commit: Commit, length: int = 10) -> string:
    return commit.hexsha[:length]


def create_working_directory() -> Path:
    directory = base_directory.joinpath(str(uuid.uuid4()))
    directory.mkdir()
    return directory


def get_base_directory() -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', default='.', help='name of the directory to use')
    args = parser.parse_args()
    return Path(str(args.d))


# SCRIPT START

base_directory = get_base_directory()
assert base_directory.is_dir()

with base_directory.joinpath('config.json').open('r') as jsonFile:
    cfg = json.load(jsonFile)
    wd = create_working_directory()
    try:
        execute(wd, cfg)
    finally:
        shutil.rmtree(wd)

# SCRIPT END
