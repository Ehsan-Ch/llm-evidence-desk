"""Transparent fixture checks, not an LLM judge or a general reliability claim."""
import json
from pathlib import Path
import platform
import statistics
from datetime import datetime, timezone
from .core import Index, bundled, answer, normalize, SYSTEM
import hashlib


def score_result(question, result):
    gold = question['gold']
    if not gold:
        return {'fact_match':False,'source_match':False,'success':result['status']=='ABSTAIN',
                'retrieval_hit':None}
    expected = {g['source'] for g in gold}
    matched = all(any(e['source_id']==g['source'] and normalize(g['contains']).casefold() in normalize(e['quote']).casefold()
                      for e in result['evidence']) for g in gold)
    sources = bool(result['evidence']) and {e['source_id'] for e in result['evidence']} <= expected
    retrieved = expected <= {h['id'] for h in result['hits']}
    return {'fact_match':matched,'source_match':sources,
            'success':result['status']=='ANSWER' and matched and sources,'retrieval_hit':retrieved}


def evaluate(client, output, provenance=None):
    index = Index(bundled('corpus.json'))
    questions = bundled('questions.json')
    dev = [q for q in questions if q['split']=='development']
    calibration = []
    for k in (1,3,5):
        hits = sum({g['source'] for g in q['gold']} <= {h['id'] for h in index.retrieve(q['question'],k)} for q in dev)
        calibration.append({'k':k,'hits':hits,'questions':len(dev),'recall':hits/len(dev)})
    # Maximize development recall, then minimize context. Never select on evaluation labels.
    k = max(calibration, key=lambda c:(c['recall'],-c['k']))['k']
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for q in (q for q in questions if q['split']=='evaluation'):
        try:
            result = answer(index, q['question'], client, k)
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            result = dict(question=q['question'],hits=index.retrieve(q['question'],k),status='ERROR',evidence=[],
                          errors=[str(exc)], raw='',model_called=True,latency_seconds=0.,usage={})
        rows.append({**q, **result, 'checks':score_result(q,result)})
        # Persist incremental progress if a model process is interrupted.
        (output/'progress.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
        print(q['id'], result['status'], 'PASS' if rows[-1]['checks']['success'] else 'MISS', flush=True)
    positive = [r for r in rows if r['gold']]
    unknown = [r for r in rows if not r['gold']]
    accepted = [r for r in rows if r['status']=='ANSWER']
    latency = [r['latency_seconds'] for r in rows if r['model_called'] and r['status']!='ERROR']
    ratio = lambda a,b:a/b if b else None
    summary = dict(total=len(rows),successes=sum(r['checks']['success'] for r in rows),
        success_rate=ratio(sum(r['checks']['success'] for r in rows),len(rows)),
        answerable=len(positive), answerable_successes=sum(r['checks']['success'] for r in positive),
        retrieval_hits=sum(r['checks']['retrieval_hit'] for r in positive),
        unknown=len(unknown), unknown_abstentions=sum(r['status']=='ABSTAIN' for r in unknown),
        accepted=len(accepted), accepted_correct=sum(r['checks']['success'] for r in accepted),
        accepted_precision=ratio(sum(r['checks']['success'] for r in accepted),len(accepted)),
        check_failures=sum(r['status']=='CHECK_FAILED' for r in rows),errors=sum(r['status']=='ERROR' for r in rows),
        model_calls=sum(r['model_called'] for r in rows),median_latency_seconds=statistics.median(latency) if latency else None,
        prompt_tokens=sum(r['usage'].get('prompt_tokens',0) for r in rows),
        completion_tokens=sum(r['usage'].get('completion_tokens',0) for r in rows),
        adversarial_successes=sum(r['checks']['success'] for r in rows if r['kind']=='adversarial'),
        adversarial_total=sum(r['kind']=='adversarial' for r in rows))
    payload = dict(title='Evidence Desk',mode='report',created_utc=datetime.now(timezone.utc).isoformat(),
        model=client.model,runtime_provenance=provenance,
        python=platform.python_version(),corpus_sha256=index.digest,
        prompt_sha256=hashlib.sha256(SYSTEM.encode()).hexdigest(),
        config=dict(k=k,temperature=0,seed=41,max_tokens=384,thinking=False),
        development=calibration,summary=summary,rows=rows,excluded=index.excluded,
        corpus=[{'id':c.id,'title':c.title,'text':c.text} for c in index.chunks])
    (output/'evaluation.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False),encoding='utf-8')
    (output/'progress.json').unlink(missing_ok=True)
    print(json.dumps(summary, indent=2), flush=True)
    return payload


def render(payload, output):
    from importlib.resources import files
    template = files('evidence_desk').joinpath('template.html').read_text(encoding='utf-8')
    content = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace('<','\\u003c')
    Path(output).write_text(template.replace('__PAYLOAD__',content), encoding='utf-8')
