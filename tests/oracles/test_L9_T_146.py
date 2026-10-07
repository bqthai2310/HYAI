from pathlib import Path
from ._support import ROOT, oracle
def _valid(files):
    return all("rollback" in p.read_text(encoding="utf-8").lower() or "irreversible" in p.read_text(encoding="utf-8").lower() for p in files)
def test_l9_t_146_migration_discipline(tmp_path):
    no_db_changes=list((ROOT/"migrations").glob("*.sql")); good=tmp_path/"001.sql"; good.write_text("-- rollback\n")
    bad=tmp_path/"002.sql"; bad.write_text("create table x")
    oracle("L9-REQ-IMP-004","L9-T-146",lambda:not no_db_changes or _valid(no_db_changes),lambda:_valid([bad]))
