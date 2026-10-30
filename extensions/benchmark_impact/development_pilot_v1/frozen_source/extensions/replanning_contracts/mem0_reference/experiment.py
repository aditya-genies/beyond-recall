#!/usr/bin/env python3
"""Native Mem0/Qdrant admission experiment with explicitly controlled extraction.

Source audit motivates the hypothesis. Freeze before measured runs. Controlled
extractors are not LLM results. Real embeddings are an independent factor.
No company source, model API key, hosted memory service or telemetry is used.
"""
from __future__ import annotations
import argparse, collections, hashlib, importlib.metadata, json, math, os
from pathlib import Path
import re, socket, sqlite3, sys, tempfile, time

HERE=Path(__file__).resolve().parent
EXPECTED_SOURCE="26cdefb46600c0fa5953c4b5ee5003c125539fc4"
SIZES=(1,5,10,11,13,20,21,40)
ARMS=("native_k10","widened_candidates","exact_admission")
EXTRACTORS=("literal_reemit","visible_delta")
EMBEDDERS=("hash_control","bge_small")
FACTS=[
 "The synthetic user prefers mango as a fruit.",
 "The synthetic user prefers jasmine as a flower.",
 "The synthetic user prefers emerald as a color.",
 "The synthetic user prefers cycling as a sport.",
 "The synthetic user prefers chess as a board game.",
 "The synthetic user prefers violin as an instrument.",
 "The synthetic user prefers espresso as a coffee.",
 "The synthetic user prefers chamomile as a tea.",
 "The synthetic user prefers rye as a bread.",
 "The synthetic user prefers lentils as a soup.",
 "The synthetic user prefers pine as a tree.",
 "The synthetic user prefers quartz as a mineral.",
 "The synthetic user prefers astronomy as a science.",
 "The synthetic user prefers origami as a craft.",
 "The synthetic user prefers Lisbon as a travel destination.",
 "The synthetic user prefers autumn as a season.",
 "The synthetic user prefers dawn as a time of day.",
 "The synthetic user prefers linen as a fabric.",
 "The synthetic user prefers jazz as a music genre.",
 "The synthetic user prefers mystery as a book genre.",
 "The synthetic user prefers comedy as a film genre.",
 "The synthetic user prefers wolves as a wild animal.",
 "The synthetic user prefers finches as a bird.",
 "The synthetic user prefers tulsi as a garden herb.",
 "The synthetic user prefers oatmeal as a breakfast.",
 "The synthetic user prefers peaches as a dessert flavor.",
 "The synthetic user prefers pottery as a weekend activity.",
 "The synthetic user prefers trains as a travel mode.",
 "The synthetic user prefers mountains as a landscape.",
 "The synthetic user prefers fountain pens as a writing tool.",
 "The synthetic user prefers metric as a measurement system.",
 "The synthetic user prefers concise as an answer style.",
 "The synthetic user prefers walking as a commute exercise.",
 "The synthetic user prefers algebra as a mathematics topic.",
 "The synthetic user prefers cyan as a diagram accent.",
 "The synthetic user prefers markdown as a note format.",
 "The synthetic user prefers mornings as a study period.",
 "The synthetic user prefers tofu as a lunch protein.",
 "The synthetic user prefers libraries as a quiet venue.",
 "The synthetic user prefers cedar as a wood scent.",
]
ACTIVE={}

def canonical(x):return json.dumps(x,sort_keys=True,separators=(",",":"))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+"\n")
def hash_text(s):return hashlib.md5(s.encode()).hexdigest()

def setup_environment(out,offline=True):
 for key in list(os.environ):
  if key.endswith("_API_KEY") or key in ("HF_TOKEN","HUGGING_FACE_HUB_TOKEN"):
   os.environ.pop(key)
 os.environ["MEM0_TELEMETRY"]="false"
 os.environ["MEM0_DIR"]=str(out/"private-library-config")
 os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
 os.environ.setdefault("FASTEMBED_CACHE_PATH","/tmp/beyond-recall-bge-model")
 os.environ["OMP_NUM_THREADS"]="2"
 if offline:os.environ["HF_HUB_OFFLINE"]="1"

def existing_from_prompt(messages):
 user=next(x["content"] for x in messages if x["role"]=="user")
 match=re.search(r"## Existing Memories\n(.*?)\n\n## New Messages",user,re.S)
 if not match:raise ValueError("Native prompt section layout changed")
 values=json.loads(match.group(1))
 if not isinstance(values,list):raise ValueError("Expected native existing-memory list")
 return values

class ControlledLLM:
 """Explicit dependency injection through native LlmFactory registration."""
 def __init__(self,config=None):self.config=config
 def generate_response(self,messages,**kwargs):
  existing=existing_from_prompt(messages)
  visible={m["text"] for m in existing}
  candidates=ACTIVE["facts"]
  chosen=[x for x in candidates if ACTIVE["extractor"]=="literal_reemit" or x not in visible]
  before_filter=list(chosen)
  # An authored sequential control. It changes admission rather than retrieval.
  # This read/filter is NOT an atomic multi-writer protocol.
  if ACTIVE["arm"]=="exact_admission":
   full=ACTIVE["memory"].get_all(filters={"user_id":"synthetic-study-user"},top_k=10000,show_expired=True)["results"]
   known={x["memory"] for x in full}
   chosen=[x for x in chosen if x not in known]
  response={"memory":[{"id":str(i),"text":text,"attributed_to":"user","linked_memory_ids":[]} for i,text in enumerate(chosen)]}
  ACTIVE["calls"].append(dict(existing=existing,emitted_before_admission_filter=before_filter,
    emitted_texts=chosen,response=response,
    system_prompt_sha256=hashlib.sha256(messages[0]["content"].encode()).hexdigest(),
    user_prompt_sha256=hashlib.sha256(messages[1]["content"].encode()).hexdigest()))
  return json.dumps(response)

class HashEmbedding:
 """Nonsemantic control. No retrieval-quality claim is made for this arm."""
 def __init__(self,config=None):self.config=config
 def embed(self,text,memory_action=None):
  values=[(b-127.5)/127.5 for b in hashlib.sha256(text.encode()).digest()]
  norm=math.sqrt(sum(x*x for x in values))
  return [x/norm for x in values]
 def embed_batch(self,texts,memory_action="add"):
  return [self.embed(t,memory_action) for t in texts]

def memory(folder,embedder,arm):
 from mem0 import Memory
 from mem0.configs.base import MemoryConfig
 from mem0.llms.configs import LlmConfig
 from mem0.embeddings.configs import EmbedderConfig
 from mem0.utils.factory import LlmFactory,EmbedderFactory
 LlmFactory.register_provider("study_controlled",__name__+".ControlledLLM")
 # Native configuration validation predates dynamic registration. Construct only
 # this study-supplied dependency config; native memory/store code stays intact.
 llm=LlmConfig.model_construct(provider="study_controlled",config={})
 if embedder=="hash_control":
  EmbedderFactory.provider_to_class["study_hash"]=__name__+".HashEmbedding"
  emb=EmbedderConfig.model_construct(provider="study_hash",config={"embedding_dims":32});dims=32
 else:
  emb=EmbedderConfig(provider="fastembed",config={"model":"BAAI/bge-small-en-v1.5","embedding_dims":384});dims=384
 config=MemoryConfig(llm=llm,embedder=emb,
  vector_store={"provider":"qdrant","config":{"collection_name":"study_memories","path":str(folder/"qdrant"),"embedding_model_dims":dims}},
  history_db_path=str(folder/"history.sqlite"))
 m=Memory(config)
 original_search=m.vector_store.search
 def observed_search(*args,**kwargs):
  requested=kwargs.get("top_k")
  if arm=="widened_candidates" and requested==10:kwargs["top_k"]=10000
  result=original_search(*args,**kwargs)
  ACTIVE["searches"].append(dict(requested_top_k=requested,effective_top_k=kwargs.get("top_k"),
   filters=kwargs.get("filters"),query_sha256=hashlib.sha256(kwargs.get("query","").encode()).hexdigest(),
   returned=[dict(id=x.id,text=x.payload.get("data"),hash=x.payload.get("hash")) for x in result]))
  return result
 m.vector_store.search=observed_search
 return m

def environment():
 return {"python":sys.version,"sqlite":sqlite3.sqlite_version,
  "packages":{x:importlib.metadata.version(x) for x in ("mem0ai","qdrant-client","fastembed","onnxruntime","numpy","pydantic")}}

def prepare(out):
 out.mkdir(parents=True,exist_ok=False);setup_environment(out,offline=False)
 import mem0.memory.main
 source=Path(mem0.memory.main.__file__)
 spec=dict(prepared_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
  design="8 batch sizes x2 extraction controls x2 embedders x3 admission/retrieval arms =96 parameterized executions; each has initial add and two exact-source redeliveries",
  source_commit=EXPECTED_SOURCE,installed_main_sha256=sha(source),runner_sha256=sha(__file__),
  sizes=SIZES,arms=ARMS,extractors=EXTRACTORS,embedders=EMBEDDERS,facts=FACTS,
  source_url="https://github.com/mem0ai/mem0/tree/"+EXPECTED_SOURCE,
  hypothesis="For an already stored N-fact exact-literal set, a top-k candidate set contains at most k distinct hashes. If the extractor reemits every fact omitted from that candidate set and admission hashes only candidates, at least max(0,N-k) repeated physical facts can be inserted per replay. This is conditional on the controlled extraction and current pinned implementation.",
  outcomes=["native physical record count","distinct exact fact strings","extra physical copies","ADD result count","ADD history count","write-time candidate count and distinct hashes","literal returned extraction"],
  positive_controls="A widened candidate set and a sequential exact-admission filter should suppress the specified duplicates without changing the initial exact fact set.",
  recently_extracted_context="Native recently_extracted_memories argument remains its default empty value. Last-message history is allowed as actually used by the native pipeline; controlled extractors deliberately use either all exact facts or visible candidate texts only.",
  scope="Controlled extraction is not live-model behavior. Hash embeddings are not semantic embeddings. BGE embeddings are real local ONNX inference. Widened and exact-admission arms are authored interventions, not stock API flags or a concurrent deduplication solution. No natural incidence or exactly-once vendor promise is asserted.",
  preregistration="Source-audit-motivated design frozen before measured executions; not externally preregistered. Development feasibility is separate.",
  environment=environment())
 write(out/"frozen_spec.json",spec)
 (out/"spec.sha256").write_text(sha(out/"frozen_spec.json")+"\n")
 print(json.dumps({"prepared":str(out),"parameterized_executions":96,"spec_sha256":sha(out/"frozen_spec.json")}))

def snapshot(m):
 rows=m.get_all(filters={"user_id":"synthetic-study-user"},top_k=10000,show_expired=True)["results"]
 return sorted(rows,key=lambda r:r["id"])

def execute(out,embedder,extractor,arm,n):
 folder=out/"state"/f"{embedder}__{extractor}__{arm}__n{n}";folder.mkdir(parents=True,exist_ok=False)
 ACTIVE.clear();ACTIVE.update(facts=FACTS[:n],extractor=extractor,arm=arm,calls=[],searches=[])
 m=memory(folder,embedder,arm);ACTIVE["memory"]=m;attempts=[]
 messages=[{"role":"user","content":"Please remember these synthetic preferences:\n"+"\n".join(FACTS[:n])}]
 try:
  for attempt in range(3):
   before_calls=len(ACTIVE["calls"]);before_searches=len(ACTIVE["searches"])
   result=m.add(messages,user_id="synthetic-study-user",infer=True)
   rows=snapshot(m);facts=[r["memory"] for r in rows]
   with sqlite3.connect(folder/"history.sqlite") as c:
    tables=c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    history_count=c.execute("SELECT COUNT(*) FROM history WHERE event='ADD'").fetchone()[0]
   attempts.append(dict(attempt=attempt,result=result,records=rows,physical_records=len(rows),
    extraction_calls_this_attempt=len(ACTIVE["calls"])-before_calls,search_calls_this_attempt=len(ACTIVE["searches"])-before_searches,
    distinct_facts=len(set(facts)),extra_copies=len(rows)-len(set(facts)),fact_set_matches=set(facts)==set(FACTS[:n]),
    add_history_rows=history_count,extraction=ACTIVE["calls"][-1],search=ACTIVE["searches"][-1]))
  row=dict(embedder=embedder,extractor=extractor,arm=arm,n=n,attempts=attempts)
  write(folder/"case.json",row);return row
 finally:
  m.close()
  m.vector_store.client.close()

def run(out):
 setup_environment(out)
 spec=json.loads((out/"frozen_spec.json").read_text())
 assert spec["runner_sha256"]==sha(__file__) and (out/"spec.sha256").read_text().strip()==sha(out/"frozen_spec.json")
 import mem0.memory.main
 assert spec["installed_main_sha256"]==sha(mem0.memory.main.__file__)
 # Fail closed: local Qdrant + prewarmed model need no outbound network.
 original_connect=socket.socket.connect
 def no_external(sock,address):
  if isinstance(address,tuple) and address[0] not in ("127.0.0.1","::1","localhost"):
   raise RuntimeError("Unexpected external network attempt during offline campaign")
  return original_connect(sock,address)
 socket.socket.connect=no_external
 rows=[]
 for embedder in EMBEDDERS:
  for extractor in EXTRACTORS:
   for arm in ARMS:
    for n in SIZES:
     row=execute(out,embedder,extractor,arm,n);rows.append(row)
     print(canonical({"case":f"{embedder}/{extractor}/{arm}/{n}","physical":[x["physical_records"] for x in row["attempts"]]}),flush=True)
 assert len(rows)==96
 write(out/"cases.json",rows);write(out/"environment.json",environment())
 summarize(out,rows)

def summarize(out,rows):
 groups=[]
 for embedder in EMBEDDERS:
  for extractor in EXTRACTORS:
   for arm in ARMS:
    r=[x for x in rows if (x["embedder"],x["extractor"],x["arm"])==(embedder,extractor,arm)]
    groups.append(dict(embedder=embedder,extractor=extractor,arm=arm,executions=len(r),
     final_extra_copies=sum(x["attempts"][-1]["extra_copies"] for x in r),
     final_fact_set_passes=sum(x["attempts"][-1]["fact_set_matches"] for x in r)))
 write(out/"summary.json",dict(parameterized_executions=len(rows),groups=groups,
  interpretation="Finite source-audit parameter sweep, not independent model trials or population incidence. Inspect per-case rows and all raw native stores."))
 print(json.dumps(groups,indent=2))

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("action",choices=["prepare","run"]);p.add_argument("--out",required=True,type=Path);a=p.parse_args();a.out=a.out.resolve()
 prepare(a.out) if a.action=="prepare" else run(a.out)
