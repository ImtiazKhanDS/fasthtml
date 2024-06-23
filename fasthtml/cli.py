# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/04_cli.ipynb.

# %% auto 0
__all__ = ['railway_link']

# %% ../nbs/04_cli.ipynb 1
from fastcore.utils import *
from fastcore.script import call_parse
from subprocess import run

import json

# %% ../nbs/04_cli.ipynb 3
@call_parse
def railway_link():
    t = run("railway status --json".split(), capture_output=True)
    j = json.loads(t.stdout)
    prj = j['id']
    idxpath = 'edges', 0, 'node', 'id'
    env = nested_idx(j, 'environments', *idxpath)
    svc = nested_idx(j, 'services', *idxpath)

    cmd = f"railway link -e {env} -p {prj} -s {svc}"
    res = run(cmd.split(), capture_output=True)
