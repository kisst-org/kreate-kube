#!/usr/bin/env python3
import kreate
import appdef

def kreate_config(env: str) -> kreate.core.Config:
    cfg = kreate.core.Config()
    cfg._values.add_obj(appdef)
    cfg._values.add_yaml(f"tests/script/values-{env}.yaml")
    cfg.add_files(
        f"tests/script/config-demo-{env}.yaml",
        "tests/script/demo-strukt.yaml",
        "src/kreate/templates/default-values.yaml",
        )
    return cfg


def kreate_app(env: str) -> kreate.App:
    app = kreate.App('demo', env, config=kreate_config(env))

    kreate.Ingress(app, "root")
    app.ingress.root.sticky()
    app.ingress.root.whitelist("10.20.30.40")
    app.ingress.root.basic_auth()
    app.ingress.root.label("dummy", "jan")
    kreate.Ingress(app, "api")

    kreate.Egress(app, "db")
    kreate.Egress(app, "redis")
    kreate.Egress(app, "xyz")

    depl=kreate.Deployment(app)
    depl.pod_label("egress-to-db", "enabled")
    kreate.HttpProbesPatch(app.depl.main)
    kreate.AntiAffinityPatch(depl)
    kreate.Service(app)
    app.service.main.headless()
    kreate.Service(app, "https")


    pdb = kreate.PodDisruptionBudget(app, name="demo-pdb")
    pdb.yaml.spec.minAvailable = 2
    pdb.label("testje","test")

    app.kreate_resource("ServiceAccount")
    app.kreate_resource("ServiceMonitor")
    app.kreate_resource("HorizontalPodAutoscaler")

    cm = kreate.ConfigMap(app, "vars") # kustomize=False
    cm.add_var("ENV", app.values["env"])
    cm.add_var("ORACLE_URL")
    cm.add_var("ORACLE_USR")
    cm.add_var("ORACLE_SCHEMA")

    return app

kreate.run_cli(kreate_app)
