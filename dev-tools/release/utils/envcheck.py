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

# Reads the given file and applies the
# callback to it. If the callback changed
# a line the given file is replaced with
# the modified input.

import os
from functools import partial
from ..maven import mvn
import subprocess

env = os.environ

# console colors
OKGREEN = '\033[92m'
OKWARN = '\033[93m'
ENDC = '\033[0m'
FAIL = '\033[91m'


def check_command_exists(name, cmd):
    try:
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        raise RuntimeError('Could not run command %s - please make sure it is installed' % (name))


def run_and_print(text, run_function, optional=False):
    try:
        print(text, end='')
        run_function()
        print(OKGREEN + 'OK' + ENDC)
    except RuntimeError:
        if optional:
            print(OKWARN + 'NOT PRESENT' + ENDC)
        else:
            print(FAIL + 'FAILED' + ENDC)


def check_env_var(text, env_var, optional=False):
    try:
        print(text, end='')
        value = env[env_var]
        print(OKGREEN + 'OK' + ENDC)
    except KeyError:
        if optional:
            print(OKWARN + 'NOT PRESENT' + ENDC)
        else:
            print(FAIL + 'FAILED' + ENDC)


def check_environment_and_commandline_tools():
    check_env_var('Checking for AWS env configuration AWS_SECRET_ACCESS_KEY...        ', 'AWS_SECRET_ACCESS_KEY')
    check_env_var('Checking for AWS env configuration AWS_ACCESS_KEY_ID...            ', 'AWS_ACCESS_KEY_ID')
    check_env_var('Checking for Github env configuration GITHUB_LOGIN...              ', 'GITHUB_LOGIN', True)
    check_env_var('Checking for Github env configuration GITHUB_PASSWORD...           ', 'GITHUB_PASSWORD', True)
    check_env_var('Checking for Github env configuration GITHUB_KEY...                ', 'GITHUB_KEY', True)
    check_env_var('Checking for Email settings MAIL_SENDER...                         ', 'MAIL_SENDER')
    check_env_var('Checking for Email settings MAIL_TO...                             ', 'MAIL_TO', True)
    check_env_var('Checking for Email settings SMTP_SERVER...                         ', 'SMTP_SERVER', True)
    # check_env_var('Checking for SONATYPE env configuration SONATYPE_USERNAME...       ', 'SONATYPE_USERNAME')
    # check_env_var('Checking for SONATYPE env configuration SONATYPE_PASSWORD...       ', 'SONATYPE_PASSWORD')
    # check_env_var('Checking for GPG env configuration GPG_KEY_ID...                   ', 'GPG_KEY_ID')
    # check_env_var('Checking for GPG env configuration GPG_PASSPHRASE...               ', 'GPG_PASSPHRASE')
    # check_env_var('Checking for S3 repo upload env configuration S3_BUCKET_SYNC_TO... ', 'S3_BUCKET_SYNC_TO')
    # check_env_var('Checking for git env configuration GIT_AUTHOR_NAME...              ', 'GIT_AUTHOR_NAME')
    # check_env_var('Checking for git env configuration GIT_AUTHOR_EMAIL...             ', 'GIT_AUTHOR_EMAIL')

    run_and_print('Checking command: gpg...            ', partial(check_command_exists, 'gpg', 'gpg --version'))
    run_and_print('Checking command: expect...         ', partial(check_command_exists, 'expect', 'expect -v'))
    # run_and_print('Checking command: createrepo...     ', partial(check_command_exists, 'createrepo', 'createrepo --version'))
    run_and_print('Checking command: s3cmd...          ', partial(check_command_exists, 's3cmd', 's3cmd --version'))
    # run_and_print('Checking command: apt-ftparchive... ', partial(check_command_exists, 'apt-ftparchive', 'apt-ftparchive --version'))

    # boto, check error code being returned
    location = os.path.dirname(os.path.realpath(__file__))
    command = 'python %s/upload-s3.py' % location
    run_and_print('Testing boto python dependency...   ', partial(check_command_exists, 'python-boto', command))

    run_and_print('Checking java version...            ', partial(mvn.verify_java_version, '1.7'))
    run_and_print('Checking java mvn version...        ', partial(mvn.verify_mvn_java_version, '1.7', mvn.MVN))


