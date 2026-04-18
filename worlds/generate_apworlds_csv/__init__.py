from worlds.AutoWorld import AutoWorldRegister
import Utils
import worlds.LauncherComponents
import pathlib
import argparse

from . import apworlds

def run_generate_apworlds(*args) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", default=None, nargs='?',
                        help="Path to database to create or update")
    parser.add_argument('--core', dest='core', default=False, action='store_true',
                        help="Also add core games to the database")
    parser.add_argument('--mark-keep', dest='mark_keep', default=False, action='store_true',
                        help="Mark games to be kept")

    args = parser.parse_args(args)

    db = apworlds.Database()
    database_file = args.database
    if database_file is None:
        database_file = Utils.save_filename("Select apworlds.csv file",
                                            (("apworlds database", (".csv",)),),
                                            "my-worlds.csv")
        if database_file is None:
            return

    try:
        db.insert_file(database_file)
    except FileNotFoundError:
        pass

    for game_name, world_class in AutoWorldRegister.world_types.items():
        if not hasattr(world_class, 'zip_path') \
                or not isinstance(world_class.zip_path, pathlib.PurePath):
            continue
        is_core = "/lib/worlds/" in ("/".join(world_class.zip_path.parents[0].parts) + "/")
        if not args.core and is_core:
            continue
        db.insert(apworlds.DatabaseEntry(file_name=world_class.zip_path.stem,
                                         keep=args.mark_keep,
                                         game_name=game_name))
    db.output(database_file)
    return


worlds.LauncherComponents.components.append(
    worlds.LauncherComponents.Component(
        "Generate apworlds.csv",
        func=run_generate_apworlds,
        component_type=worlds.LauncherComponents.Type.TOOL,
    )
)
