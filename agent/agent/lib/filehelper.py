#pylint: disable=W0511,C0103,W0621,E1101,W0105
'''
Copyright 2014 eBay Software Foundation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
""" File Utility Functions """

import logging
LOG = logging.getLogger(__name__)

def read_in_chunks(file_object, chunk_size=4096):
    """Lazy function (generator) to read a file piece by piece.
    Default chunk size: 1k."""
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data

def tail(f, window=20):
    """
    Returns the last `window` lines of file `f` as a list.
    """
    BUFSIZ = 4096
    f.seek(0, 2)
    bytes1 = f.tell()
    size = window + 1
    block = -1
    data = []
    while size > 0 and bytes1 > 0:
        if bytes1 - BUFSIZ > 0:
            # Seek back one whole BUFSIZ
            f.seek(block * BUFSIZ, 2)
            # read BUFFER
            data.insert(0, f.read(BUFSIZ))
        else:
            # file too small, start from begining
            f.seek(0, 0)
            # only read what was not read
            data.insert(0, f.read(bytes1))
        linesFound = data[0].count('\n')
        size -= linesFound
        bytes1 -= BUFSIZ
        block -= 1
    return ''.join(data).splitlines()[-window:]

def viewFile(fileName):
    """ download file """
    with open(fileName, 'r') as logFile:
        logData = logFile.read()
    return plaintext2html(logData)

def downloadFile(fileName):
    """ download file """
    with open(fileName, 'rb') as logFile:
        logData = logFile.read()
    return logData

def tailFile(fileName, lines):
    """ tail file """
    logFile = open(fileName, 'r')
    logData = tail(logFile, int(lines))
    logFile.close()
    return plaintext2html('\n'.join(logData))

import re
import cgi

RESTRING = re.compile(r'(?P<htmlchars>[<&>])|(?P<space>^[ \t]+)|(?P<lineend>\r\n|\r|\n)|(?P<protocal>(^|\s)((http|ftp)://.*?))(\s|$)', re.S|re.M|re.I)
def plaintext2html(text, tabstop=4):
    """
    convert plaintext to html
    from http://djangosnippets.org/snippets/19/
    """
    def doSub(text):
        """ do replacement """
        char = text.groupdict()
        if char['htmlchars']:
            return cgi.escape(char['htmlchars'])
        if char['lineend']:
            return '<br>'
        elif char['space']:
            html = text.group().replace('\t', '&nbsp;'*tabstop)
            html = html.replace(' ', '&nbsp;')
            return html
        elif char['space'] == '\t':
            return ' '*tabstop
        else:
            url = text.group('protocal')
            if url.startswith(' '):
                prefix = ' '
                url = url[1:]
            else:
                prefix = ''
            last = text.groups()[-1]
            if last in ['\n', '\r', '\r\n']:
                last = '<br>'
            return '%s<a href="%s">%s</a>%s' % (prefix, url, url, last)
    return re.sub(RESTRING, doSub, text)
