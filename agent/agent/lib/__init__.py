#pylint: disable=W0622,W0105

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
""" agent lib """
import os, re, sys

import logging
LOG = logging.getLogger(__name__)

# library paths
LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'lib')
for entry in os.listdir(LIB):
    file = os.path.join(LIB, entry)
    if os.path.exists(file) and re.search(r".*\.(zip|egg|tar\.gz|tgz)$", file):
        LOG.info("...appending library %s to sys.path" % file)
        sys.path.append(file)
