# Simple TTR Launcher
### Custom launcher for Toontown Rewritten

No GUI, no fuss, and with credential storage for automated logins

Currently only supported on Windows - Executable download on Releases page

How to use:
- First time run will generate a login.json file for you.
- By default it uses this json file to read stored accounts.
- An infinite number of accounts can be added to this json file, just follow the correct format by adding consecutively numbered username and password pairings (mind the commas!):  

    "username1": "lucky_cat",  
    "password1": "12345",  
    
    "username2": "billybob",  
    "password2": "pass1234"  
- The stored accounts feature can be disabled by setting 'use-stored-accounts' to false. This will allow the launcher to ask for username and password to be entered manually.
- You may also login using the command prompt with the format - STTRL.exe your_user your_pass
- Supports ToonGuard and 2 factor auth accounts as well
- Also don't forget to change the path to your TTR directory in login.json if yours is different.

Currently it cannot update the game...yet. So if the game tells you it can't connect to a gameserver or says the 
game files are out of date, you will need to launch the official launcher to allow it to update the phase files first. I know...I know, blasphemy.
