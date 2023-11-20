import subprocess

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

    def _download(self) -> None:
        self.clone()
        self.update()

    def _update(self) -> None:
        self.fetch()
        self.checkout()
