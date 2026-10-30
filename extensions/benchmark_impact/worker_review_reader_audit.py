"""Read-only frozen reader/citation/alias and official-LoCoMo metric audit.

No requests, generation, model loading, native retrieval or artifact mutation.
Only the requested audit report is written. Raw conversation/answer text is not
copied into metric discrepancy reports; paths and content digests identify it.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import contextlib
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path

try:
 from . import corrected_official_metric as corrected
 from .test_corrected_official_metric import official_functions,ASCII_PAIRS,UNICODE_PAIRS
except ImportError:
 import corrected_official_metric as corrected
 from test_corrected_official_metric import official_functions,ASCII_PAIRS,UNICODE_PAIRS

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

class AuditError(ValueError):pass

def need(condition,message):
 if not condition:raise AuditError(message)
def load(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def text_sha(text):return hashlib.sha256(text.encode()).hexdigest()
def rooted(base,relative):
 path=(base/relative).resolve();need(path.is_relative_to(base.resolve()),'Frozen path escapes root');return path

def parse_answer(value):
 need(isinstance(value,dict) and set(value)=={'answer','cited_event_ids','abstain'},'Answer schema fields differ')
 need(type(value['answer']) is str and type(value['abstain']) is bool and type(value['cited_event_ids']) is list,'Answer schema types differ')
 need(all(type(citation) is str for citation in value['cited_event_ids']),'Answer citation type differs')
 return value

def reader_constants(path):
 names={'SCHEMA','INSTRUCTION'};result={}
 for node in ast.parse(path.read_text()).body:
  if isinstance(node,ast.Assign):
   for target in node.targets:
    if isinstance(target,ast.Name) and target.id in names:result[target.id]=ast.literal_eval(node.value)
 need(set(result)==names,'Frozen reader literal constants missing');return result

def official_score(functions,prediction,reference,category):
 with contextlib.redirect_stdout(io.StringIO()):return float(functions['eval_question_answering']([dict(category=int(category),answer=reference,prediction=prediction,evidence=[])])[0][0])

def audit(out,scorer):
 out=Path(out).resolve();protocol=load(out/'protocol.json');reader=load(out/'reader_protocol.json');grading=load(out/'grading_protocol.json')
 need(sha(out/'protocol.json')==(out/'protocol.sha256').read_text().strip(),'Pilot protocol digest differs')
 need(sha(out/'reader_protocol.json')==(out/'reader_protocol.sha256').read_text().strip(),'Reader protocol digest differs')
 need(sha(out/'grading_protocol.json')==(out/'grading_protocol.sha256').read_text().strip(),'Grading protocol digest differs')
 for relative,digest in protocol['source_hashes'].items():need(sha(rooted(ROOT,relative))==digest,'Frozen source differs: '+relative)
 for relative,digest in protocol['protected_release'].items():need(sha(rooted(ROOT,relative))==digest,'Protected published artifact differs: '+relative)
 need(sha(HERE/'reader.py')==reader['reader_source_sha256'],'Frozen reader source differs')
 need(sha(HERE/'grade.py')==grading['source_sha256'],'Frozen grade source differs')
 need(sha(out/'grading_calibration.json')==grading['calibration_sha256'],'Frozen calibration expected labels differ')
 need(sha(out/'grading_protocol.json')==reader['grading_protocol_sha256'],'Reader/grader protocol binding differs')
 need(sha(out/'contexts.json')==reader['contexts_sha256'] and sha(out/'reader_aliases.json')==reader['aliases_sha256'],'Contexts/aliases changed')
 need(sha(out/'evaluator_questions.json')==protocol['evaluator_sha256'],'Question evaluator input changed')
 constants=reader_constants(HERE/'reader.py');contexts=load(out/'contexts.json');aliases=load(out/'reader_aliases.json');questions={q['key']:q for q in load(out/'evaluator_questions.json')}
 expected_aliases=[];unique={};cases=set()
 for row in contexts:
  need(row['case'] not in cases,'Repeated condition case');cases.add(row['case']);q=questions[row['question_key']]
  need(row['question']==q['question'] and row['question_date']==q['question_date'],'Wrong query text/date in reader condition')
  for record in row['context']:need(set(record)=={'event_id','source_id','date','text'} and all(isinstance(v,str) for v in record.values()),'Unexpected evaluator/unknown field in reader evidence')
  need(len(json.dumps(row['context'],ensure_ascii=True,separators=(',',':')).encode())<=12000,'Serialized reader evidence exceeds frozen budget')
  text=constants['INSTRUCTION']+json.dumps({'question':row['question'],'question_date':row['question_date'],'evidence':row['context']},ensure_ascii=True,separators=(',',':'))
  h=text_sha(text);entry={'prompt':text,'allowed_events':sorted({e['event_id'] for e in row['context']})}
  if h in unique:need(unique[h]==entry,'Prompt digest alias has different evidence/allowlist')
  unique[h]=entry;expected_aliases.append(dict(case=row['case'],prompt_sha256=h,question_key=row['question_key'],backend=row['backend'],arm=row['arm']))
 need(aliases==expected_aliases and len(aliases)==reader['condition_cells'],'Aliases do not exactly cover frozen context conditions')
 need(set(unique)==set(reader['input_hashes']) and len(unique)==reader['unique_prompt_count'],'Unique prompt/input coverage differs')
 tracked={out/'protocol.json':sha(out/'protocol.json'),out/'reader_protocol.json':sha(out/'reader_protocol.json'),out/'grading_protocol.json':sha(out/'grading_protocol.json'),out/'contexts.json':sha(out/'contexts.json'),out/'reader_aliases.json':sha(out/'reader_aliases.json'),out/'evaluator_questions.json':sha(out/'evaluator_questions.json'),out/'grading_calibration.json':sha(out/'grading_calibration.json')}
 for h,entry in unique.items():
  folder=out/'reader_inputs'/h;need(sha(folder/'input.json')==reader['input_hashes'][h],'Frozen reader input hash differs')
  need(load(folder/'input.json')==entry,'Frozen input differs from independently constructed question/date/evidence prompt')
  need((folder/'prompt.txt').read_bytes()==entry['prompt'].encode(),'Frozen input prompt bytes differ')
  need(load(folder/'schema.json')==constants['SCHEMA'],'Frozen reader answer schema differs')
  for name in ('input.json','prompt.txt','schema.json'):tracked[folder/name]=sha(folder/name)
 expected={(model,h,f'r{repeat}') for model,repeats in [('sol',2),('qwen',1)] for h in unique for repeat in range(repeats)}
 need(len(expected)==447,'Unexpected declared reader call count')
 paths=list((out/'reader_results').glob('*/*/r*/status.json'));seen=set();responses={};status_counts=Counter();invalid_counts=Counter();invalid_records=[];fence_count=0;in_progress=[]
 for path in paths:
  model,h,repeat=path.relative_to(out/'reader_results').parts[:3];key=(model,h,repeat)
  need(key in expected and key not in seen,'Unknown/repeated reader status');seen.add(key)
  try:status=load(path)
  except json.JSONDecodeError:in_progress.append('/'.join(key));continue
  folder=path.parent;status_counts[model+'/'+status['status']]+=1
  need((folder/'prompt.txt').read_bytes()==unique[h]['prompt'].encode(),'Submitted archived prompt bytes differ from frozen input')
  need(status['prompt_sha256']==h==sha(folder/'prompt.txt'),'Reader prompt digest mismatch')
  if model=='sol':
   need(status['requested_model']==reader['profiles']['sol']['requested_model'],'Requested Sol alias differs')
   need(status['tool_event_types']==[] and all(kind in ('agent_message','reasoning') for kind in status['item_types']),'Unexpected retained Sol tool event type')
   need(load(folder/'schema.json')==constants['SCHEMA'],'Submitted Sol output schema differs')
   tracked[folder/'schema.json']=sha(folder/'schema.json')
   if status['status']=='PASS':need(status['returncode']==0 and len(status['usage'])==1,'Sol success lacks completed request usage/returncode')
  else:
   need(status['model']==reader['profiles']['qwen']['model'] and status['revision']==reader['profiles']['qwen']['revision'],'Qwen model/revision differs')
   need(type(status['input_tokens']) is int and type(status['output_tokens']) is int and status['input_tokens']>0 and status['output_tokens']>=0,'Invalid Qwen token metadata')
  tracked[path]=sha(path);tracked[folder/'prompt.txt']=sha(folder/'prompt.txt')
  if status['status']!='PASS':continue
  need(sha(folder/'response.txt')==status['response_sha256'],'Raw final response digest differs')
  raw=(folder/'response.txt').read_text();cleaned=raw
  if model=='qwen':
   cleaned=raw.strip()
   if cleaned.startswith('```'):
    lines=cleaned.splitlines()
    if lines[-1].strip()=='```':cleaned='\n'.join(lines[1:-1]);fence_count+=1
  value=parse_answer(json.loads(cleaned));recorded=parse_answer(load(folder/'parsed.json'))
  need(value==recorded,'Raw final text does not match recorded parsed result under frozen parsing rule')
  invalid=[citation for citation in value['cited_event_ids'] if citation not in set(unique[h]['allowed_events'])]
  need(invalid==status['invalid_citations'],'Invalid citation accounting differs from frozen context allowlist')
  invalid_counts[model+'/responses_with_invalid_citations']+=bool(invalid);invalid_counts[model+'/invalid_citation_occurrences']+=len(invalid)
  if invalid:invalid_records.append(dict(reader=model,prompt_sha256=h,repeat=repeat,response_path=str((folder/'parsed.json').relative_to(out)),invalid_citations=invalid))
  responses[key]=value
  for name in ('response.txt','parsed.json'):tracked[folder/name]=sha(folder/name)
 functions=official_functions(scorer)
 module_spec=importlib.util.spec_from_file_location('frozen_grade_metric',HERE/'grade.py');frozen=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(frozen)
 edges=[]
 for category in range(1,6):
  for prediction,reference in UNICODE_PAIRS:
   published=official_score(functions,prediction,reference,category);old=frozen.locomo_proxy(prediction,reference,category);new=corrected.locomo_proxy(prediction,reference,category)
   need(abs(new-published)<=1e-14,'Corrected Unicode proxy disagrees with pinned official scorer')
   if abs(old-published)>1e-12:edges.append(dict(category=category,prediction=prediction,reference=reference,frozen_proxy=old,corrected_proxy=new,official_proxy=published))
 comparisons=[];discrepancies=[];rounding=0;max_difference=0.;used_response_paths=set()
 for alias in aliases:
  q=questions[alias['question_key']]
  if q['dataset']!='locomo':continue
  h=alias['prompt_sha256']
  for model,repeats in [('sol',2),('qwen',1)]:
   for repeat in range(repeats):
    key=(model,h,f'r{repeat}')
    if key not in responses:continue
    prediction=responses[key]['answer'];published=official_score(functions,prediction,q['reference'],q['category']);old=frozen.locomo_proxy(prediction,q['reference'],q['category']);new=corrected.locomo_proxy(prediction,q['reference'],q['category'])
    need(abs(new-published)<=1e-14,'Corrected measured proxy differs from official scorer')
    difference=abs(old-published);max_difference=max(max_difference,difference);rounding+=old!=published and difference<=1e-12
    response_path=str(Path('reader_results')/model/h/f'r{repeat}'/'parsed.json');used_response_paths.add(response_path)
    row=dict(case=alias['case'],question_key=alias['question_key'],backend=alias['backend'],arm=alias['arm'],reader=model,repeat=repeat,response_path=response_path,category=q['category'],prediction_sha256=text_sha(prediction),reference_sha256=text_sha(q['reference']),frozen_proxy=old,corrected_official_proxy=new,pinned_official_proxy=published,absolute_frozen_difference=difference)
    comparisons.append(row)
    if difference>1e-12:discrepancies.append(row)
 missing=expected-seen;ready=len(seen)==len(expected) and not in_progress
 for path,digest in tracked.items():need(sha(path)==digest,'Reader artifact changed during read-only audit: '+str(path.relative_to(out)))
 manifest={str(path.relative_to(out)):digest for path,digest in tracked.items()}
 return dict(status='PASS' if ready else 'NOT_READY',phase='Read-only same-study reader and official-metric audit; no requests/generation/remeasurement',reader_protocol_sha256=sha(out/'reader_protocol.json'),pilot_protocol_sha256=sha(out/'protocol.json'),
  declared_unique_prompts=len(unique),declared_condition_aliases=len(aliases),declared_reader_calls=len(expected),present_status_files=len(seen),status_counts=dict(status_counts),missing_statuses=len(missing),in_progress_statuses=in_progress,successfully_parsed_answers=len(responses),
  all_archived_prompts_match_frozen_bytes=True,raw_to_parsed_answers_match=True,retained_sol_tool_summaries_empty=True,qwen_outer_fence_removals=fence_count,invalid_citation_counts=dict(invalid_counts),invalid_citation_records=invalid_records,
  auditor_sha256=sha(__file__),checked_artifact_hashes=manifest,checked_artifact_manifest_sha256=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
  official_scorer=corrected.provenance(),official_scorer_cached_sha256=sha(scorer),corrected_metric_source_sha256=sha(HERE/'corrected_official_metric.py'),
  authored_unicode_edge_comparisons=len(UNICODE_PAIRS)*5,authored_unicode_edge_discrepancies=edges,
  measured_locomo_condition_scores=len(comparisons),measured_locomo_unique_physical_response_files=len(used_response_paths),measured_frozen_proxy_discrepancies=discrepancies,measured_frozen_proxy_rounding_only_differences=rounding,max_measured_frozen_absolute_difference=max_difference,measured_metric_comparisons=comparisons,
  metric_comparison_tolerance=1e-12,model_calls_by_this_audit=0,reader_or_native_remeasurement=False,
  disclosure='Corrected metric is a versioned development-analysis correction, not relabelled generation. Frozen grade.py/outputs remain immutable; known Unicode non-equivalence is retained even if measured scores agree.',
  coverage_limits=['Sol tool absence checked against retained status summaries/item types; complete raw CLI stdout/tool event stream was not archived by frozen reader.py.','Task prompt bytes and raw final text are verified; unexposed provider/system instructions or immutable Sol serving snapshot cannot be reconstructed.','Shared-prompt aliases reuse physical responses; condition score count is not independent model observations.','This audit does not validate semantic task labels or repair the failed auxiliary calibration.'])

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--scorer',type=Path,default=Path('/tmp/beyond-recall-benchmark-feasibility-20261029/locomo_scorer.py'));parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
 try:report=audit(args.out,args.scorer)
 except Exception as error:report=dict(status='FAIL',error_type=type(error).__name__,error=str(error),model_calls_by_this_audit=0)
 args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps({key:value for key,value in report.items() if key not in ('measured_metric_comparisons','authored_unicode_edge_discrepancies','checked_artifact_hashes')},indent=2))
 if report['status']=='FAIL':raise SystemExit(1)
