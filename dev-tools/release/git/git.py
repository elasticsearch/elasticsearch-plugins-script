# Licensed to Elasticsearch under one or more contributor
# license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright
# ownership. Elasticsearch licenses this file to you under
# the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance  with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on
# an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import os

from ..utils import run


# Returns the hash of the current git HEAD revision
def get_head_hash():
    return os.popen('git rev-parse --verify HEAD 2>&1').read().strip()


# Returns the name of the current branch
def get_current_branch():
    return os.popen('git rev-parse --abbrev-ref HEAD  2>&1').read().strip()


# runs get fetch on the given remote
def fetch(remote):
    run.run('git fetch %s' % remote)


# Creates a new release branch from the given source branch
# and rebases the source branch from the remote before creating
# the release branch. Note: This fails if the source branch
# doesn't exist on the provided remote.
def create_release_branch(remote, src_branch, release):
    checkout(src_branch)
    run.run('git pull --rebase %s %s' % (remote, src_branch))
    run.run('git checkout -b %s' % (release_branch(src_branch, release)))


# Stages the given files for the next git commit
def add_pending_files(*files):
    for file in files:
        run.run('git add %s' % file)


# Executes a git commit with 'release [version]' as the commit message
def commit_release(artifact_id, release):
    run.run('git commit -m "prepare release %s-%s"' % (artifact_id, release))


# Commit documentation changes on the master branch
def commit_master(release):
    run.run('git commit -m "update documentation with release %s"' % release)


# Commit next snapshot files
def commit_snapshot():
    run.run('git commit -m "prepare for next development iteration"')


# Put the version tag on on the current commit
def tag_release(release):
    run.run('git tag -a v%s -m "Tag release version %s"' % (release, release))


# Checkout a given branch
def checkout(branch):
    run.run('git checkout %s' % branch)


# Merge the release branch with the actual branch
def merge(src_branch, release_version):
    checkout(src_branch)
    run('git merge %s' % release_branch(src_branch, release_version))


# Push the actual branch and master branch
def push(remote, src_branch, release_version, dry_run):
    if not dry_run:
        run.run('git push %s %s master' % (remote, src_branch))  # push the commit and the master
        run.run('git push %s v%s' % (remote, release_version))  # push the tag
    else:
        print('  dryrun [True] -- skipping push to remote %s %s master' % (remote, src_branch))

# Utility that returns the name of the release branch for a given version
def release_branch(branchsource, version):
    return 'release_branch_%s_%s' % (branchsource, version)
