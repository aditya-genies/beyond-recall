"""Posthoc SQLite replay of archived plans; no model calls or primary-result edits."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PILOT = ROOT / "extensions/sol_pilot/registered"
ARMS = ("replan_positional", "replan_fresh", "retained_positional")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def address(namespace, *parts):
    return namespace + ":" + hashlib.sha256(canonical([namespace + "-v1", *parts]).encode()).hexdigest()


def stable(intent, slot):
    return address("positional", intent, slot).replace("positional:", "pos:", 1)


@contextmanager
def connection(path):
    db = sqlite3.connect(path)
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize(path, records):
    with connection(path) as db:
        db.executescript("""
        CREATE TABLE records(address TEXT PRIMARY KEY, public_id TEXT UNIQUE NOT NULL,
                             fact_key TEXT NOT NULL, fact_value TEXT NOT NULL);
        CREATE TABLE bindings(public_id TEXT PRIMARY KEY, address TEXT UNIQUE NOT NULL);
        CREATE TABLE audit(serial INTEGER PRIMARY KEY, stage TEXT NOT NULL, slot INTEGER NOT NULL,
                           operation TEXT NOT NULL, address TEXT NOT NULL, before_record TEXT,
                           after_record TEXT);
        """)
        for record in records:
            physical = address("named", record["id"])
            db.execute("INSERT INTO bindings VALUES(?,?)", (record["id"], physical))
            db.execute("INSERT INTO records VALUES(?,?,?,?)",
                       (physical, record["id"], record["key"], record["value"]))


def record_at(db, physical):
    r = db.execute("SELECT address,public_id,fact_key,fact_value FROM records WHERE address=?",
                   (physical,)).fetchone()
    return dict(zip(("address", "id", "key", "value"), r)) if r else None


def apply(path, operation, intent, slot, stage, arm, case_id, exposed_new_id=None):
    with connection(path) as db:
        if operation["target"] is not None:
            match = db.execute("SELECT address FROM bindings WHERE public_id=?",
                               (operation["target"],)).fetchone()
            if match is None:
                raise ValueError("Unbound named target: " + operation["target"])
            physical = match[0]
        else:
            if operation["kind"] != "put":
                raise ValueError("Targetless delete is outside the declared schema use")
            physical = address("fresh", case_id, slot) if arm == "replan_fresh" and stage == "recovery" else stable(intent, slot)
        before = record_at(db, physical)
        if operation["kind"] == "put":
            public_id = before["id"] if before else exposed_new_id or operation["target"] or physical
            db.execute("INSERT OR IGNORE INTO bindings VALUES(?,?)", (public_id, physical))
            db.execute("INSERT INTO records VALUES(?,?,?,?) ON CONFLICT(address) DO UPDATE SET fact_key=excluded.fact_key,fact_value=excluded.fact_value",
                       (physical, public_id, operation["key"], operation["value"]))
        else:
            db.execute("DELETE FROM records WHERE address=?", (physical,))
        after = record_at(db, physical)
        db.execute("INSERT INTO audit(stage,slot,operation,address,before_record,after_record) VALUES(?,?,?,?,?,?)",
                   (stage, slot, canonical(operation), physical,
                    canonical(before) if before else None, canonical(after) if after else None))
    return physical


def snapshot(path):
    with connection(path) as db:
        return [dict(zip(("id", "key", "value"), r)) for r in
                db.execute("SELECT public_id,fact_key,fact_value FROM records ORDER BY public_id")]


def require_partial(path, records):
    if snapshot(path) != sorted(records, key=lambda r:r["id"]):
        raise ValueError("Physical/public-ID projection differs from archived partial snapshot")


def observe(path, prefix_address, first_operation):
    with connection(path) as db:
        prefix = record_at(db, prefix_address)
        aliases = []
        for serial,slot,op_text,physical,before_text,after_text in db.execute(
            "SELECT serial,slot,operation,address,before_record,after_record FROM audit WHERE stage='recovery' ORDER BY serial"):
            op = json.loads(op_text)
            before = json.loads(before_text) if before_text else None
            after = json.loads(after_text) if after_text else None
            if (physical == prefix_address and op["kind"] == "put" and op["target"] is None
                    and before is not None and before["key"] != op["key"]):
                aliases.append(dict(serial=serial, slot=slot, operation=op, address=physical,
                                    before_record=before, after_record=after))
        if first_operation["kind"] == "delete":
            binding_preserved = literal_preserved = prefix is None
        else:
            binding_preserved = prefix is not None and prefix["key"] == first_operation["key"]
            literal_preserved = binding_preserved and prefix["value"] == first_operation["value"]
    return dict(structural_alias=bool(aliases), alias_events=aliases,
                prefix_binding_preserved=binding_preserved,
                literal_prefix_record_preserved=literal_preserved,
                final_prefix_record=prefix, final_records=snapshot(path))


def protected_paths():
    return sorted(p for p in PILOT.rglob("*") if p.is_file()) + [ROOT/"study.py"] + [ROOT/"results"/name for name in
            ("cases.jsonl", "summary.json", "frozen_spec.json", "boundary_probes.json")]


def freeze():
    target = HERE / "design_freeze.json"
    if target.exists():
        raise FileExistsError(target)
    sources = [HERE/name for name in ("DESIGN.md", "replay.py", "check.py", "test_replay.py")]
    manifest = dict(design_status="posthoc exploratory; frozen before SQLite replay, after observing model outputs",
                    created_at_utc=datetime.now(timezone.utc).isoformat(),
                    code_and_design={str(p.relative_to(ROOT)):digest(p) for p in sources},
                    protected_inputs={str(p.relative_to(ROOT)):digest(p) for p in protected_paths()},
                    model_calls_in_this_extension=0)
    target.write_text(json.dumps(manifest,indent=2)+"\n")
    print("FROZEN", digest(target))


def require_freeze():
    manifest = json.loads((HERE/"design_freeze.json").read_text())
    for group in ("code_and_design", "protected_inputs"):
        for rel, expected in manifest[group].items():
            if digest(ROOT/rel) != expected:
                raise ValueError("Frozen input changed: " + rel)
    return manifest


def run(out):
    require_freeze()
    out.mkdir()  # An existing run is never overwritten.
    rows = json.loads((PILOT/"results.json").read_text())
    index = {r["trial"]:r for r in rows}
    scenarios = json.loads((PILOT/"protocol.json").read_text())["scenarios"]
    cases = []
    for scenario in scenarios:
        intent = scenario["id"]
        base = index[intent+"-original-0"]
        original = json.loads((PILOT/"trials"/base["trial"]/"response.txt").read_text())["operations"]
        assert base["schema_valid"] and original == base["operations"] and original
        for repeat in (0,1):
            partial = index[f"{intent}-partial-{repeat}"]
            replanned = json.loads((PILOT/"trials"/partial["trial"]/"response.txt").read_text())["operations"]
            assert partial["schema_valid"] and replanned == partial["operations"]
            case_id = partial["trial"]
            for arm in ARMS:
                path = out/(case_id+"__"+arm+".sqlite")
                initialize(path, scenario["records"])
                first = original[0]
                prefix_address = apply(path, first, intent, 0, "prefix", arm, case_id,
                                       exposed_new_id=intent+"-first-effect" if first["target"] is None else None)
                require_partial(path, partial["records"])
                chosen = original if arm == "retained_positional" else replanned
                for slot, operation in enumerate(chosen):
                    apply(path, operation, intent, slot, "recovery", arm, case_id)
                cases.append(dict(case_id=case_id, scenario=intent, partial_repeat=repeat, arm=arm,
                                  database=path.name, prefix_address=prefix_address,
                                  baseline_trial=base["trial"], recovery_trial=partial["trial"],
                                  recovery_operations=chosen, **observe(path,prefix_address,first)))
    assert len(cases)==36
    (out/"cases.json").write_text(json.dumps(cases,indent=2)+"\n")
    summary = []
    for arm in ARMS:
        group = [r for r in cases if r["arm"]==arm]
        summary.append(dict(arm=arm,plan_pairs=len(group),
                            structural_alias_cases=sum(r["structural_alias"] for r in group),
                            prefix_binding_preserved=sum(r["prefix_binding_preserved"] for r in group),
                            literal_prefix_record_preserved=sum(r["literal_prefix_record_preserved"] for r in group)))
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    (out/"counterexamples.json").write_text(json.dumps([r for r in cases if r["structural_alias"]],indent=2)+"\n")
    require_freeze()
    provenance = dict(design_freeze_sha256=digest(HERE/"design_freeze.json"),
                      design="posthoc exploratory; no additional model calls", sqlite_version=sqlite3.sqlite_version,
                      completed_at_utc=datetime.now(timezone.utc).isoformat(),
                      original_inputs_unchanged=True,
                      output_sha256={p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()})
    (out/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")
    print(json.dumps(summary,indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=("freeze","run"))
    parser.add_argument("--out",type=Path,default=HERE/"results")
    args=parser.parse_args()
    freeze() if args.command=="freeze" else run(args.out)
