"""Fresh primary-URL and DOI registry retrieval. No cached corpus input."""
from pathlib import Path
from urllib import request,error
from html.parser import HTMLParser
from pypdf import PdfReader
import concurrent.futures,datetime,hashlib,json
H=Path(__file__).resolve().parent
SEEDS=[('li2026where','2609.29095'),('marla2026permission','2610.31916'),('sun2026agentic','2608.13900')]
class Meta(HTMLParser):
 def __init__(self):super().__init__();self.meta={}
 def handle_starttag(self,t,attrs):
  d=dict(attrs)
  if t=='meta' and d.get('name'):self.meta.setdefault(d['name'],[]).append(d.get('content',''))
def get(job):
 key,aid,kind,url=job;result={'key':key,'arxiv_id':aid,'kind':kind,'requested_url':url,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 headers={'User-Agent':'IndependentRecoveryStudy-CitationAudit/1.0','Cache-Control':'no-cache','Pragma':'no-cache'}
 try:
  with request.urlopen(request.Request(url,headers=headers),timeout=35) as r:
   raw=r.read();result.update(http_status=r.status,final_url=r.url,response_headers={k:r.headers.get(k) for k in ['Content-Type','Date','Last-Modified','ETag','Age','Via'] if r.headers.get(k)})
  suffix='pdf' if kind=='pdf' else ('json' if kind=='datacite' else 'html');name=f'{key}.{kind}.{suffix}';(H/name).write_bytes(raw);result.update(status='saved',path='revisions/review1/references/'+name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
  if kind=='abs':
   p=Meta();p.feed(raw.decode(errors='replace'));result['citation_metadata']=p.meta
  elif kind=='datacite':result['registry_metadata']=json.loads(raw)
  elif kind=='pdf':
   assert raw.startswith(b'%PDF');reader=PdfReader(H/name);pages=[p.extract_text() for p in reader.pages];text='\n'.join(f'\n[PDF PAGE {i+1}]\n'+t for i,t in enumerate(pages));name=f'{key}.fresh.txt';(H/name).write_text(text);result.update(pdf_pages=len(pages),text_path='revisions/review1/references/'+name,text_chars=len(text),first_page=pages[0])
 except error.HTTPError as e:
  result.update(status='http_error',http_status=e.code,error=str(e));body=e.read();name=f'{key}.{kind}.error.txt';(H/name).write_bytes(body);result['error_body_path']='revisions/review1/references/'+name
 except Exception as e:result.update(status='network_or_parse_error',error=repr(e))
 return result
jobs=[]
for key,aid in SEEDS:
 jobs.extend([(key,aid,'abs','https://arxiv.org/abs/'+aid),(key,aid,'pdf','https://arxiv.org/pdf/'+aid),(key,aid,'datacite','https://api.datacite.org/dois/10.48550/arxiv.'+aid)])
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:results=list(ex.map(get,jobs))
(H/'fresh_fetch_manifest.json').write_text(json.dumps({'fetch_policy':'New requests to public canonical primary URLs and the DOI registration agency, with no-cache request headers. Earlier cached reports/PDFs were not read as evidence. HTTP errors are retained and not relabeled as absence or fabrication.','records':results},indent=2))
for r in results:print(json.dumps({k:r[k] for k in ['key','kind','status','http_status','pdf_pages','error'] if k in r}))
