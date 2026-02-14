#!/usr/bin/env python3

# SPDX-License-Identifier: CC0-1.0

import argparse
import csv
import json
import logging
import pathlib
import sys
import yaml
import json
import zipfile
from typing import Any


log = logging.getLogger(__name__)
meta_root_options = {"meta_description"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.description = "Get the names."

    parser.add_argument("players", type=str, help="Player folder containing the YAMLs")

    args = parser.parse_args()


    for child in pathlib.Path(args.players).iterdir():
        if not child.is_file():
            continue
        try:
            with open(child, 'rt', encoding='utf-8-sig') as f:
                inp = list(yaml.safe_load_all(f.read()))
        except:
            log.exception(f"Failed to parse {child}")
            return 1
        for i, content in enumerate(inp):
            games = set()
            if 'game' in content:
                if type(content['game']) is str:
                    games.add(content['game'])
                    log.debug("%s #%i: Found ['%s']", child, i, content['game'])
                elif type(content['game']) is dict:
                    games.update(content['game'].keys())
                    log.debug("%s #%i: Found %r", child, i,
                              list(content['game'].keys()))
                else:
                    log.warning(f"{child} #{i + 1} unknown 'game' {type(game)}")
                    log.debug(f"{child} #{i + 1} unknown 'game' was %r", game)
                main_name = content['name']
                main_name = main_name.replace('{number}', '')
                main_name = main_name.replace('{NUMBER}', '')
                print(f'    - {json.dumps(main_name)}     # {child.name}')
                triggers = content.get('triggers', [])
                for game in games:
                    triggers.extend(content.get(game, {}).get('triggers', []))
                for trigger in triggers:
                    # Coding the name getter thingy if you're interested
                    opts = trigger.get('options', {})
                    name = None
                    if '' in opts and 'name' in opts['']:
                        name = opts['']['name']
                    elif None in opts and 'name' in opts[None]:
                        name = opts[None]['name']
                    if name is not None:
                        name = name.replace('{number}', '')
                        name = name.replace('{NUMBER}', '')
                        print(f'    - {json.dumps(name)} # {main_name}     # {child.name}')
            elif 'meta_description' not in content:
                info.warning(f"{child} #{i + 1} does not have 'game'")

    return 0


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    # logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    sys.exit(main())
