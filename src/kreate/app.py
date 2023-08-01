import os
import sys
import shutil
from collections.abc import Mapping

from . import templates, core

class App:
    def __init__(self, name: str,
                 config: Mapping = None,
                 kustomize: bool =False):
        self.name = name
        self.script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.vars = dict()
        self.config = config
        self.kustomize = kustomize
        self.namespace = self.name + "-" + self.config["env"]
        self.target_dir = "./build/" + self.namespace
        self.resources = []
        self.kust_resources = []
        self._kinds = {}

    def add(self, res) -> None:
        if not res.skip:
            self.resources.append(res)

        map = self._kinds.get(res.kind.lower(), None)
        if map is None:
            map = core.DictWrapper({})
            self._kinds[res.kind.lower()] = map
        if res.shortname is None:
            map["_"] = res # TODO: better name/abbrev ....
        else:
            map[res.shortname] = res

    def __getattr__(self, attr):
        if attr in self.__dict__ or attr == "_dict":
            return super().__getattribute__(attr)
        return self._kinds.get(attr, None)

    def kreate_files(self):
        # TODO better place: to clear directory
        if os.path.exists(self.target_dir) and os.path.isdir(self.target_dir):
            shutil.rmtree(self.target_dir)
        os.makedirs(self.target_dir, exist_ok=True)

        for rsrc in self.resources:
            rsrc.kreate()
        if self.kustomize:
            kust = Kustomization(self)
            kust.kreate()

class Strukture(App):
    def __init__(self, name: str, env: str, config: Mapping):
        super().__init__(name, env, config=config)
        for name in config.egress.keys():
            Egress(self, name)
        for name in config.ingress.keys():
            Ingress(self, name)
        #Deployment(self, self.name)



##################################################################

class Resource(core.YamlBase):
    def __init__(self, app: App, shortname=None, kind: str = None,
                 name: str = None,
                 filename: str = None,
                 skip: bool = False,
                 config: Mapping = None):
        self.app = app
        if kind is None:
            self.kind = self.__class__.__name__
        else:
            self.kind = kind
        self.shortname = shortname
        typename = self.kind.lower()
        if shortname is None:
            self.name = name or f"{app.name}-{typename}"
        else:
            self.name = name or f"{app.name}-{typename}-{shortname}"
        self.filename = filename or f"{self.name}.yaml"
        self.patches = []
        self.skip = skip

        if config:
            self.config = config
        else:
            if typename in app.config:
                if shortname is None:
                    print(f"DEBUG using default config for {typename}")
                    self.config = app.config[typename]
                elif shortname in app.config[typename]:
                    print(f"DEBUG using named config {typename}.{shortname}")
                    self.config = app.config[typename][shortname]
                else:
                    print(f"DEBUG could not find config for {shortname} in {typename}.")
                    self.config = {}
            else:
                print(f"DEBUG could not find any config for {typename}")
                self.config = {}
        template = f"{self.kind}.yaml"
        core.YamlBase.__init__(self, template)
        if self.config.get("ignore", False):
            # config indicates to be ignored
            # - do not load the template (config might be missing)
            # - do not register
            print(f"INFO: ignoring {typename}.{self.name}")
            self.skip = True
        else:
            self.load_yaml()
        self.app.add(self)

    def _get_jinja_vars(self):
        return {
            "app": self.app,
            "cfg": self.config,
            "my": self,
        }

    def kreate(self) -> None:
        self.save_yaml(f"{self.app.target_dir}/{self.filename}")
        for p in self.patches:
            p.kreate()

    def annotate(self, name: str, val: str) -> None:
        if "annotations" not in self.yaml.metadata:
            self.yaml.metadata["annotations"]={}
        self.yaml.metadata.annotations[name]=val

    def add_label(self, name: str, val: str) -> None:
        if "labels" not in self.yaml.metadata:
            self.yaml.metadata["labels"]={}
        self.yaml.metadata.labels[name]=val

class Kustomization(Resource):
    def __init__(self, app: App):
        Resource.__init__(self, app, "TODO", filename="kustomization.yaml", skip=True)


class Deployment(Resource):
    def __init__(self, app: App):
        # TODO: make name configurable?
        Resource.__init__(self, app, shortname=None)

    def add_template_annotation(self, name: str, val: str) -> None:
        if not "annotations" in self.yaml.spec.template.metadata:
            self.yaml.spec.template.metadata["annotations"] = {}
        self.yaml.spec.template.metadata.annotations[name] = val

    def add_template_label(self, name: str, val: str) -> None:
        if not "labels" in self.yaml.spec.template.metadata:
            self.yaml.spec.template.metadata["labels"] = {}
        self.yaml.spec.template.metadata.labels[name] = val


class PodDisruptionBudget(Resource):
    def __init__(self, app: App):
        Resource.__init__(self, app, shortname="TODO", name=f"{app.name}-pdb")

class Service(Resource):
    def __init__(self, app: App, shortname=None):
        Resource.__init__(self, app, shortname=shortname)

    def headless(self):
        self.yaml.spec.clusterIP="None"

class Egress(Resource):
    def __init__(self, app: App, shortname: str):
        Resource.__init__(self, app, shortname= shortname, name=f"{app.name}-egress-to-{shortname}")

class ConfigMap(Resource):
    def __init__(self, app: App, shortname=None, name: str = None, kustomize=False):
        self.kustomize = kustomize
        Resource.__init__(self, app, shortname=shortname, name=name, skip=kustomize)
        if kustomize:
            app.kustomize = True
            app.kust_resources.append(self)
            self.fieldname = "literals"
            self.yaml[self.fieldname] = {}
        else:
            self.fieldname = "data"


    def add_var(self, name, value=None):
        if value is None:
            value = self.app.config.vars[name]
        # We can not use self.yaml.data, since data is a field in UserDict
        self.yaml[self.fieldname][name] = value


class Ingress(Resource):
    def __init__(self, app: App, shortname: str ="root", path: str ="/" ):
        self.path = path
        Resource.__init__(self, app, shortname=shortname) # TODO, config=app.config.ingress[name])

    def nginx_annon(self, name: str, val: str) -> None:
        self.annotate("nginx.ingress.kubernetes.io/" + name, val)

    def sticky(self) -> None:
        self.nginx_annon("affinity", "cookie")

    def rewrite_url(self, url: str) -> None:
        self.nginx_annon("rewrite-target", url)

    def read_timeout(self, sec: int) -> None:
        self.nginx_annon("proxy-read-timeout", str(sec))

    def max_body_size(self, size: int) -> None:
        self.nginx_annon("proxy-body-size", str(size))

    def whitelist(self, whitelist: str) -> None:
        self.nginx_annon("whitelist-source-range", whitelist)

    def session_cookie_samesite(self) -> None:
        self.nginx_annon("session-cookie-samesite", "None")

    def basic_auth(self, secret: str = "basic-auth") -> None:
        self.nginx_annon("auth-type", "basic")
        self.nginx_annon("auth-secret", secret)
        self.nginx_annon("auth-realm", self.app.name + "-realm")

#########################################################################################
class Patch(core.YamlBase):
    def __init__(self, target: Resource, template, config: Mapping):
        self.target = target
        self.target.patches.append(self)
        self.config = config
        self.filename = template
        core.YamlBase.__init__(self, template=template)
        self.load_yaml()

    def kreate(self) -> None:
        self.save_yaml(f"{self.target.app.target_dir}/{self.filename}")

    def _get_jinja_vars(self):
        return {
            "target": self.target,
            "cfg" : self.config,
            "app" : self.target.app,
            "my" : self
        }


class HttpProbesPatch(Patch):
    def __init__(self, target: Resource, container_name : str ="app"):
        config = target.app.config.containers[container_name]
        Patch.__init__(self, target, "patch-http-probes.yaml", config=config)

class AntiAffinityPatch(Patch):
    def __init__(self, target: Resource, container_name : str ="app"):
        config = target.app.config.containers[container_name]
        Patch.__init__(self, target, "patch-anti-affinity.yaml", config=config)
