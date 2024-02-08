#!/usr/bin/env python3

"""Sets up up the STTRL menu and launcher."""

import webbrowser
import sys
import helper
from launcher import Launcher


def show_menu(launcher, redraw=True):
    """Displays the Main Menu of the launcher and handles menu item selection.

    :param redraw: Used to check if menu list should be output to console.
    :return: The new redraw status flag.
    """

    # Skip menu if using command line args
    if len(sys.argv) == 3:
        helper.quit_launcher()

    num_menu_items = 10
    if redraw:
        print('### Main Menu ###')
        print('1. Play')
        print('2. Add an account')
        print('3. Change a stored password')
        print('4. Remove an account')
        print('5. Change Toontown Rewritten installation path')
        print('6. Enable/Disable password encryption')
        print('7. Toontown Rewritten website')
        print('8. Toontown Rewritten server status')
        print('9. ToonHQ.org')

    redraw = choose_menu_item(launcher, num_menu_items)

    return redraw


def choose_menu_item(launcher, num_menu_items):
    """Handles menu picker logic.

    :param num_menu_items: The number of menu items that the user can choose.
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
        print()
        launcher.change_ttr_dir()
    elif selection == 6:
        print()
        launcher.manage_password_encryption()
    elif selection == 7:
        webbrowser.open('https://toon.town')
        redraw = False
    elif selection == 8:
        webbrowser.open('https://toon.town/status')
        redraw = False
    elif selection == 9:
        webbrowser.open('https://toonhq.org')
        redraw = False
    elif selection == 10:
        sys.exit()

    return redraw


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
