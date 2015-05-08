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

from ..fileupdater import updater
from ..utils import strings

# Moves the pom.xml file from a snapshot to a release
def remove_maven_snapshot(pom, release):
    pattern = '<version>%s-SNAPSHOT</version>' % release
    replacement = '<version>%s</version>' % release

    def callback(line):
        return line.replace(pattern, replacement)

    updater.process_file(pom, callback)


# Moves the pom.xml file to the next snapshot
def add_maven_snapshot(pom, release, snapshot):
    pattern = '<version>%s</version>' % release
    replacement = '<version>%s-SNAPSHOT</version>' % snapshot

    def callback(line):
        return line.replace(pattern, replacement)

    updater.process_file(pom, callback)


# Moves the README.md file from a snapshot to a release version. Doc looks like:
# ## Version 2.5.0-SNAPSHOT for Elasticsearch: 1.x
# It needs to be updated to
# ## Version 2.5.0 for Elasticsearch: 1.x
def update_documentation_in_released_branch(readme_file, release, esversion):
    pattern = '## Version (.)+ for Elasticsearch: (.)+'
    es_digits = strings.split_version_to_digits(esversion)
    replacement = '## Version %s for Elasticsearch: %s.%s\n' % (
        release, es_digits[0], es_digits[1])

    def callback(line):
        # If we find pattern, we replace its content
        if re.search(pattern, line) is not None:
            return replacement
        else:
            return line

    updater.process_file(readme_file, callback)


# Moves the README.md file from a snapshot to a release (documentation link)
# We need to find the right branch we are on and update the line
#        |    es-1.3              | Build from source | [2.4.0-SNAPSHOT](https://github.com/elasticsearch/elasticsearch-cloud-azure/tree/es-1.3/#version-240-snapshot-for-elasticsearch-13)     |
#        |    es-1.2              |     2.3.0         | [2.3.0](https://github.com/elasticsearch/elasticsearch-cloud-azure/tree/v2.3.0/#version-230-snapshot-for-elasticsearch-13)              |
def update_documentation_to_released_version(readme_file, repo_url, release, branch, esversion):
    pattern = '%s' % branch
    replacement = '|    %s              |     %s         | [%s](%stree/v%s/%s)                  |\n' % (
        branch, release, release, repo_url, release, get_doc_anchor(release, esversion))

    def callback(line):
        # If we find pattern, we replace its content
        if line.find(pattern) >= 0:
            return replacement
        else:
            return line

    updater.process_file(readme_file, callback)


# Update installation instructions in README.md file
def set_install_instructions(readme_file, artifact_name, release):
    pattern = 'bin/plugin -?install elasticsearch/%s/.+' % artifact_name
    replacement = 'bin/plugin install elasticsearch/%s/%s' % (artifact_name, release)

    def callback(line):
        return re.sub(pattern, replacement, line)

    updater.process_file(readme_file, callback)


# Guess the anchor in generated documentation
# Looks like this "#version-230-for-elasticsearch-13"
def get_doc_anchor(release, esversion):
    plugin_digits = strings.split_version_to_digits(release)
    es_digits = strings.split_version_to_digits(esversion)
    return '#version-%s%s%s-for-elasticsearch-%s%s' % (
        plugin_digits[0], plugin_digits[1], plugin_digits[2], es_digits[0], es_digits[1])


