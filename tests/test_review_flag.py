"""Review flags stay editable until a writer result is collected."""

import shutil
import unittest

from test_reviews import ReviewFlowCase
from test_viewer_server import ViewerServerCase, request, run_node
from test_graph_cards import OVR_JS


class ReviewFlagTests(ReviewFlowCase):
    def test_running_changes_drive_planned_reviews_and_collection(self):
        sb = self.sandbox()
        for initial, final in ((False, True), (True, False)):
            with self.subTest(initial=initial):
                slug = 'enable' if final else 'disable'
                task = self.planned(sb, slug, [('ONE', 'implementation', '', ['--review'] if initial else [])],
                                    settings=['review=selected-jobs'])
                self.run_writer(sb, task, slug, 'ONE', collect=False)
                points = sb.json('status', slug)['settings']['review']['points']
                sb.sae('job', 'edit', slug, 'ONE', '--review' if final else '--no-review', '--reason', 'scope changed')
                event = [e for e in sb.events(task) if e['type'] == 'job.changed'][-1]
                self.assertEqual((event['by'], event['reason'], event['changes']['review']),
                                 ('cli', 'scope changed', [initial, final]))
                status = sb.json('status', slug)
                self.assertEqual(status['settings']['review']['points'], points)
                from sae_lib.tasks import Task
                from sae_lib.control import next_step_card
                from sae_lib.reviews import planned_reviews
                loaded = Task(sb.task_worktree(task), task, folder=sb.task_dir(task))
                loaded.load()
                self.assertEqual('REVIEW-ONE' in [r['id'] for r in planned_reviews(loaded)], final)
                card = next_step_card(loaded, None, ['REVIEW-INTEGRATION'])
                self.assertIn(f'review flag ONE: {"on" if initial else "off"} → {"on" if final else "off"}',
                              card["changes"])
                sb.sae('collect', slug, 'ONE')
                jobs = sb.state(task)['jobs']
                self.assertEqual('REVIEW-ONE' in jobs, final)
                self.assertEqual(jobs['ONE']['merged'], not final)
                self.assertIn('done', sb.sae('job', 'edit', slug, 'ONE', '--review', '--reason', 'late', code=1).stderr)

    def test_review_points_keep_control_of_collection(self):
        sb = self.sandbox()
        for points, flagged, due in (('all-jobs', True, True), ('all-jobs', False, True),
                                     ('integration', True, False), ('integration', False, False)):
            with self.subTest(points=points, flagged=flagged):
                slug = points + ('-on' if flagged else '-off')
                task = self.planned(sb, slug, [('ONE', 'implementation', '', ['--review'] if not flagged else [])],
                                    settings=['review=' + points])
                self.run_writer(sb, task, slug, 'ONE', collect=False)
                sb.sae('job', 'edit', slug, 'ONE', '--review' if flagged else '--no-review', '--reason', 'scope changed')
                sb.sae('collect', slug, 'ONE')
                jobs = sb.state(task)['jobs']
                self.assertEqual('REVIEW-ONE' in jobs, due)
                self.assertEqual(jobs['ONE']['merged'], not due)
                self.assertEqual(sb.json('status', slug)['settings']['review']['points'], [points])

    def test_refusals_leave_running_job_unchanged(self):
        sb = self.sandbox()
        task = self.planned(sb, 'refuse', [('ONE', 'implementation', '', []), ('CHECK', 'validation', '', [])])
        sb.sae('dispatch', 'refuse', 'ONE')
        before = sb.state(task)['jobs']['ONE']
        for fields in (['--needs', ''], ['--difficulty', 'normal'], ['--review', '--needs', ''],
                       ['--no-review', '--difficulty', 'hard']):
            error = sb.sae('job', 'edit', 'refuse', 'ONE', *fields, '--reason', 'test', code=1).stderr
            self.assertIn('only --review or --no-review', error)
        self.assertIn('--reason is required', sb.sae('job', 'edit', 'refuse', 'ONE', '--review', code=1).stderr)
        self.assertEqual(sb.state(task)['jobs']['ONE'], before)
        self.assertIn('only writer jobs', sb.sae('job', 'edit', 'refuse', 'CHECK', '--review', '--reason', 'test', code=1).stderr)
        sb.result(task, 'jobs/ONE.result.md', status='failed', summary='failed', validation='fail', changes='none')
        sb.sae('collect', 'refuse', 'ONE')
        self.assertIn('failed', sb.sae('job', 'edit', 'refuse', 'ONE', '--no-review', '--reason', 'test', code=1).stderr)

    def test_pending_flag_changes(self):
        sb = self.sandbox()
        task = sb.new_task('Pending', 'pending')
        sb.sae('job', 'add', 'pending', 'ONE', '--kind', 'implementation')
        for flag, value in (('--review', True), ('--no-review', False)):
            sb.sae('job', 'edit', 'pending', 'ONE', flag, '--reason', 'plan changed')
            self.assertEqual(sb.state(task)['jobs']['ONE']['review'], value)


class ViewerReviewFlagTests(ViewerServerCase, ReviewFlowCase):
    def test_route_uses_cli_and_records_origin(self):
        sb = self.sandbox()
        task = self.planned(sb, 'viewer', [('ONE', 'implementation', '', [])], settings=['review=selected-jobs'])
        view = self.view(sb, 'viewer')
        port, token = view['port'], self.token(view['port'])
        body = {'repo': view['repo'], 'task': task, 'job': 'ONE', 'review': True}
        for value in ('true', None, 1):
            self.assertEqual(self.post(port, 'job-review', {**body, 'review': value}, token)[0], 400)
        self.assertEqual(self.post(port, 'job-review', {**body, 'job': '--review'}, token)[0], 400)
        for running, value in ((False, True), (True, False), (True, True)):
            if running and sb.state(task)['jobs']['ONE']['status'] == 'pending':
                self.run_writer(sb, task, 'viewer', 'ONE', collect=False)
            status, answer, _ = self.post(port, 'job-review', {**body, 'review': value}, token)
            self.assertEqual((status, answer['ok']), (200, True), answer)
            event = [e for e in sb.events(task) if e['type'] == 'job.changed'][-1]
            self.assertEqual((event['by'], event['reason']), ('viewer', 'changed in the viewer'))
        sb.sae('collect', 'viewer', 'ONE')
        self.assertIn('REVIEW-ONE', sb.state(task)['jobs'])
        self.assertEqual(self.post(port, 'job-review', body, token)[0], 422)

    @unittest.skipUnless(shutil.which('node'), 'node runs viewer scripts')
    def test_control_names_states_and_settings_effect(self):
        sb = self.sandbox()
        task = self.planned(sb, 'control', [('ONE', 'implementation', '', [])])
        view = self.view(sb, 'control')
        _, data, _ = request(view['port'], 'GET', f"/api/task?repo={view['repo']}&task={task}")
        script = OVR_JS.replace('({can: canOvr(TASK, ID), body: ovrBody(TASK, ID)})',
                                '({html: reviewFlagControl(TASK, ID), body: jobBody(TASK, ID)})')
        for state in ('pending', 'running', 'done', 'failed'):
            for points, text in ((['selected-jobs'], 'Review selected jobs'), (['all-jobs'], 'all writer jobs'), ([], 'job reviews are off')):
                data['state']['jobs']['ONE']['status'] = state
                data['settings']['review']['points'] = points
                out = run_node(script, 'app.js', 'task-views.js', data=data, args=('ONE',))
                self.assertIn(text, out['html'])
                self.assertIn('Review flag: off', out['body'])
                self.assertEqual('<button' in out['html'], state in ('pending', 'running'))
                if state in ('pending', 'running'):
                    self.assertIn('aria-label="Review flag for ONE"', out['html'])
                    self.assertIn('aria-pressed="false"', out['html'])
