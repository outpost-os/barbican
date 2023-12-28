# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

from pyledger.outpost.utils import pow2_greatest_divisor, pow2_round_up

def test_pow2_round_up():
    _test_set = {
        0: 1,
        1: 1,
        2: 2,
        3: 4,
        999: 1024,
        2*1024 - 1: 2*1024,
        4*1024 + 512 + 32: 8*1024,
        4*1024 + 512 + 32 - 5: 8*1024,
        4*1024 + 512: 8*1024,
        4*1024 + 512 - 5 : 8*1024,
        4*1024: 4*1024,
        28954: 32768,
        48547: 65536,
    }

    for value, expected in _test_set.items():
        assert pow2_round_up(value) == expected

def test_pow2_greatest_divisor():
    _test_set = {
        1: 1,
        2: 2,
        3: 1,
        999: 1,
        2*1024 - 1: 1,
        4*1024 + 512 + 32: 32,
        4*1024 + 512: 512,
        4*1024: 4*1024,
    }

    for value, expected in _test_set.items():
        assert pow2_greatest_divisor(value) == expected
