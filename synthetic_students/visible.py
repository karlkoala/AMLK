#!/usr/bin/env python3
"""Sichtbarer Testmodus für die vorhandene mathkomp-Engine."""
import argparse
from dataclasses import asdict
from datetime import datetime
from http.server import HTTPServer
import json
from pathlib import Path
import secrets
import sys
import webbrowser
from simulator import MVPAdapter, ResponseEngine, guard, validate, dump

HERE=Path(__file__).resolve().parent

class LiveRun:
    def __init__(self,repo,output):
        self.repo=repo; self.output=output; self.adapter=MVPAdapter(repo)
        self.profiles=json.loads((HERE/'profiles.json').read_text())
        self.view_db=None; self.conn=None; self.session=None; self.steps=[]; self.finished=False; self.stop=None

    def start(self,student,seed):
        from mathkomp import attempts,renderer
        if student not in self.profiles: raise ValueError('Unbekanntes Testprofil')
        if self.conn:
            self.finish('RESTARTED'); self.conn.close()
        self.view_db=None; self.profile=self.profiles[student]; self.seed=seed
        self.dest=self.output/(datetime.now().strftime('%Y%m%d-%H%M%S')+'_'+student+'_'+secrets.token_hex(3))
        self.dest.mkdir(parents=True)
        self.conn,self.clock,self.session=self.adapter.start(self.dest/'mvp.sqlite3',self.profile['grade'])
        self.engine=ResponseEngine(self.profile,seed); self.steps=[]; self.finished=False; self.stop=None
        self.decision=self.session.next_task(); self.conn.commit()
        return self.snapshot()

    def snapshot(self):
        from mathkomp import attempts,renderer
        task=None
        if self.session and not self.finished and self.decision and self.decision.selected_task:
            raw=attempts.load_task(self.conn,self.decision.selected_task)
            task=renderer.render(raw)
            task['title']=raw['title']; task['primary_competency']=raw['primary_competency']
        if self.session and not task and not self.finished: self.finish(self.decision.stop_reason or 'ENGINE_STOP')
        return dict(started=self.session is not None, finished=self.finished, task=task,
            count=len(self.steps),stop_reason=self.stop,report_path=str(self.dest/'report.md') if self.finished else None,
            history=[dict(task_id=s['task_id'],correct=s['mvp_correct'],answer=s['generated_answer'],prompt=s['prompt']) for s in self.steps],
            last=self.steps[-1] if self.steps else None)

    def step(self,task_id):
        from mathkomp import attempts,renderer,api
        from mathkomp.attempts import Submission
        from mathkomp.simulation import events_for
        if not self.session or self.finished: raise ValueError('Bitte zuerst einen Test starten.')
        if self.decision.selected_task!=task_id: raise ValueError('Aufgabe wurde bereits beantwortet. Ansicht neu laden.')
        task=attempts.load_task(self.conn,task_id)
        features={k:sorted(v) for k,v in attempts.task_features(self.conn,task_id).items()}
        outcome=self.engine.decide(task,features); answer,pattern=self.engine.answer(task,outcome)
        spec=renderer.render(task); events=events_for(task,spec,outcome['generated_correct'])
        if task['interaction_mode']=='CLICK_SEQUENCE' and isinstance(answer,int) and answer>=0:
            events=[dict(event_type='CLICK',object_id=f'obj{i+1}') for i in range(answer)]+[dict(event_type='SUBMIT')]
        request=dict(task_id=task_id,answer=answer,events=events,selected_by_reason=self.decision.reason,selected_by_rule=self.decision.rule_triggered)
        guard(request); self.clock.advance(seconds=30)
        turn=self.session.submit(Submission(**request))
        step=dict(task_id=task_id,prompt=task['task_prompt'],primary_competency=task['primary_competency'],
            scoring_rule=task['scoring_rule'],question_form=task['question_form'],
            difficulty=task['internal_difficulty'],representation=task['representation_mode'],task_purpose=task['task_purpose'],
            features=features,generated_answer=answer,generated_error_pattern=pattern,**outcome,
            missing_metadata=[],mvp_correct=turn.is_correct,mvp_error_code=turn.error_codes,
            mvp_evidence=turn.evidence_created,mvp_hypotheses_after_task=api.hypotheses_view(self.conn,self.session.student_id),
            mvp_competency_state_after_task=self.session.state_snapshot(),routing_reason=self.decision.explanation,
            next_task_id=turn.next_decision.selected_task if turn.next_decision else None)
        self.steps.append(step); self.decision=turn.next_decision; self.conn.commit()
        with (self.dest/'steps.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(step,ensure_ascii=False)+'\n')
        if self.decision is None or self.decision.selected_task is None:
            self.finish(self.decision.stop_reason if self.decision else 'ENGINE_STOP')
        elif len(self.steps)>=100: self.finish('MAX_TASKS')
        return self.snapshot()

    def finish(self,reason):
        from mathkomp import api
        if not self.session or self.finished: return
        self.stop=reason; self.finished=True
        inference=api.student_profile(self.conn,self.session.student_id,self.session.cfg,self.clock)
        checks=validate(self.profile,self.steps,inference,reason)
        dump(self.dest/'mvp_inference.json',inference)
        dump(self.dest/'report.json',dict(student_id=self.profile['id'],seed=self.seed,ground_truth=self.profile,
            behavior=self.steps,mvp_inference=inference,assertions=checks,stop_reason=reason))
        (self.dest/'report.md').write_text(f"# {self.profile['id']} · Seed {self.seed}\n\n{len(self.steps)} Aufgaben · {reason}\n\n"+
            '\n'.join(f"- {c['status']}: {c['assertion']} – {c['detail']}" for c in checks),encoding='utf-8')
        self.conn.commit()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',type=Path,default=HERE.parent)
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args(); repo=args.repo.resolve()
    if not (repo/'src/mathkomp/session.py').is_file(): parser.error('Projektordner mit --repo angeben.')
    sys.path.insert(0,str(repo/'src'))
    from mathkomp.server import Handler
    run=LiveRun(repo,HERE/'visible_results'); token=secrets.token_urlsafe(24)
    class VisibleHandler(Handler):
        ui_root=repo/'ui'
        def _send(self,status,body,content_type):
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'")
            self.end_headers()
            if self.command!='HEAD': self.wfile.write(body)
        def do_GET(self):
            from urllib.parse import urlparse
            route=urlparse(self.path).path
            if route=='/live/runs':
                items=[]
                for report in sorted(run.output.glob('*/report.json'),reverse=True):
                    data=json.loads(report.read_text())
                    items.append(dict(id=report.parent.name,label=f"{data['student_id']} · Seed {data['seed']} · {len(data['behavior'])} Aufgaben · {report.parent.name[:15]}"))
                return self._json(items)
            if route=='/live/state': return self._json(run.snapshot())
            if route=='/live/profiles': return self._json(dict(token=token,profiles=[dict(id=p['id'],notes=p['notes']) for p in run.profiles.values()]))
            if route in ('/','/live.js','/live.css'):
                name={'/':'live.html','/live.js':'live.js','/live.css':'live.css'}[route]
                return self._send(200,(HERE/name).read_bytes(),{'/':'text/html; charset=utf-8','/live.js':'text/javascript; charset=utf-8','/live.css':'text/css; charset=utf-8'}[route])
            if route.startswith('/api/'):
                if not run.session and not run.view_db: return self._error(409,'Bitte zuerst einen Test-SuS starten.')
                self.db_path=run.view_db or run.dest/'mvp.sqlite3'
            super().do_GET()
        def do_POST(self):
            # Nur die lokale Testansicht darf Sessions verändern.
            if self.headers.get('X-Simulation-Token')!=token: return self._error(403,'Ungültiges Sitzungstoken')
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size>8192: return self._error(413,'Anfrage zu groß')
                data=json.loads(self.rfile.read(size))
                if self.path=='/live/start': result=run.start(data['student'],int(data['seed']))
                elif self.path=='/live/view':
                    if run.session and not run.finished: raise ValueError('Bitte zuerst den laufenden Test beenden.')
                    selected=(run.output/data['id']).resolve()
                    if selected.parent!=run.output.resolve() or not (selected/'report.json').is_file(): raise ValueError('Unbekanntes Ergebnis')
                    run.view_db=selected/'mvp.sqlite3'
                    result={'selected':data['id']}
                elif self.path=='/live/step': result=run.step(data['task_id'])
                elif self.path=='/live/stop': run.finish('USER_STOP'); result=run.snapshot()
                else: return self._error(404,'Unbekannter Endpunkt')
                return self._json(result)
            except (ValueError,KeyError) as exc: return self._error(400,str(exc))
            except Exception as exc: return self._error(500,f'{type(exc).__name__}: {exc}')
    server=HTTPServer(('127.0.0.1',args.port),VisibleHandler)
    url=f'http://127.0.0.1:{server.server_port}/'
    print(f'Sichtbarer Test: {url}',flush=True)
    print('Dieses Fenster geöffnet lassen. Beenden mit Ctrl+C.',flush=True)
    if not args.no_browser: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        run.finish('SERVER_STOP')
        if run.conn: run.conn.close()
        server.server_close()

if __name__=='__main__': main()
