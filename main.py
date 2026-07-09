#!/usr/bin/env python3

"""Sets up the STTRL menu and launcher."""

import sys
import webbrowser
import helper
from launcher import Launcher


def show_menu(launcher):
    """Displays the Main Menu of the launcher.

    :param launcher: A Launcher object.
    :param redraw: The redraw status.
                   0 = The menu will not be redrawn
                   1 = The menu will be redrawn
                   2 = The menu will be redrawn without an extra print()
    :return: The new redraw status.
    """

    version = 'v3.4'
    redraw = 1

    # Menu items
    menu = {
        1: 'Play',
        2: 'Add an account',
        3: 'Change a stored password',
        4: 'Remove an account',
        5: 'Launcher settings',
        6: 'Toontown Rewritten website',
        7: 'Toontown Rewritten server status',
        8: 'Toontown Rewritten Wiki',
        9: 'ToonHQ (Invasions, Groups and more!)',
    }

    # Calculate the length of the longest menu item's text
    longest_string = max(menu.values(), key=len)
    border_box_width = len(longest_string) + 7
    box_label = " Simple TTR Launcher "
    box_label_len = len(box_label)

    while True:
        # Draw the menu if redraw is set
        if redraw > 0:
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

        redraw = 1

        selection = helper.confirm('Choose an option: ', 1, len(menu))
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
            redraw = show_options_menu(launcher)
        elif selection == 6:
            print('\nOpened web browser.')
            webbrowser.open('https://toon.town')
            redraw = 0
        elif selection == 7:
            print('\nOpened web browser.')
            webbrowser.open('https://toon.town/status')
            redraw = 0
        elif selection == 8:
            print('\nOpened web browser.')
            webbrowser.open('https://toontownrewritten.wiki')
            redraw = 0
        elif selection == 9:
            print('\nOpened web browser.')
            webbrowser.open('https://toonhq.org')
            redraw = 0

        if redraw != 2:
            print()


def show_options_menu(launcher):
    """Displays menu for additional launcher options.

    :param launcher: A Launcher object.
    :return: The new redraw status.
    """

    helper.clear()

    while True:
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

        selection = helper.confirm(
            'Choose an option or enter 0 to return: ', 0, len(menu))

        if selection == 0:
            helper.clear()
            return 2

        if selection == 1:
            helper.clear()
            launcher.change_ttr_dir()
            print()
        elif selection == 2:
            helper.clear()
            launcher.manage_password_encryption()
            print()
        elif selection == 3:
            helper.clear()
            encryption_enabled = launcher.toggle_account_storage()
            if encryption_enabled:
                print()
        elif selection == 4:
            helper.clear()
            encryption_enabled = launcher.toggle_os_keyring()
            if encryption_enabled:
                print()
        elif selection == 5:
            helper.clear()
            launcher.toggle_game_log_display()


def main():
    """Starts STTRL."""

    launcher = Launcher()

    # Skip menu if using command line args, else show menu
    if len(sys.argv) == 3:
        launcher.prepare_login()
    else:
        try:
            # Display the Main Menu
            show_menu(launcher)
        except KeyboardInterrupt:
            sys.exit()


main()
