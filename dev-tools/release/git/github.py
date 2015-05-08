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

import github3
import os

"""
Depends on github3 module which must be installed first
    - github3 module (pip-3.3 install github3.py)

Usage

from release.git import github

# Define your repository using the "repository name"
github.get_github_repository("elasticsearch")

# You can also use a specific owner instead of default elastic one
github.get_github_repository("elasticsearch", owner="elastic")

It's better to define either GITHUB_LOGIN / GITHUB_PASSWORD
or GITHUB_KEY system variable so you won't have a limited number of API anonymous calls
see https://github.com/settings/applications#personal-access-tokens

Or you can also pass them when creating the repository:
github.get_github_repository("elasticsearch", login="foo", password="bar")
github.get_github_repository("elasticsearch", key="mygithubaccesskey")

# Raise an error if there are remaining issues with label v2.0.0
github.check_opened_issues("v2.0.0")

# List all issues for version labelled "v2.0.0" and default label "bug"
github.list_issues("v2.0.0")

# List all issues for version labelled "v2.0.0" and label "feature"
github.list_issues("v2.0.0", severity='feature')
"""

env = os.environ

# Create a Github repository instance to access issues
def get_github_repository(reponame,
                          owner="elastic",
                          login=env.get('GITHUB_LOGIN', None),
                          password=env.get('GITHUB_PASSWORD', None),
                          key=env.get('GITHUB_KEY', None)):
    global repo_owner, repo_name, repository
    repo_owner = owner
    repo_name = reponame

    if login:
            g = github3.login(login, password)
    elif key:
        g = github3.login(token=key)
    else:
        g = github3.GitHub()

    repository = g.repository(owner, reponame)


# Check if there are some remaining open issues and fails
def check_opened_issues(version):
    global repo_owner, repo_name, repository
    opened_issues = [i for i in repository.iter_issues(state='open', labels='%s' % version)]
    if len(opened_issues) > 0:
        raise NameError(
            'Some issues [%s] are still opened. Check https://github.com/%s/%s/issues?labels=%s&state=open'
            % (len(opened_issues), repo_owner, repo_name, version))


# List issues from github: can be done anonymously if you don't
# exceed a given number of github API calls per day
def list_issues(version,
                severity='bug'):
    global repository
    issues = [i for i in repository.iter_issues(state='closed', labels='%s,%s' % (severity, version))]
    return issues
