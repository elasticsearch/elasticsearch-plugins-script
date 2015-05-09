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
import re
from os.path import dirname, abspath

from ..utils import run
from ..utils import strings

ROOT_DIR = abspath(os.path.join(abspath(dirname(__file__)), '../'))
POM_FILE = ROOT_DIR + '/pom.xml'

env = os.environ
try:
    JAVA_HOME = env['JAVA_HOME']
except KeyError:
    raise RuntimeError("""
  Please set JAVA_HOME in the env before running release tool
  On OSX use: export JAVA_HOME=`/usr/libexec/java_home -v '1.7*'`""")

try:
    MVN = 'mvn'
    # make sure mvn3 is used if mvn3 is available
    # some systems use maven 2 as default
    run.run('mvn3 --version', quiet=True)
    MVN = 'mvn3'
except RuntimeError:
    pass


def java_exe():
    path = JAVA_HOME
    return 'export JAVA_HOME="%s" PATH="%s/bin:$PATH" JAVACMD="%s/bin/java"' % (path, path, path)


def verify_java_version(version):
    s = os.popen('%s; java -version 2>&1' % java_exe()).read()
    if ' version "%s.' % version not in s:
        raise RuntimeError('got wrong version for java %s:\n%s' % (version, s))


def verify_mvn_java_version(version, mvn):
    s = os.popen('%s; %s --version 2>&1' % (java_exe(), mvn)).read()
    if 'Java version: %s' % version not in s:
        raise RuntimeError('got wrong java version for %s %s:\n%s' % (mvn, version, s))


# Run a given maven command
def run_mvn(*cmd):
    for c in cmd:
        run.run('%s; %s -f %s %s' % (java_exe(), MVN, POM_FILE, c))


# Maven clean
def clean():
    run_mvn('clean')


# Run deploy or package depending on dry_run
# Default to run mvn package
# When run_tests=True a first mvn clean test is run
def build_release(run_tests=False, dry_run=True):
    target = 'deploy'
    tests = '-DskipTests'
    if run_tests:
        tests = ''
    if dry_run:
        target = 'package'
    run_mvn('clean %s %s' % (target, tests))


# Guess the next snapshot version number (increment last digit)
def guess_snapshot(version):
    digits = strings.split_version_to_digits(version)
    source = '%s.%s.%s' % (digits[0], digits[1], digits[2])
    destination = '%s.%s.%s' % (digits[0], digits[1], digits[2] + 1)
    return version.replace(source, destination)


# Checks the pom.xml for the release version. <version>2.0.0-SNAPSHOT</version>
# This method fails if the pom file has no SNAPSHOT version set ie.
# if the version is already on a release version we fail.
# Returns the next version string ie. 0.90.7
def find_release_version(src_branch):
    with open(POM_FILE, encoding='utf-8') as file:
        for line in file:
            match = re.search(r'<version>(.+)-SNAPSHOT</version>', line)
            if match:
                return match.group(1)
        raise RuntimeError('Could not find release version in branch %s' % src_branch)


# extract a value from pom.xml after a given line
def find_from_pom(tag, first_line=None):
    with open(POM_FILE, encoding='utf-8') as file:
        previous_line_matched = False
        if first_line is None:
            previous_line_matched = True
        for line in file:
            if previous_line_matched:
                match = re.search(r'<%s>(.+)</%s>' % (tag, tag), line)
                if match:
                    return match.group(1)

            if first_line is not None:
                match = re.search(r'%s' % first_line, line)
                if match:
                    previous_line_matched = True

        if first_line is not None:
            raise RuntimeError('Could not find %s in pom.xml file after %s' % (tag, first_line))
        else:
            raise RuntimeError('Could not find %s in pom.xml file' % tag)


# Get artifacts which have been generated in target/releases
def get_artifacts(artifact_id, release):
    artifact_path = ROOT_DIR + '/target/releases/%s-%s.zip' % (artifact_id, release)
    print('  Path %s' % artifact_path)
    if not os.path.isfile(artifact_path):
        raise RuntimeError('Could not find required artifact at %s' % artifact_path)
    return artifact_path

