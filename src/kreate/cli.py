import argparse
import os
import logging

logger = logging.getLogger(__name__)

def do_files(kreate_app, env):
    app=kreate_app(env)
    app.kreate_files()

def do_out(kreate_app, env):
    app=kreate_app(env)
    app.kreate_files()
    cmd = f"kustomize build {app.target_dir}"
    logger.info(f"running: {cmd}")
    os.system(cmd)

def do_diff(kreate_app, env):
    app=kreate_app(env)
    app.kreate_files()
    cmd = f"kustomize build {app.target_dir} | kubectl diff -f - "
    logger.info(f"running: {cmd}")
    os.system(cmd)

def do_apply(kreate_app, env):
    app=kreate_app(env)
    app.kreate_files()
    cmd = f"kustomize build {app.target_dir} | kubectl apply --dry-run -f - "
    logger.info(f"running: {cmd}")
    os.system(cmd)

def do_test(kreate_app, env):
    app=kreate_app(env)
    app.kreate_files()
    cmd = f"kustomize build {app.target_dir} | diff  {app.script_dir}/test-{app.name}-{app.env}.out -"
    logger.info(f"running: {cmd}")
    os.system(cmd)

def do_testupdate(kreate_app, env):
    app=kreate_app(env)
    app.kreate_files()
    cmd = f"kustomize build {app.target_dir} > {app.script_dir}/test-{app.name}-{app.env}.out"
    logger.info(f"running: {cmd}")
    os.system(cmd)


def run_cli(kreate_app):
    parser = argparse.ArgumentParser()
    parser.add_argument("-e","--env", action="store", default="dev")
    parser.add_argument("-v","--verbose", action="store_true")
    parser.add_argument("-q","--quiet", action="store_true")


    subparsers = parser.add_subparsers(help="subcommand", description="valid subcommands", title="subcmd")
    #parser.add_subparsers(title="command", help="subcommand")
    files_cmd = subparsers.add_parser("files", help="kreate all the files (default command)", aliases=["f"])
    out_cmd = subparsers.add_parser("out", help="output all the resources", aliases=["o", "b",  "build"])
    apply_cmd = subparsers.add_parser("apply", help="apply the output to kubernetes", aliases=["a"])
    diff_cmd = subparsers.add_parser("diff", help="diff with current existing resources", aliases=["d"])
    test_cmd = subparsers.add_parser("test", help="test output against test.out file", aliases=["t"])
    testupdate_cmd = subparsers.add_parser("testupdate", help="update test.out file", aliases=["tu"])
    files_cmd.set_defaults(func=do_files)
    out_cmd.set_defaults(func=do_out)
    diff_cmd.set_defaults(func=do_diff)
    apply_cmd.set_defaults(func=do_apply)
    test_cmd.set_defaults(func=do_test)
    testupdate_cmd.set_defaults(func=do_testupdate)
    # from https://stackoverflow.com/questions/6365601/default-sub-command-or-handling-no-sub-command-with-argparse
    parser.set_defaults(func=do_files) # TODO: better way to set default command?

    args = parser.parse_args()
    env = args.env
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    elif args.quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.INFO)



    args.func(kreate_app, env)
