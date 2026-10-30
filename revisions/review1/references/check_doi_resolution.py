from pathlib import Path
from urllib import request,error
import concurrent.futures,datetime,json,hashlib
H=Path(__file__).resolve().parent
seeds=[('li2026where','2609.29095'),('marla2026permission','2610.31916'),('sun2026agentic','2608.13900')]
class Tracker(request.HTTPRedirectHandler):
 def __init__(self):super().__init__();self.log=[]
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  self.log.append({'status':code,'from':req.full_url,'to':newurl});return super().redirect_request(req,fp,code,msg,headers,newurl)
def get(s):
 key,aid=s;t=Tracker();url='https://doi.org/10.48550/arXiv.'+aid;d={'key':key,'requested_url':url,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  opener=request.build_opener(t)
  with opener.open(request.Request(url,headers={'User-Agent':'IndependentRecoveryStudy-CitationAudit/1.0','Cache-Control':'no-cache'}),timeout=35) as r:
   raw=r.read();name=key+'.doi_resolution.html';(H/name).write_bytes(raw);d.update(status='resolved',http_status=r.status,final_url=r.url,path='revisions/review1/references/'+name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 except error.HTTPError as e:d.update(status='http_error',http_status=e.code,error=str(e))
 except Exception as e:d.update(status='network_error',error=repr(e))
 d['redirects']=t.log;return d
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as e:rows=list(e.map(get,seeds))
(H/'doi_resolution.json').write_text(json.dumps({'records':rows},indent=2));print(json.dumps(rows,indent=2))
