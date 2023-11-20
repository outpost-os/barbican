import os
from pyledger.outpost.scm import scmCreate

class Package():
    def __init__(self, name, parent_project, config_node: dict) -> None:
        self._name = name
        self._parent = parent_project
        self._config = config_node
        self._scm = scmCreate(self)

    @property
    def name(self) -> str:
        return self._name

    @property
    def sourcedir(self) -> str:
        return os.path.join(self._parent.sourcedir, self.name)

    @property
    def builddir(self) -> str:
        return os.path.join(self._parent.builddir, self.name)

    @property
    def stagingdir(self) -> str:
        return self._parent.stagingdir

    @property
    def parent(self):
        return self._parent

    @property
    def deps(self):
        # XXX sanity checks
        return self._config["deps"] if "deps" in self._config else list()

    def download(self) -> None:
        self._scm.download()

    def __getattr__(self, attr):
        return self._config[attr] if attr in self._config else None
