# -*- coding: utf-8 -*-
"""토폴로지 데이터 (v1.4.31) — 앱 단위 화면이 쓰는 값: Ingress 호스트 · 경로 · TLS, Service 포트,
워크로드의 바라는 수 · 이미지, 파드 대기 사유(CrashLoopBackOff …) · 준비 수 · 재시작 수.

쿠버네티스 클라이언트 대신 가짜 객체(SimpleNamespace)로 — 실제 클러스터에 붙지 않는다.
여기서 만든 결과는 ui/src/topologyApps.test.mjs 와 같은 모양이다.
"""
import json
import unittest
from types import SimpleNamespace as N

from src.api.topology import TopologyMixin


def meta(name, ns='shop', labels=None, owners=None, uid=''):
    return N(name=name, namespace=ns, labels=labels or {}, owner_references=owners or [], uid=uid or name)


def owner(kind, name, uid=''):
    return N(kind=kind, name=name, uid=uid or name)


def container(image, env=None, env_from=None):
    return N(image=image, env=env or [], env_from=env_from or [])


def vol(cm=None, secret=None, pvc=None):
    return N(config_map=N(name=cm) if cm else None, secret=N(secret_name=secret) if secret else None,
             persistent_volume_claim=N(claim_name=pvc) if pvc else None)


def tmpl(labels, containers, volumes=None):
    return N(metadata=N(labels=labels), spec=N(containers=containers, volumes=volumes or []))


def deploy(name, labels, replicas, containers, volumes=None, kind_ns='shop'):
    return N(metadata=meta(name, kind_ns), spec=N(selector=N(match_labels=labels), replicas=replicas,
                                                  template=tmpl(labels, containers, volumes)))


def cstatus(ready, restarts=0, waiting=None):
    return N(ready=ready, restart_count=restarts,
             state=N(waiting=N(reason=waiting) if waiting else None))


def pod(name, labels, owner_ref, phase='Running', statuses=None, conditions=None, volumes=None):
    return N(metadata=meta(name, labels=labels, owners=[owner_ref]),
             spec=N(volumes=volumes or [], containers=[container('x')]),
             status=N(phase=phase, container_statuses=statuses or [], conditions=conditions or []))


def rs(name, deploy_name):
    return N(metadata=meta(name, owners=[owner('Deployment', deploy_name)]))


def svc(name, selector, ports, typ='ClusterIP'):
    return N(metadata=meta(name), spec=N(selector=selector, type=typ, ports=ports))


def port(p, target=None, node=None, proto='TCP'):
    return N(port=p, target_port=target, node_port=node, protocol=proto)


def ingress(name, rules, tls=None, cls='nginx'):
    return N(metadata=meta(name), spec=N(ingress_class_name=cls, tls=tls or [], rules=[
        N(host=h, http=N(paths=[N(path=pth, backend=N(service=N(name=s))) for pth, s in paths])) for h, paths in rules]))


SHARED = 'registry-cred'


def fixture():
    web = deploy('web', {'app': 'web'}, 2, [container('nginx:1.27', env_from=[N(config_map_ref=N(name='web-config'), secret_ref=None)])],
                 [vol(secret=SHARED)])
    api = deploy('api', {'app': 'api'}, 2, [container('shop/api:3.1')], [vol(secret=SHARED), vol(pvc='api-data')])
    idle = deploy('old-worker', {'app': 'old'}, 0, [container('shop/worker:1')])
    pods = [
        pod('web-1', {'app': 'web'}, owner('ReplicaSet', 'web-rs'), statuses=[cstatus(True)]),
        pod('web-2', {'app': 'web'}, owner('ReplicaSet', 'web-rs'), statuses=[cstatus(True)]),
        pod('api-1', {'app': 'api'}, owner('ReplicaSet', 'api-rs'), statuses=[cstatus(True, 0)]),
        pod('api-2', {'app': 'api'}, owner('ReplicaSet', 'api-rs'), statuses=[cstatus(False, 7, 'CrashLoopBackOff')]),
        pod('report-1', {'job': 'r1'}, owner('Job', 'report-28811'), phase='Succeeded', statuses=[cstatus(False)]),
    ]
    jobs = [N(metadata=meta('report-28811', owners=[owner('CronJob', 'report', 'cj-uid')]),
              spec=N(selector=None, completions=1, template=tmpl({}, [container('shop/report:2')])),
              status=N(succeeded=1, failed=0, active=0))]
    cron = [N(metadata=meta('report', uid='cj-uid'), spec=N(schedule='0 3 * * *'))]
    k = N(connected=True)
    k.apps = N(list_namespaced_replica_set=lambda ns: N(items=[rs('web-rs', 'web'), rs('api-rs', 'api')]),
               list_namespaced_deployment=lambda ns: N(items=[web, api, idle]),
               list_namespaced_stateful_set=lambda ns: N(items=[]),
               list_namespaced_daemon_set=lambda ns: N(items=[]))
    k.core = N(list_namespaced_pod=lambda ns: N(items=pods),
               list_namespaced_service=lambda ns: N(items=[
                   svc('web', {'app': 'web'}, [port(80, 8080)]),
                   svc('api', {'app': 'api'}, [port(443, 'https'), port(9090, 9090, 30090)], 'NodePort')]),
               list_namespaced_persistent_volume_claim=lambda ns: N(items=[
                   N(metadata=meta('api-data'), spec=N(volume_name='pv-001'), status=N(phase='Bound'))]),
               list_persistent_volume=lambda: N(items=[N(metadata=N(name='pv-001'), status=N(phase='Bound'))]))
    k.batch = N(list_namespaced_cron_job=lambda ns: N(items=cron), list_namespaced_job=lambda ns: N(items=jobs))
    k.net = N(list_namespaced_ingress=lambda ns: N(items=[
        ingress('shop', [('shop.example.com', [('/', 'web'), ('/api', 'api')])], tls=[N(hosts=['shop.example.com'])])]))
    return k


class TopologyDataTests(unittest.TestCase):
    def data(self):
        class API(TopologyMixin):
            pass
        a = API()
        a.k8s = fixture()
        d = a.get_topology_data('shop')
        self.assertTrue(d['ok'], d.get('error'))
        self.assertNotIn('error', d)
        return d

    def test_Ingress_호스트_경로_TLS(self):
        ing = self.data()['ingresses'][0]
        self.assertEqual(ing['rules'], [{'host': 'shop.example.com', 'path': '/', 'svc': 'web'},
                                        {'host': 'shop.example.com', 'path': '/api', 'svc': 'api'}])
        self.assertEqual((ing['tls_hosts'], ing['class']), (['shop.example.com'], 'nginx'))

    def test_Service_포트(self):
        s = {x['name']: x for x in self.data()['services']}
        self.assertEqual(s['web']['ports'], ['80→8080'])
        self.assertEqual(s['api']['ports'], ['443→https', '9090 (노드 30090)'])

    def test_워크로드_파드_사유_재시작_바라는_수(self):
        w = {x['name']: x for x in self.data()['workloads']}
        self.assertEqual((w['web']['total'], w['web']['ready'], w['web']['waiting']), (2, 2, []))
        self.assertEqual((w['api']['total'], w['api']['running'], w['api']['ready']), (2, 2, 1),
                         'Running 이어도 준비 안 된 파드는 준비 수에서 뺀다')
        self.assertEqual((w['api']['waiting'], w['api']['restarts']), (['CrashLoopBackOff'], 7))
        self.assertEqual((w['old-worker']['replicas'], w['old-worker']['total']), (0, 0))
        self.assertEqual(w['web']['images'], ['nginx:1.27'])
        self.assertEqual(w['report-28811']['ready'], 1, '끝난(Succeeded) Job 파드는 준비로 센다')

    def test_대기_중인_파드의_스케줄_실패도_사유로(self):
        k = fixture()
        k.core.list_namespaced_pod = lambda ns: N(items=[pod('web-1', {'app': 'web'}, owner('ReplicaSet', 'web-rs'), phase='Pending',
                                                                conditions=[N(type='PodScheduled', status='False', reason='Unschedulable')])])

        class API(TopologyMixin):
            pass
        a = API()
        a.k8s = k
        w = {x['name']: x for x in a.get_topology_data('shop')['workloads']}
        self.assertEqual(w['web']['waiting'], ['Unschedulable'])

    def test_화면_테스트용_결과를_남긴다(self):
        # ui/src/topologyApps.test.mjs 가 같은 모양을 쓴다 — 백엔드가 바뀌면 여기서 먼저 깨진다
        d = self.data()
        keys = {'ingresses', 'services', 'cronjobs', 'workloads', 'config_nodes', 'pv_nodes', 'edges'}
        self.assertTrue(keys <= set(d))
        json.dumps(d)                     # 화면으로 넘어갈 수 있어야 한다(직렬화)


if __name__ == '__main__':
    unittest.main()
