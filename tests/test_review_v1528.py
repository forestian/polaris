"""v1.5.28 전체 검토(보안 · 성능 · 안정성) 반영분 회귀 테스트."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class KubeContextTests(unittest.TestCase):
    """고른 context 가 kubectl · helm 에도 가도록 current-context 를 바꾼 사본을 만든다."""
    KC = """apiVersion: v1
clusters:
- name: dev
  cluster: {server: 'https://dev:6443', certificate-authority: ca/dev.crt}
- name: prod
  cluster: {server: 'https://prod:6443', certificate-authority-data: AAA}
contexts:
- {name: dev, context: {cluster: dev, user: u}}
- {name: prod, context: {cluster: prod, user: u}}
current-context: dev
users:
- {name: u, user: {client-key: keys/u.key, token: t}}
"""

    def test_다른_context_를_고르면_사본의_current_context_가_바뀐다(self):
        import yaml
        from src.k8s import _kubeconfig_with_context
        base = os.path.abspath('kube-base')
        y = yaml.safe_load(_kubeconfig_with_context(self.KC, 'prod', base))
        self.assertEqual(y['current-context'], 'prod')
        # 사본은 임시 폴더에 놓이므로 상대 경로는 원래 폴더 기준 절대 경로로
        self.assertEqual(y['clusters'][0]['cluster']['certificate-authority'],
                         os.path.normpath(os.path.join(base, 'ca/dev.crt')))
        self.assertEqual(y['users'][0]['user']['client-key'], os.path.normpath(os.path.join(base, 'keys/u.key')))

    def test_바꿀_필요가_없거나_못_하면_None(self):
        from src.k8s import _kubeconfig_with_context
        self.assertIsNone(_kubeconfig_with_context(self.KC, 'dev'))      # 이미 current
        self.assertIsNone(_kubeconfig_with_context(self.KC, 'nope'))     # 없는 context
        self.assertIsNone(_kubeconfig_with_context(':: bad', 'prod'))
        self.assertIsNone(_kubeconfig_with_context('', 'prod'))


class KubectlTerminalTests(unittest.TestCase):
    def test_윈도우_경로가_깨지지_않는다(self):
        from src.tools import _parse_kubectl_command as p
        self.assertEqual(p(r'kubectl apply -f C:\work\a.yaml'), ['apply', '-f', r'C:\work\a.yaml'])
        self.assertEqual(p(r'apply -f "C:\my dir\a.yaml"'), ['apply', '-f', r'C:\my dir\a.yaml'])
        self.assertEqual(p('get pods -l "a=b c"'), ['get', 'pods', '-l', 'a=b c'])

    def test_스트리밍_감지(self):
        from src.tools import _parse_kubectl_command as p, _is_kubectl_streaming_args as s
        for c in ('logs x -f', 'logs x --follow=true', 'logs x -fp', 'get pods -w', 'get pods -Aw', 'proxy'):
            self.assertTrue(s(p(c)), c)
        for c in ('logs x --follow=false', 'get pods -owide', 'get pods', 'describe pod x'):
            self.assertFalse(s(p(c)), c)

    def test_내장_명령만_받는다(self):
        from src.api.terminal import TerminalMixin

        class K:
            kubeconfig = 'x.yaml'

        class T(TerminalMixin):
            k8s = K()
            _active_id = ''
        import src.api.terminal as AT
        orig = AT._find_kubectl
        AT._find_kubectl = lambda *a: 'kubectl'
        try:
            r = T().run_kubectl('kubectl evil-plugin --x')
            self.assertIn('내장 명령이 아닙니다', r['error'])
            r = T().run_kubectl('get pods --kubeconfig=C:/other.yaml')
            self.assertIn('--kubeconfig', r['error'])
        finally:
            AT._find_kubectl = orig

    def test_cmd_대체_경로는_특수문자를_거부한다(self):
        from src.tools import _cmd_safe_or_raise
        _cmd_safe_or_raise([r'C:\Program Files (x86)\kubectl.exe', 'exec', '-it'])
        with self.assertRaises(ValueError):
            _cmd_safe_or_raise([r'C:\R&D\kc.yaml'])


class TempKubeconfigSweepTests(unittest.TestCase):
    def test_죽은_프로세스의_파일과_오래된_옛_이름만_지운다(self):
        from src.k8s import sweep_stale_temp_kubeconfigs as sweep
        d = tempfile.mkdtemp(prefix='polaris-kc-sweep-')
        self.addCleanup(lambda: [os.remove(os.path.join(d, f)) for f in os.listdir(d)] and os.rmdir(d))
        names = ['polaris-kc-999999-a.yaml', f'polaris-kc-{os.getpid()}-b.yaml', 'polaris-kc-zzz.yaml']
        for n in names:
            Path(d, n).write_text('x')
        self.assertEqual(sweep(d), 1)
        self.assertEqual(sorted(os.listdir(d)), sorted(names[1:]))
        self.assertEqual(sweep(d, now=time.time() + 13 * 3600), 1)
        self.assertEqual(os.listdir(d), [names[1]], '살아 있는 Polaris 의 파일은 둔다')


class LlmScrubTests(unittest.TestCase):
    def test_흔한_비밀값을_가린다(self):
        from src.reports import llm_scrub
        out = llm_scrub('Authorization: Bearer abcdefghijklmn password=hunter2 token: "zz9" '
                        'https://u:pw@h/x eyJhbGciOiJIUzI1.eyJzdWIiOiIxMjM0.abcdefghijk '
                        'glpat-ABCDEFGHIJKLMNOPQRST error: connection timeout')
        for s in ('abcdefghijklmn', 'hunter2', 'zz9', ':pw@', 'eyJhbGciOiJIUzI1', 'glpat-ABCD'):
            self.assertNotIn(s, out)
        self.assertIn('error: connection timeout', out, '진단에 필요한 내용은 남긴다')
        self.assertIsNone(llm_scrub(None))


class McpAuditTests(unittest.TestCase):
    def test_명령_본문은_해시만(self):
        from src.mcp_server import _redact
        r = _redact({'server': 'web1', 'command': 'mysql -psecret -e "x"', 'password': 'p'})
        self.assertEqual(r['server'], 'web1')
        self.assertEqual(r['password'], '***')
        self.assertNotIn('secret', json.dumps(r))
        self.assertEqual(r['command']['len'], len('mysql -psecret -e "x"'))


class VaultChangePasswordTests(unittest.TestCase):
    def test_열려_있어도_현재_비밀번호를_확인한다(self):
        from src import vault as V
        if not getattr(V, 'HAS_CRYPTO', True):
            self.skipTest('cryptography 없음')
        d = Path(tempfile.mkdtemp(prefix='polaris-vault-'))
        v = V.Vault(d / 'vault.json')
        v.create('right-pw')
        if not v.is_unlocked:
            v.unlock_master('right-pw')
        self.assertTrue(v.is_unlocked)
        with self.assertRaises(V.InvalidMasterPassword):
            v.change_master_password('wrong', 'stolen')
        v.change_master_password('right-pw', 'new-pw')
        v.lock()
        v.unlock_master('new-pw')
        self.assertTrue(v.is_unlocked)


class AtomicWriteTests(unittest.TestCase):
    def test_바꿔_끼우고_임시_파일을_남기지_않는다(self):
        from src.paths import atomic_write_text
        d = Path(tempfile.mkdtemp(prefix='polaris-aw-'))
        p = d / 'a.json'
        atomic_write_text(p, '{"x": 1}')
        atomic_write_text(p, '{"x": 2}')
        self.assertEqual(json.loads(p.read_text(encoding='utf-8')), {'x': 2})
        self.assertEqual(os.listdir(d), ['a.json'])


class KubectlTargetTests(unittest.TestCase):
    def test_플래그로_읽힐_값은_거부(self):
        from src.k8s import _kubectl_target_error as e
        self.assertEqual(e(kind='Deployment', ns='default', name='web-1'), '')
        self.assertTrue(e(kind='pod', ns='default', name='--raw=/x'))
        self.assertTrue(e(kind='-o', ns='default', name='x'))
        self.assertTrue(e(kind='pod', ns='-A', name='x'))


if __name__ == '__main__':
    unittest.main()
