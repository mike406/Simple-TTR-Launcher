#!/usr/bin/env python3

"""Sets up the STTRL menu and launcher."""

import sys
import webbrowser
import helper
from launcher import Launcher


def show_menu(launcher, redraw=True):
    """Displays the Main Menu of the launcher.

    :param launcher: A Launcher object.
    :param redraw: Flag to redraw the menu.
    :return: The new redraw status flag.
    """

    version = 'v3.3'

    # Menu items
    menu = {
        1: 'Play',
        2: 'Add an account',
        3: 'Change a stored password',
        4: 'Remove an account',
        5: 'Launcher settings',
        6: 'Toontown Rewritten website',
        7: 'Toontown Rewritten server status',
        8: 'ToonHQ (Invasions, Groups and more!)'
    }

    # Calculate the length of the longest menu item's text
    longest_string = max(menu.values(), key=len)
    border_box_width = len(longest_string) + 7
    box_label = " Simple TTR Launcher "
    box_label_len = len(box_label)

    # Draw the menu if redraw is True
    if redraw:
        # Build a top border using our calculated width
        print(
            f'╔═{box_label:═>2}{"":═>{border_box_width - box_label_len - 1}}╗')

        # Show the version number
        print(f'║{version:>{border_box_width - 2}}{"":>2}║')

        # Print menu items
        for num, item in menu.items():
            print(f'║  {num}. {item:{border_box_width - 5}}║')

        # Print empty space before bottom border
        print(f'║{"":^{border_box_width}}║')

        # Use the calculated width again for the bottom border
        print(f'╚{"═":═^{border_box_width}}╝')

    redraw = choose_menu_item(launcher, len(menu))

    return redraw


def choose_menu_item(launcher, num_menu_items):
    """Handles menu picker logic.

    :param launcher: A Launcher object.
    :param num_menu_items: The number of menu items that the user can
                           choose.
    :return: The new redraw status flag.
    """

    redraw = True

    selection = helper.confirm('Choose an option: ', 1, num_menu_items)
    if selection == 1:
        print()
        launcher.prepare_login()
    elif selection == 2:
        print()
        launcher.add_account()
    elif selection == 3:
        print()
        launcher.change_account()
    elif selection == 4:
        print()
        launcher.remove_account()
    elif selection == 5:
        show_options_menu(launcher)
    elif selection == 6:
        print('\nOpened web browser.')
        webbrowser.open('https://toon.town')
        redraw = False
    elif selection == 7:
        print('\nOpened web browser.')
        webbrowser.open('https://toon.town/status')
        redraw = False
    elif selection == 8:
        print('\nOpened web browser.')
        webbrowser.open('https://toonhq.org')
        redraw = False

    return redraw


def show_options_menu(launcher, clear=True):
    """Displays menu for additional launcher options.

    :param launcher: A Launcher object.
    :param clear: Flag to clear the console upon opening options menu.
    """

    if clear:
        helper.clear()

    setting_key = 'use-password-encryption'
    choice_encrypt = 'Enable'
    if launcher.settings_data['launcher'][setting_key]:
        choice_encrypt = 'Disable'

    setting_key = 'use-stored-accounts'
    choice_account_storage = 'Enable'
    if launcher.settings_data['launcher'][setting_key]:
        choice_account_storage = 'Disable'

    setting_key = 'use-os-keyring'
    choice_keyring = 'Enable'
    if launcher.settings_data['launcher'][setting_key]:
        choice_keyring = 'Disable'

    setting_key = 'display-logging'
    choice_logging = 'Enable'
    if launcher.settings_data['launcher'][setting_key]:
        choice_logging = 'Disable'

    menu = {
        1: 'Change Toontown Rewritten installation path',
        2: f'{choice_encrypt} password encryption',
        3: f'{choice_account_storage} account storage',
        4: f'{choice_keyring} OS keyring for account storage',
        5: f'{choice_logging} showing game log in console',
    }

    # Calculate the length of the longest menu item's text
    longest_string = max(menu.values(), key=len)
    border_box_width = len(longest_string) + 7
    box_label = " Settings "
    box_label_len = len(box_label)

    # Build a top border using our calculated width
    print(f'╔═{box_label:═>2}{"":═>{border_box_width - box_label_len - 1}}╗')

    # Print empty space after top border
    print(f'║{"":^{border_box_width}}║')

    # Print menu items
    for num, item in menu.items():
        print(f'║  {num}. {item:{border_box_width - 5}}║')

    # Print empty space before bottom border
    print(f'║{"":^{border_box_width}}║')

    # Use the calculated width again for the bottom border
    print(f'╚{"═":═^{border_box_width}}╝')

    choose_options_menu_item(launcher, len(menu))


def choose_options_menu_item(launcher, num_menu_items):
    """Options submenu

    :param launcher: A Launcher object.
    :param num_menu_items: The number of menu items that the user can
                           choose.
    """

    clear = True
    selection = helper.confirm(
        'Choose an option or enter 0 to return: ', 0, num_menu_items)

    if selection == 1:
        helper.clear()
        launcher.change_ttr_dir()
        print()
        clear = False
    if selection == 2:
        helper.clear()
        launcher.manage_password_encryption()
        print()
        clear = False
    elif selection == 3:
        encryption_enabled = launcher.toggle_account_storage()
        if encryption_enabled:
            print()
            clear = False
    elif selection == 4:
        launcher.toggle_os_keyring()
    elif selection == 5:
        launcher.toggle_game_log_display()

    if selection != 0:
        show_options_menu(launcher, clear)


def main():
    """Starts STTRL."""

    launcher = Launcher()

    # Skip menu if using command line args, else show menu
    if len(sys.argv) == 3:
        launcher.prepare_login()
    else:
        redraw = True
        while True:
            try:
                # Display the Main Menu
                redraw = show_menu(launcher, redraw)
                print()
            except KeyboardInterrupt:
                sys.exit()


main()
