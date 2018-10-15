#!/usr/bin/env python3

# Copyright (C) 2017, 2018 Michael Luck
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

import os, sys, subprocess, time, json, requests, getpass

def show_menu(settings_data):
    #Menu
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

    
def prepare_login(settings_data):
    ttr_dir = settings_data['launcher']['ttr-dir']
    
    #Check if use-stored-accounts is set
    use_stored_accounts = settings_data['launcher']['use-stored-accounts']
    if use_stored_accounts is True:
        num_accounts = len(settings_data['accounts'])
        if num_accounts == 0:
            print('No accounts available. Returning to menu.\n')
            show_menu(settings_data)
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
    url = 'https://www.toontownrewritten.com/api/login'
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    params = {'format': 'json', 'username': username, 'password': password}    
        
    login_worker(ttr_dir, url, headers, params)
    
def add_account(settings_data):
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
    
    print('\nAccount added. Returning to menu.\n')
    show_menu(settings_data)
    
def change_account(settings_data):
    num_accounts = len(settings_data['accounts'])
    if num_accounts == 0:
        print('No accounts to change. Returning to menu.\n')
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
    
    print('\nPassword changed. Returning to menu.\n')
    show_menu(settings_data)
    
    
def remove_account(settings_data):
    num_accounts = len(settings_data['accounts'])
    if num_accounts == 0:
        print('No accounts to remove. Returning to menu.\n')
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
        
    print('\nAccount has been removed. Returning to menu.\n')
    show_menu(settings_data)
    
def change_ttr_dir(settings_data):
    ttr_dir = input('Enter full path to your Toontown Rewritten directory: ')
    
    settings_data['launcher']['ttr-dir'] = ttr_dir
    
    # Open file and write json
    with open('login.json', 'w') as settings_file:
        json.dump(settings_data, settings_file, indent=4)
        
    print('\nSet new directory. Returning to menu.\n')
    show_menu(settings_data)

def login_worker(ttr_dir, url, headers, params):
    #Begin login request
    print("Requesting login...")
    (resp, data) = do_request(url, params, headers)

    if data is None:
        fail(resp)

    #Check for incorrect login info
    data = check_login_info(data, url, headers)

    #Check for toonguard or 2 factor
    data = check_additional_auth(data, url, headers)
    
    #Wait in queue
    data = data = check_queue(data, url, headers)
    
    #Start game
    start_game(data, ttr_dir)

def do_request(url, params, headers):
    try:
        resp = requests.post(url=url, params=params, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
        else:
            data = None
    except:
        print('Could not connect to login server. Check connection...\n')
        quit()
        
    return (resp, data)
    
def check_login_info(data, url, headers):
    while data['success'] == 'false':
        print(data['banner'])
        username = input('Enter username: ')
        password = getpass.getpass('Enter password: ')
        params = {'format': 'json', 'username': username, 'password': password}
        (resp, data) = do_request(url, params, headers)
        
        if data is None:
            fail(resp)

    return data
            
def check_additional_auth(data, url, headers):
    while data['success'] == 'partial':
        print(data['banner'])
        code = input('Enter code: ')
        params = {'format': 'json', 'appToken': code.rstrip(), 'authToken': data['responseToken']}
        (resp, data) = do_request(url, params, headers)
        
        if data is None:
            fail(resp)
        
        #Too many attempts so we're gonna start over with login
        if data['success'] == 'false':
            data = check_login_info(data, url, headers)
         
    return data
         
def check_queue(data, url, headers):
    print('Checking queue...')
    #Check for queueToken
    while data['success'] == 'delayed':
        print('You are queued in position ' + data['position'])
        #Wait 3 secs to check if no longer in queue
        time.sleep(3)
        params = {'format': 'json', 'queueToken': data['queueToken']}
        (resp, data) = do_request(url, params, headers)
        
        if data is None:
            fail(resp)
            
    return data
    
def start_game(data, ttr_dir):
    TTR_GAMESERVER = data['gameserver']
    TTR_PLAYCOOKIE = data['cookie']

    #Set environment vars
    os.environ['TTR_GAMESERVER'] = TTR_GAMESERVER
    os.environ['TTR_PLAYCOOKIE'] = TTR_PLAYCOOKIE
    
    #Change to ttr directory
    try:
        os.chdir(ttr_dir)
        
        #Start ttr
        no_console_log = 0x08000000
        sp = subprocess.Popen(args="ttrengine.exe", creationflags=no_console_log)
        print('Login success...')
        time.sleep(5)
    except:
        print('Could not find Toontown Rewritten. Restart launcher and set your TTR directory at the Menu.\n')
        quit()

def fail(resp):
    print('Login request fail...servers might be down.\nStatus Code: ' + str(resp.status_code) + '\n')
    quit()
    
def quit():
    input('Press enter to quit.')
    sys.exit()
                
def init():
    #Open settings file
    try:
        with open('login.json', 'r') as settings_file:
            settings_data = json.load(settings_file)
    except FileNotFoundError:
        print('Creating new login.json file. Restart launcher to continue.')
        try:
            json_data = {
                            "accounts": {
                            },
                            "launcher": {
                                "ttr-dir": "C:/Program Files (x86)/Toontown Rewritten",
                                "use-stored-accounts": True
                            }
                        }
            with open('login.json', 'w+') as f:
                json.dump(json_data, f, indent=4)
        except:
            print('Failed to create login.json\n')
        quit()
    except json.decoder.JSONDecodeError as inst:
        print('Badly formatted login.json file')
        print(inst)
        print('\nIf unsure how to fix, delete the login.json file and re-run launcher\n')
        quit()
    except:
        print('File IO Error\n')
        quit()
    
    #Skip menu if using command line args
    if len(sys.argv) == 3:
        prepare_login(settings_data)
    else:
        show_menu(settings_data)
    
init()