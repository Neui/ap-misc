#!/usr/bin/env python3

# SPDX-License-Identifier: CC0-1.0

import argparse
import collections
import dataclasses
import json
import logging
import pathlib
import sys
import yaml
from typing import Any


log = logging.getLogger(__name__)
meta_root_options = {"meta_description"}

def clean_name(name: str) -> str:
    name = name.replace('{number}', '')
    name = name.replace('{NUMBER}', '')
    return name


@dataclasses.dataclass
class WeightsFile:
    path: pathlib.Path
    index: int
    games: list[str] = dataclasses.field(default_factory=list)
    main_name: str = ""
    possible_names: list[str] = dataclasses.field(default_factory=list)
    all_names: list[str] = dataclasses.field(default_factory=list)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.description = "Get the names."

    parser.add_argument("players", type=str, help="Player folder containing the YAMLs")

    args = parser.parse_args()
    all_weights: list[WeightsFile] = []

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
            weights = WeightsFile(
                path=child,
                index=i,
            )

            if 'game' in content:
                if type(content['game']) is str:
                    weights.games.append(content['game'])
                elif type(content['game']) is dict:
                    weights.games.extend((game
                                          for game, weight in content['game'].items()
                                          if weight != 0))
                else:
                    log.warning(f"{child} #{i + 1} unknown 'game' {type(game)}")
                    log.debug(f"{child} #{i + 1} unknown 'game' was %r", game)

                weights.main_name = content['name']
                main_name = clean_name(content['name'])

                triggers = content.get('triggers', [])
                for game in weights.games:
                    triggers.extend(content.get(game, {}).get('triggers', []))

                for trigger in triggers:
                    opts = trigger.get('options', {})
                    name = None
                    if '' in opts and 'name' in opts['']:
                        name = opts['']['name']
                    elif None in opts and 'name' in opts[None]:
                        name = opts[None]['name']
                    if name is not None:
                        weights.possible_names.append(name)

                all_weights.append(weights)
            elif 'meta_description' not in content:
                info.warning(f"{child} #{i + 1} does not have 'game'")

    all_names = [[weights.main_name, weights] for weights in all_weights]
    for weights in all_weights:
        for possible_name in weights.possible_names:
            all_names.append([possible_name, weights])

    # Sort by filename since that is how AP does it for player slot number?
    # TODO: Verify what order AP oses for player slot number
    all_names.sort(key=lambda w: (w[1].path.name, w[0]))

    # {player} replaced with the player's slot number.
    # {PLAYER} replaced with the player's slot number, if that slot number is greater than 1.
    # {number} replaced with the counter value of the name.
    # {NUMBER} replaced with the counter value of the name, if the counter value is greater than 1.
    total_counter = collections.Counter([a[0] for a in all_names])
    counter = collections.Counter()

    for i, data in enumerate(all_names):
        name, weights = data
        if '[player]' in name or '{PLAYER}' in name:
            raise NotImplementedError("{PLAYER} and {player} not yet implemented for %s", name)
        if '{number}' in name:
            counter[name] += 1  # Counting starts from 1
            name = name.replace('{number}', str(counter[name]))
        elif '{NUMBER}' in name:
            counter[name] += 1
            if total_counter[name] <= 1:
                name = name.replace('{NUMBER}', '')
            else:
                name = name.replace('{NUMBER}', str(counter[name]))
        all_names[i][0] = name
        print(f"    - {json.dumps(name)}    # {weights.path.name}")

    return 0


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    # logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    sys.exit(main())
