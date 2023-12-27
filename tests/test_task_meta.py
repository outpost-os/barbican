# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: Apache-2.0

from pyledger.outpost.relocation.task_meta import TaskMeta, JobFlags, TaskHandle


def test_jobflags_struct_size():
    job_flags = JobFlags()
    assert job_flags.sizeof() == 4

def test_jobflags_autostart_mode():
    job_flags = JobFlags()
    job_flags.autostart_mode = True
    assert job_flags.autostart_mode == True
    job_flags.autostart_mode = False
    assert job_flags.autostart_mode == False

def test_jobflags_exit_mode():
    _expected = {
        "norestart": 0,
        "restart": 1,
        "panic": 2,
        "periodic": 3,
        "reset": 4,
    }
    job_flags = JobFlags()

    for mode, value in _expected.items():
        job_flags.exit_mode = mode
        assert job_flags.exit_mode == value

def test_jobflags_serialize():
    job_flags = JobFlags()
    job_flags.autostart_mode = True
    assert job_flags.pack() == b"\x01\x00\x00\x00"
    job_flags.exit_mode = "panic"
    assert job_flags.pack() == b"\x05\x00\x00\x00"
    job_flags.exit_mode = "reset"
    assert job_flags.pack() == b"\x09\x00\x00\x00"
    job_flags.autostart_mode = False
    assert job_flags.pack() == b"\x08\x00\x00\x00"
    job_flags.exit_mode = "periodic"
    assert job_flags.pack() == b"\x06\x00\x00\x00"
    job_flags.exit_mode = "norestart"
    assert job_flags.pack() == b"\x00\x00\x00\x00"

def test_taskh_size():
    taskh = TaskHandle()
    assert taskh.sizeof() == 4

def test_taskh_id():
    taskh = TaskHandle()
    for id in [42, 12354, 0xffff, 0, 42]:
        taskh.id = id
        assert taskh.id == id

def test_taskh_serialize():
    taskh = TaskHandle()
    for id in [42, 12354, 0xffff, 0, 42]:
        taskh.id = id
        expected = int.to_bytes((id << TaskHandle._id_shift) & TaskHandle._id_mask, taskh.sizeof(), "little")
        assert taskh.pack() == expected


def test_taskmeta():
    task_meta = TaskMeta()
    task_meta.handle.id = 42
    task_meta.flags.autostart_mode = True
    task_meta.flags.exit_mode = "panic"
