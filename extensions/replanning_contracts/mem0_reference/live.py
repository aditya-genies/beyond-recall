#!/usr/bin/env python3
"""Fresh Codex/Sol requests inside native Mem0, plus recorded-result controls.

An initial native API call commits, then the child actually exits87 before its
logical acknowledgement. Fresh processes redeliver against copied native stores.
All calls/controls/failures are separate from the controlled 96-cell campaign.
"""
from __future__ import annotations
import argparse, collections, concurrent.futures, copy, hashlib, importlib.metadata
import json, os, shutil, sqlite3, subprocess, sys, tempfile, time
from pathlib import Path
import experiment as controlled

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
MODEL="gpt-6.1-sol"
SIZES=(8,12,24,40)
ARMS=controlled.ARMS
HISTORIES=("fresh_recent_context","aged_recent_context")
STRATEGIES=("fresh_model","recorded_model_result")
SCHEMA={"type":"object","properties":{"memory":{"type":"array","items":{"type":"object","properties":{
 "id":{"type":"string"},"text":{"type":"string"},"attributed_to":{"type":"string"},
 "linked_memory_ids":{"type":"array","items":{"type":"string"}}},
 "required":["id","text","attributed_to","linked_memory_ids"],"additionalProperties":False}}},
 "required":["memory"],"additionalProperties":False}

def write(p,x):controlled.write(p,x)
def sha(p):return controlled.sha(p)
def source(n):
 return [{"role":"user","content":"Please remember my preferences:\n"+"\n".join(x.replace("The synthetic user prefers","I prefer") for x in controlled.FACTS[:n])}]

class NativeCodexLLM:
 def __init__(self,folder,cli,arm,memory,strategy,baseline_response=None):
  self.folder=folder;self.cli=cli;self.arm=arm;self.memory=memory;self.strategy=strategy
  self.baseline_response=baseline_response;self.config=None
 def generate_response(self,messages,**kwargs):
  self.folder.mkdir(parents=True,exist_ok=True)
  write(self.folder/"native_messages.json",messages)
  if self.strategy=="recorded_model_result":
   raw=copy.deepcopy(self.baseline_response);self.folder.joinpath("response.txt").write_text(json.dumps(raw))
   info={"requested_model":None,"additional_model_call":False,"strategy":self.strategy,
    "source":"Exact archived baseline model response reused as a retained nondeterministic result; not a fresh model observation."}
  else:
   task=("Act as the configured memory-extraction model for the role-designated messages below. "
    "Apply their instructions and return only the requested JSON. Do not use tools or read files. "
    "These messages and preferences are synthetic research inputs.\n\n"
    +json.dumps(messages,ensure_ascii=True))
   self.folder.joinpath("codex_prompt.txt").write_text(task)
   env=dict(os.environ)
   for key in list(env):
    if key.endswith("_API_KEY") or key in ("OPENAI_BASE_URL","OPENAI_API_BASE","CODEX_THREAD_ID","CODEX_SESSION_ID"):
     env.pop(key)
   with tempfile.TemporaryDirectory(prefix="memory-native-fresh-") as cwd:
    schema=self.folder/"schema.json";write(schema,SCHEMA)
    cmd=[self.cli,"exec","--model",MODEL,"--ephemeral","--ignore-user-config","--skip-git-repo-check",
     "--sandbox","read-only","--json","--config","project_doc_max_bytes=0",
     "--config",'model_reasoning_effort="medium"',"--cd",cwd,"--output-schema",str(schema),
     "-o",str(self.folder/"response.txt"),"-"]
    started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    start=time.monotonic()
    try:r=subprocess.run(cmd,input=task,text=True,capture_output=True,env=env,timeout=240)
    except subprocess.TimeoutExpired:
     write(self.folder/"request_status.json",{"status":"timeout","additional_model_call":True})
     raise RuntimeError("Codex request timed out")
   events=[];item_types=[];tool_events=[]
   for line in r.stdout.splitlines():
    try:event=json.loads(line)
    except ValueError:continue
    if event.get("type")=="turn.completed":events.append({"type":"turn.completed","usage":event.get("usage")})
    if event.get("type")=="item.completed":
     kind=event.get("item",{}).get("type");item_types.append(kind)
     if kind not in ("agent_message","reasoning"):tool_events.append(kind)
   private=Path(tempfile.gettempdir())/"beyond-recall-native-codex-diagnostics";private.mkdir(exist_ok=True)
   (private/(self.folder.parent.name+"-"+self.folder.name+".stderr")).write_text(r.stderr)
   info={"requested_model":MODEL,"additional_model_call":True,"returncode":r.returncode,
    "wall_seconds":round(time.monotonic()-start,3),"public_usage_events":events,"item_types":item_types,
    "tool_event_types":tool_events,"prompt_sha256":sha(self.folder/"codex_prompt.txt"),
    "started_at_utc":started_utc}
   write(self.folder/"request_status.json",info)
   if r.returncode!=0:raise RuntimeError("Codex request failed; public return code retained")
   if tool_events:raise RuntimeError("Unexpected tool activity in model request")
   raw=json.loads((self.folder/"response.txt").read_text())
  if not isinstance(raw,dict) or not isinstance(raw.get("memory"),list):raise ValueError("Invalid native extraction response")
  for item in raw["memory"]:
   if not isinstance(item.get("text"),str):raise ValueError("Extraction has no string text")
  used=copy.deepcopy(raw);removed=[]
  if self.arm=="exact_admission":
   known={r["memory"] for r in controlled.snapshot(self.memory)}
   removed=[x for x in used["memory"] if x["text"] in known]
   used["memory"]=[x for x in used["memory"] if x["text"] not in known]
  write(self.folder/"used_response.json",used)
  info.update(response_sha256=sha(self.folder/"response.txt"),native_messages_sha256=sha(self.folder/"native_messages.json"),
   used_response_sha256=sha(self.folder/"used_response.json"),exact_admission_removed=removed)
  write(self.folder/"request_status.json",info)
  return json.dumps(used)

def prepare(out,cli):
 out.mkdir(parents=True,exist_ok=False)
 controlled.setup_environment(out)
 import mem0.memory.main
 protected={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/"study.py",ROOT/"results/cases.jsonl",HERE/"experiment.py",HERE/"results/frozen_spec.json",HERE/"results/cases.json"]}
 spec={"prepared_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"driver_sha256":sha(__file__),
  "native_main_sha256":sha(mem0.memory.main.__file__),"protected_inputs":protected,"sizes":SIZES,"arms":ARMS,
  "histories":HISTORIES,"strategies":STRATEGIES,"schema":SCHEMA,
  "design":"4 initial live-model native calls, each abrupt exit87 after API effects return and before logical acknowledgement; 4x2recent-contexts x3arms x2retrystrategies =48 fresh-process retries. Fresh strategies make24 model calls; recorded strategies make none. Planned live calls total28.",
  "input_messages":{str(n):source(n) for n in SIZES},
  "clone_rule":"Close/no-running-client copy of each exited baseline native Qdrant+history store; IDs/content held identical across arms. All baseline IDs/strings captured before retry.",
  "aged_fixture":"Before aged retries, native SQLiteManager.save_messages appends12 neutral synthetic user messages; get_last_messages(limit=10) sees no original preference source. This is an explicit cache precondition, not simulated model output or extra live calls.",
  "extractor":"Native Mem0 role-designated prompts sent through fresh requested Sol6.1 Codex contexts. Not the default OpenAI API model or an uncontrolled deployment.",
  "captured_response_strategy":"Exact baseline response including its literal strings is retained and reused despite changed prompt. This is an explicitly labelled recovery policy/control, not a fresh model call.",
  "outcomes":["physical records","exact duplicate copies relative to baseline","new distinct literal strings","baseline record/value preservation","native candidates/hashes","raw versus used model responses","real process exit code","all errors/not-runnable cells"],
  "semantic_quality":"No paraphrase is automatically called wrong, no natural model error/failure rate, and no independent semantic adjudication.",
  "limitations":"One requested alias, one Codex harness,4authored batches; exact backend snapshot/system prompt/temperature/seed not controlled. Authored widened/exact-admission controls are not stock Mem0 flags or concurrent fixes. Not externally preregistered.",
  "cli_version":subprocess.check_output([cli,"--version"],text=True).strip(),"requested_model":MODEL}
 write(out/"protocol.json",spec);(out/"protocol.sha256").write_text(sha(out/"protocol.json")+"\n")
 print(json.dumps({"prepared":str(out),"planned_live_requests":28,"planned_retries":48,"protocol_sha256":sha(out/"protocol.json")}))

def verify_frozen(out):
 spec=json.loads((out/"protocol.json").read_text())
 assert sha(out/"protocol.json")==(out/"protocol.sha256").read_text().strip()
 assert spec["driver_sha256"]==sha(__file__)
 for rel,want in spec["protected_inputs"].items():assert sha(ROOT/rel)==want,rel
 import mem0.memory.main
 assert spec["native_main_sha256"]==sha(mem0.memory.main.__file__)
 return spec

def age_history(folder):
 from mem0.memory.storage import SQLiteManager
 from mem0.memory.main import _build_session_scope
 scope=_build_session_scope({"user_id":"synthetic-study-user"});db=SQLiteManager(str(folder/"history.sqlite"))
 neutral=[{"role":"user","content":f"Neutral synthetic acknowledgement {i}: thank you."} for i in range(12)]
 try:
  db.save_messages(neutral,scope)
  recent=db.get_last_messages(scope,limit=10)
  write(folder/"aged_context_fixture.json",{"appended_messages":neutral,"recent_messages":recent,"scope":scope})
 finally:db.close()

def child(out,folder,n,arm,history,strategy,cli,baseline=False):
 controlled.setup_environment(out);verify_frozen(out)
 controlled.ACTIVE.clear();controlled.ACTIVE.update(facts=controlled.FACTS[:n],extractor="literal_reemit",arm=arm,calls=[],searches=[])
 if not baseline and history=="aged_recent_context":age_history(folder)
 m=controlled.memory(folder,"bge_small",arm);controlled.ACTIVE["memory"]=m
 before=controlled.snapshot(m)
 baseline_response=None if baseline else json.loads((out/"baselines"/f"n{n}"/"model"/"response.txt").read_text())
 m.llm=NativeCodexLLM(folder/"model",cli,arm,m,strategy,baseline_response)
 try:
  result=m.add(source(n),user_id="synthetic-study-user",infer=True)
  after=controlled.snapshot(m);old={r["id"]:r["memory"] for r in before};final={r["id"]:r["memory"] for r in after}
  new=[r for r in after if r["id"] not in old];counts=collections.Counter(r["memory"] for r in after)
  row={"n_requested_source_preferences":n,"arm":arm,"history":history,"strategy":strategy,"is_baseline":baseline,
   "result":result,"before":before,"after":after,"physical_before":len(before),"physical_after":len(after),
   "distinct_before":len(set(old.values())),"distinct_after":len(set(final.values())),
   "new_record_count":len(new),"new_exact_copies_of_baseline":sum(r["memory"] in set(old.values()) for r in new),
   "extra_exact_copies_after":sum(v-1 for v in counts.values()),"baseline_ids_and_values_preserved":all(final.get(k)==v for k,v in old.items()),
   "write_searches":controlled.ACTIVE["searches"],"source_messages":source(n),"request_status":json.loads((folder/"model/request_status.json").read_text())}
  write(folder/"result.json",row)
  if baseline:
   print(json.dumps({"event":"native_api_effects_returned","physical_records":len(after),"logical_acknowledgement_emitted":False}),flush=True)
   os._exit(87)
 finally:
  m.close();m.vector_store.client.close()

def invoke(out,folder,n,arm,history,strategy,cli,baseline=False):
 cmd=[sys.executable,str(Path(__file__).resolve()),"child","--out",str(out),"--folder",str(folder),"--n",str(n),
  "--arm",arm,"--history",history,"--strategy",strategy,"--cli",cli]
 if baseline:cmd.append("--baseline")
 start=time.monotonic()
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=330)
  returncode=p.returncode;stdout=p.stdout;stderr=p.stderr
 except subprocess.TimeoutExpired as e:
  returncode=None;stdout="";stderr="child timeout"
 private=Path(tempfile.gettempdir())/"beyond-recall-native-worker-diagnostics";private.mkdir(exist_ok=True)
 (private/(folder.name+".stderr")).write_text(stderr)
 path=folder/"result.json";result=json.loads(path.read_text()) if path.exists() else {"status":"failed_before_result","n_requested_source_preferences":n,"arm":arm,"history":history,"strategy":strategy,"is_baseline":baseline}
 result.update(child_returncode=returncode,expected_returncode=87 if baseline else 0,wall_seconds=round(time.monotonic()-start,3),child_public_stdout=stdout.strip())
 write(folder/"execution.json",result)
 print(json.dumps({"case":folder.name,"returncode":returncode,"physical_before":result.get("physical_before"),"physical_after":result.get("physical_after"),"new_exact_copies":result.get("new_exact_copies_of_baseline")}),flush=True)
 return result

def run(out,cli):
 controlled.setup_environment(out);verify_frozen(out)
 baselines=[];retries=[];jobs=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for n in SIZES:
   folder=out/"baselines"/f"n{n}";folder.mkdir(parents=True,exist_ok=False)
   jobs.append(pool.submit(invoke,out,folder,n,"native_k10","fresh_recent_context","fresh_model",cli,True))
  for job in concurrent.futures.as_completed(jobs):baselines.append(job.result())
  by_n={r["n_requested_source_preferences"]:r for r in baselines};jobs=[]
  for n in SIZES:
   baseline_folder=out/"baselines"/f"n{n}"
   for history in HISTORIES:
    for arm in ARMS:
     for strategy in STRATEGIES:
      name=f"n{n}__{history}__{arm}__{strategy}";folder=out/"retries"/name
      if by_n[n].get("child_returncode")!=87 or "after" not in by_n[n]:
       retries.append({"case":name,"status":"not_run_baseline_unavailable","n_requested_source_preferences":n,"history":history,"arm":arm,"strategy":strategy});continue
      folder.mkdir(parents=True,exist_ok=False)
      shutil.copytree(baseline_folder/"qdrant",folder/"qdrant")
      shutil.copy2(baseline_folder/"history.sqlite",folder/"history.sqlite")
      for sidecar in baseline_folder.glob("history.sqlite-*"):
       shutil.copy2(sidecar,folder/sidecar.name)
      jobs.append(pool.submit(invoke,out,folder,n,arm,history,strategy,cli,False))
  for job in concurrent.futures.as_completed(jobs):retries.append(job.result())
 baselines.sort(key=lambda r:r["n_requested_source_preferences"])
 retries.sort(key=lambda r:(r["n_requested_source_preferences"],r.get("history",""),r.get("arm",""),r.get("strategy","")))
 write(out/"results.json",{"baselines":baselines,"retries":retries})
 groups=[]
 for history in HISTORIES:
  for arm in ARMS:
   for strategy in STRATEGIES:
    rs=[r for r in retries if (r.get("history"),r.get("arm"),r.get("strategy"))==(history,arm,strategy)]
    groups.append({"history":history,"arm":arm,"strategy":strategy,"planned":len(rs),"successful":sum(r.get("child_returncode")==0 for r in rs),
     "new_exact_copies":sum(r.get("new_exact_copies_of_baseline",0) for r in rs),"new_records":sum(r.get("new_record_count",0) for r in rs)})
 summary={"baseline_attempts":len(baselines),"actual_baseline_exit87":sum(r.get("child_returncode")==87 for r in baselines),
  "retry_attempts_or_not_runnable_cells":len(retries),"successful_retry_attempts":sum(r.get("child_returncode")==0 for r in retries),
  "planned_live_requests":28,"recorded_live_request_status_files":sum(json.loads(p.read_text()).get("additional_model_call") is True for p in out.glob("**/request_status.json")),
  "groups":groups,"interpretation":"Finite authored source batches, one requested model/harness, no inferential or semantic-error-rate claim. Recorded-result strategy is not a new model observation."}
 write(out/"summary.json",summary);print(json.dumps(summary,indent=2))

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("action",choices=("prepare","run","child"));p.add_argument("--out",required=True,type=Path)
 p.add_argument("--cli",required=True);p.add_argument("--folder",type=Path);p.add_argument("--n",type=int)
 p.add_argument("--arm",choices=ARMS);p.add_argument("--history",choices=HISTORIES);p.add_argument("--strategy",choices=STRATEGIES);p.add_argument("--baseline",action="store_true")
 a=p.parse_args();a.out=a.out.resolve()
 if a.action=="prepare":prepare(a.out,a.cli)
 elif a.action=="run":run(a.out,a.cli)
 else:child(a.out,a.folder,a.n,a.arm,a.history,a.strategy,a.cli,a.baseline)
