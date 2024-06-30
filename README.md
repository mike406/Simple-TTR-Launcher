# Simple TTR Launcher

A custom launcher for Toontown Rewritten with credential storage for automated logins.

Officially supported on Windows and Linux. Mac is untested at this time, but feel free to give it a try and let me know!

Windows executable downloads are on the Releases page. Linux and Mac users should run this from source.

## How to use:
- The first time run will generate a launcher.json file for you. This is used by STTRL to store your passwords and settings. If you ever need to reset your launcher to default settings, just delete this file.
- You can add as many accounts as you want through the launcher. By default saved passwords in launcher.json are encrypted. You may disable password encryption if you wish. NEVER share your launcher.json file with anyone!
- The stored accounts feature can be disabled in the launcher options. This will allow the launcher to ask for your username and password to be entered manually instead.
- You can also enable showing TTR Engine logging to the command line in the launcher options.
- You may alternatively login using the command line with the format: `STTRL.exe your_user your_pass` if using the Windows executable or `./main.py your_user your_pass` if running from source. You can use this method to automate your login with something like Steam for example by adding it to your library and setting your username and password in its launch options. NOTE: Your credentials WILL be exposed in plain text by using this method, either in your command line history or to the application you are linking with. Be sure that you trust where you are using this method!

## Running from source:

`pip install -r requirements.txt`

`./main.py`
