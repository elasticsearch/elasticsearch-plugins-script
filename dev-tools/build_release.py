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

import re
import os
import argparse
import subprocess
import sys

from functools import partial

from os.path import dirname, abspath
from release.logger import logger
from release.git import github
from release.git import git
from release.announcement import announcement
from release.utils import run
from release.utils import checksums
from release.documentation import doc_update
from release.maven import mvn

"""
 This tool builds a release from the a given elasticsearch plugin branch.
 In order to execute it go in the top level directory and run:
   $ python3 dev_tools/build_release.py --branch master --publish --remote origin

 By default this script runs in 'dry' mode which essentially simulates a release. If the
 '--publish' option is set the actual release is done.
 If not in 'dry' mode, a mail will be automatically sent to the mailing list.
 You can disable it with the option  '--disable_mail'

   $ python3 dev_tools/build_release.py --publish --remote origin --disable_mail

 The script takes over almost all
 steps necessary for a release from a high level point of view it does the following things:

  - run prerequisite checks ie. check for S3 credentials available as env variables
  - detect the version to release from the specified branch (--branch) or the current branch
  - check that github issues related to the version are closed
  - creates a version release branch & updates pom.xml to point to a release version rather than a snapshot
  - creates a master release branch & updates README.md to point to the latest release version for the given elasticsearch branch
  - builds the artifacts
  - commits the new version and merges the version release branch into the source branch
  - merges the master release branch into the master branch
  - creates a tag and pushes branch and master to the specified origin (--remote)
  - publishes the releases to sonatype and S3
  - send a mail based on github issues fixed by this version

Once it's done it will print all the remaining steps.

 Prerequisites:
    - Python 3k for script execution
    - Boto for S3 Upload ($ apt-get install python-boto or pip-3.3 install boto)
    - github3 module (pip-3.3 install github3.py)
    - S3 keys exported via ENV Variables (AWS_ACCESS_KEY_ID,  AWS_SECRET_ACCESS_KEY)
    - GITHUB (login/password) or key exported via ENV Variables (GITHUB_LOGIN,  GITHUB_PASSWORD or GITHUB_KEY)
    (see https://github.com/settings/applications#personal-access-tokens) - Optional: default to no authentication
    - SMTP_HOST - Optional: default to localhost
    - MAIL_SENDER - Optional: default to 'david@pilato.fr': must be authorized to send emails to elasticsearch mailing list
    - MAIL_TO - Optional: default to 'discuss%2Bannouncements@elastic.co'
"""
env = os.environ

ROOT_DIR = abspath(os.path.join(abspath(dirname(__file__)), '../'))
README_FILE = ROOT_DIR + '/README.md'
POM_FILE = ROOT_DIR + '/pom.xml'
DEV_TOOLS_DIR = ROOT_DIR + '/plugin_tools'

# console colors
OKGREEN = '\033[92m'
OKWARN = '\033[93m'
ENDC = '\033[0m'
FAIL = '\033[91m'


##########################################################
#
# Clean logs
#
##########################################################
logger.purge_log()


##########################################################
#
# String and file manipulation utils
#
##########################################################
# Get artifacts which have been generated in target/releases
def get_artifacts(artifact_id, release):
    artifact_path = ROOT_DIR + '/target/releases/%s-%s.zip' % (artifact_id, release)
    print('  Path %s' % artifact_path)
    if not os.path.isfile(artifact_path):
        raise RuntimeError('Could not find required artifact at %s' % artifact_path)
    return artifact_path


##########################################################
#
# Amazon S3 publish commands
#
##########################################################
# Upload files to S3
def publish_artifacts(artifacts, base='elasticsearch/elasticsearch', dry_run=True):
    location = os.path.dirname(os.path.realpath(__file__))
    for artifact in artifacts:
        if dry_run:
            print('Skip Uploading %s to Amazon S3 in %s' % (artifact, base))
        else:
            print('Uploading %s to Amazon S3' % artifact)
            # requires boto to be installed but it is not available on python3k yet so we use a dedicated tool
            run.run('python %s/upload-s3.py --file %s --path %s' % (location, os.path.abspath(artifact), base))


def print_sonatype_notice():
    settings = os.path.join(os.path.expanduser('~'), '.m2/settings.xml')
    if os.path.isfile(settings):
        with open(settings, encoding='utf-8') as settings_file:
            for line in settings_file:
                if line.strip() == '<id>sonatype-nexus-snapshots</id>':
                    # moving out - we found the indicator no need to print the warning
                    return
    print("""
    NOTE: No sonatype settings detected, make sure you have configured
    your sonatype credentials in '~/.m2/settings.xml':

    <settings>
    ...
    <servers>
      <server>
        <id>sonatype-nexus-snapshots</id>
        <username>your-jira-id</username>
        <password>your-jira-pwd</password>
      </server>
      <server>
        <id>sonatype-nexus-staging</id>
        <username>your-jira-id</username>
        <password>your-jira-pwd</password>
      </server>
    </servers>
    ...
  </settings>
  """)


def check_s3_credentials():
    if not env.get('AWS_ACCESS_KEY_ID', None) or not env.get('AWS_SECRET_ACCESS_KEY', None):
        raise RuntimeError(
            'Could not find "AWS_ACCESS_KEY_ID" / "AWS_SECRET_ACCESS_KEY" in the env variables please export in order to upload to S3')


def check_command_exists(name, cmd):
    try:
        print('%s' % cmd)
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
        env[env_var]
        print(OKGREEN + 'OK' + ENDC)
    except KeyError:
        if optional:
            print(OKWARN + 'NOT PRESENT' + ENDC)
        else:
            print(FAIL + 'FAILED' + ENDC)


def check_environment_and_commandline_tools():
    check_env_var('Checking for AWS env configuration AWS_SECRET_ACCESS_KEY_ID...     ', 'AWS_SECRET_ACCESS_KEY')
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Builds and publishes a Elasticsearch Plugin Release')
    parser.add_argument('--branch', '-b', metavar='master', default=git.get_current_branch(),
                        help='The branch to release from. Defaults to the current branch.')
    parser.add_argument('--skiptests', '-t', dest='tests', action='store_false',
                        help='Skips tests before release. Tests are run by default.')
    parser.set_defaults(tests=True)
    parser.add_argument('--remote', '-r', metavar='origin', default='origin',
                        help='The remote to push the release commit and tag to. Default is [origin]')
    parser.add_argument('--publish', '-p', dest='dryrun', action='store_false',
                        help='Publishes the release. Disable by default.')
    parser.add_argument('--disable_mail', '-dm', dest='mail', action='store_false',
                        help='Do not send a release email. Email is sent by default.')
    parser.add_argument('--check', dest='check', action='store_true',
                        help='Checks and reports for all requirements and then exits')

    parser.set_defaults(dryrun=True)
    parser.set_defaults(mail=True)
    parser.set_defaults(check=False)
    args = parser.parse_args()

    src_branch = args.branch
    remote = args.remote
    run_tests = args.tests
    dry_run = args.dryrun
    mail = args.mail

    if args.check:
        check_environment_and_commandline_tools()
        sys.exit(0)

    if src_branch == 'master':
        raise RuntimeError('Can not release the master branch. You need to create another branch before a release')

    # we print a notice if we can not find the relevant infos in the ~/.m2/settings.xml
    print_sonatype_notice()

    if not dry_run:
        check_s3_credentials()
        print('WARNING: dryrun is set to "false" - this will push and publish the release')
        if mail:
            print('An email to %s will be sent after the release'
                  % env.get('MAIL_TO', 'discuss%2Bannouncements@elastic.co'))
        input('Press Enter to continue...')

    print(''.join(['-' for _ in range(80)]))
    print('Preparing Release from branch [%s] running tests: [%s] dryrun: [%s]' % (src_branch, run_tests, dry_run))
    print('  JAVA_HOME is [%s]' % mvn.JAVA_HOME)
    print('  Running with maven command: [%s] ' % mvn.MVN)

    git.checkout(src_branch)
    release_version = mvn.find_release_version(src_branch)
    artifact_id = mvn.find_from_pom('artifactId')
    artifact_name = mvn.find_from_pom('name')
    artifact_description = mvn.find_from_pom('description')
    project_url = mvn.find_from_pom('url')

    try:
        elasticsearch_version = mvn.find_from_pom('elasticsearch.version')
    except RuntimeError:
        # With projects using elasticsearch-parent project, we need to consider elasticsearch version
        # to be after <artifactId>elasticsearch-parent</artifactId>
        elasticsearch_version = mvn.find_from_pom('version', '<artifactId>elasticsearch-parent</artifactId>')

    print('  Artifact Id: [%s]' % artifact_id)
    print('  Release version: [%s]' % release_version)
    print('  Elasticsearch: [%s]' % elasticsearch_version)
    if elasticsearch_version.find('-SNAPSHOT') != -1:
        raise RuntimeError('Can not release with a SNAPSHOT elasticsearch dependency: %s' % elasticsearch_version)

    # extract snapshot
    default_snapshot_version = mvn.guess_snapshot(release_version)
    snapshot_version = input('Enter next snapshot version [%s]:' % default_snapshot_version)
    snapshot_version = snapshot_version or default_snapshot_version

    print('  Next version: [%s-SNAPSHOT]' % snapshot_version)
    print('  Artifact Name: [%s]' % artifact_name)
    print('  Artifact Description: [%s]' % artifact_description)
    print('  Project URL: [%s]' % project_url)

    if not dry_run:
        smoke_test_version = release_version

    try:
        git.checkout('master')
        master_hash = git.get_head_hash()
        git.checkout(src_branch)
        version_hash = git.get_head_hash()
        mvn.clean()  # clean the env!
        git.create_release_branch(remote, 'master', release_version)
        print('  Created release branch [%s]' % (git.release_branch('master', release_version)))
        git.create_release_branch(remote, src_branch, release_version)
        print('  Created release branch [%s]' % (git.release_branch(src_branch, release_version)))
    except RuntimeError:
        logger.print_log()
        sys.exit(-1)

    success = False
    try:
        ########################################
        # Start update process in version branch
        ########################################
        pending_files = [POM_FILE, README_FILE]
        doc_update.remove_maven_snapshot(POM_FILE, release_version)
        doc_update.update_documentation_in_released_branch(README_FILE, release_version, elasticsearch_version)
        print('  Done removing snapshot version')
        git.add_pending_files(*pending_files)  # expects var args use * to expand
        git.commit_release(artifact_id, release_version)
        print('  Committed release version [%s]' % release_version)
        print(''.join(['-' for _ in range(80)]))
        print('Building Release candidate')
        input('Press Enter to continue...')
        print('  Checking github issues')
        github.get_github_repository(artifact_id)
        github.check_opened_issues(release_version)
        if not dry_run:
            print('  Running maven builds now and publish to sonatype - run-tests [%s]' % run_tests)
        else:
            print('  Running maven builds now run-tests [%s]' % run_tests)
        mvn.build_release(run_tests=run_tests, dry_run=dry_run)
        artifact = get_artifacts(artifact_id, release_version)
        artifact_and_checksums = checksums.generate_checksums(artifact)
        print(''.join(['-' for _ in range(80)]))

        ########################################
        # Start update process in master branch
        ########################################
        git.checkout(git.release_branch('master', release_version))
        doc_update.update_documentation_to_released_version(README_FILE, project_url, release_version, src_branch,
                                                 elasticsearch_version)
        doc_update.set_install_instructions(README_FILE, artifact_id, release_version)
        git.add_pending_files(*pending_files)  # expects var args use * to expand
        git.commit_master(release_version)

        print('Finish Release -- dry_run: %s' % dry_run)
        input('Press Enter to continue...')

        print('  merge release branch')
        git.merge(src_branch, release_version)
        print('  tag')
        git.tag_release(release_version)

        doc_update.add_maven_snapshot(POM_FILE, release_version, snapshot_version)
        doc_update.update_documentation_in_released_branch(README_FILE, '%s-SNAPSHOT' % snapshot_version, elasticsearch_version)
        git.add_pending_files(*pending_files)
        git.commit_snapshot()

        print('  merge master branch')
        git.merge('master', release_version)

        print('  push to %s %s -- dry_run: %s' % (remote, src_branch, dry_run))
        git.push(remote, src_branch, release_version, dry_run)
        print('  publish artifacts to S3 -- dry_run: %s' % dry_run)
        publish_artifacts(artifact_and_checksums, base='elasticsearch/%s' % (artifact_id) , dry_run=dry_run)
        print('  preparing email (from github issues)')
        msg = announcement.prepare_email(artifact_id, release_version, artifact_name, artifact_description, project_url)
        input('Press Enter to send email...')
        print('  sending email -- dry_run: %s, mail: %s' % (dry_run, mail))
        announcement.send_email(msg, dry_run=dry_run, mail=mail)

        pending_msg = """
Release successful pending steps:
    * close and release sonatype repo: https://oss.sonatype.org/
    * check if the release is there https://oss.sonatype.org/content/repositories/releases/org/elasticsearch/%(artifact_id)s/%(version)s
    * tweet about the release
"""
        print(pending_msg % {'version': release_version,
                             'artifact_id': artifact_id,
                             'project_url': project_url})
        success = True
    finally:
        if not success:
            logger.print_log()
            git.checkout('master')
            run.run('git reset --hard %s' % master_hash)
            git.checkout(src_branch)
            run.run('git reset --hard %s' % version_hash)
            try:
                run.run('git tag -d v%s' % release_version)
            except RuntimeError:
                pass
        elif dry_run:
            print('End of dry_run')
            input('Press Enter to reset changes...')
            git.checkout('master')
            run.run('git reset --hard %s' % master_hash)
            git.checkout(src_branch)
            run.run('git reset --hard %s' % version_hash)
            run.run('git tag -d v%s' % release_version)

        # we delete this one anyways
        run.run('git branch -D %s' % (git.release_branch('master', release_version)))
        run.run('git branch -D %s' % (git.release_branch(src_branch, release_version)))

        # Checkout the branch we started from
        git.checkout(src_branch)
