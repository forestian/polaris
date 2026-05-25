"""토폴로지 그래프 빌더 헬퍼.

PolarisAPI.get_topology_data() 가 호출하는 graph node 생성 헬퍼.
파드 → 워크로드 → 컨피그/시크릿/PVC 등 참조 관계를 노드/에지로 변환.
"""

def _topo_vol_refs(volumes) -> list:
    """볼륨 목록에서 (type, name) 참조 추출."""
    refs = []
    skip_prefixes = ('kube-', 'default-token', 'kube-api-access-')
    for v in (volumes or []):
        if v.config_map and v.config_map.name:
            refs.append(('configmap', v.config_map.name))
        elif v.secret and v.secret.secret_name:
            if not any(v.secret.secret_name.startswith(p) for p in skip_prefixes):
                refs.append(('secret', v.secret.secret_name))
        elif v.persistent_volume_claim and v.persistent_volume_claim.claim_name:
            refs.append(('pvc', v.persistent_volume_claim.claim_name))
    return refs


def _topo_env_refs(env_list, env_from_list) -> list:
    """컨테이너 env/envFrom에서 (type, name) 참조 추출."""
    refs = []
    for env in (env_list or []):
        vf = env.value_from
        if not vf:
            continue
        if vf.config_map_key_ref and vf.config_map_key_ref.name:
            refs.append(('configmap', vf.config_map_key_ref.name))
        elif vf.secret_key_ref and vf.secret_key_ref.name:
            refs.append(('secret', vf.secret_key_ref.name))
    for ef in (env_from_list or []):
        if ef.config_map_ref and ef.config_map_ref.name:
            refs.append(('configmap', ef.config_map_ref.name))
        elif ef.secret_ref and ef.secret_ref.name:
            refs.append(('secret', ef.secret_ref.name))
    return refs


def _topo_sel_match(selector: dict, labels: dict) -> bool:
    """셀렉터가 레이블과 일치하는지 확인."""
    if not selector:
        return False
    return all(labels.get(k) == v for k, v in selector.items())


def _topo_pod_workload_owner(owner_kind: str, owner_name: str, rs_deploy: dict, owner_ns: str = '') -> tuple[str, str]:
    """Pod ownerReference를 토폴로지 워크로드 kind/name으로 변환."""
    owner_kind = str(owner_kind or '')
    owner_name = str(owner_name or '')
    if owner_kind == 'ReplicaSet':
        deploy = rs_deploy.get((owner_ns, owner_name)) or rs_deploy.get(owner_name)
        if deploy:
            return 'Deployment', deploy
    if owner_kind in ('StatefulSet', 'DaemonSet', 'Job'):
        return owner_kind, owner_name
    return '', ''


def _topo_cronjob_node(ns: str, name: str, uid: str = '', schedule: str = '') -> dict:
    """React 토폴로지용 CronJob 노드."""
    return {
        'id': f'cj/{ns}/{name}',
        'kind': 'CronJob',
        'name': name,
        'ns': ns,
        'uid': uid or '',
        'schedule': schedule or '',
    }


def _topo_job_status(succeeded: int = 0, failed: int = 0,
                     active: int = 0, completions: int = 0) -> str:
    if failed:
        return 'Failed'
    if active:
        return 'Active'
    if succeeded and (not completions or succeeded >= completions):
        return 'Complete'
    return 'Pending'


def _topo_job_workload_node(ns: str, name: str, uid: str = '', owner_uid: str = '',
                            succeeded: int = 0, failed: int = 0,
                            active: int = 0, completions: int = 0,
                            sel: dict | None = None, crefs: list | None = None) -> dict:
    """React 토폴로지의 Workload 컬럼에 표시할 Job 노드."""
    return {
        'id': f'wl/{ns}/Job/{name}',
        'kind': 'Job',
        'name': name,
        'ns': ns,
        'uid': uid or '',
        'owner_uid': owner_uid or '',
        'succeeded': int(succeeded or 0),
        'failed': int(failed or 0),
        'active': int(active or 0),
        'completions': int(completions or 0),
        'status': _topo_job_status(succeeded, failed, active, completions),
        'sel': sel or {},
        'crefs': list(dict.fromkeys(crefs or [])),
    }


