# Simple TTR Launcher
### Custom launcher for Toontown Rewritten

With credential storage for automated logins

Officially supported on Windows. Linux and Mac is untested at this time, but feel free to give it a try and let me know!

Executable download on Releases page

How to use:
- First time run will generate a login.json file for you.
- By default it uses this json file to read stored accounts unless saving accounts is disabled.
- You can add as many accounts as you want through the launcher.
- The stored accounts feature can be disabled by setting 'use-stored-accounts' to false in login.json. This will allow the launcher to ask for username and password to be entered manually instead.
- You may also login using a terminal command with the format: 'STTRL.exe your_user your_pass'.
- Supports ToonGuard and 2 factor auth accounts as well.

Currently it cannot patch the game files yet. So if the game tells you it can't connect to a gameserver or says the 
game files are out of date, you will need to launch the official launcher to allow it to update the phase files first.
