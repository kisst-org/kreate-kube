import os
import logging

from ..kore._korecli import kreate_files as kreate_files
from ..krypt import _krypt, KryptCli, KryptKreator

logger = logging.getLogger(__name__)


class KubeKreator(KryptKreator):
    def kreate_cli(self):
        return KubeCli(self)


class KubeCli(KryptCli):
    def __init__(self, kreator):
        super().__init__(kreator)
        self.add_subcommand(build, [], aliases=["b"])
        self.add_subcommand(diff, [], aliases=["d"])
        self.add_subcommand(apply, [], aliases=["a"])
        self.add_subcommand(test, [], aliases=["t"])
        self.add_subcommand(testupdate, [], aliases=["tu"])


def build(args):
    """output all the resources"""
    app = kreate_files(args)
    cmd = f"kustomize build {app.target_dir}"
    logger.info(f"running: {cmd}")
    os.system(cmd)


def diff(args):
    """diff with current existing resources"""
    app = kreate_files(args)
    cmd = (f"kustomize build {app.target_dir} "
           f"| kubectl --context={app.env} -n {app.namespace} diff -f - ")
    logger.info(f"running: {cmd}")
    os.system(cmd)


def apply(args):
    """apply the output to kubernetes"""
    app = kreate_files(args)
    cmd = f"kustomize build {app.target_dir} | kubectl apply --dry-run -f - "
    logger.info(f"running: {cmd}")
    os.system(cmd)


def test(args):
    """test output against test.out file"""
    _krypt._dekrypt_testdummy = True  # Do not dekrypt secrets for testing
    app = kreate_files(args)
    cmd = (f"kustomize build {app.target_dir} | diff "
           f"{app.appdef.dir}/expected-output-{app.name}-{app.env}.out -")
    logger.info(f"running: {cmd}")
    os.system(cmd)


def testupdate(args):
    """update test.out file"""
    _krypt._dekrypt_testdummy = True  # Do not dekrypt secrets for testing
    app = kreate_files(args)
    cmd = (f"kustomize build {app.target_dir} "
           f"> {app.appdef.dir}/expected-output-{app.name}-{app.env}.out")
    logger.info(f"running: {cmd}")
    os.system(cmd)
