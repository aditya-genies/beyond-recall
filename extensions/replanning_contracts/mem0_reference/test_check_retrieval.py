"""Three independent evidence-forgery tests on newly authored toy states."""
import base64
import copy
import hashlib
import json
import pickle
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path

from qdrant_client.http.models import PointStruct, SparseVector
import check_retrieval as checker


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n')


class RetrievalEvidenceForgeryTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.here=Path(temporary.name)
        self.out=self.here/'retrieval_results'
        self.out.mkdir()
        (self.here/'retrieval.py').write_text('# Newly authored fixture source, never the campaign runner.\n')
        self.facts=['The synthetic user prefers apples.', 'The synthetic user prefers chess.']
        ids=[str(uuid.UUID(int=n)) for n in (1,2,3)]
        payloads=[dict(user_id='synthetic-study-user', data=text,
            hash=hashlib.md5(text.encode()).hexdigest(), created_at='2026-01-01T00:00:00Z',
            updated_at='2026-01-01T00:00:00Z', attributed_to='user') for text in self.facts]
        points=[PointStruct(id=mid,vector={'':[float(j==i) for j in range(384)],
                    'bm25':SparseVector(indices=[i],values=[1.0])},payload=payload)
                for i,(mid,payload) in enumerate(zip(ids,payloads))]
        extra=PointStruct(id=ids[2],vector=copy.deepcopy(points[0].vector),payload=copy.deepcopy(payloads[0]))
        self.rows=[];self.snapshots=[];self.groups=[]
        for state in checker.STATES:
            physical=points+[extra] if state=='native_k10' else points
            folder=checker.source_folder(self.here,2,state)
            self.make_store(folder,physical)
            projected=[self.project(p) for p in physical]
            write(folder/'execution.json',{'after':projected})
            self.snapshots.append(dict(n_source_preferences=2,state=state,native_records=projected,
                query_source='all distinct baseline fact strings',record_state_unchanged_by_search=True))
            returned=[self.project(points[0]),self.project(extra)] if state=='native_k10' else [self.project(p) for p in points]
            for row in returned:
                row['score']=0.75
            for query in self.facts:
                self.rows.append(dict(n_source_preferences=2,state=state,query=query,
                    query_sha256=hashlib.sha256(query.encode()).hexdigest(),budget=2,
                    results=copy.deepcopy(returned),returned_records=2,
                    distinct_literal_facts=1 if state=='native_k10' else 2,
                    duplicate_context_slots=1 if state=='native_k10' else 0,
                    exact_target_present=(query==self.facts[0]) if state=='native_k10' else True))
            self.groups.append(dict(n_source_preferences=2,state=state,budget=2,query_count=2,
                total_returned_records=4,total_distinct_literal_facts=2 if state=='native_k10' else 4,
                duplicate_context_slots=2 if state=='native_k10' else 0,
                minimum_distinct_facts=1 if state=='native_k10' else 2,
                mean_distinct_facts=1.0 if state=='native_k10' else 2.0,
                exact_target_present_count=1 if state=='native_k10' else 2))
        protected={str(p.relative_to(self.here)):checker.digest(p)
            for p in (self.here/'live_results').rglob('*') if p.is_file()}
        write(self.out/'protocol.json',dict(source_sha256=checker.digest(self.here/'retrieval.py'),
            sizes=[2],budgets=[2],states=list(checker.STATES),protected_inputs=protected,model_requests=0))
        (self.out/'protocol.sha256').write_text(checker.digest(self.out/'protocol.json')+'\n')
        write(self.out/'states.json',self.snapshots)
        write(self.out/'cases.json',self.rows)
        self.summary=dict(native_search_calls=8,additional_model_requests=0,groups=self.groups)
        write(self.out/'summary.json',self.summary)
        self.design=((2,),(2,),checker.STATES)
        # Each negative fixture passes intact before a deliberately forged mutation.
        self.assertEqual(self.verify()['status'],'PASS')

    def project(self,point):
        return dict(id=point.id,memory=point.payload['data'],metadata=None,
            **{k:point.payload[k] for k in checker.CORE})

    def make_store(self,folder,points):
        database=folder/'qdrant/collection/study_memories/storage.sqlite'
        database.parent.mkdir(parents=True)
        connection=sqlite3.connect(database)
        try:
            connection.execute('CREATE TABLE points(id TEXT PRIMARY KEY,point BLOB)')
            for point in points:
                connection.execute('INSERT INTO points VALUES(?,?)',
                    (base64.b64encode(pickle.dumps(point.id,protocol=4)).decode(),pickle.dumps(point)))
            connection.commit()
        finally:
            connection.close()
        connection=sqlite3.connect(folder/'history.sqlite')
        try:
            connection.execute('CREATE TABLE history(id TEXT PRIMARY KEY,memory_id TEXT,old_memory TEXT,new_memory TEXT,event TEXT,created_at TEXT,updated_at TEXT,is_deleted INTEGER)')
            for i,point in enumerate(points):
                connection.execute('INSERT INTO history VALUES(?,?,?,?,?,?,?,?)',
                    (f'h{i}',point.id,None,point.payload['data'],'ADD',point.payload['created_at'],None,0))
            connection.commit()
        finally:
            connection.close()

    def verify(self):
        return checker.audit(self.here,self.out,self.design)

    def test_rejects_forged_returned_literal_and_diversity_metric(self):
        with self.subTest('returned literal not in its physical point'):
            rows=copy.deepcopy(self.rows)
            rows[0]['results'][0]['memory']='A forged fact absent from the stored point.'
            write(self.out/'cases.json',rows)
            with self.assertRaisesRegex(checker.VerificationError,'Returned literal differs'):
                self.verify()
        with self.subTest('literal diversity metric forged despite honest returned records'):
            rows=copy.deepcopy(self.rows)
            rows[0]['distinct_literal_facts']=1
            write(self.out/'cases.json',rows)
            with self.assertRaisesRegex(checker.VerificationError,'distinct_literal_facts metric mismatch'):
                self.verify()

    def test_rejects_favorable_query_omission_even_with_rewritten_summary(self):
        rows=copy.deepcopy(self.rows[:-1])
        write(self.out/'cases.json',rows)
        summary=copy.deepcopy(self.summary)
        summary['native_search_calls']=7
        summary['groups'][-1]['query_count']=1
        write(self.out/'summary.json',summary)
        with self.assertRaisesRegex(checker.VerificationError,'Search coverage mismatch'):
            self.verify()

    def test_rejects_mutated_frozen_source_database(self):
        database=checker.source_folder(self.here,2,'baseline')/'history.sqlite'
        connection=sqlite3.connect(database)
        try:
            connection.execute("UPDATE history SET new_memory='Changed after freeze' WHERE id='h0'")
            connection.commit()
        finally:
            connection.close()
        with self.assertRaisesRegex(checker.VerificationError,'Frozen input changed'):
            self.verify()


if __name__=='__main__':
    unittest.main()
