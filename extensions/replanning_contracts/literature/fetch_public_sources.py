"""Fetch public evidence to a non-distributed temporary cache; retain hashes only."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import json,urllib.request,urllib.error,hashlib
HERE=Path(__file__).resolve().parent
CACHE=Path('/tmp/beyond-recall-public-literature-20261029');CACHE.mkdir(exist_ok=True)
IDS=['2607.23929','2609.21284','2609.08258','2609.04875']
class Text(HTMLParser):
 def __init__(self):super().__init__();self.bits=[];self.skip=0
 def handle_starttag(self,t,a):
  if t in ('script','style'):self.skip+=1
 def handle_endtag(self,t):
  if t in ('script','style'):self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip and d.strip():self.bits.append(d.strip())
def fetch(record):
 key,url,extension=record;now=datetime.now(timezone.utc).isoformat();result={'key':key,'url':url,'retrieved_utc':now,'full_text_included_in_repository':False}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Public academic evidence audit/1.0','Cache-Control':'no-cache'}),timeout=40) as r:
   raw=r.read();result.update(http_status=r.status,final_url=r.geturl(),content_type=r.headers.get('Content-Type'))
  path=CACHE/f'{key}.{extension}';path.write_bytes(raw);result.update(status='saved_external_cache',cache_filename=path.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
  if extension=='html':
   t=Text();t.feed(raw.decode('utf-8',errors='replace'));(CACHE/f'{key}.txt').write_text('\n'.join(t.bits))
 except Exception as e:result.update(status='unavailable',error=str(e))
 return result
def main():
 records=[]
 for identifier in IDS:
  k=identifier.replace('.','_')
  records +=[(k+'_abs','https://arxiv.org/abs/'+identifier,'html'),(k+'_html','https://arxiv.org/html/'+identifier,'html'),(k+'_pdf','https://arxiv.org/pdf/'+identifier,'pdf'),(k+'_datacite','https://api.datacite.org/dois/10.48550/arXiv.'+identifier,'json')]
 with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,records))
 (HERE/'new_scholarly_fetch_manifest.json').write_text(json.dumps({'cache_scope':'Non-distributed temporary cache. Only URLs, hashes, bounded claim summaries and metadata are retained in repository.','records':results},indent=2)+'\n')
 print(json.dumps([{'key':r['key'],'status':r['status'],'http_status':r.get('http_status')} for r in results]))
if __name__=='__main__':main()
