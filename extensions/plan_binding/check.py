"""Separately implemented checker; imports no replay execution/metric functions."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PILOT=ROOT/"extensions/sol_pilot/registered"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(value):
    return json.dumps(value,sort_keys=True,separators=(",", ":"))


def key(namespace,*parts):
    digest=hashlib.sha256(encode([namespace+"-v1",*parts]).encode()).hexdigest()
    return ("pos" if namespace=="positional" else namespace)+":"+digest


def check(out):
    freeze=json.loads((HERE/"design_freeze.json").read_text())
    for group in ("code_and_design","protected_inputs"):
        for path,digest in freeze[group].items():
            assert sha(ROOT/path)==digest, ("freeze mismatch",path)
    provenance=json.loads((out/"provenance.json").read_text())
    assert provenance["design_freeze_sha256"]==sha(HERE/"design_freeze.json")
    for path,digest in provenance["output_sha256"].items():
        assert sha(out/path)==digest, ("output mismatch",path)
    specs=json.loads((PILOT/"protocol.json").read_text())["scenarios"]
    trials={r["trial"]:r for r in json.loads((PILOT/"results.json").read_text())}
    recorded=json.loads((out/"cases.json").read_text())
    assert len(recorded)==36
    lookup={(r["scenario"],r["partial_repeat"],r["arm"]):r for r in recorded}
    assert len(lookup)==36
    recomputed=[]
    for spec in specs:
        intent=spec["id"]
        base=trials[intent+"-original-0"]
        original=json.loads((PILOT/"trials"/base["trial"]/"response.txt").read_text())["operations"]
        for repeat in (0,1):
            trial_id=f"{intent}-partial-{repeat}"
            partial=trials[trial_id]
            remaining=json.loads((PILOT/"trials"/trial_id/"response.txt").read_text())["operations"]
            for arm in ("replan_positional","replan_fresh","retained_positional"):
                row=lookup[intent,repeat,arm]
                dbpath=out/row["database"]
                con=sqlite3.connect(dbpath.resolve().as_uri()+"?mode=ro",uri=True)
                try:
                    assert con.execute("PRAGMA integrity_check").fetchone()==("ok",)
                    physical={a:dict(address=a,id=i,key=k,value=v) for a,i,k,v in con.execute("SELECT address,public_id,fact_key,fact_value FROM records")}
                    actual_bindings=dict(con.execute("SELECT public_id,address FROM bindings"))
                    actual_audit=list(con.execute("SELECT serial,stage,slot,operation,address,before_record,after_record FROM audit ORDER BY serial"))
                finally:
                    con.close()
                state={key("named",r["id"]):dict(address=key("named",r["id"]),**r) for r in spec["records"]}
                bindings={r["id"]:key("named",r["id"]) for r in spec["records"]}
                aliases=[]
                expected_audit=[]
                prefix_address=None
                prefix_projection=None
                selected=original if arm=="retained_positional" else remaining
                for stage,operations in (("prefix",original[:1]),("recovery",selected)):
                    for slot,op in enumerate(operations):
                        if op["target"] is not None:
                            address=bindings[op["target"]]
                        elif stage=="recovery" and arm=="replan_fresh":
                            address=key("fresh",trial_id,slot)
                        else:
                            address=key("positional",intent,slot)
                        before=state.get(address)
                        if op["kind"]=="delete":
                            state.pop(address,None)
                        else:
                            public=(before["id"] if before else
                                    intent+"-first-effect" if stage=="prefix" and op["target"] is None else
                                    op["target"] or address)
                            bindings[public]=address
                            state[address]=dict(address=address,id=public,key=op["key"],value=op["value"])
                        after=state.get(address)
                        serial=len(expected_audit)+1
                        expected_audit.append((serial,stage,slot,encode(op),address,
                                               encode(before) if before else None,encode(after) if after else None))
                        if stage=="prefix":
                            prefix_address=address
                            prefix_projection=sorted([{k:v for k,v in record.items() if k!="address"} for record in state.values()],key=lambda r:r["id"])
                        elif (op["kind"]=="put" and op["target"] is None and address==prefix_address
                              and before is not None and before["key"]!=op["key"]):
                            aliases.append(dict(serial=serial,slot=slot,operation=op,address=address,before_record=before,after_record=after))
                assert prefix_projection==sorted(partial["records"],key=lambda r:r["id"])
                assert physical==state and actual_bindings==bindings and actual_audit==expected_audit
                final_prefix=state.get(prefix_address)
                first=original[0]
                binding_preserved=(final_prefix is None if first["kind"]=="delete" else
                                   final_prefix is not None and final_prefix["key"]==first["key"])
                literal_preserved=(binding_preserved if first["kind"]=="delete" else
                                   binding_preserved and final_prefix["value"]==first["value"])
                observations=dict(structural_alias=bool(aliases),alias_events=aliases,
                                  prefix_binding_preserved=binding_preserved,
                                  literal_prefix_record_preserved=literal_preserved,
                                  final_prefix_record=final_prefix,
                                  final_records=sorted([{k:v for k,v in record.items() if k!="address"} for record in state.values()],key=lambda r:r["id"]))
                for metric,value in observations.items():
                    assert row[metric]==value,(trial_id,arm,metric)
                assert row["recovery_operations"]==selected and row["prefix_address"]==prefix_address
                recomputed.append(dict(arm=arm,scenario=intent,repeat=repeat,**observations))
    summary=[]
    for arm in ("replan_positional","replan_fresh","retained_positional"):
        group=[r for r in recomputed if r["arm"]==arm]
        summary.append(dict(arm=arm,plan_pairs=len(group),structural_alias_cases=sum(r["structural_alias"] for r in group),
                            prefix_binding_preserved=sum(r["prefix_binding_preserved"] for r in group),
                            literal_prefix_record_preserved=sum(r["literal_prefix_record_preserved"] for r in group)))
    assert summary==json.loads((out/"summary.json").read_text())
    assert [r for r in recorded if r["structural_alias"]]==json.loads((out/"counterexamples.json").read_text())
    report=dict(status="PASS",integration_count=len(recomputed),plan_pairs=12,arms=3,
                checker_implementation="Separate implementation; no replay functions imported. Same author and host; not external replication.",
                checks=["frozen code/design and all protected inputs unchanged","all output hashes",
                        "all physical SQLite records and bindings","all committed before/after audit rows",
                        "exact archived partial snapshots","raw recorded response operation lists",
                        "prefix and cross-key alias observations","aggregate and counterexample reconciliation"],
                summary=summary,semantic_accuracy_graded=False,additional_model_calls=0,
                design_freeze_sha256=sha(HERE/"design_freeze.json"))
    (out/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=HERE/"results")
    check(parser.parse_args().out)
