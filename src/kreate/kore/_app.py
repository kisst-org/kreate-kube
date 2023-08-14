import os
import shutil
import logging

from ._core import DictWrapper
from ._appdef import AppDef

logger = logging.getLogger(__name__)


class App():
    def __init__(self, appdef: AppDef):
        self.name = appdef.name
        self.env = appdef.env
        self.appdef = appdef
        self.values = appdef.values
        self.komponents = []
        self._kinds = {}
        self.aliases = {}
        self.strukture = appdef.calc_strukture()

    def add_alias(self, kind: str, *aliases: str) -> None:
        if kind in self.aliases:
            self.aliases[kind].append(aliases)
        else:
            self.aliases[kind] = list(aliases)

    def get_aliases(self, kind: str):
        result = [kind, kind.lower()]
        if kind in self.aliases:
            result.append(*self.aliases[kind])
        return result

    def add(self, res) -> None:
        if not res.skip:
            self.komponents.append(res)
        map = self._kinds.get(res.kind, None)
        if map is None:
            map = DictWrapper({})
            self.get_aliases(res.kind)
            for alias in self.get_aliases(res.kind):
                self._kinds[alias] = map

        map[res.shortname] = res

    def __getattr__(self, attr):
        if attr in self.__dict__ or attr == "_dict":
            return super().__getattribute__(attr)
        return self._kinds.get(attr, None)

    def kreate_komponent(self, kind: str, shortname: str = None, **kwargs):
        raise NotImplementedError(
            f"can not create komponent for {kind}.{shortname}")

    def aktivate(self):
        for komp in self.komponents:
            logger.debug(
                f"aktivating {komp.kind}.{komp.shortname}")
            komp.aktivate()

    def kreate_files(self):
        if os.path.exists(self.target_dir) and os.path.isdir(self.target_dir):
            shutil.rmtree(self.target_dir)
        os.makedirs(self.target_dir, exist_ok=True)

        for komp in self.komponents:
            if (komp.filename):
                logger.info(f"kreating file {komp.filename}")
                komp.kreate_file()
            else:
                logger.info(f"skipping file for {komp.kind}.{komp.shortname}")

    def _shortnames(self, kind: str) -> list:
        if kind in self.strukture:
            return self.strukture[kind].keys()
        return []

    def kreate_komponents_from_strukture(self):
        for kind in sorted(self.strukture.keys()):
            if kind in self.kind_classes:
                for shortname in sorted(self.strukture[kind].keys()):
                    logger.debug(f"kreating komponent {kind}.{shortname}")
                    self.kreate_komponent(kind, shortname)
            elif kind != "default":
                logger.warning(f"Unknown toplevel komponent {kind}")
