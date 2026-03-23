#!/usr/bin/env python3

# SPDX-License-Identifier: CC0-1.0

from collections.abc import Iterable
import csv
import dataclasses
import logging
import re


log = logging.getLogger(__name__)
keep_values = {"yes", "Yes", "true", "True", "keep", "1"}
known_columns = ("file", "keep", "game")


@dataclasses.dataclass(slots=True)
class DatabaseEntry:
    file_name: str
    keep: bool
    game_name: str
    _other: dict[str, str] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_csv_line(cls, line: dict) -> 'DatabaseEntry':
        return cls(file_name=line['name'],
                   keep=line.get('keep', '0').lower().strip() in keep_values,
                   game_name=line['game'],
                   _other=line)

    def to_output_dict(self) -> dict[str, str]:
        return self._other | {
            'name': self.file_name,
            'keep': 'true' if self.keep else '',
            'game': self.game_name,
        }


class Database:
    def __init__(self):
        self.entries: list[DatabaseEntry] = []
        self.from_file_name: dict[str, DatabaseEntry] = {}
        self.from_game_name: dict[str, DatabaseEntry] = {}

    def insert_file(self, file_path) -> None:
        with open(file_path) as f:
            self.insert_multiple(map(DatabaseEntry.from_csv_line, csv.DictReader(f)))

    def insert_multiple(self, entries: Iterable[DatabaseEntry]) -> None:
        for entry in entries:
            self.insert(entry)

    def insert(self, entry: DatabaseEntry) -> None:
        exists = False
        if entry.file_name != "":
            other = self.from_file_name.get(entry.file_name)
            if other is not None:
                exists = True
                other.keep |= entry.keep
                if other.game_name == "":
                    other.game_name = entry.game_name
                    self.from_game_name[entry.game_name] = other
        if entry.game_name != "":
            other = self.from_game_name.get(entry.game_name)
            if other is not None:
                exists = True
                other.keep |= entry.keep
                if other.file_name == "":
                    other.file_name = entry.file_name
                    self.from_file_name[entry.file_name] = other
        if not exists:
            self.entries.append(entry)
            if entry.file_name != "":
                self.from_file_name[entry.file_name] = entry
            if entry.game_name != "":
                self.from_game_name[entry.game_name] = entry

    def output(self, path):
        field_names = ["name", "keep", "game"]
        for entry in self.entries:
            for other_field_name in entry._other.keys():
                if other_field_name not in field_names:
                    field_names.add(other_field_name)

        with open(path, 'w', encoding='utf-8') as f:
            writer = csv.DictWriter(f, field_names)
            writer.writeheader()
            outputs = [entry.to_output_dict() for entry in self.entries]
            outputs.sort(key=lambda e: (_natural_sort_key(e['name']),
                                        e['keep'],
                                        _natural_sort_key(e['game'])))
            writer.writerows(outputs)

    def should_keep_game(self, game_name: str, default: bool = True) -> bool:
        entry = self.from_game_name.get(game_name)
        return entry.keep if entry is not None else default

    def should_keep_file(self, file_name: str) -> bool:
        entry = self.from_file_name.get(file_name)
        return entry.keep if entry is not None else default

_find_number_re = re.compile(r'(\d+)')
def _natural_sort_key(name: str):
    return tuple(int(sub) if sub.isdigit() else sub
                 for sub in _find_number_re.split(name.lower()))
