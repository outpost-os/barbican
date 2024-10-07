# SPDX-FileCopyrightText: 2024 Ledger SAS
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from pathlib import Path
from random import choices
from string import ascii_letters

from git import Repo
from git.exc import GitCommandError

from outpost.barbican.scm import scm_create
from outpost.barbican.scm.git import Git


class GitTestBase:
    @pytest.fixture(scope="class")
    def private_dir(self, tmp_path_factory):
        return tmp_path_factory.mktemp(type(self).__name__)

    @pytest.fixture(scope="class")
    def clone_dir(self, private_dir):
        filename = private_dir / "cloned"
        return filename

    def add_and_commit_random_file(self, repo):
        file = Path(repo.working_tree_dir, "".join(choices(ascii_letters, k=16)))
        file.touch()
        repo.index.add(file)
        repo.index.commit(f"Adding {file.name}")

    @staticmethod
    def set_repo_default_user_config(repo: Repo) -> None:
        name: str
        email: str

        with repo.config_reader(config_level="repository") as reader:
            name = reader.get_value("user", "name", "CI Joe")
            email = reader.get_value("user", "email", "ci.joe@ci.com")

        with repo.config_writer(config_level="repository") as writer:
            writer.set_value("user", "name", name)
            writer.set_value("user", "email", email)

    @pytest.fixture(scope="class")
    def origin(self, private_dir):
        origin_dir = private_dir / "origin"
        # initialize empty git repository
        origin_repo = Repo.init(origin_dir)
        self.set_repo_default_user_config(origin_repo)
        self.add_and_commit_random_file(origin_repo)
        return origin_repo

    @pytest.fixture(scope="class")
    def default_branch(self, origin):
        # master by default, until git v2.28, this is hardcoded.
        # from git v2.28, this can be changed through `init.defaultBranch`
        default_branch = "master"
        major, minor, _ = origin.git.version_info
        if major >= 2 and minor >= 28:
            try:
                default_branch = origin.git.config(["--global", "init.defaultBranch"])
            except GitCommandError:
                pass
        return default_branch


class GitTestProjectMock:
    class _Parent:
        class _Path:
            def __init__(self, src_dir):
                self.src_dir = src_dir

        def __init__(self, src_dir):
            self.path = GitTestProjectMock._Parent._Path(src_dir)

    def __init__(self, path, name, uri, revision):
        self.name = name
        self.scm = {
            "git": {
                "uri": uri,
                "revision": revision,
            }
        }
        self.src_dir = path / name
        self.parent = GitTestProjectMock._Parent(path)

    def post_update_hook(self): ...
    def post_download_hook(self): ...


def git_test_create(path, name, uri, revision):
    prj_mock = GitTestProjectMock(path, name, uri, revision)
    repo = scm_create(prj_mock)
    assert isinstance(repo, Git)
    return repo


class TestGit(GitTestBase):
    @pytest.mark.dependency()
    def test_download_branch_ref(self, private_dir, origin, default_branch):
        repo = git_test_create(private_dir, "test", origin.git_dir, default_branch)
        repo.download()
        assert repo._repo.head.commit == origin.head.commit
        self.add_and_commit_random_file(origin)
        assert repo._repo.head.commit != origin.head.commit

    @pytest.mark.dependency(depends=["TestGit::test_download_branch_ref"])
    def test_update_same_branch(self, private_dir, origin, default_branch):
        repo = git_test_create(private_dir, "test", origin.git_dir, default_branch)
        assert repo._repo.head.commit != origin.head.commit
        repo.update()
        assert repo._repo.head.commit == origin.head.commit
        self.add_and_commit_random_file(origin)
        assert repo._repo.head.commit != origin.head.commit

    @pytest.mark.dependency(depends=["TestGit::test_update_same_branch"])
    def test_update_to_commit(self, private_dir, origin):
        repo = git_test_create(private_dir, "test", origin.git_dir, str(origin.head.commit))
        assert repo._repo.head.commit != origin.head.commit
        repo.update()
        assert repo._repo.head.commit == origin.head.commit
        self.add_and_commit_random_file(origin)
        assert repo._repo.head.commit != origin.head.commit

    @pytest.mark.dependency(depends=["TestGit::test_update_same_branch"])
    def test_update_from_commit_to_branch(self, private_dir, origin, default_branch):
        repo = git_test_create(private_dir, "test", origin.git_dir, default_branch)
        assert repo._repo.head.commit != origin.head.commit
        repo.update()
        assert repo._repo.head.commit == origin.head.commit
        self.add_and_commit_random_file(origin)
        assert repo._repo.head.commit != origin.head.commit

    @pytest.mark.dependency()
    def test_download_commit(self, private_dir, origin):
        commit = origin.head.commit
        repo = git_test_create(private_dir, "test_commit", origin.git_dir, str(commit))
        self.add_and_commit_random_file(origin)
        repo.download()
        assert repo._repo.head.commit == commit
        assert repo._repo.head.commit != origin.head.commit

    def test_download_invalid_ref(self, private_dir, origin):
        with pytest.raises(Exception):
            repo = git_test_create(private_dir, "test_invalid_ref", origin.git_dir, "pouette")
            repo.download()

    def test_download_invalid_commit(self, private_dir, origin):
        with pytest.raises(Exception):
            repo = git_test_create(
                private_dir, "test_invalid_commit", origin.git_dir, str("a" * 40)
            )
            repo.download()
