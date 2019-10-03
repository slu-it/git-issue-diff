import argparse
import json
import os
import os.path
import re
import shutil
import string
import uuid
from pathlib import Path
from typing import List

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


class DiffSummary:
    def __init__(self, start_commit: Commit, end_commit: Commit, relevant_commits: List[Commit]):
        self.start_commit = start_commit
        self.end_commit = end_commit
        self.commits = relevant_commits


def get_base_directory() -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', default='.', help='name of the directory to use')
    args = parser.parse_args()
    return Path(str(args.d))


def create_working_directory() -> Path:
    directory = base_directory.joinpath(str(uuid.uuid4()))
    directory.mkdir()
    return directory


def execute(working_directory: Path, configuration: dict):
    for definition in map(RepositoryDefinition, configuration['repositories']):
        if not definition.active:
            continue

        repository = clone(working_directory, definition)
        diff_summary = diff_between_start_and_end(repository, definition)

        relevant_messages = map(lambda c: c.message, diff_summary.commits)

        issue_keys = set([])
        for message in relevant_messages:
            for found in re.findall(configuration['issueKeyPattern'], message):
                issue_keys.add(found)

        print_result(definition, diff_summary, issue_keys)


def clone(working_directory: Path, repository: RepositoryDefinition) -> Repo:
    os.system('cd {} && git clone {} {}'.format(working_directory, repository.url, repository.name))
    return Repo('{}/{}'.format(working_directory, repository.name))


def diff_between_start_and_end(repository: Repo, definition: RepositoryDefinition, ) -> DiffSummary:
    start_commit = repository.commit(definition.start) if definition.start is not None else None
    start_commit_hexsha = start_commit.hexsha if start_commit is not None else None

    end_commit = repository.commit(definition.end) if definition.end is not None else None
    end_commit_hexsha = end_commit.hexsha if end_commit is not None else None

    relevant_commits = []
    for commit in repository.iter_commits(end_commit_hexsha):
        relevant_commits.append(commit)
        if commit.hexsha == start_commit_hexsha:
            break

    relevant_commits.reverse()

    return DiffSummary(start_commit, end_commit, relevant_commits)


def print_result(definition, diff_summary, issue_keys):
    print()
    print('### PROCESSING {} ###'.format(definition.name))
    print()
    if diff_summary.start_commit is not None:
        c = diff_summary.start_commit
        print('start [{}]: {} - {}'.format(definition.start, short_sha(c), c.message))
    else:
        print('start [None]')
    if diff_summary.end_commit is not None:
        c = diff_summary.end_commit
        print('  end [{}]: {} - {}'.format(definition.start, short_sha(c), c.message))
    else:
        print('  end [None]')
    print()
    for c in diff_summary.commits:
        print('{} - {}'.format(short_sha(c), c.message))
    print()
    print('Issue Keys: {}'.format(', '.join(issue_keys)))


def short_sha(commit: Commit, length: int = 10) -> string:
    return commit.hexsha[:length]


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
