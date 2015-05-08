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

"""
Parse a file and potentially rewrite a line

from release.fileupdater import updater

def callback(line):
    return line.replace("<version>1.2.3-SNAPSHOT</version>", "<version>1.2.3</version>")

updater.process_file("/path/to/myfile.txt", callback)
"""


import tempfile
import os
import shutil

def dummy_line_callback(line):
    return line


def process_file(file_path, line_callback=dummy_line_callback):
    fh, abs_path = tempfile.mkstemp()
    modified = False
    with open(abs_path, 'w', encoding='utf-8') as new_file:
        with open(file_path, encoding='utf-8') as old_file:
            for line in old_file:
                new_line = line_callback(line)
                modified = modified or (new_line != line)
                new_file.write(new_line)
    os.close(fh)
    if modified:
        #Remove original file
        os.remove(file_path)
        #Move new file
        shutil.move(abs_path, file_path)
        return True
    else:
        # nothing to do - just remove the tmp file
        os.remove(abs_path)
        return False

