"""Handles password encryption for the launcher.
It uses a user-created master password to encrypt account passwords.
The KDF used currently is argon2id and is used with Fernet
to encrypt passwords. The parameters used for argon2id are as defined in
RFC 9106 using the second recommended option for better compatibility with
devices that have lower amounts of memory.
https://www.rfc-editor.org/rfc/rfc9106.html#section-4-6.2
"""

import os
import base64
import pwinput
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
import helper


class Encrypt:
    """Password encryption class for the launcher."""

    def __init__(self, settings_data):
        """Initialize Encrypt class and store salt if it exists."""

        self.salt_length = 16
        self.hash_length = 32
        self.hashing_params = {
            't': 3,
            'm': 65536,
            'p': 4
        }

        # If settings_data['password-salt'] exists, upgrade to the new format
        if 'password-salt' in settings_data['launcher']:
            print(
                'To improve security your passwords will need to be '
                're-encrypted.')

            master_password_encoded = self.verify_master_password(
                settings_data)
            if not master_password_encoded:
                helper.quit_launcher()

            num_accounts = len(settings_data['accounts'])
            old_salt = settings_data['launcher']['password-salt']

            # Decrypt existing passwords
            for num in range(num_accounts):
                acc = f'account{num + 1}'
                password = settings_data['accounts'][acc]['password']
                password_decrypted = self.decrypt(
                    master_password_encoded, password, old_salt, settings_data['launcher']['hashing-params'])
                settings_data['accounts'][acc]['password'] = password_decrypted

            # Reset password encryption settings
            settings_data['launcher']['use-password-encryption'] = False
            del settings_data['launcher']['password-salt']
            del settings_data['launcher']['password-verification']

            # Re-encrypt passwords
            self.manage_password_encryption(settings_data, upgrade=True)

        # Check for new hashing params
        if settings_data['launcher']['use-password-encryption']:
            if not self.check_hashing_params(settings_data):
                # Wrong password entered too many times
                helper.quit_launcher()

    def __encrypt_accounts(self, master_password_encoded, settings_data):
        """Encrypts all currently stored accounts using the master password
        and salt.

        :param master_password_encoded: The master password as a byte string.
        :param settings_data: The settings from launcher.json
                              using json.load().
        :return: The updated settings_data object.
        """

        num_accounts = len(settings_data['accounts'])

        # Set new hashing parameters
        settings_data['launcher']['hashing-params'] = dict(self.hashing_params)

        # Encrypt all existing account passwords
        for num in range(num_accounts):
            # Generate a new salt
            salt = os.urandom(self.salt_length)

            # Derive our key using master password and salt
            key = self.__derive_key(
                master_password_encoded, salt, self.hashing_params)

            # Use Fernet class to encrypt each password using our key
            fernet = Fernet(key)

            # Get account username
            acc = f'account{num + 1}'
            username = settings_data['accounts'][acc]['username']

            # Get current password
            if settings_data['launcher']['use-os-keyring']:
                password = helper.get_keyring_password(username).encode(
                    'utf-8')
            else:
                password = settings_data['accounts'][acc]['password'].encode(
                    'utf-8')

            # Encrypt the current password
            password_encrypted = fernet.encrypt(password).decode('utf-8')

            # Store the encrypted password depending on which method is in use
            if settings_data['launcher']['use-os-keyring']:
                helper.add_keyring_account(username, password_encrypted)
                settings_data['accounts'][acc]['password'] = 'KEYRING_PASS'
            else:
                settings_data['accounts'][acc]['password'] = password_encrypted

            # Store the salt for this account in base64
            settings_data['accounts'][acc]['salt'] = base64.urlsafe_b64encode(
                salt).decode('utf-8')

        settings_data['launcher']['use-password-encryption'] = True

        # Generate a salt for password verification
        verification_salt = os.urandom(self.salt_length)
        settings_data[
            'launcher']['salt-verification'] = base64.urlsafe_b64encode(
                verification_salt).decode('utf-8')

        key = self.__derive_key(
            master_password_encoded, verification_salt, self.hashing_params)
        fernet = Fernet(key)

        # Encrypt the bytes and store them for password verification
        encrypted_bytes = fernet.encrypt(verification_salt).decode('utf-8')
        settings_data['launcher']['password-verification'] = encrypted_bytes

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

        # Decrypt all existing account passwords
        for num in range(num_accounts):
            # Get account
            acc = f'account{num + 1}'

            # Get account salt
            salt = base64.urlsafe_b64decode(
                settings_data['accounts'][acc]['salt'])

            # Derive our key using master password and salt
            key = self.__derive_key(
                master_password_encoded, salt, hashing_params)

            # Use Fernet class to decrypt each password using our key
            fernet = Fernet(key)

            # Get the current password
            if settings_data['launcher']['use-os-keyring']:
                username = settings_data['accounts'][acc]['username']
                password = helper.get_keyring_password(username).encode(
                    'utf-8')
            else:
                password = settings_data['accounts'][acc]['password'].encode(
                    'utf-8')

            # Decrypt the current password
            password_decrypted = fernet.decrypt(password).decode('utf-8')

            # Store the decrypted password depending on which method is in use
            if settings_data['launcher']['use-os-keyring']:
                helper.add_keyring_account(username, password_decrypted)
            else:
                settings_data['accounts'][acc]['password'] = password_decrypted

            # Delete the account salt
            del settings_data['accounts'][acc]['salt']

        settings_data['launcher']['use-password-encryption'] = False
        del settings_data['launcher']['password-verification']
        del settings_data['launcher']['salt-verification']

        return settings_data

    def __derive_key(self, master_password_encoded, salt, hashing_params):
        """Wrapper function for deriving the key using the master password
        and salt.

        :param master_password_encoded: The master password as a byte string.
        :param salt: The salt for the KDF.
        :param hashing_params: Hashing parameters for argon as a dict.
        :return: The derived key.
        """

        kdf = Argon2id(
            salt=salt,
            length=self.hash_length,
            iterations=hashing_params['t'],
            memory_cost=hashing_params['m'],
            lanes=hashing_params['p'])

        key = kdf.derive(master_password_encoded)

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
                    'passwords) by going to "Launcher settings" in the '
                    'Main Menu.')

            # Create the master password
            master_password = pwinput.pwinput('Create a master password: ')
            master_password_encoded = master_password.encode('utf-8')

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
        :return: The encrypted data and salt as a tuple.
        """
        # Generate a new salt
        salt = os.urandom(self.salt_length)
        salt_encoded = base64.urlsafe_b64encode(salt).decode('utf-8')

        # Derive our key using master password and salt
        key = self.__derive_key(
            master_password_encoded, salt, self.hashing_params)

        # Encrypt the data
        fernet = Fernet(key)
        data = data.encode('utf-8')
        data_encrypted = fernet.encrypt(data).decode('utf-8')

        return (data_encrypted, salt_encoded)

    def decrypt(self, master_password_encoded, data, salt, hashing_params=None):
        """Decrypts data using the master password and salt.

        :param master_password_encoded: The master password as a byte string.
        :param data: The data that will be decrypted.
        :param salt: The salt associated with the encrypted data.
        :return: The decrypted data.
        """

        if hashing_params is None:
            hashing_params = self.hashing_params

        # Decode the salt
        salt_decoded = base64.urlsafe_b64decode(salt)

        # Derive our key using master password and salt
        key = self.__derive_key(
            master_password_encoded, salt_decoded, hashing_params)

        # Decrypt the data
        fernet = Fernet(key)
        data = data.encode('utf-8')
        data_decrypted = fernet.decrypt(data).decode('utf-8')

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
                current_hashing_parameters = {
                    't': argon_t_cur,
                    'm': argon_m_cur,
                    'p': argon_p_cur
                }

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
                    current_hashing_parameters)

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

        # Get current hashing params
        hashing_params = self.check_hashing_params(
            settings_data, check_mismatch=False)

        # Get the verification salt
        if 'password-salt' in settings_data['launcher']:
            verification_salt = base64.urlsafe_b64decode(
                settings_data['launcher']['password-salt'])
        else:
            verification_salt = base64.urlsafe_b64decode(
                settings_data['launcher']['salt-verification'])

        # Encode the test data for later decryption
        test_data = settings_data[
            'launcher']['password-verification'].encode('utf-8')

        bad_password = 0
        while bad_password < 3:
            try:
                # Ask user for their master password and encode it
                master_password = pwinput.pwinput(
                    'Enter your master password: ')
                master_password_encoded = master_password.encode('utf-8')

                # Derive our key using master password and salt
                key = self.__derive_key(
                    master_password_encoded, verification_salt, hashing_params)

                # Try to decrypt the test data in password-verification
                fernet = Fernet(key)
                fernet.decrypt(test_data)
            except InvalidToken:
                print('The password entered was incorrect.')
                bad_password += 1
            else:
                break

        if bad_password == 3:
            print(msg)
            return False

        return master_password_encoded
