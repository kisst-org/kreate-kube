import logging

from ..kore import JinYamlKomponent
from ..krypt.functions import dekrypt_str

logger = logging.getLogger(__name__)


__all__ = [
    "Resource",
    "Deployment",
    "PodDisruptionBudget",
    "ConfigMap",
    "Ingress",
    "Service",
    "Egress",
]


class Resource(JinYamlKomponent):
    def aktivate(self):
        super().aktivate()
        self.add_metadata()

    def __str__(self):
        return f"<Resource {self.kind}.{self.shortname} {self.name}>"

    @property
    def dirname(self):
        return  "resources"

    @property
    def filename(self):
        # prefix the file, because the name of a resource is not guaranteed
        # to be unique
        return f"{self.kind}-{self.name}.yaml"

    def add_metadata(self):
        for key in self.strukture.get("annotations", {}):
            if "annotations" not in self.yaml.metadata:
                self.yaml.metadata.annotations = {}
            self.yaml.metadata.annotations[key] = (
                self.strukture.annotations[key])
        for key in self.strukture.get("labels", {}):
            if "labels" not in self.yaml.metadata:
                self.yaml.metadata.labels = {}
            self.yaml.metadata.labels[key] = self.strukture.labels[key]

    def annotation(self, name: str, val: str) -> None:
        if "annotations" not in self.yaml.metadata:
            self.yaml.metadata["annotations"] = {}
        self.yaml.metadata.annotations[name] = val

    def label(self, name: str, val: str) -> None:
        if "labels" not in self.yaml.metadata:
            self.yaml.metadata["labels"] = {}
        self.yaml.metadata.labels[name] = val

    def load_file(self, filename: str) -> str:
        with open(f"{self.app.konfig.dir}/{filename}") as f:
            return f.read()


class Deployment(Resource):
    def calc_name(self):
        if self.shortname == "main":
            return self.app.appname
        return f"{self.app.appname}-{self.shortname}"

    def pod_annotation(self, name: str, val: str) -> None:
        if "annotations" not in self.yaml.spec.template.metadata:
            self.yaml.spec.template.metadata["annotations"] = {}
        self.yaml.spec.template.metadata.annotations[name] = val

    def pod_label(self, name: str, val: str) -> None:
        if "labels" not in self.yaml.spec.template.metadata:
            self.yaml.spec.template.metadata["labels"] = {}
        self.yaml.spec.template.metadata.labels[name] = val


class PodDisruptionBudget(Resource):
    pass


class Service(Resource):
    def headless(self):
        self.yaml.spec.clusterIP = "None"


class Egress(Resource):
    def calc_name(self):
        return f"{self.app.appname}-egress-to-{self.shortname}"

class Secret(Resource):
    @property
    def dirname(self):
        return "secrets"


class SecretBasicAuth(Secret):
    def calc_name(self):
        return f"{self.app.appname}-{self.shortname}"

    def users(self):
        result = []
        for usr in self.strukture.users:
            entry = dekrypt_str(self.app.konfig.secrets[usr])
            result.append(f"{usr}:{entry}")
        result.append("")  # for the final newline
        return "\n".join(result)


class ConfigMap(Resource):
    def calc_name(self):
        return f"{self.app.appname}-{self.shortname}"

    @property
    def filename(self) -> str:
        return super().filename

    def add_var(self, name, value=None):
        if value is None:
            value = self.app.konfig.values[name]
        # We can not use self.yaml.data, since data is a field in UserDict
        self.yaml["data"][name] = value


class Ingress(Resource):
    def nginx_annon(self, name: str, val: str) -> None:
        self.annotation("nginx.ingress.kubernetes.io/" + name, val)

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

    def basic_auth(self, secret: str = None) -> None:
        secret = secret or f"{self.app.appname}-basic-auth"
        self.nginx_annon("auth-type", "basic")
        self.nginx_annon("auth-secret", secret)
        self.nginx_annon("auth-realm", self.app.appname + "-realm")