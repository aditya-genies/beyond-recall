"""Build whitelisted paper and reproducibility packages from this study only."""
from pathlib import Path
import hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'release'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 qa=json.loads((ROOT/'checks/pdf_visual_qa.json').read_text())
 reviewed=json.loads((ROOT/'checks/final_manuscript_review.json').read_text())
 assert reviewed['status']=='PASS_FOR_BOUNDED_WORKING_CLAIMS'
 assert not reviewed['remaining_material_corrections']
 assert qa['accepted_for_promotion']
 assert qa['artifact']['pdf_sha256']==sha(ROOT/'manuscript/main.pdf')
 assert qa['artifact']['source_sha256']==sha(ROOT/'manuscript/main.tex')
 assert reviewed['manuscript_sha256']==sha(ROOT/'manuscript/main.tex')
 assert reviewed['plan_binding_sha256']==sha(ROOT/'manuscript/plan_binding.tex')
 assert qa['artifact']['plan_binding_source_sha256']==sha(ROOT/'manuscript/plan_binding.tex')
 payload=OUT/'repository-payload'
 if payload.exists():shutil.rmtree(payload)
 payload.mkdir(parents=True,exist_ok=True)
 files=[]
 for name in ['study.py','test_study.py','run_one.py','compare_results.py','build_release.py','README.md','README.txt','DATA_DICTIONARY.md','case_catalog.csv','requirements-figures.txt','PROVENANCE.json','refs.bib','.gitignore','CITATION.cff']:
  files.append(ROOT/name)
 for folder in ['results','reproduction','.github','figures','manuscript','extensions']:
  for p in (ROOT/folder).rglob('*'):
   if any(part.startswith('my-') or part.startswith('.venv') for part in p.relative_to(ROOT).parts):continue
   if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.aux','.bbl','.blg','.log','.out','.xdv','.toc'}:files.append(p)
 for p in (ROOT/'checks').rglob('*'):
  if not p.is_file() or '__pycache__' in p.parts or 'initial' in p.name:continue
  if p.suffix=='.py' and p.name not in {'__init__.py','check_results.py','audit_protocol.py','derive_factors.py','public_release_audit.py'}:continue
  if p.suffix in {'.py','.json','.txt','.log','.csv'}:files.append(p)
 for name in ['selected_primary_manifest.json','selected_manuscript_sources.json','academic_claim_map.json']:
  files.append(ROOT/'literature'/name)
 for name in ['campaign.log','reproduction.log']:files.append(ROOT/name)
 for name in ['response.txt','journal_readiness.txt','final_scientific_review.json','final_scientific_review.txt','final_evidence_reconciliation.json','audit_current_evidence.py','primary_verification.json','protocol_audit.json']:
  files.append(ROOT/'revisions/review1'/name)
 for name in ['citation_audit.json','citation_audit.txt','scope_and_workshop_note.txt','additions.bib','additions_claim_map.json']:
  files.append(ROOT/'revisions/review1/references'/name)
 for name in ['additions_verification.json','doi_resolution.json','fresh_fetch_manifest.json','transport_notes.json','li2026where.datacite.json','marla2026permission.datacite.json','sun2026agentic.datacite.json','check_doi_resolution.py','fetch_flagged_sources.py','write_citation_audit.py','positional_identity/manifest.json']:
  files.append(ROOT/'revisions/review1/references'/name)
 files.append(ROOT/'revisions/review1/journal_sources/manifest.json')
 for name in ['checks/figure_revision/fig_factorial_oracles_before.png','checks/figure_revision/fig_factorial_oracles_pdf_render.png','extensions/conflict_contracts/audit_tests.log','extensions/conflict_contracts/audit_verification.log','extensions/langgraph_reference/campaign.log','extensions/langgraph_reference/dependency_install.log','extensions/langgraph_reference/tests.log','extensions/langgraph_reference/tests_initial.log','extensions/langgraph_reference/verification.log']:
  files.append(ROOT/name)
 assert len(set(files))==len(files)
 for p in files:
  rel=p.relative_to(ROOT);q=payload/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 forbidden=['development_pilots','development_single_case','literature/private','literature/public/primary','worklog/pdf_qa']
 assert not any(any(p.relative_to(ROOT).as_posix().startswith(f) for f in forbidden) for p in files)
 manifest={'study':'Independent synthetic mechanism study','paper_source_sha256':sha(ROOT/'manuscript/main.tex'),'paper_pdf_sha256':sha(ROOT/'manuscript/main.pdf'),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)],'excluded':'Development pilots, installed environments, Git objects, writing-only helpers, unused background documentation, third-party full texts and private publication-review notes'}
 (payload/'ARTIFACT_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
 repro=OUT/'beyond-recall-independent-reproducibility.zip'
 with zipfile.ZipFile(repro,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(payload.rglob('*')):
   if p.is_file():z.write(p,'beyond-recall/'+p.relative_to(payload).as_posix())
 paper=OUT/'beyond-recall-independent-paper.zip'
 with zipfile.ZipFile(paper,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted((ROOT/'manuscript').rglob('*')):
   if p.is_file() and p.suffix in {'.tex','.bib','.pdf','.png','.svg'}:z.write(p,'beyond-recall-paper/'+p.relative_to(ROOT/'manuscript').as_posix())
  z.writestr('beyond-recall-paper/README.txt','Aditya Mantri: Beyond Recall, working research manuscript.\nCompile main.tex (including plan_binding.tex) with Tectonic or standard LaTeX/BibTeX.\nPublic companion repository: https://github.com/aditya-genies/beyond-recall\nPublic availability is not peer-reviewed acceptance.\n')
 for p in [repro,paper]:
  with zipfile.ZipFile(p) as z:assert z.testzip() is None
 (OUT/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in [paper,repro]))
 print(json.dumps({'files':len(files),'paper':{'path':paper.relative_to(ROOT).as_posix(),'bytes':paper.stat().st_size,'sha256':sha(paper)},'reproducibility':{'path':repro.relative_to(ROOT).as_posix(),'bytes':repro.stat().st_size,'sha256':sha(repro)}},indent=2))
if __name__=='__main__':main()
