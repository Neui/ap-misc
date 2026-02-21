#!/usr/bin/env python3

# SPDX-License-Identifier: CC0-1.0

import dataclasses
import logging
import sys
import unpickle
import zlib
import io
import zipfile
from typing import Any, Optional, Iterator

log = logging.getLogger(__name__)

PlayerName = str
PlayerId = int
GameName = str


def SlotType(slot_type: int) -> int:
    return slot_type  # TODO: What is this? Maybe an enum? Look it up in AP src


@dataclasses.dataclass
class SlotInfo:
    player_name: PlayerName
    game_name: GameName
    slot_type: int
    unknown: Any = None


@dataclasses.dataclass
class ServerOptions:
    host: Optional[str] = None
    port: Optional[int] = None
    password: Optional[str] = None
    server_password: Optional[str] = None

    @property
    def visible_password(self) -> str:
        """
        Password that the user usually has to type in.
        Normally, "no password" means "None" but the various clients
        (except the integrated text client when using the name:password@...
        syntax) turn empty passwords into "None".
        """
        return "" if self.password is None else str(self.password)


@dataclasses.dataclass(frozen=True)
class Hint:
    unknown1: int
    unknown2: int
    unknown3: int
    unknown4: int
    unknown5: bool
    unknown6: str
    unknown7: int
    hint_status: int


@dataclasses.dataclass
class MultiWorld:
    slot_data: dict[PlayerId, dict[str, Any]] = dataclasses.field(default_factory=dict)
    slot_info: dict[PlayerId, SlotInfo] = dataclasses.field(default_factory=dict)
    connect_names: dict[PlayerName, tuple] = dataclasses.field(default_factory=dict) # TODO: What is the format?
    locations: dict[PlayerId, dict[int, tuple]] = dataclasses.field(default_factory=dict) # TODO: What is the format?
    server_options: ServerOptions = dataclasses.field(default_factory=ServerOptions)
    version: Optional[tuple[int, int, int]] = (0, 0, 0)
    seed_name: str = ""
    race_mode: int = 0  # TODO: What do the numbers mean?

    def get_slots_by_game_name(self, game_name: str) -> Iterator[SlotInfo]:
        return filter(lambda slot: slot.game_name == game_name,
                      self.slot_info.values())

    def get_slot_by_player_name(self, player_name: str) -> Optional[SlotInfo]:
        return next(filter(lambda slot: slot.player_name == player_name,
                           self.slot_info.values()), None)


unpickle_mapping: unpickle.ResolveMapping = {
    ('NetUtils', 'NetworkSlot'): SlotInfo,
    ('NetUtils', 'SlotType'): SlotType,
}


def parse(raw_data: Any):
    if type(raw_data) is bytes or type(raw_data) is bytearray:
        raw_data = io.BytesIO(raw_data)
    try:
        with zipfile.ZipFile(raw_data) as zip_file:
            for filename in zip_file.namelist():
                if filename.endswith('.archipelago'):
                    return parse_bytes(zip_file.read(filename))
                    break
    except zipfile.BadZipFile:
        raw_data.seek(0)
        return parse_bytes(raw_data.read())


def parse_bytes(raw_data: bytes):
    format_version = raw_data[0]
    logging.debug("Found multiworld format version 0x%02x", format_version)
    # TODO: Check format version
    data = unpickle.Unpickler(io.BytesIO(zlib.decompress(raw_data[1:]))).load()
    data = unpickle.resolve(data, unpickle_mapping)

    so = data.get('server_options', {})
    server_options = ServerOptions(host=so.get('host', None),
                                   port=so.get('port', None),
                                   password=so.get('password', None),
                                   server_password=so.get('password', None)
                                   )

    return MultiWorld(slot_data=data.get('slot_data', {}),
                      slot_info=data.get('slot_info', {}),
                      connect_names=data.get('connect_names', {}),
                      version=data.get('version'),
                      locations=data.get('locations', {}),
                      seed_name=data.get('seed_name', ''),
                      race_mode=data.get('race_mode', 0),
                      server_options=server_options
                      )


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    import argparse
    import pprint
    parser = argparse.ArgumentParser()
    parser.description = "Parse a .archipelago world file"

    parser.add_argument("world", type=str,
                        help="Path to .archipelago or .zip file")

    args = parser.parse_args()
    with open(args.world, 'rb') as f:
        pprint.pp(parse(f), width=200)
