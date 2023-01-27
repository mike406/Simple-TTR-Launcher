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

"""
Handles password encryption for the launcher.
It uses a user-created master password to encrypt their stored account info.
"""

import os
import base64
import pwinput
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import helper


def manage_password_encryption(settings_data):
    """
    Allows the user to enable or disable password encryption.

    :param settings_data: The settings from login.json using json.load().
    """

    if settings_data['launcher']['use-password-encryption']:
        print('Would you like to remove password encryption?')
        print(
            'WARNING: Your existing passwords will revert to an unencrypted '
            'state! Please make sure you are okay with this.'
        )
        remove_encryption = helper.confirm(
            'Enter 1 to confirm or 0 for Main Menu: ', 0, 1
        )

        if remove_encryption == 0:
            print()

        # Verify master password and decrypt all accounts if correct
        if remove_encryption == 1:
            master_password_encoded = verify_master_password(
                settings_data, '\nYou made too many password attempts. '
                               'No changes have been made.\n'
            )

            if master_password_encoded:
                print('Decrypting your accounts...')
                salt = get_salt(settings_data)
                settings_data = decrypt_accounts(
                    master_password_encoded, salt, settings_data
                )
                print(
                    '\nYour accounts have been decrypted '
                    'and the master password has been removed.\n'
                )
    else:
        print(
            'You can use a master password to encrypt your stored accounts.'
            '\nYou will need to enter this password each time the launcher '
            'starts.\nYou can turn this feature off (and decrypt your '
            'passwords) by choosing the option again from the Main Menu.'
        )

        # Create the master password
        master_password = pwinput.pwinput('Create a master password: ')
        master_password_encoded = master_password.encode('utf-8')

        # Create a new salt
        salt = os.urandom(16)

        # Store the salt in base64 as we'll need it to derive the same key
        settings_data['launcher']['use-password-encryption'] = True
        settings_data['launcher']['password-salt'] = base64.urlsafe_b64encode(
            salt
        ).decode('utf-8')

        # Encrypt any existing accounts using the key
        print('Encrypting your accounts...')
        settings_data = encrypt_accounts(
            master_password_encoded, salt, settings_data
        )
        print(
            '\nYour master password has been set and any '
            'existing account passwords are now encrypted.\n'
        )

    helper.update_login_json(settings_data)


def encrypt(master_password_encoded, salt, data):
    """
    Encrypts data using the master password and salt.

    :param master_password_encoded: The master password as a byte string.
    :param salt: The salt as a byte string.
    :param data: The data that will be encrypted.
    :return: The encrypted data.
    """

    # Derive our key using master password and salt
    key = derive_key(master_password_encoded, salt)

    # Encrypt the data
    fernet = Fernet(key)
    data = data.encode('utf-8')
    data_encrypted = fernet.encrypt(data)

    return data_encrypted


def decrypt(master_password_encoded, salt, data):
    """
    Decrypts data using the master password and salt.

    :param master_password_encoded: The master password as a byte string.
    :param salt: The salt as a byte string.
    :param data: The data that will be decrypted.
    :return: The decrypted data.
    """

    # Derive our key using master password and salt
    key = derive_key(master_password_encoded, salt)

    # Decrypt the data
    fernet = Fernet(key)
    data = data.encode('utf-8')
    data_decrypted = fernet.decrypt(data)

    return data_decrypted


def encrypt_accounts(master_password_encoded, salt, settings_data):
    """
    Encrypts all currently stored accounts using the master password and salt.

    :param master_password_encoded: The master password as a byte string.
    :param salt: The salt as a byte string.
    :param settings_data: The settings from login.json using json.load().
    :return: The updated settings_data object.
    """

    num_accounts = len(settings_data['accounts'])

    # Derive our key using master password and salt
    key = derive_key(master_password_encoded, salt)

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


def decrypt_accounts(master_password_encoded, salt, settings_data):
    """
    Decrypts all currently stored accounts using the master password and salt.

    :param master_password_encoded: The master password as a byte string.
    :param salt: The salt as a byte string.
    :param settings_data: The settings from login.json using json.load().
    :return: The updated settings_data object.
    """

    num_accounts = len(settings_data['accounts'])

    # Derive our key using master password and salt
    key = derive_key(master_password_encoded, salt)

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


def derive_key(master_password_encoded, salt):
    """
    Wrapper function for deriving the key using the master password and salt.

    :param master_password_encoded: The master password as a byte string.
    :param salt: The salt as a byte string.
    :return: The derived key.
    """

    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    key = base64.urlsafe_b64encode(kdf.derive(master_password_encoded))

    return key


def get_salt(settings_data):
    """
    Retrieves the stored salt used for the encryption.

    :param settings_data: The settings from login.json using json.load().
    :return: The stored salt in settings_data.
    """

    return base64.urlsafe_b64decode(settings_data['launcher']['password-salt'])


def verify_master_password(
        settings_data, msg='\nYou have made too many password attempts.\n'):
    """
    Used for verifying the user's master password. It will ask the user to
    confirm their password and does this by attempting to decrypt the test
    value in settings_data['launcher']['password-verification'].

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
            key = derive_key(master_password_encoded, salt)

            # Try to decrypt the test value in password-verification
            test = settings_data['launcher']['password-verification'].encode(
                'utf-8'
            )
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
