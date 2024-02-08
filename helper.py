#!/usr/bin/env python3

"""This module contains some common helper functions that the other
modules share.
"""

import os
import platform
import sys
import time
import json

if platform.system() == 'Windows':
    import winreg


def load_login_json():
    """Loads the login.json settings file and creates one if it doesn't
    exist.

    :return: The settings from login.json using json.load().
    """

    try:
        login_json = os.path.join(get_launcher_path(), 'login.json')
        with open(login_json, encoding='utf-8') as settings_file:
            settings_data = json.load(settings_file)
    except FileNotFoundError:
        # Set a default TTR installation directory
        try:
            if platform.system() == 'Windows':
                reg_key = (r'SOFTWARE\Microsoft\Windows\CurrentVersion'
                           r'\App Paths\Launcher.exe')
                ttr_dir = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE, reg_key)
                ttr_dir = ttr_dir.replace('Launcher.exe', '')
                ttr_dir = ttr_dir.rstrip('/\\')
            else:
                ttr_dir = os.path.join(
                    get_launcher_path(), 'Toontown Rewritten')
        except OSError:
            ttr_dir = os.path.join(get_launcher_path(), 'Toontown Rewritten')

        # Set default login.json content
        json_data = {
                        "accounts": {
                        },
                        "launcher": {
                            "ttr-dir": ttr_dir,
                            "use-stored-accounts": True
                        }
                    }

        # Create login.json
        update_login_json(json_data)

        # File was created successfully, reload it
        settings_data = load_login_json()
    except json.decoder.JSONDecodeError as ex:
        print(f'Badly formatted login.json file.\n{ex}')
        print('\nIf unsure how to fix, delete the login.json file and '
              'restart the launcher.')
        quit_launcher()
    except OSError as ex:
        print(f'File IO Error.\n{ex}')
        quit_launcher()

    return settings_data


def update_login_json(settings_data):
    """Updates the login.json settings file with the settings_data object.

    :param settings_data: The settings from login.json using json.load().
    """

    # Open file and write json
    try:
        login_json = os.path.join(get_launcher_path(), 'login.json')
        with open(login_json, 'w', encoding='utf-8') as settings_file:
            json.dump(settings_data, settings_file, indent=4)
    except OSError as ex:
        print(f'Failed to write login.json.\n{ex}')
        quit_launcher()


def get_launcher_path():
    """Gets path to the running launcher's directory.

    :return: The path to the launcher.
    """

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        launcher_path = os.path.dirname(sys.executable)
    else:
        launcher_path = os.path.dirname(os.path.abspath(__file__))

    return launcher_path


def confirm(text, lower_bound, upper_bound):
    """Helper function for selecting a numerical choice from the end user.

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
    """Nicely quit the launcher.

    :param ret: The return value, defaults to 0.
    """

    input('Press enter to quit.')
    sys.exit(ret)


def retry(count, interval, callback, **kwargs):
    """Wrapper function to try executing a function a certain number of times
    at an interval in seconds. To trigger a failed attempt the callback
    must return a falsy value or raise an exception. None is not treated as
    failure.

    :param count: The amount of times to try executing a function.
    :param interval: The amount of seconds to wait between each attempt.
    :param callback: The callback function.
    :param **kwargs: The arguments for the callback function.
    :return: The result of the callback.
    """

    exception = None
    attempt = 0

    while attempt < count:
        try:
            result = callback(**kwargs)
            if result is None:
                break
            if not result:
                if attempt < count:
                    print('Retrying...')
                    time.sleep(interval)
            else:
                break
        except Exception as ex:
            exception = ex
            if attempt < count:
                print('Retrying...')
                time.sleep(interval)
        attempt += 1

    if exception:
        raise exception

    return result
