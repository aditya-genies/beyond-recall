"""Real Redis EVAL adapter. Multi-write scripts isolate but do not roll back errors."""
import json
from .contract import body, canonical, initial_state, result

# All accessed application keys are explicit KEYS. Decisions, validation and JSON
# construction precede a single SET in envelope. Other profiles intentionally
# have a separate successful-receipt hash; grouped is the declared weaker path.
APPLY_LUA = r'''
local state = cjson.decode(redis.call('GET', KEYS[1]))
local opid, binding, profile = ARGV[1], ARGV[2], ARGV[3]
local op = cjson.decode(binding)
local function outcome(status, changed)
  return cjson.encode({status=status, changed=changed or false,
    historical_ack=status=='historical_ack',
    acknowledged=(status=='applied' or status=='historical_ack')})
end
if profile=='preflight' or profile=='envelope' then
  local receipt
  if profile=='envelope' then
    if type(state.receipts)~='table' then return outcome('receipt_storage_invalid') end
    receipt=state.receipts[opid]
  else
    local storage=redis.call('TYPE',KEYS[2]).ok
    if storage~='none' and storage~='hash' then return outcome('receipt_storage_invalid') end
    local raw=redis.call('HGET',KEYS[2],opid)
    if raw then receipt=cjson.decode(raw) end
  end
  if receipt then
    if receipt.body==binding then return outcome('historical_ack') end
    return outcome('body_conflict')
  end
end
if state.epoch~=op.expected_epoch then return outcome('stale_epoch') end
if state.version~=op.expected_version then return outcome('stale_version') end
if ARGV[4]=='1' then return redis.error_reply('CONTROLLED_BEFORE_EFFECT') end
state.version=state.version+1
state.value=op.value; state.visible=true; state.origin=opid; state.record_epoch=op.expected_epoch
-- Redis cjson encodes an empty Lua table as {}; initial history is [], and it is
-- immediately nonempty after this append. Snapshot canonicalization handles [].
table.insert(state.history,{kind='participant',opid=opid,body=binding,value=op.value,
  version=state.version,epoch=state.epoch})
local receipt={body=binding,outcome={value=op.value,version=state.version,epoch=state.epoch}}
if profile=='envelope' then
  state.receipts[opid]=receipt
  local replacement=cjson.encode(state)
  local reply=outcome('applied',true)
  redis.call('SET',KEYS[1],replacement)
  return reply
end
redis.call('SET',KEYS[1],cjson.encode(state))
if profile=='split' then
  return cjson.encode({status='effect_committed',receipt=receipt})
end
redis.call('HSET',KEYS[2],opid,cjson.encode(receipt))
return outcome('applied',true)
'''

CONTROL_LUA = r'''
local state=cjson.decode(redis.call('GET',KEYS[1]))
local action=ARGV[1]
if action=='gc_receipt' then
  if ARGV[4]=='envelope' then state.receipts[ARGV[3]]=nil
  else redis.call('HDEL',KEYS[2],ARGV[3]); return 1 end
elseif action=='revoke' then
  state.epoch=state.epoch+1
  state.value=cjson.null;state.visible=false;state.origin=cjson.null;state.record_epoch=cjson.null
  table.insert(state.history,{kind='revoke',epoch=state.epoch,version=state.version})
elseif action=='foreign' then
  state.version=state.version+1
  state.value=ARGV[2];state.visible=true;state.origin='external';state.record_epoch=state.epoch
  table.insert(state.history,{kind='foreign',value=ARGV[2],version=state.version,epoch=state.epoch})
else return redis.error_reply('unknown control') end
redis.call('SET',KEYS[1],cjson.encode(state));return 1
'''

class RedisStore:
    def __init__(self, client, namespace, profile):
        self.client=client; self.profile=profile
        self.state_key=namespace+':state'; self.receipt_key=namespace+':receipts'
    def initialize(self):
        state=initial_state()
        if self.profile=='envelope':state['receipts']={}
        self.client.set(self.state_key,canonical(state))
    def _keys(self):
        return [self.state_key] if self.profile=='envelope' else [self.state_key,self.receipt_key]
    def snapshot(self):
        raw_state=self.client.get(self.state_key);state=json.loads(raw_state)
        # cjson turns empty maps into {} (desired for receipts) and may do so for
        # history after GC before any write; normalize only the declared list.
        if state['history']=={}:state['history']=[]
        if self.profile=='envelope':
            receipts=state.pop('receipts');kind='envelope';raw={'state_json':raw_state}
        else:
            kind=self.client.type(self.receipt_key)
            receipts=({key:json.loads(value) for key,value in self.client.hgetall(self.receipt_key).items()}
                      if kind in ('none','hash') else None)
            raw_receipts=(self.client.hgetall(self.receipt_key) if kind=='hash' else
                          self.client.get(self.receipt_key) if kind=='string' else None)
            raw={'state_json':raw_state,'receipts_type':kind,'receipts_data':raw_receipts}
        return dict(state=state,receipts=receipts,receipt_storage=kind,raw=raw)
    def entry(self,op):
        snap=self.snapshot()
        if snap['receipts'] is None:raise RuntimeError('receipt storage unavailable at entry')
        receipt=snap['receipts'].get(op['opid'])
        return snap,((result('historical_ack') if receipt['body']==body(op) else result('body_conflict')) if receipt else None)
    def apply_new(self,op,before_error=False,after_effect=None):
        keys=self._keys()
        reply=json.loads(self.client.eval(APPLY_LUA,len(keys),*keys,op['opid'],body(op),self.profile,'1' if before_error else '0'))
        if reply['status']=='effect_committed':
            if after_effect is not None:after_effect()
            self.client.hset(self.receipt_key,op['opid'],canonical(reply['receipt']))
            return result('applied',changed=True)
        return reply
    def control(self,kind,value=None,opid='A'):
        if kind=='poison_receipts':
            if self.profile=='envelope':raise ValueError('no separate receipt hash')
            self.client.set(self.receipt_key,'controlled-wrong-type');return
        keys=self._keys()
        self.client.eval(CONTROL_LUA,len(keys),*keys,kind,value or '',opid,self.profile)
