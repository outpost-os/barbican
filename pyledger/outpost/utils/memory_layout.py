# SPDX-FileCopyrightText: 2024 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

from collections import UserList, UserDict
import json
from os import PathLike
import typing as T


# XXX: add json schema validation here
# a MemoryLayout is an array of memoryRegion
# Memory region is a dict w/ name, saddr, size,(TODO: [perm,] )
# a MemoryRegion may have a, array of subregion for plotting (svc, heap, stack , etc.)
# TODO: Add JsonDecoder


class MemoryRegion(UserDict):
    """Memory region user defined dictionary

    MemoryRegion is a python UserDict with a fixed set of possible keys
     - name: memory region name
     - start_addr: memory region start address
     - size: memory region size
     - subregion: subset of inner region, optional
    """

    def __init__(self, name: str, start_addr: int, size: int) -> None:
        """Initialiazer

        Parameters are defined at initialization time and are non mutable

        Parameters
        ----------
        name
            memory region name
        start_addr
            memory region start address
        size
            memory region size in bytes
        """
        super(MemoryRegion, self).__init__()
        self.data["name"] = name
        self.data["start_addr"] = start_addr
        self.data["size"] = size

    def __setitem__(self, key, val):
        """override :py:func:`__setitem__`

        Direct call to setitem is forbidden for MemoryRegion

        Raises
        ------
        Exception
        """
        raise Exception("MemoryRegion set item is forbidden")

    def append_subregions(self, subregion: "MemoryRegion") -> None:
        """Append a subregion to the given region

        Parameters
        ----------
        subregion
            Memory region to append
        """
        if "subregion" not in self.data.keys():
            self.data["subregion"] = []
        self.data[subregion].append(subregion)


class _JSONEncoder(json.JSONEncoder):
    """Custom json encoder for :py:class:`MemoryRegion` and :py:class:`MemoryLayout`
    Derived from :py:class:`json.JSONEncoder`
    """

    def default(self, obj: T.Any) -> T.Any:
        """override :py:meth:`json.JSONEncoder.default`

        Parameters
        ----------
        obj
            python object to serialize in json

        Notes
        -----
        As :py:class:`MemoryRegion`(resp. :py:class:`MemoryLayout`) derived from standard built-in
        type :py:class:`dict` (resp. :py:class:`list`), one only need to forward the internal data
        representation.
        """
        if isinstance(obj, (MemoryLayout, MemoryRegion)):
            return obj.data
        return super().default(obj)


class MemoryLayout(UserList):
    """Memory Layout

    Memory layout is a user defined list that can only accepts :py:class:`MemoryRegion` items.
    """

    def __setitem__(self, index: T.Any, item: T.Any) -> None:
        if type(item) is MemoryRegion:
            self.data[index] = item
        else:
            raise TypeError("Item must be a MemoryRegion.")

    def append(self, item: MemoryRegion) -> None:
        """override :py:meth:`list.append`

        Parameters
        ----------
        item
            :py:class:`MemoryRegion` to append to the list

        Raises
        ------
        TypeError: if item type is not :py:class:`MemoryRegion`
        """
        if type(item) is MemoryRegion:
            self.data.append(item)
        else:
            raise TypeError("Item must be a MemoryRegion.")

    def save_as_json(self, file: PathLike) -> None:
        """Save MemoryLayout as json file

        Parameters
        ----------
        file
            Path to json file to write
        """
        with open(file, "w") as f:
            json.dump(self, f, indent=4, cls=_JSONEncoder)
