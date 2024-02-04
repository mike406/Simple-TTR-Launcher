#!/usr/bin/env python3

# Copyright (C) 2023 Michael Luck
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

"""Handles password encryption for the launcher.
It uses a user-created master password to encrypt their stored account info.
"""

import os
import base64
import pwinput
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import helper


def manage_password_encryption(settings_data, upgrade=False):
    """Allows the user to enable or disable password encryption.

    :param settings_data: The settings from login.json using json.load().
    :param upgrade: Suppresses some message output when upgrading hashing.
    """

    if settings_data['launcher']['use-password-encryption']:
        print('Would you like to remove password encryption?')
        print(
            'WARNING: Your existing passwords will revert to an unencrypted '
            'state! Please make sure you are okay with this.')
        remove_encryption = helper.confirm(
            'Enter 1 to confirm or 0 for Main Menu: ', 0, 1)

        # Verify master password and decrypt all accounts if correct
        if remove_encryption == 1:
            master_password_encoded = verify_master_password(
                settings_data, '\nYou made too many password attempts. '
                               'No changes have been made.')

            if master_password_encoded:
                print('Decrypting your accounts...')
                salt = get_salt(settings_data)
                settings_data = decrypt_accounts(
                    master_password_encoded, salt, settings_data,
                    get_hashing_params())
                print(
                    '\nYour accounts have been decrypted '
                    'and the master password has been removed.')
    else:
        if not upgrade:
            print(
                'You can use a master password to encrypt your stored '
                'accounts.\n'
                'You will need to enter this password each time the launcher '
                'starts.\n'
                'You can turn this feature off (and decrypt your '
                'passwords) by choosing the option again from the Main Menu.')

        # Create the master password
        master_password = pwinput.pwinput('Create a master password: ')
        master_password_encoded = master_password.encode('utf-8')

        # Create a new salt
        salt = os.urandom(16)

        # Store the salt in base64 as we'll need it to derive the same key
        settings_data['launcher']['use-password-encryption'] = True
        settings_data['launcher']['password-salt'] = base64.urlsafe_b64encode(
            salt).decode('utf-8')

        # Encrypt any existing accounts using the key
        print('Encrypting your accounts...')
        settings_data = encrypt_accounts(
            master_password_encoded, salt, settings_data)
        print(
            '\nYour master password has been set and any '
            'existing account passwords are now encrypted.')

    helper.update_login_json(settings_data)


def encrypt(master_password_encoded, salt, data):
    """Encrypts data using the master password and salt.

    :param master_password_encoded: The master password as a byte string.
    :param salt: The salt as a byte string.
    :param data: The data that will be encrypted.
    :return: The encrypted data.
    """

    # Derive our key using master password and salt
    key = derive_key(master_password_encoded, salt, get_hashing_params())

    # Encrypt the data
    fernet = Fernet(key)
    data = data.encode('utf-8')
    data_encrypted = fernet.encrypt(data)

    return data_encrypted


def decrypt(master_password_encoded, salt, data):
    """Decrypts data using the master password and salt.

    :param master_password_encoded: The master password as a byte string.
    :param salt: The salt as a byte string.
    :param data: The data that will be decrypted.
    :return: The decrypted data.
    """

    # Derive our key using master password and salt
    key = derive_key(master_password_encoded, salt, get_hashing_params())

    # Decrypt the data
    fernet = Fernet(key)
    data = data.encode('utf-8')
    data_decrypted = fernet.decrypt(data)

    return data_decrypted


def encrypt_accounts(master_password_encoded, salt, settings_data):
    """Encrypts all currently stored accounts using the master password
    and salt.

    :param master_password_encoded: The master password as a byte string.
    :param salt: The salt as a byte string.
    :param settings_data: The settings from login.json using json.load().
    :return: The updated settings_data object.
    """

    num_accounts = len(settings_data['accounts'])

    # Set Scrypt parameters
    (scrypt_n, scrypt_r, scrypt_p) = get_hashing_params()
    settings_data['launcher']['hashing-params'] = {
        'n': scrypt_n,
        'r': scrypt_r,
        'p': scrypt_p
    }

    # Derive our key using master password and salt
    key = derive_key(master_password_encoded, salt, get_hashing_params())

    # Use Fernet class to encrypt each password using our key
    fernet = Fernet(key)

    # Encrypt all existing account passwords
    for num in range(num_accounts):
        acc = f'account{num + 1}'
        password = settings_data['accounts'][acc]['password'].encode('utf-8')
        password_encrypted = fernet.encrypt(password).decode('utf-8')
        settings_data['accounts'][acc]['password'] = password_encrypted

    # Save encrypted version of the salt. This will be used for verification.
    salt = settings_data['launcher']['password-salt'].encode('utf-8')
    salt_encrypted = fernet.encrypt(salt).decode('utf-8')
    settings_data['launcher']['password-verification'] = salt_encrypted

    return settings_data


def decrypt_accounts(
        master_password_encoded, salt, settings_data, hashing_params=None):
    """Decrypts all currently stored accounts using the master password
    and salt.

    :param master_password_encoded: The master password as a byte string.
    :param salt: The salt as a byte string.
    :param settings_data: The settings from login.json using json.load().
    :param hashing_params: Hashing parameters for Scrypt as a tuple.
    :return: The updated settings_data object.
    """

    num_accounts = len(settings_data['accounts'])

    # Derive our key using master password and salt
    key = derive_key(master_password_encoded, salt, hashing_params)

    # Use Fernet class to decrypt each password using our key
    fernet = Fernet(key)

    # Decrypt all existing account passwords
    for num in range(num_accounts):
        acc = f'account{num + 1}'
        password = settings_data['accounts'][acc]['password'].encode('utf-8')
        password_decrypted = fernet.decrypt(password).decode('utf-8')
        settings_data['accounts'][acc]['password'] = password_decrypted

    settings_data['launcher']['use-password-encryption'] = False
    del settings_data['launcher']['password-salt']
    del settings_data['launcher']['password-verification']

    return settings_data


def derive_key(master_password_encoded, salt, hashing_params):
    """Wrapper function for deriving the key using the master password
    and salt.

    :param master_password_encoded: The master password as a byte string.
    :param salt: The salt as a byte string.
    :param hashing_params: Hashing parameters for Scrypt as a tuple.
    :return: The derived key.
    """

    (scrypt_n, scrypt_r, scrypt_p) = hashing_params

    kdf = Scrypt(salt=salt, length=32, n=scrypt_n, r=scrypt_r, p=scrypt_p)
    key = base64.urlsafe_b64encode(kdf.derive(master_password_encoded))

    return key


def check_hashing_params(
        master_password_encoded, salt, settings_data, check_mismatch=True):
    """Checks for updated password hashing paramters and prompts the user to
    upgrade their password encryption if new settings are available.
    Optionally set check_mismatch to False to skip checking for new
    hashing parameters and instead return the currently used ones.

    :param master_password_encoded: The master password as a byte string.
    :param salt: The salt as a byte string.
    :param settings_data: The settings from login.json using json.load().
    :param check_mismatch: For checking if there is a mismatch in login.json's
                           hashing parameters compared to what is expected.
    :return: A tuple containing Scrypt parameters N, r, p.
    """
    if 'hashing-params' in settings_data['launcher']:
        # Fetch current parameters
        try:
            scrypt_n_cur = settings_data['launcher']['hashing-params']['n']
            scrypt_r_cur = settings_data['launcher']['hashing-params']['r']
            scrypt_p_cur = settings_data['launcher']['hashing-params']['p']
        except KeyError:
            print(
                'Invalid hashing settings in login.json. '
                'You will need to delete the login.json file '
                'and start over.\n')
            helper.quit_launcher()
    else:
        # Use legacy default to maintain compatibility with older launcher
        scrypt_n_cur = 2**14
        scrypt_r_cur = 8
        scrypt_p_cur = 1

    if check_mismatch:
        # Fetch required Scrypt parameters
        (scrypt_n, scrypt_r, scrypt_p) = get_hashing_params()

        # Compare with what is in settings_data
        # If there is a mismatch, decrypt everything and re-encrypt
        mismatch = False
        if scrypt_n != scrypt_n_cur:
            mismatch = True
        if scrypt_r != scrypt_r_cur:
            mismatch = True
        if scrypt_p != scrypt_p_cur:
            mismatch = True

        if mismatch:
            # Need to re-encrypt all data with newest parameters
            print(
                'To improve security your data will need to be re-encrypted.')

            # Store new hashing params
            settings_data['launcher']['hashing-params'] = {
                'n': scrypt_n,
                'r': scrypt_r,
                'p': scrypt_p
            }

            # Decrypt everything using the current parameters
            decrypt_accounts(
                master_password_encoded, salt, settings_data,
                (scrypt_n_cur, scrypt_r_cur, scrypt_p_cur))

            # Re-encrypt using the new parameters
            manage_password_encryption(settings_data, True)
            salt = get_salt(settings_data)
    else:
        # Just return the current parameters
        return (scrypt_n_cur, scrypt_r_cur, scrypt_p_cur)

    return (scrypt_n, scrypt_r, scrypt_p)


def get_hashing_params():
    """Retrieves required N, r and p parameters for Scrypt.

    :return: A tuple containing Scrypt parameters N, r, p
    """

    return (2**17, 8, 1)


def get_salt(settings_data):
    """
    Retrieves the stored salt used for the encryption.

    :param settings_data: The settings from login.json using json.load().
    :return: The stored salt in settings_data.
    """

    return base64.urlsafe_b64decode(settings_data['launcher']['password-salt'])


def verify_master_password(
        settings_data, msg='\nYou have made too many password attempts.'):
    """Used for verifying the user's master password. It will ask the user to
    confirm their password and does this by attempting to decrypt the test
    value in settings_data['launcher']['password-verification'].

    :param settings_data: The settings from login.json using json.load().
    :param msg: The message to print when too many passwords were entered.
    :return: The master password encoded as a UTF-8 byte string on success
             or False if the user enters the password incorrect 3 times.
    """

    bad_password = 0
    while bad_password < 3:
        try:
            # Ask user for their master password and encode it
            master_password = pwinput.pwinput('Enter your master password: ')
            master_password_encoded = master_password.encode('utf-8')

            # Derive our key using master password and salt
            salt = get_salt(settings_data)
            hashing_params = check_hashing_params(
                None, salt, settings_data, False)
            key = derive_key(master_password_encoded, salt, hashing_params)

            # Try to decrypt the test value in password-verification
            test = settings_data['launcher']['password-verification'].encode(
                'utf-8')
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
