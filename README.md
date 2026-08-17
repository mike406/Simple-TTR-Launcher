# Simple TTR Launcher

A custom launcher for Toontown Rewritten with credential storage for automated logins.

Officially supported on Windows and Linux. Mac is untested at this time, but feel free to give it a try and let me know!

Windows executable downloads are on the Releases page. Linux and Mac users should run this from source.

## How to use:
- The first time run will generate a launcher.json file for you. This is used by STTRL to store your settings and optionally your accounts. If you ever need to reset your launcher to default settings, just delete this file. Please do not make edits to it directly and instead use the Launcher to make changes.
- On Windows, STTRL will try to look for your existing TTR installation and use that. If you don't have one, or if running on Linux or Mac, STTRL will install TTR in the current directory you are in. It will ask you to confirm if this is where you want to install TTR before doing so.
- If you would like to make a portable install, you can change the TTR path in the Launcher settings to something like "./Toontown Rewritten" and it will install the game to a relative path. This is useful for playing from a computer you do not have admin rights on, a USB drive or network storage between computers.
- You can save accounts in the Launcher by enabling the account storage feature through the Launcher settings.
    - Passwords are stored in your operating system's keyring (Windows Credential Manager, GNOME Keyring, macOS Keychain, etc) by default as it is the most secure and convenient method. Password based encryption is disabled by default in this mode, but may be toggled on for enhanced security in the Launcher settings. This will encrypt your passwords with a master password before storing them into your OS keyring. You will be required to enter this master password to login, add new accounts, or change a password.
    - If desired, you can store your passwords in launcher.json directly instead by disabling the OS keyring in the Launcher settings. This is useful if you want your STTRL install to be completely portable between systems. By enabling this, saved passwords in launcher.json will be encrypted with a master password of your choosing. You may disable password encryption if you wish but this will show your passwords as plain text in the launcher.json config file. NEVER share your launcher.json file with anyone!
- You can also enable showing TTR Engine logging to the command line in the Launcher settings.
- You may alternatively login using the command line with the format: `STTRL.exe account_number` if using the Windows executable or `./main.py account_number` if running from source as a way to automate logins. You must have account storage enabled to use this. The number you pass as a parameter corresponds to the account number as shown in the Launcher. Using the OS keyring storage method (default) is recommended so that your login can happen automatically. You will still need to input any ToonGuard or 2FA codes however, so if you want full automation you will need to decide if you need those enabled on your account.

## Running from source:

1. Create a python3 virtual environment and activate it:
    - `python3 -m venv sttrl-venv`
    - `source sttrl-venv/bin/activate`
2. Install requirements: `pip install -r requirements.txt`
3. Start STTRL with `./main.py`
