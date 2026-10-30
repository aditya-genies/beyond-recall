"""Three forgery checks using newly authored toy databases, never campaign data."""
from pathlib import Path
import base64,copy,hashlib,json,math,pickle,sqlite3,tempfile,unittest,uuid
from qdrant_client.http.models import PointStruct,SparseVector
import check


class RawEvidenceForgeryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name);self.store=self.folder/'qdrant/collection/study_memories/storage.sqlite'
        self.store.parent.mkdir(parents=True)
        self.facts=['The synthetic user prefers mango as a fruit.'];self.mid=str(uuid.UUID(int=1))
        self.point=self.point_for(self.mid,self.facts[0])
        connection=sqlite3.connect(self.store)
        try:
            connection.execute('CREATE TABLE points(id TEXT PRIMARY KEY,point BLOB)')
            connection.execute('INSERT INTO points VALUES(?,?)',self.serialized(self.point));connection.commit()
        finally:connection.close()
        connection=sqlite3.connect(self.folder/'history.sqlite')
        try:
            connection.execute('CREATE TABLE history(id TEXT PRIMARY KEY,memory_id TEXT,old_memory TEXT,new_memory TEXT,event TEXT,created_at TEXT,updated_at TEXT,is_deleted INTEGER,actor_id TEXT,role TEXT)')
            connection.execute('INSERT INTO history VALUES(?,?,?,?,?,?,?,?,?,?)',('h1',self.mid,None,self.facts[0],'ADD',self.point.payload['created_at'],None,0,None,None));connection.commit()
        finally:connection.close()
        record=dict(id=self.mid,memory=self.facts[0],hash=check.md5(self.facts[0]),metadata=None,created_at=self.point.payload['created_at'],updated_at=self.point.payload['updated_at'],user_id='synthetic-study-user',attributed_to='user')
        response={'memory':[{'id':'0','text':self.facts[0],'attributed_to':'user','linked_memory_ids':[]}]}
        query='user: Please remember these synthetic preferences:\n'+self.facts[0]+'\n'
        attempts=[]
        for n in range(3):
            candidates=[] if n==0 else [dict(id=self.mid,text=self.facts[0],hash=record['hash'])]
            attempts.append(dict(attempt=n,result={'results':[dict(id=self.mid,memory=self.facts[0],event='ADD')] if n==0 else []},records=[copy.deepcopy(record)],physical_records=1,extraction_calls_this_attempt=1,search_calls_this_attempt=1,distinct_facts=1,extra_copies=0,fact_set_matches=True,add_history_rows=1,
                search=dict(requested_top_k=10,effective_top_k=10,filters={'user_id':'synthetic-study-user'},query_sha256=hashlib.sha256(query.encode()).hexdigest(),returned=candidates),
                extraction=dict(existing=[{'id':str(i),'text':c['text']} for i,c in enumerate(candidates)],emitted_before_admission_filter=list(self.facts),emitted_texts=list(self.facts),response=copy.deepcopy(response),system_prompt_sha256='a'*64,user_prompt_sha256='b'*64)))
        self.row=dict(n=1,embedder='hash_control',extractor='literal_reemit',arm='native_k10',attempts=attempts)
        check.check_case(self.row,self.folder,self.facts)  # Each forged fixture first passes intact.

    def point_for(self,mid,text):
        vector=[(x-127.5)/127.5 for x in hashlib.sha256(text.encode()).digest()]
        norm=math.sqrt(sum(x*x for x in vector));vector=[x/norm for x in vector]
        return PointStruct(id=mid,vector={'':vector,'bm25':SparseVector(indices=[],values=[])},payload=dict(user_id='synthetic-study-user',data=text,hash=check.md5(text),created_at='2026-01-01T00:00:00Z',updated_at='2026-01-01T00:00:00Z',attributed_to='user'))

    def serialized(self,point):
        return base64.b64encode(pickle.dumps(point.id,protocol=4)).decode(),pickle.dumps(point)

    def test_rejects_forged_candidate_hash(self):
        self.row['attempts'][1]['search']['returned'][0]['hash']='0'*32
        with self.assertRaisesRegex(check.VerificationError,'Candidate hash mismatch'):
            check.check_case(self.row,self.folder,self.facts)

    def test_rejects_hidden_physical_point_without_history(self):
        extra=self.point_for(str(uuid.UUID(int=2)),self.facts[0])
        connection=sqlite3.connect(self.store)
        try:
            connection.execute('INSERT INTO points VALUES(?,?)',self.serialized(extra));connection.commit()
        finally:connection.close()
        with self.assertRaisesRegex(check.VerificationError,'Physical point/history count mismatch'):
            check.check_case(self.row,self.folder,self.facts)

    def test_rejects_forged_duplicate_metric(self):
        self.row['attempts'][2]['extra_copies']=1
        with self.assertRaisesRegex(check.VerificationError,'extra_copies metric mismatch'):
            check.check_case(self.row,self.folder,self.facts)


if __name__=='__main__':unittest.main()
