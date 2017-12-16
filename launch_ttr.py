# Copyright (C) 2017 Michael Luck
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

#!/usr/bin/env python3
import os, sys, subprocess, time, json, requests, threading, getpass

def do_request(url, params, headers):
    try:
        resp = requests.post(url=url, params=params, headers=headers)
        if (resp.status_code == 200):
            data = resp.json()
        else:
            data = None
    except:
        print('Could not connect to login server. Check connection...')
        quit();
        
    return (resp, data)
    
def check_login_info(data, url, headers):
    while (data['success'] == 'false'):
        print(data['banner'])
        username = input('Enter username: ')
        password = getpass.getpass('Enter password: ')
        params = {'format': 'json', 'username': username, 'password': password}
        (resp, data) = do_request(url, params, headers)
        
        if (data is None):
            fail(resp)

    return data
            
def check_additional_auth(data, url, headers):
    while (data['success'] == 'partial'):
        print(data['banner'])
        code = input('Enter code: ')
        params = {'format': 'json', 'appToken': code.rstrip(), 'authToken': data['responseToken']}
        (resp, data) = do_request(url, params, headers)
        
        if (data is None):
            fail(resp)
        
        #Too many attempts so we're gonna start over with login
        if (data['success'] == 'false'):
            data = check_login_info(data, url, headers)
         
    return data
         
def check_queue(data, url, headers):
    print('Checking queue...')
    #Check for queueToken
    while (data['success'] == 'delayed'):
        print('You are queued in position ' + data['position'])
        #Wait 3 secs to check if no longer in queue
        time.sleep(3)
        params = {'format': 'json', 'queueToken': data['queueToken']}
        (resp, data) = do_request(url, params, headers)
        
        if (data is None):
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
        
        print('Login success...')
        
        #Start ttr
        no_console_log = 0x08000000
        sp = subprocess.Popen(args="ttrengine.exe", creationflags=no_console_log)
    except:
        print('Could not find Toontown Rewritten directory')
        quit();

def fail(resp):
    print('Login request fail...servers probably down\nstatus_code=' + str(resp.status_code))
    quit();
    
def quit():
    input('Press enter to quit')
    sys.exit()
    
def login_worker(ttr_dir, url, headers, params):
    #Begin login request
    print("Requesting login...")
    (resp, data) = do_request(url, params, headers)

    if (data is None):
        fail(resp)

    #Check for incorrect login info
    data = check_login_info(data, url, headers)

    #Check for toonguard or 2 factor
    data = check_additional_auth(data, url, headers)
    
    #Wait in queue
    data = data = check_queue(data, url, headers)
    
    #Start game
    start_game(data, ttr_dir)
        
def init():
    #Open settings file
    try:
        with open('login.json', 'r') as settings_file:
            settings_data = json.loads(settings_file.read())
    except FileNotFoundError:
        print('Creating new login.json file. Add accounts to the newly created file and re-run launcher.')
        try:
            with open('login.json', 'w+') as f:
                f.write('{\n\t"accounts": {\n\t\t"username1": "username",\n\t\t"password1": "password",\n\n\t\t"username2": "add_as_many_accounts",\n\t\t"password2": "as_you_want"\n\t},\n\n\t"launcher": {\n\t\t"ttr-dir": "C:/Program Files (x86)/Toontown Rewritten",\n\t\t"use-stored-accounts": true\n\t}\n}')
        except:
            print('Failed to create login.json')
        quit();
    except json.decoder.JSONDecodeError as inst:
        print('Badly formatted login.json file')
        print(inst)
        print('\nIf unsure how to fix, simply delete the login.json file and re-run launcher\n')
        quit();
    except:
        print('File IO Error')
        quit();
    
    ttr_dir = settings_data['launcher']['ttr-dir']
    
    #Check if use-stored-accounts is set
    use_stored_accounts = settings_data['launcher']['use-stored-accounts']
    if (use_stored_accounts is True):
        length = len(settings_data['accounts'])
        if (length & 1 == 1):
            print('Mismatched account information\nDouble check login.json for any mistakes')
            quit();
        num_accounts = length / 2
        selection = 1
    
    #Begin user input
    if (use_stored_accounts is True and num_accounts >= 2 and len(sys.argv) != 3):
        print('Which account do you wish to log in?')
        try:
            selection = int(input('Enter corresponding number between 1 - ' + str(int(num_accounts)) + ': '))
            badval = False
        except:
            badval = True
        while (selection <= 0 or selection > num_accounts or badval is True):
            badval = False
            try:
                selection = int(input('Invalid choice. Try again: '))
            except:
                badval = True
    
    #Select correct stored account
    if (use_stored_accounts is True):
        if ('username'+str(selection) in settings_data['accounts']):
            username = settings_data['accounts']['username'+str(selection)]
        else:
            print('Missing username' + str(selection) + ' in login.json')
            username = input('Enter correct username: ')
        if ('password'+str(selection) in settings_data['accounts']):
            password = settings_data['accounts']['password'+str(selection)]
        else:
            print('Missing password' + str(selection) + ' in login.json')
            password = getpass.getpass('Enter password: ')
    
    #Alternative login methods
    if (len(sys.argv) == 3):
        username = sys.argv[1]
        password = sys.argv[2]
    elif (use_stored_accounts is False):
        username = input('Enter username: ')
        password = getpass.getpass('Enter password: ')

    #Information for TTR's login api
    url = 'https://www.toontownrewritten.com/api/login'
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    params = {'format': 'json', 'username': username, 'password': password}    
        
    login_worker(ttr_dir, url, headers, params)
    
init()