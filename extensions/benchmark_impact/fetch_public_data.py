"""Download pinned public data to an explicitly external cache and verify bytes."""
from pathlib import Path
import argparse,hashlib,json,os,tempfile,urllib.request
from data import PINNED

URLS={
 'locomo10.json':'https://raw.githubusercontent.com/snap-research/locomo/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/data/locomo10.json',
 'longmemeval_oracle.json':'https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_oracle.json',
 'longmemeval_s_cleaned.json':'https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_s_cleaned.json'}
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(2**20),b''):h.update(chunk)
 return h.hexdigest()
def fetch(cache):
 cache=cache.resolve();root=Path(__file__).resolve().parents[2]
 if cache==root or root in cache.parents:raise ValueError('Raw data cache must be outside the repository')
 cache.mkdir(parents=True,exist_ok=True)
 for name,url in URLS.items():
  path=cache/name
  if path.exists():
   if digest(path)!=PINNED[name]:raise ValueError('Existing data differs; will not overwrite: '+name)
  else:
   with tempfile.NamedTemporaryFile(dir=cache,prefix='download-',delete=False) as target:
    temporary=Path(target.name)
    try:
     with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'BeyondRecallIndependentResearch/1'}),timeout=120) as response:
      for chunk in iter(lambda:response.read(2**20),b''):target.write(chunk)
     target.flush()
     if digest(temporary)!=PINNED[name]:raise ValueError('Downloaded data digest differs: '+name)
     os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)
  print(json.dumps({'file':name,'bytes':path.stat().st_size,'sha256':PINNED[name],'status':'VERIFIED'}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);a=p.parse_args();fetch(a.cache)
