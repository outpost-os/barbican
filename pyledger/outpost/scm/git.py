# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import subprocess

from git import Repo, RemoteProgress
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from .. import logger

from .scm import ScmBaseClass

from typing import TYPE_CHECKING, Optional, cast

if TYPE_CHECKING:
    from pyledger.outpost.package import Package

from rich import print, progress, status


class GitProgressBar(RemoteProgress):
    OP_CODES = [
        "BEGIN",
        "CHECKING_OUT",
        "COMPRESSING",
        "COUNTING",
        "END",
        "FINDING_SOURCES",
        "RECEIVING",
        "RESOLVING",
        "WRITING",
    ]

    OP_CODE_MAP = {getattr(RemoteProgress, _op_code): _op_code for _op_code in OP_CODES}

    def __init__(self) -> None:
        super().__init__()
        self._progressbar = progress.Progress(
            progress.SpinnerColumn(),
            progress.TextColumn("[progress.description]{task.description}"),
            progress.BarColumn(),
            progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            "eta",
            progress.TimeRemainingColumn(),
            progress.TextColumn("{task.fields[message]}"),
            transient=False,
        )
        self._progressbar.start()
        # self._active_task: Optional[progress.TaskID] = None

    def __del__(self) -> None:
        self._progressbar.stop()

    @classmethod
    def get_curr_op(cls, op_code: int) -> str:
        """Get OP name from OP code."""
        op_code_masked = op_code & cls.OP_MASK
        return cls.OP_CODE_MAP.get(op_code_masked, "?").title()

    def update(
        self,
        op_code: int,
        cur_count: str | float,
        max_count: str | float | None = None,
        message: str | None = "",
    ) -> None:
        # Start new bar on each BEGIN-flag
        if op_code & self.BEGIN:
            self.curr_op = self.get_curr_op(op_code)
            self._active_task = self._progressbar.add_task(
                description=self.curr_op,
                total=cast(Optional[float], max_count),
                message=message,
            )

        self._progressbar.update(
            task_id=self._active_task,
            completed=cast(Optional[float], cur_count),
            message=message,
        )

        # End progress monitoring on each END-flag
        if op_code & self.END:
            self._progressbar.update(
                task_id=self._active_task,
                message=f"[bright_black]{message}",
            )
            del self._active_task


class Git(ScmBaseClass):
    def __init__(self, package: "Package") -> None:
        super().__init__(package)
        self._repo: Optional[Repo] = None
        try:
            self._repo = Repo(package.sourcedir)
        except NoSuchPathError:
            logger.debug(f"{self.name} not cloned yet")
        except InvalidGitRepositoryError:
            logger.warning(f"{self.name} not a git repository")
            # XXX: Fatal or rm and clone ?

    def clone(self) -> None:
        self._repo = Repo.clone_from(
            url=self.url,
            to_path=self.name,
            progress=GitProgressBar(),  # type: ignore
            branch=self.revision,
        )

    def fetch(self) -> None:
        subprocess.run(["git", "fetch", "--all"])

    def checkout(self) -> None:
        subprocess.run(["git", "switch", f"{self.revision}"])

    def git_toplevel_directory(self) -> str:
        """return the git top level directory from cwd"""
        return (
            subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True)
            .stdout.strip()
            .decode()
        )

    def _download(self) -> None:
        if self._repo:
            print(f"[b]{self.name} already clone, skip[/b]")
            logger.info(f"{self.name} already clone, skip")
            return

        print(f"[b]Cloning git repository [i]{self.name}[/i] (revision={self.revision})... [/b]")
        self.clone()
        with status.Status("  Running post clone hook", spinner="moon"):
            self._package.post_download_hook()
        print("[b]Done.[/b]")

    def _update(self) -> None:
        self.fetch()
        self.checkout()
        self._package.post_update_hook()
