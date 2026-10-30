"""Fetch primary public references externally; retain only metadata/hashes here."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from html.parser import HTMLParser
import hashlib,json,urllib.request

HERE=Path(__file__).resolve().parent
CACHE=Path('/tmp/beyond-recall-benchmark-impact-literature-20261029')
CACHE.mkdir(parents=True,exist_ok=True)

class Text(HTMLParser):
    def __init__(self):super().__init__();self.skip=0;self.bits=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip and data.strip():self.bits.append(data.strip())

def fetch(rec):
    key,url,ext=rec
    result=dict(key=key,url=url,retrieved_utc=datetime.now(timezone.utc).isoformat(),
        full_text_or_code_in_repository=False)
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Public academic evidence audit/1.0'}),timeout=50) as response:
            raw=response.read()
            result.update(http_status=response.status,final_url=response.geturl(),content_type=response.headers.get('Content-Type'))
        path=CACHE/f'{key}.{ext}';path.write_bytes(raw)
        result.update(status='saved_external_cache',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),cache_filename=path.name)
        if ext=='html':
            parser=Text();parser.feed(raw.decode('utf-8',errors='replace'))
            (CACHE/f'{key}.txt').write_text('\n'.join(parser.bits))
    except Exception as error:
        result.update(status='unavailable',error=str(error))
    return result

def main():
    records=[]
    for aid in ['2610.25561','2605.12493','2604.05467','2410.10813','2402.17753']:
        key=aid.replace('.','_')
        records.extend((key+suffix,url,ext) for suffix,url,ext in [
          ('_abs','https://arxiv.org/abs/'+aid,'html'),
          ('_html','https://arxiv.org/html/'+aid,'html'),
          ('_pdf','https://arxiv.org/pdf/'+aid,'pdf'),
          ('_datacite','https://api.datacite.org/dois/10.48550/arXiv.'+aid,'json')])
    for aid in ['2024.acl-long.562','2026.acl-long.923','2026.acl-long.1357']:
        key=aid.replace('.','_')
        records += [(key+'_landing','https://aclanthology.org/'+aid+'/','html'),
                    (key+'_pdf','https://aclanthology.org/'+aid+'.pdf','pdf'),
                    (key+'_bib','https://aclanthology.org/'+aid+'.bib','bib'),
                    (key+'_crossref','https://api.crossref.org/works/10.18653/v1/'+aid,'json')]
    records += [('plur_checklist','https://plur.ai/blog/agent-memory-tool-duplicate-write-checklist/','html'),
       ('agentmemory_readme','https://raw.githubusercontent.com/rohitg00/agentmemory/main/README.md','md'),
       ('agentmemory_head','https://api.github.com/repos/rohitg00/agentmemory/commits/main','json'),
       ('agentmemory_tree','https://api.github.com/repos/rohitg00/agentmemory/git/trees/main?recursive=1','json'),
       ('longmemeval_tree','https://api.github.com/repos/xiaowu0162/LongMemEval/git/trees/9e0b455f4ef0e2ab8f2e582289761153549043fc?recursive=1','json'),
       ('locomo_tree','https://api.github.com/repos/snap-research/locomo/git/trees/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376?recursive=1','json'),
       ('longmemeval_v2_readme','https://raw.githubusercontent.com/xiaowu0162/LongMemEval-V2/2cc8c540bdb87fe6761629b585e727e1c4704520/README.md','md')]
    with ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(fetch,records))
    (HERE/'fetch_manifest.json').write_text(json.dumps(dict(cache_scope='Third-party bodies are external and not redistributed.',records=results),indent=2)+'\n')
    print(json.dumps([dict(key=r['key'],status=r['status'],http_status=r.get('http_status')) for r in results]))

if __name__=='__main__':main()
