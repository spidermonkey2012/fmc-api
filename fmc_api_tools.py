# Import Required Modules
import os,\
        re,\
        sys,\
        csv,\
        json,\
        socket,\
        random,\
        netaddr,\
        netmiko,\
        tarfile,\
        getpass,\
        requests,\
        warnings,\
        traceback
from datetime import datetime
from ipaddress import IPv4Network

# Import custom modules from file
from fmc_api_module import \
        select,\
        get_items,\
        parse_rule,\
        access_token,\
        get_fmc_details,\
        define_password,\
        put_bulk_acp_rules,\
        get_device_details,\
        get_net_object_uuid
# Disable SSL warning
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

#
#
#
# Define Blank URL Get Script as Function
def blank_get(server,headers):
    print ('''
***********************************************************************************************
*                             Basic URL GET Script                                            *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. URI Path (/api/fmc_config/v1/domain/{domain_UUID}/object/networkgroups/{object_UUID})   *
*                                                                                             *
*  2. Expand output to show details of each object *(Not Supported with {object_UUID} GET)    *
*                                                                                             *
*  3. Limit output to a specific number of objects *(Not Supported with {object_UUID} GET)    *
*                                                                                             *
*  4. Save output to file                                                                     *
*                                                                                             *
*                                                                                             *
***********************************************************************************************
''')

    # Request API URI Path
    api_path = input('Please Enter URI: ').lower().strip()

    # Clean URI
    if (api_path[-1] == '/'):
        api_path = api_path[:-1]

    # Check for GETBYID Operation in URI
    getbyid = re.match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', api_path[-36:])

    # Set URL
    url = f'{server}{api_path}'

    # Ask to Expand and/or assign output Limit
    if getbyid == None:
        expand = input('Would You Like To Expand Output Entries? [y/N]: ').lower()
        limit = input('Would You Like To Limit Output Entries? [Number or "No"]: ').lower()

        if limit not in (['no','n','']) and expand in (['yes','ye','y']):
            url = f'{server}{api_path}?expanded=true&limit={limit}'
        elif limit not in (['no','n','']) and expand in (['no','n','']):
            url = f'{server}{api_path}?limit={limit}'
        elif limit in (['no','n','']) and expand in (['yes','ye','y']):
            url = f'{server}{api_path}?expanded=true'
    if url[-1] == '/':
        url = url[:-1]

    # Perform API GET call
    print(f'Performing API GET to: {url}')
    try:
        # REST call with SSL verification turned off:
        r = requests.get(url, headers=headers, verify=False)
        status_code = r.status_code
        resp = r.json()
        if (status_code == 200):
            print('GET successful...')
            # Ask if output should be saved to File
            save = input('Would You Like To Save The Output To File? [y/N]: ').lower()
            if save in (['yes','ye','y']):
                # Random Generated JSON Output File
                filename = ''.join(i for i in [chr(random.randint(97,122)) for i in range(6)])
                filename += '.json'
                print(f'*\n*\nRANDOM LOG FILE CREATED... {filename}\n')
                with open(filename, 'a') as outfile:
                    outfile.write(json.dumps(resp,indent=4))
            elif save in (['no','n','']):
                print(json.dumps(resp,indent=4))
        else:
            r.raise_for_status()
            print(f'Error occurred in GET --> {resp}')
    except requests.exceptions.HTTPError as err:
        print(f'Error in connection --> {err}')
        print(json.dumps(resp,indent=4))
    # End
    finally:
        try:
            if r: r.close()
        except:
            None


#
#
#
# Define Network Object POST Script as Funtion
def post_network_object(server,headers,api_uuid):
    print ('''
***********************************************************************************************
*                          Create Network Objects in bulk                                     *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. Select Object type                                                                      *
*                                                                                             *
*  2. CSV Data Input file                                                                     *
*       # CSV FORMAT:                                                                         *
*           No Header Row & comma delimited                                                   *
*           Can contain Host, Range, Network or FQDN objects, not a combination               *
*           Column0 = ObjectName                                                              *
*           Column1 = Address                                                                 *
*                                                                                             *
***********************************************************************************************
''')
    obj_types = [
        {
            'name':'Host',
            'url':f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/hosts?bulk=true'
        },
        {
            'name':'Range',
            'url':f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/ranges?bulk=true'
        },
        {
            'name':'Network',
            'url':f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/networks?bulk=true'
        },
        {
            'name':'FQDN',
            'url':f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/fqdns?bulk=true'
        }
    ]
    # Select type of Object to post
    obj_type = select('Object Type',obj_types)

    Test = False

    while not Test:
        # Request Input File
        read_csv = input('Please Enter Input File /full/file/path.csv: ')
        if os.path.isfile(read_csv):
            # Read csv file
            open_read_csv = open(read_csv, 'r')
            my_csv_reader = csv.reader(open_read_csv, delimiter=',')
            Test = True
        else:
            print('MUST PROVIDE INPUT FILE...')

    post_data = []
    # Create For Loop To Process Each Item In CSV
    for row in my_csv_reader:
        obj_name = row[0]
        address = row[1]
        post_data.append({
            'name': obj_name,
            'type': obj_type['name'],
            'description': '',
            'value': address
        })

    try:
        # REST call with SSL verification turned off:
        url = obj_type['url']
        r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
        status_code = r.status_code
        resp = r.text
        print(f'Status code is: {status_code}')
        if status_code == 201 or status_code == 202:
            print('Network Objects successfully created...')
        else :
            print(f'Error occurred in POST --> {json.dumps(r.json(),indent=4)}')
            r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print (f'Error in connection --> {traceback.format_exc()}')
    finally:
        try:
            if r: r.close()
        except:
            None

#
#
#
# Define Network Object-Group POST Script as Funtion
def post_network_object_group(server,headers,api_uuid):
    print ('''
***********************************************************************************************
*                     Create Network Objects and Object Groups in bulk                        *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. TXT Data Input file                                                                     *
*       # Output from ASA "show run object network" and "show run object-group network"       *
*       # Ensure no object names overlap with existing objects                                *
*       # Ensure nested groups are above groups nesting them                                  *
*                                                                                             *
***********************************************************************************************
''')

    Test = False
    while not Test:
        # Request Input File
        read_file = input('Please Enter Input File /full/file/path.txt: ').strip()
        if os.path.isfile(read_file):
            # Read csv file
            open_read_file = open(read_file, 'r').read()
            Test = True
        else:
            print('MUST PROVIDE INPUT FILE...')

    temp_data = {
        'objects':[],
        'groups':[]
    }

    split = re.split(r'\nobject',open_read_file)
    for item in split:
        obj = item.splitlines()
        name = obj[0].split()[-1]
        if obj[0].startswith('-group'):
            obj.pop(0)
            temp_data['groups'].append({'name':name,'entries':obj})
        else:
            obj.pop(0)
            temp_data['objects'].append({'name':name,'entry':obj[0].strip()})

    data = {
        'objects': {
            'Host':[],
            'Network':[],
            'Range':[],
            'FQDN':[]
        },
        'groups':{}
    }

    for obj in temp_data['objects']:
        obj_name = obj['name']
        if obj['entry'].startswith('host'):
            obj_type = 'Host'
            address = obj['entry'].split()[-1]
            data['objects']['Host'].append({
                'name': obj_name,
                'type': obj_type,
                'description': '',
                'value': address
            })
        elif obj['entry'].startswith('subnet'):
            obj_type = 'Network'
            address = f'{obj["entry"].split()[-2]}/{obj["entry"].split()[-1]}'
            data['objects']['Network'].append({
                'name': obj_name,
                'type': obj_type,
                'description': '',
                'value': address
            })
        elif obj['entry'].startswith('range'):
            obj_type = 'Range'
            address = f'{obj["entry"].split()[-2]}-{obj["entry"].split()[-1]}'
            data['objects']['Range'].append({
                'name': obj_name,
                'type': obj_type,
                'description': '',
                'value': address
            })
        if obj['entry'].startswith('fqdn'):
            obj_type = 'FQDN'
            address = obj['entry'].split()[-1]
            data['objects']['FQDN'].append({
                'name': obj_name,
                'type': obj_type,
                'description': '',
                'value': address
            })


    # Post Host objects, and store JSON response with object uuids
    try:
        # REST call with SSL verification turned off:
        post_data = data['objects']['Host']
        url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/hosts?bulk=true'
        r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
        status_code = r.status_code
        resp = r.text
        print(f'Status code is: {status_code}')
        if status_code == 201 or status_code == 202:
            print('Network Objects successfully created...')
            data['objects']['Host'] = r.json()['items']
        else :
            print(f'Error occurred in POST --> {json.dumps(r.json(),indent=4)}')
            r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print (f'Error in connection --> {traceback.format_exc()}')
    finally:
        try:
            if r: r.close()
        except:
            None

    # Post Network objects, and store JSON response with object uuids
    try:
        # REST call with SSL verification turned off:
        post_data = data['objects']['Network']
        url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/networks?bulk=true'
        r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
        status_code = r.status_code
        resp = r.text
        print(f'Status code is: {status_code}')
        if status_code == 201 or status_code == 202:
            print('Network Objects successfully created...')
            data['objects']['Network'] = r.json()['items']
        else :
            print(f'Error occurred in POST --> {json.dumps(r.json(),indent=4)}')
            r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print (f'Error in connection --> {traceback.format_exc()}')
    finally:
        try:
            if r: r.close()
        except:
            None

    # Post Ranges objects, and store JSON response with object uuids
    try:
        # REST call with SSL verification turned off:
        post_data = data['objects']['Range']
        url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/ranges?bulk=true'
        r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
        status_code = r.status_code
        resp = r.text
        print(f'Status code is: {status_code}')
        if status_code == 201 or status_code == 202:
            print('Network Objects successfully created...')
            data['objects']['Range'] = r.json()['items']
        else :
            print(f'Error occurred in POST --> {json.dumps(r.json(),indent=4)}')
            r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print (f'Error in connection --> {traceback.format_exc()}')
    finally:
        try:
            if r: r.close()
        except:
            None

    # Post FQDN objects, and store JSON response with object uuids
    try:
        # REST call with SSL verification turned off:
        post_data = data['objects']['FQDN']
        url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/fqdns?bulk=true'
        r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
        status_code = r.status_code
        resp = r.text
        print(f'Status code is: {status_code}')
        if status_code == 201 or status_code == 202:
            print('Network Objects successfully created...')
            data['objects']['FQDN'] = r.json()['items']
        else :
            print(f'Error occurred in POST --> {json.dumps(r.json(),indent=4)}')
            r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print (f'Error in connection --> {traceback.format_exc()}')
    finally:
        try:
            if r: r.close()
        except:
            None

    for obj in temp_data['groups']:
        obj_name = obj['name']
        obj = {
            'name': obj_name,
            'type': 'NetworkGroup',
            'objects': [],
            'literals': []
        }
        for item in obj['entries']:
            if 'network-object host ' in item:
                address = item.split()[-1]
                obj['literals'].append({
                    'type': 'Host',
                    'value': address
                })
            elif 'network-object object ' in item:
                nestObjName = item.split()[-1]
                for k,v in data['objects'].items():
                    for i in v:
                        if i['name'] == nestObjName:
                            obj['objects'].append({
                                'type': i['type'],
                                'id': i['id']
                            })
            elif 'network-object ' in item:
                address = f'{item.split()[-2]}/{item.split()[-1]}'
                obj['literals'].append({
                    'type': 'Network',
                    'value': address
                })
            elif 'group-object ' in item:
                nestObjName = item.split()[-1]
                i = data['groups'][nestObjName]
                obj['objects'].append({
                    'type': i['type'],
                    'id': i['id']
                })

        # Post object group, and store JSON response with object uuids
        try:
            # REST call with SSL verification turned off:
            post_data = obj
            url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/networkgroups'
            r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
            status_code = r.status_code
            resp = r.text
            print(f'Status code is: {status_code}')
            if status_code == 201 or status_code == 202:
                print('Network Object Group successfully created...')
                data['groups'].update({obj_name:r.json()})
            else :
                print(f'Error occurred in POST --> {json.dumps(r.json(),indent=4)}')
                r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print (f'Error in connection --> {traceback.format_exc()}')
        finally:
            try:
                if r: r.close()
            except:
                None


#
#
#
# Define IPS/File Policy Put Script as Funtion
def put_intrusion_file(server,headers,api_uuid):
    print ('''
***********************************************************************************************
*                     Update IPS and/or File Policy for Access Rules                          *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. Select Access Policy                                                                    *
*                                                                                             *
*  2. Apply IPS and File Policy to ALL rules [y/N]                                            *
*       Note: Selecting NO will apply changes only to rules                                   *
*               which currently have IPS/File policy applied                                  *
*                                                                                             *
*  3. Select Intrusion Policy and Variable Set to apply to ALL rules                          *
*       Note: Selecting 'None' will NOT remove currently applied policy                       *
*                                                                                             *
*  4. Select File Policy to apply to ALL rules                                                *
*       Note: Selecting 'None' will NOT remove currently applied policy                       *
*                                                                                             *
***********************************************************************************************
''')
    all_rules = False
    Test = False
    while not Test:
        choice = input('Would You Like To Apply IPS and File Policy to ALL rules? [y/N]: ').lower()
        if choice in (['yes','ye','y']):
            all_rules = True
            Test = True
        elif choice in (['no','n','']):
            Test = True
        else:
            print('Invalid Selection...\n')


    # Get all Access Control Policies
    print('*\n*\nCOLLECTING Access Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/accesspolicies?expanded=true&offset=0&limit=1000'
    acp_list = get_items(url,headers)

    acp = select('Access Control Policy',acp_list)
    #print(json.dumps(acp,indent=4))

    # Get all Access Control Policy rules
    print('*\n*\nCOLLECTING Access Policy rules...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/accesspolicies/{acp["id"]}/accessrules?offset=0&limit=1000&expanded=true'
    acp_rules = get_items(url,headers)

    # Get all Intrusion Policies
    print('*\n*\nCOLLECTING Intusion Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/intrusionpolicies?offset=0&limit=1000'
    ips_list = get_items(url,headers)
    # Add None option
    ips_list.append({'None':'None'})
    ips = select('Intusion Policy',ips_list)
    #print(json.dumps(ips,indent=4))

    if ips:
        # Get all Variable Sets
        print('*\n*\nCOLLECTING Variable Sets...')
        url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/variablesets?offset=0&limit=1000'
        vset_list = get_items(url,headers)
        vset = select('Variable Set',vset_list)
    else:
        vset = None

    # Get all File Policies
    print('*\n*\nCOLLECTING File Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/filepolicies?offset=0&limit=1000'
    file_list = get_items(url,headers)
    # Add None option
    file_list.append({'None':'None'})
    filepolicy = select('File Policy',file_list)

    # Operate only on ALLOW rules
    acp_rules = [i for i in acp_rules if i['action'] == 'ALLOW']

    # Operate only on rules that have IPS/File policy
    if not all_rules:
        acp_rules = [i for i in acp_rules if ('ipsPolicy' in i) or ('filePolicy' in i)]

    # Exit if no IPS or File Policy Selected
    if (not ips) and (not filepolicy):
        print(f'*\n*\nNo IPS or File policy selected, Exiting...\n')
        return

    # For Loop to update all rules
    for item in acp_rules:
        if (ips) and ((all_rules) or ('ipsPolicy' in item)):
            # Create IPS Policy
            item ['ipsPolicy'] = {}
            # Assign Values
            item ['ipsPolicy']['id'] = ips['id']
            item ['ipsPolicy']['name'] = ips['name']
            item ['ipsPolicy']['type'] = 'IntrusionPolicy'
            # Create VariableSet
            item ['variableSet'] = {}
            # Assign Values
            item ['variableSet']['id'] = vset['id']
            item ['variableSet']['name'] = vset['name']
            item ['variableSet']['type'] = 'VariableSet'
        if (filepolicy) and ((all_rules) or ('filePolicy' in item)):
            # Create FilePolicy
            item ['filePolicy'] = {}
            # Assign Values
            item ['filePolicy']['id'] = filepolicy['id']
            item ['filePolicy']['name'] = filepolicy['name']
            item ['filePolicy']['type'] = 'FilePolicy'

        # Delete Unprocessable items
        del item['links']
        del item['metadata']
        if 'commentHistoryList' in item:
            del item['commentHistoryList']
        if ('logFiles' in item) and ('filePolicy' not in item):
            del item['logFiles']

    if len(acp_rules) > 500:
        print(f'*\n*\nModifying a large number of rules, please be patient...\n')
    # Send PUT requests with a maximum 1000 items per request
    while len(acp_rules) !=0:
        if len(acp_rules) >= 1000:
            put_data = acp_rules[:1000]
            put_bulk_acp_rules(server,headers,username,password,API_UUID,acp['id'],put_data)
            acp_rules = acp_rules[1000:]
        else:
            put_data = acp_rules[:len(acp_rules)]
            put_bulk_acp_rules(server,headers,username,password,API_UUID,acp['id'],put_data)
            acp_rules = acp_rules[len(acp_rules):]



#
#
#
# Define Inventory List Script as Funtion
def get_inventory(server,headers,api_uuid):
    print ('''
***********************************************************************************************
*                           Pull Full FMC Device Inventory List                               *
*_____________________________________________________________________________________________*
*                                                                                             *
***********************************************************************************************
''')
    # Get all Devices
    print('*\n*\nCOLLECTING ALL INVENTORY...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/devices/devicerecords?expanded=true&offset=0&limit=1000'
    devicelist_data = get_items(url,headers)

    # Get all Cluster Devices
    print('*\n*\nCOLLECTING CLUSTER INVENTORY...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/deviceclusters/ftddevicecluster?expanded=true&offset=0&limit=1000'
    cluster_data = get_items(url,headers)

    # Get all HA Devices
    print('*\n*\nCOLLECTING HA PAIR INVENTORY...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/devicehapairs/ftddevicehapairs?expanded=true&offset=0&limit=1000'
    ha_data = get_items(url,headers)



    # Create base inventory dict
    inventory = {
        'deviceClusters':[],
        'deviceHAPairs':[],
        'devices':[]
        }

    # Append HA devices to inventory
    if cluster_data != []:
        for item in cluster_data:
            temp_dict = {}
            temp_dict['name']= item['name']
            if 'masterDevice' in item:
                temp_dict['controlDevice'] = get_device_details(item['masterDevice']['id'],devicelist_data)
                temp_dict['dataDevices'] = []
                if 'slaveDevices' in item:
                    for item in item['slaveDevices']:
                        temp_dict['dataDevices'].append(get_device_details(item['id'],devicelist_data))
            else:
                temp_dict['controlDevice'] = get_device_details(item['controlDevice']['deviceDetails']['id'],devicelist_data)
                temp_dict['dataDevices'] = []
                if 'dataDevices' in item:
                    for item in item['dataDevices']:
                        temp_dict['dataDevices'].append(get_device_details(item['deviceDetails']['id'],devicelist_data))
            inventory['deviceClusters'].append(temp_dict)

    # Append HA devices to inventory
    if ha_data != []:
        for item in ha_data:
            temp_dict = {}
            temp_dict['name']= item['name']
            temp_dict['primary'] = get_device_details(item['primary']['id'],devicelist_data)
            temp_dict['secondary'] = get_device_details(item['secondary']['id'],devicelist_data)
            inventory['deviceHAPairs'].append(temp_dict)

    # Append remaining devices to inventory list
    if devicelist_data != []:
        ids = [i['id'] for i in devicelist_data]
        for id in ids:
            inventory['devices'].append(get_device_details(id,devicelist_data))


    print('*\n*\nFMC Inventory compilation successful...')
    # Ask if JSON output should be saved to File
    save = input('Would you like to save the JSON output to file? [y/N]: ').lower()
    if save in (['yes','ye','y']):
        # Random Generated JSON Output File
        filename = ''.join(i for i in [chr(random.randint(97,122)) for i in range(6)])
        filename += '.json'
        print(f'*\n*\nRANDOM OUTPUT FILE CREATED... {filename}\n')
        with open(filename, 'a') as outfile:
            outfile.write(json.dumps(inventory,indent=4))
    elif save in (['no','n','']):
        p = input('Would you like to print JSON Output to console? [y/N]: ').lower()
        if p in (['yes','ye','y']):
            print(json.dumps(inventory,indent=4))

    # Ask if CSV output should be saved to File
    save = input('Would You Like To Save CSV Output To File? [y/N]: ').lower()
    if save in (['yes','ye','y']):
        # Random Generated CSV Output File
        filename = ''.join(i for i in [chr(random.randint(97,122)) for i in range(6)])
        filename += '.csv'
        print(f'*\n*\nRANDOM OUTPUT FILE CREATED... {filename}\n')
        with open(filename, 'a') as outfile:
            outfile.write('NAME,HOSTNAME,MODEL,VERSION,ACCESS POLICY,STATUS,DEVICE SERIAL,CHASSIS SERIAL,MODE,LICENSE,SRU,VDB,SNORT VERSION,SNORT ENG,CONTAINER,CHASSIS INVENTORY,DOMAIN,MULTI-INSTANCE\n')
            if inventory['deviceClusters'] != []:
                for item in inventory['deviceClusters']:
                    # Reset all variables
                    name = ''
                    hostname = ''
                    model = ''
                    version = ''
                    acp = ''
                    status = ''
                    device_sn = ''
                    chassis_sn = ''
                    mode = ''
                    license = ''
                    sru_ver = ''
                    vdb_ver = ''
                    snort_ver = ''
                    snort_eng = ''
                    container = ''
                    chassis_inv = ''
                    domain = ''
                    multi_inst = ''

                    name = item['controlDevice']['name']
                    model = item['controlDevice']['model']
                    version = item['controlDevice']['sw_version']
                    status = item['controlDevice']['healthStatus']
                    license = ';'.join(item['controlDevice']['license_caps'])
                    if 'accessPolicy' in item['controlDevice']: acp = item['controlDevice']['accessPolicy']['name']
                    if 'hostName' in item['controlDevice']: hostname = item['controlDevice']['hostName']
                    if 'snortEngine' in item['controlDevice']: snort_eng = item['controlDevice']['snortEngine']
                    if 'deviceSerialNumber' in item['controlDevice']: device_sn = item['controlDevice'
                                                                        ]['deviceSerialNumber']
                    if 'containerDetails' in item['controlDevice']: container = f"""{item['controlDevice'
                                                                        ]['containerDetails'
                                                                        ]['type']}: {
                                                                    item['controlDevice'
                                                                        ]['containerDetails'
                                                                        ]['name']}; {
                                                                    item['controlDevice'
                                                                        ]['containerDetails'
                                                                        ]['role']}"""
                    if 'inventoryData' in item['controlDevice']: chassis_inv = '; '.join([f'''{k}: {
                                                                                v}''' for k,v in item['controlDevice'
                                                                                ]['inventoryData'
                                                                                ].items()])
                    if 'domain' in item['controlDevice']: domain = item['controlDevice']['domain'
                                                                        ]['name']
                    if 'isMultiInstance' in item['controlDevice']: multi_inst = item['controlDevice'
                                                                        ]['isMultiInstance']


                    if 'ftdMode' in item['controlDevice']: mode = item['controlDevice']['ftdMode']
                    if 'sruVersion' in item['controlDevice']: sru_ver = item['controlDevice']['sruVersion']
                    if 'vdbVersion' in item['controlDevice']: vdb_ver = item['controlDevice']['vdbVersion']
                    if 'snortVersion' in item['controlDevice']: snort_ver = item['controlDevice'
                                                                                    ]['snortVersion']
                    if 'chassisData' in item['controlDevice']: chassis_sn = item['controlDevice'
                                                                                    ]['chassisData'
                                                                                    ]['chassisSerialNo']
                    outfile.write(f'''{name},{hostname},{model},{version},{acp},{status},{device_sn},{
                                    chassis_sn},{mode},{license},{sru_ver},{vdb_ver},{snort_ver},{
                                    snort_eng},{container},{chassis_inv},{domain},{multi_inst}\n''')
                    if 'dataDevices' in item:
                        for item in item['dataDevices']:
                            # Reset all variables
                            name = ''
                            hostname = ''
                            model = ''
                            version = ''
                            acp = ''
                            status = ''
                            device_sn = ''
                            chassis_sn = ''
                            mode = ''
                            license = ''
                            sru_ver = ''
                            vdb_ver = ''
                            snort_ver = ''
                            snort_eng = ''
                            container = ''
                            chassis_inv = ''
                            domain = ''
                            multi_inst = ''

                            name = item['name']
                            model = item['model']
                            version = item['sw_version']
                            status = item['healthStatus']
                            license = ';'.join(item['license_caps'])
                            if 'accessPolicy' in item: acp = item['accessPolicy']['name']
                            if 'hostName' in item: hostname = item['hostName']
                            if 'snortEngine' in item: snort_eng = item['snortEngine']
                            if 'deviceSerialNumber' in item: device_sn = item['deviceSerialNumber']
                            if 'containerDetails' in item: container = f"""{item['containerDetails'
                                                                                ]['type']}: {
                                                                            item['containerDetails'
                                                                                ]['name']}; {
                                                                            item['containerDetails'
                                                                                ]['role']}"""
                            if 'inventoryData' in item: chassis_inv = '; '.join([f'''{k}: {
                                                                            v}''' for k,v in item['inventoryData'
                                                                            ].items()])
                            if 'domain' in item: domain = item['domain']['name']
                            if 'isMultiInstance' in item: multi_inst = item['isMultiInstance']


                            if 'ftdMode' in item: mode = item['ftdMode']
                            if 'sruVersion' in item: sru_ver = item['sruVersion']
                            if 'vdbVersion' in item: vdb_ver = item['vdbVersion']
                            if 'snortVersion' in item: snort_ver = item['snortVersion']
                            if 'chassisData' in item: chassis_sn = item['chassisData']['chassisSerialNo']
                            outfile.write(f'''{name},{hostname},{model},{version},{acp},{status},{device_sn},{
                                            chassis_sn},{mode},{license},{sru_ver},{vdb_ver},{snort_ver},{
                                            snort_eng},{container},{chassis_inv},{domain},{multi_inst}\n''')
            if inventory['deviceHAPairs'] != []:
                for item in inventory['deviceHAPairs']:
                    # HA Primary Member
                    # Reset all variables
                    name = ''
                    hostname = ''
                    model = ''
                    version = ''
                    acp = ''
                    status = ''
                    device_sn = ''
                    chassis_sn = ''
                    mode = ''
                    license = ''
                    sru_ver = ''
                    vdb_ver = ''
                    snort_ver = ''
                    snort_eng = ''
                    container = ''
                    chassis_inv = ''
                    domain = ''
                    multi_inst = ''

                    name = item['primary']['name']
                    model = item['primary']['model']
                    version = item['primary']['sw_version']
                    status = item['primary']['healthStatus']
                    license = ';'.join(item['primary']['license_caps'])
                    if 'accessPolicy' in item['primary']: acp = item['primary']['accessPolicy']['name']
                    if 'hostName' in item['primary']: hostname = item['primary']['hostName']
                    if 'snortEngine' in item['primary']: snort_eng = item['primary']['snortEngine']
                    if 'deviceSerialNumber' in item['primary']: device_sn = item['primary'
                                                                        ]['deviceSerialNumber']
                    if 'containerDetails' in item['primary']: container = f"""{item['primary'
                                                                        ]['containerDetails'
                                                                        ]['type']}: {
                                                                    item['primary'
                                                                        ]['containerDetails'
                                                                        ]['name']}"""
                    if 'inventoryData' in item['primary']: chassis_inv = '; '.join([f'''{k}: {
                                                                                v}''' for k,v in item['primary'
                                                                                ]['inventoryData'
                                                                                ].items()])
                    if 'domain' in item['primary']: domain = item['primary']['domain'
                                                                        ]['name']
                    if 'isMultiInstance' in item['primary']: multi_inst = item['primary'
                                                                        ]['isMultiInstance']
                    if 'ftdMode' in item['primary']: mode = item['primary']['ftdMode']
                    if 'sruVersion' in item['primary']: sru_ver = item['primary']['sruVersion']
                    if 'vdbVersion' in item['primary']: vdb_ver = item['primary']['vdbVersion']
                    if 'snortVersion' in item['primary']: snort_ver = item['primary']['snortVersion']
                    if 'chassisData' in item['primary']: chassis_sn = item['primary']['chassisData'
                                                                                    ]['chassisSerialNo']
                    outfile.write(f'''{name},{hostname},{model},{version},{acp},{status},{device_sn},{
                                       chassis_sn},{mode},{license},{sru_ver},{vdb_ver},{snort_ver},{
                                        snort_eng},{container},{chassis_inv},{domain},{multi_inst}\n''')
                    # HA Secondary Member
                    # Reset all variables
                    name = ''
                    hostname = ''
                    model = ''
                    version = ''
                    acp = ''
                    status = ''
                    device_sn = ''
                    chassis_sn = ''
                    mode = ''
                    license = ''
                    sru_ver = ''
                    vdb_ver = ''
                    snort_ver = ''
                    snort_eng = ''
                    container = ''
                    chassis_inv = ''
                    domain = ''
                    multi_inst = ''

                    name = item['secondary']['name']
                    model = item['secondary']['model']
                    version = item['secondary']['sw_version']
                    status = item['secondary']['healthStatus']
                    license = ';'.join(item['secondary']['license_caps'])
                    if 'accessPolicy' in item['secondary']: acp = item['secondary']['accessPolicy']['name']
                    if 'hostName' in item['secondary']: hostname = item['secondary']['hostName']
                    if 'snortEngine' in item['secondary']: snort_eng = item['secondary']['snortEngine']
                    if 'deviceSerialNumber' in item['secondary']: device_sn = item['secondary'
                                                                        ]['deviceSerialNumber']
                    if 'containerDetails' in item['secondary']: container = f"""{item['secondary'
                                                                        ]['containerDetails'
                                                                        ]['type']}: {
                                                                    item['secondary'
                                                                        ]['containerDetails'
                                                                        ]['name']}"""
                    if 'inventoryData' in item['secondary']: chassis_inv = '; '.join([f'''{k}: {
                                                                                v}''' for k,v in item['secondary'
                                                                                ]['inventoryData'
                                                                                ].items()])
                    if 'domain' in item['secondary']: domain = item['secondary']['domain'
                                                                        ]['name']
                    if 'isMultiInstance' in item['secondary']: multi_inst = item['secondary'
                                                                        ]['isMultiInstance']
                    if 'ftdMode' in item['secondary']: mode = item['secondary']['ftdMode']
                    if 'sruVersion' in item['secondary']: sru_ver = item['secondary']['sruVersion']
                    if 'vdbVersion' in item['secondary']: vdb_ver = item['secondary']['vdbVersion']
                    if 'snortVersion' in item['secondary']: snort_ver = item['secondary']['snortVersion']
                    if 'chassisData' in item['secondary']: chassis_sn = item['secondary']['chassisData'
                                                                                    ]['chassisSerialNo']
                    outfile.write(f'''{name},{hostname},{model},{version},{acp},{status},{device_sn},{
                                       chassis_sn},{mode},{license},{sru_ver},{vdb_ver},{snort_ver},{
                                        snort_eng},{container},{chassis_inv},{domain},{multi_inst}\n''')
            if inventory['devices'] != []:
                for item in inventory['devices']:
                    # Reset all variables
                    name = ''
                    hostname = ''
                    model = ''
                    version = ''
                    acp = ''
                    status = ''
                    device_sn = ''
                    chassis_sn = ''
                    mode = ''
                    license = ''
                    sru_ver = ''
                    vdb_ver = ''
                    snort_ver = ''
                    snort_eng = ''
                    container = ''
                    chassis_inv = ''
                    domain = ''
                    multi_inst = ''

                    name = item['name']
                    model = item['model']
                    version = item['sw_version']
                    license = ';'.join(item['license_caps'])
                    status = item['healthStatus']
                    if 'accessPolicy' in item: acp = item['accessPolicy']['name']
                    if 'hostName' in item: hostname = item['hostName']
                    if 'snortEngine' in item: snort_eng = item['snortEngine']
                    if 'deviceSerialNumber' in item: device_sn = item['deviceSerialNumber']
                    if 'containerDetails' in item: container = f"""{item['containerDetails'
                                                                        ]['type']}: {
                                                                    item['containerDetails'
                                                                        ]['name']}"""
                    if 'inventoryData' in item: chassis_inv = '; '.join([f'''{k}: {
                                                                    v}''' for k,v in item['inventoryData'
                                                                    ].items()])
                    if 'domain' in item: domain = item['domain']['name']
                    if 'isMultiInstance' in item: multi_inst = item['isMultiInstance']
                    if 'ftdMode' in item: mode = item['ftdMode']
                    if 'sruVersion' in item: sru_ver = item['sruVersion']
                    if 'vdbVersion' in item: vdb_ver = item['vdbVersion']
                    if 'snortVersion' in item: snort_ver = item['snortVersion']
                    if 'chassisData' in item: chassis_sn = item['chassisData']['chassisSerialNo']
                    outfile.write(f'''{name},{hostname},{model},{version},{acp},{status},{device_sn},{
                                       chassis_sn},{mode},{license},{sru_ver},{vdb_ver},{snort_ver},{
                                        snort_eng},{container},{chassis_inv},{domain},{multi_inst}\n''')





#
#
#
# Define Inventory List Script as Funtion
def register_ftd(server,headers,api_uuid):
    print ('''
***********************************************************************************************
*                                   Register FTD to FMC                                       *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. FTD IP address                                                                          *
*                                                                                             *
*  2. FTD display name                                                                        *
*                                                                                             *
*  3. FTD CLI username and password                                                           *
*                                                                                             *
*  4. Select ACP to apply to FTD                                                              *
*                                                                                             *
***********************************************************************************************
''')
    # Request FTD Details
    ftd_ip = input('Please enter FTD IP Address: ').strip()
    ftd_name = input('Please enter FTD display name: ').strip()
    ftd_user = input('Please enter FTD username: ').strip()
    ftd_pass = define_password()
    # Generate random Registration Key
    reg_key = ''.join(i for i in [chr(random.randint(97,122)) for i in range(6)])

    # Create Get DATA JSON Dictionary to collect all ACP names
    print('*\n*\nCOLLECTING Access Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/accesspolicies?offset=0&limit=1000'
    acp_list = get_items(url,headers)
    if acp_list == []:
        print('*\n*\nNO ACCESS POLICY CONFIGURED...\nCREATE ACCESS POLICY IN FMC AND ATTEMPT AGAIN...')
        return
    acp = select('Access Control Policy',acp_list)
    #print(json.dumps(acp,indent=4))

    post_data = {
        'name': ftd_name,
        'hostName': ftd_ip,
        'natID': 'cisco123',
        'regKey': reg_key,
        'type': 'Device',
        'license_caps': [
            'BASE',
            'MALWARE',
            'URLFilter',
            'THREAT'
        ],
        'accessPolicy': {
            'id': acp['id'],
            'type': 'AccessPolicy'
        }
    }


    url =f'{server}/api/fmc_config/v1/domain/{api_uuid}/devices/devicerecords'
    print(f'\nPerforming API POST to: {url}...\n')
    try:
        # REST call with SSL verification turned off:
        r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
        status_code = r.status_code
        resp = r.text
        print(f'Status code is: {status_code}')
        if status_code == 201 or status_code == 202:
            print('FMC Registration Post successful...')
            json_resp = r.json()
        else :
            r.raise_for_status()
            print (f'Error occurred in POST --> {resp}')
    except requests.exceptions.HTTPError as err:
        print (f'Error in connection --> {traceback.format_exc()}')
    finally:
        try:
            if r: r.close()
        except:
            None

    try:
        # Connect to FTD, and initiate registration
        print('\nConnecting to FTD for CLI registration...')
        connection = netmiko.ConnectHandler(ip=ftd_ip, device_type='autodetect', username=ftd_user, password=ftd_pass, global_delay_factor=6)
        output = connection.send_command(f'configure manager add {server.replace("https://","")} {reg_key} cisco123')
        connection.disconnect()
        print('FTD Registration command successful...')
    except:
        print (f'Error in SSH connection --> {traceback.format_exc()}')
        connection.disconnect()



#
#
#
# Define Inventory List Script as Funtion
def prefilter_to_acp(server,headers,api_uuid):
    print ('''
***********************************************************************************************
*                    Convert Prefilter rules to Access-Control rules                          *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. Select Access Policy                                                                    *
*                                                                                             *
*  2. Select Intrusion Policy and Variable Set to apply to ALL converted rules                *
*                                                                                             *
*  3. Select File Policy to apply to ALL converted rules                                      *
*                                                                                             *
***********************************************************************************************
''')
    # Get all Access Control Policies
    print('*\n*\nCOLLECTING Access Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/accesspolicies?expanded=true&offset=0&limit=1000'
    acp_list = get_items(url,headers)

    acp = select('Access Control Policy',acp_list)
    #print(json.dumps(acp,indent=4))

    # Get Prefilter Policy
    print('*\n*\nCOLLECTING Applied Prefilter Policy...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/prefilterpolicies/{acp["prefilterPolicySetting"]["id"]}/prefilterrules?expanded=true&offset=0&limit=1000'
    prefilter_list = get_items(url,headers)

    # Remove all 'TUNNEL' rules
    prefilter_list = [i for i in prefilter_list if i['ruleType'] != 'TUNNEL']

    if prefilter_list == []:
        print('*\n*\nNo Prefilter Rules available to migrate...')
        return

    # Get all Intrusion Policies
    print('*\n*\nCOLLECTING Intusion Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/intrusionpolicies?offset=0&limit=1000'
    ips_list = get_items(url,headers)
    # Add None option
    ips_list.append({'None':'None'})
    ips = select('Intusion Policy',ips_list)

    # Get all Variable Sets
    print('*\n*\nCOLLECTING Variable Sets...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/variablesets?offset=0&limit=1000'
    vset_list = get_items(url,headers)

    # Get Default Variable Set
    for item in vset_list:
        if item['name'] == 'Default-Set':
            default_vset = item

    # Select Variable Set for access rules
    if ips:
        vset = select('Variable Set',vset_list)
    else:
        vset = None

    # Get all File Policies
    print('*\n*\nCOLLECTING File Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/filepolicies?offset=0&limit=1000'
    file_list = get_items(url,headers)
    # Add None option
    file_list.append({'None':'None'})
    filepolicy = select('File Policy',file_list)
    #print(filepolicy)

    # Migrate prefilter rules to Access Rules
    print('*\n*\nConverting existing Prefilter rules to Access Rules...')
    acp_data = []
    DATE = datetime.now().strftime('%Y-%m-%d_%H%M')

    for item in prefilter_list:
        item['name']  =  f'Prefilter_{item["name"]}_{DATE}'
        if len(item['name']) > 50:
            item['newComments'] = [item['name']]
            item['name'] = item['name'][:50]
        if 'id' in item: del item['id']
        if 'metadata' in item: del item["metadata"]
        if 'links' in item: del item["links"]
        if 'bidirectional' in item: del item["bidirectional"]
        if 'sourceInterfaces' in item:
            item['sourceZones'] = item['sourceInterfaces']
            del item['sourceInterfaces']
        if 'destinationInterfaces' in item:
            item['destinationZones'] = item['destinationInterfaces']
            del item['destinationInterfaces']
        if 'bidirectional' in item: del item["bidirectional"]
        if (item['action'] == 'ANALYZE') and (item['ruleType'] !='TUNNEL'):
            item['logFiles'] = False
            item['action'] = 'ALLOW'
            item['type'] ='AccessRule'
            if ips:
                item['ipsPolicy'] = ips
                item['ipsPolicy']['type'] = 'IntrusionPolicy'
                item['variableSet'] = vset
                item['variableSet']['type'] = 'VariableSet'
            if filepolicy:
                item['logFiles'] = True
                item['sendEventsToFMC'] = True
                item['filePolicy'] = filepolicy
                item['filePolicy']['type'] = 'FilePolicy'
            del item['ruleType']
            acp_data.append(item)
        elif item['action'] =='BLOCK':
            item['logFiles'] = False
            item['type'] ='AccessRule'
            item['variableSet'] = default_vset
            del item["ruleType"]
            acp_data.append(item)
        elif item['action'] =='FASTPATH':
            item['logFiles'] = False
            item['logBegin'] = False
            item['action'] ='TRUST'
            item['type'] ='AccessRule'
            del item['ruleType']
            acp_data.append(item)



    # Post newly migrated access rules
    print('*\n*\nPosting new Access Rules...')
    url =f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/accesspolicies/{acp["id"]}/accessrules?bulk=true'
    print(f'\nPerforming API POST to: {url}...\n')
    try:
        # REST call with SSL verification turned off:
        r = requests.post(url, data=json.dumps(acp_data), headers=headers, verify=False)
        status_code = r.status_code
        resp = r.text
        print(f'Status code is: {status_code}')
        if status_code == 201 or status_code == 202:
            print('FMC Access Rules Post successful...')
        else :
            print (f'Error occurred in POST --> {resp}')
            r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print (f'Error in connection --> {traceback.format_exc()}')
    finally:
        try:
            if r: r.close()
        except:
            None




#
#
#
# Object Group Compare and Update
def obj_group_update(server,headers,api_uuid):
    print ('''
***********************************************************************************************
*                    Update Object Group with entries from txt file                           *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. Object Group Name                                                                       *
*                                                                                             *
*  2. Network Text File                                                                       *
*                                                                                             *
*       Notes:                                                                                *
*          Supports groups with only IPv4 Host and Network objects                            *
*          Text file must contain only host IPs and networks with CIDR notation               *
*                                                                                             *
***********************************************************************************************
''')

    obj_group_name = input('Please Enter Object Group Name: ').strip()
    Test = False
    while not Test:
        # Request Input File
        read_file = input('Please Enter Input File /full/file/path.txt: ').strip()
        if os.path.isfile(read_file):
            # Read csv file
            open_read_file = open(read_file, 'r').read()
            Test = True
        else:
            print('MUST PROVIDE INPUT FILE...')

    file_entries = open_read_file.splitlines()


    # Collect all Network objects
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/networks?expanded=true&offset=0&limit=1000'
    networks = get_items(url,headers)
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/hosts?expanded=true&offset=0&limit=1000'
    hosts = get_items(url,headers)



    url = f'{server}/api/fmc_config/v1/domain/e276abec-e0f2-11e3-8169-6d9ed49b625f/object/networkgroups?expanded=true&offset=0&limit=1000'
    obj_group_entries = []
    obj_groups = get_items(url,headers)
    obj_group = None
    for g in obj_groups:
        if g['name'] == obj_group_name:
            obj_group = g

    if not obj_group:
        print(f'Group name "{obj_group_name}" not found')
        return
    else:
        if 'literals' in obj_group:
            for lit in obj_group['literals']:
                if lit['type'] == 'Network':
                    obj_group_entries.append(IPv4Network(lit['value']).with_prefixlen)
                else:
                    obj_group_entries.append(lit['value'])
        if 'objects' in obj_group:
            # Append networks with CIDR notation
            obj_group_entries += [
                IPv4Network(item['value']).with_prefixlen for item in networks if item['id'] in [i['id'] for i in obj_group['objects']]]
            obj_group_entries += [
                item['value'] for item in hosts if item['id'] in [i['id'] for i in obj_group['objects']]]

        # Compile list of Missing entries on FMC
        diff_missing = [ip for ip in file_entries if ip not in obj_group_entries]
        # Compile list of Extra entries on FMC
        diff_extra = [ip for ip in obj_group_entries if ip not in file_entries]

        new_lits = []
        new_objs = []
        new_entries = []
        # Include literals if they are in the file entries
        if 'literals' in obj_group:
            for lit in obj_group['literals']:
                if lit['type'] == 'Network':
                    if IPv4Network(lit['value']).with_prefixlen in file_entries:
                        new_entries.append(IPv4Network(lit['value']).with_prefixlen)
                        new_lits.append(lit)
                elif lit['value'] in file_entries:
                    new_entries.append(lit['value'])
                    new_lits.append(lit)

        for ip in file_entries:
            if ('/' in ip) and (IPv4Network(ip).with_prefixlen not in new_entries):
                for net in networks:
                    try:
                        if IPv4Network(ip).with_prefixlen == IPv4Network(net['value']).with_prefixlen:
                            new_objs.append({
                                'type': net['type'],
                                'name': net['name'],
                                'id': net['id']
                            })
                            new_entries.append(IPv4Network(ip).with_prefixlen)
                    except:
                        None
            else:
                for host in hosts:
                    if (ip not in new_entries) and (ip == host['value']):
                        new_objs.append({
                            'type': host['type'],
                            'name': host['name'],
                            'id': host['id']
                        })
                        new_entries.append(ip)

        missing_obj = [ip for ip in file_entries if ip not in new_entries]

        create_nets = {'data': [], 'result': []}
        create_hosts = {'data': [], 'result': []}
        for ip in missing_obj:
            if '/' in ip:
                create_nets['data'].append({
                    'name': f'Net-{ip.replace("/","-")}',
                    'type': 'Network',
                    'description': '',
                    'value': ip
                })
            else:
                create_hosts['data'].append({
                    'name': f'Host-{ip}',
                    'type': 'Host',
                    'description': '',
                    'value': ip
                })

        if create_nets['data'] != []:
            # Post Network objects, and store JSON response with object uuids
            try:
                # REST call with SSL verification turned off:
                post_data = create_nets['data']
                url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/networks?bulk=true'
                r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
                status_code = r.status_code
                resp = r.text
                print(f'Status code is: {status_code}')
                if status_code == 201 or status_code == 202:
                    print('Network Objects successfully created...')
                    create_nets['result'] = r.json()['items']
                else :
                    print(f'Error occurred in POST --> {json.dumps(r.json(),indent=4)}')
                    r.raise_for_status()
            except requests.exceptions.HTTPError as err:
                print (f'Error in connection --> {traceback.format_exc()}')
            finally:
                try:
                    if r: r.close()
                except:
                    None

        if create_hosts['data'] != []:
            # Post Host objects, and store JSON response with object uuids
            try:
                # REST call with SSL verification turned off:
                post_data = create_hosts['data']
                url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/hosts?bulk=true'
                r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
                status_code = r.status_code
                resp = r.text
                print(f'Status code is: {status_code}')
                if status_code == 201 or status_code == 202:
                    print('Network Objects successfully created...')
                    create_hosts['result'] = r.json()['items']
                else :
                    print(f'Error occurred in POST --> {json.dumps(r.json(),indent=4)}')
                    r.raise_for_status()
            except requests.exceptions.HTTPError as err:
                print (f'Error in connection --> {traceback.format_exc()}')
            finally:
                try:
                    if r: r.close()
                except:
                    None

        for net in create_nets['result']:
            new_objs.append({
                'type': net['type'],
                'name': net['name'],
                'id': net['id']
            })

        for host in create_hosts['result']:
            new_objs.append({
                'type': host['type'],
                'name': host['name'],
                'id': host['id']
            })

        # Update Object Group data
        del obj_group['links']
        del obj_group['metadata']
        obj_group['objects'] = new_objs
        obj_group['literals'] = new_lits

        # PUT object group
        try:
            # REST call with SSL verification turned off:
            post_data = obj_group
            url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/object/networkgroups/{obj_group["id"]}'
            r = requests.put(url, data=json.dumps(post_data), headers=headers, verify=False)
            status_code = r.status_code
            resp = r.text
            print(f'Status code is: {status_code}')
            if status_code == 200:
                print('Network Object Group successfully updated...')
            else :
                print(f'Error occurred in PUT --> {json.dumps(r.json(),indent=4)}')
                r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print (f'Error in connection --> {traceback.format_exc()}')
        finally:
            try:
                if r: r.close()
            except:
                None

        # Print report
        print(f'Objects added to group:\n{json.dumps(diff_missing,indent=4)}')
        print(f'Objects removed from group:\n{json.dumps(diff_extra,indent=4)}')




#
#
#
# Export ACP and Prefilter Rules
def export_acp_rules(server,headers,api_uuid):
    print ('''
***********************************************************************************************
*                      Export ACP and Prefilter Rules to CSV file                             *
*_____________________________________________________________________________________________*
*                                                                                             *
***********************************************************************************************
''')

    outfile = open(f'acp_rule_export_{datetime.now().strftime("%Y-%m-%d_%H%M")}.csv','w')
    outfile.write('FMC_NAME,ACP_NAME,ACP_TYPE,ACP_ID,R_NAME,R_ID,R_ACTION,R_SRC_ZN,R_DST_ZN,R_SRC_IP,R_DST_IP,R_VLAN,R_USERS,R_APP,R_URL,R_SRC_P,R_DST_P,R_SRC_SGT,R_DST_SGT,R_IPS,R_FILE\n')

    # Get all Access Control Policies
    print('*\n*\nCOLLECTING Access Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/accesspolicies?expanded=true&offset=0&limit=1000'
    acp_list = get_items(url,headers)

    for acp in acp_list:
        url = f'{acp["rules"]["links"]["self"]}?expanded=true&offset=0&limit=1000'
        rules = get_items(url,headers)
        for rule in rules:
            temp_list = parse_rule(fmc_name,rule)
            outfile.write(f'{",".join(temp_list)}\n')

        # GET PREFILTER RULES ALSO
        # Get Prefilter Policy
        if "prefilterPolicySetting" in acp:
            print('*\n*\nCOLLECTING Applied Prefilter Policy...')
            url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/prefilterpolicies/{acp["prefilterPolicySetting"]["id"]}/prefilterrules?expanded=true&offset=0&limit=1000'
            prefilter_rules = get_items(url,headers)
            for rule in prefilter_rules:
                temp_list = parse_rule(fmc_name,rule)
                outfile.write(f'{",".join(temp_list)}\n')

    outfile.close()


#
#
#
# Deploy Pending FTDs
def deploy_ftds(server,headers,api_uuid):
    print ('''
***********************************************************************************************
*                                 Deploy Pending FTDs                                         *
*_____________________________________________________________________________________________*
*                                                                                             *
***********************************************************************************************
''')
    traffic_int = False
    while True:
        choice = input('Would You Like To Deploy FTDs With Traffic Interruption? [y/N]: ').lower()
        if choice in (['yes','ye','y']):
            traffic_int = True
            break
        elif choice in (['no','n','']):
            break
        else:
            print('Invalid Selection...\n')

    # Get all Access Control Policies
    print('*\n*\nCOLLECTING Deployable FTDs...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/deployment/deployabledevices?expanded=true&offset=0&limit=1000'
    ftd_list = get_items(url,headers)
    # include only deployable ftds
    ftd_list = [ftd for ftd in ftd_list if ftd['canBeDeployed'] == True]
    # if traffic interrupt false
    if traffic_int == False:
        ftd_list = [ftd for ftd in ftd_list if ftd['trafficInterruption'] == 'NO']

    if ftd_list == []:
        print('*\n*\nNo Available FTDs to deploy...')
        return
    deploy_req = {
        'type': 'DeploymentRequest',
        'version': ftd_list[0]['version'],
        'forceDeploy': False,
        'ignoreWarning': True,
        'deviceList': [ftd['device']['id'] for ftd in ftd_list]
    }

    print(f'*\n*\nDeploying to below FTDs....\n- ' + '\n- '.join([ftd["name"] for ftd in ftd_list]))
    # Post Deployment Request
    try:
        # REST call with SSL verification turned off:
        post_data = deploy_req
        url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/deployment/deploymentrequests'
        r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
        status_code = r.status_code
        resp = r.text
        print(f'Status code is: {status_code}')
        if status_code == 202:
            print('Deployment request successfully created...')
        else :
            print(f'Error occurred in POST --> {json.dumps(r.json(),indent=4)}')
            r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print (f'Error in connection --> {traceback.format_exc()}')
    finally:
        try:
            if r: r.close()
        except:
            None


#
#
#
# Download Snort.org Rules
def download_snort_rules():
    print ('''
***********************************************************************************************
*                             Download Snort.org rules                                        *
*_____________________________________________________________________________________________*
*                                                                                             *
***********************************************************************************************
''')

    print(f'*\n*\nDownloading Snort Signatures')
    # Post Deployment Request
    try:
        # REST call with SSL verification turned off:
        url = f'https://snort.org/downloads/community/community-rules.tar.gz'
        r = requests.get(url, verify=False)
        status_code = r.status_code
        resp = r.text
        print(f'Status code is: {status_code}')

        if status_code == 200:
            open('community-rules.tar.gz', 'wb').write(r.content)
            file = tarfile.open('community-rules.tar.gz')
            file.extract('community-rules/community.rules')
            file.close()
            file = open('community-rules/community.rules','r').readlines()
            with open('snort.rules','w') as output:
                for line in file:
                    if re.search(r'\; sid\:(\d+)\;', line):
                        sid = re.search(r'\; sid\:(\d+)\;', line).groups()[0]
                        # Increase SID number to > 1000000
                        output.write(re.sub(r'\; sid\:(\d+)\;', rf'; sid:{sid}0000;', line))
                    else:
                        output.write(line)
            print('Snort Rules successfully downloaded...\nFile "snort.rules" modified and ready to import into FMC...')
        else :
            print(f'Error occurred in POST --> {json.dumps(r.json(),indent=4)}')
            r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print (f'Error in connection --> {traceback.format_exc()}')
    finally:
        try:
            if r: r.close()
        except:
            None

#
#
#
# Delete FTDs from FMC
def delete_ftds_from_fmc(server,headers,username,password,api_uuid):
    print ('''
***********************************************************************************************
*                    Delete FTDs from FMC using Name or Model search                          *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. Search for FTD by Name                                                                  *
*                                                                                             *
*  2. Search for FTD by Model                                                                 *
*                                                                                             *
*  3. Verify FTDs to be deleted                                                               *
*                                                                                             *
***********************************************************************************************
''')
    print('Collecting all devices and VPN policies...')
    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/devices/devicerecords?expanded=true&limit=1000'
    devices = get_items(url,headers)

    # Restructure device data
    devices = {
        d['id'].lower(): {
            'id': d['id'].lower(),
            'name': d['name'],
            'model': d['model'],
            'ftds2svpn': []
        } for d in devices
    }

    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/ftds2svpns?expanded=true&limit=1000'
    s2svpns = get_items(url,headers)

    # Restructure vpn data
    s2svpns = {
        s['id'].lower(): {
            'id': s['id'].lower(),
            's2s_endpts': [e['device']['id'].lower(
                        ) for e in get_items(f'{s["endpoints"]["links"]["self"]}?expanded=true',
                                                headers) if e['extranet'] == False]
        } for s in s2svpns
    }

    # Add the VPN policy to the device
    for id,s in s2svpns.items():
        for e in s['s2s_endpts']:
            if e in devices:
                devices[e]['ftds2svpn'].append(id)

    # Run search in While loop to be able to re-search
    del_devs = None
    while not del_devs:
        # Printing \n to give space between API calls and input request
        print('\n')
        del_devs = {}

        search_terms = []
        term = ''
        while term != 'DONE':
            term = input('Please enter a FTD name string to search. Enter "DONE" to finish: ').strip()
            if (term != 'DONE') and (term != ''):
                search_terms.append(term)
        for id,d in devices.items():
            # Match on Name contains
            if any(i.lower() in d['name'].lower() for i in search_terms) and (id not in del_devs):
                del_devs[id] = d

        search_terms = []
        term = ''
        while term != 'DONE':
            term = input('Please enter a FTD model string to search (IE. "9000", "VMWare"). Enter "DONE" to finish: ').strip()
            if (term != 'DONE') and (term != ''):
                search_terms.append(term)
        for id,d in devices.items():
            # Match on Model type
            if any(i.lower() in d['model'].lower() for i in search_terms) and (id not in del_devs):
                del_devs[id] = d

        if len(del_devs) == 0:
            print('\nNo search results, re-enter search strings...')
            del_devs = None
        else:
            print (f'''
***********************************************************************************************
*                                                                                             *
*                                 FTD Search Results                                          *
*_____________________________________________________________________________________________*
*           NAME          ,                 UUID                ,           Model             *
*_____________________________________________________________________________________________*''')

            print('* '+'\n* '.join([f'{d["name"]}, {d["id"]}, {d["model"]}' for id,d in del_devs.items()]))
            print('''***********************************************************************************************\n''')

            delete = input('Do you wish to delete the above devices? [y/N]: ').lower()
            if delete in ['y','ye','yes']:
                break
            elif delete in ['n','no','']:
                search = input('Do you wish to re-enter search strings? [y/N]').lower()
                if search in ['y','ye','yes']:
                    del_devs = None
                else:
                    del_devs = {}
                    break
            else:
                print('Invalid entry, re-enter search strings...')
                del_devs = None
    del_length = len(del_devs)
    count = 0

    if del_length > 0:
        for id,d in del_devs.items():
            if 'ftds2svpn' != []:
                vlength = len(d['ftds2svpn'])
                vcount = 0
                for v in d['ftds2svpn']:
                    vcount += 1
                    url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/policy/ftds2svpns/{v}'
                    try:
                        r = requests.delete(url, headers=headers, verify=False)
                        status_code = r.status_code
                        if status_code == 429:
                            print("Rate limit reached. Waiting 60 seconds before continuing...")
                            time.sleep(61)
                            r = requests.delete(url, headers=headers, verify=False)
                            status_code = r.status_code
                            if status_code == 200:
                                print(f'\n{d["name"]} s2svpn policy has been removed. {vcount} of {vlength}. Status code: {status_code}')
                            elif status_code == 401:
                                print("Token expired, renewing...")
                                results = access_token(server,headers,username,password)
                                headers['X-auth-access-token']=results[0]

                                try:
                                    r = requests.delete(url, headers=headers, verify=False)
                                    status_code = r.status_code
                                    if status_code == 429:
                                        print("Rate limit reached. Waiting 60 seconds before continuing...")
                                        time.sleep(61)
                                        r = requests.delete(url, headers=headers, verify=False)
                                        status_code = r.status_code
                                        if status_code == 200:
                                            print(f'\n{d["name"]} s2svpn policy has been removed. {vcount} of {vlength}. Status code: {status_code}')
                                        else:
                                            print(f'\n{d["name"]} s2svpn policy failed to be removed! Status code: {status_code}\n')
                                    elif status_code == 200:
                                        print(f'\n{d["name"]} s2svpn policy has been removed. {vcount} of {vlength}. Status code: {status_code}')
                                    else:
                                        print(f'\n{d["name"]} s2svpn policy failed to be removed! {vcount} of {vlength}. Status code: {status_code}')
                                except requests.exceptions.HTTPError as err:
                                    print (f'Error in connection --> {traceback.format_exc()}')

                            else:
                                print(f'\n{d["name"]} s2svpn policy failed to be removed! Status code: {status_code}\n')
                        elif status_code == 200:
                            print(f'\n{d["name"]} s2svpn policy has been removed. {vcount} of {vlength}. Status code: {status_code}')
                        elif status_code == 401:
                            print("Token expired, renewing...")
                            results = access_token(server,headers,username,password)
                            headers['X-auth-access-token']=results[0]

                            try:
                                r = requests.delete(url, headers=headers, verify=False)
                                status_code = r.status_code
                                if status_code == 429:
                                    print("Rate limit reached. Waiting 60 seconds before continuing...")
                                    time.sleep(61)
                                    r = requests.delete(url, headers=headers, verify=False)
                                    status_code = r.status_code
                                    if status_code == 200:
                                        print(f'\n{d["name"]} s2svpn policy has been removed. {vcount} of {vlength}. Status code: {status_code}')
                                    else:
                                        print(f'\n{d["name"]} s2svpn policy failed to be removed! Status code: {status_code}\n')
                                elif status_code == 200:
                                    print(f'\n{d["name"]} s2svpn policy has been removed. {vcount} of {vlength}. Status code: {status_code}')
                                else:
                                    print(f'\n{d["name"]} s2svpn policy failed to be removed! {vcount} of {vlength}. Status code: {status_code}')
                            except requests.exceptions.HTTPError as err:
                                print (f'Error in connection --> {traceback.format_exc()}')

                        else:
                            print(f'\n{d["name"]} s2svpn policy failed to be removed! {vcount} of {vlength}. Status code: {status_code}')
                    except requests.exceptions.HTTPError as err:
                        print (f'Error in connection --> {traceback.format_exc()}')

            count += 1
            url = f'{server}/api/fmc_config/v1/domain/{api_uuid}/devices/devicerecords/{id}'
            try:
                r = requests.delete(url, headers=headers, verify=False)
                status_code = r.status_code
                if status_code == 429:
                    print("Rate limit reached. Waiting 60 seconds before continuing...")
                    time.sleep(61)
                    r = requests.delete(url, headers=headers, verify=False)
                    status_code = r.status_code
                    if status_code == 200:
                        print(f'\n{d["name"]} has been removed. {count} of {del_length}. Status code: {status_code}')
                    elif status_code == 401:
                        print("Token expired, renewing...")
                        results = access_token(server,headers,username,password)
                        headers['X-auth-access-token']=results[0]

                        try:
                            r = requests.delete(url, headers=headers, verify=False)
                            status_code = r.status_code
                            if status_code == 429:
                                print("Rate limit reached. Waiting 60 seconds before continuing...")
                                time.sleep(61)
                                r = requests.delete(url, headers=headers, verify=False)
                                status_code = r.status_code
                                if status_code == 200:
                                    print(f'\n{d["name"]} has been removed. {count} of {del_length}. Status code: {status_code}')
                                else:
                                    print(f'\n{d["name"]} failed to be removed! Status code: {status_code}\n')
                            elif status_code == 200:
                                print(f'\n{d["name"]} has been removed. {count} of {del_length}. Status code: {status_code}')
                            else:
                                print(f'\n{d["name"]} failed to be removed! {count} of {del_length}. Status code: {status_code}')

                        except requests.exceptions.HTTPError as err:
                            print (f'Error in connection --> {traceback.format_exc()}')

                    else:
                        print(f'\n{d["name"]} failed to be removed! Status code: {status_code}\n')
                elif status_code == 200:
                    print(f'\n{d["name"]} has been removed. {count} of {del_length}. Status code: {status_code}')
                elif status_code == 401:
                    print("Token expired, renewing...")
                    results = access_token(server,headers,username,password)
                    headers['X-auth-access-token']=results[0]

                    try:
                        r = requests.delete(url, headers=headers, verify=False)
                        status_code = r.status_code
                        if status_code == 429:
                            print("Rate limit reached. Waiting 60 seconds before continuing...")
                            time.sleep(61)
                            r = requests.delete(url, headers=headers, verify=False)
                            status_code = r.status_code
                            if status_code == 200:
                                print(f'\n{d["name"]} has been removed. {count} of {del_length}. Status code: {status_code}')
                            else:
                                print(f'\n{d["name"]} failed to be removed! Status code: {status_code}\n')
                        elif status_code == 200:
                            print(f'\n{d["name"]} has been removed. {count} of {del_length}. Status code: {status_code}')
                        else:
                            print(f'\n{d["name"]} failed to be removed! {count} of {del_length}. Status code: {status_code}')

                    except requests.exceptions.HTTPError as err:
                        print (f'Error in connection --> {traceback.format_exc()}')
                else:
                    print(f'\n{d["name"]} failed to be removed! {count} of {del_length}. Status code: {status_code}')

            except requests.exceptions.HTTPError as err:
                print (f'Error in connection --> {traceback.format_exc()}')
    else:
        print("\nNothing to delete. Closing...")


#
#
#
# Edit manager config for FTDs
def ftd_manager_edit():
    print ('''
***********************************************************************************************
*                         Edit manager config for FTDs in bulk                                *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. Primary FMC UUID to edit (obtain from FMC CLI "show version")                           *
*                                                                                             *
*  2. New IP address for Primary FMC                                                          *
*                                                                                             *
*  3. Secondary FMC UUID to edit (obtain from FMC CLI "show version")                         *
*                                                                                             *
*  4. New IP address for Secondary FMC                                                        *
*                                                                                             *
*  5. CSV File for FTD SSH details; format: "ftd_hostname, ssh_port, ftd_user, ftd_pass"      *
*       # CSV FORMAT:                                                                         *
*           No Header Row & comma delimited                                                   *
*           Column0 = ftd_hostname                                                            *
*           Column1 = ssh_port                                                                *
*           Column2 = ftd_user                                                                *
*           Column3 = ftd_pass                                                                *
*                                                                                             *
*  6. Comma separated list of FTD hostnames or IPs (IE. "1.1.1.1, 2.2.2.2, 3.3.3.3")          *
*                                                                                             *
*  7. FTD SSH port, if not default                                                            *
*                                                                                             *
*  8. Username and Password for FTD SSH                                                       *
*                                                                                             *
***********************************************************************************************
''')

    while True:
        edit_pri = False
        choice = ''
        while True:
            choice = input('Would you like to edit Primary FMC IP for FTDs? [y/N]: ').lower()
            if choice in (['yes','ye','y']):
                pri_fmc_uuid = input('Please enter Primary FMC UUID: ').strip()
                if pri_fmc_uuid != '':
                    edit_pri = True
                    pri_fmc_ip = input('Please enter new Primary FMC Hostname/IP: ').strip()
                    break
                else:
                    print('Invalid entry...\n')
            elif choice in (['no','n','']):
                break
            else:
                print('Invalid Selection...\n')

        edit_sec = False
        choice = ''
        while True:
            choice = input('Would you like to edit Secondary FMC IP for FTDs? [y/N]: ').lower()
            if choice in (['yes','ye','y']):
                sec_fmc_uuid = input('Please enter Secondary FMC UUID: ').strip()
                if sec_fmc_uuid != '':
                    edit_sec = True
                    sec_fmc_ip = input('Please enter new Secondary FMC Hostname/IP: ').strip()
                    break
                else:
                    print('Invalid entry...\n')
            elif choice in (['no','n','']):
                break
            else:
                print('Invalid Selection...\n')
        # Break While loop if at least one is selected
        if (not edit_pri) and (not edit_sec):
            print('Invalid Selection...\n')
        else:
            break


    choice = ''
    ftd_file = False
    while True:
        ftds = []
        choice = input('Would you like to use CSV file for FTD details? [y/N]: ').lower()
        if choice in (['yes','ye','y']):
            read_file = input('Please enter file path to csv file: ').strip()
            if os.path.isfile(read_file):
                # Read csv file
                open_read_file = open(read_file, 'r', encoding='utf-8-sig').read()
                try:
                    for i in open_read_file.splitlines():
                        if i == '':
                            pass
                        else:
                            i = i.split(',')
                            ftds.append([i[0].strip(), i[1].strip(), i[2].strip(), i[3].strip()])
                    break
                except:
                    print(f'Error reading input file, please check format...\n{traceback.format_exc()}')
            else:
                print('Invalid input file path...\n')
        elif choice in (['no','n','']):
            # Request Details
            ftd_ips = input('Please enter comma separated list of FTD hostnames/IPs: ').split(',')
            ssh_port = input('Please enter SSH port, if not default [22]: ').strip()
            ssh_port = '22' if ssh_port == '' else ssh_port
            ftd_user = input('Please enter FTD username: ').strip()
            ftd_pass = define_password()
            for i in ftd_ips:
                ftds.append([i.strip(), ssh_port, ftd_user, ftd_pass])
            break
        else:
            print('Invalid Selection...\n')



    for ftd in ftds:
        ftd_ip = ftd[0]
        ftd_port = ftd[1]
        ftd_user = ftd[2]
        ftd_pass = ftd[3]
        try:
            # Connect to FTD, and initiate registration
            print(f'Connecting to FTD {ftd_ip}:{ftd_port}...\n')
            connection = netmiko.ConnectHandler(ip=ftd_ip, device_type='autodetect', username=ftd_user,
                                                password=ftd_pass, port=ftd_port, global_delay_factor=6)
            # Get FTD version
            output = connection.send_command('show version')
            for line in output.splitlines():
                if line.startswith('Model'):
                    version = line.split('Version')[1].split()[0]
                    version = float(f'{version.split(".")[0]}.{version.split(".")[1]}')

            try:
                if version >= 7.2:
                    if edit_pri:
                        print('Editing Primary FMC IP...')
                        output = connection.send_command(f'configure manager edit {pri_fmc_uuid} hostname {pri_fmc_ip} ')
                        if 'Error' in output:
                            raise netmiko.ssh_exception.ConfigInvalidException(output)
                        print(output)
                    if edit_sec:
                        print('Editing Secondary FMC IP...')
                        output = connection.send_command(f'configure manager edit {sec_fmc_uuid} hostname {sec_fmc_ip} ')
                        if 'Error' in output:
                            raise netmiko.ssh_exception.ConfigInvalidException(output)
                        print(output)
                else:
                    if edit_pri:
                        print('Editing Primary FMC IP...')
                        output = connection.send_command(f'configure manager edit {pri_fmc_uuid} {pri_fmc_ip} ')
                        if 'Error' in output:
                            raise netmiko.ssh_exception.ConfigInvalidException(output)
                        print(output)
                    if edit_sec:
                        print('Editing Secondary FMC IP...')
                        output = connection.send_command(f'configure manager edit {sec_fmc_uuid} {sec_fmc_ip} ')
                        if 'Error' in output:
                            raise netmiko.ssh_exception.ConfigInvalidException(output)
                        print(output)
                print(f'FTD managers edited successfully for {ftd_ip}...')
                output = connection.send_command('show managers')
                print(output)
                connection.disconnect()
            except:
                print (f'Error in command execution for {ftd_ip} --> {traceback.format_exc()}')
                output = connection.send_command('show managers')
                print(f'show manager output for {ftd_ip}...\n{output}')
                connection.disconnect()
        except:
            print (f'Error in SSH connection for {ftd_ip} --> {traceback.format_exc()}')




#
#
#
# Run Script if main
if __name__ == "__main__":
    print ('''
***********************************************************************************************
*                                                                                             *
*                   Cisco FMC 6.7+ API Tools (Written for Python 3.6+)                        *
*                                                                                             *
***********************************************************************************************''')
    # Init Variables
    server,headers,username,password = '','','',''
    loop = ''

    # Run script until user cancels
    while True:
        print ('''
***********************************************************************************************
*                                                                                             *
* TOOLS AVAILABLE:                                                                            *
*                                                                                             *
*  1. Basic URL GET                                                                           *
*                                                                                             *
*  2. Create Network-Objects in bulk                                                          *
*                                                                                             *
*  3. Create Network-Objects in bulk and add to New Object-Group                              *
*                                                                                             *
*  4. Update IPS and/or File Policy for Access Rules                                          *
*                                                                                             *
*  5. Get Inventory List from FMC                                                             *
*                                                                                             *
*  6. Register FTD to FMC                                                                     *
*                                                                                             *
*  7. Deploy Pending FTDs                                                                     *
*                                                                                             *
*  8. Migrate Prefilter rules to Access Rules                                                 *
*                                                                                             *
*  9. Update Object Group with entries from txt file                                          *
*                                                                                             *
*  10. Export ACP and Prefilter Rules to CSV file                                             *
*                                                                                             *
*  11. Download Snort.org Rules                                                               *
*                                                                                             *
*  12. Delete FTDs from FMC using Name or Model search                                        *
*                                                                                             *
*  13. Edit manager config for FTDs in bulk                                                   *
*                                                                                             *
***********************************************************************************************
''')
        if loop == '':
            pass
        else:
            # Ask to end the loop
            loop = input('Would You Like To use another tool? [y/N]').lower()
            if loop not in ['yes','ye','y','1','2','3','4','5','6','7','8','9','10','11','12','13']:
                break

        # Select Script
        if loop in ['1','2','3','4','5','6','7','8','9','10','11','12','13']:
            script = loop
        else:
            script = input('Please Select Tool: ')

        # Run selection
        if script == '1':
            server,headers,username,password = get_fmc_details(server,headers,username,password)
            print('Generating Access Token')
            # Generate Access Token and pull domains from auth headers
            while True:
                results = access_token(server,headers,username,password)
                if not results:
                    print('Authentication failure, please re-enter FMC details...')
                    server,headers,username,password = get_fmc_details(server,headers,username,password)
                else:
                    break
            headers['X-auth-access-token']=results[0]
            domains = results[1]
            if len(domains) > 1:
                api_uuid = select('Domain',domains)['uuid']
            else:
                api_uuid = domains[0]['uuid']

            blank_get(server,headers)

        elif script == '2':
            server,headers,username,password = get_fmc_details(server,headers,username,password)
            print('Generating Access Token')
            # Generate Access Token and pull domains from auth headers
            while True:
                results = access_token(server,headers,username,password)
                if not results:
                    print('Authentication failure, please re-enter FMC details...')
                    server,headers,username,password = get_fmc_details(server,headers,username,password)
                else:
                    break
            headers['X-auth-access-token']=results[0]
            domains = results[1]
            if len(domains) > 1:
                api_uuid = select('Domain',domains)['uuid']
            else:
                api_uuid = domains[0]['uuid']

            post_network_object(server,headers,api_uuid)

        elif script == '3':
            server,headers,username,password = get_fmc_details(server,headers,username,password)
            print('Generating Access Token')
            # Generate Access Token and pull domains from auth headers
            while True:
                results = access_token(server,headers,username,password)
                if not results:
                    print('Authentication failure, please re-enter FMC details...')
                    server,headers,username,password = get_fmc_details(server,headers,username,password)
                else:
                    break
            headers['X-auth-access-token']=results[0]
            domains = results[1]
            if len(domains) > 1:
                api_uuid = select('Domain',domains)['uuid']
            else:
                api_uuid = domains[0]['uuid']

            post_network_object_group(server,headers,api_uuid)

        elif script == '4':
            server,headers,username,password = get_fmc_details(server,headers,username,password)
            print('Generating Access Token')
            # Generate Access Token and pull domains from auth headers
            while True:
                results = access_token(server,headers,username,password)
                if not results:
                    print('Authentication failure, please re-enter FMC details...')
                    server,headers,username,password = get_fmc_details(server,headers,username,password)
                else:
                    break
            headers['X-auth-access-token']=results[0]
            domains = results[1]
            if len(domains) > 1:
                api_uuid = select('Domain',domains)['uuid']
            else:
                api_uuid = domains[0]['uuid']

            put_intrusion_file(server,headers,api_uuid)

        elif script == '5':
            server,headers,username,password = get_fmc_details(server,headers,username,password)
            print('Generating Access Token')
            # Generate Access Token and pull domains from auth headers
            while True:
                results = access_token(server,headers,username,password)
                if not results:
                    print('Authentication failure, please re-enter FMC details...')
                    server,headers,username,password = get_fmc_details(server,headers,username,password)
                else:
                    break
            headers['X-auth-access-token']=results[0]
            domains = results[1]
            if len(domains) > 1:
                api_uuid = select('Domain',domains)['uuid']
            else:
                api_uuid = domains[0]['uuid']

            get_inventory(server,headers,api_uuid)

        elif script == '6':
            server,headers,username,password = get_fmc_details(server,headers,username,password)
            print('Generating Access Token')
            # Generate Access Token and pull domains from auth headers
            while True:
                results = access_token(server,headers,username,password)
                if not results:
                    print('Authentication failure, please re-enter FMC details...')
                    server,headers,username,password = get_fmc_details(server,headers,username,password)
                else:
                    break
            headers['X-auth-access-token']=results[0]
            domains = results[1]
            if len(domains) > 1:
                api_uuid = select('Domain',domains)['uuid']
            else:
                api_uuid = domains[0]['uuid']

            register_ftd(server,headers,api_uuid)

        elif script == '7':
            server,headers,username,password = get_fmc_details(server,headers,username,password)
            print('Generating Access Token')
            # Generate Access Token and pull domains from auth headers
            while True:
                results = access_token(server,headers,username,password)
                if not results:
                    print('Authentication failure, please re-enter FMC details...')
                    server,headers,username,password = get_fmc_details(server,headers,username,password)
                else:
                    break
            headers['X-auth-access-token']=results[0]
            domains = results[1]
            if len(domains) > 1:
                api_uuid = select('Domain',domains)['uuid']
            else:
                api_uuid = domains[0]['uuid']

            deploy_ftds(server,headers,api_uuid)

        elif script == '8':
            server,headers,username,password = get_fmc_details(server,headers,username,password)
            print('Generating Access Token')
            # Generate Access Token and pull domains from auth headers
            while True:
                results = access_token(server,headers,username,password)
                if not results:
                    print('Authentication failure, please re-enter FMC details...')
                    server,headers,username,password = get_fmc_details(server,headers,username,password)
                else:
                    break
            headers['X-auth-access-token']=results[0]
            domains = results[1]
            if len(domains) > 1:
                api_uuid = select('Domain',domains)['uuid']
            else:
                api_uuid = domains[0]['uuid']

            prefilter_to_acp(server,headers,api_uuid)

        elif script == '9':
            server,headers,username,password = get_fmc_details(server,headers,username,password)
            print('Generating Access Token')
            # Generate Access Token and pull domains from auth headers
            while True:
                results = access_token(server,headers,username,password)
                if not results:
                    print('Authentication failure, please re-enter FMC details...')
                    server,headers,username,password = get_fmc_details(server,headers,username,password)
                else:
                    break
            headers['X-auth-access-token']=results[0]
            domains = results[1]
            if len(domains) > 1:
                api_uuid = select('Domain',domains)['uuid']
            else:
                api_uuid = domains[0]['uuid']

            obj_group_update(server,headers,api_uuid)

        elif script == '10':
            server,headers,username,password = get_fmc_details(server,headers,username,password)
            print('Generating Access Token')
            # Generate Access Token and pull domains from auth headers
            while True:
                results = access_token(server,headers,username,password)
                if not results:
                    print('Authentication failure, please re-enter FMC details...')
                    server,headers,username,password = get_fmc_details(server,headers,username,password)
                else:
                    break
            headers['X-auth-access-token']=results[0]
            domains = results[1]
            if len(domains) > 1:
                api_uuid = select('Domain',domains)['uuid']
            else:
                api_uuid = domains[0]['uuid']

            export_acp_rules(server,headers,api_uuid)

        elif script == '11':
            download_snort_rules()

        elif script == '12':
            server,headers,username,password = get_fmc_details(server,headers,username,password)
            print('Generating Access Token')
            # Generate Access Token and pull domains from auth headers
            while True:
                results = access_token(server,headers,username,password)
                if not results:
                    print('Authentication failure, please re-enter FMC details...')
                    server,headers,username,password = get_fmc_details(server,headers,username,password)
                else:
                    break
            headers['X-auth-access-token']=results[0]
            domains = results[1]
            if len(domains) > 1:
                api_uuid = select('Domain',domains)['uuid']
            else:
                api_uuid = domains[0]['uuid']

            delete_ftds_from_fmc(server,headers,username,password,api_uuid)

        elif script == '13':
            ftd_manager_edit()

        else:
            print('Invalid selection... ')

        loop = ' '
