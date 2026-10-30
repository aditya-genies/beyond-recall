#!/usr/bin/env python3
"""Posthoc native-search exposure test over immutable copied live stores.

All baseline fact strings are queries. Measures literal context diversity and
target presence, not answer quality, semantic correctness or population recall.
No new model requests. Freeze source/design/input hashes before any searches.
"""
import argparse, collections, hashlib, json, shutil, socket, tempfile, time
from pathlib import Path
import experiment as controlled

HERE=Path(__file__).resolve().parent
SIZES=(8,12,24,40)
BUDGETS=(5,10,20)
STATES=("baseline","native_k10","widened_candidates","exact_admission")

class NoModel:
 config=None
 def generate_response(self,*args,**kwargs):raise RuntimeError("Retrieval study must not call an LLM")

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):controlled.write(p,x)
def source_folder(live,n,state):
 if state=="baseline":return live/"baselines"/f"n{n}"
 return live/"retries"/f"n{n}__fresh_recent_context__{state}__fresh_model"
def freeze(out,live):
 out.mkdir(parents=True,exist_ok=False)
 protected={}
 for n in SIZES:
  for state in STATES:
   folder=source_folder(live,n,state)
   for p in folder.rglob("*"):
    if p.is_file():protected[str(p.relative_to(HERE))]=sha(p)
 spec={"prepared_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"source_sha256":sha(__file__),
  "sizes":SIZES,"budgets":BUDGETS,"states":STATES,"protected_inputs":protected,
  "design":"Every distinct baseline fact is a literal query against baseline and three fresh-context/fresh-model post-retry stores, with identical native reader and3explicit budgets. 84queries x4states x3budgets =1008native search calls.",
  "posthoc":"Designed after observing physical duplicate records; frozen before any measured search. Not independent confirmation or externally preregistered.",
  "reader":"Pinned native Memory.search, real local BGE+BM25, threshold0, show_expired=False; all four states use identical reader configuration. Optional spaCy absent; native fallback.",
  "outcomes":["returned physical records","distinct exact fact strings","duplicate context slots","exact queried fact present"],
  "limits":"Literal diversity is not semantic diversity, QA accuracy, agent harm, model token cost or a natural-workload statistic. Query every baseline fact; no favourable query selection. Preserved target presence can coexist with fewer distinct context facts.",
  "model_requests":0}
 write(out/"protocol.json",spec);(out/"protocol.sha256").write_text(sha(out/"protocol.json")+"\n")
 print(json.dumps({"frozen":str(out),"native_queries_planned":1008,"protocol_sha256":sha(out/"protocol.json")}))

def check_inputs(out):
 spec=json.loads((out/"protocol.json").read_text())
 assert sha(out/"protocol.json")==(out/"protocol.sha256").read_text().strip() and sha(__file__)==spec["source_sha256"]
 for rel,want in spec["protected_inputs"].items():assert sha(HERE/rel)==want,rel
 return spec

def run(out,live):
 controlled.setup_environment(out);check_inputs(out);rows=[];states=[]
 original_connect=socket.socket.connect
 def no_external(sock,address):
  if isinstance(address,tuple) and address[0] not in ("127.0.0.1","::1","localhost"):
   raise RuntimeError("Unexpected external network call during local retrieval")
  return original_connect(sock,address)
 socket.socket.connect=no_external
 for n in SIZES:
  baseline=json.loads((source_folder(live,n,"baseline")/"execution.json").read_text())
  queries=sorted({r["memory"] for r in baseline["after"]})
  for state in STATES:
   original=source_folder(live,n,state)
   with tempfile.TemporaryDirectory(prefix="memory-retrieval-copy-") as tmp:
    folder=Path(tmp);shutil.copytree(original/"qdrant",folder/"qdrant")
    for p in original.glob("history.sqlite*"):shutil.copy2(p,folder/p.name)
    controlled.ACTIVE.clear();controlled.ACTIVE.update(facts=[],extractor="literal_reemit",arm="native_k10",calls=[],searches=[])
    m=controlled.memory(folder,"bge_small","native_k10");m.llm=NoModel()
    before=controlled.snapshot(m)
    try:
     for query in queries:
      for k in BUDGETS:
       result=m.search(query,filters={"user_id":"synthetic-study-user"},top_k=k,threshold=0.0,show_expired=False)
       returned=result["results"];texts=[x["memory"] for x in returned]
       row={"n_source_preferences":n,"state":state,"query":query,"query_sha256":hashlib.sha256(query.encode()).hexdigest(),
        "budget":k,"results":returned,"returned_records":len(returned),"distinct_literal_facts":len(set(texts)),
        "duplicate_context_slots":len(texts)-len(set(texts)),"exact_target_present":query in texts}
       assert len(returned)<=k;rows.append(row)
     after=controlled.snapshot(m);assert before==after,"Native searches unexpectedly changed record state"
     states.append({"n_source_preferences":n,"state":state,"native_records":before,"query_source":"all distinct baseline fact strings","record_state_unchanged_by_search":True})
    finally:m.close();m.vector_store.client.close()
   print(json.dumps({"n":n,"state":state,"queries":len(queries),"budgets":len(BUDGETS)}),flush=True)
 write(out/"cases.json",rows);write(out/"states.json",states)
 groups=[]
 for n in SIZES:
  for state in STATES:
   for k in BUDGETS:
    rs=[r for r in rows if (r["n_source_preferences"],r["state"],r["budget"])==(n,state,k)]
    groups.append({"n_source_preferences":n,"state":state,"budget":k,"query_count":len(rs),
     "total_returned_records":sum(r["returned_records"] for r in rs),"total_distinct_literal_facts":sum(r["distinct_literal_facts"] for r in rs),
     "duplicate_context_slots":sum(r["duplicate_context_slots"] for r in rs),
     "minimum_distinct_facts":min(r["distinct_literal_facts"] for r in rs),
     "mean_distinct_facts":sum(r["distinct_literal_facts"] for r in rs)/len(rs),
     "exact_target_present_count":sum(r["exact_target_present"] for r in rs)})
 assert len(rows)==1008;check_inputs(out)
 write(out/"summary.json",{"native_search_calls":len(rows),"additional_model_requests":0,"groups":groups,
  "interpretation":"Complete finite authored query set, arithmetic summaries only. Exact target presence is checked separately; no QA harm or population rates inferred."})
 print(json.dumps({"native_search_calls":len(rows),"model_calls":0,"groups":groups},indent=2))

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("action",choices=("freeze","run"));p.add_argument("--out",type=Path,required=True);p.add_argument("--live",type=Path,default=HERE/"live_results")
 a=p.parse_args();a.out=a.out.resolve();a.live=a.live.resolve()
 freeze(a.out,a.live) if a.action=="freeze" else run(a.out,a.live)
