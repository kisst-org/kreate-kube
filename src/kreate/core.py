import os
import sys
import jinja2
import pkgutil
from collections import UserDict, UserList
from collections.abc import Mapping, Sequence
import logging

from ruamel.yaml import YAML
from . import templates

logger = logging.getLogger(__name__)

class DictWrapper(UserDict):
    def __init__(self, dict):
        # do not copy the original dict as the normal UserDict does
        # but wrap the original so that updates go to the original
        # __setattr__ is used, because the data attribute does not exist yet
        super().__setattr__("data", dict)

    def __getattr__(self, attr):
        if attr not in self.data:
            raise AttributeError(f"could not find attribute {attr} in {self}")
        else:
            return wrap(self.data[attr])

    def __setattr__(self, attr, val):
        self.data[attr] = val


class ListWrapper(UserList):
    def __init__(self, seq) -> None:
        # do not copy the original list as the normal UserList does
        # but wrap the original so that updates go to the original
        self.data = seq

    def __getitem__(self, idx):
        # Wrap the returned value
        return wrap(self._seq[idx])

def wrap(obj):
    if isinstance(obj, Sequence) and not isinstance(obj, ListWrapper):
        return ListWrapper(obj)
    if isinstance(obj, Mapping) and not isinstance(obj, DictWrapper):
        return DictWrapper(obj)
    return obj



class DeepChain(Mapping):
    def __init__(self, *maps: Mapping):
        self._maps = maps

    def __getitem__(self, key):
        all_vals = tuple(m.get(key, None) for m in self._maps)
        vals = tuple(v for v in all_vals if v is not None)
        nrof_map_vals = sum(isinstance(v,Mapping) for v in vals)
        if nrof_map_vals>0:
            if nrof_map_vals < len(vals):
                raise AttributeError(f"key {key} is not mergeable into dictionary since not all values are maps {vals}")
            args=list(m for m in vals)
            return DeepChain(*args)
        if len(vals)>0:
            return vals[0]
        return None

    def __getattr__(self, attr):
        if attr not in self:
            raise AttributeError(f"DeepChain object could not find attribute {attr} in {self}")
        else:
            return self[attr]

    def get(self, attr, default):
        if attr in self:
            return self[attr]
        return default

    def keys(self):
        result = set()
        for m in self._maps:
            for k in m.keys():
                result.add(k)
        return result

    def __len__(self):
        return len(self.keys())

    def __iter__(self):
        return iter(self.keys())

    def __contains__(self, key):
        for m in self._maps:
            if key in m:
                return True
        return False

    def __repr__(self):
        return f"DeepChain({self._maps})"


    def pprint(self, map=None, indent="", field=None):
        indent_step = "  "
        if map is None:
            map = self
        if field:
            print(f"{field}:")
            indent = indent + indent_step
            map = map.get(field,{})
        for key in sorted(map.keys()):
            val = map.get(key, None)
            if isinstance(val, Mapping):
                if len(val) == 0:
                    print(f"{indent}{key}: "+"{}")
                else:
                    print(f"{indent}{key}:")
                    self.pprint(map=val, indent=indent + indent_step)
            elif isinstance(val, str):
                print(f"{indent}{key}: {val}")
            elif isinstance(val, Sequence):
                print(f"{indent}{key}:")
                for v in val:
                    print(f"{indent}- {v}")
            else:
                print(f"{indent}{key}: {val}")


parser = YAML()

def load_yaml(filename: str, package=None, warn: bool = True) -> Mapping:
    if package:
        data = pkgutil.get_data(package, filename).decode('utf-8')
        return parser.load(data)
    if os.path.exists(filename):
        with open(filename) as f:
            return parser.load(f)
    else:
        if warn:
            logger.warn(f"skipping yaml file {filename}")
            return {}
        else:
            raise(ValueError(f"could not find yaml file {filename}"))

class YamlBase:
    def __init__(self, template: str):
        self.template = template

    def load_yaml(self):
        parsed = parser.load(self._render())
        self.yaml = wrap(parsed)

    def save_yaml(self, outfile) -> None:
        logger.info(f"kreating {outfile}")
        with open(outfile, 'wb') as f:
            parser.dump(self.yaml.data, f)

    def _template_vars(self):
        return {}

    def _render(self, outfile=None):
        # TODO: make template package flexible (or directory)
        template_data = pkgutil.get_data(
            templates.__package__,
            self.template
        ).decode('utf-8')
        tmpl = jinja2.Template(
            template_data,
            undefined=jinja2.StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True
        )
        vars = self._template_vars()
        return tmpl.render(vars)


class Values():
    def __init__(self):
        self._map = {}

    def add_map(self, map: Mapping):
        self._map.update(map)

    def add_yaml(self, filename: str, package=None):
        self._map.update(load_yaml(filename, package))

    def add_obj(self, obj):
        d = { key: obj.__dict__[key] for key in obj.__dict__.keys() if not key.startswith("_")}
        self._map.update(d)

    def add_jinyaml(self, filename: str, package=None):
        self._map.update(load_yaml(filename, package))

def load_jinyaml(filename: str, vars: Mapping):
    #if not os.path.exists(filename):
    #    raise FileNotFoundError(filename)
    logger.info(f"loading config {filename}")
    with open(filename) as f:
        tmpl = jinja2.Template(
            f.read(),
            undefined=jinja2.StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True
        )
        return parser.load(tmpl.render(vars))


class AppConfig():
    def __init__(self, env, filename="appdef.yaml", *args):
        dir = os.path.dirname(filename)
        self._values = Values()
        self._maps = []
        if filename:
            vars = { "env": env }
            self.appdef = load_jinyaml(filename, vars)
            self._values.add_map(self.appdef)
            for file in self.appdef.get("value_files",[]):
                self._values.add_yaml(f"{dir}/{file}")
            for file in self.appdef.get("config_files"):
                self.add_file(f"{dir}/{file}")


    def add_file(self, filename):
        if os.path.exists(filename):
            logger.info(f"loading config {filename}")
            with open(filename) as f:
                tmpl = jinja2.Template(
                    f.read(),
                    undefined=jinja2.StrictUndefined,
                    trim_blocks=True,
                    lstrip_blocks=True
                )
                vars = { "val": self.values() }
                m = parser.load(tmpl.render(vars))
                self._maps.append(m)
        else:
            logger.warn(f"skipping jinyaml file {filename}")

    def add_files(self, *filenames):
        maps = []
        for fname in filenames:
            self.add_file(fname)

    def values(self):
        return self._values._map

    def config(self):
        return DeepChain(*self._maps)
