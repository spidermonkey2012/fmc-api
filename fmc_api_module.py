# Import Required Modules
import os
import re
import sys
import csv
import json
import socket
import random
import netaddr
import getpass
import requests
import traceback




#
#
# FMC Object
class FMC(object):
    def __init__(self):
        self.hostname = ''
        self.username = ''
        self.password = ''
        self.serial_number = ""
        self.uuid = ""
        self.version = ""
        self.train = float()
        self.patch = ""
        self.date = datetime.today().strftime('%Y-%m-%d %H:%M')
        self.id = hashlib.md5((f'{str(time.time())}').encode('utf-8')).hexdigest()
        self.conn_handler = netmiko.ConnectHandler
        self.session = requests.session()
        self.session.auth = (self.username, self.password)
        self.session.headers = {'Content-Type': 'application/json','Accept': 'application/json'}
        self.domains = ''
        self.api_uuid = ''
    #
    #
    # Define Generate Access Token Function
    def access_token(self):
        auth_url = f'{server}/api/fmc_platform/v1/auth/generatetoken'
        try:
            # REST call with SSL verification turned off:
            r = self.post(auth_url, headers=self.headers, verify=False)
            print(r.status_code)
            if r.status_code == 401:
                return False
            else:
                self.session.headers['X-auth-access-token'] = r.headers['X-auth-access-token']
                self.domains = json.loads(r.headers['DOMAINS'])
                return True
        except:
            print (f'Error in generating auth token --> {traceback.format_exc()}')
            print(r.headers)
            return False


    # Get FMC IP and Credentials
    def get_details(self):
        if self.hostname != '':
            print ('''
***********************************************************************************************
*                           Provide FMC hostname and credentials                              *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. Hostname for FMC server (hostname.domain.com)                                           *
*                                                                                             *
*  2. API Username                                                                            *
*                                                                                             *
*  3. API Password                                                                            *
*                                                                                             *
***********************************************************************************************
''')
            print(f'\nCurrent FMC: {self.hostname}\n')
            while True:
                choice = input('Would you like to enter a different FMC? [y/N]: ').lower()
                if choice in (['yes','ye','y']):

                    while True:
                        # Request FMC server Hostname
                        self.hostname = input('Please enter FMC hostname: ').lower().strip()

                        # Validate FQDN
                        if self.hostname[-1] == '/':
                            self.hostname = self.hostname[:-1]
                        if '//' in self.hostname:
                            self.hostname = self.hostname.split('//')[-1]

                        # Perform Test Connection To FQDN
                        s = socket.socket()
                        print(f'Attempting to connect to {self.hostname} on port 443')
                        try:
                            s.connect((self.hostname, 443))
                            print(f'Connecton successful to {self.hostname} on port 443')
                            break
                        except:
                            print(f'Connection to {self.hostname} on port 443 failed: {traceback.format_exc()}\n\n')

                    # Adding HTTPS to Server for URL
                    self.hostname = f'https://{self.hostname}'
                    self.session.headers = {'Content-Type': 'application/json','Accept': 'application/json'}

                    # Request Username and Password without showing password in clear text
                    self.username = input('Please enter API username: ').strip()
                    self.password = define_password()
                elif choice in (['no','n','']):
                    choice = input('Would you like to enter different username/password? [y/N]: ').lower()
                    if choice in (['yes','ye','y']):
                        self.username = input('Please enter API username: ').strip()
                        self.password = define_password()
                    break
                else:
                    print('Invalid Selection...\n')
        else:
            print ('''
***********************************************************************************************
*                           Provide FMC hostname and credentials                              *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. Hostname for FMC server (hostname.domain.com)                                           *
*                                                                                             *
*  2. API Username                                                                            *
*                                                                                             *
*  3. API Password                                                                            *
*                                                                                             *
***********************************************************************************************
''')

            while True:
                # Request FMC server FQDN
                self.hostname = input('Please enter FMC hostname: ').lower().strip()
                if self.hostname == '':
                    continue
                # Validate FQDN
                if self.hostname[-1] == '/':
                    self.hostname = self.hostname[:-1]
                if '//' in self.hostname:
                    self.hostname = self.hostname.split('//')[-1]

                # Perform Test Connection To FQDN
                s = socket.socket()
                print(f'Attempting to connect to {self.hostname} on port 443')
                try:
                    s.connect((self.hostname, 443))
                    print(f'Connecton successful to {self.hostname} on port 443')
                    break
                except:
                    print(f'Connection to {self.hostname} on port 443 failed: {traceback.format_exc()}\n\n')

            # Adding HTTPS to Server for URL
            self.hostname = f'https://{self.hostname}'
            self.session.headers = {'Content-Type': 'application/json','Accept': 'application/json'}

            # Request Username and Password without showing password in clear text
            self.username = input('Please enter API username: ').strip()
            self.password = define_password()


        if len(self.domains) > 1:
            self.api_uuid = select('Domain',self.domains)['uuid']
        else:
            self.api_uuid = self.domains[0]['uuid']

        return


    #
    # Collects and returns items from all pages
    def get_items(self,url):
        try:
            print(f'COLLECTING PAGE... {url}')
            # REST call with SSL verification turned off
            r = self.session.get(url, allow_redirects=False, verify=False)
            status_code = r.status_code
            #print(json.dumps(r.json(),indent=4))
            try:
                temp_list = r.json()['items']
            except:
                return []
            json_resp = r.json()
            #print(f'Json: {json_resp}')
            if status_code == 200:
                while 'next' in json_resp['paging']:
                    url_get = json_resp['paging']['next'][0]
                    print(f'*\n*\nCOLLECTING NEXT PAGE... {url_get}')
                    try:
                        # REST call with SSL verification turned off
                        r = self.session.get(url_get, allow_redirects=False, verify=False)
                        status_code = r.status_code
                        json_resp = r.json()
                        if status_code == 200:
                            # Loop for First Page of Items
                            for item in json_resp['items']:
                                # Append Items to New Dictionary
                                temp_list.append(item)
                    except requests.exceptions.HTTPError as err:
                        print (f'Error in connection --> {traceback.format_exc()}')
        except requests.exceptions.HTTPError as err:
            print (f'Error in connection --> {traceback.format_exc()}')
        return temp_list



    def get(self,url):
        try:
            #print(f'\nPerforming GET to: {url}...')
            r = self.session.get(url, allow_redirects=False, verify=False)
            if r.status_code == 200:
                return r.text
            elif r.status_code == 401:
                print("Token expired, renewing...")
                self.access_token()
                r = self.session.get(url, allow_redirects=False, verify=False)
                if r.status_code == 200:
                    return r.text
                else :
                    print (f'Error occurred in GET --> {r.text}')
                    r.raise_for_status()
            else :
                print (f'Error occurred in GET --> {r.text}')
                r.raise_for_status()
        except requests.exceptions.HTTPError:
            print (f'Error in connection --> {traceback.format_exc()}')
            return None

    def post(self,url,data):
        try:
            #print(f'\nPerforming POST to: {url}...')
            r = self.session.post(url, data, allow_redirects=False, verify=False)
            if r.status_code == 200 or r.status_code == 201:
                return r.text
            elif r.status_code == 401:
                print("Token expired, renewing...")
                self.access_token()
                r = self.session.post(url, allow_redirects=False, verify=False)
                if r.status_code == 200 or r.status_code == 201:
                    return r.text
                else :
                    print (f'Error occurred in GET --> {r.text}')
                    r.raise_for_status()
            else :
                print (f'Error occurred in POST --> {r.text}')
                r.raise_for_status()
                print(r.status_code)
        except requests.exceptions.HTTPError:
            print (f'Error in connection --> {traceback.format_exc()}')
            return None

    def put(self,url,data):
        try:
            #print(f'\nPerforming PUT to: {url}...')
            r = self.session.put(url, data, allow_redirects=False, verify=False)
            if r.status_code == 200:
                return r.text
            elif r.status_code == 401:
                print("Token expired, renewing...")
                self.access_token()
                r = self.session.put(url, allow_redirects=False, verify=False)
                if r.status_code == 200:
                    return r.text
                else :
                    print (f'Error occurred in GET --> {r.text}')
                    r.raise_for_status()
            else :
                print (f'Error occurred in PUT --> {r.text}')
                r.raise_for_status()
                print(r.status_code)
        except requests.exceptions.HTTPError:
            print (f'Error in connection --> {traceback.format_exc()}')
            return None

    def cli_login(self):
        try:
            print(f'Performing CLI Login...')
            self.conn = self.conn_handler(ip=self.hostname,
                                          device_type='linux',
                                          username=self.username,
                                          password=self.password,
                                          global_delay_factor=8
                                         )
        except:
            print (f'Error in connection --> {traceback.format_exc()}')
            return False



#
#
#
# Define Password Function
def define_password():
    password = None
    while not password:
        password = getpass.getpass('Please Enter Password: ')
        passwordverify = getpass.getpass('Re-enter Password to Verify: ')
        if not password == passwordverify:
            print('Passwords Did Not Match Please Try Again')
            password = None
    return password

#
#
#
# Define Generate Access Token Function
def access_token(server,headers,username,password):
    auth_url = f'{server}/api/fmc_platform/v1/auth/generatetoken'
    try:
        # REST call with SSL verification turned off:
        r = requests.post(auth_url, headers=headers, auth=requests.auth.HTTPBasicAuth(username,password), verify=False)
        print(r.status_code)
        if r.status_code == 401:
            return None
        else:
            auth_token = r.headers['X-auth-access-token']
            domains = json.loads(r.headers['DOMAINS'])
            return auth_token,domains
    except Exception as err:
        print (f'Error in generating auth token --> {traceback.format_exc()}')
        print(r.headers)
        return None


#
# Get FMC IP and Credentials
def get_fmc_details(server,headers,username,password):
    if server != '':
        print ('''
***********************************************************************************************
*                           Provide FMC hostname and credentials                              *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. Hostname for FMC server (hostname.domain.com)                                           *
*                                                                                             *
*  2. API Username                                                                            *
*                                                                                             *
*  3. API Password                                                                            *
*                                                                                             *
***********************************************************************************************
''')
        print(f'\nCurrent FMC: {server}\n')
        while True:
            choice = input('Would you like to enter a different FMC? [y/N]: ').lower()
            if choice in (['yes','ye','y']):

                while True:
                    # Request FMC server Hostname
                    server = input('Please enter FMC hostname: ').lower().strip()

                    # Validate FQDN
                    if server[-1] == '/':
                        server = server[:-1]
                    if '//' in server:
                        server = server.split('//')[-1]

                    # Perform Test Connection To FQDN
                    s = socket.socket()
                    print(f'Attempting to connect to {server} on port 443')
                    try:
                        s.connect((server, 443))
                        print(f'Connecton successful to {server} on port 443')
                        break
                    except:
                        print(f'Connection to {server} on port 443 failed: {traceback.format_exc()}\n\n')

                # Adding HTTPS to Server for URL
                server = f'https://{server}'
                headers = {'Content-Type': 'application/json','Accept': 'application/json'}

                # Request Username and Password without showing password in clear text
                username = input('Please enter API username: ').strip()
                password = define_password()
            elif choice in (['no','n','']):
                choice = input('Would you like to enter different username/password? [y/N]: ').lower()
                if choice in (['yes','ye','y']):
                    username = input('Please enter API username: ').strip()
                    password = define_password()
                break
            else:
                print('Invalid Selection...\n')
    else:
        print ('''
***********************************************************************************************
*                           Provide FMC hostname and credentials                              *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. Hostname for FMC server (hostname.domain.com)                                           *
*                                                                                             *
*  2. API Username                                                                            *
*                                                                                             *
*  3. API Password                                                                            *
*                                                                                             *
***********************************************************************************************
''')

        while True:
            # Request FMC server FQDN
            server = input('Please enter FMC hostname: ').lower().strip()
            if server == '':
                continue
            # Validate FQDN
            if server[-1] == '/':
                server = server[:-1]
            if '//' in server:
                server = server.split('//')[-1]

            # Perform Test Connection To FQDN
            s = socket.socket()
            print(f'Attempting to connect to {server} on port 443')
            try:
                s.connect((server, 443))
                print(f'Connecton successful to {server} on port 443')
                break
            except:
                print(f'Connection to {server} on port 443 failed: {traceback.format_exc()}\n\n')

        # Adding HTTPS to Server for URL
        server = f'https://{server}'
        headers = {'Content-Type': 'application/json','Accept': 'application/json'}

        # Request Username and Password without showing password in clear text
        username = input('Please enter API username: ').strip()
        password = define_password()

    return server,headers,username,password




#
#
# Get Device Details from Inventory List
# And Delete item from Inventory List
def get_device_details(id,device_list):
    temp_dict = {}
    for item in device_list:
        if item['id']==id:
            temp_dict['accessPolicy'] = item['accessPolicy']
            temp_dict['name'] = item['name']
            temp_dict['model'] = item['model']
            temp_dict['healthStatus'] = item['healthStatus']
            temp_dict['sw_version'] = item['sw_version']
            temp_dict['license_caps'] = item['license_caps']
            if 'ftdMode' in item: temp_dict['ftdMode'] = item['ftdMode']

            if 'hostname' in item: temp_dict['hostName'] = item['hostname']
            if 'hostName' in item: temp_dict['hostName'] = item['hostName']
            if 'snortEngine' in item: temp_dict['snortEngine'] = item['snortEngine']

            if 'deviceSerialNumber' in item['metadata']: temp_dict['deviceSerialNumber'] = item['metadata']['deviceSerialNumber']
            if 'containerDetails' in item['metadata']: temp_dict['containerDetails'] = item['metadata']['containerDetails']
            if 'inventoryData' in item['metadata']: temp_dict['inventoryData'] = item['metadata']['inventoryData']
            if 'domain' in item['metadata']: temp_dict['domain'] = item['metadata']['domain']
            if 'isMultiInstance' in item['metadata']: temp_dict['isMultiInstance'] = item['metadata']['isMultiInstance']

            if 'sruVersion' in item['metadata']: temp_dict['sruVersion'] = item['metadata']['sruVersion']
            if 'vdbVersion' in item['metadata']: temp_dict['vdbVersion'] = item['metadata']['vdbVersion']
            if 'snortVersion' in item['metadata']: temp_dict['snortVersion'] = item['metadata']['snortVersion']
            if 'chassisData' in item['metadata']: temp_dict['chassisData'] = item['metadata']['chassisData']
            # Delete item from Device List
            device_list.pop(device_list.index(item))
    return temp_dict


#
#
#
# Get Net Object UUID
def get_net_object_uuid(server,API_UUID,headers,ObjectName,outfile):
    # Create Get DATA JSON Dictionary to collect data from GET calls
    GetDATA = {}
    GetDATA['items'] = []
    try:
        # Collect Network Objects
        url_get = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networks?offset=0&limit=1000'
        # REST call with SSL verification turned off
        r = requests.get(url_get, headers=headers, verify=False)
        status_code = r.status_code
        resp = r.text
        print(f'Status code is: {status_code}')
        json_resp = r.json()
        if status_code == 200:
            # Loop for First Page of Items
            for item in json_resp['items']:
                # Append Items to New Dictionary
                GetDATA['items'].append({'name': item['name'],'id': item['id']})
            while json_resp['paging'].__contains__('next'):
                url_get = json_resp['paging']['next'][0]
                try:
                    # REST call with SSL verification turned off
                    r = requests.get(url_get, headers=headers, verify=False)
                    status_code = r.status_code
                    resp = r.text
                    print(f'Status code is: {status_code}')
                    json_resp = r.json()
                    if status_code == 200:
                        # Loop for First Page of Items
                        for item in json_resp['items']:
                            # Append Items to New Dictionary
                            GetDATA['items'].append({'name': item['name'],'id': item['id']})
                except requests.exceptions.HTTPError as err:
                    print (f'Error in connection --> {err}')
                    outfile.write(f'Error occurred in POST --> {resp}\n{ObjectName}\n')
        # Collect Host Objects
        url_get = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/hosts?offset=0&limit=1000'
        # REST call with SSL verification turned off
        r = requests.get(url_get, headers=headers, verify=False)
        status_code = r.status_code
        resp = r.text
        print(f'Status code is: {status_code}')
        json_resp = r.json()
        if status_code == 200:
            # Loop for First Page of Items
            for item in json_resp['items']:
                # Append Items to New Dictionary
                GetDATA['items'].append({'name': item['name'],'id': item['id']})
            while json_resp['paging'].__contains__('next'):
                url_get = json_resp['paging']['next'][0]
                try:
                    # REST call with SSL verification turned off
                    r = requests.get(url_get, headers=headers, verify=False)
                    status_code = r.status_code
                    resp = r.text
                    print(f'Status code is: {status_code}')
                    json_resp = r.json()
                    if status_code == 200:
                        # Loop for First Page of Items
                        for item in json_resp['items']:
                            # Append Items to New Dictionary
                            GetDATA['items'].append({'name': item['name'],'id': item['id']})
                except requests.exceptions.HTTPError as err:
                    print (f'Error in connection --> {err}')
                    outfile.write(f'Error occurred in POST --> {resp}\n{ObjectName}\n')
                try:
                    if r: r.close()
                except:
                    None
    except requests.exceptions.HTTPError as err:
        print (f'Error in connection --> {err}')
        outfile.write(f'Error occurred in POST --> {resp}\n{ObjectName}\n')
    try:
        if r: r.close()
    except:
        None

    for item in GetDATA['items']:
        if item['name'] == ObjectName:
            # Pull Object UUID from json_resp data
            ObjectID = item['id']
    return ObjectID


#
#
#
# Prompt user to select from options, returns selection
#   L == list of dict items with a 'name' key
def select(opt,L):
    options = {}
    counter = 0
    if L == []:
        L.append({'None':'None'})
    for item in L:
        counter += 1
        if 'None' in item:
            options.update({str(counter):{'key':'None', 'value':'None'}})
        else:
            options.update({str(counter):{'key':item['name'],'value':item}})
    while True:
        print(f'''
#---------------------------------------------------
{opt} options...
#---------------------------------------------------''')
        for k,v in options.items():
            print(f'  {k}: {v["key"]}')
        option = input(f'Select a {opt}: ').lower()
        if option not in options:
            print('Invalid selection....\n')
            continue
        elif options[option]['value'] == 'None':
            return None
        else:
            return options[option]['value']





#
#
#
# Collects and returns items from all pages
def get_items(url,headers):
    try:
        print(f'COLLECTING PAGE... {url}')
        # REST call with SSL verification turned off
        r = requests.get(url, headers=headers, verify=False)
        status_code = r.status_code
        #print(json.dumps(r.json(),indent=4))
        try:
            temp_list = r.json()['items']
        except:
            return []
        json_resp = r.json()
        #print(f'Json: {json_resp}')
        if status_code == 200:
            while 'next' in json_resp['paging']:
                url_get = json_resp['paging']['next'][0]
                print(f'*\n*\nCOLLECTING NEXT PAGE... {url_get}')
                try:
                    # REST call with SSL verification turned off
                    r = requests.get(url_get, headers=headers, verify=False)
                    status_code = r.status_code
                    json_resp = r.json()
                    if status_code == 200:
                        # Loop for First Page of Items
                        for item in json_resp['items']:
                            # Append Items to New Dictionary
                            temp_list.append(item)
                except requests.exceptions.HTTPError as err:
                    print (f'Error in connection --> {traceback.format_exc()}')
    except requests.exceptions.HTTPError as err:
        print (f'Error in connection --> {traceback.format_exc()}')
    return temp_list






#
# Parse ACP Rule, return list
def parse_rule(FMC_NAME,rule):
    if 'prefilterPolicy' in rule['metadata']:
        ACP_NAME    = rule['metadata']['prefilterPolicy']['name']
        ACP_TYPE    = rule['metadata']['prefilterPolicy']['type']
        ACP_ID      = rule['metadata']['prefilterPolicy']['id']
    else:
        ACP_NAME    = rule['metadata']['accessPolicy']['name']
        ACP_TYPE    = rule['metadata']['accessPolicy']['type']
        ACP_ID      = rule['metadata']['accessPolicy']['id']
    R_NAME      = rule['name']
    R_ID        = rule['id']
    R_ACTION    = rule['action']
    R_SRC_ZN    = ''
    R_DST_ZN    = ''
    R_SRC_IP    = ''
    R_DST_IP    = ''
    R_VLAN      = ''
    R_USERS     = ''
    R_APP       = 'false'
    R_URL       = 'false'
    R_SRC_P     = ''
    R_DST_P     = ''
    R_SRC_SGT   = ''
    R_DST_SGT   = ''
    R_IPS       = ''
    R_FILE      = ''

    # Source Zones
    if 'sourceZones' in rule:
        temp_list = [i['name'] for i in rule['sourceZones']['objects']]
        if len(temp_list) > 1:
            R_SRC_ZN = '; '.join(temp_list)
        else:
            R_SRC_ZN = temp_list[0]
    # Destination Zones
    if 'destinationZones' in rule:
        temp_list = [i['name'] for i in rule['destinationZones']['objects']]
        if len(temp_list) > 1:
            R_DST_ZN = '; '.join(temp_list)
        else:
            R_DST_ZN = temp_list[0]
    # Source Zones for Prefilter Rules
    if 'sourceInterfaces' in rule:
        temp_list = [i['name'] for i in rule['sourceInterfaces']['objects']]
        if len(temp_list) > 1:
            R_SRC_ZN = '; '.join(temp_list)
        else:
            R_SRC_ZN = temp_list[0]
    # Destination Zones for Prefilter Rules
    if 'destinationInterfaces' in rule:
        temp_list = [i['name'] for i in rule['destinationInterfaces']['objects']]
        if len(temp_list) > 1:
            R_DST_ZN = '; '.join(temp_list)
        else:
            R_DST_ZN = temp_list[0]
    # Source Networks
    if 'sourceNetworks' in rule:
        lits = ''
        objs = ''
        if 'literals' in rule['sourceNetworks']:
            temp_list = [i['value'] for i in rule['sourceNetworks']['literals']]
            if len(temp_list) > 1:
                lits = '; '.join(temp_list)
            else:
                lits = temp_list[0]
        if 'objects' in rule['sourceNetworks']:
            temp_list = [i['name'] for i in rule['sourceNetworks']['objects']]
            if len(temp_list) > 1:
                objs = '; '.join(temp_list)
            else:
                objs = temp_list[0]
        if (lits != '') and (objs != ''):
            R_SRC_IP = '; '.join([lits,objs])
        elif lits != '':
            R_SRC_IP = lits
        elif objs != '':
            R_SRC_IP = objs
    # Destination Networks
    if 'destinationNetworks' in rule:
        lits = ''
        objs = ''
        if 'literals' in rule['destinationNetworks']:
            temp_list = [i['value'] for i in rule['destinationNetworks']['literals']]
            if len(temp_list) > 1:
                lits = '; '.join(temp_list)
            else:
                lits = temp_list[0]
        if 'objects' in rule['destinationNetworks']:
            temp_list = [i['name'] for i in rule['destinationNetworks']['objects']]
            if len(temp_list) > 1:
                objs = '; '.join(temp_list)
            else:
                objs = temp_list[0]
        if (lits != '') and (objs != ''):
            R_DST_IP = '; '.join([lits,objs])
        elif lits != '':
            R_DST_IP = lits
        elif objs != '':
            R_DST_IP = objs
    # VLAN Tags
    if 'vlanTags' in rule:
        lits = ''
        objs = ''
        if 'literals' in rule['vlanTags']:
            temp_list = []
            for i in rule['vlanTags']['literals']:
                if i['startTag'] == i['endTag']:
                    temp_list.append(str(i['startTag']))
                else:
                    temp_list.append(f'{i["startTag"]}-{i["endTag"]}')
            if len(temp_list) > 1:
                lits = '; '.join(temp_list)
            else:
                lits = temp_list[0]
        if 'objects' in rule['vlanTags']:
            temp_list = [i['name'] for i in rule['vlanTags']['objects']]
            if len(temp_list) > 1:
                objs = '; '.join(temp_list)
            else:
                objs = temp_list[0]
        if (lits != '') and (objs != ''):
            R_VLAN = '; '.join([lits,objs])
        elif lits != '':
            R_VLAN = lits
        elif objs != '':
            R_VLAN = objs
    # Users
    if 'users' in rule:
        temp_list = [i['name'] for i in rule['users']['objects']]
        if len(temp_list) > 1:
            R_USERS = '; '.join(temp_list)
        else:
            R_USERS = temp_list[0]
    # Application Filters, Too complext to represent simply.
    # Using true/false to represent if configured or not
    if 'applications' in rule:
        R_APP = 'true'
    # URL Reputation Filters, Too complext to represent simply.
    # Using true/false to represent if configured or not
    if 'urls' in rule:
        R_URL = 'true'
    # Source Ports
    if 'sourcePorts' in rule:
        lits = ''
        objs = ''
        if 'literals' in rule['sourcePorts']:
            temp_list = []
            for i in rule['sourcePorts']['literals']:
                if i['protocol'] == '6':
                    temp_list.append(f'TCP:{i["port"]}')
                elif i['protocol'] == '17':
                    temp_list.append(f'UDP:{i["port"]}')
            if len(temp_list) > 1:
                lits = '; '.join(temp_list)
            else:
                lits = temp_list[0]
        if 'objects' in rule['sourcePorts']:
            temp_list = [i['name'] for i in rule['sourcePorts']['objects']]
            if len(temp_list) > 1:
                objs = '; '.join(temp_list)
            else:
                objs = temp_list[0]
        if (lits != '') and (objs != ''):
            R_SRC_P = '; '.join([lits,objs])
        elif lits != '':
            R_SRC_P = lits
        elif objs != '':
            R_SRC_P = objs
    # Destination Ports
    if 'destinationPorts' in rule:
        lits = ''
        objs = ''
        if 'literals' in rule['destinationPorts']:
            temp_list = []
            for i in rule['destinationPorts']['literals']:
                if i['protocol'] == '6':
                    temp_list.append(f'TCP:{i["port"]}')
                elif i['protocol'] == '17':
                    temp_list.append(f'UDP:{i["port"]}')
            if len(temp_list) > 1:
                lits = '; '.join(temp_list)
            else:
                lits = temp_list[0]
        if 'objects' in rule['destinationPorts']:
            temp_list = [i['name'] for i in rule['destinationPorts']['objects']]
            if len(temp_list) > 1:
                objs = '; '.join(temp_list)
            else:
                objs = temp_list[0]
        if (lits != '') and (objs != ''):
            R_DST_P = '; '.join([lits,objs])
        elif lits != '':
            R_DST_P = lits
        elif objs != '':
            R_DST_P = objs
    # Encapsulation Ports, equivalent to Destination Ports for Prefilter
    if 'encapsulationPorts' in rule:
        if len(rule['encapsulationPorts']) > 1:
            R_DST_P = '; '.join(rule['encapsulationPorts'])
        else:
            R_DST_P = rule['encapsulationPorts'][0]
    # Source SGTs
    if 'sourceSecurityGroupTags' in rule:
        temp_list = [i['name'] for i in rule['sourceSecurityGroupTags']['objects']]
        if len(temp_list) > 1:
            R_SRC_SGT = '; '.join(temp_list)
        else:
            R_SRC_SGT = temp_list[0]
    # Destination SGTs
    if 'destinationSecurityGroupTags' in rule:
        temp_list = [i['name'] for i in rule['destinationSecurityGroupTags']['objects']]
        if len(temp_list) > 1:
            R_DST_SGT = '; '.join(temp_list)
        else:
            R_DST_SGT = temp_list[0]
    # IPS Policy
    if 'ipsPolicy' in rule:
        R_IPS = rule['ipsPolicy']['name']
    # File Policy
    if 'filePolicy' in rule:
        R_FILE = rule['filePolicy']['name']

    temp_list = [
        FMC_NAME,
        ACP_NAME,
        ACP_TYPE,
        ACP_ID,
        R_NAME,
        R_ID,
        R_ACTION,
        R_SRC_ZN,
        R_DST_ZN,
        R_SRC_IP,
        R_DST_IP,
        R_VLAN,
        R_USERS,
        R_APP,
        R_URL,
        R_SRC_P,
        R_DST_P,
        R_SRC_SGT,
        R_DST_SGT,
        R_IPS,
        R_FILE,
    ]
    return temp_list

def put_bulk_acp_rules(server,headers,username,password,API_UUID,acp_id,put_data):
    try:
        url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/policy/accesspolicies/{acp_id}/accessrules?bulk=true'
        print(f'Performing API PUT to: {url}')
        # REST call with SSL verification turned off:
        r = requests.put(url, json=put_data, headers=headers, verify=False)
        status_code = r.status_code
        json_resp = r.json()
        if status_code == 200:
            print(f'Access Rules successfully updated')
        else:
            print(f'Status code:--> {status_code}')
            print(f'Error occurred in PUT --> {json_resp}')
            r.raise_for_status()
    except requests.exceptions.HTTPError:
        err_resp = r.json()
        for item in err_resp['error']['messages']:
            # Error Handling for Access Token Timeout
            if 'Access token invalid' in item['description']:
                print ('Access token invalid... Attempting to Renew Token...')
                results=access_token(server,headers,username,password)
                headers['X-auth-access-token']=results[0]
                try:

                    # REST call with SSL verification turned off:
                    r = requests.put(url, json=put_data, headers=headers, verify=False)
                    print(f'Performing API PUT to: {url}')
                    status_code = r.status_code
                    json_resp = r.json()
                    if (status_code == 200):
                        print(f'Access Rules successfully updated')
                    else:
                        print(f'Status code:--> {status_code}')
                        print(f'Error occurred in PUT --> {json.dumps(json_resp,indent=4)}')
                        r.raise_for_status()


                except requests.exceptions.HTTPError:
                    print (f'Error in connection --> {traceback.format_exc()}')

            else:
                print (f'Error in connection --> {traceback.format_exc()}')
    # End
    finally:
        if r: r.close()


















