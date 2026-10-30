"""Real SQLite transaction adapter; deliberately distinct authored write profiles."""
import copy
import json
from pathlib import Path
import sqlite3

from .contract import body,canonical,initial_state,result

class SQLiteStore:
 def __init__(self,path,profile):self.path=Path(path);self.profile=profile
 def connect(self):
  connection=sqlite3.connect(self.path,timeout=15);connection.execute('PRAGMA synchronous=FULL');connection.execute('PRAGMA journal_mode=DELETE');return connection
 def initialize(self):
  connection=self.connect()
  try:
   if self.profile=='envelope':
    connection.execute('CREATE TABLE envelope(id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
    connection.execute('INSERT INTO envelope VALUES(?,?)',('record',canonical(initial_state()|{'receipts':{}})))
   else:
    connection.executescript('CREATE TABLE record(id TEXT PRIMARY KEY,value TEXT,visible INTEGER,origin TEXT,record_epoch INTEGER,version INTEGER,epoch INTEGER,history TEXT); CREATE TABLE receipts(opid TEXT PRIMARY KEY,body TEXT,outcome TEXT);')
    connection.execute('INSERT INTO record VALUES(?,?,?,?,?,?,?,?)',('record',None,0,None,None,0,0,'[]'))
   connection.commit()
  finally:connection.close()
 def _read(self,c):
  if self.profile=='envelope':return json.loads(c.execute("SELECT payload FROM envelope WHERE id='record'").fetchone()[0])
  row=c.execute("SELECT value,visible,origin,record_epoch,version,epoch,history FROM record WHERE id='record'").fetchone()
  return dict(value=row[0],visible=bool(row[1]),origin=row[2],record_epoch=row[3],version=row[4],epoch=row[5],history=json.loads(row[6]))
 def _write(self,c,state):
  if self.profile=='envelope':c.execute("UPDATE envelope SET payload=? WHERE id='record'",(canonical(state),))
  else:c.execute("UPDATE record SET value=?,visible=?,origin=?,record_epoch=?,version=?,epoch=?,history=? WHERE id='record'",(state['value'],int(state['visible']),state['origin'],state['record_epoch'],state['version'],state['epoch'],canonical(state['history'])))
 def _storage_valid(self,c):
  return [row[1] for row in c.execute('PRAGMA table_info(receipts)')]==['opid','body','outcome']
 def _receipt(self,c,state,identity):
  if self.profile=='envelope':return state['receipts'].get(identity)
  row=c.execute('SELECT body,outcome FROM receipts WHERE opid=?',(identity,)).fetchone()
  return dict(body=row[0],outcome=json.loads(row[1])) if row else None
 def _put_receipt(self,c,state,op,receipt):
  if self.profile=='envelope':state['receipts'][op['opid']]=receipt
  else:c.execute('INSERT INTO receipts VALUES(?,?,?)',(op['opid'],receipt['body'],canonical(receipt['outcome'])))
 def snapshot(self):
  c=self.connect()
  try:
   state=self._read(c)
   if self.profile=='envelope':
    receipts=state.pop('receipts');raw={'envelope':json.loads(c.execute("SELECT payload FROM envelope WHERE id='record'").fetchone()[0])};kind='envelope'
   else:
    valid=self._storage_valid(c)
    receipts={row[0]:dict(body=row[1],outcome=json.loads(row[2])) for row in c.execute('SELECT opid,body,outcome FROM receipts ORDER BY opid')} if valid else None
    raw={'record':dict(state),'receipts_table_columns':[row[1] for row in c.execute('PRAGMA table_info(receipts)')]};kind='table' if valid else 'missing_or_invalid_table'
   return dict(state=state,receipts=receipts,receipt_storage=kind,raw=raw)
  finally:c.close()
 def entry(self,op):
  snap=self.snapshot()
  if snap['receipts'] is None:raise sqlite3.OperationalError('receipt storage unavailable at entry')
  receipt=snap['receipts'].get(op['opid'])
  return snap,(result('historical_ack') if receipt['body']==body(op) else result('body_conflict')) if receipt else None
 def apply_new(self,op,before_error=False,after_effect=None):
  c=self.connect();split=self.profile=='split'
  try:
   c.execute('BEGIN IMMEDIATE');state=self._read(c)
   if self.profile in ('preflight','envelope'):
    if self.profile=='preflight' and not self._storage_valid(c):c.commit();return result('receipt_storage_invalid')
    receipt=self._receipt(c,state,op['opid'])
    if receipt:c.commit();return result('historical_ack') if receipt['body']==body(op) else result('body_conflict')
   if state['epoch']!=op['expected_epoch']:c.commit();return result('stale_epoch')
   if state['version']!=op['expected_version']:c.commit();return result('stale_version')
   if before_error:c.execute('SELECT controlled_missing_column FROM controlled_absent_table')
   state['version']+=1;state.update(value=op['value'],visible=True,origin=op['opid'],record_epoch=op['expected_epoch'])
   state['history'].append(dict(kind='participant',opid=op['opid'],body=body(op),value=op['value'],version=state['version'],epoch=state['epoch']))
   receipt=dict(body=body(op),outcome=dict(value=op['value'],version=state['version'],epoch=state['epoch']))
   if self.profile=='envelope':self._put_receipt(c,state,op,receipt)
   self._write(c,state)
   if not split and self.profile!='envelope':self._put_receipt(c,state,op,receipt)
   c.commit()
  except BaseException:c.rollback();raise
  finally:c.close()
  if split:
   if after_effect is not None:after_effect()
   c=self.connect()
   try:
    c.execute('BEGIN IMMEDIATE');self._put_receipt(c,None,op,receipt);c.commit()
   except BaseException:c.rollback();raise
   finally:c.close()
  return result('applied',changed=True)
 def control(self,kind,value=None,opid='A'):
  c=self.connect()
  try:
   c.execute('BEGIN IMMEDIATE')
   if kind=='poison_receipts':
    if self.profile=='envelope':raise ValueError('no separate receipt table in envelope')
    c.execute('DROP TABLE receipts')
   elif kind=='gc_receipt':
    if self.profile=='envelope':
     state=self._read(c);state['receipts'].pop(opid,None);self._write(c,state)
    else:c.execute('DELETE FROM receipts WHERE opid=?',(opid,))
   else:
    state=self._read(c)
    if kind=='revoke':
     state['epoch']+=1;state.update(value=None,visible=False,origin=None,record_epoch=None)
     state['history'].append(dict(kind='revoke',epoch=state['epoch'],version=state['version']))
    elif kind=='foreign':
     state['version']+=1;state.update(value=value,visible=True,origin='external',record_epoch=state['epoch'])
     state['history'].append(dict(kind='foreign',value=value,version=state['version'],epoch=state['epoch']))
    else:raise ValueError('unknown control')
    self._write(c,state)
   c.commit()
  except BaseException:c.rollback();raise
  finally:c.close()
