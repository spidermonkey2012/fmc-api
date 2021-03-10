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
        getpass,\
        requests,\
        warnings,\
        traceback
from datetime import datetime

# Import custom modules from file
from fmc_api_module import \
        define_password,\
        AccessToken,\
        GetDeviceDetails,\
        GetNetObjectUUID, \
        Select,\
        GetItems

# Disable SSL warning
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

#
#
#
# Define Blank URL Get Script as Function
def BlankGet(server,headers,username,password):
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

    print('Generating Access Token')
    # Generate Access Token and pull domains from auth headers
    results=AccessToken(server,headers,username,password)
    headers['X-auth-access-token']=results[0]

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
                with open(filename, 'a') as OutFile:
                    OutFile.write(json.dumps(resp,indent=4))
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
def PostNetworkObject(server,headers,username,password):
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

    print('Generating Access Token')
    # Generate Access Token and pull domains from auth headers
    results=AccessToken(server,headers,username,password)
    headers['X-auth-access-token']=results[0]
    domains = results[1]

    Test = False
    if len(domains) > 1:
        while not Test:
            print('Multiple FMC domains found:')
            for domain in domains:
                print(f'    {domain["name"]}')
            choice = input('\nPlease select an FMC domain: ').strip()
            for domain in domains:
                if choice in domain['name']:
                    API_UUID = domain['uuid']
                    Test=True
            if not Test:
                print('Invalid Selection...\n')
    else:
        API_UUID = domains[0]['uuid']

    objTypes= [
        {
            'name':'Host',
            'url':f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/hosts?bulk=true'
        },
        {
            'name':'Range',
            'url':f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/ranges?bulk=true'
        },
        {
            'name':'Network',
            'url':f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networks?bulk=true'
        },
        {
            'name':'FQDN',
            'url':f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/fqdns?bulk=true'
        }
    ]
    # Select type of Object to post
    objType = Select('Object Type',objTypes)

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
        objName = row[0]
        address = row[1]
        post_data.append({
            'name': objName,
            'type': objType['name'],
            'description': '',
            'value': address
        })

    try:
        # REST call with SSL verification turned off:
        url = objType['url']
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
def PostNetworkObjectGroup(server,headers,username,password):
    print ('''
***********************************************************************************************
*                Create Network Objects in bulk and add to new Object-Group                   *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. TXT Data Input file (ASA "show run object-group" output)                                *
*                                                                                             *
***********************************************************************************************
''')

    print('Generating Access Token')
    # Generate Access Token and pull domains from auth headers
    results=AccessToken(server,headers,username,password)
    headers['X-auth-access-token']=results[0]
    domains = results[1]

    Test = False
    if len(domains) > 1:
        while not Test:
            print('Multiple FMC domains found:')
            for domain in domains:
                print(f'    {domain["name"]}')
            choice = input('\nPlease select an FMC domain: ').strip()
            for domain in domains:
                if choice in domain['name']:
                    API_UUID = domain['uuid']
                    Test=True
            if not Test:
                print('Invalid Selection...\n')
    else:
        API_UUID = domains[0]['uuid']

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

    # Random Generated JSON Output File
    filename = ''.join(i for i in [chr(random.randint(97,122)) for i in range(6)])
    filename += '.json'
    print(f'*\n*\nRANDOM LOG FILE CREATED... {filename}\n')
    outfile = open(filename,'w')

    # Define Counters
    NetOb_Counter = 0
    ObGr_Counter = 0
    ObGr = False
    # Create For Loop To Process Each Item In CSV
    for item in open_read_file.splitlines():
        # Find Object-Group Name
        if item.startswith('object-group network '):
            if ObGr:
                # Post existing Object-Group JSON, and reset counters
                NetOb_Counter = 0
                ObGr_Counter = 0
                url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networkgroups'
                # ReDefine Original Object-Group Name
                ObGr_NAME = ObGr_NAME_Orig
                ObGr_json_Size = json.dumps(ObGr_json)
                # Perform POST for Obect-Group
                try:
                    # REST call with SSL verification turned off:
                    r = requests.post(url, data=json.dumps(ObGr_json), headers=headers, verify=False)
                    status_code = r.status_code
                    resp = r.text
                    json_resp = json.loads(resp)
                    print(f'Status code is: {status_code}')
                    if status_code == 201 or status_code == 202:
                        print(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... View Output File For Full Change Log...\n{"*"*95}')
                        # Append Object-Group JSON with new entry for Network-Object
                        outfile.write(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... \n{json.dumps(ObGr_json,indent=4)}\n{"*"*95}')
                    else :
                        json_resp = json.loads(resp)
                        print(f'Error occurred in POST --> {resp}{ObjectName}')
                        outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')
                        r.raise_for_status()
                except requests.exceptions.HTTPError as err:
                    print (f'Error in connection --> {err}')
                    outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')
                finally:
                    try:
                        if r: r.close()
                    except:
                        None

            # Create New Object-Group JSON
            ObGr = True
            ObGr_NAME_Orig = item.strip('object-group network ')
            ObGr_NAME = ObGr_NAME_Orig
            # Create Base JSON data for Object-Group
            ObGr_json = {
            'name': ObGr_NAME,
            'objects': [],
            'type': 'NetworkGroup'
            }







           # # Create Network-Object JSON Data RANGE
           # post_data = {
           # 'name': ObjectName,
           # 'type': 'Range',
           # 'description': '',
           # 'value': '1.1.1.1-1.1.1.2'
           # }





        # Process Host Entries
        elif item.startswith(' network-object host '):
            Address = item.strip(' network-object host ')
            # Define Network-Object Name
            ObjectName = f'host-{Address}'
            # Create Network-Object JSON Data
            post_data = {
            'name': ObjectName,
            'type': 'Host',
            'description': '',
            'value': Address
            }
            # Define Network-Object Counter
            NetOb_Counter += 1
            if NetOb_Counter in list(range(50,2000,50)):
                ## Generate Access Token
                print ('Attempting to Renew Token...')
                results=AccessToken(server,headers,username,password)
                headers['X-auth-access-token']=results[0]
            # Perform POST for each Network-Object
            try:
                # Format URL for Network-Object POST
                url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/hosts'
                # REST call with SSL verification turned off:
                r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
                status_code = r.status_code
                resp = r.text
                print(f'[{NetOb_Counter}] Network-Object Processing... View Output File For Full Change Log...')
                print(f'Status code is: {status_code}')
                json_resp = json.loads(resp)
                if status_code == 201 or status_code == 202:
                    # Pull Object UUID from json_resp data
                    ObjectID = json_resp ['id']
                    # Append Object-Group JSON with new entry for Network-Object
                    ObGr_json['objects'].append({'type': 'Host','id': ObjectID})
                    outfile.write(f'{json.dumps(json_resp,indent=4)}\n')
                    # Set JSON Data for checking DUMP size
                    ObGr_json_Size = json.dumps(ObGr_json)
                    # Validate size of JSON Data
                    if sys.getsizeof(ObGr_json_Size) >= 20000:
                        print(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... View Output File For Full Change Log...\n{"*"*95}')
                        outfile.write(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... \n{json.dumps(ObGr_json,indent=4)}\n{"*"*95}')
                        # Increase Object-Group Counter
                        ObGr_Counter += 1
                        # Add Counter To Group Name
                        ObGr_Count = f'{ObGr_NAME}-{ObGr_Counter}'
                        ObGr_json['name'] = ObGr_Count
                        # Format URL for Object-Group POST
                        url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networkgroups'
                        # Perform POST for Obect-Group
                        try:
                            # REST call with SSL verification turned off:
                            r = requests.post(url, data=json.dumps(ObGr_json), headers=headers, verify=False)
                            status_code = r.status_code
                            resp = r.text
                            json_resp = json.loads(resp)
                            print(f'Status code is: {status_code}')
                            if status_code == 201 or status_code == 202:
                                print('Object-Group Processing... View Output File For Full Change Log...')
                                # Append Object-Group JSON with new entry for Network-Object
                                outfile.write(f'Object-Group Created...\n{ObGr_Count}\n{json.dumps(json_resp,indent=4)}\n')
                                # Reset Object-Group Data
                                ObGr_Data = None
                                ObGr_Data = {
                                'name': ObGr_NAME,
                                'objects': [],
                                'type': 'NetworkGroup'
                                }
                                # Read Object-Group JSON data for Editing
                                ObGr_json = json.loads(json.dumps(ObGr_Data))
                            else :
                                json_resp = json.loads(resp)
                                r.raise_for_status()
                                print (f'Error occurred in POST --> {resp}{ObjectName}')
                                outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')
                        except requests.exceptions.HTTPError as err:
                            print (f'Error in connection --> {err}')
                            outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')

                        finally:
                            try:
                                if r: r.close()
                            except:
                                None
                else :
                    r.raise_for_status()
                    outfile.write(f'Error occurred in POST --> {json.dumps(json_resp,indent=4)}\n{ObjectName}\n')
                    print(f'Error occurred in POST --> {json.dumps(json_resp,indent=4)}\n{ObjectName}\n')
            except requests.exceptions.HTTPError as err:
                json_resp = json.loads(resp)
                print(f'Error in connection -->{err}')
                outfile.write(f'Error in connection --> {err}\n{json.dumps(json_resp,indent=4)}\n{ObjectName}\n')
                for item in json_resp['error']['messages']:
                    # Error Handling for Network-Object that already exists
                    if 'already exists' in item['description']:
                        print(f'Network Object Already Exists... Attempting to Get UUID for {ObjectName}')

                        # Perform GET to grab UUID for Network Object that already exists
                        ObjectID = GetNetObjectUUID(server,API_UUID,headers,ObjectName,outfile)

                        # Append Object-Group JSON with new entry for Network-Object
                        ObGr_json['objects'].append({'type': 'Network','id': ObjectID})
                        outfile.write(json.dumps(json_resp,sort_keys=True,indent=4, separators=(',', ': '))+'\n')

                        # Set JSON Data for checking DUMP size
                        ObGr_json_Size = json.dumps(ObGr_json)

                        # Validate size of JSON Data
                        if sys.getsizeof(ObGr_json_Size) >= 20000:
                            print(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... View Output File For Full Change Log...\n{"*"*95}')
                            outfile.write(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... \n{json.dumps(ObGr_json,indent=4)}\n{"*"*95}')
                            # Increase Object-Group Counter
                            ObGr_Counter += 1

                            # Run Object Object-Group Creation
                            #ObGr_Data = LargeObGrPost()

                            # Add Counter To Group Name
                            ObGr_Count = f'{ObGr_NAME}-{ObGr_Counter}'
                            ObGr_json['name'] = ObGr_Count
                            # Format URL for Object-Group POST
                            url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networkgroups'
                            # Perform POST for Obect-Group
                            try:
                                # REST call with SSL verification turned off:
                                r = requests.post(url, data=json.dumps(ObGr_json), headers=headers, verify=False)
                                status_code = r.status_code
                                resp = r.text
                                json_resp = json.loads(resp)
                                print(f'Status code is: {status_code}')
                                if status_code == 201 or status_code == 202:
                                    print('Object-Group Processing... View Output File For Full Change Log...')
                                    # Append Object-Group JSON with new entry for Network-Object
                                    outfile.write(f'Object-Group Created...\n{ObGr_Count}\n{json.dumps(json_resp,indent=4)}\n')
                                    # Reset Object-Group Data
                                    ObGr_Data = None
                                    ObGr_Data = {
                                    'name': ObGr_NAME,
                                    'objects': [],
                                    'type': 'NetworkGroup'
                                    }
                                    # Read Object-Group JSON data for Editing
                                    ObGr_json = json.loads(json.dumps(ObGr_Data))
                                else :
                                    json_resp = json.loads(resp)
                                    r.raise_for_status()
                                    print (f'Error occurred in POST --> {resp}{ObjectName}')
                                    outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')
                            except requests.exceptions.HTTPError as err:
                                print (f'Error in connection --> {err}')
                                outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')

                            finally:
                                try:
                                    if r: r.close()
                                except:
                                    None

                    # Error Handling for Access Token Timeout
                    elif 'Access token invalid' in item['description']:
                        print ('Access token invalid... Attempting to Renew Token...')
                        results=AccessToken(server,headers,username,password)
                        headers['X-auth-access-token']=results[0]

                        # Perform POST for each Network-Object
                        try:
                            # Format URL for Network-Object POST
                            url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/hostss'
                            # REST call with SSL verification turned off:
                            r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
                            # REST call with SSL verification turned on:
                            # r = requests.post(url, data=json.dumps(post_data), headers=headers, verify='/path/to/ssl_certificate')
                            status_code = r.status_code
                            resp = r.text
                            print('['+str(NetOb_Counter)+'] Network-Object Processing... View Output File For Full Change Log...')
                            print(f'Status code is: {status_code}')
                            json_resp = json.loads(resp)
                            if status_code == 201 or status_code == 202:
                                # Pull Object UUID from json_resp data
                                ObjectID = json_resp ['id']
                                # Append Object-Group JSON with new entry for Network-Object
                                ObGr_json['objects'].append({'type': 'Host','id': ObjectID})
                                outfile.write(f'{json.dumps(json_resp,indent=4)}\n')
                                # Set JSON Data for checking DUMP size
                                ObGr_json_Size = json.dumps(ObGr_json)
                                # Validate size of JSON Data
                                if sys.getsizeof(ObGr_json_Size) >= 20000:
                                    print(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... View Output File For Full Change Log...\n{"*"*95}')
                                    outfile.write(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... \n{json.dumps(ObGr_json,indent=4)}\n{"*"*95}')
                                    # Increase Object-Group Counter
                                    ObGr_Counter = ObGr_Counter + 1

                                    # Run Object Object-Group Creation
                                    #ObGr_Data = LargeObGrPost()

                                    # Add Counter To Group Name
                                    ObGr_Count = f'{ObGr_NAME}-{ObGr_Counter}'
                                    ObGr_json['name'] = ObGr_Count
                                    # Format URL for Object-Group POST
                                    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networkgroups'
                                    # Perform POST for Obect-Group
                                    try:
                                        # REST call with SSL verification turned off:
                                        r = requests.post(url, data=json.dumps(ObGr_json), headers=headers, verify=False)
                                        status_code = r.status_code
                                        resp = r.text
                                        json_resp = json.loads(resp)
                                        print(f'Status code is: {status_code}')
                                        if status_code == 201 or status_code == 202:
                                            print('Object-Group Processing... View Output File For Full Change Log...')
                                            # Append Object-Group JSON with new entry for Network-Object
                                            outfile.write(f'Object-Group Created...\n{ObGr_Count}\n{json.dumps(json_resp,indent=4)}\n')
                                            # Reset Object-Group Data
                                            ObGr_Data = None
                                            ObGr_Data = {
                                            'name': ObGr_NAME,
                                            'objects': [],
                                            'type': 'NetworkGroup'
                                            }
                                            # Read Object-Group JSON data for Editing
                                            ObGr_json = json.loads(json.dumps(ObGr_Data))
                                        else :
                                            json_resp = json.loads(resp)
                                            r.raise_for_status()
                                            print (f'Error occurred in POST --> {resp}{ObjectName}')
                                            outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')
                                    except requests.exceptions.HTTPError as err:
                                        print (f'Error in connection --> {err}')
                                        outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')

                                    finally:
                                        try:
                                            if r: r.close()
                                        except:
                                            None
                            else :
                                r.raise_for_status()
                                outfile.write('Error occurred in POST --> '+json.dumps(json_resp,sort_keys=True,indent=4, separators=(',', ': '))+'\n'+ObjectName+'\n')
                                print ('Error occurred in POST --> '+json.dumps(json_resp,sort_keys=True,indent=4, separators=(',', ': '))+'\n'+ObjectName+'\n')
                        except requests.exceptions.HTTPError as err:
                            json_resp = json.loads(resp)
                            print (f'Error in connection --> {err}')
                            outfile.write(f'Error in connection --> {err}'+'\n'+json.dumps(json_resp,sort_keys=True,indent=4, separators=(',', ': '))+'\n'+ObjectName+'\n')
                            for item in json_resp['error']['messages']:
                                # Error Handling for Network-Object that already exists
                                if 'already exists' in item['description']:
                                    print(f'Network Object Already Exists... Attempting to Get UUID for {ObjectName}')

                                    # Perform GET to grab UUID for Network Object that already exists
                                    ObjectID = GetNetObjectUUID(server,API_UUID,headers,ObjectName,outfile)

                                    # Append Object-Group JSON with new entry for Network-Object
                                    ObGr_json['objects'].append({'type': 'Host','id': ObjectID})
                                    outfile.write(f'{json.dumps(json_resp,indent=4)}\n')

                                    # Set JSON Data for checking DUMP size
                                    ObGr_json_Size = json.dumps(ObGr_json)

                                    # Validate size of JSON Data
                                    if sys.getsizeof(ObGr_json_Size) >= 20000:
                                        print(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... View Output File For Full Change Log...\n{"*"*95}')
                                        outfile.write(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... \n{json.dumps(ObGr_json,indent=4)}\n{"*"*95}')
                                        # Increase Object-Group Counter
                                        ObGr_Counter += 1

                                        # Run Object Object-Group Creation
                                        #ObGr_Data = LargeObGrPost()

                                        # Add Counter To Group Name
                                        ObGr_Count = ObGr_NAME+'-'+str(ObGr_Counter)
                                        ObGr_json['name'] = ObGr_Count
                                        # Format URL for Object-Group POST
                                        url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networkgroups'
                                        # Perform POST for Obect-Group
                                        try:
                                            # REST call with SSL verification turned off:
                                            r = requests.post(url, data=json.dumps(ObGr_json), headers=headers, verify=False)
                                            status_code = r.status_code
                                            resp = r.text
                                            json_resp = json.loads(resp)
                                            print(f'Status code is: {status_code}')
                                            if status_code == 201 or status_code == 202:

                                                print('Object-Group Processing... View Output File For Full Change Log...')
                                                # Append Object-Group JSON with new entry for Network-Object

                                                outfile.write(f'Object-Group Created...\n{ObGr_Count}\n{json.dumps(json_resp,indent=4)}\n')
                                                # Reset Object-Group Data
                                                ObGr_Data = None
                                                ObGr_Data = {
                                                'name': ObGr_NAME,
                                                'objects': [],
                                                'type': 'NetworkGroup'
                                                }
                                                # Read Object-Group JSON data for Editing
                                                ObGr_json = json.loads(json.dumps(ObGr_Data))
                                            else :
                                                json_resp = json.loads(resp)
                                                r.raise_for_status()
                                                print(f'Error occurred in POST --> {resp}{ObjectName}')
                                                outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')
                                        except requests.exceptions.HTTPError as err:
                                            print (f'Error in connection --> {err}')
                                            outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')

                                        finally:
                                            try:
                                                if r: r.close()
                                            except:
                                                None
                        finally:
                            try:
                                if r: r.close()
                            except:
                                None

        # Process Network Entries
        elif item.startswith(' network-object '):
            net = item.strip(' network-object ').replace(' ','/')
            # Convert Netmask to CIDR notation
            Address = netaddr.IPNetwork(net).cidr
            # Define Network-Object Name
            ObjectName = f'net-{str(Address).replace("/","n")}'
            # Create Network-Object JSON Data
            post_data = {
            'name': ObjectName,
            'type': 'Network',
            'description': '',
            'value': str(Address)
            }
            # Define Network-Object Counter
            NetOb_Counter += 1
            if NetOb_Counter in list(range(50,2000,50)):
                ## Generate Access Token
                print ('Attempting to Renew Token...')
                results=AccessToken(server,headers,username,password)
                headers['X-auth-access-token']=results[0]
            # Perform POST for each Network-Object
            try:
                # Format URL for Network-Object POST
                url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networks'
                # REST call with SSL verification turned off:
                r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
                status_code = r.status_code
                resp = r.text
                print(f'[{NetOb_Counter}] Network-Object Processing... View Output File For Full Change Log...')
                print(f'Status code is: {status_code}')
                json_resp = json.loads(resp)
                if status_code == 201 or status_code == 202:
                    # Pull Object UUID from json_resp data
                    ObjectID = json_resp ['id']
                    # Append Object-Group JSON with new entry for Network-Object
                    ObGr_json['objects'].append({'type': 'Network','id': ObjectID})
                    outfile.write(f'{json.dumps(json_resp,indent=4)}\n')
                    # Set JSON Data for checking DUMP size
                    ObGr_json_Size = json.dumps(ObGr_json)
                    # Validate size of JSON Data
                    if sys.getsizeof(ObGr_json_Size) >= 20000:
                        print(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... View Output File For Full Change Log...\n{"*"*95}')
                        outfile.write(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... \n{json.dumps(ObGr_json,indent=4)}\n{"*"*95}')
                        # Increase Object-Group Counter
                        ObGr_Counter += 1
                        # Add Counter To Group Name
                        ObGr_Count = f'{ObGr_NAME}-{ObGr_Counter}'
                        ObGr_json['name'] = ObGr_Count
                        # Format URL for Object-Group POST
                        url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networkgroups'
                        # Perform POST for Obect-Group
                        try:
                            # REST call with SSL verification turned off:
                            r = requests.post(url, data=json.dumps(ObGr_json), headers=headers, verify=False)
                            status_code = r.status_code
                            resp = r.text
                            json_resp = json.loads(resp)
                            print(f'Status code is: {status_code}')
                            if status_code == 201 or status_code == 202:
                                print('Object-Group Processing... View Output File For Full Change Log...')
                                # Append Object-Group JSON with new entry for Network-Object
                                outfile.write(f'Object-Group Created...\n{ObGr_Count}\n{json.dumps(json_resp,indent=4)}\n')
                                # Reset Object-Group Data
                                ObGr_Data = None
                                ObGr_Data = {
                                'name': ObGr_NAME,
                                'objects': [],
                                'type': 'NetworkGroup'
                                }
                                # Read Object-Group JSON data for Editing
                                ObGr_json = json.loads(json.dumps(ObGr_Data))
                            else :
                                json_resp = json.loads(resp)
                                r.raise_for_status()
                                print (f'Error occurred in POST --> {resp}{ObjectName}')
                                outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')
                        except requests.exceptions.HTTPError as err:
                            print (f'Error in connection --> {err}')
                            outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')

                        finally:
                            try:
                                if r: r.close()
                            except:
                                None
                else :
                    r.raise_for_status()
                    outfile.write(f'Error occurred in POST --> {json.dumps(json_resp,indent=4)}\n{ObjectName}\n')
                    print(f'Error occurred in POST --> {json.dumps(json_resp,indent=4)}\n{ObjectName}\n')
            except requests.exceptions.HTTPError as err:
                json_resp = json.loads(resp)
                print(f'Error in connection -->{err}')
                outfile.write(f'Error in connection --> {err}\n{json.dumps(json_resp,indent=4)}\n{ObjectName}\n')
                for item in json_resp['error']['messages']:
                    # Error Handling for Network-Object that already exists
                    if 'already exists' in item['description']:
                        print(f'Network Object Already Exists... Attempting to Get UUID for {ObjectName}')

                        # Perform GET to grab UUID for Network Object that already exists
                        ObjectID = GetNetObjectUUID(server,API_UUID,headers,ObjectName,outfile)

                        # Append Object-Group JSON with new entry for Network-Object
                        ObGr_json['objects'].append({'type': 'Network','id': ObjectID})
                        outfile.write(json.dumps(json_resp,sort_keys=True,indent=4, separators=(',', ': '))+'\n')

                        # Set JSON Data for checking DUMP size
                        ObGr_json_Size = json.dumps(ObGr_json)

                        # Validate size of JSON Data
                        if sys.getsizeof(ObGr_json_Size) >= 20000:
                            print(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... View Output File For Full Change Log...\n{"*"*95}')
                            outfile.write(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... \n{json.dumps(ObGr_json,indent=4)}\n{"*"*95}')
                            # Increase Object-Group Counter
                            ObGr_Counter += 1

                            # Run Object Object-Group Creation
                            #ObGr_Data = LargeObGrPost()

                            # Add Counter To Group Name
                            ObGr_Count = f'{ObGr_NAME}-{ObGr_Counter}'
                            ObGr_json['name'] = ObGr_Count
                            # Format URL for Object-Group POST
                            url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networkgroups'
                            # Perform POST for Obect-Group
                            try:
                                # REST call with SSL verification turned off:
                                r = requests.post(url, data=json.dumps(ObGr_json), headers=headers, verify=False)
                                status_code = r.status_code
                                resp = r.text
                                json_resp = json.loads(resp)
                                print(f'Status code is: {status_code}')
                                if status_code == 201 or status_code == 202:
                                    print('Object-Group Processing... View Output File For Full Change Log...')
                                    # Append Object-Group JSON with new entry for Network-Object
                                    outfile.write(f'Object-Group Created...\n{ObGr_Count}\n{json.dumps(json_resp,indent=4)}\n')
                                    # Reset Object-Group Data
                                    ObGr_Data = None
                                    ObGr_Data = {
                                    'name': ObGr_NAME,
                                    'objects': [],
                                    'type': 'NetworkGroup'
                                    }
                                    # Read Object-Group JSON data for Editing
                                    ObGr_json = json.loads(json.dumps(ObGr_Data))
                                else :
                                    json_resp = json.loads(resp)
                                    r.raise_for_status()
                                    print (f'Error occurred in POST --> {resp}{ObjectName}')
                                    outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')
                            except requests.exceptions.HTTPError as err:
                                print (f'Error in connection --> {err}')
                                outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')

                            finally:
                                try:
                                    if r: r.close()
                                except:
                                    None

                    # Error Handling for Access Token Timeout
                    elif 'Access token invalid' in item['description']:
                        print ('Access token invalid... Attempting to Renew Token...')
                        results=AccessToken(server,headers,username,password)
                        headers['X-auth-access-token']=results[0]

                        # Perform POST for each Network-Object
                        try:
                            # Format URL for Network-Object POST
                            url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networks'
                            # REST call with SSL verification turned off:
                            r = requests.post(url, data=json.dumps(post_data), headers=headers, verify=False)
                            # REST call with SSL verification turned on:
                            # r = requests.post(url, data=json.dumps(post_data), headers=headers, verify='/path/to/ssl_certificate')
                            status_code = r.status_code
                            resp = r.text
                            print('['+str(NetOb_Counter)+'] Network-Object Processing... View Output File For Full Change Log...')
                            print(f'Status code is: {status_code}')
                            json_resp = json.loads(resp)
                            if status_code == 201 or status_code == 202:
                                # Pull Object UUID from json_resp data
                                ObjectID = json_resp ['id']
                                # Append Object-Group JSON with new entry for Network-Object
                                ObGr_json['objects'].append({'type': 'Network','id': ObjectID})
                                outfile.write(f'{json.dumps(json_resp,indent=4)}\n')
                                # Set JSON Data for checking DUMP size
                                ObGr_json_Size = json.dumps(ObGr_json)
                                # Validate size of JSON Data
                                if sys.getsizeof(ObGr_json_Size) >= 20000:
                                    print(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... View Output File For Full Change Log...\n{"*"*95}')
                                    outfile.write(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... \n{json.dumps(ObGr_json,indent=4)}\n{"*"*95}')
                                    # Increase Object-Group Counter
                                    ObGr_Counter = ObGr_Counter + 1

                                    # Run Object Object-Group Creation
                                    #ObGr_Data = LargeObGrPost()

                                    # Add Counter To Group Name
                                    ObGr_Count = f'{ObGr_NAME}-{ObGr_Counter}'
                                    ObGr_json['name'] = ObGr_Count
                                    # Format URL for Object-Group POST
                                    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networkgroups'
                                    # Perform POST for Obect-Group
                                    try:
                                        # REST call with SSL verification turned off:
                                        r = requests.post(url, data=json.dumps(ObGr_json), headers=headers, verify=False)
                                        status_code = r.status_code
                                        resp = r.text
                                        json_resp = json.loads(resp)
                                        print(f'Status code is: {status_code}')
                                        if status_code == 201 or status_code == 202:
                                            print('Object-Group Processing... View Output File For Full Change Log...')
                                            # Append Object-Group JSON with new entry for Network-Object
                                            outfile.write(f'Object-Group Created...\n{ObGr_Count}\n{json.dumps(json_resp,indent=4)}\n')
                                            # Reset Object-Group Data
                                            ObGr_Data = None
                                            ObGr_Data = {
                                            'name': ObGr_NAME,
                                            'objects': [],
                                            'type': 'NetworkGroup'
                                            }
                                            # Read Object-Group JSON data for Editing
                                            ObGr_json = json.loads(json.dumps(ObGr_Data))
                                        else :
                                            json_resp = json.loads(resp)
                                            r.raise_for_status()
                                            print (f'Error occurred in POST --> {resp}{ObjectName}')
                                            outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')
                                    except requests.exceptions.HTTPError as err:
                                        print (f'Error in connection --> {err}')
                                        outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')

                                    finally:
                                        try:
                                            if r: r.close()
                                        except:
                                            None
                            else :
                                r.raise_for_status()
                                outfile.write('Error occurred in POST --> '+json.dumps(json_resp,sort_keys=True,indent=4, separators=(',', ': '))+'\n'+ObjectName+'\n')
                                print ('Error occurred in POST --> '+json.dumps(json_resp,sort_keys=True,indent=4, separators=(',', ': '))+'\n'+ObjectName+'\n')
                        except requests.exceptions.HTTPError as err:
                            json_resp = json.loads(resp)
                            print (f'Error in connection --> {err}')
                            outfile.write(f'Error in connection --> {err}'+'\n'+json.dumps(json_resp,sort_keys=True,indent=4, separators=(',', ': '))+'\n'+ObjectName+'\n')
                            for item in json_resp['error']['messages']:
                                # Error Handling for Network-Object that already exists
                                if 'already exists' in item['description']:
                                    print(f'Network Object Already Exists... Attempting to Get UUID for {ObjectName}')

                                    # Perform GET to grab UUID for Network Object that already exists
                                    ObjectID = GetNetObjectUUID(server,API_UUID,headers,ObjectName,outfile)

                                    # Append Object-Group JSON with new entry for Network-Object
                                    ObGr_json['objects'].append({'type': 'Network','id': ObjectID})
                                    outfile.write(f'{json.dumps(json_resp,indent=4)}\n')

                                    # Set JSON Data for checking DUMP size
                                    ObGr_json_Size = json.dumps(ObGr_json)

                                    # Validate size of JSON Data
                                    if sys.getsizeof(ObGr_json_Size) >= 20000:
                                        print(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... View Output File For Full Change Log...\n{"*"*95}')
                                        outfile.write(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... \n{json.dumps(ObGr_json,indent=4)}\n{"*"*95}')
                                        # Increase Object-Group Counter
                                        ObGr_Counter += 1

                                        # Run Object Object-Group Creation
                                        #ObGr_Data = LargeObGrPost()

                                        # Add Counter To Group Name
                                        ObGr_Count = ObGr_NAME+'-'+str(ObGr_Counter)
                                        ObGr_json['name'] = ObGr_Count
                                        # Format URL for Object-Group POST
                                        url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networkgroups'
                                        # Perform POST for Obect-Group
                                        try:
                                            # REST call with SSL verification turned off:
                                            r = requests.post(url, data=json.dumps(ObGr_json), headers=headers, verify=False)
                                            # REST call with SSL verification turned on:
                                            # r = requests.post(url, data=json.dumps(post_data), headers=headers, verify='/path/to/ssl_certificate')
                                            status_code = r.status_code
                                            resp = r.text
                                            json_resp = json.loads(resp)
                                            print(f'Status code is: {status_code}')
                                            if status_code == 201 or status_code == 202:

                                                print('Object-Group Processing... View Output File For Full Change Log...')
                                                # Append Object-Group JSON with new entry for Network-Object

                                                outfile.write(f'Object-Group Created...\n{ObGr_Count}\n{json.dumps(json_resp,indent=4)}\n')
                                                # Reset Object-Group Data
                                                ObGr_Data = None
                                                ObGr_Data = {
                                                'name': ObGr_NAME,
                                                'objects': [],
                                                'type': 'NetworkGroup'
                                                }
                                                # Read Object-Group JSON data for Editing
                                                ObGr_json = json.loads(json.dumps(ObGr_Data))
                                            else :
                                                json_resp = json.loads(resp)
                                                r.raise_for_status()
                                                print(f'Error occurred in POST --> {resp}{ObjectName}')
                                                outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')
                                        except requests.exceptions.HTTPError as err:
                                            print (f'Error in connection --> {err}')
                                            outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')

                                        finally:
                                            try:
                                                if r: r.close()
                                            except:
                                                None
                        finally:
                            try:
                                if r: r.close()
                            except:
                                None


    # Post Final Object-Group
    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/networkgroups'
    # ReDefine Original Object-Group Name
    ObGr_NAME = ObGr_NAME_Orig
    ObGr_json_Size = json.dumps(ObGr_json)
    # Perform POST for Obect-Group
    try:
        # REST call with SSL verification turned off:
        r = requests.post(url, data=json.dumps(ObGr_json), headers=headers, verify=False)
        status_code = r.status_code
        resp = r.text
        json_resp = json.loads(resp)
        print(f'Status code is: {status_code}')
        if status_code == 201 or status_code == 202:
            print(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... View Output File For Full Change Log...\n{"*"*95}')
            # Append Object-Group JSON with new entry for Network-Object
            outfile.write(f'{"*"*95}\nObject-Group Size {sys.getsizeof(ObGr_json_Size)}B, Processing Now... \n{json.dumps(ObGr_json,indent=4)}\n{"*"*95}')
        else :
            json_resp = json.loads(resp)
            r.raise_for_status()
            print(f'Error occurred in POST --> {resp}{ObjectName}')
            outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')
    except requests.exceptions.HTTPError as err:
        print (f'Error in connection --> {err}')
        outfile.write(f'{json.dumps(json_resp,indent=4)}\n{ObGr_NAME}\n')
    finally:
        try:
            if r: r.close()
        except:
            None

    outfile.close()

#
#
#
# Define IPS/File Policy Put Script as Funtion
def PutIntrusionFile(server,headers,username,password):
    print ('''
***********************************************************************************************
*                     Update IPS and/or File Policy for Access Rules                          *
*_____________________________________________________________________________________________*
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. Select Access Policy                                                                    *
*                                                                                             *
*  2. Select Intrusion Policy and Variable Set to apply to ALL rules                          *
*                                                                                             *
*  3. Select File Policy to apply to ALL rules                                                *
*                                                                                             *
***********************************************************************************************
''')

    print('Generating Access Token')
    # Generate Access Token and pull domains from auth headers
    results=AccessToken(server,headers,username,password)
    headers['X-auth-access-token']=results[0]
    domains = results[1]

    Test = False
    if len(domains) > 1:
        while not Test:
            print('Multiple FMC domains found:')
            for domain in domains:
                print(f'    {domain["name"]}')
            choice = input('\nPlease select an FMC domain: ').strip()
            for domain in domains:
                if choice in domain['name']:
                    API_UUID = domain['uuid']
                    Test=True
            if not Test:
                print('Invalid Selection...\n')
    else:
        API_UUID = domains[0]['uuid']


    # Get all Access Control Policies
    print('*\n*\nCOLLECTING Access Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/policy/accesspolicies?expanded=true&offset=0&limit=1000'
    acp_list = GetItems(url,headers)

    acp = Select('Access Control Policy',acp_list)
    #print(json.dumps(acp,indent=4))

    # Get all Access Control Policy rules
    print('*\n*\nCOLLECTING Access Policy rules...')
    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/policy/accesspolicies/{acp["id"]}/accessrules?offset=0&limit=1000&expanded=true'
    acp_rules = GetItems(url,headers)

    # Get all Intrusion Policies
    print('*\n*\nCOLLECTING Intusion Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/policy/intrusionpolicies?offset=0&limit=1000'
    ips_list = GetItems(url,headers)
    # Add None option
    ips_list.append({'None':'None'})
    ips = Select('Intusion Policy',ips_list)
    #print(json.dumps(ips,indent=4))

    if ips:
        # Get all Variable Sets
        print('*\n*\nCOLLECTING Variable Sets...')
        url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/variablesets?offset=0&limit=1000'
        vset_list = GetItems(url,headers)
        vset = Select('Variable Set',vset_list)
    else:
        vset = None

    # Get all File Policies
    print('*\n*\nCOLLECTING File Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/policy/filepolicies?offset=0&limit=1000'
    file_list = GetItems(url,headers)
    # Add None option
    file_list.append({'None':'None'})
    filepolicy = Select('File Policy',file_list)


    # For Loop to update all rules
    for item in acp_rules:
        if item ['action'] == 'ALLOW':
            if ips:
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
            if filepolicy:
                # Create FilePolicy
                item ['filePolicy'] = {}
                # Assign Values
                item ['filePolicy']['id'] = filepolicy['id']
                item ['filePolicy']['name'] = filepolicy['name']
                item ['filePolicy']['type'] = 'FilePolicy'

            # Delete Unprocessable items
            del item['links']
            del item['metadata']

            # Create Comment List if not in item, to be able to delete
            item ['commentHistoryList'] = {}
            del item['commentHistoryList']

    try:
        put_data = acp_rules
        url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/policy/accesspolicies/{acp["id"]}/accessrules?bulk=true'
        # REST call with SSL verification turned off:
        r = requests.put(url, json=put_data, headers=headers, verify=False)
        print(f'Performing API PUT to: {url}')
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
                results=AccessToken(server,headers,username,password)
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





#
#
#
# Define Inventory List Script as Funtion
def GetInventory(server,headers,username,password):
    print ('''
***********************************************************************************************
*                           Pull Full FMC Device Inventory List                               *
*_____________________________________________________________________________________________*
*                                                                                             *
***********************************************************************************************
''')

    print('Generating Access Token')
    # Generate Access Token and pull domains from auth headers
    results=AccessToken(server,headers,username,password)
    headers['X-auth-access-token']=results[0]
    domains = results[1]

    Test = False
    if len(domains) > 1:
        while not Test:
            print('Multiple FMC domains found:')
            for domain in domains:
                print(f'    {domain["name"]}')
            choice = input('\nPlease select an FMC domain: ').strip()
            for domain in domains:
                if choice in domain['name']:
                    API_UUID = domain['uuid']
                    Test=True
            if not Test:
                print('Invalid Selection...\n')
    else:
        API_UUID = domains[0]['uuid']

    # Get all Devices
    print('*\n*\nCOLLECTING ALL INVENTORY...')
    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/devices/devicerecords?expanded=true&offset=0&limit=1000'
    DEVICELIST_DATA = GetItems(url,headers)

    # Get all Cluster Devices
    print('*\n*\nCOLLECTING CLUSTER INVENTORY...')
    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/deviceclusters/ftddevicecluster?expanded=true&offset=0&limit=1000'
    CLUSTER_DATA = GetItems(url,headers)

    # Get all HA Devices
    print('*\n*\nCOLLECTING HA PAIR INVENTORY...')
    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/devicehapairs/ftddevicehapairs?expanded=true&offset=0&limit=1000'
    HA_DATA = GetItems(url,headers)


    ## TEST PRINT
    #print(json.dumps(DEVICELIST_DATA,indent=4))
    #print(json.dumps(CLUSTER_DATA,indent=4))
    #print(json.dumps(HA_DATA,indent=4))

    # Create Base Dict
    INVENTORY = {
        'deviceClusters':[],
        'deviceHAPairs':[],
        'devices':[]
        }

    if CLUSTER_DATA != []:
        for item in CLUSTER_DATA:
            temp_dict = {}
            temp_dict['name']= item['name']
            temp_dict['masterDevice'] = GetDeviceDetails(item['masterDevice']['id'],DEVICELIST_DATA)
            temp_dict['slaveDevices'] = []
            for item in item['slaveDevices']:
                temp_dict['slaveDevices'].append(GetDeviceDetails(item['id'],DEVICELIST_DATA))
            INVENTORY['deviceClusters'].append(temp_dict)

    if HA_DATA != []:
        for item in HA_DATA:
            temp_dict = {}
            temp_dict['name']= item['name']
            temp_dict['primary'] = GetDeviceDetails(item['primary']['id'],DEVICELIST_DATA)
            temp_dict['secondary'] = GetDeviceDetails(item['secondary']['id'],DEVICELIST_DATA)
            INVENTORY['deviceHAPairs'].append(temp_dict)

    if DEVICELIST_DATA != []:
        for item in DEVICELIST_DATA:
            temp_dict = {}
            temp_dict['name'] = item['name']
            temp_dict['model'] = item['model']
            temp_dict['hostname'] = item['hostName']
            temp_dict['healthStatus'] = item['healthStatus']
            temp_dict['sw_version'] = item['sw_version']
            temp_dict['license_caps'] = item['license_caps']
            temp_dict['ftdMode'] = ''
            if 'ftdMode' in item: temp_dict['ftdMode'] = item['ftdMode']
            temp_dict['deviceSerialNumber'] = ''
            if 'deviceSerialNumber' in item['metadata']: temp_dict['deviceSerialNumber'] = item['metadata']['deviceSerialNumber']
            if 'sruVersion' in item['metadata']: temp_dict['sru_version'] = item['metadata']['sruVersion']
            if 'vdbVersion' in item['metadata']: temp_dict['vdb_version'] = item['metadata']['vdbVersion']
            if 'snortVersion' in item['metadata']: temp_dict['snort_version'] = item['metadata']['snortVersion']
            if 'chassisData' in item['metadata']: temp_dict['chassisData'] = item['metadata']['chassisData']
            INVENTORY['devices'].append(temp_dict)


    print('*\n*\nFMC Inventory compilation successful...')
    # Ask if JSON output should be saved to File
    save = input('Would You Like To Save The JSON Output To File? [y/N]: ').lower()
    if save in (['yes','ye','y']):
        # Random Generated JSON Output File
        filename = ''.join(i for i in [chr(random.randint(97,122)) for i in range(6)])
        filename += '.json'
        print(f'*\n*\nRANDOM OUTPUT FILE CREATED... {filename}\n')
        with open(filename, 'a') as OutFile:
            OutFile.write(json.dumps(INVENTORY,indent=4))
    elif save in (['no','n','']):
        print(json.dumps(INVENTORY,indent=4))

    # Ask if CSV output should be saved to File
    save = input('Would You Like To Save CSV Output To File? [y/N]: ').lower()
    if save in (['yes','ye','y']):
        # Random Generated CSV Output File
        filename = ''.join(i for i in [chr(random.randint(97,122)) for i in range(6)])
        filename += '.csv'
        print(f'*\n*\nRANDOM OUTPUT FILE CREATED... {filename}\n')
        with open(filename, 'a') as OutFile:
            OutFile.write('NAME,MODEL,VERSION,STATUS,SERIAL,MODE,LICENSE,SRU,VDB,SNORT\n')
            if INVENTORY['deviceClusters'] != []:
                for item in INVENTORY['deviceClusters']:
                    mode = ''
                    sru_version = ''
                    vdb_version = ''
                    snort_version = ''
                    serial = ''
                    name = item['masterDevice']['name']
                    model = item['masterDevice']['model']
                    version = item['masterDevice']['sw_version']
                    status = item['masterDevice']['healthStatus']
                    license = ';'.join(item['masterDevice']['license_caps'])
                    if 'ftdMode' in item['masterDevice']: mode = item['masterDevice']['ftdMode']
                    if 'sru_version' in item['masterDevice']: sru_version = item['masterDevice']['sru_version']
                    if 'vdb_version' in item['masterDevice']: vdb_version = item['masterDevice']['vdb_version']
                    if 'snort_version' in item['masterDevice']: snort_version = item['masterDevice']['snort_version']
                    if 'chassisData' in item['masterDevice']: serial = item['masterDevice']['chassisData']['chassisSerialNo']
                    OutFile.write(f'{name},{model},{version},{status},{serial},{mode},{license},{sru_version},{vdb_version},{snort_version}\n')
                    for item in item['slaveDevices']:
                        mode = ''
                        sru_version = ''
                        vdb_version = ''
                        snort_version = ''
                        serial = ''
                        name = item['name']
                        model = item['model']
                        version = item['sw_version']
                        status = item['healthStatus']
                        license = ';'.join(item['license_caps'])
                        if 'ftdMode' in item: mode = item['ftdMode']
                        if 'sru_version' in item: sru_version = item['sru_version']
                        if 'vdb_version' in item: vdb_version = item['vdb_version']
                        if 'snort_version' in item: snort_version = item['snort_version']
                        if 'chassisData' in item: serial = item['chassisData']['chassisSerialNo']
                        OutFile.write(f'{name},{model},{version},{status},{serial},{mode},{license},{sru_version},{vdb_version},{snort_version}\n')
            if INVENTORY['deviceHAPairs'] != []:
                for item in INVENTORY['deviceHAPairs']:
                    mode = ''
                    sru_version = ''
                    vdb_version = ''
                    snort_version = ''
                    serial = ''
                    name = item['primary']['name']
                    model = item['primary']['model']
                    version = item['primary']['sw_version']
                    status = item['primary']['healthStatus']
                    license = ';'.join(item['primary']['license_caps'])
                    if 'ftdMode' in item['primary']: mode = item['primary']['ftdMode']
                    if 'sru_version' in item['primary']: sru_version = item['primary']['sru_version']
                    if 'vdb_version' in item['primary']: vdb_version = item['primary']['vdb_version']
                    if 'snort_version' in item['primary']: snort_version = item['primary']['snort_version']
                    if 'chassisData' in item['primary']:
                        serial = item['primary']['chassisData']['chassisSerialNo']
                    elif 'deviceSerialNumber' in item['primary']:
                        serial = item['primary']['deviceSerialNumber']
                    OutFile.write(f'{name},{model},{version},{status},{serial},{mode},{license},{sru_version},{vdb_version},{snort_version}\n')
                    mode = ''
                    sru_version = ''
                    vdb_version = ''
                    snort_version = ''
                    serial = ''
                    name = item['secondary']['name']
                    model = item['secondary']['model']
                    version = item['secondary']['sw_version']
                    status = item['secondary']['healthStatus']
                    license = ';'.join(item['secondary']['license_caps'])
                    if 'ftdMode' in item['secondary']: mode = item['secondary']['ftdMode']
                    if 'sru_version' in item['secondary']: sru_version = item['secondary']['sru_version']
                    if 'vdb_version' in item['secondary']: vdb_version = item['secondary']['vdb_version']
                    if 'snort_version' in item['secondary']: snort_version = item['secondary']['snort_version']
                    if 'chassisData' in item['secondary']:
                        serial = item['secondary']['chassisData']['chassisSerialNo']
                    elif 'deviceSerialNumber' in item['secondary']:
                        serial = item['secondary']['deviceSerialNumber']
                    OutFile.write(f'{name},{model},{version},{status},{serial},{mode},{license},{sru_version},{vdb_version},{snort_version}\n')
            if INVENTORY['devices'] != []:
                for item in INVENTORY['devices']:
                    serial = item['deviceSerialNumber']
                    name = item['name']
                    model = item['model']
                    hostname = item['hostname']
                    version = item['sw_version']
                    license = ';'.join(item['license_caps'])
                    status = item['healthStatus']
                    mode = ''
                    sru_version = ''
                    vdb_version = ''
                    snort_version = ''
                    serial = ''
                    if 'ftdMode' in item: mode = item['ftdMode']
                    if 'sru_version' in item: sru_version = item['sru_version']
                    if 'vdb_version' in item: vdb_version = item['vdb_version']
                    if 'snort_version' in item: snort_version = item['snort_version']
                    if 'chassisData' in item:
                        serial = item['chassisData']['chassisSerialNo']
                    elif 'deviceSerialNumber' in item:
                        serial = item['deviceSerialNumber']
                    OutFile.write(f'{name},{model},{version},{status},{serial},{mode},{license},{sru_version},{vdb_version},{snort_version}\n')





#
#
#
# Define Inventory List Script as Funtion
def RegisterFTD(server,headers,username,password):
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

    print('Generating Access Token')
    # Generate Access Token and pull domains from auth headers
    results=AccessToken(server,headers,username,password)
    headers['X-auth-access-token']=results[0]
    domains = results[1]

    Test = False
    if len(domains) > 1:
        while not Test:
            print('Multiple FMC domains found:')
            for domain in domains:
                print(f'    {domain["name"]}')
            choice = input('\nPlease select an FMC domain: ').strip()
            for domain in domains:
                if choice in domain['name']:
                    API_UUID = domain['uuid']
                    Test=True
            if not Test:
                print('Invalid Selection...\n')
    else:
        API_UUID = domains[0]['uuid']

    # Request FTD Details
    FTD_IP = input('Please enter FTD IP Address: ').strip()
    FTD_name = input('Please enter FTD display name: ').strip()
    FTD_user = input('Please enter FTD username: ').strip()
    FTD_pass = define_password()
    # Generate random Registration Key
    regKey = ''.join(i for i in [chr(random.randint(97,122)) for i in range(6)])

    # Create Get DATA JSON Dictionary to collect all ACP names
    print('*\n*\nCOLLECTING Access Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/policy/accesspolicies?offset=0&limit=1000'
    acp_list = GetItems(url,headers)


    acp = Select('Access Control Policy',acp_list)
    #print(json.dumps(acp,indent=4))

    post_data = {
        'name': FTD_name,
        'hostName': FTD_IP,
        'natID': 'cisco123',
        'regKey': regKey,
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


    url =f'{server}/api/fmc_config/v1/domain/{API_UUID}/devices/devicerecords'
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
            print ('Error occurred in POST --> {resp}')
    except requests.exceptions.HTTPError as err:
        print ('Error in connection --> {traceback.format_exc()}')
    finally:
        try:
            if r: r.close()
        except:
            None

    try:
        # Connect to FTD, and initiate registration
        print('\nConnecting to FTD for CLI registration...')
        connection = netmiko.ConnectHandler(ip=FTD_IP, device_type='autodetect', username=FTD_user, password=FTD_pass, global_delay_factor=6)
        output = connection.send_command(f'configure manager add {server.replace("https://","")} {regKey} cisco123')
        connection.disconnect()
        print('FTD Registration command successful...')
    except:
        print ('Error in SSH connection --> {traceback.format_exc()}')
        connection.disconnect()



#
#
#
# Define Inventory List Script as Funtion
def Prefilter2ACP(server,headers,username,password):
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

    print('Generating Access Token')
    # Generate Access Token and pull domains from auth headers
    results=AccessToken(server,headers,username,password)
    headers['X-auth-access-token']=results[0]
    domains = results[1]

    Test = False
    if len(domains) > 1:
        while not Test:
            print('Multiple FMC domains found:')
            for domain in domains:
                print(f'    {domain["name"]}')
            choice = input('\nPlease select an FMC domain: ').strip()
            for domain in domains:
                if choice in domain['name']:
                    API_UUID = domain['uuid']
                    Test=True
            if not Test:
                print('Invalid Selection...\n')
    else:
        API_UUID = domains[0]['uuid']


    # Get all Access Control Policies
    print('*\n*\nCOLLECTING Access Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/policy/accesspolicies?expanded=true&offset=0&limit=1000'
    acp_list = GetItems(url,headers)

    acp = Select('Access Control Policy',acp_list)
    #print(json.dumps(acp,indent=4))

    # Get Prefilter Policy
    print('*\n*\nCOLLECTING Applied Prefilter Policy...')
    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/policy/prefilterpolicies/{acp["prefilterPolicySetting"]["id"]}/prefilterrules?expanded=true&offset=0&limit=1000'
    prefilter_list = GetItems(url,headers)

    # Get all Intrusion Policies
    print('*\n*\nCOLLECTING Intusion Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/policy/intrusionpolicies?offset=0&limit=1000'
    ips_list = GetItems(url,headers)
    # Add None option
    ips_list.append({'None':'None'})
    ips = Select('Intusion Policy',ips_list)

    if ips:
        # Get all Variable Sets
        print('*\n*\nCOLLECTING Variable Sets...')
        url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/object/variablesets?offset=0&limit=1000'
        vset_list = GetItems(url,headers)
        vset = Select('Variable Set',vset_list)
    else:
        vset = None

    # Get all File Policies
    print('*\n*\nCOLLECTING File Policies...')
    url = f'{server}/api/fmc_config/v1/domain/{API_UUID}/policy/filepolicies?offset=0&limit=1000'
    file_list = GetItems(url,headers)
    # Add None option
    file_list.append({'None':'None'})
    filepolicy = Select('File Policy',file_list)
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
    url =f'{server}/api/fmc_config/v1/domain/{API_UUID}/policy/accesspolicies/{acp["id"]}/accessrules?bulk=true'
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
# Run Script if main
if __name__ == "__main__":
    #
    #
    #
    # Initial input request
    print ('''
***********************************************************************************************
*                                                                                             *
*                   Cisco FMC v6.7 API Tools (Written for Python 3.6+)                        *
*                                                                                             *
***********************************************************************************************
*                                                                                             *
* USER INPUT NEEDED:                                                                          *
*                                                                                             *
*  1. FQDN for FMC server (hostname.domain.com)                                               *
*                                                                                             *
*  2. API Username                                                                            *
*                                                                                             *
*  3. API Password                                                                            *
*                                                                                             *
***********************************************************************************************
''')

    Test = False
    while not Test:
        # Request FMC server FQDN
        server = input('Please Enter FMC fqdn: ').lower().strip()

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
            Test = True
        except:
            print(f'Connection to {server} on port 443 failed: {traceback.format_exc()}\n\n')

    # Adding HTTPS to Server for URL
    server = f'https://{server}'
    headers = {'Content-Type': 'application/json','Accept': 'application/json'}

    # Request Username and Password without showing password in clear text
    username = input('Please Enter API Username: ').strip()
    password = define_password()
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
*  7. Migrate Prefilter rules to Access Rules                                                 *
*                                                                                             *
***********************************************************************************************
''')

    #
    #
    #
    # Run script until user cancels
    while True:
        Script = False
        while not Script:
            script = input('Please Select Tool: ')
            if script == '1':
                Script = True
                BlankGet(server,headers,username,password)
            elif script == '2':
                Script = True
                PostNetworkObject(server,headers,username,password)
            elif script == '3':
                Script = True
                PostNetworkObjectGroup(server,headers,username,password)
            elif script == '4':
                Script = True
                PutIntrusionFile(server,headers,username,password)
            elif script == '5':
                Script = True
                GetInventory(server,headers,username,password)
            elif script == '6':
                Script = True
                RegisterFTD(server,headers,username,password)
            elif script == '7':
                Script = True
                Prefilter2ACP(server,headers,username,password)
            else:
                print('INVALID ENTRY... ')

        # Ask to end the loop
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
*  7. Migrate Prefilter rules to Access Rules                                                 *
*                                                                                             *
***********************************************************************************************
''')
        Loop = input('*\n*\nWould You Like To use another tool? [y/N]').lower()
        if Loop not in (['yes','ye','y','1','2','3','4','5','6','7']):
            break
