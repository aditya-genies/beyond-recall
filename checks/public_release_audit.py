#!/usr/bin/env python3
"""Bounded credential/path scan of every reachable Git blob and staged file.

This complements the source/data scope review; a pattern scan is not a security
proof. Output never includes matched credential bytes. Full reference texts and
local runtime/configuration files are excluded by an explicit release selection.
"""
import argparse, hashlib, json, pathlib, re, subprocess

PATTERNS={
 'openai_key':re.compile(rb'\bsk-[A-Za-z0-9_-]{30,}\b'),
 'github_token':re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{25,}\b'),
 'aws_access_key':re.compile(rb'\bAKIA[A-Z0-9]{16}\b'),
 'private_key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'personal_absolute_path':re.compile(b'/'+b'Users/'+rb'[^\s"<>]+'),
}
def git(*args):return subprocess.check_output(['git',*args])
def main(out):
 reachable={}
 for line in git('rev-list','--objects','--all').decode().splitlines():
  oid,_,name=line.partition(' ');reachable.setdefault(oid,set()).add(name)
 paths=[]
 for record in git('ls-files','-s','-z').decode().split('\0'):
  if not record:continue
  meta,path=record.split('\t',1);mode,oid,stage=meta.split();assert stage=='0'
  reachable.setdefault(oid,set()).add(path);paths.append(path)
 forbidden=[p for p in paths if any(x in pathlib.PurePosixPath(p).parts for x in ('__pycache__','.venv-framework','.venv')) or p.startswith('release/') or p=='revisions/review1/reviewer.txt' or p.startswith('revisions/review1/prior_manuscript/') or p.startswith('revisions/review1/references/positional_identity/') and pathlib.Path(p).suffix in ('.pdf','.html','.txt')]
 findings=[];blobs=0;total=0;manifest=[]
 proc=subprocess.Popen(['git','cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
 try:
  for oid,names in sorted(reachable.items()):
   proc.stdin.write((oid+'\n').encode());proc.stdin.flush()
   header=proc.stdout.readline().decode().strip().split()
   if len(header)!=3:continue
   _,kind,size=header;data=proc.stdout.read(int(size));assert proc.stdout.read(1)==b'\n'
   if kind!='blob':continue
   blobs+=1;total+=len(data)
   for category,pattern in PATTERNS.items():
    if pattern.search(data):findings.append(dict(category=category,blob=oid,paths=sorted(n for n in names if n)))
   manifest.append(dict(git_blob=oid,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
 finally:
  proc.stdin.close();proc.stdout.close();proc.wait(timeout=10)
 report=dict(status='PASS' if not findings and not forbidden else 'FAIL',
  scope='All reachable Git-history blobs plus staged index; known credential shapes and personal absolute paths. Separate source/data review checks synthetic provenance.',
  tracked_paths=len(paths),unique_blobs_scanned=blobs,bytes_scanned=total,findings=findings,
  forbidden_release_paths=forbidden,blob_digest_manifest_sha256=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),
  excluded='Installed environments, raw review attachment, reference full texts, cached venue/source pages, private CLI diagnostics, hidden reasoning and auth/config files.',
  authorised_background='Supplied author employment/degree biography and user-authorized companion repository URL.',
  limit='Pattern and provenance checks reduce accidental disclosure; no universal absence-of-secrets proof is asserted.')
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 if report['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=pathlib.Path);main(p.parse_args().out)
