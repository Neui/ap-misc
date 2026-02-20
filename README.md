Various unordered Archipelago-related tools
===========================================

You need to have [`PyYAML`](https://pypi.org/project/PyYAML/) installed:
```sh
python3 -m pip install -r requirements.txt
```

## `strip_apworlds.py`

Accepts `Players` folder path and `custom_worlds` folder path, and removes unreferenced apworlds from the specified `custom_worlds` folder.
This is to speed up the startup time.

It uses the `archipelago.json` manifest to detect games.

Because not every game has one, there is a `apworlds.csv` file (pass it with `--database apworlds.csv`) that can be used for apworlds without the manifest.
The one provided in this repository is generated from [Eijebong's Archipelago index](https://github.com/Eijebong/Archipelago-index) with a few changes.
The `keep` column can be set to `true` to always keep the APworld, such as the Universal Tracker or other tools.

Note that this does not process APworlds as folders (like in `Archipelago/lib/worlds`).

Example usage:

```sh
python3 strip_apworlds.py --database apworlds.csv "$HOME/bin/Archipelago/Players" "$HOME/bin/Archipelago/custom_worlds"
```

## `upload.py`

Uploads and creates a room for the specified multiworld zip file to Archipelago and prepares a chat message to send out to your players.
It uses `upload.yaml` as the configuration file which also contains the message.

The script requires a secrets file containing your session ID to log into so it'll appear in your "User Content" and allows you to input admin commands.
Copy `secrets.example.yaml` to `secrets.yaml`, visit https://archipelago.gg/session (or equivalent), and copy-paste the session URL.

Example usage after setup:
```py
python3 upload.py /home/neui/bin/Archipelago/output/AP_68547229467390776870.zip
```
Example console output (also outputs the message to `message.txt`):
```
INFO:__main__:Loading secret cookies
INFO:__main__:Loading multiworld data
INFO:__main__:Uploading multiworld
INFO:__main__:Opening new room
INFO:__main__:Waiting for server to start up
INFO:__main__:Attempt 1/30
INFO:__main__:Attempt 2/30
INFO:__main__:Attempt 3/30
INFO:__main__:Attempt 4/30
INFO:__main__:Attempt 5/30
INFO:__main__:Attempt 6/30
INFO:__main__:Message:
## Room
Room: https://archipelago.gg/room/P-7ALogtTDaZtX9RLS-l4w `/connect archipelago.gg:50259`
Tracker: https://archipelago.gg/tracker/a_GA7XunTv-6HzokLHsQaw
ANAP tracker: https://tomagueri.fr/anaptracker/room/P-7ALogtTDaZtX9RLS-l4w

# Wait until after the countdown to start playing!
```
