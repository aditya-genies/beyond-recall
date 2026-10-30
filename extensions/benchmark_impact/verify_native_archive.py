"""Independently stream-check every archived byte against its manifest."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,tarfile

def verify(path):
 observed={}
 with tarfile.open(path,mode='r|xz') as archive:
  iterator=iter(archive);first=next(iterator);assert first.name=='ARCHIVE_MANIFEST.json' and first.isfile()
  manifest=json.load(archive.extractfile(first));expected={r['path']:r for r in manifest['files']};assert len(expected)==len(manifest['files'])
  for member in iterator:
   relative=PurePosixPath(member.name)
   assert member.isfile() and not relative.is_absolute() and '..' not in relative.parts
   assert member.name in expected and member.name not in observed
   assert member.size==expected[member.name]['bytes']
   digest=hashlib.sha256();size=0
   source=archive.extractfile(member)
   for block in iter(lambda:source.read(2**20),b''):digest.update(block);size+=len(block)
   assert size==member.size and digest.hexdigest()==expected[member.name]['sha256'],member.name
   observed[member.name]=digest.hexdigest()
 assert set(observed)==set(expected)
 digest=hashlib.sha256()
 with path.open('rb') as source:
  for block in iter(lambda:source.read(2**20),b''):digest.update(block)
 report={'status':'PASS','archive':path.name,'archive_bytes':path.stat().st_size,'archive_sha256':digest.hexdigest(),'verified_payload_files':len(observed),'verified_uncompressed_bytes':sum(r['bytes'] for r in expected.values()),'scope':'Every member is a safe regular-file path and matches original manifest size/SHA; tar headers normalized, raw file bytes preserved.'}
 output=path.with_suffix(path.suffix+'.verified.json');output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('archive',type=Path);a=p.parse_args();verify(a.archive.resolve())
