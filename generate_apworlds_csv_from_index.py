#!/usr/bin/env python3

# SPDX-License-Identifier: CC0-1.0

import argparse
import csv
import itertools
import logging
import pathlib
import sys
import tomllib


log = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.description = "Generate apworlds.csv like from github.com/Eijebong/Archipelago-index"

    parser.add_argument("index", type=str,
                        help="Directory to the index folder")
    parser.add_argument("database", type=str,
                        help="Path to the apworlds.csv to update")

    args = parser.parse_args()

    index_path = pathlib.Path(args.index)
    database_path = pathlib.Path(args.database)

    map_stem_to_game: dict[str, str] = dict()

    for child in index_path.iterdir():
        if not child.name.endswith('.toml'):
            continue
        with open(child, 'rb') as f:
            data = tomllib.load(f)
        map_stem_to_game[child.stem] = data['name']

    db = []
    if database_path.exists():
        with open(database_path, 'r', encoding='utf-8') as f:
            db = list(csv.DictReader(f))

    known_stems = {entry['name']: entry
                   for entry in db
                   if 'name' in entry.keys()}

    update_count = 0
    unchanged_count = 0
    add_count = 0
    for stem, game_name in map_stem_to_game.items():
        if stem in known_stems.keys():
            if known_stems[stem]['name'] != stem:
                known_stems[stem]['name'] = stem
                update_count += 1
            else:
                unchanged_count += 1
        else:
            db.append({'name': stem,
                       'game': game_name,
                       'keep': ""})
            add_count += 1

    log.debug("Updated %s entries, added %s entires", update_count, add_count)

    # TODO: Rearrange column
    fieldnames = list(set(itertools.chain.from_iterable(
        entry.keys() for entry in db)))

    with open(database_path, 'w', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames)
        writer.writeheader()
        writer.writerows(db)

    return 0


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    sys.exit(main())
