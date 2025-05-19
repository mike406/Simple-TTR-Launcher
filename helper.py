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


def load_launcher_json():
    """Loads the launcher.json settings file and creates one if it doesn't
    exist.

    :return: The settings from launcher.json using json.load().
    """

    try:
        if os.path.exists('login.json'):
            os.rename('login.json', 'launcher.json')

        launcher_json = os.path.join(get_launcher_path(), 'launcher.json')
        with open(launcher_json, encoding='utf-8') as settings_file:
            settings_data = json.load(settings_file)
            fix_settings_data(settings_data)
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

        # Set default launcher.json content
        json_data = {
                        "accounts": {
                        },
                        "launcher": {
                            "ttr-dir": ttr_dir,
                            "use-stored-accounts": False,
                            "use-password-encryption": False,
                            "display-logging": False
                        }
                    }

        # Create launcher.json
        update_launcher_json(json_data)

        # File was created successfully, reload it
        settings_data = load_launcher_json()
    except json.decoder.JSONDecodeError as ex:
        print(f'Badly formatted launcher.json file.\n{ex}')
        print('\nIf unsure how to fix, delete the launcher.json file and '
              'restart the launcher.')
        quit_launcher()
    except OSError as ex:
        print(f'File IO Error.\n{ex}')
        quit_launcher()

    return settings_data


def update_launcher_json(settings_data):
    """Updates the launcher.json settings file with the settings_data object.

    :param settings_data: The settings from launcher.json using json.load().
    """

    # Open file and write json
    try:
        launcher_json = os.path.join(get_launcher_path(), 'launcher.json')
        with open(launcher_json, 'w', encoding='utf-8') as settings_file:
            json.dump(settings_data, settings_file, indent=4)
    except OSError as ex:
        print(f'Failed to write launcher.json.\n{ex}')
        quit_launcher()


def fix_settings_data(settings_data):
    """Runs known fixes on settings_data.
    Fixes applied:
    - Run os.path.expandpath() on ttr-dir if path starts with a ~

    :param settings_data: The settings from launcher.json using json.load().
    """

    updated = False

    ttr_dir = settings_data['launcher']['ttr-dir']
    if ttr_dir[0] == '~':
        updated = True
        settings_data['launcher']['ttr-dir'] = os.path.expanduser(ttr_dir)

    if 'use-password-encryption' not in settings_data['launcher']:
        updated = True
        settings_data['launcher']['use-password-encryption'] = False

    if 'use-stored-accounts' not in settings_data['launcher']:
        updated = True
        settings_data['launcher']['use-stored-accounts'] = False

    if 'display-logging' not in settings_data['launcher']:
        updated = True
        settings_data['launcher']['display-logging'] = False

    if updated:
        update_launcher_json(settings_data)


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


def retry(count, interval, callback, print_retries=True, **kwargs):
    """Wrapper function to try executing a function a certain number of times
    at an interval in seconds. To trigger a failed attempt the callback
    must return a falsy value or raise an exception. None is not treated as
    failure.

    :param count: The amount of times to try executing a function.
    :param interval: The amount of seconds to wait between each attempt.
    :param callback: The callback function.
    :param print_retries: Show or hide Retrying message.
    :param **kwargs: The arguments for the callback function.
    :return: The result of the callback.
    """

    attempt = 0

    while attempt < count:
        exception = None
        try:
            result = callback(**kwargs)
            if result is None:
                break
            if not result:
                if attempt < count:
                    if print_retries:
                        print('Retrying...')
                    time.sleep(interval)
            else:
                break
        except Exception as ex:
            exception = ex
            if attempt < count:
                if print_retries:
                    print('Retrying...')
                time.sleep(interval)
        attempt += 1

    if exception:
        raise exception

    return result


def clear():
    """Clear the console"""

    if sys.platform == 'win32':
        os.system('cls')
    else:
        os.system('clear')
