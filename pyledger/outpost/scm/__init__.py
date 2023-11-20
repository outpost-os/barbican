from .git import Git
from .scm import ScmBaseClass

__all__ = ['Git']

SCM_FACTORY_DICT = {
    "git": Git,
    # TODO tarball, etc.
}

def scmCreate(package) -> ScmBaseClass:
    ScmType = SCM_FACTORY_DICT[package.method]
    return ScmType(package)
