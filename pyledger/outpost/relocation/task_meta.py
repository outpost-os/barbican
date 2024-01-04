# SPDX-FileCopyrightText: 2023 Ledger SAS
# SPDX-License-Identifier: Apache-2.0


import cstruct

EXIT_NORESTART = "norestart"
EXIT_RESTART = "restart"
EXIT_PANIC = "panic"
EXIT_PERIODIC_RESTART = "periodic"
EXIT_RESET = "reset"

EXIT_MODES = [
    EXIT_NORESTART,
    EXIT_RESTART,
    EXIT_PANIC,
    EXIT_PERIODIC_RESTART,
    EXIT_RESET,
]

class JobFlags(cstruct.MemCStruct):
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __def__ = """

    /**
     * These are job start mode possible values (bitfield)
     */
    #define JOB_FLAG_START_NOAUTO 0
    #define JOB_FLAG_START_AUTO   1

    /**
     * These are job exit mode possible values (bitfield)
     */
    #define JOB_FLAG_EXIT_NORESTART       0
    #define JOB_FLAG_EXIT_RESTART         1
    #define JOB_FLAG_EXIT_PANIC           2
    #define JOB_FLAG_EXIT_PERIODICRESTART 3
    #define JOB_FLAG_EXIT_RESET           4

    struct {
        uint32_t raw;
    }
    """

    @property
    def autostart_mode(self) -> int:
        return self.raw & 0x1 == cstruct.getdef('JOB_FLAG_START_AUTO')

    @autostart_mode.setter
    def autostart_mode(self, auto: bool) -> None:
        start_mode = int()
        self.raw = self.raw & 0xfffffffe

        if auto:
            start_mode = cstruct.getdef('JOB_FLAG_START_AUTO')
        else:
            start_mode = cstruct.getdef('JOB_FLAG_START_NOAUTO')

        self.raw = self.raw | (start_mode & 0x1)


    @property
    def exit_mode(self) -> int:
        return (self.raw >> 1) & 0x7

    @exit_mode.setter
    def exit_mode(self, mode: str) -> None:
        _exit_mode = {
            EXIT_NORESTART: cstruct.getdef("JOB_FLAG_EXIT_NORESTART"),
            EXIT_RESTART: cstruct.getdef("JOB_FLAG_EXIT_RESTART"),
            EXIT_PANIC: cstruct.getdef("JOB_FLAG_EXIT_PANIC"),
            EXIT_PERIODIC_RESTART: cstruct.getdef("JOB_FLAG_EXIT_PERIODICRESTART"),
            EXIT_RESET: cstruct.getdef("JOB_FLAG_EXIT_RESET"),
        }

        mode = _exit_mode[mode]
        self.raw = self.raw & 0xfffffff1
        self.raw = self.raw | ((mode & 0x7) << 1)

class TaskHandle(cstruct.MemCStruct):
    """XXX: Task handle family is 0, rerun is a runtime counter for running index
    """
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __def__ = """

    struct {
        uint32_t raw;
    }
    """


    _id_shift = 13
    _id_mask = (0x0000ffff << _id_shift)


    @property
    def id(self) -> int:
        return (self.raw & self._id_mask) >> self._id_shift

    @id.setter
    def id(self, id: int) -> None:
        self.raw = self.raw & (~self._id_mask)
        self.raw = self.raw | (id << self._id_shift & (self._id_mask))

class TaskMeta(cstruct.MemCStruct):
    """Task meta structure with padding
    As a variable of type TaskMeta is align on 8 bytes boundary (due to uint64 first field)
    There is padding at the end to align size on 8 bytes to.
    """
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __def__ = """

    typedef struct JobFlags job_flags_t;
    typedef struct TaskHandle taskh_t;

    struct {
        uint64_t magic;
        uint32_t version;

        taskh_t handle;

        uint8_t priority;
        uint8_t quantum;

        uint8_t pad1[2];

        uint32_t capabilities;
        job_flags_t flags;

        uint8_t domain;
        uint8_t pad2[3];

        uint32_t s_text;
        uint32_t text_size;
        uint32_t s_got;
        uint32_t got_size;
        uint32_t rodata_size;
        uint32_t data_size;
        uint32_t bss_size;
        uint32_t heap_size;
        uint32_t s_svcexchange;

        uint16_t stack_size;
        uint16_t entrypoint_offset;
        uint16_t finalize_offset;

        uint8 num_shm;
        uint8_t pad3;
        uint32_t shms[4];

        uint8 num_dev;
        uint8_t pad4[3];
        uint32_t devs[4];

        uint8 num_dma;
        uint8_t pad5[3];
        uint32_t dmas[4];

        uint8_t task_hmac[32];
        uint8_t metadata_hmac[32];
        uint8_t pad6[4];
    }
    """
