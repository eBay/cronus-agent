#pylint: disable=E1121,W0105
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
'''
Created on Feb 21, 2014

@author: biyu
'''
from agent.lib.security import UnauthorizedException, invalidAuthHandler
from pylons import request, config
import logging
import re
import base64
from decorator import decorator
from agent.lib import configutil, manifestutil
import os
import traceback


LOG = logging.getLogger(__name__)

def authorize():
    '''
    docorator for authorize
    @parameter inSecurity: bool indicating whether incomming security need to check
    '''
    def validate(func, self, *args, **kwargs):
        ''' function that calls authrozing function'''
        
        isAuthEnabled = True
        isPkiEnabled = False
        authPassed = False
        
        try:
            appGlobal = config['pylons.app_globals']

            isAuthEnabled = configutil.getConfigAsBool('basicauth.local')
            isPkiEnabled = (appGlobal.encryptedtokens and configutil.getConfigAsBool('pkiauth_enabled'))
        
        except BaseException as excep:
            LOG.error('Error loading auth config %s - %s' % (str(excep), traceback.format_exc(2)))
            
        if isAuthEnabled:
            
            if 'Authorization' not in request.headers and 'authorization' not in request.headers:
                return invalidAuthHandler('Authorization header missing', {})

            message = None
            result = {}
            
            # base authentication
            if not isPkiEnabled:
                token = ('%s:%s' % (configutil.getConfig('username.local'), configutil.getConfig('password.local')))
                try:
                    isAuthenticated(token)
                    authPassed = True
                except UnauthorizedException:
                    message = 'Please provide valid username and password'
                    result['scheme'] = 'base'
                
            if not authPassed:
                # pki authentication
                token = appGlobal.authztoken 
                try: 
                    isAuthenticated(token)
                    authPassed = True
                except UnauthorizedException:
                    if isPkiEnabled:
                        result['scheme'] = 'pki'
                        user = request.headers['AuthorizationUser'] if 'AuthorizationUser' in request.headers else 'agent'  
                        pubKey = '%s.cert' % user 
                        if pubKey in appGlobal.encryptedtokens:
                            message = appGlobal.encryptedtokens[pubKey]
                            result['key'] = appGlobal.encryptedtokens[pubKey]
                        else:
                            message = 'Unknown AuthroizationUser %s' % user

                    return invalidAuthHandler(message, result)

        return func(self, *args, **kwargs)

    return decorator(validate)

def isAuthenticated(token):
    ''' check whether user name and password are right '''
    message = 'Please provide valid username and password'
    inHeader = None
    try:
        if 'authorization' in request.headers:
            inHeader = request.headers['authorization']
        elif 'Authorization' in request.headers:
            inHeader = request.headers['Authorization']

        if inHeader is not None:
            base64string = base64.encodestring(token)[:-1]
            match = re.match(r'\s*Basic\s*(?P<auth>\S*)$', inHeader)

            if match is not None and match.group('auth') == base64string:
                return True

        raise UnauthorizedException(message + " Header:" + str(request.headers))
    except:
        raise UnauthorizedException(message + " Header:" + str(request.headers))

def buildTokenCache(authztoken):
    """ build in memory cache for security tokens """
    # find all pub keys in agent and encrypt the security token with them
    appGlobal = config['pylons.app_globals']
    pubKeyDir = os.path.join(manifestutil.manifestPath('agent'), 'agent', 'cronus', 'keys')
    LOG.info('key directory %s' % pubKeyDir)
    if os.path.exists(pubKeyDir):
        try:
            import pki
            from M2Crypto import X509
            pubKeyFiles = [f for f in os.listdir(pubKeyDir) if re.match(r'.*\.cert', f)]
            LOG.info('key files %s' % pubKeyFiles)
            for pubKeyFile in pubKeyFiles:
                # reload the certs from disk
                certf = open(os.path.join(pubKeyDir, pubKeyFile), 'r')
                ca_cert_content = certf.read()
                certf.close()

                cert = X509.load_cert_string(ca_cert_content)
                #            pub = RSA.load_pub_key(os.path.join(pubKeyDir, pubKeyFile))
                encryptedToken = pki.encrypt(cert.get_pubkey(), authztoken)
                appGlobal.encryptedtokens[pubKeyFile] = encryptedToken    
                LOG.info('token %s=%s' % (pubKeyFile, encryptedToken))
        except BaseException as excep:
            LOG.error('Error loading pki keys %s - %s' % (str(excep), traceback.format_exc(2)))
    
    