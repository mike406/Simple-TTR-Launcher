"""Handles password encryption for the launcher.
It uses a user-created master password to encrypt account passwords.
The KDF used currently is argon2id from argon2-cffi and is used with Fernet
to encrypt passwords. The parameters used for argon2id are as defined in
RFC 9106 using the second recommended option for better compatibility with
devices that have lower amounts of memory.
https://www.rfc-editor.org/rfc/rfc9106.html#section-4-6.2
"""

import os
import base64
import pwinput
from cryptography.fernet import Fernet, InvalidToken
from argon2.low_level import hash_secret_raw
from argon2.low_level import Type
from argon2.profiles import RFC_9106_LOW_MEMORY
import helper


class Encrypt:
    """Password encryption class for the launcher."""

    def __init__(self, settings_data):
        """Initialize Encrypt class and store salt if it exists."""

        self.salt_length = 16
        self.argon_type = Type.ID
        self.hashing_params = {
            't': RFC_9106_LOW_MEMORY.time_cost,
            'm': RFC_9106_LOW_MEMORY.memory_cost,
            'p': RFC_9106_LOW_MEMORY.parallelism
        }

        if 'password-salt' in settings_data['launcher']:
            self.salt = base64.urlsafe_b64decode(
                settings_data['launcher']['password-salt'])
        else:
            self.salt = os.urandom(self.salt_length)

    def __encrypt_accounts(self, master_password_encoded, settings_data):
        """Encrypts all currently stored accounts using the master password
        and salt.

        :param master_password_encoded: The master password as a byte string.
        :param settings_data: The settings from launcher.json
                              using json.load().
        :return: The updated settings_data object.
        """

        num_accounts = len(settings_data['accounts'])

        # Set argon parameters
        settings_data['launcher']['hashing-params'] = dict(self.hashing_params)

        # Derive our key using master password and salt
        key = self.__derive_key(master_password_encoded, self.hashing_params)

        # Use Fernet class to encrypt each password using our key
        fernet = Fernet(key)

        # Encrypt all existing account passwords
        for num in range(num_accounts):
            acc = f'account{num + 1}'
            password = settings_data['accounts'][acc]['password'].encode(
                'utf-8')
            password_encrypted = fernet.encrypt(password).decode('utf-8')
            settings_data['accounts'][acc]['password'] = password_encrypted

        # Encrypted version of the salt will be used for verification
        salt_encrypted = fernet.encrypt(self.salt).decode('utf-8')
        settings_data['launcher']['password-verification'] = salt_encrypted

        return settings_data

    def __decrypt_accounts(
            self, master_password_encoded, settings_data, hashing_params):
        """Decrypts all currently stored accounts using the master password
        and salt.

        :param master_password_encoded: The master password as a byte string.
        :param settings_data: The settings from launcher.json
                              using json.load().
        :param hashing_params: Hashing parameters for argon as a dict.
        :return: The updated settings_data object.
        """

        num_accounts = len(settings_data['accounts'])

        # Derive our key using master password and salt
        key = self.__derive_key(master_password_encoded, hashing_params)

        # Use Fernet class to decrypt each password using our key
        fernet = Fernet(key)

        # Decrypt all existing account passwords
        for num in range(num_accounts):
            acc = f'account{num + 1}'
            password = settings_data['accounts'][acc]['password'].encode(
                'utf-8')
            password_decrypted = fernet.decrypt(password).decode('utf-8')
            settings_data['accounts'][acc]['password'] = password_decrypted

        settings_data['launcher']['use-password-encryption'] = False
        del settings_data['launcher']['password-salt']
        del settings_data['launcher']['password-verification']

        return settings_data

    def __derive_key(self, master_password_encoded, hashing_params):
        """Wrapper function for deriving the key using the master password
        and salt.

        :param master_password_encoded: The master password as a byte string.
        :param hashing_params: Hashing parameters for argon as a dict.
        :return: The derived key.
        """

        key = hash_secret_raw(
            secret=master_password_encoded,
            salt=self.salt,
            time_cost=hashing_params['t'],
            memory_cost=hashing_params['m'],
            parallelism=hashing_params['p'],
            hash_len=32,
            type=self.argon_type)

        return base64.urlsafe_b64encode(key)

    def manage_password_encryption(self, settings_data, upgrade=False):
        """Allows the user to enable or disable password encryption.

        :param settings_data: The settings from launcher.json
                              using json.load().
        :param upgrade: Suppresses some message output when upgrading hashing.
        """

        if 'use-password-encryption' not in settings_data['launcher']:
            settings_data['launcher']['use-password-encryption'] = False

        if settings_data['launcher']['use-password-encryption']:
            print('Would you like to remove password encryption?')
            print(
                'WARNING: Your existing passwords will revert to an '
                'unencrypted state! Please make sure you are okay with this.')
            remove_encryption = helper.confirm(
                'Enter 1 to confirm or 0 to cancel: ', 0, 1)

            # Verify master password and decrypt all accounts if correct
            if remove_encryption == 1:
                master_password_encoded = self.verify_master_password(
                    settings_data, '\nYou made too many password attempts. '
                                   'No changes have been made.')

                if master_password_encoded:
                    success = '\nYour master password has been removed.'
                    if len(settings_data['accounts']) > 0:
                        success += (' Any existing account passwords are now'
                                    ' decrypted.')
                        print('Decrypting your accounts...')
                    settings_data = self.__decrypt_accounts(
                        master_password_encoded, settings_data,
                        self.hashing_params)
                    print(success)
        else:
            if not upgrade:
                print(
                    'You can use a master password to encrypt your stored '
                    'accounts.\n'
                    'You can turn this feature off (and decrypt your '
                    'passwords) by going to "More options" in the Main Menu.')

            # Create the master password
            master_password = pwinput.pwinput('Create a master password: ')
            master_password_encoded = master_password.encode('utf-8')

            # Store the salt in base64 as we'll need it to derive the same key
            settings_data['launcher']['use-password-encryption'] = True
            settings_data[
                'launcher']['password-salt'] = base64.urlsafe_b64encode(
                    self.salt).decode('utf-8')

            # Encrypt any existing accounts using the key
            success = '\nYour master password has been set.'
            if len(settings_data['accounts']) > 0:
                success += ' Any existing account passwords are now encrypted.'
                print('Encrypting your accounts...')
            settings_data = self.__encrypt_accounts(
                master_password_encoded, settings_data)
            print(success)

            if upgrade:
                # Add a blank line before the menu gets displayed again
                print()

        helper.update_launcher_json(settings_data)

    def encrypt(self, master_password_encoded, data):
        """Encrypts data using the master password and salt.

        :param master_password_encoded: The master password as a byte string.
        :param data: The data that will be encrypted.
        :return: The encrypted data.
        """

        # Derive our key using master password and salt
        key = self.__derive_key(master_password_encoded, self.hashing_params)

        # Encrypt the data
        fernet = Fernet(key)
        data = data.encode('utf-8')
        data_encrypted = fernet.encrypt(data)

        return data_encrypted

    def decrypt(self, master_password_encoded, data):
        """Decrypts data using the master password and salt.

        :param master_password_encoded: The master password as a byte string.
        :param data: The data that will be decrypted.
        :return: The decrypted data.
        """

        # Derive our key using master password and salt
        key = self.__derive_key(master_password_encoded, self.hashing_params)

        # Decrypt the data
        fernet = Fernet(key)
        data = data.encode('utf-8')
        data_decrypted = fernet.decrypt(data)

        return data_decrypted

    def check_hashing_params(self, settings_data, check_mismatch=True):
        """Checks for updated password hashing paramters and prompts the user
        to upgrade their password encryption if new settings are available.
        Optionally set check_mismatch to False to skip checking for new
        hashing parameters and instead return the currently used ones.

        :param settings_data: The settings from launcher.json
                              using json.load().
        :param check_mismatch: For checking if there is a mismatch in
                               launcher.json's hashing parameters compared
                               to what is expected. If a mismatch is found,
                               everything is re-encrypted with the parameters
                               defined by self.hashing_params.
        :return: A dict containing argon parameters t, m, p or False if
                 too many password attempts were made during upgrade.
        """

        argon_t_cur = 0
        argon_m_cur = 0
        argon_p_cur = 0

        if 'hashing-params' in settings_data['launcher']:
            # Fetch current parameters
            try:
                argon_t_cur = settings_data['launcher']['hashing-params']['t']
                argon_m_cur = settings_data['launcher']['hashing-params']['m']
                argon_p_cur = settings_data['launcher']['hashing-params']['p']
            except KeyError:
                print(
                    'Invalid hashing settings in launcher.json. '
                    'You will need to delete the launcher.json file '
                    'and start over.\n')
                helper.quit_launcher()

        if check_mismatch:
            # Fetch required argon parameters
            argon_t = self.hashing_params['t']
            argon_m = self.hashing_params['m']
            argon_p = self.hashing_params['p']

            # Compare with what is in settings_data
            # If there is a mismatch, decrypt everything and re-encrypt
            mismatch = False
            if argon_t != argon_t_cur:
                mismatch = True
            if argon_m != argon_m_cur:
                mismatch = True
            if argon_p != argon_p_cur:
                mismatch = True

            if mismatch:
                # Need to re-encrypt all data with required parameters
                print(
                    'To improve security your passwords will need to be '
                    're-encrypted.')

                # Get the master password
                master_password_encoded = self.verify_master_password(
                    settings_data)

                # Too many password attempts
                if not master_password_encoded:
                    return False

                # Decrypt everything using the current parameters
                self.__decrypt_accounts(
                    master_password_encoded, settings_data,
                    {'t': argon_t_cur, 'm': argon_m_cur, 'p': argon_p_cur})

                # Store new hashing params
                settings_data['launcher']['hashing-params'] = {
                    't': argon_t,
                    'm': argon_m,
                    'p': argon_p
                }

                # Re-encrypt using the new parameters
                self.manage_password_encryption(settings_data, True)
        else:
            # Just return the current parameters
            return {'t': argon_t_cur, 'm': argon_m_cur, 'p': argon_p_cur}

        return {'t': argon_t, 'm': argon_m, 'p': argon_p}

    def verify_master_password(
            self, settings_data,
            msg='\nYou have made too many password attempts.'):
        """Used for verifying the user's master password. It will ask the user
        to confirm their password and does this by attempting to decrypt the
        test value in settings_data['launcher']['password-verification'].

        :param settings_data: The settings from launcher.json
                              using json.load().
        :param msg: The message to print when too many passwords were entered.
        :return: The master password encoded as a UTF-8 byte string on success
                 or False if the user enters the password incorrect 3 times.
        """

        bad_password = 0
        while bad_password < 3:
            try:
                # Ask user for their master password and encode it
                master_password = pwinput.pwinput(
                    'Enter your master password: ')
                master_password_encoded = master_password.encode('utf-8')

                # Derive our key using master password and salt
                hashing_params = self.check_hashing_params(
                    settings_data, check_mismatch=False)
                key = self.__derive_key(
                    master_password_encoded, hashing_params)

                # Try to decrypt the test value in password-verification
                test = settings_data[
                    'launcher']['password-verification'].encode('utf-8')
                fernet = Fernet(key)
                fernet.decrypt(test)
            except InvalidToken:
                print('The password entered was incorrect.')
                bad_password += 1
            else:
                break

        if bad_password == 3:
            print(msg)
            return False

        return master_password_encoded
