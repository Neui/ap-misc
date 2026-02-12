#!/usr/bin/env python3

# SPDX-License-Identifier: CC0-1.0

import argparse
import csv
import json
import logging
import pathlib
import sys
import yaml
import zipfile
from typing import Any


log = logging.getLogger(__name__)
meta_root_options = {"meta_description"}
really_keep = {"A Link to the Past"}
keep_values = {"yes", "Yes", "true", "True", "keep"}


def get_manifest(world_path: pathlib.Path) -> Any | None:
    if world_path.name.lower().endswith('.apworld'):
        ap_json_path = f'{world_path.stem}/archipelago.json'
        with zipfile.ZipFile(world_path) as world_zip:
            # AP 0.6.6 does a walk, but that seems excessive.
            if ap_json_path not in world_zip.namelist():
                ap_json_path = 'archipelago.json'  # Common enough
            if ap_json_path not in world_zip.namelist():
                return None
            with world_zip.open(ap_json_path) as f:
                # TODO: Force UTF-8(-sig?) encoding
                return json.load(f)
    else:
        log.warning("Unsupported non-.apworld %s", world_path)
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.description = "Remove apworlds that don't appear in the player yamls."

    parser.add_argument("--dry-run", action='store_true', default=False,
                        dest='dryrun',
                        help="Don't actually delete/move the apworlds")
    parser.add_argument("--database", type=str, default=None,
                        help="Where to find information about APWorlds")
    parser.add_argument("--keep", type=str, default=None,
                        help="Which APWorlds to not strip, comma separated game list")
    parser.add_argument("--move-to", type=str, default=None, dest='moveto',
                        help="Move stripped apworlds to directory instead of deleting them")
    parser.add_argument("players", type=str, help="Player folder containing the YAMLs")
    parser.add_argument("custom_worlds", type=str, help="custom_worlds folder to strip")

    args = parser.parse_args()

    if args.dryrun:
        log.info("This is a dry run, no modifications will be made.")

    games = set()
    if args.keep is not None:
        games |= map(str.strip, args.keep.split(','))
    log.debug("Games to keep (cli): %r", games)
    games |= really_keep
    log.debug("Games to really keep (built-in): %r", really_keep)

    # TODO: Look into DB
    if args.database is None:
        database_path = pathlib.Path("apworlds.csv")
    else:
        database_path = pathlib.Path(args.database)
    db = []
    try:
        with open(database_path) as f:
            db = list(csv.DictReader(f))
    except FileNotFoundError:
        if args.database is not None:
            raise  # Only error when it was specified

    db_keep = set((entry['game']
                   for entry in db
                   if 'game' in entry and entry.get('keep') in keep_values))
    log.debug("Games to keep (DB): %r", db_keep)
    games |= db_keep
    del db_keep

    db_games: dict[str, str] = {entry['name']: entry['game']
                for entry in db
                if 'name' in entry and 'game' in entry}

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
            if 'game' in content:
                if type(content['game']) is str:
                    games.add(content['game'])
                elif type(content['game']) is dict:
                    games.update(content['game'].keys())
                else:
                    log.warning(f"{child} #{i + 1} unknown 'game' {type(game)}")
                    log.debug(f"{child} #{i + 1} unknown 'game' was %r", game)
            elif 'meta_description' not in content:
                info.warning(f"{child} #{i + 1} does not have 'game'")
            if 'meta_description' in content:
                log.info(f"Found meta file {child} #{i + 1}")
                games.update((category for category in content.keys() if category not in meta_root_options))

    log.debug("Games to keep: %s", games)

    custom_worlds_path = pathlib.Path(args.custom_worlds)

    apworlds_to_remove: dict[pathlib.Path, str] = dict() # path stem: game name

    # Remove via database
    for world_path in custom_worlds_path.iterdir():
        if not world_path.is_file() \
                or not world_path.name.lower().endswith('.apworld') \
                or world_path in apworlds_to_remove.keys() \
                or world_path.stem not in db_games.keys():
            continue
        game = db_games[world_path.stem]
        if game not in games:
            apworlds_to_remove[world_path] = game

    # Look into remaining apworlds and check their archipelago.json manifest
    for world_path in custom_worlds_path.iterdir():
        if not world_path.is_file() \
                or not world_path.name.lower().endswith('.apworld') \
                or world_path in apworlds_to_remove.keys() \
                or world_path.stem in db_games.keys():
            continue
        ap_json = get_manifest(world_path)
        if ap_json is None:
            log.warning("%s does not have a archipelago.json manifest", world_path)
            continue
        if type(ap_json) is not dict:
            log.warning("%s archipelago.json error: Root needs to be a dict", world_path)
            continue
        if 'game' not in ap_json:
            log.warning("%s archipelago.json error: No 'game' found", world_path)
            continue
        game = ap_json['game']
        if type(game) is not str:
            log.warning("%s archipelago.json error: 'game' must be a string", world_path)
            continue
        if game not in games:
            apworlds_to_remove[world_path] = game

    # Look into manuals, they have a game.json we can use for now
    for world_path in custom_worlds_path.iterdir():
        if not world_path.is_file() \
                or not world_path.name.lower().startswith('manual_') \
                or not world_path.name.lower().endswith('.apworld') \
                or world_path in apworlds_to_remove.keys() \
                or world_path.stem in db_games.keys():
            continue
        manual_game_json_path = f'{world_path.stem}/data/game.json'
        with zipfile.ZipFile(world_path) as world_zip:
            if manual_game_json_path not in world_zip.namelist():
                continue
            with world_zip.open(manual_game_json_path) as f:
                # TODO: Force UTF-8(-sig?) encoding
                game_json = json.load(f)
        if type(game_json) is not dict:
            log.warning(f"{world_path} manual data/game.json error: Root needs to be a dict")
            continue
        if 'game' not in game_json:
            log.warning(f"{world_path} manual data/game.json error: No 'game' found")
            continue
        game_name = game_json['game']
        if type(game_name) is not str:
            log.warning(f"{world_path} manual data/game.json error: 'game' must be a string")
            continue
        if 'player' not in game_json and 'creator' not in game_json:
            log.warning(f"{world_path} manual data/game.json error: No 'creator' found")
            continue
        if 'creator' in game_json:
            creator_name = game_json['creator']
            if type(creator_name) is not str:
                log.warning(f"{world_path} manual data/game.json error: 'creator' must be a string")
                continue
        else:
            creator_name = game_json['player']
            if type(creator_name) is not str:
                log.warning(f"{world_path} manual data/game.json error: 'player' must be a string")
                continue
        game = f'Manual_{game_name}_{creator_name}'
        if game_name == "Stable" or game_name == "Unstable":
            continue  # Keep the official client
        if game not in games:
            apworlds_to_remove[world_path] = game

    if args.moveto:
        move_to_path = pathlib.Path(args.moveto)
    else:
        move_to_path = None

    for world_path in apworlds_to_remove.keys():
        log.debug("Removing %s", world_path)
        if not args.dryrun:
            try:
                if move_to_path is not None:
                    log.error("TODO: Implement move to path")
                    raise NotImplementedError
                else:
                    world_path.unlink()
            except:
                log.exception("Failed to (re)move %s", world_path)

    return 0


if __name__ == '__main__':
    # logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    sys.exit(main())
