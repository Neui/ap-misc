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

