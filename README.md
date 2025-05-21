# Simple TTR Launcher

A custom launcher for Toontown Rewritten with credential storage for automated logins.

Officially supported on Windows and Linux. Mac is untested at this time, but feel free to give it a try and let me know!

Windows executable downloads are on the Releases page. Linux and Mac users should run this from source.

## How to use:
- The first time run will generate a launcher.json file for you. This is used by STTRL to store your settings and optionally your accounts. If you ever need to reset your launcher to default settings, just delete this file. Please do not make edits to it directly and instead use the Launcher to make changes.
- You can save accounts and passwords in the Launcher by enabling the account storage feature through the Launcher settings.
    - Passwords are stored in your operating system's keyring (Windows Credential Manager, GNOME Keyring, macOS Keychain, etc) by default as it is the most secure method. Password based encryption is disabled by default in this mode, but may be toggled on for enhanced security in the Launcher settings.
    - If desired, you can store your passwords in launcher.json directly instead by disabling the OS keyring in the Launcher settings. This is useful if you want your STTRL install to be completely portable between systems. By default saved passwords in launcher.json are encrypted with a master password. You may disable password encryption if you wish but this will show your passwords as plain text in the launcher.json config file. NEVER share your launcher.json file with anyone!
- You can also enable showing TTR Engine logging to the command line in the Launcher settings.
- You may alternatively login using the command line with the format: `STTRL.exe your_user your_pass` if using the Windows executable or `./main.py your_user your_pass` if running from source as a way to automate logins. NOTE: Your credentials WILL be exposed in plain text by using this method, either in your command line history or to an application you execute this with. Be sure that you trust where you are using this method!

## Running from source:

1. Create a python3 virtual environment and activate it:
    - `python3 -m venv sttrl-venv`
    - `source sttrl-venv/bin/activate`
2. Install requirements: `pip install -r requirements.txt`
3. Start STTRL with `./main.py`
