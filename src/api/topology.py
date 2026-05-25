"""TopologyMixin — get_topology_data (그래프 노드/에지 빌더).
"""
from src.topology import (
    _topo_vol_refs, _topo_env_refs, _topo_sel_match,
    _topo_pod_workload_owner, _topo_cronjob_node,
    _topo_job_status, _topo_job_workload_node,
)


class TopologyMixin:
    def get_topology_data(self, ns: str = ''):
        """토폴로지 그래프용 관계 데이터 수집."""
        k = self.k8s
        if not k.connected:
            return {'ok': False, 'error': '연결되지 않음'}

        # all-ns 여부
        an = not ns or ns.strip() == ''

        out = {
            'ok': True,
            'ingresses': [], 'services': [],
            'cronjobs': [], 'workloads': [], 'config_nodes': [], 'pv_nodes': [],
            'edges': [],
        }

        # 엣지 중복 방지용 집합
        edge_set = set()

        def add_edge(frm, to):
            key = (frm, to)
            if key not in edge_set:
                edge_set.add(key)
                out['edges'].append({'from': frm, 'to': to})

        try:
            # ── 1. ReplicaSet → Deployment 맵 ──
            try:
                rss = (k.apps.list_replica_set_for_all_namespaces().items if an
                       else k.apps.list_namespaced_replica_set(ns).items)
            except Exception:
                rss = []
            rs_deploy = {}  # (ns, rs_name) → deploy_name
            for rs in rss:
                for ref in (rs.metadata.owner_references or []):
                    if ref.kind == 'Deployment':
                        rs_deploy[(rs.metadata.namespace, rs.metadata.name)] = ref.name
                        break

            # ── 2. Pods ──
            try:
                pods_raw = (k.core.list_pod_for_all_namespaces().items if an
                            else k.core.list_namespaced_pod(ns).items)
            except Exception:
                pods_raw = []

            pod_data = []
            for p in pods_raw:
                ok_kind, ok_name = '', ''
                for ref in (p.metadata.owner_references or []):
                    if ref.kind in ('ReplicaSet', 'StatefulSet', 'DaemonSet', 'Job'):
                        ok_kind, ok_name = _topo_pod_workload_owner(
                            ref.kind, ref.name, rs_deploy, p.metadata.namespace)
                        break

                crefs = _topo_vol_refs(p.spec.volumes)
                for c in (p.spec.containers or []):
                    crefs.extend(_topo_env_refs(c.env, c.env_from))

                status = (p.status.phase or 'Unknown') if p.status else 'Unknown'
                pod_data.append({
                    'name': p.metadata.name,
                    'ns':   p.metadata.namespace,
                    'labels': p.metadata.labels or {},
                    'ok': ok_kind,
                    'on': ok_name,
                    'crefs': list(dict.fromkeys(crefs)),   # dedup preserve order
                    'status': status,
                })

            # ── 3. Workloads ──
            wl_list = []

            def _collect_wl(items, kind):
                for w in items:
                    sel = {}
                    if w.spec.selector and w.spec.selector.match_labels:
                        sel = dict(w.spec.selector.match_labels)
                    tmpl_vols = []
                    try:
                        tmpl_vols = w.spec.template.spec.volumes or []
                    except Exception:
                        pass
                    crefs = _topo_vol_refs(tmpl_vols)
                    # env refs from pod template containers
                    try:
                        for c in (w.spec.template.spec.containers or []):
                            crefs.extend(_topo_env_refs(c.env, c.env_from))
                    except Exception:
                        pass
                    wl_id = f"wl/{w.metadata.namespace}/{kind}/{w.metadata.name}"
                    wl_list.append({
                        'kind': kind, 'name': w.metadata.name,
                        'ns': w.metadata.namespace,
                        'sel': sel, 'crefs': list(dict.fromkeys(crefs)),
                        'id': wl_id,
                    })

            try:
                _collect_wl(k.apps.list_deployment_for_all_namespaces().items if an
                            else k.apps.list_namespaced_deployment(ns).items, 'Deployment')
            except Exception:
                pass
            try:
                _collect_wl(k.apps.list_stateful_set_for_all_namespaces().items if an
                            else k.apps.list_namespaced_stateful_set(ns).items, 'StatefulSet')
            except Exception:
                pass
            try:
                _collect_wl(k.apps.list_daemon_set_for_all_namespaces().items if an
                            else k.apps.list_namespaced_daemon_set(ns).items, 'DaemonSet')
            except Exception:
                pass

            cronjob_uid_to_id = {}
            try:
                cjs_raw = (k.batch.list_cron_job_for_all_namespaces().items if an
                           else k.batch.list_namespaced_cron_job(ns).items)
            except Exception:
                cjs_raw = []
            for cj in cjs_raw:
                node = _topo_cronjob_node(
                    cj.metadata.namespace,
                    cj.metadata.name,
                    cj.metadata.uid or '',
                    (cj.spec.schedule or '') if cj.spec else '',
                )
                out['cronjobs'].append(node)
                if node['uid']:
                    cronjob_uid_to_id[node['uid']] = node['id']

            try:
                jobs_raw = (k.batch.list_job_for_all_namespaces().items if an
                            else k.batch.list_namespaced_job(ns).items)
            except Exception:
                jobs_raw = []
            for job in jobs_raw:
                owner_uid = ''
                for ref in (job.metadata.owner_references or []):
                    if ref.kind == 'CronJob':
                        owner_uid = ref.uid or ''
                        break
                sel = {}
                if job.spec and job.spec.selector and job.spec.selector.match_labels:
                    sel = dict(job.spec.selector.match_labels)
                tmpl_vols = []
                try:
                    tmpl_vols = job.spec.template.spec.volumes or []
                except Exception:
                    pass
                crefs = _topo_vol_refs(tmpl_vols)
                try:
                    for c in (job.spec.template.spec.containers or []):
                        crefs.extend(_topo_env_refs(c.env, c.env_from))
                except Exception:
                    pass
                node = _topo_job_workload_node(
                    job.metadata.namespace,
                    job.metadata.name,
                    job.metadata.uid or '',
                    owner_uid,
                    succeeded=(job.status.succeeded or 0) if job.status else 0,
                    failed=(job.status.failed or 0) if job.status else 0,
                    active=(job.status.active or 0) if job.status else 0,
                    completions=(job.spec.completions or 0) if job.spec else 0,
                    sel=sel,
                    crefs=crefs,
                )
                wl_list.append(node)
                cj_id = cronjob_uid_to_id.get(owner_uid)
                if cj_id:
                    add_edge(cj_id, node['id'])

            # 파드 상태 집계
            pod_status = {}  # wl_id → {total, running}
            for p in pod_data:
                if p['ok'] and p['on']:
                    wid = f"wl/{p['ns']}/{p['ok']}/{p['on']}"
                    if wid not in pod_status:
                        pod_status[wid] = {'total': 0, 'running': 0}
                    pod_status[wid]['total'] += 1
                    if p['status'] in ('Running', 'Succeeded'):
                        pod_status[wid]['running'] += 1

            for w in wl_list:
                ps = pod_status.get(w['id'], {'total': 0, 'running': 0})
                w['total']   = ps['total']
                w['running'] = ps['running']

            out['workloads'] = wl_list

            # ── 4. Services ──
            try:
                svcs_raw = (k.core.list_service_for_all_namespaces().items if an
                            else k.core.list_namespaced_service(ns).items)
            except Exception:
                svcs_raw = []

            svcs = []
            for s in svcs_raw:
                svcs.append({
                    'name': s.metadata.name,
                    'ns':   s.metadata.namespace,
                    'sel':  dict(s.spec.selector) if s.spec.selector else {},
                    'type': s.spec.type or 'ClusterIP',
                    'id':   f"svc/{s.metadata.namespace}/{s.metadata.name}",
                })

            # Service → Workload edges (pod label matching)
            connected_svcs = set()
            for svc in svcs:
                if not svc['sel']:
                    continue
                for p in pod_data:
                    if p['ns'] != svc['ns']:
                        continue
                    if _topo_sel_match(svc['sel'], p['labels']):
                        if p['ok'] and p['on']:
                            wid = f"wl/{p['ns']}/{p['ok']}/{p['on']}"
                            add_edge(svc['id'], wid)
                            connected_svcs.add(svc['id'])

            # ── 5. Ingresses ──
            try:
                ings_raw = (k.net.list_ingress_for_all_namespaces().items if an
                            else k.net.list_namespaced_ingress(ns).items)
            except Exception:
                ings_raw = []

            for ing in ings_raw:
                ing_id = f"ing/{ing.metadata.namespace}/{ing.metadata.name}"
                svc_refs = []
                for rule in (ing.spec.rules or []):
                    if rule.http:
                        for path in (rule.http.paths or []):
                            b = path.backend
                            sn = None
                            if b:
                                if getattr(b, 'service', None):
                                    sn = b.service.name
                                elif getattr(b, 'service_name', None):
                                    sn = b.service_name
                            if sn and sn not in svc_refs:
                                svc_refs.append(sn)

                if svc_refs:
                    out['ingresses'].append({
                        'name': ing.metadata.name, 'ns': ing.metadata.namespace,
                        'id': ing_id, 'svc_refs': svc_refs,
                    })
                    for sr in svc_refs:
                        sid = f"svc/{ing.metadata.namespace}/{sr}"
                        add_edge(ing_id, sid)
                        connected_svcs.add(sid)

            # 연결된 서비스만 포함
            out['services'] = [s for s in svcs if s['id'] in connected_svcs]

            # ── 6. Config / Storage refs ──
            cfg_map = {}  # cfg_id → {type, name, ns, id}

            def _add_cfg(wid, crefs, wl_ns):
                for rtype, rname in crefs:
                    cfg_id = f"{rtype}/{wl_ns}/{rname}"
                    if cfg_id not in cfg_map:
                        cfg_map[cfg_id] = {'type': rtype, 'name': rname, 'ns': wl_ns, 'id': cfg_id}
                    add_edge(wid, cfg_id)

            for w in wl_list:
                _add_cfg(w['id'], w['crefs'], w['ns'])

            # 파드 직접 참조 (워크로드에 없는 경우 보완)
            for p in pod_data:
                if p['ok'] and p['on']:
                    wid = f"wl/{p['ns']}/{p['ok']}/{p['on']}"
                    _add_cfg(wid, p['crefs'], p['ns'])

            out['config_nodes'] = list(cfg_map.values())

            # ── 7. PVC → PV ──
            pvc_names = {v['name'] for v in cfg_map.values() if v['type'] == 'pvc'}
            pv_map = {}
            if pvc_names:
                try:
                    pvcs_raw = (k.core.list_persistent_volume_claim_for_all_namespaces().items if an
                                else k.core.list_namespaced_persistent_volume_claim(ns).items)
                    for pvc in pvcs_raw:
                        if pvc.metadata.name not in pvc_names:
                            continue
                        pv_name = pvc.spec.volume_name or ''
                        if pv_name:
                            pv_id  = f"pv//{pv_name}"
                            pvc_id = f"pvc/{pvc.metadata.namespace}/{pvc.metadata.name}"
                            pv_map[pv_id] = {
                                'type': 'pv', 'name': pv_name, 'ns': '', 'id': pv_id,
                                'status': (pvc.status.phase or '') if pvc.status else '',
                            }
                            add_edge(pvc_id, pv_id)
                except Exception:
                    pass

                if pv_map:
                    try:
                        for pv in k.core.list_persistent_volume().items:
                            pid = f"pv//{pv.metadata.name}"
                            if pid in pv_map:
                                pv_map[pid]['status'] = (pv.status.phase or '') if pv.status else ''
                    except Exception:
                        pass

            out['pv_nodes'] = list(pv_map.values())

        except Exception as e:
            import traceback
            out['error'] = str(e) + '\n' + traceback.format_exc()[:400]

        return out


