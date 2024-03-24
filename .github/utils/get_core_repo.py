# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import itertools
import json
import os
import re
import subprocess
import sys


CORE = sys.argv[1]
SCOPE = sys.argv[2]
CORE_USER, CORE_REPO = CORE.split('/')


def lookup_via_referenced_prs():
    this_pr_body = os.environ['PR_BODY']
    this_base_ref = os.environ['PR_BASE_REF']

    referenced_prs = set()
    for match in itertools.chain(
        re.finditer(r'(?:(?<![/\w.-])(\w[\w.-]+)/(\w[\w.-]+)|\B)#([1-9]\d*)\b', this_pr_body),
        re.finditer(r'\bhttps://github\.com/([^/]+)/([^/]+)/pull/([1-9]\d*)\b', this_pr_body)
    ):
        user, repo, num = match.groups()
        if user != CORE_USER or repo != CORE_REPO:
            continue
        referenced_prs.add(int(num))

    print(f'Referenced core PRs: {referenced_prs or "none"}')
    if not referenced_prs:
        return None

    candidates = {}
    for num in referenced_prs:
        try:
            resp = subprocess.check_output(['gh', 'api', f'repos/{CORE}/pulls/{num}'], encoding='utf-8')
        except subprocess.CalledProcessError:
            print(f'Discarding {num}: not found (probably an issue and not a PR)')
            continue
        pr_data = json.loads(resp)
        if pr_data['state'] != 'open':
            print(f'Discarding {num}: not open')
            continue
        head_ref = pr_data['head']['ref']
        head_repo = pr_data['head']['repo']['full_name']
        base_ref = pr_data['base']['ref']
        if base_ref != this_base_ref:
            print(f'Discarding {num}: different base branches ({base_ref} != {this_base_ref})')
            continue
        candidates[num] = (head_repo, head_ref)

    print(f'Viable core PRs: {",".join(map(str, candidates)) or "none"}')
    if len(candidates) > 1:
        print('Found multiple PRs, not guessing which one to use')
        # Fail the CI run - if this ever happens, we may be able to come up with suitable logic to pick one
        sys.exit(1)
    elif not candidates:
        print('Found no suitable PRs')
        return None
    return candidates.popitem()[1]


def main():
    gh_event = os.environ['GITHUB_EVENT_NAME']
    check_common_branch = True
    if gh_event == 'push':
        full_repo = CORE
        branch = os.environ['GITHUB_REF'].removeprefix('refs/heads/')
        print(f'Using current branch: {branch}')
    elif gh_event == 'pull_request':
        if res := lookup_via_referenced_prs():
            full_repo, branch = res
            check_common_branch = False
            print(f'Using branch from referenced core PR: {full_repo}:{branch}')
        else:
            full_repo = CORE
            branch = os.environ['GITHUB_BASE_REF'].removeprefix('refs/heads/')
            print(f'Using branch from PR target: {branch}')
    else:
        print(f'Unsupported event: {gh_event}')
        return 1

    if check_common_branch and branch != 'master' and not branch.endswith('.x'):
        print(f'Uncommon branch {branch}; defaulting to master')
        branch = 'master'

    with open(os.environ['GITHUB_ENV'], 'a') as f:
        f.write(f'{SCOPE}_REPO={full_repo}\n')
        f.write(f'{SCOPE}_BRANCH={branch}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
