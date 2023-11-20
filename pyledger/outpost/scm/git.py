import subprocess
import os

from pyledger.outpost.utils import working_directory_attr
from pyledger.outpost import logger

from .scm import ScmBaseClass

class Git(ScmBaseClass):
    def __init__(self, package) -> None:
        self._package = package

    def clone(self) -> None:
        subprocess.run(["git", "clone", f"{self.url}", f"{self.name}"])

    def fetch(self) -> None:
        subprocess.run(["git", "fetch", f"{self.url}", f"{self.revision}"])

    def checkout(self) -> None:
        subprocess.run(["git", "checkout", f"{self.revision}"])

    def git_toplevel_directory(self) -> str:
        """return the git top level directory from cwd"""
        return subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True).stdout.strip().decode()

    @working_directory_attr("sourcedir")
    def is_valid(self) -> bool:
       return self.git_toplevel_directory() == os.getcwd()

    def _download(self) -> None:
        skip_clone = False
        if os.path.isdir(self._package.sourcedir):
            skip_clone = self.is_valid()
            logger.info("Already donwload, step skipped")

        if not skip_clone:
            self.clone()
            self.update()

    def _update(self) -> None:
        self.fetch()
        self.checkout()
