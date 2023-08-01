#!/usr/bin/env python3
import kreate

def kreate_demo_app(env: str):
    cfg = kreate.ConfigChain(
        f"tests/script/config-demo-{env}.yaml",
        "tests/script/config-demo.yaml",
        "src/kreate/templates/default-values.yaml",
        )
    app = kreate.App('demo', env, kustomize=True, config=cfg)

    kreate.Ingress(app)
    app.ingress.root.sticky()
    app.ingress.root.whitelist("ggg")
    app.ingress.root.basic_auth()
    app.ingress.root.add_label("dummy", "jan")
    kreate.Ingress(app, path="/api", name="api")

    kreate.Egress(app, name="db")
    kreate.Egress(app, name="redis")
    kreate.Egress(app, name="xyz")

    kreate.Deployment(app)
    #app.depl.add_template_label("egress-to-oracle", "enabled")
    #kreate.HttpProbesPatch(app.deployment)
    #kreate.AntiAffinityPatch(app.deployment)
    kreate.Service(app, "http")
    app.service.http.headless()

    pdb = kreate.PodDisruptionBudget(app, name="demo-pdb")
    pdb.yaml.spec.minAvailable = 2
    pdb.add_label("testje","test")


    cm = kreate.ConfigMap(app, name="demo-vars", kustomize=True)
    cm.add_var("ENV", value=app.config["env"])
    cm.add_var("ORACLE_URL")
    cm.add_var("ORACLE_USR")
    cm.add_var("ORACLE_SCHEMA")

    return app

kreate.run_cli(kreate_demo_app)