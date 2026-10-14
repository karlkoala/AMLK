"""P0 regressions: public session paths, transparent validator and stop snapshots."""
import importlib.util
import json
from pathlib import Path
import pytest
from mathkomp import db, importer, attempts, hypotheses, api
from mathkomp.session import Session
from mathkomp.attempts import Submission
from mathkomp.clock import FixedClock
from mathkomp.config import Config
from mathkomp.simulation import correct_answer_for

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('p0_simulator',ROOT/'synthetic_students/simulator.py')
sim=importlib.util.module_from_spec(spec);spec.loader.exec_module(sim)

@pytest.fixture
def database():
    c=db.connect(':memory:');db.init_schema(c);importer.import_all(c,ROOT/'content')
    yield c
    c.close()

def submit(s,tid,answer=None,**kw):
    if answer is None:answer=correct_answer_for(attempts.load_task(s.conn,tid))
    s.clock.advance(seconds=30)
    return s.submit(Submission(task_id=tid,answer=answer,**kw))

def representation(s):
    submit(s,'ZO06-D2-S-C',6);submit(s,'ZO06-D2-S-D',7)
    submit(s,'ZO06-D2-I-A',60);submit(s,'ZO06-D2-I-B',70)
    return s.conn.execute("SELECT * FROM student_hypotheses WHERE student_id=? AND hypothesis_type='REPRESENTATION_HYPOTHESIS'",(s.student_id,)).fetchone()

@pytest.mark.parametrize('prob,status,expected',[(.97,'SUPPORT_FOCUS','FAIL'),(.2,'PARKED','FAIL'),(.2,'SECURE','FAIL'),(.97,'ACTIVE','INCONCLUSIVE'),(.97,'UNCERTAIN','INCONCLUSIVE'),(.97,'PARKED','PASS'),(.2,'SUPPORT_FOCUS','PASS')])
def test_validator_statuses(prob,status,expected):
    profile={'id':'TEST','competencies':{'X':prob},'rules':[]}
    steps=[dict(task_id=str(i),primary_competency='X',generated_correct=True,mvp_correct=True,missing_metadata=[]) for i in range(3)]
    checks=sim.validate(profile,steps,{'competency_states':[dict(competency_id='X',status=status)]},'NO_ELIGIBLE_CANDIDATES')
    assert next(x for x in checks if x['dimension']=='COMPETENCY_LOCALIZATION')['status']==expected
    assert next(x for x in checks if x['dimension']=='DIAGNOSTIC_COMPLETION')['status']=='INCONCLUSIVE'

def test_validator_requires_distinct_observations_and_contrasts():
    profile={'id':'TEST','competencies':{'X':.97},'rules':[{'id':'r'}]}
    steps=[dict(task_id='same',primary_competency='X',generated_correct=True,mvp_correct=True,missing_metadata=[],triggered_ground_truth_rule=['r']) for _ in range(3)]
    checks=sim.validate(profile,steps,{'competency_states':[dict(competency_id='X',status='PARKED')]},'MAX_TASKS')
    assert next(x for x in checks if x['dimension']=='COMPETENCY_LOCALIZATION')['status']=='NOT_TESTABLE'
    assert next(x for x in checks if x['dimension']=='CONTRAST_COVERAGE')['status']=='NOT_TESTABLE'

def test_representation_counterexamples_and_idempotence(database):
    s=Session(database,'COUNTERS',FixedClock());h=representation(s)
    assert h['status']=='OPEN'
    control=attempts.load_task(database,h['falsifying_task'])
    assert hypotheses._comparison_key(control)==hypotheses._comparison_key(attempts.load_task(database,'ZO06-D2-S-C'))
    turn=submit(s,'ZO06-D2-S-C')
    assert any(a.status=='WEAKENED' for a in turn.hypothesis_actions)
    turn=submit(s,'ZO06-D2-S-D')
    h=dict(database.execute('SELECT * FROM student_hypotheses WHERE hypothesis_id=?',(h['hypothesis_id'],)).fetchone())
    assert h['status']=='REJECTED'
    ids=json.loads(h['contradicting_evidence']);assert len(ids)==len(set(ids))==2
    assert not (set(ids)&set(json.loads(h['supporting_evidence'])))
    assert hypotheses.detect(database,s.student_id,'ZO06_PLACE_VALUE',s.cfg,s.clock)==[]

def test_incomparable_and_supported_answers_not_counterevidence(database):
    s=Session(database,'COMPARABILITY',FixedClock());h=representation(s)
    submit(s,'ZO06-D2-S-A') # different question form
    submit(s,'ZO06-D2-S-C',support_used=True)
    h=dict(database.execute('SELECT * FROM student_hypotheses WHERE hypothesis_id=?',(h['hypothesis_id'],)).fetchone())
    assert h['status']=='OPEN'
    assert json.loads(h['contradicting_evidence'])==[]

def test_generic_supported_lifecycle_is_idempotent(database):
    s=Session(database,'LIFE',FixedClock())
    def call(support,contra):return hypotheses._open_or_update(database,s.student_id,'REPRESENTATION_HYPOTHESIS','TEST','ZO06-D2-S-C',support,contra,90,s.cfg,s.clock,'test')
    assert call(['a','b'],[]).status=='OPEN'
    assert call(['a','b','c'],[]).status=='SUPPORTED'
    assert call(['a','a','b','c'],[]).action=='UNCHANGED'
    assert call(['a','b','c'],['x']).status=='WEAKENED'
    assert call(['a','b','c'],['x','x']).action=='UNCHANGED'
    assert call(['a','b','c'],['x','y']).status=='REJECTED'

def test_prerequisite_success_updates_dependent_hypothesis(database):
    s=Session(database,'PREREQ',FixedClock())
    # Use existing equal-condition prerequisite items, no content extension.
    h=hypotheses._open_or_update(database,s.student_id,'PREREQUISITE_HYPOTHESIS',
        'ZO07_ADDITION:requires:ZO06_PLACE_VALUE','ZO06-D2-S-C',[],[],80,s.cfg,s.clock,'test')
    submit(s,'ZO06-D2-S-C')
    row=database.execute('SELECT * FROM student_hypotheses WHERE hypothesis_id=?',(h.hypothesis_id,)).fetchone()
    assert row['status']=='WEAKENED'
    submit(s,'ZO06-D2-S-D')
    row=database.execute('SELECT * FROM student_hypotheses WHERE hypothesis_id=?',(h.hypothesis_id,)).fetchone()
    assert row['status']=='REJECTED'
    assert len(json.loads(row['contradicting_evidence']))==2

def test_presence_counterexamples(database):
    s=Session(database,'PRESENCE',FixedClock())
    # Discover a controlled existing compensation family.
    rows=[dict(r) for r in database.execute("SELECT * FROM tasks WHERE primary_competency='ZO07_ADDITION'")]
    groups={}
    for t in rows:
        k=hypotheses._comparison_key(t)
        has='COMPENSATION' in attempts.task_features(database,t['task_id']).get('STRATEGY_AFFORDANCE',())
        groups.setdefault(k,{True:[],False:[]})[has].append(t)
    group=next(v for v in groups.values() if len(v[True])>=2 and len(v[False])>=2)
    for t in group[True][:2]:submit(s,t['task_id'])
    for t in group[False][:2]:submit(s,t['task_id'],-999)
    h=database.execute("SELECT * FROM student_hypotheses WHERE student_id=? AND target_construct LIKE '%STRATEGY_AFFORDANCE:without(COMPENSATION)%'",(s.student_id,)).fetchone()
    assert h is not None
    for t in group[False][:2]:submit(s,t['task_id'])
    h=database.execute('SELECT * FROM student_hypotheses WHERE hypothesis_id=?',(h['hypothesis_id'],)).fetchone()
    assert h['status']=='REJECTED'

def test_no_items_is_not_diagnostically_complete(database):
    s=Session(database,'EMPTY',FixedClock(),focus={'ZO06_2_UNBUNDLING'})
    d=s.next_task();assert d.selected_task is None
    assert d.stop_reason=='NO_ELIGIBLE_CANDIDATES'
    assert d.termination['open_areas'][0]['status']=='UNKNOWN'
    assert 'NO_ITEMS' in d.termination['open_areas'][0]['exclusion_reasons']
    profile=api.student_profile(database,s.student_id,s.cfg,s.clock)
    assert profile['next_decision']['termination']==d.termination

def test_actual_complete_focus(database):
    s=Session(database,'COMPLETE',FixedClock(),focus={'ZO13_ARITHMETIC_LAWS'})
    for _ in range(10):
        d=s.next_task()
        if not d.selected_task:break
        submit(s,d.selected_task)
    assert d.stop_reason=='ALL_NODES_SUFFICIENTLY_INFORMED'
    assert d.termination['diagnostically_complete']
    assert d.termination['open_areas']==[]

def test_node_limit_reports_unresolved_status(database):
    cfg=Config(database);cfg.override('testing.max_items_per_node',1)
    s=Session(database,'LIMIT',FixedClock(),cfg=cfg,focus={'ZO12_TASK_RELATIONS'})
    d=s.next_task();submit(s,d.selected_task)
    d=s.next_task()
    assert d.stop_reason=='NODE_TASK_LIMIT_REACHED'
    assert any(a['status']=='ACTIVE' and 'NODE_TASK_LIMIT' in a['exclusion_reasons'] for a in d.termination['open_areas'])
    assert not d.termination['diagnostically_complete']
