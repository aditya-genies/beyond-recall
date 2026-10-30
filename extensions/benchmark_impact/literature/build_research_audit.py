"""Build a skeptical primary-source landscape without changing any manuscript."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,re

HERE=Path(__file__).resolve().parent
CACHE=Path('/tmp/beyond-recall-benchmark-impact-literature-20261029')
NOW=datetime.now(timezone.utc).isoformat()

def load(path):return json.loads(Path(path).read_text())
def save(name,value):(HERE/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
manifest={}
for name in ('fetch_manifest.json','close_prior_art_fetch_manifest.json','implementation_fetch_manifest.json',
             'event_identity_fetch_manifest.json','artifact_availability_manifest.json'):
    for rec in load(HERE/name)['records']:
        manifest[rec['key']]=rec
def ev(*keys):
    return [{k:r[k] for k in ('key','url','sha256','http_status','status','retrieved_utc') if k in r}
        for r in (manifest[x] for x in keys)]

SPECS={
 'ke2024bridging':dict(priority='necessary background',locations=['§§3–4','§5.3'],
  summary='BGM jointly learns passage selection/order and permits repeating passage IDs. It challenges blanket redundancy assumptions, but the inspected text does not isolate repetition as the cause of its gains.',
  no_claim='Do not say this paper alone proves ordinary delivery retries improve QA.',
  overlap=dict(controlled_reader_context=True,native_delivery_fault=False,event_lifetime_controls=False)),
 'jain2026cuer':dict(priority='mandatory closest baseline',locations=['§4.6','§§5.4–5.9','§7','Appendices B–E'],
  summary='Single-shot BM25 top-five QA perturbs one selected item with REMOVE/REPLACE/DUPLICATE. Target selection uses model references and gold-title priority. Deterministic soft matching, title-overlap grounding and self-reported IDs/confidence are proxies; no independent sentence-level judge is supplied.',
  no_claim='Do not claim first duplicate-evidence QA evaluation or treat reported chunk use as verified reasoning.',
  overlap=dict(controlled_reader_context=True,native_delivery_fault=False,event_lifetime_controls=False)),
 'ross2026redundancy':dict(priority='mandatory controlled comparison',locations=['§§3.1–3.4','§4.1'],
  summary='FictionalQA compares exact copies, paraphrases and diverse-genre evidence while checking answer support and closed-book performance. Main duplicate conditions mostly show little correctness benefit; qualified exceptions prevent a universal no-effect claim. The experiment constructs contexts rather than executing delivery recovery.',
  no_claim='Do not generalize its nonsignificant differences as equivalence, or call genres independent real corroboration.',
  overlap=dict(controlled_reader_context=True,native_delivery_fault=False,event_lifetime_controls=False)),
 'brouillette2026balance':dict(priority='mandatory redundancy-regime comparator',locations=['§4.3','§§5–6','§8'],
  summary='Fixed-pool near-copy injection and overlapping chunks link redundancy, evidence coverage and QA. Diversification can help or hurt by regime. Gold-derived evidence requirement is explicitly an oracle. RNG-Score does not suppress exactly coincident copies; that boundary is assigned to hash deduplication.',
  no_claim='Do not claim a new redundancy/evidence-requirement tradeoff or score RNG-Score as a failed exact-copy filter.',
  overlap=dict(controlled_reader_context=True,native_delivery_fault=False,event_lifetime_controls=False)),
 'cho2026rare':dict(priority='necessary evidence-oracle background',locations=['Framework and RedQA construction','Evaluation methodology'],
  summary='RARE tracks atomic-fact redundancy across highly similar corpora. Its key evaluation warning is that a retrieved alternative can supply sufficient evidence even if its document identity differs from annotated support. Raw ID diversity alone is therefore an inadequate correctness oracle.',
  no_claim='Do not assume the absence of an annotated evidence ID proves that useful support was lost.',
  overlap=dict(controlled_reader_context=True,native_delivery_fault=False,event_lifetime_controls=False)),
 'schuster2026whose':dict(priority='relevant source/repetition interaction',locations=['Source-conflict experiments','Repetition conditions','Limitations'],
  summary='Synthetic inter-context source conflicts show that repetition can reverse source preferences. This concerns reader input and source credibility, rather than ordinary memory transport faults. It motivates preserving root provenance and separating repeated presentation from genuinely independent observation.',
  no_claim='Do not infer ordinary retries are attacks, or treat repeated source labels as independent corroboration.',
  overlap=dict(controlled_reader_context=True,native_delivery_fault=False,event_lifetime_controls=False)),
 'chauhan2026sleep':dict(priority='context only; sparse reproducibility',locations=['§3','§4'],
  summary='The three-page RSPM text discusses pruning/decay and reports LoCoMo effects, including negative cases. Its SWE-bench component is explicitly a simulation. Retry loops mean repeated agent strategies, not transport redelivery. Model/judge/protocol details and an author artifact are not supplied sufficiently for reproduction here.',
  no_claim='Do not describe headline issue counts as native agent executions or infer acceptance from its older conference-template footer.',
  overlap=dict(controlled_reader_context=False,native_delivery_fault=False,event_lifetime_controls=False)),
 'wu2026longmemevalv2':dict(priority='benchmark/protocol reference; resource feasibility separate',locations=['§3.3','Appendix A.5','Appendix B','Appendix E.1'],
  summary='V2 evaluates memory context gathering over pre-collected browser trajectories with a fixed reader, not live task learning. Structured questions have deterministic evaluators; gotchas/abstention use a GPT-5.2 judge. Generic UNKNOWN is incorrect, including when a flawed premise must be explained. Its oracle and no-history pilots are distinct from full haystack evaluation.',
  no_claim='Do not call an oracle/text-only adaptation the complete multimodal benchmark or end-to-end agent success.',
  overlap=dict(controlled_reader_context=True,native_delivery_fault=False,event_lifetime_controls=False)),
 'wu2024longmemeval':dict(priority='actual workload and category-grader contract',locations=['Official pinned src/evaluation/evaluate_qa.py','Official retrieval metrics'],
  summary='Pinned grading has category-specific allowances: temporal counts tolerate off-by-one errors; update answers may include old information if the required new answer is present; preference responses need not cover every rubric point. Official accuracy and a new conflicting-current-assertion outcome must be separate.',
  no_claim='Do not silently tighten the official rubric or label a Sol adaptation official GPT-4o scoring.',
  overlap=dict(controlled_reader_context=True,native_delivery_fault=False,event_lifetime_controls=False)),
 'maharana2024evaluating':dict(priority='actual workload and scorer contract',locations=['Official pinned task_eval/evaluation.py','Dataset evidence annotations'],
  summary='The supplied LoCoMo scorer uses category-specific stemmed token F1, a multi-answer variant and special abstention-string handling. Evidence annotations and answer scoring are distinct. Its conversation clusters, rather than individual question repetitions, govern claims about independent sampling.',
  no_claim='Do not call all supplied scores exact accuracy or assume more reported record IDs mean more independent evidence.',
  overlap=dict(controlled_reader_context=True,native_delivery_fault=False,event_lifetime_controls=False)),
}

verified=load(HERE/'verified_sources.json')['papers']
records=[]
metadata_conflicts=[]
normal=lambda s:re.sub('[^a-z0-9]','',s.lower())
for r in verified:
    r=dict(r);r.update(SPECS[r['key']])
    prefix=r['source_prefix']
    pdf=normal((CACHE/(prefix+'_pdf.txt')).read_text()[:10000])
    positions=[]
    for author in r['authors']:
        family,given=author.split(',',1)
        positions.append(pdf.find(normal(given+' '+family)))
    r['pdf_full_author_names_found']=all(p>=0 for p in positions)
    r['pdf_author_order_matches_primary_metadata']=positions==sorted(positions)
    if not r['pdf_author_order_matches_primary_metadata']:
        conflict=dict(key=r['key'],type='author_order',
            arxiv_landing_and_datacite_order=r['authors'],
            pdf_and_html_order=['Chauhan, Kargi','Revankar, Pratibha','Nur, Sadiba Nusrat','Montgomery, Kyle','Wang, Chenguang'],
            handling='Preserve both. BibTeX follows arXiv/DataCite with an explicit audit comment; inspect before main integration. No fabrication inference.')
        r['metadata_conflict']=conflict;metadata_conflicts.append(conflict)
    suffixes=['_abs','_html','_pdf','_datacite'] if '_acl-long_' not in prefix else ['_landing','_pdf','_bib','_crossref']
    r['evidence']=ev(*(prefix+s for s in suffixes))
    if r['key']=='wu2024longmemeval':r['implementation_evidence']=ev('lme_evaluate_qa','lme_retrieval_metrics')
    if r['key']=='maharana2024evaluating':r['implementation_evidence']=ev('locomo_evaluate_qa','locomo_evaluation')
    records.append(r)

capture=load(CACHE/'agentmemory_head.json')
balance=load(CACHE/'balance_repo.json')
balance_commit=load(CACHE/'balance_commits.json')[0]
pi=load(CACHE/'pi_head.json')[0]
pi_pinned=load(HERE/'pi_pinned_body_check.json')
code_contracts=[
 dict(id='agentmemory_capture',project='rohitg00/agentmemory',commit=capture['sha'],
    version=load(CACHE/'agentmemory__package.json.json')['version'],
    license_from_pinned_file='Apache-2.0',
    scope='Static primary-source audit; no implementation or QA experiment executed by this agent.',
    verified_contract='Capture uses project/session/event identity, retains completed/deleted-event records for a configured window, and distinguishes separate host events with identical content.',
    client_hook_fallback='deriveEventId uses the host ID when present; without host ID/time, its fallback is content-derived.',
    server_missing_id='capture allocates a fresh server ID when no valid client event ID is supplied; this differs from hook-side identity derivation.',
    limits=['Documentation includes a durability grace window and retention/capacity bounds; no unlimited replay guarantee.',
      'This is raw observation capture, not evidence that every knowledge-consolidation path shares the same semantics.',
      'Explicit reaffirmation/date-refresh wording was not located in inspected project sources; do not attribute separate pi-memory-evolution wording here.'],
    evidence=ev('agentmemory_pinned__README.md','agentmemory__src__capture__event-id.ts',
       'agentmemory_pinned__src__functions__capture.ts','agentmemory__src__capture__event-record.ts',
       'agentmemory__test__capture-event-id.test.ts','agentmemory__LICENSE')),
 dict(id='plur_checklist',scope='Public proposed engineering procedure, AI-agent authored; not a benchmark result or peer-reviewed study.',
    verified_contract='Separates retry of one logical save, a fresh operation with identical text, paraphrase and correction, inspecting stored identities and subsequent recall.',
    no_claim='Do not present its proposed procedure as measured product performance.',evidence=ev('plur_checklist')),
 dict(id='rfc9110_identity',scope='HTTP semantics standard, not a specification that makes every memory API idempotent.',
    verified_contract='Section 9.2.2 defines idempotency through intended server effect; identical responses and universal automatic retries are not required.',
    evidence=ev('rfc9110')),
 dict(id='pi_reaffirmation',scope='Separate public project; illustrative contract only, not an evaluated baseline.',
    verified_contract='Core-quality documentation distinguishes incorporated reaffirmation/fresh progress from aliases/repeated summaries and discusses root-observation dependence.',
    commit=pi_pinned['commit'],body_sha256=pi_pinned['record'].get('sha256'),
    pinned_body_matches_fetched_main=pi_pinned['same_body_as_main'],
    caution='The pinned documentation contract was inspected; runtime conformance and benchmark outcomes were not executed.',
    evidence=[{k:v for k,v in pi_pinned['record'].items() if k in ('key','url','sha256','http_status','status','retrieved_utc')}]),
]
artifacts=[
 dict(key='jain2026cuer',availability='No author code/artifact URL located in inspected PDF/HTML. Paper recipe can be independently implemented, clearly labelled.',runnable_author_code_obtained=False),
 dict(key='ross2026redundancy',url='https://anonymous.4open.science/r/rag-redunancy-C8BC',
    availability='Author-linked landing page returned 200; source version/license/runtime not independently established.',runnable_author_code_obtained=False,evidence=ev('ross_artifact_landing')),
 dict(key='brouillette2026balance',url=balance['html_url'],commit=balance_commit['sha'],
    api_license=balance.get('license'),availability='Public repository and commit metadata fetched; not installed or executed.',
    evidence=ev('balance_repo','balance_commits')),
 dict(key='chauhan2026sleep',availability='No author artifact URL located in three-page primary body/landing.',runnable_author_code_obtained=False),
]
save('source_claim_map.json',dict(prepared_utc=NOW,source_cutoff='2026-10-29 inclusive',
    scope='Targeted full-text primary-source audit, not exhaustive academic coverage. Summaries are original auditor prose, not abstracts.',
    model_calls_by_literature_agent=0,no_company_access=True,manuscript_edited=False,
    full_texts_and_code_external_only=True,papers=records,implementation_contracts=code_contracts,
    artifact_availability=artifacts,metadata_conflicts=metadata_conflicts))

# Focused answers to the mandatory closest-baseline questions. Keep source prose short.
save('cue_r_protocol_audit.json',dict(source_key='jain2026cuer',
    mandatory_baseline=True,intervention_origin='Post-retrieval reader prompt; top-five BM25 plus one copied target by default.',
    native_memory_ingestion_executed=False,post_effect_worker_failure_executed=False,
    event_identity_new_occurrence_expiry_revocation_controls=False,
    duplication_position_controls=['front','after-original','end'],
    independent_sentence_level_support_judging=False,
    grading=dict(correctness='Normalized/yes-no/numeric/soft-F1 match',soft_f1_threshold=0.8,
        grounding='Gold-title overlap of model-reported used chunk IDs',confidence='Self-reported instance-level absolute error proxy'),
    models=['qwen3:8b through local Ollama','gpt-5.2 API'],reported_temperature=0,
    main_sample_sizes=dict(hotpot_primary=200,hotpot_cross_model=100,wiki2=100),
    target_selection_uses_gold=True,
    absence_claim_scope='Not part of the inspected single-shot protocol; no assertion about all author work.',
    originality_boundary='Duplicating evidence and measuring answer/behavior sensitivity is prior art. Native delivery/recovery/event-provenance experiments would add a different intervention origin.',
    caution='Its own limitation section separates prompt sensitivity from strongest causal attribution; input length, position and distribution co-vary.'))

grading=[
 dict(source='LongMemEval pinned official scorer',contract='Category-dependent yes/no grading; keep official label and model configuration separately.',
    pitfalls=['Knowledge-update scoring can accept a correct updated value alongside old information.',
      'Historical explanation is not a contradictory-current assertion.',
      'Temporal count tolerance and preference-rubric partial coverage are explicit.',
      'An adapted Sol judge is neither the official gpt-4o endpoint nor independent human validation.'],
    evidence=ev('lme_evaluate_qa')),
 dict(source='LoCoMo pinned official scorer',contract='Category-specific stemmed token F1/multi-answer matching and special adversarial abstention handling.',
    pitfalls=['Preserve denominator/category and distinguish scores from exact accuracy.',
      'Token overlap can miss unsupported extra assertions; stricter outcomes must be separately defined.',
      'Gold evidence labels may not exhaust alternative support.'],evidence=ev('locomo_evaluation')),
 dict(source='LongMemEval-V2 primary protocol',contract='Fixed-reader context gathering; deterministic structured scoring, semantic judges for gotchas/abstention.',
    pitfalls=['UNKNOWN is not a substitute for diagnosing a flawed premise.',
      'Oracle and no-history pilots are not full-history results.',
      'The resource-heavy multimodal haystack is not automatically reproduced by text-only adaptation.']),
]
save('grading_contracts.json',dict(prepared_utc=NOW,records=grading,
    recommended_new_outcome='Evidence-supported correctness and explicit conflicting CURRENT assertions, separately reported from official scoring. Preserve legitimate past-state explanation and history-targeted questions.',
    adjudication='Freeze rubrics; blind arm identity/order; preserve raw grading outputs; obtain authorized independent adjudication for disputed/sampled cases. No reviewers have been invented or contacted.'))

hypotheses=[
 dict(id='H1_delivery_effect',claim_to_test='Identical logical source histories can yield different task outcomes under actual repeated delivery.',
    falsifier='Paired differences remain within a preregistered practical equivalence region, including clean repeated-reader variation.',
    required_controls=['No-context reader','Clean repeated reader','Captured extraction versus fresh extraction','Native raw-document versus inferred ingestion','Fixed logical source timestamps and provenance']),
 dict(id='H2_event_vs_content',claim_to_test='A documented event-identity control can suppress retries while preserving new same-content observations and updates.',
    falsifier='Strong native behavior already satisfies all declared cases, or the adapter rejects legitimate new events.',
    required_controls=['Same event ID redelivery','New event ID identical text','Correction','Reaffirmation','Expiry/regrant within declared identity lifetime']),
 dict(id='H3_support_not_ids',claim_to_test='Returned physical IDs, independent root evidence and answer-supported correctness can disagree.',
    falsifier='Canonical provenance/support and task labels agree under all tested regimes.',
    required_controls=['Collapse aliases to original event IDs','Grade all required evidence pieces','Permit alternative valid support','Treat self-reported citations as claims to verify']),
 dict(id='H4_regime_direction',claim_to_test='Repetition effects depend on evidence needs, context budget and presentation, and can be beneficial, harmful or negligible.',
    falsifier='A purported directional benefit disappears under held-out episodes or matched budget/position controls.',
    required_controls=['Matched token budget','Reported slot budget','Duplicate placement','Single- versus multi-evidence tasks','Strong exact/text and retrieval-time dedup baselines']),
]
save('falsifiable_questions.json',dict(prepared_utc=NOW,novelty_not_assumed=True,hypotheses=hypotheses))

# BibTeX is proposed only. Existing LongMemEval/LoCoMo entries should be reused.
bibs=[]
for r in records:
    if r['key'] in ('wu2024longmemeval','maharana2024evaluating'):continue
    if '_acl-long_' in r['source_prefix']:
        bib=(CACHE/(r['source_prefix']+'_bib.bib')).read_text()
        bib=re.sub(r'(@\w+\{)[^,]+',lambda m:m.group(1)+r['key'],bib,count=1)
        # Abstracts are not needed in a bibliography and are not redistributed.
        lines=bib.splitlines();lines=[line for line in lines if not line.lstrip().startswith('abstract =')]
        # ACL exports put the entire abstract on one line.
        bib='\n'.join(lines)
    else:
        comment='% Author-order conflict with PDF/HTML recorded in source_claim_map.json.\n' if r.get('metadata_conflict') else ''
        fields=dict(author=' and '.join(r['authors']),title='{'+r['title']+'}',year=str(r['year']),
            howpublished='arXiv preprint',archivePrefix='arXiv',eprint=r['source_prefix'].replace('_','.'),
            doi=r['doi'],url=r['url'],note='Version '+str(r['version'])+'; preprint')
        bib=comment+'@misc{'+r['key']+',\n'+'\n'.join('  '+k+' = {'+v+'},' for k,v in fields.items()).rstrip(',')+'\n}'
    bibs.append(bib)
(HERE/'new_sources.bib').write_text('% Proposed relevant additions; no manuscript bibliography changed.\n'
    '% LongMemEval and LoCoMo are verified in the map; reuse existing entries.\n\n'+'\n\n'.join(bibs)+'\n')

(HERE/'public_contract_sources.bib').write_text('''% Engineering contracts, separately classified from research papers.
@misc{plur2026duplicatechecklist,
  author = {{PLUR}},
  title = {Choosing an Agent Memory Tool: Test Duplicate Writes Before You Commit},
  year = {2026},
  url = {https://plur.ai/blog/agent-memory-tool-duplicate-write-checklist/},
  note = {October 15; authored by Data, an AI agent; proposed procedure, not a benchmark report; accessed 2026-10-29}
}

@misc{rohitg002026capture,
  author = {{rohitg00}},
  title = {agentmemory: Capture Delivery Contract},
  year = {2026},
  url = {https://github.com/rohitg00/agentmemory/blob/'''+capture['sha']+'''/README.md},
  note = {Version 0.9.31; commit '''+capture['sha']+'''; configured event-retention and durability scope; accessed 2026-10-29}
}

@techreport{fielding2022http,
  author = {Fielding, R. and Nottingham, M. and Reschke, J.},
  title = {{HTTP} Semantics},
  institution = {Internet Engineering Task Force},
  type = {RFC},
  number = {9110},
  year = {2022},
  month = jun,
  url = {https://www.rfc-editor.org/rfc/rfc9110.html},
  note = {Section 9.2.2; editors listed as on the primary header}
}
''')

assessment='''Skeptical contribution assessment — benchmark-impact study

The broad question “can duplicate or redundant evidence change QA?” is already studied. CUE-R is a mandatory protocol baseline, not an optional citation. Ross et al. and Finding the Right Balance provide direct controlled comparisons/regime analysis. The PLUR procedure already asks evaluators to distinguish same-operation retries, fresh identical saves and corrections. Event identity, deduplication and legitimate occurrence lifetimes are established engineering mechanisms. No first-discovery or new-idempotency claim is supportable here.

The potentially distinguishing experiment is an operational chain: ordinary repeated delivery or an actual post-effect/pre-ack worker cut, through a pinned native memory ingestion API, into retained records, canonical source evidence and a fixed reader's task outcomes over realistic public long histories. This differs from copying reader context after retrieval. Whether it adds useful knowledge remains empirical. Negative or beneficial effects must be retained, and a negligible effect within a meaningful prespecified bound must not be marketed as harm.

Use the CUE-R-style prompt intervention as a separate reference, not as a substitute for native ingestion. Freeze both captured-extraction replay and fresh-extraction arms; the latter mixes storage and extraction variation unless that variation is separately controlled. Keep one event's original timestamp and source ID fixed on retry. An ingestion operation ID does not by itself prove which root observation supports a newly extracted sentence, since extraction may read earlier memories. Do not count copied or derived presentations as independent corroboration.

Official benchmark scoring and a new conflicting-current-assertion measure must remain separate. Valid “previously X, now Y” explanations and questions about old states are not stale-current errors. Report evidence-supported correctness; self-reported citations, raw distinct record IDs and high token overlap are insufficient. Strip evaluator labels before ingestion. Grade under frozen blinded rubrics and preserve raw decisions; a Sol-adapted grader is not the official endpoint or independent human validation.

The proposed gold-evidence component split controls answer-bearing overlap. It should not be called fully source-disjoint unless full-haystack overlap is also checked. LoCoMo conversation clusters and repeated observations within an episode/model remain dependent. Oracle histories support development, not full-history retrieval conclusions. Use paired clustered analysis, clean-repeat and no-context controls, meaningful effect/equivalence bounds, and matched budgets/positions. Do not infer equivalence from nonsignificance or inflate sample counts with retries.

Strong baselines are the best documented native contract, complete exact-text admission within its real scope, retrieval-time duplicate suppression, retained extraction and a provenance/event control. These are not new algorithms. Preserve new identical observations, corrections, reaffirmation, expiry and newly authorized occurrences. Test the declared identity window; behavior outside an advertised retention window is not automatically a defect. Near-duplicate diversification and exact-copy filtering are different baselines.

Let Them Sleep is relevant context but not a fully reproduced large native benchmark. Its primary text is sparse, contains a simulation and negative pruning cases, and has an author-order discrepancy between metadata and PDF. The verified rohitg00 event-capture contract must not be conflated with separate pi-memory-evolution reaffirmation wording. Neither a product checklist nor a public README is peer-reviewed QA evidence.

This audit finds a plausible narrower empirical question, not a confirmed novel result, exhaustive literature coverage or journal-readiness guarantee. A useful contribution would need a defensible operational distinction over the closest studies, reproducible task effects or well-bounded null findings, robust legitimate-update behavior and credible cost/scaling limits. No model calls, company access or manuscript edits were performed by this literature task.
'''
(HERE/'contribution_assessment.txt').write_text(assessment)

index=load(HERE/'index_verification_report.json')['records']
source_report=dict(prepared_utc=NOW,status='PRIMARY_IDENTITIES_VERIFIED_WITH_EXPLICIT_METADATA_CONFLICT',
    paper_count=len(records),pdf_title_identity_matches=sum(r['pdf_title_contiguous_normalized_match'] for r in records),
    all_pdf_author_full_names_found=all(r['pdf_full_author_names_found'] for r in records),
    author_order_agreements=sum(r['pdf_author_order_matches_primary_metadata'] for r in records),
    author_order_conflicts=metadata_conflicts,
    semantic_scholar_verified=sum(r['semantic_scholar_verified'] for r in records),
    semantic_scholar_http429=sum(x.get('http_status')==429 for x in index if x['key'].endswith('_s2')),
    openalex_exact_title_doi_corroborations=sum(x.get('title_match_ratio')==100 for x in index if x['key'].endswith('_openalex')),
    workflow_scope='Literature discovery/verification/design critique only. No section draft or citation-count gate is fabricated.',
    index_deviation='One S2 success, nine public rate limits. Ten primary PDFs plus DataCite/Crossref and exact OpenAlex corroboration retained; never fabricate S2 IDs/abstracts.',
    full_text_redistribution=False,model_calls=0,
    outputs={p.name:sha(p) for p in HERE.iterdir() if p.is_file() and p.name in ['source_claim_map.json','cue_r_protocol_audit.json','grading_contracts.json','falsifiable_questions.json','new_sources.bib','public_contract_sources.bib','contribution_assessment.txt']})
save('source_verification_report.json',source_report)
print(json.dumps({k:source_report[k] for k in ['status','paper_count','pdf_title_identity_matches','author_order_agreements','semantic_scholar_verified','semantic_scholar_http429','openalex_exact_title_doi_corroborations']},indent=2))
