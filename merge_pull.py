#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 Reinhard Nägele
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from subprocess import Popen, STDOUT, PIPE
from textwrap import dedent

desc = dedent('''
        Merges a Bitbucket pull request. Multiple commits are squashed. The
        commits are then rebased on top of upstream changes and pushed directly
        to the feature branch and the target branch. Bitbucket regognizes this
        and marks the pull request as merged. Then switches to the target branch
        and deletes the feature branch.
    ''').strip()
args_parser = ArgumentParser(description=desc, formatter_class=ArgumentDefaultsHelpFormatter)
args_parser.add_argument('--target-branch', '-t', default='master', help='The target_branch of the pull request')
args_parser.add_argument('--remote', '-r', default='origin', help='The name of the remote')
args_parser.add_argument('--message', '-m', help='If commits need to be squashed, a commit message for ' + 
                         'the final commit is required. You will be prompted to re-use the message of the ' +
                         'first commit on the feature branch. You may then decide to enter a different message')
args_parser.add_argument('--assume-yes', '-y', action="store_true", help='Automatic yes to prompts')

args = args_parser.parse_args()

target_branch = args.target_branch
remote = args.remote
message = args.message
assume_yes = args.assume_yes

def git(*arguments):
    cmdline = ['git']
    cmdline.extend(arguments)

    print ''
    print ' '.join(arg for arg in cmdline)

    proc = Popen(cmdline, stdout=PIPE, stderr=STDOUT)
    print ''
    output = []
    while True:
        line = proc.stdout.readline()
        if not line:
            break

        line = line.rstrip()
        print 'git> %s' % line#
        output.append(line)

    print ''
    proc.wait()

    # We are only interested in the first line
    return output and output[0] or None

target_branch_remote = '%s/%s' % (remote, target_branch)
feature_branch = git('rev-parse', '--abbrev-ref', '--verify', 'HEAD')
target_branch_ref = git('rev-parse', target_branch)
feature_branch_ref = git('rev-parse', feature_branch)

print 'Merging pull request for branch %s with target branch %s...' % (feature_branch, target_branch)

if target_branch_ref == feature_branch_ref:
    raise ValueError, 'Target branch and HEAD point to the same ref. Make sure you are on your feature branch.'

print 'Fetching upstream changes...'
git('fetch', remote)

commit_count = int(git('rev-list', '--count', '%s..HEAD' % target_branch_remote))
if commit_count == 1:
    print 'Rebasing commit...'
    git('rebase', target_branch_remote)
else:
    merge_base = git('merge-base', 'HEAD', target_branch_remote)
    first_commit_on_branch = git('rev-list', '%s..HEAD' % merge_base, '--reverse')
    msg_of_first_commit = git('show', '--no-patch', '--format=%B', first_commit_on_branch)

    print 'Merging in upstream changes...'
    git('merge', target_branch_remote)

    print 'Squashing commits...'
    git('reset', '--soft', target_branch_remote)

    if not message:
        print 'Message of the first commit on this branch:'
        print '----'
        print ''
        print msg_of_first_commit
        print ''
        print '----'

        if assume_yes or 'y' == raw_input('Re-use the this message (y/N): ').lower():
            print 'Re-using commit messsage...'
            message = msg_of_first_commit
        else:
            print 'Enter/paste your message. Hit Ctrl-D to save it.'
            contents = []
            while True:
                try:
                    line = raw_input('')
                except EOFError:
                    break
                contents.append(line)
            message = '\n'.join(line for line in contents)

    git('commit', '-m', message)

print 'Force-pushing commit to feature branch...'
git('push', '--force', remote, 'HEAD:%s' % feature_branch)

print 'Pushing commit to target branch...'
git('push', remote, 'HEAD:%s' % target_branch)

print 'Switching to target branch...'
git('checkout', target_branch)

print 'Pulling in upstream changes...'
git('pull', remote, target_branch, '--rebase')

if assume_yes or 'y' == raw_input('Delete feature branches (y/N): ').lower():
    print 'Deleting feature branch...'
    git('branch', '-d', feature_branch)

    print 'Deleting feature branch on server...'
    git('push', remote, feature_branch, '--delete')

print 'Good bye.'
