#!/usr/bin/env python3
"""Isolierter, reproduzierbarer Simulator für mathkomp. Nur Python-Standardbibliothek."""
from __future__ import annotations
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
FORBIDDEN = {'ground_truth', 'expected_result', 'expected_competency', 'expected_error', 'expected_hypothesis', 'competencies', 'systematic_error_patterns'}

def guard(value):
    if isinstance(value, dict):
        if FORBIDDEN.intersection(value):
            raise ValueError('Ground-Truth-Leakage im MVP-Request')
        for v in value.values(): guard(v)
    elif isinstance(value, (list, tuple)):
        for v in value: guard(v)

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def matches(rule, task, features):
    return (('competencies' not in rule or task['primary_competency'] in rule['competencies'])
        and ('representations' not in rule or task['representation_mode'] in rule['representations'])
        and ('difficulties' not in rule or task['internal_difficulty'] in rule['difficulties'])
        and all(v in features.get(k, []) for k, vals in rule.get('all_features', {}).items() for v in vals)
        and (not rule.get('any_features') or any(v in features.get(k, []) for k, vals in rule['any_features'].items() for v in vals)))

class ResponseEngine:
    """Kennt nur Profil, Item und Merkmale; erhält keine MVP-Inferenz."""
    def __init__(self, profile, seed):
        self.profile = copy.deepcopy(profile)
        self.rng = random.Random(seed)

    def decide(self, task, features):
        p = self.profile
        prob = p['competencies'].get(task['primary_competency'], p['base_probability'])
        applied = []
        pattern = None
        for rule in p['rules']:
            if matches(rule, task, features):
                prob = rule.get('probability', prob + rule.get('effect', 0))
                applied.append(rule['id'])
                pattern = rule.get('error_pattern', pattern)
        prob = max(0., min(1., prob))
        draw = self.rng.random()
        slip_draw = self.rng.random()
        slip = slip_draw < p['slip_probability']
        correct = draw < prob and not slip
        return {'calculated_probability_correct': prob * (1-p['slip_probability']),
                'probability_before_slip': prob, 'random_value': draw, 'slip_random_value': slip_draw,
                'slip': slip, 'generated_correct': correct, 'triggered_ground_truth_rule': applied,
                'requested_error_pattern': None if slip or correct else pattern}

    def answer(self, task, decision):
        from mathkomp.simulation import correct_answer_for
        from mathkomp.scoring import score
        correct = correct_answer_for(task)
        if decision['generated_correct']: return correct, None
        pattern = decision['requested_error_pattern']
        candidate = None
        if isinstance(correct, (int, float)) and not isinstance(correct, bool):
            if pattern == 'OMITTED_CARRY': candidate = correct - 10
            elif pattern == 'OMITTED_BORROW': candidate = correct + 10
            elif pattern == 'PLACE_VALUE_SWAP' and isinstance(correct, int) and 10 <= correct <= 99:
                candidate = int(str(correct)[::-1])
        if candidate is not None and not score(task, candidate).is_correct:
            return candidate, pattern
        # Generische Fehler sind bewusst keine behaupteten systematischen Muster.
        for _ in range(100):
            delta = self.rng.choice([-3, -2, -1, 1, 2, 3])
            if isinstance(correct, bool): candidate = not correct
            elif isinstance(correct, (int, float)): candidate = correct + delta
            elif isinstance(correct, list):
                candidate = list(correct)
                if candidate:
                    i = self.rng.randrange(len(candidate))
                    candidate[i] = candidate[i] + delta if isinstance(candidate[i], (int,float)) else '__wrong__'
                else: candidate = ['__wrong__']
            elif isinstance(correct, dict):
                candidate = dict(correct)
                key = self.rng.choice(list(candidate))
                candidate[key] = max(0, candidate[key] + delta)
            else:
                options = json.loads(task['task_payload']).get('options', [])
                candidate = self.rng.choice(options) if options else str(delta)
            if not score(task, candidate).is_correct:
                return candidate, 'SLIP' if decision['slip'] else 'ALTERNATIVE_ERROR'
        raise ValueError(f"Keine gültige Falschantwort erzeugbar: {task['task_id']}")

class MVPAdapter:
    def __init__(self, repo):
        from mathkomp import db, importer
        self.template = db.connect(':memory:')
        db.init_schema(self.template)
        with db.transaction(self.template): importer.import_all(self.template, repo/'content')

    def __del__(self):
        if hasattr(self, 'template'): self.template.close()

    def start(self, output, grade):
        from mathkomp import db
        from mathkomp.clock import FixedClock
        from mathkomp.session import Session
        conn = db.connect(output)
        self.template.backup(conn)
        clock = FixedClock()
        # Absichtlich identische neutrale ID in voneinander isolierten Datenbanken.
        session = Session(conn, 'SIMULATED_LEARNER', clock, grade_reference=grade)
        return conn, clock, session


def evaluation_summary(checks):
    """Descriptive counts, never a blanket pedagogical PASS."""
    return dict(collections.Counter(c['status'] for c in checks))


def validate(profile, steps, inference, stop):
    checks = []
    def add(dimension, name, status, detail):
        checks.append(dict(dimension=dimension, assertion=name, status=status, detail=detail))
    def distinct(rows):
        return len({s['task_id'] for s in rows})
    def condition(s):
        # Missing comparison metadata cannot prove controlled contrasts.
        return (s['primary_competency'], s.get('difficulty'), s.get('scoring_rule'), s.get('question_form'))
    add('RESPONSE_INTEGRITY', 'generated_answers_match_mvp_scoring',
        'NOT_TESTABLE' if not steps else ('PASS' if all(s['generated_correct']==s['mvp_correct'] for s in steps) else 'FAIL'),
        'Technischer Abgleich, kein unabhängiger Nachweis der Lösungsschlüssel.')
    states = {s['competency_id']:s for s in inference['competency_states']}
    real_statuses = {'UNKNOWN','ACTIVE','SECURE','PARKED','UNCERTAIN','SUPPORT_FOCUS','BLOCKED','REACTIVATED'}
    for cid, expected in profile['competencies'].items():
        subset = [s for s in steps if s['primary_competency']==cid]
        actual = states.get(cid, {}).get('status', 'UNKNOWN')
        probs = [s.get('probability_before_slip', expected) for s in subset]
        uniform_safe = probs and min(probs)>=.9
        uniform_weak = probs and max(probs)<=.35
        if actual not in real_statuses:
            status = 'FAIL'
        elif distinct(subset)<2:
            status = 'NOT_TESTABLE'
        elif uniform_safe and actual=='SUPPORT_FOCUS':
            status = 'FAIL'
        elif uniform_weak and actual in ('SECURE','PARKED'):
            status = 'FAIL'
        elif actual in ('UNKNOWN','ACTIVE','REACTIVATED','BLOCKED','UNCERTAIN'):
            status = 'INCONCLUSIVE'
        elif uniform_safe and actual in ('SECURE','PARKED'):
            status = 'PASS'
        elif uniform_weak and actual=='SUPPORT_FOCUS':
            status = 'PASS'
        else:
            status = 'INCONCLUSIVE'
        add('COMPETENCY_LOCALIZATION',cid,status,
            f'Basis={expected}; effektiv beobachtete Profilbedingungen={sorted(set(probs))}; '
            f'MVP={actual}; verschiedene Items={distinct(subset)}. '
            'UNCERTAIN kann angemessen sein; ACTIVE bleibt offen. Gemischte Bedingungen erlauben kein pauschales Sollurteil.')
    known_profile_limits = {'SUS_02':'Bündelung erbt hohe Basis statt vorgesehener Unsicherheit.',
        'SUS_08':'Faktenwissen und Grundvorstellung sind nicht getrennt.',
        'SUS_10':'Strategieangebot ist nur Proxy für Strategieanforderung.',
        'SUS_11':'IMAGE_CONTEXT trifft auch basale Zählbilder.'}
    if profile['id'] in known_profile_limits:
        add('PROFILE_VALIDITY','intended_profile','NOT_TESTABLE',known_profile_limits[profile['id']])
    for rule in profile['rules']:
        hit = [s for s in steps if rule['id'] in s.get('triggered_ground_truth_rule',[])]
        add('BEHAVIOR_COVERAGE',rule['id'], 'PASS' if distinct(hit)>=2 else 'NOT_TESTABLE',
            f'{distinct(hit)} verschiedene passende Items; technische Abdeckung, keine Ursachenbestätigung.')
        # Explicit matched counterconditions are required for conditional targets.
        controls = [s for s in steps if rule['id'] not in s.get('triggered_ground_truth_rule',[])]
        pairs = [(key,[s for s in hit if condition(s)==key],[s for s in controls if condition(s)==key])
                 for key in {condition(s) for s in hit} if all(key)]
        adequate = [(key,h,c) for key,h,c in pairs if distinct(h)>=2 and distinct(c)>=2]
        status = 'INCONCLUSIVE' if adequate else 'NOT_TESTABLE'
        add('CONTRAST_COVERAGE',rule['id'], status,
            f'{len(adequate)} Gruppen mit mindestens zwei Ziel- und Kontrollitems bei gleicher Kompetenz, Stufe, Scoring- und Frageform. '
            'Weitere Merkmalskonfundierung bleibt fachlich zu prüfen; kein kausales PASS.')
    if profile['id']=='SUS_13':
        grouped=collections.defaultdict(list)
        for s in steps:
            if s['difficulty']=='D4': grouped[s['primary_competency']].append(s)
        mixed=[k for k,v in grouped.items() if distinct(v)>=2 and any(s['mvp_correct'] for s in v) and not all(s['mvp_correct'] for s in v)]
        add('UNCERTAINTY_HANDLING','contradictory_D4_evidence',
            'NOT_TESTABLE' if not mixed else ('PASS' if all(any(f['value']=='D4' and f['status']=='UNCERTAIN'
            for f in states[k].get('facets',{}).get('INTERNAL_DIFFICULTY',[])) for k in mixed) else 'FAIL'),
            'Konkretes Unsicherheitsziel, betroffene Kompetenzen: '+str(mixed))
    missing = [s['task_id'] for s in steps if s.get('missing_metadata')]
    add('METADATA','metadata_available','FAIL' if missing else ('PASS' if steps else 'NOT_TESTABLE'),str(missing))
    termination = (inference.get('next_decision') or {}).get('termination',{})
    technical = stop in ('MAX_TASKS','USER_STOP','ENGINE_STOP')
    open_states = [s['competency_id'] for s in states.values() if s['status'] in ('ACTIVE','UNKNOWN','UNCERTAIN','SUPPORT_FOCUS','REACTIVATED')]
    if stop=='ALL_NODES_SUFFICIENTLY_INFORMED':
        status='PASS' if termination.get('diagnostically_complete') and not termination.get('open_areas') and not termination.get('open_hypotheses') else 'FAIL'
    else:
        status='INCONCLUSIVE'
    add('DIAGNOSTIC_COMPLETION','remaining_targets',status,
        f'Stopp={stop}; technische Begrenzung={technical}; offene gespeicherte Bereiche={open_states}; '
        f'Abschlussdetails={termination}. Ein technischer Stopp bestätigt keine vollständige Diagnostik.')
    for dimension in ['ERROR_PATTERN_DETECTION','HYPOTHESIS_GENERATION','HYPOTHESIS_DISCRIMINATION','REPRESENTATION_EFFECT_DETECTION']:
        add(dimension,'specific_goal','NOT_TESTABLE',
            'Kein fachlich kontrollierter automatischer Sollnachweis für dieses Profil. Nicht als bestanden gewertet; P0-Regressionsfolgen separat auswerten.')
    add('DATA_EFFICIENCY','redundancy','NOT_TESTABLE','Ohne erfüllte diagnostische Ziele ist eine kurze Session kein Effizienznachweis.')
    return checks

class Runner:
    def __init__(self, repo, output, profiles=None, max_tasks=100):
        self.repo=Path(repo).resolve(); self.output=Path(output).resolve()
        sys.path.insert(0,str(self.repo/'src'))
        self.profiles=json.loads(Path(profiles or HERE/'profiles.json').read_text(encoding='utf-8'))
        self.adapter=MVPAdapter(self.repo); self.max_tasks=max_tasks
        self.output.mkdir(parents=True,exist_ok=True)

    def runStudent(self, studentId, seed):
        from mathkomp import attempts, api, renderer
        from mathkomp.attempts import Submission
        from mathkomp.simulation import events_for
        from dataclasses import asdict
        p=self.profiles[studentId]
        dest=self.output/f'{studentId}_seed_{seed}'
        suffix=1
        while dest.exists():
            dest=self.output/f'{studentId}_seed_{seed}_{suffix}'; suffix+=1
        dest.mkdir()
        conn,clock,session=self.adapter.start(dest/'mvp.sqlite3',p['grade'])
        try:
            engine=ResponseEngine(p,seed)
            steps=[]; decision=session.next_task(); stop='MAX_TASKS'
            for index in range(self.max_tasks):
                if decision.selected_task is None:
                    stop=decision.stop_reason or 'ENGINE_STOP'; break
                task=attempts.load_task(conn,decision.selected_task)
                features={k:sorted(v) for k,v in attempts.task_features(conn,task['task_id']).items()}
                result=engine.decide(task,features)
                answer,pattern=engine.answer(task,result)
                events=events_for(task,renderer.render(task),result['generated_correct'])
                # Bei Zählinteraktionen entsprechen Klicks der abgegebenen Zahl.
                if task['interaction_mode']=='CLICK_SEQUENCE' and isinstance(answer,int) and answer>=0:
                    events=[{'event_type':'CLICK','object_id':f'obj{i+1}'} for i in range(answer)]+[{'event_type':'SUBMIT'}]
                request=dict(task_id=task['task_id'],answer=answer,events=events,
                    selected_by_reason=decision.reason,selected_by_rule=decision.rule_triggered)
                guard(request)
                clock.advance(seconds=30)
                turn=session.submit(Submission(**request))
                missing=[k for k in ['primary_competency','internal_difficulty','representation_mode','task_purpose'] if not task.get(k)]
                if not features: missing.append('task_features')
                entry=dict(simulation_run_id=f'{studentId}:{seed}',student_id=studentId,seed=seed,
                    task_id=task['task_id'],primary_competency=task['primary_competency'],difficulty=task['internal_difficulty'],
                    scoring_rule=task['scoring_rule'],question_form=task['question_form'],
                    representation=task['representation_mode'],task_purpose=task['task_purpose'],features=features,
                    generated_answer=answer,generated_error_pattern=pattern,**result,
                    missing_metadata=missing,metadata_warning='MISSING_TASK_METADATA' if missing else None,
                    mvp_correct=turn.is_correct,mvp_error_code=turn.error_codes,mvp_evidence=turn.evidence_created,
                    mvp_hypotheses_after_task=api.hypotheses_view(conn,session.student_id),
                    mvp_competency_state_after_task=session.state_snapshot(),
                    routing_reason=decision.explanation,routing=asdict(decision),
                    next_task_id=turn.next_decision.selected_task if turn.next_decision else None)
                steps.append(entry)
                decision=turn.next_decision
                if decision is None: stop='ENGINE_STOP'; break
            if decision is not None and decision.selected_task is None: stop=decision.stop_reason or 'ENGINE_STOP'
            inference=api.student_profile(conn,session.student_id,session.cfg,clock)
            conn.commit()
            checks=validate(p,steps,inference,stop)
            unsupported=[s['task_id'] for s in steps if s['requested_error_pattern'] and s['generated_error_pattern']!=s['requested_error_pattern']]
            checks.append(dict(dimension='ERROR_GENERATION',assertion='requested_pattern_supported',status='FAIL' if unsupported else 'PASS',detail=str(unsupported)))
            status='EVALUATED'
            assertion_summary=evaluation_summary(checks)
            coverage=[]
            for rule in p['rules']:
                matching=[]
                for row in conn.execute('SELECT * FROM tasks ORDER BY task_id'):
                    t=dict(row); f=attempts.task_features(conn,t['task_id'])
                    if matches(rule,t,f): matching.append(t['task_id'])
                coverage.append({'rule':rule['id'],'available_tasks':matching,'warning':None if matching else 'NO_MATCHING_ITEMS'})
            efficiency=dict(total_tasks=len(steps),purposes=dict(collections.Counter(s['task_purpose'] for s in steps)),
                competency_nodes_activated=len({s['primary_competency'] for s in steps}),
                hypotheses_generated=len(inference['hypotheses']),redundancy_status='UNKNOWN')
            report=dict(student_id=studentId,seed=seed,status=status,stop_reason=stop,
                assertion_summary=assertion_summary,ground_truth=p,behavior=steps,mvp_inference=inference,assertions=checks,efficiency=efficiency,
                catalog_coverage=coverage,limitations=['Simulationsparameter sind technische Annahmen, keine empirisch kalibrierten Personenparameter.',
                'Alter wird nicht übertragen: die bestehende Session-Schnittstelle unterstützt nur Klassenstufe.',
                'Leere Merkmalslisten bedeuten unbekannte Abdeckung, nicht nachgewiesene Merkmalsfreiheit.'])
            dump(dest/'report.json',report)
            dump(dest/'mvp_inference.json',inference)
            with (dest/'steps.jsonl').open('w',encoding='utf-8') as stream:
                for s in steps: stream.write(json.dumps(s,ensure_ascii=False,sort_keys=True)+'\n')
            text=[f'# {studentId} · Seed {seed} · {status}',p['notes'],
                f'\nAufgaben: {len(steps)} · Stopp: {stop}',
                '\nEinzelziele: PASS / FAIL / INCONCLUSIVE / NOT_TESTABLE. EVALUATED ist kein fachliches Gesamturteil.',
                '\n## Soll / Ist', '| Kompetenz | P korrekt (Basis) | MVP-Status |','|---|---:|---|']
            states={s['competency_id']:s for s in inference['competency_states']}
            for cid,prob in p['competencies'].items(): text.append(f"| {cid} | {prob} | {states.get(cid,{}).get('status','UNKNOWN')} |")
            text+=['\n## Prüfungen']+[f"- **{c['status']}** {c['dimension']} / {c['assertion']}: {c['detail']}" for c in checks]
            text+=['\n## Fehlende Aufgaben']+[f"- {c['rule']}: keine passenden Items vorhanden." for c in coverage if c['warning']]
            text+=['\n## Dateien','`report.json`: vollständiger Vergleich und Verlauf. `mvp_inference.json`: ausschließlich echte MVP-Ergebnisse. `mvp.sqlite3`: isolierte Session.']
            (dest/'report.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
            print(f'{studentId} seed={seed}: {status}, {len(steps)} Aufgaben ({stop})',flush=True)
            return report
        finally: conn.close()

    def runAllStudents(self,seed): return [self.runStudent(s,seed) for s in self.profiles]
    def runStudentMultiple(self,studentId,seeds): return [self.runStudent(studentId,s) for s in seeds]
    def runAllStudentsMultiple(self,seeds): return [self.runStudent(s,n) for n in seeds for s in self.profiles]
    def runStudentMonteCarlo(self,studentId,runs=100,seed=1): return self.runStudentMultiple(studentId,range(seed,seed+runs))

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--repo',type=Path,default=Path('/Users/philippwechsler/12'))
    a.add_argument('--output',type=Path,default=HERE/'results')
    a.add_argument('--profiles',type=Path,default=HERE/'profiles.json')
    a.add_argument('--student',default='all',help='all oder z.B. SUS_05; mehrere kommasepariert')
    a.add_argument('--seed',type=int,default=42)
    a.add_argument('--seeds',help='z.B. 1,2,3,4,5')
    a.add_argument('--mode',choices=['deterministic','stochastic','monte-carlo'],default='deterministic')
    a.add_argument('--runs',type=int,default=100)
    a.add_argument('--max-tasks',type=int,default=100)
    args=a.parse_args()
    if args.max_tasks<1 or args.runs<1: a.error('runs und max-tasks müssen positiv sein')
    if not (args.repo/'src/mathkomp/session.py').exists(): a.error('Kein mathkomp-Projekt unter --repo')
    runner=Runner(args.repo,args.output,args.profiles,args.max_tasks)
    students=list(runner.profiles) if args.student=='all' else args.student.split(',')
    if any(s not in runner.profiles for s in students): a.error('Unbekannte Test-SuS-ID')
    seeds=[int(s) for s in args.seeds.split(',')] if args.seeds else [args.seed]
    if args.mode=='monte-carlo': seeds=list(range(args.seed,args.seed+args.runs))
    elif args.mode=='stochastic' and not args.seeds: seeds=[random.SystemRandom().randrange(2**63)]
    reports=[runner.runStudent(s,n) for n in seeds for s in students]
    summary=[dict(student_id=r['student_id'],seed=r['seed'],status=r['status'],tasks=r['efficiency']['total_tasks'],
        assertions=collections.Counter(c['status'] for c in r['assertions'])) for r in reports]
    dump(args.output/'batch_report.json',summary)
    (args.output/'batch_report.md').write_text('# Synthetic MVP Validation\n\nEVALUATED bedeutet ausgewertet, nicht bestanden. Einzelbewertungen stehen in den Berichten.\n\n| SuS | Seed | Status | Aufgaben |\n|---|---:|---|---:|\n'+'\n'.join(f"| {r['student_id']} | {r['seed']} | {r['status']} | {r['tasks']} |" for r in summary)+'\n',encoding='utf-8')
    print(f'Berichte: {args.output.resolve()}')

if __name__=='__main__': main()
