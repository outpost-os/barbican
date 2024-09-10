# SPDX-FileCopyrightText: 2023 - 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

from git import Repo, RemoteProgress
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from ..logger import logger

from .scm import ScmBaseClass

from typing import TYPE_CHECKING, Optional, cast

if TYPE_CHECKING:
    from ..package import Package

from ..console import console


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
        self._progressbar = console.progress_bar()

    def __del__(self) -> None:
        if self._progressbar.live.is_started:
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
            # Start rendering at first task insertion
            if not self._progressbar.live.is_started:
                self._progressbar.start()

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
        self._repo: Repo
        try:
            self._repo = Repo(package.src_dir)
        except NoSuchPathError:
            logger.debug(f"{self.name} not cloned yet")
        except InvalidGitRepositoryError:
            logger.warning(f"{self.name} not a git repository")
            # XXX: Fatal or rm and clone ?

    @staticmethod
    def is_hex_sha(string: str) -> bool:
        """Check if given is an commit sha in hex.

        Parameters
        ----------
        string: str
            input string

        Returns
        -------
        True if string matches git sha format
        """
        return Repo.re_hexsha_only.match(string)

    def is_valid_commit_sha(self, sha: str) -> bool:
        return self.is_hex_sha(sha) and self._repo.is_valid_object(sha)

    def _reset(self, revision: str, hard: bool = True) -> None:
        args: list(str) = []
        if hard:
            args.append("--hard")
        args.append(str(self.revision))
        self._repo.git.reset(args)

    def _reset_head(self, sha: str) -> None:
        if not self.is_valid_commit_sha(sha):
            raise ValueError
        self._repo.head.reset(sha)

    def _checkout(self, sha: str) -> None:
        if not self.is_valid_commit_sha(sha):
            raise ValueError
        self._repo.git.checkout(sha)

    def clone(self) -> None:
        if self.is_hex_sha(self.revision):
            self._repo = Repo.clone_from(
                url=self.url,
                to_path=self.name,
                progress=GitProgressBar(),  # type: ignore
                no_checkout=True,
            )
            self._checkout(self.revision)
        else:
            self._repo = Repo.clone_from(
                url=self.url,
                to_path=self.name,
                progress=GitProgressBar(),  # type: ignore
                branch=self.revision,
                single_branch=True,
            )
        logger.info(f"git clone {self.name}@{self.revision} ({self._repo.head.commit})")

    def fetch(self) -> None:
        logger.info(f"git fetch {self.name} origin/{self.revision}")

        fetch_infos = self._repo.remotes.origin.fetch(refspec=self.revision, progress=GitProgressBar())  # type: ignore

        # this shouldn't occur
        if len(fetch_infos) != 1:
            raise Exception

        fetch_info = fetch_infos[0]

        if self.is_hex_sha(self.revision):
            self._checkout(self.revision)
        else:
            if self._repo.head.is_detached or self._repo.active_branch != self.revision:
                self._repo.git.switch(self.revision)
            self._reset_head(str(fetch_info.commit))
            self._reset(str(fetch_info.commit))

    def clean(self) -> None:
        logger.info(f"git clean {self.name}")
        self._repo.git.clean(["-ffdx"])

    def _download(self) -> None:
        if hasattr(self, "_repo"):
            console.message(f"[b]{self.name} already clone, skip[/b]")
            return

        console.message(
            f"[b]Cloning git repository [i]{self.name}[/i] (revision={self.revision})...[/b]"
        )
        self.clone()
        with console.status("Running post clone hook"):
            self._package.post_download_hook()
        console.message("[b]Done.[/b]")

    def _update(self) -> None:
        if self._repo.is_dirty():
            console.warning(f"{self.name} is dirty, cannot update")
            return

        console.message(f"[b]Updating [i]{self.name}[/i] (revision={self.revision})...[/b]")
        old_ref = self._repo.head.commit

        self.fetch()
        self.clean()

        new_ref = self._repo.head.commit

        if old_ref == new_ref:
            console.message("[b]Already up-to-date[/b]")
        else:
            console.message(f"[b][i]{self.name}[/i] updated {old_ref}→ {new_ref}[/b]")

        with console.status("Running post update hook"):
            self._package.post_update_hook()
