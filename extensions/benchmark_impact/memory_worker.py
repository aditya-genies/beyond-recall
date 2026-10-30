"""Native raw-document memory participants; no extractor LLM is called.

Mem0's documented infer=False API and LlamaIndex's persistent vector index are
different participants. This is not an experiment in native inferred fact quality.
Authored sequential admission controls are not concurrent uniqueness guarantees.
"""
from __future__ import annotations
import argparse,hashlib,json,os,sqlite3,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
USER='independent-benchmark-participant'
MODES=('native_once','native_retry','event_admission','content_admission')
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def sha_obj(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def content(e):return e['speaker']+': '+e['text']
def metadata(e):return {'study_event_id':e['event_id'],'study_source_id':e['source_id'],'study_date':e['occurred_at'],'study_body_sha256':sha_obj(e)}
def validate_episode(episode):
 if not isinstance(episode,dict) or set(episode)!={'scope','events'} or not isinstance(episode['scope'],str) or not isinstance(episode['events'],list):raise ValueError('Unexpected episode/evaluator field')
 seen=set()
 for e in episode['events']:
  if not isinstance(e,dict) or set(e)!={'event_id','source_id','occurred_at','speaker','text'} or not all(isinstance(v,str) for v in e.values()):raise ValueError('Unexpected event/evaluator field')
  if e['event_id'] in seen:raise ValueError('Non-unique occurrence identity in original history')
  seen.add(e['event_id'])
 return episode

class EmbeddingCache:
 def __init__(self,path,namespace,document,query,manifest):
  self.conn=sqlite3.connect(path,timeout=30);self.conn.execute('PRAGMA journal_mode=WAL');self.conn.execute('BEGIN IMMEDIATE');self.conn.execute('CREATE TABLE IF NOT EXISTS embeddings(k TEXT PRIMARY KEY,v TEXT NOT NULL)');self.conn.execute('CREATE TABLE IF NOT EXISTS manifest(h TEXT PRIMARY KEY)')
  try:
   h=file_sha(manifest);prior=self.conn.execute('SELECT h FROM manifest').fetchall()
   if prior and prior!=[(h,)]:raise ValueError('Embedding cache manifest differs')
   if not prior:
    if self.conn.execute('SELECT COUNT(*) FROM embeddings').fetchone()[0]:raise ValueError('Unbound preexisting embedding cache')
    self.conn.execute('INSERT INTO manifest VALUES(?)',(h,))
   self.conn.commit()
  except Exception:self.conn.rollback();self.conn.close();raise
  self.namespace=namespace+'@'+h;self.document=document;self.query=query
 def get(self,text,kind):
  key=sha_obj([self.namespace,kind,text]);row=self.conn.execute('SELECT v FROM embeddings WHERE k=?',(key,)).fetchone()
  if row:return json.loads(row[0])
  v=list(map(float,(self.query if kind=='query' else self.document)(text)))
  self.conn.execute('INSERT OR IGNORE INTO embeddings VALUES(?,?)',(key,json.dumps(v)));self.conn.commit();return v
 def close(self):self.conn.close()

class Mem0Participant:
 def __init__(self,folder,cache,manifest):
  sys.path.insert(0,str(ROOT/'extensions/replanning_contracts/mem0_reference'))
  import experiment as old
  old.setup_environment(folder);old.ACTIVE.clear();old.ACTIVE.update(calls=[],searches=[],facts=[],extractor='literal_reemit',arm='native_k10')
  self.old=old;self.memory=old.memory(folder,'bge_small','native_k10');original=self.memory.embedding_model
  self.cache=EmbeddingCache(cache,'mem0-fastembed-bge-small-en-v1.5',lambda text:original.embed(text,'add'),lambda text:original.embed(text,'search'),manifest)
  owner=self
  class Cached:
   config=getattr(original,'config',None)
   def embed(self,text,memory_action=None):return owner.cache.get(text,'query' if memory_action=='search' else 'document')
   def embed_batch(self,texts,memory_action='add'):return [self.embed(t,memory_action) for t in texts]
  self.memory.embedding_model=Cached()
 def add(self,e):
  rows=self.memory.add([{'role':'user','content':content(e)}],user_id=USER,metadata=metadata(e),infer=False)['results']
  if len(rows)!=1:raise AssertionError('Native raw add did not create one record')
  return rows[0]['id']
 def rows(self):
  rows=self.memory.get_all(filters={'user_id':USER},top_k=10000,show_expired=True)['results']
  return [self.convert(r) for r in rows]
 def convert(self,r):
  m=r.get('metadata',{})
  return {'physical_id':r['id'],'text':r['memory'],'event_id':m['study_event_id'],'source_id':m['study_source_id'],'occurred_at':m['study_date'],'body_sha256':m['study_body_sha256'],'score':r.get('score')}
 def query(self,text,limit):return [self.convert(r) for r in self.memory.search(text,filters={'user_id':USER},top_k=limit,threshold=0,show_expired=False)['results']]
 def persist(self):pass # Native add commits its own point/history mutations.
 def close(self):
  if self.old.ACTIVE['calls']:raise AssertionError('Unexpected extraction call in raw-document participant')
  self.memory.close();self.memory.vector_store.client.close();self.cache.close()

class LlamaParticipant:
 def __init__(self,folder,cache,manifest):
  from llama_index.core import VectorStoreIndex,StorageContext,load_index_from_storage,Settings
  from llama_index.embeddings.fastembed import FastEmbedEmbedding
  Settings.llm=None
  self.folder=folder;self.embedding=FastEmbedEmbedding(model_name='BAAI/bge-small-en-v1.5',cache_dir='/tmp/beyond-recall-bge-model',threads=2)
  self.cache=EmbeddingCache(cache,'llama-index-fastembed-bge-small-en-v1.5',self.embedding.get_text_embedding,self.embedding.get_query_embedding,manifest)
  self.index=load_index_from_storage(StorageContext.from_defaults(persist_dir=str(folder/'storage')),embed_model=self.embedding) if (folder/'storage/docstore.json').exists() else VectorStoreIndex(nodes=[],embed_model=self.embedding)
 def add(self,e):
  from llama_index.core.schema import TextNode
  node=TextNode(text=content(e),metadata=metadata(e),excluded_embed_metadata_keys=list(metadata(e)),excluded_llm_metadata_keys=list(metadata(e)))
  node.embedding=self.cache.get(content(e),'document');self.index.insert_nodes([node]);return node.node_id
 def rows(self):
  return [self.convert(node) for node in self.index.docstore.docs.values() if getattr(node,'text',None) is not None]
 def convert(self,node,score=None):
  m=node.metadata
  return {'physical_id':node.node_id,'text':node.text,'event_id':m['study_event_id'],'source_id':m['study_source_id'],'occurred_at':m['study_date'],'body_sha256':m['study_body_sha256'],'score':score}
 def query(self,text,limit):
  from llama_index.core.schema import QueryBundle
  q=QueryBundle(query_str=text,embedding=self.cache.get(text,'query'))
  return [self.convert(r.node,r.score) for r in self.index.as_retriever(similarity_top_k=limit).retrieve(q)]
 def persist(self):self.index.storage_context.persist(persist_dir=str(self.folder/'storage'))
 def close(self):self.cache.close()

def admit(participant,event,mode,known_events,known_text):
 text=content(event);body=sha_obj(event)
 if mode=='event_admission' and event['event_id'] in known_events:
  if known_events[event['event_id']]!=body:raise ValueError('Same occurrence identity with different body')
  return {'status':'suppressed_event_replay','event_id':event['event_id']}
 if mode=='content_admission' and text in known_text:return {'status':'suppressed_exact_content','event_id':event['event_id']}
 physical=participant.add(event);known_events[event['event_id']]=body;known_text.add(text)
 return {'status':'applied','event_id':event['event_id'],'physical_id':physical}

def run(args):
 for key in list(os.environ):
  if key.endswith('_API_KEY') or key in ['HF_TOKEN','HUGGING_FACE_HUB_TOKEN']:os.environ.pop(key)
 os.environ.update(HF_HUB_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',MEM0_TELEMETRY='false',OMP_NUM_THREADS='2')
 folder=args.folder.resolve();folder.mkdir(parents=True,exist_ok=True)
 if args.action in ('initial','retry'):
  episode=validate_episode(json.loads(args.episode.read_text()))
  if args.action=='initial' and args.mode!='native_once':raise ValueError('Initialize one common native baseline before cloning controls')
  if args.action=='retry' and args.mode=='native_once':raise ValueError('Clean baseline cannot receive replay writes')
 participant=(Mem0Participant if args.backend=='mem0_raw' else LlamaParticipant)(folder,args.cache.resolve(),args.embedding_manifest)
 before=participant.rows();known_events={r['event_id']:r['body_sha256'] for r in before};known_text={r['text'] for r in before};started=time.monotonic()
 try:
  if args.action in ('initial','retry'):
   events=episode['events']
   if len(events)*3>10000:raise ValueError('Case exceeds the declared native snapshot bound')
   if args.action=='retry':events=[e for e in events if e['source_id'] in set(json.loads(args.retry_sources.read_text()))]
   receipts=[]
   for delivery in range(1 if args.action=='initial' else args.redeliveries):
    for e in events:receipts.append(admit(participant,e,args.mode,known_events,known_text))
   participant.persist();after=participant.rows();write(folder/(args.action+'_receipts.json'),receipts);write(folder/(args.action+'_snapshot.json'),after)
   report={'backend':args.backend,'mode':args.mode,'phase':args.action,'before_count':len(before),'after_count':len(after),'submitted_events':len(events),'redeliveries':1 if args.action=='initial' else args.redeliveries,'wall_seconds':round(time.monotonic()-started,4),'extraction_calls':0,'fault':'Actual os._exit87 after native writes/persistence and raw witness, before logical batch acknowledgement' if args.cut else None}
   write(folder/(args.action+'_status.json'),report);print(json.dumps(report),flush=True)
   if args.cut:os._exit(87)
  else:
   queries=json.loads(args.queries.read_text());out=[]
   for q in queries:
    # Only query text and an opaque invocation key cross this boundary.
    if set(q)!={'invocation','question'}:raise ValueError('Unexpected query-side evaluator field')
    out.append({'invocation':q['invocation'],'candidates':participant.query(q['question'],args.limit)})
   write(args.output,out)
 finally:participant.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['initial','retry','query']);p.add_argument('--backend',choices=['mem0_raw','llama_index'],required=True);p.add_argument('--mode',choices=MODES,required=True);p.add_argument('--folder',type=Path,required=True);p.add_argument('--cache',type=Path,required=True)
 p.add_argument('--embedding-manifest',type=Path,required=True);p.add_argument('--episode',type=Path);p.add_argument('--retry-sources',type=Path);p.add_argument('--queries',type=Path);p.add_argument('--output',type=Path);p.add_argument('--redeliveries',type=int,default=2);p.add_argument('--limit',type=int,default=60);p.add_argument('--cut',action='store_true');run(p.parse_args())
