"""Serialization and caller-side durable prepared-body journal (not a store guarantee)."""
import hashlib
import json
import os
from pathlib import Path

PROFILES=('split','grouped','preflight','envelope')

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def body(operation):return canonical({key:value for key,value in operation.items() if key!='opid'})
def operation(identity='A',value='preferred',version=0,epoch=0):
 return dict(opid=identity,target='record',value=value,expected_version=version,expected_epoch=epoch)
def initial_state():
 return dict(value=None,visible=False,origin=None,record_epoch=None,version=0,epoch=0,history=[])
def result(status,changed=False,**extra):
 return dict(status=status,changed=changed,historical_ack=status=='historical_ack',acknowledged=status in ('applied','historical_ack'),**extra)

def prepare(path,operations):
 path=Path(path);bindings={}
 for op in operations:
  if op['opid'] in bindings and bindings[op['opid']]!=body(op):raise ValueError('conflicting prepared identity')
  bindings[op['opid']]=body(op)
 if path.exists() and json.loads(path.read_text())!=bindings:raise ValueError('prepared journal already bound')
 data=canonical(bindings).encode();temporary=path.with_suffix('.prepared-tmp')
 with temporary.open('wb') as handle:handle.write(data);handle.flush();os.fsync(handle.fileno())
 os.replace(temporary,path)
 descriptor=os.open(path.parent,os.O_RDONLY)
 try:os.fsync(descriptor)
 finally:os.close(descriptor)
 return hashlib.sha256(data).hexdigest()

def validate_prepared(path,op):
 data=Path(path).read_bytes();bindings=json.loads(data)
 return bindings.get(op['opid'])==body(op),hashlib.sha256(data).hexdigest()
