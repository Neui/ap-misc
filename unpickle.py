#!/usr/bin/env python3

# SPDX-License-Identifier: CC0-1.0

# Basically a version of the Python Unpickler except it does not create
# instances of real classes, but rather instances of "Unpickled" that can
# be later resolved to real objects.

import functools
import logging
import pickle
import sys
from typing import Any, Union, Callable, Optional


log = logging.getLogger(__name__)


OriginName = tuple[str, str]
Origin = Union[OriginName, 'Unpickled', None]


class Unpickled:
    origin: Origin = None
    args: list[Any]
    kwargs: dict[Any, Any]

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    # For some reason this is needed, otherwise __init__ won't be called?
    def __new__(cls, *args, **kwargs):
        o = object.__new__(cls)
        o.__init__(*args, **kwargs)
        return o

    def __str__(self) -> str:
        return f"Unpickled(origin={self.origin}, " \
            f"args={self.args}, kwargs={self.kwargs})"

    def __repr__(self) -> str:
        return f"Unpickled(origin={repr(self.origin)}, " \
            f"args={repr(self.args)}, kwargs={repr(self.kwargs)})"

    # TODO: More testing whenever this is actually used (RESOLVE opcode)
    # def __call__(self, *args, **kwargs) -> 'Unpickled':
    #     o = Unpickled(*args, **kwargs)
    #     o.origin = self
    #     return o


def _create_global(module: str, name: str) -> type[Unpickled]:
    return type(f'Unpickled_{module}_{name}', (Unpickled,), {
        'origin': (module, name)
    })


class Unpickler(pickle.Unpickler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__cached_globals: dict[OriginName, type[Unpickled]] = {}

    def find_class(self, module: str, name: str):
        combined = (module, name)
        if combined not in self.__cached_globals:
            self.__cached_globals[combined] = _create_global(module, name)
        return self.__cached_globals[combined]


ResolveMappingCallback = Callable[..., Any]
ResolveMappingFallbackCallback = Callable[
    [Union[tuple[str, str], Unpickled, None],
     list[Any], dict[Any, Any]], Any]
ResolveMapping = dict[tuple[str, str], ResolveMappingCallback]


def _resolve(mapping: ResolveMapping,
             fallback: Optional[ResolveMappingFallbackCallback],
             o: Any) -> Any:
    resolve = functools.partial(_resolve, mapping, fallback)
    if isinstance(o, Unpickled):
        if o.origin is None or o.origin not in mapping:
            if fallback is not None:
                return fallback(o.origin, resolve(o.args), resolve(o.kwargs))
        return mapping[o.origin](*resolve(o.args), **resolve(o.kwargs))
    elif type(o) is list:
        return list(map(resolve, o))
    elif type(o) is tuple:
        return tuple(map(resolve, o))
    elif type(o) is set:
        return set(map(resolve, o))
    elif type(o) is frozenset:
        return frozenset(map(resolve, o))
    elif type(o) is dict:
        return dict(map(resolve, o.items()))
    elif isinstance(o, (int, str, bool, float)) or o is None:
        return o
    else:
        logging.warning(f"Unhandled: {type(o)}")
        return o


def resolve(o: Any, mapping: ResolveMapping,
            fallback: Optional[ResolveMappingFallbackCallback] = None) -> Any:
    # TODO: Currently shared objects won't be shared
    return _resolve(mapping, fallback, o)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    import argparse
    import pprint
    parser = argparse.ArgumentParser()
    parser.description = "Parse a Python pickle file"

    parser.add_argument("pickle", type=str,
                        help="Path to pickle file to unpickle")

    args = parser.parse_args()
    with open(args.pickle, 'rb') as f:
        unpickled = Unpickler(f).load()
        pprint.pp(unpickled, width=200)
