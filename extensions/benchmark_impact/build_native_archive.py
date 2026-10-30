"""Byte-preserving native-evidence archive; excludes live grading and weights."""
from pathlib import Path
import argparse,hashlib,io,json,lzma,re,tarfile

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
PATTERNS={'private_machine_path':re.escape((str(Path.home())+'/').encode()),'openai_key_shape':rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}','github_token_shape':rb'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})','aws_key_shape':rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b','private_key':rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'}

def build(output):
 if output.exists():raise FileExistsError(output)
 paths={Path(__file__),HERE/'THIRD_PARTY_DATA.md',HERE/'worker_review_pilot_v2.json',HERE/'worker_review_pilot_audit.py'}
 for version in ('development_pilot_v1','development_pilot_v2'):
  folder=HERE/version
  for group in ('stores','embedding_caches','frozen_source','participants','queries','retry_sources','executions'):
   paths.update(p for p in (folder/group).rglob('*') if p.is_file())
  paths.update(folder.glob('*-embedding-cache.sqlite*'))
  for name in ('protocol.json','protocol.sha256','embedding_manifest.json','evaluator_questions.json','split.json','contexts.json','native_completion.json','abandoned_run.json'):
   p=folder/name
   if p.exists():paths.add(p)
 files=[];findings=[]
 for path in sorted(paths):
  body=path.read_bytes();relative=str(path.relative_to(ROOT))
  if path.is_symlink():raise ValueError('Unexpected symlink: '+relative)
  for label,pattern in PATTERNS.items():
   if re.search(pattern,body):findings.append({'path':relative,'pattern':label})
  files.append({'path':relative,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
 if findings:
  print(json.dumps({'status':'REVIEW_REQUIRED','findings':findings},indent=2));raise ValueError('Archive privacy check requires review; no file bytes changed')
 manifest={'scope':'Native physical stores/caches and frozen input/source witnesses for both retained development versions. No model weights or active grading results.',
  'raw_store_bytes_preserved':True,'tar_header_normalization':'uid/gid/mtime0, mode0644; file content unchanged',
  'privacy_scan':{'status':'PASS','patterns':list(PATTERNS),'scope_limit':'Known credential shapes and this researcher machine path; not a blanket guarantee.'},
  'data_terms':'Derived public LoCoMo material retains CC-BY-NC4.0; see THIRD_PARTY_DATA.md. Independent noncommercial research.',
  'files':files}
 payload=(json.dumps(manifest,indent=2)+'\n').encode();output.parent.mkdir(parents=True,exist_ok=True)
 with lzma.LZMAFile(output,'wb',filters=[{'id':lzma.FILTER_LZMA2,'preset':6,'dict_size':64*1024**2}]) as compressed:
  with tarfile.open(fileobj=compressed,mode='w|') as archive:
   entry=tarfile.TarInfo('ARCHIVE_MANIFEST.json');entry.size=len(payload);entry.mode=0o644;archive.addfile(entry,io.BytesIO(payload))
   for row in files:
    path=ROOT/row['path'];entry=tarfile.TarInfo(row['path']);entry.size=row['bytes'];entry.mode=0o644
    with path.open('rb') as source:archive.addfile(entry,source)
 digest=hashlib.sha256(output.read_bytes()).hexdigest();report={'status':'BUILT_NOT_YET_REOPEN_VERIFIED','archive':output.name,'bytes':output.stat().st_size,'sha256':digest,'payload_files':len(files),'uncompressed_payload_bytes':sum(r['bytes'] for r in files)}
 output.with_suffix(output.suffix+'.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.output.resolve())
