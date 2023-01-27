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
This module contains some common helper functions that the other modules share.
"""

import os
import platform
import sys
import json

if platform.system() == 'Windows':
    import winreg


def load_login_json():
    """
    Loads the login.json settings file and creates one if it doesn't exist.

    :return: The settings from login.json using json.load().
    """
    try:
        login_json = os.path.join(get_launcher_path(), 'login.json')
        with open(login_json, encoding='utf-8') as settings_file:
            settings_data = json.load(settings_file)
    except FileNotFoundError:
        # Create new settings file
        if platform.system() == 'Windows':
            try:
                reg_key = (r'SOFTWARE\Microsoft\Windows\CurrentVersion'
                           r'\App Paths\Launcher.exe')
                ttr_dir = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE, reg_key)
                ttr_dir = ttr_dir.replace('Launcher.exe', '')
                ttr_dir = ttr_dir.rstrip('/\\')
            except OSError:
                ttr_dir = 'C:/Program Files/Toontown Rewritten'
        else:
            ttr_dir = input('Please enter your desired installation path: ')

        json_data = {
                        "accounts": {
                        },
                        "launcher": {
                            "ttr-dir": ttr_dir,
                            "use-stored-accounts": True
                        }
                    }

        update_login_json(json_data)

        # File was created successfully, reload it
        settings_data = load_login_json()
    except json.decoder.JSONDecodeError as ex:
        print('Badly formatted login.json file.\n' + str(ex))
        print('\nIf unsure how to fix, delete the login.json file and '
              'restart the launcher.\n')
        quit_launcher()
    except OSError as ex:
        print('File IO Error.\n' + str(ex) + '\n')
        quit_launcher()

    return settings_data


def update_login_json(settings_data):
    """
    Updates the login.json settings file with the settings_data object.

    :param settings_data: The settings from login.json using json.load().
    """

    # Open file and write json
    try:
        login_json = os.path.join(get_launcher_path(), 'login.json')
        with open(login_json, 'w', encoding='utf-8') as settings_file:
            json.dump(settings_data, settings_file, indent=4)
    except OSError as ex:
        print('Failed to write login.json.\n' + str(ex))
        quit_launcher()


def get_launcher_path():
    """
    Gets path to the running launcher's directory.

    :return: The path to the launcher.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        launcher_path = os.path.dirname(sys.executable)
    else:
        launcher_path = os.path.dirname(os.path.abspath(__file__))

    return launcher_path


def confirm(text, lower_bound, upper_bound):
    """
    Helper function for selecting a numerical choice from the end user.

    :param text: The text to display in the input prompt.
    :param lower_bound: The lowest possible numerical option.
    :param upper_bound: The highest possible numerical option.
    """

    while True:
        try:
            selection = int(input(text))
        except ValueError:
            print('Invalid choice. Try again.')
            continue
        else:
            if selection < lower_bound or selection > upper_bound:
                print('Invalid choice. Try again.')
                continue
            break

    return selection


def quit_launcher(ret=0):
    """
    Nicely quit the launcher.

    :param ret: The return value, defaults to 0.
    """

    input('Press enter to quit.')
    sys.exit(ret)
