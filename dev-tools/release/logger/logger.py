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

"""
This module defines all the logging logic

Usage example:

from release.logger import logger

logger.purge_log()
logger.log("hello")

logger.print_log()

If you need to access LOG file, just use logger.LOG

Note that log file is by default /tmp/elasticsearch_release.log but can be changed
by setting ES_RELEASE_LOG system variable to whatever absolute path like /tmp/elasticsearch_release.log
"""

import os

env = os.environ

LOG = env.get('ES_RELEASE_LOG', '/tmp/elasticsearch_release.log')


##########################################################
#
# Utility methods (log and run)
#
##########################################################
# Log a message
def log(msg):
    log_plain('\n%s' % msg)


# Purge the log file
def purge_log():
    try:
        os.remove(LOG)
    except FileNotFoundError:
        pass


# Log a message to the LOG file
def log_plain(msg):
    f = open(LOG, mode='ab')
    f.write(msg.encode('utf-8'))
    f.close()


# Print the log file
def print_log():
    print('Logs:')
    with open(LOG, 'r') as log_file:
        print(log_file.read())
