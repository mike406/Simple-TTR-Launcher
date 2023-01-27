# Simple TTR Launcher
### Custom launcher for Toontown Rewritten

With credential storage for automated logins

Officially supported on Windows. Linux and Mac is untested at this time, but feel free to give it a try and let me know!

Executable download on the Releases page

How to use:
- The first time run will generate a login.json file for you. This is used by STTRL to store your passwords and settings. If you ever need to reset your launcher to default settings, just delete this file.
- You can add as many accounts as you want through the launcher. NOTE: By default saved passwords in login.json are unencrypted. If you want added security please make use of the password encryption feature! This is especially recommended if you share your computer with anyone. NEVER share your login.json file with anyone!
- The stored accounts feature can be disabled by setting 'use-stored-accounts' to false in login.json. This will allow the launcher to ask for your username and password to be entered manually instead.
- You may also login using the command line with the format: 'STTRL.exe your_user your_pass'. You can use this method to automate your login with something like Steam for example by adding it to your library and setting your username and password in its launch options. NOTE: Your credentials WILL be exposed in plain text by using this method, either in your command line history or to the application you are linking with. Be sure that you trust where you are using this method!
- Supports ToonGuard and two factor authentication accounts as well.
