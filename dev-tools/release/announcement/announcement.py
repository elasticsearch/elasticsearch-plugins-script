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
This module defines all the emailing logic to make announcement based
on github issues for 4 categories:
* Fix
* Update
* New
* Doc

It reads user email templates if defined from /dev-tools/templates dir:
* email_template.html
* email_template.txt

And if not found, fallback to the default module templates

Usage example:

from release.announcement import email

msg = email.prepare_email("elasticsearch-plugin-my",  // Artifact ID
                          "v2.0.0",                   // Version you are releasing
                          "My cool plugin",           // Artifact name
                          "Cool plugin is doing XYZ", // A full description
                          "http://my-url/",           // URL to your project
                          issues_bug,                 // Issues coming from GH for Fix
                          issues_update,              // Issues coming from GH for Update
                          issues_new,                 // Issues coming from GH for New
                          issues_doc)                 // Issues coming from GH for Doc
email.send_email(msg)

By default, send_email is running in dry mode so it only prints out the generated email.

If you want to send the email, you need to set dry_run=False:

email.send_email(msg, dry_run=False)

Emails are sent to discuss+announcements@elastic.co by default.
You can set your own destination by setting MAIL_TO env variable.
You need to define MAIL_SENDER env variable and set it to the sender email address which
is allowed to send emails to the announcement mailing list.

By default, SMTP server used to send emails is localhost.
You can define another one by setting SMTP_SERVER env variable.
"""

import os

env = os.environ

import smtplib

from os.path import dirname, abspath
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..logger import logger
from .. import common

DEV_TOOLS_DIR = common.ROOT_DIR + '/plugin_tools'
DEFAULT_TEMPLATE_DIR = abspath(os.path.join(abspath(dirname(__file__)), 'templates'))
USER_TEMPLATE_DIR = common.ROOT_DIR + '/dev-tools/templates'

DEFAULT_EMAIL_RECIPIENT = "discuss%2Bannouncements@elastic.co"

# Generates a Plain/HTML Multipart email from an issue list
def prepare_email(artifact_id,
                  release_version,
                  artifact_name,
                  artifact_description,
                  project_url,
                  issues_bug,
                  issues_update,
                  issues_new,
                  issues_doc):

    total_issues = 0
    plain_issues_bug = ""
    html_issues_bug = ""
    plain_issues_update = ""
    html_issues_update = ""
    plain_issues_new = ""
    html_issues_new = ""
    plain_issues_doc = ""
    html_issues_doc = ""

    if issues_bug is not None and len(issues_bug) > 0:
        # Format content to plain text
        plain_issues_bug = format_issues_plain(issues_bug, 'Fix')
        # Format content to html
        html_issues_bug = format_issues_html(issues_bug, 'Fix')
        total_issues += len(issues_bug)

    if issues_update is not None and len(issues_update) > 0:
        # Format content to plain text
        plain_issues_update = format_issues_plain(issues_update, 'Update')
        # Format content to html
        html_issues_update = format_issues_html(issues_update, 'Update')
        total_issues += len(issues_update)

    if issues_new is not None and len(issues_new) > 0:
        # Format content to plain text
        plain_issues_new = format_issues_plain(issues_new, 'New')
        # Format content to html
        html_issues_new = format_issues_html(issues_new, 'New')
        total_issues += len(issues_new)

    if issues_doc is not None and len(issues_doc) > 0:
        # Format content to plain text
        plain_issues_doc = format_issues_plain(issues_doc, 'Doc')
        # Format content to html
        html_issues_doc = format_issues_html(issues_doc, 'Doc')
        total_issues += len(issues_doc)

    if total_issues > 0:
        plain_empty_message = ""
        html_empty_message = ""

    else:
        plain_empty_message = "No issue listed for this release"
        html_empty_message = "<p>No issue listed for this release</p>"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = '[ANN] %s %s released' % (artifact_name, release_version)
    text = read_email_template('txt') % {'release_version': release_version,
                                         'artifact_id': artifact_id,
                                         'artifact_name': artifact_name,
                                         'artifact_description': artifact_description,
                                         'project_url': project_url,
                                         'empty_message': plain_empty_message,
                                         'issues_bug': plain_issues_bug,
                                         'issues_update': plain_issues_update,
                                         'issues_new': plain_issues_new,
                                         'issues_doc': plain_issues_doc}

    html = read_email_template('html') % {'release_version': release_version,
                                          'artifact_id': artifact_id,
                                          'artifact_name': artifact_name,
                                          'artifact_description': artifact_description,
                                          'project_url': project_url,
                                          'empty_message': html_empty_message,
                                          'issues_bug': html_issues_bug,
                                          'issues_update': html_issues_update,
                                          'issues_new': html_issues_new,
                                          'issues_doc': html_issues_doc}

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)

    return msg


def send_email(msg,
               dry_run=True,
               mail=True,
               sender=env.get('MAIL_SENDER'),
               to=env.get('MAIL_TO', DEFAULT_EMAIL_RECIPIENT),
               smtp_server=env.get('SMTP_SERVER', 'localhost'),
               file=common.ROOT_DIR + '/target/email.txt'):
    msg['From'] = 'Elasticsearch Team <%s>' % sender
    msg['To'] = 'Elasticsearch Announcement List <%s>' % to
    # save mail on disk
    with open(file, 'w') as email_file:
        email_file.write(msg.as_string())
    if mail and not dry_run:
        s = smtplib.SMTP(smtp_server, 25)
        s.sendmail(sender, to, msg.as_string())
        s.quit()
    else:
        print('generated email: open %s' % file)
        print(msg.as_string())


# Format a GitHub issue as plain text
def format_issues_plain(issues, title='Fix'):
    response = ""

    if issues is not None and len(issues) > 0:
        response += '%s:\n' % title
        for issue in issues:
            response += ' * [%s] - %s (%s)\n' % (issue.number, issue.title, issue.html_url)

    return response


# Format a GitHub issue as html text
def format_issues_html(issues, title='Fix'):
    response = ""

    if issues is not None and len(issues) > 0:
        response += '<h2>%s</h2>\n<ul>\n' % title
        for issue in issues:
            response += '<li>[<a href="%s">%s</a>] - %s\n' % (issue.html_url, issue.number, issue.title)
        response += '</ul>\n'

    return response


# Read an email template
def read_email_template(mail_format='html'):
    # We try to read from USER_TEMPLATE_DIR and fallback to DEFAULT_TEMPLATE_DIR
    template_dir=USER_TEMPLATE_DIR
    file_name = '%s/email_template.%s' % (template_dir, mail_format)
    logger.log('open email template %s' % file_name)
    try:
        with open(file_name, encoding='utf-8') as template_file:
            data = template_file.read()
    except FileNotFoundError:
        template_dir=DEFAULT_TEMPLATE_DIR
        file_name = '%s/email_template.%s' % (template_dir, mail_format)
        logger.log('open email template %s' % file_name)
        with open(file_name, encoding='utf-8') as template_file:
            data = template_file.read()

    return data

