import re
import json
from nested_dict import *
from optparse import OptionParser # Deprecated since version 2.7

class createConfig():
    ''' class to create config file based on template'''
    def __init__(self):
        ''' constructor '''
        pass

    @staticmethod
    def create(tmplFileName, iniFileName, dict):
        ''' create config file'''
        with open(tmplFileName, 'r') as tmplFile:
            with open(iniFileName, 'w') as iniFile:
                section = ""
                for line in tmplFile:
                    m = re.match(r'^\[\s*(?P<section>\S*)\s*\](\s*$|\s*#.*)', line)
                    if m:
                        section = m.group('section')
                    elif section in dict:
                        for key in dict[section]:
                            m = re.match(r'\s*(?P<key>\w[\S|\s]*\S)\s*=\s*(?P<value>[\S| ]*\S)(\s*$|\s*#.*)', line)
                            if m and str(key) == m.group('key'):
                                if None == dict[section][key]:
                                    line = '\n'
                                else:
                                    line = '%s = %s\n' %(str(key), str(dict[section][key]))
                                break

                    iniFile.write(line)

def make_config():
    ''' make four config file base on tmpl.ini'''
    # parse command line
    usage = 'usage: %prog [options] (agent|orchestator|dashboard)'
    parser = OptionParser(usage=usage)
    parser.add_option('-f', '--file', dest='file', default='conf/tmpl.ini',
                      help='template ini file')
    (options, args) = parser.parse_args()

    if len(args) != 1 and args[0] not in compPorts:
        parser.print_usage()
        exit(1)

    component = args[0]

    with open('conf/iniChanges.json', 'r') as f:
        configDict = json.loads(f.read())
        
        for env, settings in configDict[component].items():
            iniFilename = 'conf/%s.ini' % env
            createConfig.create(options.file, iniFilename, settings)

if __name__ == '__main__':
    make_config()
