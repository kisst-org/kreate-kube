# Versions of kreate-kube
At this moment there are not many versions of kreate-kube:
- `1.0.0` This is the first official release
- `1.1.0` This is the first bugfix release, with minor improvements
  - better handling of versions that might be interpreted as floats (e.g. 0.3)
  - slightly improved logging
  - updated documentation files
  - added global `konfig` to be used in jinja. `konf._get_path` will be deprecated in future
  - it is possible to have a main konfig in a repo
  - removed `py:` and `main_konfig:` repo's. They were not used
  - fixed bug in `view` cli subcommand
- `1.2.0` This version was never released since the tag was not set
- `1.2.1` This had all the improvements for `1.2.0`
  - many fixes and improvents for the test and test_diff commands
  - added a tracer to get shorter trace with additional information
- `1.3.0`
  - add cli_args for so you can now say `kreate files ...` and do smart stuff with that
  - added many `KREATE_REPO_..LOCAL_DIR..` options for development
  - added a third logging level `-vvv` to see even more detailed information
  - added syntax to get_path to get first element of array
  - added a new `output` command, which is synomous for build
  - include the text of rendered jinja text when not being able to parse yaml
  - added a `show_branch_warning` property on repos', when set to False will not show a warning if using a branch

Since the `1.0.0` release a semantic versioning for backward compatibilty will be used.
- There is no garantuee that python code will be backward compatible,
- yaml should be compatible unless otherwise noted.
- logging and output may change

In general you can specify which version of kreate in the version section
in your konfig:
```
version:
  kreate_kube_version: '>=1.0.0'
```
This use the python syntax for specifying version.
With the special characters you probably need to quote it.