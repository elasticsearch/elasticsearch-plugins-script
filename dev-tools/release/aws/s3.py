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
from ..utils import run
from .. import common


# Upload files to S3
def publish_artifacts(artifacts, base='elasticsearch/elasticsearch', dry_run=True):
    for artifact in artifacts:
        if dry_run:
            print('Skip Uploading %s to Amazon S3 in %s' % (artifact, base))
        else:
            print('Uploading %s to Amazon S3' % artifact)
            # requires boto to be installed but it is not available on python3k yet so we use a dedicated tool
            run.run('python %s/upload-s3.py --file %s --path %s' % (common.ROOT_DIR, os.path.abspath(artifact), base))


