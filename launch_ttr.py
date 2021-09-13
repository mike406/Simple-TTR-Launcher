#!/usr/bin/env python3

# Copyright (C) 2017, 2018, 2021 Michael Luck
# Distributed under the GNU GPL v3. For full terms see the file LICENSE.txt

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os, sys, platform, subprocess, time, json, requests, getpass
if platform.system() == 'Windows':
    import winreg

def show_menu(settings_data):
    #Skip menu if using command line args
    if len(sys.argv) == 3:
        prepare_login(settings_data)
        
    num_menu_items = 6
    print('### Main Menu ###')
    print('1. Play')
    print('2. Add an account')
    print('3. Change a stored password')
    print('4. Remove an account')
    print('5. Set TTR directory location')
    print('6. Quit')
    
    while True:
        try:
            selection = int(input('Choose an option: '))
        except:
            print('Invalid choice. Try again.')
            continue;
        else:
            if selection < 1 or selection > num_menu_items:
                print('Invalid choice. Try again.')
                continue;
            break;
            
    print()
    
    if selection == 1:
        prepare_login(settings_data)
    elif selection == 2:
        add_account(settings_data)
    elif selection == 3:
        change_account(settings_data)
    elif selection == 4:
        remove_account(settings_data)
    elif selection == 5:
        change_ttr_dir(settings_data)
    elif selection == 6:
        sys.exit()
        
def add_account(settings_data, return_menu=True):
    u = input('Enter username to store or 0 for Menu: ')
    try:
        n = int(u)
    except:
        pass
    else:
        if n == 0:
            print()
            show_menu(settings_data)
            
    p = getpass.getpass('Enter password to store: ')
    
    num_accounts = len(settings_data['accounts'])
    
    # Add new account to json
    settings_data['accounts']['account'+str(num_accounts+1)] = {'username':u, 'password':p}
    
    # Open file and write json
    with open('login.json', 'w') as settings_file:
        json.dump(settings_data, settings_file, indent=4)
        
    print('\nAccount added.\n')
    
    if return_menu == True:
        show_menu(settings_data)
    
def change_account(settings_data):
    num_accounts = len(settings_data['accounts'])
    if num_accounts == 0:
        print('No accounts to change. Please add one first.\n')
        show_menu(settings_data)
        
    print('Which account do you wish to modify?')
    for x in range(num_accounts):
        print(str(x+1) + ". " + settings_data['accounts']['account'+str(x+1)]['username'])
    while True:
        try:
            selection = int(input('Enter account number or 0 for Menu: '))
        except:
            print('Invalid choice. Try again.')
            continue;
        else:
            if selection < 0 or selection > num_accounts:
                print('Invalid choice. Try again.')
                continue;
            elif selection == 0:
                print()
                show_menu(settings_data)
            break;
            
    p = getpass.getpass('Enter new password: ')
    
    # Set new password in json
    settings_data['accounts']['account'+str(selection)]['password'] = p
    
    # Open file and write json
    with open('login.json', 'w') as settings_file:
        json.dump(settings_data, settings_file, indent=4)
        
    print('\nPassword changed.\n')
    show_menu(settings_data)
    
def remove_account(settings_data):
    num_accounts = len(settings_data['accounts'])
    if num_accounts == 0:
        print('No accounts to remove.\n')
        show_menu(settings_data)
        
    print('Which account do you wish to delete?')
    for x in range(num_accounts):
        print(str(x+1) + ". " + settings_data['accounts']['account'+str(x+1)]['username'])
    while True:
        try:
            selection = int(input('Enter account number or 0 for Menu: '))
        except:
            print('Invalid choice. Try again.')
            continue;
        else:
            if selection < 0 or selection > num_accounts:
                print('Invalid choice. Try again.')
                continue;
            elif selection == 0:
                print()
                show_menu(settings_data)
            break;
            
    # Remove account from json
    del settings_data['accounts']['account'+str(selection)]
    
    # Adjust account numbering
    selection += 1
    for x in range(selection, num_accounts+1):
        settings_data['accounts']['account'+str(x-1)] = settings_data['accounts'].pop('account'+str(x))
        
    # Open file and write json
    with open('login.json', 'w') as settings_file:
        json.dump(settings_data, settings_file, indent=4)
        
    print('\nAccount has been removed.\n')
    show_menu(settings_data)
    
def change_ttr_dir(settings_data):
    ttr_dir = input('Enter full path to your Toontown Rewritten directory: ')
    
    settings_data['launcher']['ttr-dir'] = ttr_dir
    
    # Open file and write json
    with open('login.json', 'w') as settings_file:
        json.dump(settings_data, settings_file, indent=4)
        
    print('\nSet new directory.\n')
    show_menu(settings_data)
    
def prepare_login(settings_data):
    #Check if use-stored-accounts is set
    use_stored_accounts = settings_data['launcher']['use-stored-accounts']
    if use_stored_accounts is True:
        num_accounts = len(settings_data['accounts'])
        if num_accounts == 0:
            #print('No accounts available. Returning to menu.\n')
            add_account(settings_data, False)
        selection = 1
        
    #Begin user input
    if use_stored_accounts is True and num_accounts > 1 and len(sys.argv) != 3:
        print('Which account do you wish to log in?')
        for x in range(num_accounts):
            print(str(x+1) + ". " + settings_data['accounts']['account'+str(x+1)]['username'])
        while True:
            try:
                selection = int(input('Enter account number or 0 for Menu: '))
            except:
                print('Invalid choice. Try again.')
                continue;
            else:
                if selection < 0 or selection > num_accounts:
                    print('Invalid choice. Try again.')
                    continue;
                elif selection == 0:
                    print()
                    show_menu(settings_data)
                break;
                
    #Select correct stored account
    if use_stored_accounts is True and len(sys.argv) != 3 and 'account'+str(selection) in settings_data['accounts']:
        username = settings_data['accounts']['account'+str(selection)]['username']
        password = settings_data['accounts']['account'+str(selection)]['password']
        
    #Alternative login methods
    if len(sys.argv) == 3:
        username = sys.argv[1]
        password = sys.argv[2]
    elif use_stored_accounts is False:
        username = input('Enter username: ')
        password = getpass.getpass('Enter password: ')
        
    #Information for TTR's login api
    url = 'https://www.toontownrewritten.com/api/login?format=json'
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    data = {'username': username, 'password': password}    
    
    login_worker(settings_data, url, headers, data)
    
def login_worker(settings_data, url, headers, data):
    #Begin login request
    print("Requesting login...")
    (resp, resp_data) = do_request(url, data, headers)
    
    if resp_data is None:
        fail(resp)
        
    #Check for incorrect login info
    resp_data = check_login_info(resp_data, url, headers)
    
    #Check for toonguard or 2 factor
    resp_data = check_additional_auth(resp_data, url, headers)
    
    #Wait in queue
    resp_data = resp_data = check_queue(resp_data, url, headers)
    
    #Start game
    start_game(settings_data, resp_data)
    
def do_request(url, data, headers):
    try:
        resp = requests.post(url=url, data=data, headers=headers)
        if resp.status_code == 200:
            resp_data = resp.json()
        else:
            resp_data = None
    except:
        print('Could not connect to login server. Check connection...\n')
        quit()
        
    return (resp, resp_data)
    
def check_login_info(resp_data, url, headers):
    while resp_data['success'] == 'false':
        print(resp_data['banner'])
        username = input('Enter username: ')
        password = getpass.getpass('Enter password: ')
        data = {'username': username, 'password': password}
        (resp, resp_data) = do_request(url, data, headers)
        
        if resp_data is None:
            fail(resp)
            
    return resp_data
    
def check_additional_auth(resp_data, url, headers):
    while resp_data['success'] == 'partial':
        print(resp_data['banner'])
        code = input('Enter code: ')
        data = {'appToken': code.rstrip(), 'authToken': resp_data['responseToken']}
        (resp, resp_data) = do_request(url, data, headers)
        
        if resp_data is None:
            fail(resp)
        
        #Too many attempts so we're gonna start over with login
        if resp_data['success'] == 'false':
            resp_data = check_login_info(resp_data, url, headers)
            
    return resp_data
    
def check_queue(resp_data, url, headers):
    print('Checking queue...')
    #Check for queueToken
    while resp_data['success'] == 'delayed':
        print('You are queued in position ' + resp_data['position'])
        #Wait 3 secs to check if no longer in queue
        time.sleep(3)
        data = {'queueToken': resp_data['queueToken']}
        (resp, resp_data) = do_request(url, data, headers)
        
        if resp_data is None:
            fail(resp)
            
    print('Login successful...\n')
    
    return resp_data
    
def start_game(settings_data, resp_data):
    ttr_dir = settings_data['launcher']['ttr-dir']
    ttr_gameserver = resp_data['gameserver']
    ttr_playcookie = resp_data['cookie']
    
    #Set environment vars
    os.environ['TTR_GAMESERVER'] = ttr_gameserver
    os.environ['TTR_PLAYCOOKIE'] = ttr_playcookie
    
    #Change to ttr directory and start the game
    try:
        os.chdir(ttr_dir)
        
        sp = subprocess.Popen(args="ttrengine")
        sp.wait()
    except:
        print('Could not find Toontown Rewritten. Set your TTR directory at the Menu.')
        
    if len(sys.argv) == 3:
        sys.exit()
    else:
        print()
        show_menu(settings_data)
    
def fail(resp):
    print('Login request fail...servers might be down.\nStatus Code: ' + str(resp.status_code) + '\n')
    quit()
    
def quit(ret=0):
    input('Press enter to quit.')
    sys.exit(ret)
    
def init():
    print()
    
    #Open settings file
    try:
        with open('login.json', 'r') as settings_file:
            settings_data = json.load(settings_file)
    except FileNotFoundError:
        # Create new settings file
        if platform.system() == 'Windows':
            try:
                ttr_dir = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Launcher.exe')
                ttr_dir = ttr_dir.replace('Launcher.exe', '')
            except:
                ttr_dir = 'C:/Program Files/Toontown Rewritten'
        else:
            ttr_dir = input('Please set your TTR installation directory: ')
            
        json_data = {
                        "accounts": {
                        },
                        "launcher": {
                            "ttr-dir": ttr_dir,
                            "use-stored-accounts": True
                        }
                    }
                    
        try:
            with open('login.json', 'w+') as f:
                json.dump(json_data, f, indent=4)
        except:
            print('Failed to create login.json\n')
            quit()
            
        # File was created successfully, restart init()
        print('Created new login.json file.')
        init()
    except json.decoder.JSONDecodeError as inst:
        print('Badly formatted login.json file')
        print(inst)
        print('\nIf unsure how to fix, delete the login.json file and re-run launcher\n')
        quit()
    except:
        print('File IO Error\n')
        quit()
        
    show_menu(settings_data)
    
init()
