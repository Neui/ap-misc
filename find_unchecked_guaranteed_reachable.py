# This was never meant to be seen by another pair of eyes.
# Good luck.
import multiworld
import unpickle
import io
import enum

import platform
if platform.system() == "Windows":
    import sys  # Workaround for file redirection on Windows
    sys.stdout.reconfigure(encoding='utf-8')

# AP multidata from in the output .zip
AP_PATH = r"/home/neui/AP/Archipelago/output/AP_63582889109049541795.zip"
UNREACHABLE_SPHERE = 232
# download the sphere tracker through right click -> save link as
SPHERE_TRACKER_PATH = r"/home/neui/projects/ap-misc/sphere-tracker.html"

class ItemClassification(enum.IntFlag):
    filler = 0b00000
    progression = 0b00001
    useful = 0b00010
    trap = 0b00100
    skip_balancing = 0b01000
    deprioritized = 0b10000
    progression_deprioritized_skip_balancing = 0b11001
    progression_skip_balancing = 0b01001
    progression_deprioritized = 0b10001

def find_unchecked_progression(
        progression_only: bool = False,
        guaranteed_in_logic_only: bool = False,
        ignore_emblems_and_strawberries: bool = False,
) -> None:
    from collections import defaultdict
    import zlib
    import re
    import html

    

    with open(AP_PATH, "rb") as f:
        raw_data = f.read()
        mw = multiworld.parse(raw_data)
        ver, data = multiworld._get_inner(multiworld._find_multiworld(raw_data))
        data = unpickle.Unpickler(io.BytesIO(data)).load()
        data = unpickle.resolve(data, multiworld.unpickle_mapping)
    # [0] is team, [1] is slot number
    location_id_to_name = {game: {v: k for k, v in game_data["location_name_to_id"].items()}
                           for game, game_data in data["datapackage"].items()}
    locations: dict[int, dict[int, tuple[int, int, int]]] = data["locations"]
    game_data_packages = data["datapackage"]
    item_id_to_name_game_data_packages = {
        game: {v: k for k, v in datapackage["item_name_to_id"].items()}
        for game, datapackage
        in game_data_packages.items()
    }

    with open(SPHERE_TRACKER_PATH, "r", encoding="utf-8") as f:
        contents = f.read()

    per_sphere_location_names: dict[int, dict[str, dict[str, int]]] = {}

    player_name_to_id = {slot.player_name: player_id for player_id, slot in mw.slot_info.items()}

    player_locations = defaultdict(list)

    for sphere_num, per_player_locs in enumerate(data["spheres"], start=1):
        escaped_prog_loc_names_by_escaped_player_name: dict[str, dict[str, int]] = {}
        per_sphere_location_names[sphere_num] = escaped_prog_loc_names_by_escaped_player_name

        for player, loc_ids in per_player_locs.items():
            player_locs = locations[player]
            if progression_only:
                progression_loc_ids = [loc_id for loc_id in loc_ids if
                                       ItemClassification.progression in ItemClassification(player_locs[loc_id][2])]
            else:
                progression_loc_ids = loc_ids
            id_to_name = location_id_to_name[mw.slot_info[player].game_name]
            loc_names = {id_to_name[loc_id]: loc_id for loc_id in progression_loc_ids}
            # These should really be events, and don't actually send on goal because the game client implementations are
            # bad.
            if "Perfect Chaos Fight" in loc_names:
                del loc_names["Perfect Chaos Fight"]
            if "Bowser" in loc_names:
                del loc_names["Bowser"]
            if "Yoshi's House" in loc_names:
                del loc_names["Yoshi's House"]
            escaped_prog_loc_names_by_escaped_player_name[mw.slot_info[player].player_name] = loc_names

    for match in re.finditer(
            r"<td>(\d+)</td>\s+<td>([^<]+)</td>\n.+\n.+\n\s+<td>([^<]+)", contents):
        sphere_num, escaped_player_name, escaped_location_name = match.groups()
        unescaped_loc_name = html.unescape(escaped_location_name)
        locs_dict = per_sphere_location_names[int(sphere_num)][html.unescape(escaped_player_name)]
        if unescaped_loc_name in locs_dict:
            del locs_dict[unescaped_loc_name]

    players_missing_progression_items: set[int] = set()

    from collections import Counter
    reachable_counts: Counter[str] = Counter()

    all_player_names: set[str] = set()

    per_player_locs: dict[str, dict[str, int]]
    for sphere_num, per_player_locs in per_sphere_location_names.items():
        missing_progression_items_after_sphere: set[int] = set()

        if sphere_num == UNREACHABLE_SPHERE:
            # The last sphere contains only unreachable locations
            continue

        if guaranteed_in_logic_only:
            per_player_locs_reduced: dict[str, dict[str, int]] = {}
            for player_name, locs_dict in per_player_locs.items():
                player_id = player_name_to_id[player_name]
                player_locs = locations[player_id]
                for loc_id in locs_dict.values():
                    item_player_id = player_locs[loc_id][1]
                    if item_player_id == player_id:
                        # Reachable local items do not block the player because they can just get the local item.
                        continue
                    if ItemClassification.progression not in ItemClassification(player_locs[loc_id][2]):
                        # Non-progression does not block.
                        continue
                    if ignore_emblems_and_strawberries:
                        item_id = player_locs[loc_id][0]
                        item_name = item_id_to_name_game_data_packages[mw.slot_info[item_player_id].game_name][item_id]
                        if item_name in ("Emblem", "Strawberry"):
                            continue
                    missing_progression_items_after_sphere.add(item_player_id)

                if player_id in players_missing_progression_items:
                    # The current player might not be able to reach locations in this sphere.
                    continue
                else:
                    per_player_locs_reduced[player_name] = locs_dict
        else:
            per_player_locs_reduced = per_player_locs

        if any(per_player_locs_reduced.values()):
            non_empty_per_player_locs = {k: v for k, v in per_player_locs_reduced.items() if v}
            print(f"{sphere_num} ({sum(map(len, non_empty_per_player_locs.values()))}):")
            for player, locs in sorted(non_empty_per_player_locs.items(), key=lambda t: t[0], reverse=True):
                player_locations[player] += locs
                reachable_counts[player] += len(locs)
                print(f"\t{player} ({len(locs)}):\n\t\t{', '.join(sorted(locs.keys()))}")
                all_player_names.add(player)
                # print(f"\t{player} ({len(locs)})")
            #print(f"{sphere_num}:\n\t{non_empty_per_player_locs}")

        players_missing_progression_items.update(missing_progression_items_after_sphere)

    if guaranteed_in_logic_only:
        print(*sorted(reachable_counts.items(), key=lambda t: t[0].casefold()), sep="\n")

        for player, locs in sorted(player_locations.items(), key=lambda t: t[0].casefold()):
            sorted_locs = sorted(locs)
            print(player, len(sorted_locs), ", ".join(sorted_locs), sep="\t")
            #print("\t" + ", ".join(sorted_locs))
    else:
        print(sorted(all_player_names, key=str.casefold))
        print(*sorted(reachable_counts.items(), key=lambda t: t[0].casefold()), sep="\n")

if __name__ == "__main__":
    find_unchecked_progression(
        progression_only=True,
        guaranteed_in_logic_only=True,
        # Emblems and Strawberries don't unlock much, but they can still be logically relevant outside of the goal, so
        # enabling this will no longer 100% guarantee reachability.
        ignore_emblems_and_strawberries=False,
    )
