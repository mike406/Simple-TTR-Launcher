"""Contains the Launcher class which handles all main launcher
functionality.
"""

import os
import platform
import stat
import subprocess
import sys
import time
import pwinput
import requests
import encrypt
import helper
import patcher


class Launcher:
    """Handles the main launcher functions including:
    - Adding accounts to launcher.json
    - Changing stored passwords
    - Removing accounts from launcher.json
    - Setting TTR installation directory
    - Enabling/Disabling password encryption
    - Patches TTR game files
    """

    def __init__(self):
        """Initialize the launcher and load our launcher.json file
        Also verifies password encryption and checks if it should be
        upgraded
        """
        # Load launcher.json
        self.settings_data = helper.load_launcher_json()
        self.encrypt = encrypt.Encrypt(self.settings_data)

        if len(sys.argv) != 3:
            # If password encryption is being used, ask to verify it first
            if 'use-password-encryption' not in self.settings_data['launcher']:
                self.settings_data[
                    'launcher']['use-password-encryption'] = False
            if self.settings_data['launcher']['use-password-encryption']:
                master_password = self.encrypt.verify_master_password(
                    self.settings_data)

                if master_password:
                    # If master password is verified, check for new
                    # hashing params
                    self.encrypt.check_hashing_params(
                        master_password, self.settings_data)
                else:
                    # Wrong password entered too many times
                    helper.quit_launcher()

    def __check_update(self, patch_manifest):
        """
        Checks for updates for Toontown Rewritten and installs them.

        :param patch_manifest: The patch manifest URL path.
        """

        return patcher.check_update(
            self.settings_data['launcher']['ttr-dir'], patch_manifest)

    def __login_worker(self, username, password):
        """Orchestrates calling functions for authentication, ToonGuard, 2FA
        and launching the game.

        :param username: The account's username.
        :param password: The account's password.
        """

        # Information for TTR's login api
        url = 'https://www.toontownrewritten.com/api/login?format=json'
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        data = {'username': username, 'password': password}

        try:
            # Check for incorrect login info
            resp_data = self.__check_login_info(url, headers, data)
            if resp_data is None:
                self.__soft_fail()
                return

            # Check for toonguard or 2 factor
            resp_data = self.__check_additional_auth(resp_data, url, headers)
            if resp_data is None:
                self.__soft_fail()
                return

            # Wait in queue
            resp_data = self.__check_queue(resp_data, url, headers)
            if resp_data is None:
                self.__soft_fail()
                return
        except requests.exceptions.RequestException:
            print(
                '\nCould not connect to the Toontown Rewritten login server. '
                'Please check your internet connection '
                'as well as https://toon.town/status')
            self.__soft_fail()
        else:
            # Check for game updates, only continue logging in if it succeeds
            if not self.__check_update(resp_data['manifest']):
                return

            # Start game
            try:
                self.__start_game(resp_data)
            except FileNotFoundError:
                print(
                    '\nCould not find Toontown Rewritten. '
                    'Set your installation path at the Main Menu.')

    def __do_request(self, url, headers, data, timeout=30):
        """Uses requests.post to post data to TTR's login API.

        :param url: TTR's login API endpoint.
        :param headers: The headers that will be sent to the API.
        :param data: The data that will be sent to the API.
        :param timeout: The request timeout.
        :return: The response data as a json object.
        """

        resp = requests.post(
            url=url, data=data, headers=headers, timeout=timeout)
        resp.raise_for_status()

        return resp.json()

    def __check_login_info(self, url, headers, data):
        """Attemps authentcation using the username and password.

        :param url: TTR's login API endpoint.
        :param headers: The headers that will be sent to the API.
        :param data: The data that will be sent to the API.
        :return: The response data in json if successful
                 or None if the API reports success == false.
        """

        # Attempt login
        print('Requesting login...')
        resp_data = helper.retry(
            3, 5, self.__do_request, url=url, headers=headers, data=data)

        # False means incorrect password or servers are under maintenance
        if resp_data['success'] == 'false':
            if 'banner' in resp_data:
                banner = resp_data['banner']
                print(f'\n{banner}')
            else:
                print(
                    '\nUsername or password may be incorrect '
                    'or the servers are down. '
                    'Please check https://toon.town/status')
            resp_data = None

        return resp_data

    def __check_additional_auth(self, resp_data, url, headers):
        """Checks for ToonGuard or 2FA authentication methods.

        :param resp_data: The json response data from
                          self.__check_login_info().
        :param url: TTR's login API endpoint.
        :param headers: The headers that will be sent to the API.
        :return: The response data in json if successful
                 or None if the API reports success == false.
        """

        # Partial means TTR is looking for toonguard or 2FA so prompt
        # user for it
        while resp_data['success'] == 'partial':
            print(resp_data['banner'])
            token = input('Enter token: ')
            data = {
                'appToken': token.rstrip(),
                'authToken': resp_data['responseToken']
            }
            resp_data = helper.retry(
                3, 5, self.__do_request, url=url, headers=headers, data=data)

        # Too many attempts were encountered
        if resp_data['success'] == 'false':
            if 'banner' in resp_data:
                banner = resp_data['banner']
                print(f'\n{banner}')
            else:
                print(
                    '\nSomething is wrong with your token. '
                    'You may be entering an invalid one too many times. '
                    'Please try again later.')
            resp_data = None

        return resp_data

    def __check_queue(self, resp_data, url, headers):
        """Checks if user is waiting in queue (delayed status) and waits
        until ready.

        :param resp_data: The json response data from
                          self.__check_additional_auth().
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

            # Wait ETA seconds (1 second minimum) to check if no longer
            # in queue
            time.sleep(eta)
            data = {'queueToken': resp_data['queueToken']}
            resp_data = helper.retry(
                3, 5, self.__do_request, url=url, headers=headers, data=data)

        # Something went wrong
        if resp_data['success'] == 'false':
            if 'banner' in resp_data:
                banner = resp_data['banner']
                print(f'\n\n{banner}')
            else:
                print(
                    '\nSomething went wrong logging into the queue. '
                    'Please try again later.')
            resp_data = None

        return resp_data

    def __start_game(self, resp_data):
        """Launches the game according to installation directory location.

        :param resp_data: The json response data from self.__check_queue().
        """

        print('\nLogin successful!')

        display_logging = False
        if 'display-logging' in self.settings_data['launcher']:
            display_logging = self.settings_data['launcher']['display-logging']

        ttr_dir = self.settings_data['launcher']['ttr-dir']
        ttr_gameserver = resp_data['gameserver']
        ttr_playcookie = resp_data['cookie']

        os.environ['TTR_GAMESERVER'] = ttr_gameserver
        os.environ['TTR_PLAYCOOKIE'] = ttr_playcookie

        win32_bin = 'TTREngine'
        win64_bin = 'TTREngine64'
        linux_bin = 'TTREngine'
        darwin_bin = 'Toontown Rewritten'

        operating_system = platform.system()
        if operating_system == 'Windows':
            if platform.machine().endswith('64'):
                process = os.path.join(ttr_dir, win64_bin)
            else:
                process = os.path.join(ttr_dir, win32_bin)

            stdout = subprocess.DEVNULL
            stderr = subprocess.STDOUT
            creationflags = subprocess.CREATE_NO_WINDOW
            if display_logging:
                stdout = None
                stderr = None
                creationflags = subprocess.CREATE_NEW_CONSOLE

            subprocess.Popen(
                args=process,
                cwd=ttr_dir,
                stdout=stdout,
                stderr=stderr,
                creationflags=creationflags)
        elif operating_system in ['Linux', 'Darwin']:
            binary = linux_bin if operating_system == 'Linux' else darwin_bin
            process = os.path.join(ttr_dir, binary)
            mode = (os.stat(process).st_mode
                    | stat.S_IEXEC
                    | stat.S_IXUSR
                    | stat.S_IXGRP
                    | stat.S_IXOTH)
            os.chmod(process, mode)

            if display_logging:
                subprocess.run(args=process, cwd=ttr_dir, check=False)
            else:
                subprocess.Popen(
                    args=process, cwd=ttr_dir, stdout=subprocess.DEVNULL,
                    stderr=subprocess.STDOUT, start_new_session=True)

    def __soft_fail(self):
        """Called when a recoverable login error is encountered."""

        print('Login failed!')

    def add_account(self):
        """Adds a new account to launcher.json.

        :return: True if account was added, or False if the user cancels
                 or if the master password is incorrect.
        """

        username = input('Enter username to store or 0 to cancel: ')
        if username.isdecimal():
            num = int(username)
            if num == 0:
                return False

        password = pwinput.pwinput('Enter password to store: ')

        # If password encryption is being used, encrypt the new password
        if self.settings_data['launcher']['use-password-encryption']:
            msg = ('\nYou have made too many password attempts. '
                   'No changes have been made.')
            master_password = self.encrypt.verify_master_password(
                self.settings_data, msg)

            if not master_password:
                return False

            password = self.encrypt.encrypt(
                master_password, password).decode('utf-8')

        num_accounts = len(self.settings_data['accounts'])

        # Add new account to json
        new_account = {'username': username, 'password': password}
        self.settings_data[
            'accounts'][f'account{num_accounts + 1}'] = new_account
        helper.update_launcher_json(self.settings_data)
        print('\nAccount has been added.')

        return True

    def change_account(self):
        """Changes a stored password for an account stored in launcher.json."""

        num_accounts = len(self.settings_data['accounts'])

        if num_accounts == 0:
            print('No accounts to change. Please add one first.')
            return

        print('Which account do you wish to modify?')
        for num in range(num_accounts):
            account = self.settings_data[
                "accounts"][f"account{num + 1}"]["username"]
            print(
                f'{num + 1}. {account}')

        selection = helper.confirm(
            'Enter account number or 0 to cancel: ', 0, num_accounts)

        if selection == 0:
            return

        password = pwinput.pwinput('Enter new password: ')

        # If password encryption is being used, encrypt the new password
        if self.settings_data['launcher']['use-password-encryption']:
            msg = ('\nYou have made too many password attempts. '
                   'No changes have been made.')
            master_password = self.encrypt.verify_master_password(
                self.settings_data, msg)

            if not master_password:
                return

            password = self.encrypt.encrypt(
                master_password, password).decode('utf-8')

        # Set new password in json
        self.settings_data[
            'accounts'][f'account{selection}']['password'] = password
        helper.update_launcher_json(self.settings_data)

        print('\nPassword has been changed.')

    def remove_account(self):
        """Removes an existing account from launcher.json."""

        num_accounts = len(self.settings_data['accounts'])
        if num_accounts == 0:
            print('No accounts to remove.')
            return

        print('Which account do you wish to delete?')
        for num in range(num_accounts):
            account = self.settings_data[
                "accounts"][f"account{num + 1}"]["username"]
            print(
                f'{num + 1}. {account}')

        selection = helper.confirm(
            'Enter account number or 0 to cancel: ', 0, num_accounts)
        if selection == 0:
            return

        # Remove account from json
        del self.settings_data['accounts'][f'account{selection}']

        # Adjust account numbering
        selection += 1
        for num in range(selection, num_accounts + 1):
            self.settings_data['accounts'][f'account{num - 1}'] = (
                self.settings_data['accounts'].pop(f'account{num}'))

        helper.update_launcher_json(self.settings_data)
        print('\nAccount has been removed.')

    def change_ttr_dir(self):
        """Sets or modifies the TTR installation directory."""

        if 'ttr-dir' in self.settings_data['launcher']:
            cur = self.settings_data['launcher']['ttr-dir']
            print(f'Current installation path: {cur}')

        ttr_dir = input(
            'Enter your desired installation path or 0 to cancel: ')
        if ttr_dir != '0':
            self.settings_data['launcher']['ttr-dir'] = os.path.expanduser(
                ttr_dir)
            helper.update_launcher_json(self.settings_data)
            print('\nInstallation path has been set.')

    def prepare_login(self):
        """Start of the login process. This function can handle a couple of
        scenarios:

        - Asks user which stored account they would like to use
        - Optionally can allow user to not use the account storage feature
        - Optionally supports passing credentials as command line arguments
        """

        # Check if use-stored-accounts is set
        use_stored_accounts = self.settings_data[
            'launcher']['use-stored-accounts']
        if use_stored_accounts and len(sys.argv) != 3:
            num_accounts = len(self.settings_data['accounts'])
            if num_accounts == 0:
                # Ask user to add an account if none exist yet
                account = self.add_account()
                if not account:
                    return

            # Ask user to select account if more than one is stored
            selection = 1
            if num_accounts > 1:
                print('Which account do you wish to log in?')
                for num in range(num_accounts):
                    account = (
                        self.settings_data[
                            "accounts"][f"account{num + 1}"]["username"])
                    print(f'{num + 1}. {account}')

                selection = helper.confirm(
                    'Enter account number or 0 to cancel: ',
                    0, num_accounts)
                if selection == 0:
                    return

            # Select correct stored account
            if f'account{selection}' in self.settings_data['accounts']:
                username = (
                    self.settings_data[
                        'accounts'][f'account{selection}']['username'])
                password = (
                    self.settings_data[
                        'accounts'][f'account{selection}']['password'])

                # If password encryption is being used, decrypt the password
                if self.settings_data['launcher']['use-password-encryption']:
                    master_password = self.encrypt.verify_master_password(
                        self.settings_data)
                    if not master_password:
                        return

                    password = self.encrypt.decrypt(
                        master_password, password).decode('utf-8')

        # Alternative login methods
        if len(sys.argv) == 3:
            print('Logging in with CLI arguments...')
            username = sys.argv[1]
            password = sys.argv[2]
        elif not use_stored_accounts:
            username = input('Enter username: ')
            password = pwinput.pwinput('Enter password: ')

        self.__login_worker(username, password)

    def manage_password_encryption(self):
        """Allows the user to enable or disable password encryption."""

        self.encrypt.manage_password_encryption(self.settings_data)

    def toggle_account_storage(self):
        """Enable or disable the account storage feature."""

        self.settings_data['launcher']['use-stored-accounts'] = (
            not self.settings_data['launcher']['use-stored-accounts'])
        helper.update_launcher_json(self.settings_data)

    def toggle_game_log_display(self):
        """Enable or disable logging game to console."""

        self.settings_data['launcher']['display-logging'] = (
            not self.settings_data['launcher']['display-logging'])
        helper.update_launcher_json(self.settings_data)
