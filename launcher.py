#!/usr/bin/env python3

# Copyright (C) 2017-2018, 2021-2023 Michael Luck
# Distributed under the GNU GPL v3. For full terms see the file LICENSE.txt

# This file is part of Simple TTR Launcher.

# Simple TTR Launcher is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Simple TTR Launcher is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Simple TTR Launcher. If not, see <http://www.gnu.org/licenses/>.

"""
Handles the main launcher functions including:
- Displaying the Main Menu
- Adding accounts to login.json
- Changing stored passwords
- Removing accounts from login.json
- Setting TTR installation directory (if one is not automatically detected)
- Enabling/Disabling password encryption
"""

import os
import platform
import subprocess
import sys
import time
import webbrowser
import pwinput
import requests
import encrypt
import helper
import patcher


def show_menu(settings_data, redraw=True):
    """
    Displays the Main Menu of the launcher and handles menu item selection.

    :param settings_data: The settings from login.json using json.load().
    :param redraw: Used to check if menu list should be output to console.
    :return: The new redraw status flag.
    """

    # Skip menu if using command line args
    if len(sys.argv) == 3:
        helper.quit_launcher()

    num_menu_items = 10
    if redraw:
        print('### Main Menu ###')
        print('1. Play')
        print('2. Add an account')
        print('3. Change a stored password')
        print('4. Remove an account')
        print('5. Change Toontown Rewritten installation path')
        print('6. Enable/Disable password encryption')
        print('7. Toontown Rewritten website')
        print('8. Toontown Rewritten server status')
        print('9. ToonHQ.org')

    redraw = choose_menu(settings_data, num_menu_items)

    return redraw


def choose_menu(settings_data, num_menu_items):
    """
    Handles menu picker logic.

    :param settings_data: The settings from login.json using json.load().
    :param num_menu_items: The number of menu items that the user can choose.
    :return: The new redraw status flag.
    """

    redraw = True

    selection = helper.confirm('Choose an option: ', 1, num_menu_items)
    if selection == 1:
        print()
        if patcher.check_update(settings_data['launcher']['ttr-dir']):
            prepare_login(settings_data)
    elif selection == 2:
        print()
        add_account(settings_data)
    elif selection == 3:
        print()
        change_account(settings_data)
    elif selection == 4:
        print()
        remove_account(settings_data)
    elif selection == 5:
        print()
        change_ttr_dir(settings_data)
    elif selection == 6:
        print()
        encrypt.manage_password_encryption(settings_data)
    elif selection == 7:
        webbrowser.open('https://toon.town')
        redraw = False
    elif selection == 8:
        webbrowser.open('https://toon.town/status')
        redraw = False
    elif selection == 9:
        webbrowser.open('https://toonhq.org')
        redraw = False
    elif selection == 10:
        sys.exit()

    return redraw


def add_account(settings_data):
    """
    Adds a new account to login.json.

    :param settings_data: The settings from login.json using json.load().
    :return: True if account was added, or False if the user cancels
             or if the master password is incorrect.
    """

    username = input('Enter username to store or 0 for Main Menu: ')
    if username.isdecimal():
        num = int(username)
        if num == 0:
            print()
            return False

    password = pwinput.pwinput('Enter password to store: ')

    # If password encryption is being used, encrypt the new password
    if settings_data['launcher']['use-password-encryption']:
        msg = ('\nYou have made too many password attempts. '
               'No changes have been made.\n')
        master_password = encrypt.verify_master_password(
            settings_data, msg
        )

        if not master_password:
            return False

        salt = encrypt.get_salt(settings_data)
        password = encrypt.encrypt(
            master_password, salt, password
        ).decode('utf-8')

    num_accounts = len(settings_data['accounts'])

    # Add new account to json
    new_account = {'username': username, 'password': password}
    settings_data['accounts'][f'account{num_accounts + 1}'] = new_account
    helper.update_login_json(settings_data)
    print('\nAccount has been added.\n')

    return True


def change_account(settings_data):
    """
    Changes a stored password for an account stored in login.json.

    :param settings_data: The settings from login.json using json.load().
    """

    num_accounts = len(settings_data['accounts'])

    if num_accounts == 0:
        print('No accounts to change. Please add one first.\n')
        return

    print('Which account do you wish to modify?')
    for num in range(num_accounts):
        print(
            f'{num + 1}. '
            f'{settings_data["accounts"][f"account{num + 1}"]["username"]}'
        )

    selection = helper.confirm(
        'Enter account number or 0 for Main Menu: ', 0, num_accounts
    )

    if selection == 0:
        print()
        return

    password = pwinput.pwinput('Enter new password: ')

    # If password encryption is being used, encrypt the new password
    if settings_data['launcher']['use-password-encryption']:
        msg = ('\nYou have made too many password attempts. '
               'No changes have been made.\n')
        master_password = encrypt.verify_master_password(
            settings_data, msg
        )

        if not master_password:
            return

        salt = encrypt.get_salt(settings_data)
        password = encrypt.encrypt(
            master_password, salt, password
        ).decode('utf-8')

    # Set new password in json
    settings_data['accounts'][f'account{selection}']['password'] = password
    helper.update_login_json(settings_data)

    print('\nPassword has been changed.\n')


def remove_account(settings_data):
    """
    Removes an existing account from login.json.

    :param settings_data: The settings from login.json using json.load().
    """

    num_accounts = len(settings_data['accounts'])
    if num_accounts == 0:
        print('No accounts to remove.\n')
        return

    print('Which account do you wish to delete?')
    for num in range(num_accounts):
        print(
            f'{num + 1}. '
            f'{settings_data["accounts"][f"account{num + 1}"]["username"]}'
        )

    selection = helper.confirm(
        'Enter account number or 0 for Main Menu: ', 0, num_accounts
    )
    if selection == 0:
        print()
        return

    # Remove account from json
    del settings_data['accounts'][f'account{selection}']

    # Adjust account numbering
    selection += 1
    for num in range(selection, num_accounts + 1):
        settings_data['accounts'][f'account{num - 1}'] = (
            settings_data['accounts'].pop(f'account{num}'))

    helper.update_login_json(settings_data)
    print('\nAccount has been removed.\n')


def change_ttr_dir(settings_data):
    """
    Sets or modifies the TTR installation directory.

    :param settings_data: The settings from login.json using json.load().
    """

    ttr_dir = input(
        'Enter your desired installation path or 0 for Main Menu: '
    )
    if ttr_dir == '0':
        print()
    else:
        settings_data['launcher']['ttr-dir'] = ttr_dir
        helper.update_login_json(settings_data)
        print('\nInstallation path has been set.\n')


def prepare_login(settings_data):
    """
    Start of the login process. This function can handle a couple of scenarios:
    - Asks user which stored account they would like to use
    - Optionally can allow user to not use the account storage feature
    - Optionally supports passing credentials as command line arguments

    :param settings_data: The settings from login.json using json.load().
    """

    # Check if use-stored-accounts is set
    use_stored_accounts = settings_data['launcher']['use-stored-accounts']
    if use_stored_accounts and len(sys.argv) != 3:
        num_accounts = len(settings_data['accounts'])
        if num_accounts == 0:
            # Ask user to add an account if none exist yet
            account = add_account(settings_data)
            if not account:
                return

        # Ask user to select account if more than one is stored
        if num_accounts > 1:
            print('Which account do you wish to log in?')
            for num in range(num_accounts):
                account = (
                    settings_data["accounts"][f"account{num + 1}"]["username"])
                print(
                    f'{num + 1}. '
                    f'{account}'
                )

            selection = helper.confirm(
                'Enter account number or 0 for Main Menu: ', 0, num_accounts
            )
            if selection == 0:
                print()
                return
        else:
            selection = 1

        # Select correct stored account
        if f'account{selection}' in settings_data['accounts']:
            username = (
                settings_data['accounts'][f'account{selection}']['username'])
            password = (
                settings_data['accounts'][f'account{selection}']['password'])

            # If password encryption is being used, decrypt the password
            if settings_data['launcher']['use-password-encryption']:
                master_password = encrypt.verify_master_password(settings_data)
                if not master_password:
                    return

                salt = encrypt.get_salt(settings_data)
                password = encrypt.decrypt(
                    master_password, salt, password
                ).decode('utf-8')

    # Alternative login methods
    if len(sys.argv) == 3:
        print('Logging in with CLI arguments...')
        username = sys.argv[1]
        password = sys.argv[2]
    elif not use_stored_accounts:
        username = input('Enter username: ')
        password = pwinput.pwinput('Enter password: ')

    login_worker(settings_data, username, password)


def login_worker(settings_data, username, password):
    """
    Orchestrates calling functions for authentication, ToonGuard, 2FA
    and launching the game.

    :param settings_data: The settings from login.json using json.load().
    :param username: The account's username.
    :param password: The account's password.
    """

    # Information for TTR's login api
    url = 'https://www.toontownrewritten.com/api/login?format=json'
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    data = {'username': username, 'password': password}

    try:
        # Check for incorrect login info
        resp_data = check_login_info(url, headers, data)
        if resp_data is None:
            soft_fail()
            return

        # Check for toonguard or 2 factor
        resp_data = check_additional_auth(resp_data, url, headers)
        if resp_data is None:
            soft_fail()
            return

        # Wait in queue
        resp_data = check_queue(resp_data, url, headers)
        if resp_data is None:
            soft_fail()
            return
    except requests.exceptions.RequestException:
        print(
            'Could not connect to the Toontown Rewritten login server. '
            'Please check your internet connection '
            'as well as https://toon.town/status\n'
        )
        soft_fail()
    else:
        # Start game
        try:
            start_game(settings_data, resp_data)
        except FileNotFoundError:
            print(
                'Could not find Toontown Rewritten. '
                'Set your installation path at the Main Menu.\n'
            )


def do_request(url, headers, data, timeout=30):
    """
    Uses requests.post to post data to TTR's login API.

    :param url: TTR's login API endpoint.
    :param headers: The headers that will be sent to the API.
    :param data: The data that will be sent to the API.
    :return: The response data as a json object.
    """

    resp = requests.post(url=url, data=data, headers=headers, timeout=timeout)
    resp.raise_for_status()

    return resp.json()


def check_login_info(url, headers, data):
    """
    Attemps authentcation using the username and password.

    :param url: TTR's login API endpoint.
    :param headers: The headers that will be sent to the API.
    :param data: The data that will be sent to the API.
    :return: The response data in json if successful
             or None if the API reports success == false.
    """

    # Attempt login
    print('Requesting login...')
    resp_data = helper.retry(
        3,
        5,
        do_request,
        url=url,
        headers=headers,
        data=data
    )

    # False means incorrect password or servers are under maintenance
    if resp_data['success'] == 'false':
        if 'banner' in resp_data:
            banner = resp_data['banner']
            print(f'{banner}\n')
        else:
            print(
                'Username or password may be incorrect '
                'or the servers are down. '
                'Please check https://toon.town/status\n'
            )
        resp_data = None

    return resp_data


def check_additional_auth(resp_data, url, headers):
    """
    Checks for ToonGuard or 2FA authentication methods.

    :param resp_data: The json response data from check_login_info().
    :param url: TTR's login API endpoint.
    :param headers: The headers that will be sent to the API.
    :return: The response data in json if successful
             or None if the API reports success == false.
    """

    # Partial means TTR is looking for toonguard or 2FA so prompt user for it
    while resp_data['success'] == 'partial':
        print(resp_data['banner'])
        token = input('Enter token: ')
        data = {
            'appToken': token.rstrip(),
            'authToken': resp_data['responseToken']
        }
        resp_data = helper.retry(
            3,
            5,
            do_request,
            url=url,
            headers=headers,
            data=data
        )

    # Too many attempts were encountered
    if resp_data['success'] == 'false':
        if 'banner' in resp_data:
            banner = resp_data['banner']
            print(f'{banner}\n')
        else:
            print(
                'Something is wrong with your token. You may be entering an '
                'invalid one too many times. Please try again later.\n'
            )
        resp_data = None

    return resp_data


def check_queue(resp_data, url, headers):
    """
    Checks if user is waiting in queue (delayed status) and waits until ready.

    :param resp_data: The json response data from check_additional_auth().
    :param url: TTR's login API endpoint.
    :param headers: The headers that will be sent to the API.
    :return: The response data in json if successful
             or None if the API reports success == false.
    """

    # Check for queueToken
    while resp_data['success'] == 'delayed':
        position = resp_data['position']
        eta = int(resp_data['eta'])
        if int(eta) == 0:
            eta = 1
        print(f"You are queued in position {position}.")

        # Wait ETA seconds (1 second minimum) to check if no longer in queue
        time.sleep(eta)
        data = {'queueToken': resp_data['queueToken']}
        resp_data = helper.retry(
            3,
            5,
            do_request,
            url=url,
            headers=headers,
            data=data
        )

    # Something went wrong
    if resp_data['success'] == 'false':
        if 'banner' in resp_data:
            banner = resp_data['banner']
            print(f'{banner}\n')
        else:
            print(
                'Something went wrong logging into the queue. '
                'Please try again later.\n'
            )
        resp_data = None

    return resp_data


def start_game(settings_data, resp_data):
    """
    Launches the game according to installation directory location.

    :param settings_data: The settings from login.json using json.load().
    :param resp_data: The json response data from check_queue().
    """

    print('\nLogin successful!\n')

    ttr_dir = settings_data['launcher']['ttr-dir']
    ttr_gameserver = resp_data['gameserver']
    ttr_playcookie = resp_data['cookie']

    # Set environment vars
    os.environ['TTR_GAMESERVER'] = ttr_gameserver
    os.environ['TTR_PLAYCOOKIE'] = ttr_playcookie

    # Change to ttr directory and start the game
    os.chdir(ttr_dir)

    if platform.machine().endswith('64'):
        process = 'ttrengine64'
    else:
        process = 'ttrengine'

    subprocess.Popen(args=process, creationflags=subprocess.CREATE_NEW_CONSOLE)

    # Change directory back to the launcher
    os.chdir(helper.get_launcher_path())


def soft_fail():
    """
    Called when a recoverable login error is encountered.
    """

    print('Login failed. The above error message should tell you why.\n')


def init():
    """
    Main function, loads login.json and displays the Main Menu upon completion.
    Optionally verifies the user's master password if encryption is enabled.
    Also handles command line argument login method.
    """

    # Load login.json or create it if it does not exist
    settings_data = helper.load_login_json()

    # Skip menu if using command line args, else show menu
    if len(sys.argv) == 3:
        prepare_login(settings_data)
    else:
        # If password encryption is being used, ask to verify it first
        if 'use-password-encryption' not in settings_data['launcher']:
            settings_data['launcher']['use-password-encryption'] = False
        if settings_data['launcher']['use-password-encryption']:
            master_password = encrypt.verify_master_password(settings_data)

            if master_password:
                # If master password is verified, check for new hashing params
                encrypt.check_hashing_params(
                    master_password,
                    encrypt.get_salt(settings_data),
                    settings_data
                )
            else:
                # Wrong password entered too many times
                helper.quit_launcher()

        redraw = True
        while True:
            # Display the Main Menu
            try:
                redraw = show_menu(settings_data, redraw)
            except KeyboardInterrupt:
                sys.exit()


init()
