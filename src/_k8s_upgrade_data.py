# -*- coding: utf-8 -*-
"""쿠버네티스 업그레이드 사전 점검 데이터 — scripts/gen_k8supgrade.py 가 공식 출처에서 만든다(손으로 고치지 않는다)."""
DATA = {
 "addons": {
  "Argo CD": {
   "cni": False,
   "image": "argoproj/argocd:v?(\\d+\\.\\d+)",
   "key": "minor",
   "url": "https://argo-cd.readthedocs.io/en/stable/operator-manual/installation/#tested-versions",
   "versions": {
    "2.10": {
     "k8s": [
      25,
      26,
      27,
      28
     ],
     "max": 28,
     "min": 25
    },
    "2.11": {
     "k8s": [
      25,
      26,
      27,
      28,
      29
     ],
     "max": 29,
     "min": 25
    },
    "2.12": {
     "k8s": [
      26,
      27,
      28,
      29
     ],
     "max": 29,
     "min": 26
    },
    "2.13": {
     "k8s": [
      27,
      28,
      29,
      30
     ],
     "max": 30,
     "min": 27
    },
    "2.14": {
     "k8s": [
      28,
      29,
      30,
      31
     ],
     "max": 31,
     "min": 28
    },
    "2.6": {
     "k8s": [
      22,
      23,
      24
     ],
     "max": 24,
     "min": 22
    },
    "2.7": {
     "k8s": [
      23,
      24,
      25,
      26
     ],
     "max": 26,
     "min": 23
    },
    "2.8": {
     "k8s": [
      24,
      25,
      26,
      27
     ],
     "max": 27,
     "min": 24
    },
    "2.9": {
     "k8s": [
      25,
      26,
      27,
      28
     ],
     "max": 28,
     "min": 25
    },
    "3.0": {
     "k8s": [
      29,
      30,
      31,
      32
     ],
     "max": 32,
     "min": 29
    },
    "3.1": {
     "k8s": [
      31,
      32,
      33,
      34
     ],
     "max": 34,
     "min": 31
    },
    "3.2": {
     "k8s": [
      31,
      32,
      33,
      34
     ],
     "max": 34,
     "min": 31
    },
    "3.3": {
     "k8s": [
      32,
      33,
      34,
      35
     ],
     "max": 35,
     "min": 32
    },
    "3.4": {
     "k8s": [
      32,
      33,
      34,
      35
     ],
     "max": 35,
     "min": 32
    },
    "3.5": {
     "k8s": [
      33,
      34,
      35,
      36
     ],
     "max": 36,
     "min": 33
    },
    "3.6": {
     "k8s": [
      34,
      35,
      36,
      37
     ],
     "max": 37,
     "min": 34
    }
   }
  },
  "Calico": {
   "cni": True,
   "image": "calico(?:-|/)node:v?(\\d+\\.\\d+)",
   "key": "minor",
   "url": "https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements",
   "versions": {
    "3.31": {
     "k8s": [
      32,
      33,
      34,
      35
     ],
     "max": 35,
     "min": 32
    },
    "3.32": {
     "k8s": [
      34,
      35,
      36
     ],
     "max": 36,
     "min": 34
    },
    "3.33": {
     "k8s": [
      35,
      36,
      37
     ],
     "max": 37,
     "min": 35
    }
   }
  },
  "Cilium": {
   "cni": True,
   "image": "cilium(?:-cilium)?:v?(\\d+\\.\\d+)",
   "key": "minor",
   "url": "https://docs.cilium.io/en/stable/network/kubernetes/compatibility/",
   "versions": {
    "1.13": {
     "k8s": [
      16,
      17,
      18,
      19,
      20,
      21,
      22,
      23,
      24,
      25,
      26
     ],
     "max": 26,
     "min": 16
    },
    "1.14": {
     "k8s": [
      19,
      20,
      21,
      22,
      23,
      24,
      25,
      26,
      27
     ],
     "max": 27,
     "min": 19
    },
    "1.15": {
     "k8s": [
      26,
      27,
      28,
      29
     ],
     "max": 29,
     "min": 26
    },
    "1.16": {
     "k8s": [
      27,
      28,
      29,
      30
     ],
     "max": 30,
     "min": 27
    },
    "1.17": {
     "k8s": [
      29,
      30,
      31,
      32
     ],
     "max": 32,
     "min": 29
    },
    "1.18": {
     "k8s": [
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 30
    },
    "1.19": {
     "k8s": [
      32,
      33,
      34,
      35
     ],
     "max": 35,
     "min": 32
    },
    "1.20": {
     "k8s": [
      33,
      34,
      35,
      36
     ],
     "max": 36,
     "min": 33
    }
   }
  },
  "Istio": {
   "cni": False,
   "image": "istio/pilot:v?(\\d+\\.\\d+)",
   "key": "minor",
   "url": "https://istio.io/latest/docs/releases/supported-releases/",
   "versions": {
    "1.13": {
     "k8s": [
      20,
      21,
      22,
      23
     ],
     "max": 23,
     "min": 20
    },
    "1.14": {
     "k8s": [
      21,
      22,
      23,
      24
     ],
     "max": 24,
     "min": 21
    },
    "1.15": {
     "k8s": [
      22,
      23,
      24,
      25
     ],
     "max": 25,
     "min": 22
    },
    "1.16": {
     "k8s": [
      22,
      23,
      24,
      25
     ],
     "max": 25,
     "min": 22
    },
    "1.17": {
     "k8s": [
      23,
      24,
      25,
      26
     ],
     "max": 26,
     "min": 23
    },
    "1.18": {
     "k8s": [
      24,
      25,
      26,
      27
     ],
     "max": 27,
     "min": 24
    },
    "1.19": {
     "k8s": [
      25,
      26,
      27,
      28
     ],
     "max": 28,
     "min": 25
    },
    "1.20": {
     "k8s": [
      25,
      26,
      27,
      28,
      29
     ],
     "max": 29,
     "min": 25
    },
    "1.21": {
     "k8s": [
      26,
      27,
      28,
      29
     ],
     "max": 29,
     "min": 26
    },
    "1.22": {
     "k8s": [
      27,
      28,
      29,
      30
     ],
     "max": 30,
     "min": 27
    },
    "1.23": {
     "k8s": [
      27,
      28,
      29,
      30
     ],
     "max": 30,
     "min": 27
    },
    "1.24": {
     "k8s": [
      28,
      29,
      30,
      31
     ],
     "max": 31,
     "min": 28
    },
    "1.25": {
     "k8s": [
      29,
      30,
      31,
      32
     ],
     "max": 32,
     "min": 29
    },
    "1.26": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.27": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.28": {
     "k8s": [
      30,
      31,
      32,
      33,
      34
     ],
     "max": 34,
     "min": 30
    },
    "1.29": {
     "k8s": [
      31,
      32,
      33,
      34,
      35
     ],
     "max": 35,
     "min": 31
    },
    "1.30": {
     "k8s": [
      32,
      33,
      34,
      35,
      36
     ],
     "max": 36,
     "min": 32
    },
    "1.31": {
     "k8s": [
      32,
      33,
      34,
      35,
      36,
      37
     ],
     "max": 37,
     "min": 32
    },
    "1.32": {
     "k8s": [
      33,
      34,
      35,
      36,
      37
     ],
     "max": 37,
     "min": 33
    }
   }
  },
  "Velero": {
   "cni": False,
   "image": "velero/velero:v?(\\d+\\.\\d+)",
   "key": "minor",
   "url": "https://github.com/vmware-tanzu/velero#velero-compatibility-matrix",
   "versions": {
    "1.15": {
     "k8s": None,
     "max": None,
     "min": 18,
     "tested": [
      28,
      29,
      30,
      31
     ]
    },
    "1.16": {
     "k8s": None,
     "max": None,
     "min": 18,
     "tested": [
      31,
      32,
      33
     ]
    },
    "1.17": {
     "k8s": None,
     "max": None,
     "min": 18,
     "tested": [
      31,
      32,
      33,
      34
     ]
    },
    "1.18": {
     "k8s": None,
     "max": None,
     "min": 18,
     "tested": [
      33,
      34,
      35
     ]
    },
    "1.19": {
     "k8s": None,
     "max": None,
     "min": 18,
     "tested": [
      36,
      37
     ]
    }
   }
  },
  "cert-manager": {
   "cni": False,
   "image": "cert-manager-controller:v?(\\d+\\.\\d+)",
   "key": "minor",
   "url": "https://cert-manager.io/docs/releases/",
   "versions": {
    "0.11": {
     "k8s": [
      9,
      10,
      11,
      12,
      13,
      14,
      15,
      16,
      17,
      18,
      19,
      20,
      21
     ],
     "max": 21,
     "min": 9
    },
    "0.12": {
     "k8s": [
      11,
      12,
      13,
      14,
      15,
      16,
      17,
      18,
      19,
      20,
      21
     ],
     "max": 21,
     "min": 11
    },
    "0.13": {
     "k8s": [
      11,
      12,
      13,
      14,
      15,
      16,
      17,
      18,
      19,
      20,
      21
     ],
     "max": 21,
     "min": 11
    },
    "0.14": {
     "k8s": [
      11,
      12,
      13,
      14,
      15,
      16,
      17,
      18,
      19,
      20,
      21
     ],
     "max": 21,
     "min": 11
    },
    "0.15": {
     "k8s": [
      11,
      12,
      13,
      14,
      15,
      16,
      17,
      18,
      19,
      20,
      21
     ],
     "max": 21,
     "min": 11
    },
    "0.16": {
     "k8s": [
      11,
      12,
      13,
      14,
      15,
      16,
      17,
      18,
      19,
      20,
      21
     ],
     "max": 21,
     "min": 11
    },
    "1.0": {
     "k8s": [
      11,
      12,
      13,
      14,
      15,
      16,
      17,
      18,
      19,
      20,
      21
     ],
     "max": 21,
     "min": 11
    },
    "1.1": {
     "k8s": [
      11,
      12,
      13,
      14,
      15,
      16,
      17,
      18,
      19,
      20,
      21
     ],
     "max": 21,
     "min": 11
    },
    "1.10": {
     "k8s": [
      20,
      21,
      22,
      23,
      24,
      25,
      26
     ],
     "max": 26,
     "min": 20
    },
    "1.11": {
     "k8s": [
      21,
      22,
      23,
      24,
      25,
      26,
      27
     ],
     "max": 27,
     "min": 21
    },
    "1.12": {
     "k8s": [
      22,
      23,
      24,
      25,
      26,
      27,
      28,
      29,
      30,
      31,
      32
     ],
     "max": 32,
     "min": 22
    },
    "1.13": {
     "k8s": [
      21,
      22,
      23,
      24,
      25,
      26,
      27
     ],
     "max": 27,
     "min": 21
    },
    "1.14": {
     "k8s": [
      24,
      25,
      26,
      27,
      28,
      29,
      30,
      31
     ],
     "max": 31,
     "min": 24
    },
    "1.15": {
     "k8s": [
      25,
      26,
      27,
      28,
      29,
      30,
      31,
      32
     ],
     "max": 32,
     "min": 25
    },
    "1.16": {
     "k8s": [
      25,
      26,
      27,
      28,
      29,
      30,
      31,
      32
     ],
     "max": 32,
     "min": 25
    },
    "1.17": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.18": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.19": {
     "k8s": [
      31,
      32,
      33,
      34,
      35
     ],
     "max": 35,
     "min": 31
    },
    "1.2": {
     "k8s": [
      16,
      17,
      18,
      19,
      20,
      21
     ],
     "max": 21,
     "min": 16
    },
    "1.20": {
     "k8s": [
      32,
      33,
      34,
      35
     ],
     "max": 35,
     "min": 32
    },
    "1.21": {
     "k8s": [
      33,
      34,
      35,
      36
     ],
     "max": 36,
     "min": 33
    },
    "1.3": {
     "k8s": [
      16,
      17,
      18,
      19,
      20,
      21
     ],
     "max": 21,
     "min": 16
    },
    "1.4": {
     "k8s": [
      16,
      17,
      18,
      19,
      20,
      21
     ],
     "max": 21,
     "min": 16
    },
    "1.5": {
     "k8s": [
      16,
      17,
      18,
      19,
      20,
      21,
      22
     ],
     "max": 22,
     "min": 16
    },
    "1.6": {
     "k8s": [
      17,
      18,
      19,
      20,
      21,
      22
     ],
     "max": 22,
     "min": 17
    },
    "1.7": {
     "k8s": [
      18,
      19,
      20,
      21,
      22,
      23
     ],
     "max": 23,
     "min": 18
    },
    "1.8": {
     "k8s": [
      19,
      20,
      21,
      22,
      23,
      24
     ],
     "max": 24,
     "min": 19
    },
    "1.9": {
     "k8s": [
      20,
      21,
      22,
      23,
      24
     ],
     "max": 24,
     "min": 20
    }
   }
  },
  "ingress-nginx": {
   "cni": False,
   "image": "ingress-nginx[^:@]*controller[^:@]*:v?(\\d+\\.\\d+\\.\\d+)",
   "key": "exact",
   "url": "https://github.com/kubernetes/ingress-nginx#supported-versions-table",
   "versions": {
    "1.13.0": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.13.1": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.13.2": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.13.3": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.13.4": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.13.5": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.13.6": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.13.7": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.13.8": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.13.9": {
     "k8s": [
      29,
      30,
      31,
      32,
      33
     ],
     "max": 33,
     "min": 29
    },
    "1.14.0": {
     "k8s": [
      30,
      31,
      32,
      33,
      34
     ],
     "max": 34,
     "min": 30
    },
    "1.14.1": {
     "k8s": [
      30,
      31,
      32,
      33,
      34
     ],
     "max": 34,
     "min": 30
    },
    "1.14.2": {
     "k8s": [
      30,
      31,
      32,
      33,
      34
     ],
     "max": 34,
     "min": 30
    },
    "1.14.3": {
     "k8s": [
      30,
      31,
      32,
      33,
      34
     ],
     "max": 34,
     "min": 30
    },
    "1.14.4": {
     "k8s": [
      30,
      31,
      32,
      33,
      34
     ],
     "max": 34,
     "min": 30
    },
    "1.14.5": {
     "k8s": [
      30,
      31,
      32,
      33,
      34
     ],
     "max": 34,
     "min": 30
    },
    "1.15.0": {
     "k8s": [
      31,
      32,
      33,
      34,
      35
     ],
     "max": 35,
     "min": 31
    },
    "1.15.1": {
     "k8s": [
      31,
      32,
      33,
      34,
      35
     ],
     "max": 35,
     "min": 31
    }
   }
  },
  "metrics-server": {
   "cni": False,
   "image": "metrics-server:v?(\\d+\\.\\d+)",
   "key": "minor",
   "url": "https://github.com/kubernetes-sigs/metrics-server#compatibility-matrix",
   "versions": {
    "0.3": {
     "k8s": None,
     "max": 21,
     "min": 8
    },
    "0.4": {
     "k8s": None,
     "max": None,
     "min": 8
    },
    "0.5": {
     "k8s": None,
     "max": None,
     "min": 8
    },
    "0.6": {
     "k8s": None,
     "max": None,
     "min": 25
    },
    "0.7": {
     "k8s": None,
     "max": None,
     "min": 27
    },
    "0.8": {
     "k8s": None,
     "max": None,
     "min": 31
    },
    "0.9": {
     "k8s": None,
     "max": None,
     "min": 34
    }
   }
  }
 },
 "apps": {
  "longhorn": {
   "releases": {
    "0.2.0": {
     "date": "2018-03-23",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "0.3.0": {
     "date": "2018-08-23",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "0.3.1": {
     "date": "2018-09-18",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "0.3.2": {
     "date": "2018-11-10",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "0.3.3": {
     "date": "2019-01-15",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "0.4.0": {
     "date": "2019-02-22",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "0.4.1": {
     "date": "2019-03-23",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "0.5.0": {
     "date": "2019-05-18",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "0.6.0": {
     "date": "2019-09-21",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "0.6.1": {
     "date": "2019-09-23",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "0.6.2": {
     "date": "2019-10-08",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "0.7.0": {
     "date": "2019-11-15",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "0.8.0": {
     "date": "2020-03-11",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "0.8.1": {
     "date": "2020-04-29",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.0.0": {
     "date": "2020-05-30",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.0.1": {
     "date": "2020-07-21",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.0.2": {
     "date": "2020-08-14",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.1.0": {
     "date": "2020-12-18",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.1.1": {
     "date": "2021-04-23",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": [
      {
       "issue": 2048,
       "kind": "feature",
       "title": "Option of creating RWX volume from the Longhorn UI ("
      },
      {
       "issue": 2056,
       "kind": "bug",
       "title": "The 'Attached to' column needs to incorporate all pods history for RWX volume ("
      },
      {
       "issue": 2058,
       "kind": "feature",
       "title": "Handle NFS client info for the RWX feature ("
      },
      {
       "issue": 2059,
       "kind": "feature",
       "title": "The detach message should include the RWX volume behavior ("
      },
      {
       "issue": 2418,
       "kind": "feature",
       "title": "rwx shared directory should be rw accessible when running as non-root user ("
      },
      {
       "issue": 2316,
       "kind": "bug",
       "title": "RWX volume fails to attach to a pod ("
      },
      {
       "issue": 2389,
       "kind": "bug",
       "title": "UI - 'Expand volume' option is enabled for attached RWX volume. ("
      },
      {
       "issue": 2411,
       "kind": "bug",
       "title": "Attach option available for an already attached RWX volume. ("
      },
      {
       "issue": 2420,
       "kind": "bug",
       "title": "Unable to attach RWX to a node using Longhorn UI ("
      }
     ]
    },
    "1.1.2": {
     "date": "2021-07-07",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.1.3": {
     "date": "2021-12-17",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.10.0": {
     "date": "2025-09-25",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": [
      {
       "issue": 11158,
       "kind": "bug",
       "title": "CSI Plugin restart triggers unintended restart of migratable RWX volume workloads"
      }
     ]
    },
    "1.10.1": {
     "date": "2025-11-12",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": []
    },
    "1.10.2": {
     "date": "2026-01-28",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": []
    },
    "1.11.0": {
     "date": "2026-01-29",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": [
      {
       "issue": 10269,
       "kind": "feature",
       "title": "Support extra network interface (not only storage network) on the share manager pod"
      },
      {
       "issue": 12244,
       "kind": "bug",
       "title": "Inherit namespace for longhorn-share-manager in FastFailover mode"
      },
      {
       "issue": 11907,
       "kind": "bug",
       "title": "RWX volume causes process uninterruptible sleep"
      },
      {
       "issue": 12226,
       "kind": "bug",
       "title": "RWX volume becomes unavailable after drain node"
      }
     ]
    },
    "1.11.1": {
     "date": "2026-03-13",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": []
    },
    "1.11.2": {
     "date": "2026-05-05",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": []
    },
    "1.11.3": {
     "date": "2026-07-01",
     "fast_failover": False,
     "min_k8s": 34,
     "rwx_fixes": []
    },
    "1.12.0": {
     "date": "2026-06-02",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": [
      {
       "issue": 11203,
       "kind": "improvement",
       "title": "Record the current share manager image in the Share Manager CR status"
      },
      {
       "issue": 12644,
       "kind": "improvement",
       "title": "Relax `endpoint-network-for-rwx-volume` validation for migratable block-mode volumes"
      },
      {
       "issue": 12986,
       "kind": "bug",
       "title": "RWX Workload becomes Read-only after nodes shutdown and share manager is recreated on a new node"
      }
     ]
    },
    "1.12.1": {
     "date": "2026-08-14",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": []
    },
    "1.12.2": {
     "date": "2026-11-09",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": []
    },
    "1.13.0": {
     "date": "2026-09-29",
     "fast_failover": False,
     "min_k8s": 34,
     "rwx_fixes": [
      {
       "issue": 13221,
       "kind": "bug",
       "title": "Test case `test_rwx_delete_share_manager_pod` fails because it's unable to find the exported volume in share manager pod after it's deleted and restarted"
      }
     ]
    },
    "1.2.0": {
     "date": "2021-08-31",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": [
      {
       "issue": 2814,
       "kind": "feature",
       "title": "Support XFS for RWX volumes ("
      },
      {
       "issue": 2867,
       "kind": "feature",
       "title": "Support encrypted RWX volumes ("
      }
     ]
    },
    "1.2.1": {
     "date": "2021-10-06",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": [
      {
       "issue": 2946,
       "kind": "bug",
       "title": "Deleting the only pod in a single replica ReplicaSet causes an attachment failure of the replacement pods when the volume is RWX. ("
      }
     ]
    },
    "1.2.2": {
     "date": "2021-10-08",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.2.3": {
     "date": "2021-12-17",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": [
      {
       "issue": 3348,
       "kind": "bug",
       "title": "Drain stuck on K3s setup on node where RWX volume is attached ("
      }
     ]
    },
    "1.2.4": {
     "date": "2022-03-17",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.2.5": {
     "date": "2022-09-02",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.2.6": {
     "date": "2022-11-04",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.3.0": {
     "date": "2022-06-15",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": [
      {
       "issue": 2946,
       "kind": "bug",
       "title": "Deleting the only pod in a single replica ReplicaSet causes an attachment failure of the replacement pods when the volume is RWX. ("
      },
      {
       "issue": 3193,
       "kind": "bug",
       "title": "rwx volume fail to attach ("
      },
      {
       "issue": 3348,
       "kind": "bug",
       "title": "Drain stuck on K3s setup on node where RWX volume is attached ("
      }
     ]
    },
    "1.3.1": {
     "date": "2022-08-11",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.3.2": {
     "date": "2022-10-14",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.3.3": {
     "date": "2023-04-20",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": [
      {
       "issue": 4789,
       "kind": "improvement",
       "title": "share-manager pod bypasses the kubernetes scheduler ("
      },
      {
       "issue": 5296,
       "kind": "bug",
       "title": "Memory leak in CSI plugin caused by stuck umount processes if the RWX volume is already gone ("
      },
      {
       "issue": 5507,
       "kind": "bug",
       "title": "share-manager pod failed to restart after kubelet restart ("
      },
      {
       "issue": 5558,
       "kind": "bug",
       "title": "RWX volume is stuck at detaching when the attached node is down  ("
      },
      {
       "issue": 5537,
       "kind": "bug",
       "title": "RWX volume attachment failed if tried more enough times ("
      }
     ]
    },
    "1.4.0": {
     "date": "2022-12-30",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": [
      {
       "issue": 2293,
       "kind": "feature",
       "title": "NFS support (RWX) GA ("
      },
      {
       "issue": 2380,
       "kind": "improvement",
       "title": "Dump NFS ganesha logs to pod stdout ("
      },
      {
       "issue": 4351,
       "kind": "improvement",
       "title": "Update nfs-ganesha to v4.0 ("
      },
      {
       "issue": 4789,
       "kind": "improvement",
       "title": "share-manager pod bypasses the kubernetes scheduler ("
      },
      {
       "issue": 5017,
       "kind": "improvement",
       "title": "Disable `Automatically Delete Workload Pod when The Volume Is Detached Unexpectedly` for RWX volumes ("
      }
     ]
    },
    "1.4.1": {
     "date": "2023-03-13",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": [
      {
       "issue": 5356,
       "kind": "improvement",
       "title": "Update ganesha nfs to 4.2.3 ("
      },
      {
       "issue": 5296,
       "kind": "bug",
       "title": "Memory leak in CSI plugin caused by stuck umount processes if the RWX volume is already gone ("
      },
      {
       "issue": 5507,
       "kind": "bug",
       "title": "share-manager pod failed to restart after kubelet restart ("
      },
      {
       "issue": 5183,
       "kind": "bug",
       "title": "RWX doesn't work with release 1.4.0 due to end grace update error from recovery backend ("
      },
      {
       "issue": 5456,
       "kind": "bug",
       "title": "RWX Volume attachment is getting Failed ("
      }
     ]
    },
    "1.4.2": {
     "date": "2023-05-12",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": [
      {
       "issue": 5558,
       "kind": "bug",
       "title": "RWX volume is stuck at detaching when the attached node is down  ("
      },
      {
       "issue": 5537,
       "kind": "bug",
       "title": "RWX volume attachment failed if tried more enough times ("
      },
      {
       "issue": 5856,
       "kind": "bug",
       "title": "Unable to backup volume after NFS server IP change ("
      }
     ]
    },
    "1.4.3": {
     "date": "2023-07-14",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": [
      {
       "issue": 5954,
       "kind": "bug",
       "title": "share-manager for a given pvc keep restarting (other pvc are working fine) ("
      }
     ]
    },
    "1.4.4": {
     "date": "2023-10-26",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": [
      {
       "issue": 6655,
       "kind": "improvement",
       "title": "Support both NFS `hard` and `soft` with custom `timeo` and `retrans` options for RWX volumes"
      },
      {
       "issue": 6924,
       "kind": "bug",
       "title": "[v1.4.4-rc1] rwx workload gets stuck in ContainerCreating after cluster restart"
      },
      {
       "issue": 6829,
       "kind": "bug",
       "title": "IO error occurs when detaching RWX volume"
      }
     ]
    },
    "1.5.0": {
     "date": "2023-07-07",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": [
      {
       "issue": 5143,
       "kind": "feature",
       "title": "Support RWX volume trim ("
      },
      {
       "issue": 4829,
       "kind": "improvement",
       "title": "Add support for crypto parameters for RWX volumes ("
      },
      {
       "issue": 5356,
       "kind": "improvement",
       "title": "Update ganesha nfs to 4.2.3 ("
      },
      {
       "issue": 5507,
       "kind": "bug",
       "title": "share-manager pod failed to restart after kubelet restart ("
      },
      {
       "issue": 5558,
       "kind": "bug",
       "title": "RWX volume is stuck at detaching when the attached node is down  ("
      },
      {
       "issue": 5296,
       "kind": "bug",
       "title": "Memory leak in CSI plugin caused by stuck umount processes if the RWX volume is already gone ("
      },
      {
       "issue": 5183,
       "kind": "bug",
       "title": "RWX doesn't work with release 1.4.0 due to end grace update error from recovery backend ("
      },
      {
       "issue": 5456,
       "kind": "bug",
       "title": "RWX Volume attachment is getting Failed ("
      },
      {
       "issue": 5537,
       "kind": "bug",
       "title": "RWX volume attachment failed if tried more enough times ("
      },
      {
       "issue": 5856,
       "kind": "bug",
       "title": "Unable to backup volume after NFS server IP change ("
      },
      {
       "issue": 5954,
       "kind": "bug",
       "title": "share-manager for a given pvc keep restarting (other pvc are working fine) ("
      },
      {
       "issue": 6139,
       "kind": "bug",
       "title": "RWX volume remains attached after workload deleted if it's upgraded from v1.4.2 ("
      }
     ]
    },
    "1.5.1": {
     "date": "2023-07-19",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.5.2": {
     "date": "2023-11-03",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": [
      {
       "issue": 6655,
       "kind": "improvement",
       "title": "Support both NFS `hard` and `soft` with custom `timeo` and `retrans` options for RWX volumes"
      },
      {
       "issue": 6924,
       "kind": "bug",
       "title": "RWX workload gets stuck in ContainerCreating after cluster restart"
      },
      {
       "issue": 6829,
       "kind": "bug",
       "title": "IO error occurs when detaching RWX volume"
      }
     ]
    },
    "1.5.3": {
     "date": "2023-11-17",
     "fast_failover": False,
     "min_k8s": None,
     "rwx_fixes": []
    },
    "1.5.4": {
     "date": "2024-02-27",
     "fast_failover": False,
     "min_k8s": 21,
     "rwx_fixes": []
    },
    "1.5.5": {
     "date": "2024-04-19",
     "fast_failover": False,
     "min_k8s": 21,
     "rwx_fixes": []
    },
    "1.6.0": {
     "date": "2024-02-01",
     "fast_failover": False,
     "min_k8s": 21,
     "rwx_fixes": [
      {
       "issue": 7638,
       "kind": "feature",
       "title": "RWX volume supports different NFS version (4.2) and mount options"
      },
      {
       "issue": 6000,
       "kind": "feature",
       "title": "Update nfs-genesha to 5.x for share manager"
      },
      {
       "issue": 7741,
       "kind": "improvement",
       "title": "Revert RWX volume back to NFS v4.1"
      },
      {
       "issue": 6655,
       "kind": "improvement",
       "title": "Support both NFS `hard` and `soft` with custom `timeo` and `retrans` options for RWX volumes"
      },
      {
       "issue": 7301,
       "kind": "bug",
       "title": "Failed RWX mount due to connection timeout still happening"
      },
      {
       "issue": 6829,
       "kind": "bug",
       "title": "IO error occurs when detaching RWX volume"
      }
     ]
    },
    "1.6.1": {
     "date": "2024-03-29",
     "fast_failover": False,
     "min_k8s": 21,
     "rwx_fixes": []
    },
    "1.6.2": {
     "date": "2024-05-23",
     "fast_failover": False,
     "min_k8s": 21,
     "rwx_fixes": []
    },
    "1.6.3": {
     "date": "2024-09-20",
     "fast_failover": False,
     "min_k8s": 21,
     "rwx_fixes": []
    },
    "1.6.4": {
     "date": "2025-01-03",
     "fast_failover": False,
     "min_k8s": 21,
     "rwx_fixes": [
      {
       "issue": 10096,
       "kind": "bug",
       "title": "[v1.6.x-head] Share manager pod kept restarting"
      }
     ]
    },
    "1.7.0": {
     "date": "2024-08-20",
     "fast_failover": True,
     "min_k8s": 21,
     "rwx_fixes": [
      {
       "issue": 6205,
       "kind": "feature",
       "title": "Share manager HA - Experimental"
      },
      {
       "issue": 8184,
       "kind": "feature",
       "title": "Support storage network for RWX volumes"
      },
      {
       "issue": 8345,
       "kind": "bug",
       "title": "Do not terminate nfs-ganesha in share-manager pod after failing to access recovery backend"
      },
      {
       "issue": 9008,
       "kind": "improvement",
       "title": "Update nfs-ganesha to v5.9"
      },
      {
       "issue": 8376,
       "kind": "improvement",
       "title": "Pre-pull images (share-manager image and instance-manager image) on each Longhorn node"
      },
      {
       "issue": 7931,
       "kind": "improvement",
       "title": "Improve environment_check script for NFS protocol bug and the host system self diagnosis"
      },
      {
       "issue": 7872,
       "kind": "improvement",
       "title": "RWX volume scheduling"
      },
      {
       "issue": 9081,
       "kind": "bug",
       "title": "Test case test_rwx_delete_share_manager_pod fails after changes for RWX HA."
      },
      {
       "issue": 9089,
       "kind": "bug",
       "title": "RWX volume is stuck in auto-salvage loop forever if volume becomes faulted and RWX fast failover setting is enabled"
      },
      {
       "issue": 9022,
       "kind": "bug",
       "title": "RWX pod stuck in hanging forever after a node shutdown/reboot"
      },
      {
       "issue": 8999,
       "kind": "bug",
       "title": "[v1.7.0-rc1] Require unexpected long time to remount RWX volume after share manager restarted"
      },
      {
       "issue": 8979,
       "kind": "bug",
       "title": "Can not change `storage-network-for-rwx-volume-enabled` when RWX volume attached"
      },
      {
       "issue": 8253,
       "kind": "bug",
       "title": "RWX volume is hang on Photon OS"
      }
     ]
    },
    "1.7.1": {
     "date": "2024-09-04",
     "fast_failover": False,
     "min_k8s": 21,
     "rwx_fixes": []
    },
    "1.7.2": {
     "date": "2024-10-18",
     "fast_failover": False,
     "min_k8s": 21,
     "rwx_fixes": []
    },
    "1.7.3": {
     "date": "2025-02-19",
     "fast_failover": False,
     "min_k8s": 21,
     "rwx_fixes": []
    },
    "1.8.0": {
     "date": "2025-01-22",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": [
      {
       "issue": 9736,
       "kind": "feature",
       "title": ": Automatic online filesystem resize for RWX volumes."
      },
      {
       "issue": 10194,
       "kind": "improvement",
       "title": "Bump nfs-ganesha in longhorn-share-manager from v6.3 to v6.5"
      },
      {
       "issue": 9830,
       "kind": "improvement",
       "title": "Check NFS versions in /etc/nfsmount.conf instead"
      },
      {
       "issue": 6735,
       "kind": "improvement",
       "title": "Reject strict-local + RWX volume creation"
      },
      {
       "issue": 9614,
       "kind": "improvement",
       "title": "Update longhorn-share-manager's nfs-ganesha to v6.2"
      },
      {
       "issue": 9530,
       "kind": "bug",
       "title": "All Backups are lost in the Backup Target if the NFS Service Disconnects and Reconnects again"
      },
      {
       "issue": 9095,
       "kind": "bug",
       "title": "Remove unnecessary restart of RWX workload."
      },
      {
       "issue": 9504,
       "kind": "bug",
       "title": "Fix test case test_rwx_delete_share_manager_pod failure after changes to RWX workload restart."
      },
      {
       "issue": 7802,
       "kind": "bug",
       "title": "Faulted RWX volume upon creation"
      }
     ]
    },
    "1.8.1": {
     "date": "2025-03-05",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": []
    },
    "1.8.2": {
     "date": "2025-06-09",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": []
    },
    "1.9.0": {
     "date": "2025-05-27",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": [
      {
       "issue": 2933,
       "kind": "bug",
       "title": "Workload with RWX volume cannot recover when Kubelet restarts"
      },
      {
       "issue": 5658,
       "kind": "bug",
       "title": "RWX volume becomes faulted after the node reconnects"
      }
     ]
    },
    "1.9.1": {
     "date": "2025-07-23",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": []
    },
    "1.9.2": {
     "date": "2025-09-24",
     "fast_failover": False,
     "min_k8s": 25,
     "rwx_fixes": []
    }
   },
   "url": "https://github.com/longhorn/longhorn/releases"
  }
 },
 "feature_gates": {
  "APIListChunking": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "alpha",
     "to": 8
    },
    {
     "default": True,
     "from": 9,
     "locked": False,
     "stage": "beta",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "APIPriorityAndFairness": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 18,
     "locked": False,
     "stage": "alpha",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "beta",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "stable",
     "to": 30
    }
   ]
  },
  "APIResponseCompression": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 7,
     "locked": False,
     "stage": "\"alpha\"",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "APISelfSubjectReview": {
   "removed_in": 30,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "stable",
     "to": 29
    }
   ]
  },
  "APIServerIdentity": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "APIServerTracing": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "APIServerWebhookAuthenticationToken": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "APIServingWithRoutine": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "Accelerators": {
   "removed_in": 12,
   "stages": [
    {
     "default": False,
     "from": 6,
     "locked": False,
     "stage": "alpha",
     "to": 10
    },
    {
     "default": False,
     "from": 11,
     "locked": False,
     "stage": "deprecated",
     "to": 11
    }
   ]
  },
  "AdmissionWebhookMatchConditions": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 27,
     "locked": False,
     "stage": "alpha",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "beta",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "AdvancedAuditing": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 7,
     "locked": False,
     "stage": "alpha",
     "to": 7
    },
    {
     "default": True,
     "from": 8,
     "locked": False,
     "stage": "beta",
     "to": 11
    },
    {
     "default": True,
     "from": 12,
     "locked": False,
     "stage": "stable",
     "to": 27
    }
   ]
  },
  "AffinityInAnnotations": {
   "removed_in": 9,
   "stages": [
    {
     "default": False,
     "from": 6,
     "locked": False,
     "stage": "alpha",
     "to": 7
    },
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "deprecated",
     "to": 8
    }
   ]
  },
  "AggregatedDiscoveryEndpoint": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "AllowDNSOnlyNodeCSR": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "AllowExtTrafficLocalEndpoints": {
   "removed_in": 10,
   "stages": [
    {
     "default": False,
     "from": 4,
     "locked": False,
     "stage": "beta",
     "to": 6
    },
    {
     "default": True,
     "from": 7,
     "locked": False,
     "stage": "stable",
     "to": 9
    }
   ]
  },
  "AllowInsecureBackendProxy": {
   "removed_in": 26,
   "stages": [
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "beta",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "AllowInsecureKubeletCertificateSigningRequests": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "AllowParsingUserUIDFromCertAuth": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "AllowServiceExternalIPs": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "AllowServiceLBStatusOnNonLB": {
   "removed_in": 35,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "deprecated",
     "to": 34
    }
   ]
  },
  "AllowUnsafeMalformedObjectDeletion": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "AnonymousAuthConfigurableEndpoints": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "alpha",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "AnyVolumeDataSource": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 18,
     "locked": False,
     "stage": "alpha",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "AppArmor": {
   "removed_in": 33,
   "stages": [
    {
     "default": True,
     "from": 4,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "AppArmorFields": {
   "removed_in": 33,
   "stages": [
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "AtomicFIFO": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "AtomicWriteVolumeUserFields": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "AttachVolumeLimit": {
   "removed_in": 22,
   "stages": [
    {
     "default": False,
     "from": 11,
     "locked": False,
     "stage": "alpha",
     "to": 11
    },
    {
     "default": True,
     "from": 12,
     "locked": False,
     "stage": "beta",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "stable",
     "to": 21
    }
   ]
  },
  "AuthorizeNodeWithSelectors": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "alpha",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "AuthorizePodWebsocketUpgradeCreatePermission": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "AuthorizeWithSelectors": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "alpha",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "BalanceAttachedNodeVolumes": {
   "removed_in": 23,
   "stages": [
    {
     "default": False,
     "from": 11,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "deprecated",
     "to": 22
    }
   ]
  },
  "BlockVolume": {
   "removed_in": 22,
   "stages": [
    {
     "default": False,
     "from": 9,
     "locked": False,
     "stage": "alpha",
     "to": 12
    },
    {
     "default": True,
     "from": 13,
     "locked": False,
     "stage": "beta",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "stable",
     "to": 21
    }
   ]
  },
  "BoundServiceAccountTokenVolume": {
   "removed_in": 24,
   "stages": [
    {
     "default": False,
     "from": 13,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "stable",
     "to": 23
    }
   ]
  },
  "BtreeWatchCache": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "CBORServingAndStorage": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "CPUManager": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "alpha",
     "to": 9
    },
    {
     "default": True,
     "from": 10,
     "locked": False,
     "stage": "beta",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "CPUManagerPolicyAlphaOptions": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "CPUManagerPolicyBetaOptions": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "CPUManagerPolicyOptions": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "CRDObservedGenerationTracking": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "CRDValidationRatcheting": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "CRIContainerLogRotation": {
   "removed_in": 23,
   "stages": [
    {
     "default": False,
     "from": 10,
     "locked": False,
     "stage": "alpha",
     "to": 10
    },
    {
     "default": True,
     "from": 11,
     "locked": False,
     "stage": "beta",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "stable",
     "to": 22
    }
   ]
  },
  "CRIListStreaming": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "CSIBlockVolume": {
   "removed_in": 22,
   "stages": [
    {
     "default": False,
     "from": 11,
     "locked": False,
     "stage": "alpha",
     "to": 13
    },
    {
     "default": True,
     "from": 14,
     "locked": False,
     "stage": "beta",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "stable",
     "to": 21
    }
   ]
  },
  "CSIDriverRegistry": {
   "removed_in": 22,
   "stages": [
    {
     "default": False,
     "from": 12,
     "locked": False,
     "stage": "alpha",
     "to": 13
    },
    {
     "default": True,
     "from": 14,
     "locked": False,
     "stage": "beta",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "stable",
     "to": 21
    }
   ]
  },
  "CSIInlineVolume": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 15,
     "locked": False,
     "stage": "alpha",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "CSIMigration": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "alpha",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "CSIMigrationAWS": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "alpha",
     "to": 16
    },
    {
     "default": False,
     "from": 17,
     "locked": False,
     "stage": "beta",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "CSIMigrationAWSComplete": {
   "removed_in": 22,
   "stages": [
    {
     "default": False,
     "from": 17,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "deprecated",
     "to": 21
    }
   ]
  },
  "CSIMigrationAzureDisk": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 15,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": False,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "CSIMigrationAzureDiskComplete": {
   "removed_in": 22,
   "stages": [
    {
     "default": False,
     "from": 17,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "deprecated",
     "to": 21
    }
   ]
  },
  "CSIMigrationAzureFile": {
   "removed_in": 30,
   "stages": [
    {
     "default": False,
     "from": 15,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "beta",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "stable",
     "to": 29
    }
   ]
  },
  "CSIMigrationAzureFileComplete": {
   "removed_in": 22,
   "stages": [
    {
     "default": False,
     "from": 17,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "deprecated",
     "to": 21
    }
   ]
  },
  "CSIMigrationGCE": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "alpha",
     "to": 16
    },
    {
     "default": False,
     "from": 17,
     "locked": False,
     "stage": "beta",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "stable",
     "to": 27
    }
   ]
  },
  "CSIMigrationGCEComplete": {
   "removed_in": 22,
   "stages": [
    {
     "default": False,
     "from": 17,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "deprecated",
     "to": 21
    }
   ]
  },
  "CSIMigrationOpenStack": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "alpha",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "CSIMigrationOpenStackComplete": {
   "removed_in": 22,
   "stages": [
    {
     "default": False,
     "from": 17,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "deprecated",
     "to": 21
    }
   ]
  },
  "CSIMigrationPortworx": {
   "removed_in": 36,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 24
    },
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "stable",
     "to": 35
    }
   ]
  },
  "CSIMigrationRBD": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 27
    },
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "deprecated",
     "to": 30
    }
   ]
  },
  "CSIMigrationvSphere": {
   "removed_in": 29,
   "stages": [
    {
     "default": False,
     "from": 18,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": False,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "beta",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "stable",
     "to": 28
    }
   ]
  },
  "CSIMigrationvSphereComplete": {
   "removed_in": 23,
   "stages": [
    {
     "default": False,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "deprecated",
     "to": 22
    }
   ]
  },
  "CSINodeExpandSecret": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "stable",
     "to": 30
    }
   ]
  },
  "CSINodeInfo": {
   "removed_in": 23,
   "stages": [
    {
     "default": False,
     "from": 12,
     "locked": False,
     "stage": "alpha",
     "to": 13
    },
    {
     "default": True,
     "from": 14,
     "locked": False,
     "stage": "beta",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "stable",
     "to": 22
    }
   ]
  },
  "CSIPersistentVolume": {
   "removed_in": 17,
   "stages": [
    {
     "default": False,
     "from": 9,
     "locked": False,
     "stage": "alpha",
     "to": 9
    },
    {
     "default": True,
     "from": 10,
     "locked": False,
     "stage": "beta",
     "to": 12
    },
    {
     "default": True,
     "from": 13,
     "locked": False,
     "stage": "stable",
     "to": 16
    }
   ]
  },
  "CSIServiceAccountToken": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "CSIServiceAccountTokenSecrets": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "CSIStorageCapacity": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 19,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 27
    }
   ]
  },
  "CSIVolumeFSGroupPolicy": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 19,
     "locked": False,
     "stage": "alpha",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "beta",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "CSIVolumeHealth": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "CSRDuration": {
   "removed_in": 26,
   "stages": [
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "ChangeContainerStatusOnKubeletRestart": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "ClearingNominatedNodeNameAfterBinding": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "CloudControllerManagerWatchBasedRoutesReconciliation": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "CloudControllerManagerWebhook": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 27,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "CloudDualStackNodeIPs": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 27,
     "locked": False,
     "stage": "alpha",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  },
  "ClusterTrustBundle": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 27,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ClusterTrustBundleProjection": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ComponentFlagz": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "ComponentSLIs": {
   "removed_in": 35,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": True,
     "stage": "stable",
     "to": 34
    }
   ]
  },
  "ComponentStatusz": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "CompositePodGroup": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "ConcurrentWatchObjectDecode": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "ConfigurableFSGroupPolicy": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 18,
     "locked": False,
     "stage": "alpha",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "beta",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "ConsistentHTTPGetHandlers": {
   "removed_in": 31,
   "stages": [
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "stable",
     "to": 30
    }
   ]
  },
  "ConsistentListFromCache": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ConstrainedImpersonation": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "ContainerCheckpoint": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "ContainerRestartRules": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "ContainerStopSignals": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "ContextualLogging": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 24,
     "locked": False,
     "stage": "alpha",
     "to": None
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "ControllerManagerLeaderMigration": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "ControllerManagerReleaseLeaderElectionLockOnExit": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "CoordinatedLeaderElection": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "CronJobControllerV2": {
   "removed_in": 24,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "stable",
     "to": 23
    }
   ]
  },
  "CronJobTimeZone": {
   "removed_in": 29,
   "stages": [
    {
     "default": False,
     "from": 24,
     "locked": False,
     "stage": "alpha",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "beta",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "stable",
     "to": 28
    }
   ]
  },
  "CronJobsScheduledAnnotation": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "CrossNamespaceVolumeDataSource": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "CustomCPUCFSQuotaPeriod": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 12,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "CustomPodDNS": {
   "removed_in": 17,
   "stages": [
    {
     "default": False,
     "from": 9,
     "locked": False,
     "stage": "alpha",
     "to": 9
    },
    {
     "default": True,
     "from": 10,
     "locked": False,
     "stage": "beta",
     "to": 13
    },
    {
     "default": True,
     "from": 14,
     "locked": False,
     "stage": "stable",
     "to": 16
    }
   ]
  },
  "CustomResourceDefaulting": {
   "removed_in": 19,
   "stages": [
    {
     "default": False,
     "from": 15,
     "locked": False,
     "stage": "alpha",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "beta",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "stable",
     "to": 18
    }
   ]
  },
  "CustomResourceFieldSelectors": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "CustomResourcePublishOpenAPI": {
   "removed_in": 19,
   "stages": [
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "alpha",
     "to": 14
    },
    {
     "default": True,
     "from": 15,
     "locked": False,
     "stage": "beta",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "stable",
     "to": 18
    }
   ]
  },
  "CustomResourceSubresources": {
   "removed_in": 19,
   "stages": [
    {
     "default": False,
     "from": 10,
     "locked": False,
     "stage": "alpha",
     "to": 10
    },
    {
     "default": True,
     "from": 11,
     "locked": False,
     "stage": "beta",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "stable",
     "to": 18
    }
   ]
  },
  "CustomResourceValidation": {
   "removed_in": 19,
   "stages": [
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "alpha",
     "to": 8
    },
    {
     "default": True,
     "from": 9,
     "locked": False,
     "stage": "beta",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "stable",
     "to": 18
    }
   ]
  },
  "CustomResourceValidationExpressions": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "beta",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "stable",
     "to": 30
    }
   ]
  },
  "CustomResourceWebhookConversion": {
   "removed_in": 19,
   "stages": [
    {
     "default": False,
     "from": 13,
     "locked": False,
     "stage": "alpha",
     "to": 14
    },
    {
     "default": True,
     "from": 15,
     "locked": False,
     "stage": "beta",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "stable",
     "to": 18
    }
   ]
  },
  "DRAAdminAccess": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "DRAConsumableCapacity": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "DRAControlPlaneController": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": 31
    }
   ]
  },
  "DRADerivedAttributes": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "DRADeviceBindingConditions": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "DRADeviceCompatibilityGroups": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "DRADeviceTaintRules": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": 37
    },
    {
     "default": True,
     "from": 37,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "DRADeviceTaints": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": 37
    },
    {
     "default": True,
     "from": 37,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "DRAExtendedResource": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "DRAListTypeAttributes": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "DRANodeAllocatableResources": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "DRAOptionalNodeOperations": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "DRAPartitionableDevices": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "DRAPartitionableDevicesType": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "DRAPrioritizedList": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "DRAResourceClaimDeviceStatus": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "DRAResourceClaimGranularStatusAuthorization": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "DRAResourcePoolStatus": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "DRASchedulerFilterTimeout": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "DRAWorkloadResourceClaims": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": None
    },
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "DaemonSetUpdateSurge": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "DeclarativeValidation": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "DeclarativeValidationBeta": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "DeclarativeValidationTakeover": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "deprecated",
     "to": 36
    },
    {
     "default": False,
     "from": 37,
     "locked": True,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "DefaultHostNetworkHostPortsInPodTemplates": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "deprecated",
     "to": 30
    }
   ]
  },
  "DefaultPodSysctls": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "DefaultPodTopologySpread": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 19,
     "locked": False,
     "stage": "alpha",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "DelegateFSGroupToCSIDriver": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "stable",
     "to": 27
    }
   ]
  },
  "DeploymentReplicaSetTerminatingReplicas": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "DetectCacheInconsistency": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "DevicePluginCDIDevices": {
   "removed_in": 34,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "stable",
     "to": 33
    }
   ]
  },
  "DevicePlugins": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "alpha",
     "to": 9
    },
    {
     "default": True,
     "from": 10,
     "locked": False,
     "stage": "beta",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "stable",
     "to": 27
    }
   ]
  },
  "DisableAcceleratorUsageMetrics": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 19,
     "locked": False,
     "stage": "alpha",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "stable",
     "to": 27
    }
   ]
  },
  "DisableAllocatorDualWrite": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "DisableCPUQuotaWithExclusiveCPUs": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "DisableCloudProviders": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "DisableKubeletCloudCredentialProviders": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "DisableNodeKubeProxyVersion": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": None,
     "locked": False,
     "stage": "beta",
     "to": None
    },
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "deprecated",
     "to": None
    },
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "deprecated",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "deprecated",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": True,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "DownwardAPIHugePages": {
   "removed_in": 29,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "stable",
     "to": 28
    }
   ]
  },
  "DryRun": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 12,
     "locked": False,
     "stage": "alpha",
     "to": 12
    },
    {
     "default": True,
     "from": 13,
     "locked": False,
     "stage": "beta",
     "to": 18
    },
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "stable",
     "to": 27
    }
   ]
  },
  "DynamicAuditing": {
   "removed_in": 20,
   "stages": [
    {
     "default": False,
     "from": 13,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": False,
     "from": 19,
     "locked": False,
     "stage": "deprecated",
     "to": 19
    }
   ]
  },
  "DynamicKubeletConfig": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 4,
     "locked": False,
     "stage": "alpha",
     "to": 10
    },
    {
     "default": True,
     "from": 11,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "deprecated",
     "to": 25
    }
   ]
  },
  "DynamicProvisioningScheduling": {
   "removed_in": 12,
   "stages": [
    {
     "default": False,
     "from": 11,
     "locked": False,
     "stage": "alpha",
     "to": 11
    },
    {
     "default": False,
     "from": 12,
     "locked": False,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "DynamicResourceAllocation": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": 31
    },
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "stable",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "DynamicVolumeProvisioning": {
   "removed_in": 13,
   "stages": [
    {
     "default": True,
     "from": 3,
     "locked": False,
     "stage": "alpha",
     "to": 7
    },
    {
     "default": True,
     "from": 8,
     "locked": False,
     "stage": "stable",
     "to": 12
    }
   ]
  },
  "EfficientWatchResumption": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "ElasticIndexedJob": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "EmptyDirVolumeMode": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "EnableAggregatedDiscoveryTimeout": {
   "removed_in": 18,
   "stages": [
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "deprecated",
     "to": 17
    }
   ]
  },
  "EnableEquivalenceClassCache": {
   "removed_in": 24,
   "stages": [
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "alpha",
     "to": 12
    },
    {
     "default": False,
     "from": 13,
     "locked": False,
     "stage": "deprecated",
     "to": 23
    }
   ]
  },
  "EndpointSlice": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 16,
     "locked": False,
     "stage": "alpha",
     "to": 16
    },
    {
     "default": False,
     "from": 17,
     "locked": False,
     "stage": "beta",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "beta",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "EndpointSliceNodeName": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "EndpointSliceProxying": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 18,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "EndpointSliceTerminatingCondition": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "stable",
     "to": 27
    }
   ]
  },
  "EnvFiles": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "EphemeralContainers": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 16,
     "locked": False,
     "stage": "alpha",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "EtcdRangeStream": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "EvenPodsSpread": {
   "removed_in": 22,
   "stages": [
    {
     "default": False,
     "from": 16,
     "locked": False,
     "stage": "alpha",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "beta",
     "to": 18
    },
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "stable",
     "to": 21
    }
   ]
  },
  "EventedPLEG": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "ExcludeAdmissionWebhookVirtualResources": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "ExecProbeTimeout": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ExpandCSIVolumes": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "alpha",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "ExpandInUsePersistentVolumes": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 11,
     "locked": False,
     "stage": "alpha",
     "to": 14
    },
    {
     "default": True,
     "from": 15,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "ExpandPersistentVolumes": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "alpha",
     "to": 10
    },
    {
     "default": True,
     "from": 11,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "ExpandedDNSConfig": {
   "removed_in": 30,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "stable",
     "to": 29
    }
   ]
  },
  "ExperimentalCriticalPodAnnotation": {
   "removed_in": 17,
   "stages": [
    {
     "default": False,
     "from": 5,
     "locked": False,
     "stage": "alpha",
     "to": 12
    },
    {
     "default": False,
     "from": 13,
     "locked": False,
     "stage": "deprecated",
     "to": 16
    }
   ]
  },
  "ExperimentalHostUserNamespaceDefaulting": {
   "removed_in": 30,
   "stages": [
    {
     "default": False,
     "from": 5,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "deprecated",
     "to": 29
    }
   ]
  },
  "ExtendWebSocketsToKubelet": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "ExternalPolicyForExternalIP": {
   "removed_in": 23,
   "stages": [
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "stable",
     "to": 22
    }
   ]
  },
  "ExternalServiceAccountTokenSigner": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "GCERegionalPersistentDisk": {
   "removed_in": 17,
   "stages": [
    {
     "default": True,
     "from": 10,
     "locked": False,
     "stage": "beta",
     "to": 12
    },
    {
     "default": True,
     "from": 13,
     "locked": False,
     "stage": "stable",
     "to": 16
    }
   ]
  },
  "GRPCContainerProbe": {
   "removed_in": 29,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "beta",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "stable",
     "to": 28
    }
   ]
  },
  "GRPCContainerProbeTLS": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "GangScheduling": {
   "removed_in": 37,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": 36
    }
   ]
  },
  "GenericEphemeralVolume": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 19,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "beta",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "GenericWorkload": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": 36
    },
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "GitRepoVolumeDriver": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "GracefulNodeShutdown": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "GracefulNodeShutdownBasedOnPodPriority": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "H2CContainerProbe": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "HPAConfigurableTolerance": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "HPAContainerMetrics": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  },
  "HPAScaleToZero": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 16,
     "locked": False,
     "stage": "alpha",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "HonorPVReclaimPolicy": {
   "removed_in": 36,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": 35
    }
   ]
  },
  "HostnameOverride": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "HugePageStorageMediumSize": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 18,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "HugePages": {
   "removed_in": 17,
   "stages": [
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "alpha",
     "to": 9
    },
    {
     "default": True,
     "from": 10,
     "locked": False,
     "stage": "beta",
     "to": 13
    },
    {
     "default": True,
     "from": 14,
     "locked": False,
     "stage": "stable",
     "to": 16
    }
   ]
  },
  "HugepageAwareEviction": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "HyperVContainer": {
   "removed_in": 21,
   "stages": [
    {
     "default": False,
     "from": 10,
     "locked": False,
     "stage": "alpha",
     "to": 19
    },
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "deprecated",
     "to": 20
    }
   ]
  },
  "IPTablesOwnershipCleanup": {
   "removed_in": 30,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "stable",
     "to": 29
    }
   ]
  },
  "IPv6DualStack": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 15,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "beta",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "IdentifyPodOS": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "ImageMaximumGCAge": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ImageVolume": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ImageVolumeWithDigest": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "ImmutableEphemeralVolumes": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 18,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "InOrderInformers": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "InPlacePodLevelResourcesVerticalScaling": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "InPlacePodVerticalScaling": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 27,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "InPlacePodVerticalScalingAllocatedStatus": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "InPlacePodVerticalScalingExclusiveCPUs": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "InPlacePodVerticalScalingExclusiveMemory": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "InPlacePodVerticalScalingMemoryBackedVolumes": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "InPlacePodVerticalScalingSchedulerPreemption": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "InTreePluginAWSUnregister": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 30
    }
   ]
  },
  "InTreePluginAzureDiskUnregister": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 30
    }
   ]
  },
  "InTreePluginAzureFileUnregister": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 30
    }
   ]
  },
  "InTreePluginGCEUnregister": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 30
    }
   ]
  },
  "InTreePluginOpenStackUnregister": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 30
    }
   ]
  },
  "InTreePluginPortworxUnregister": {
   "removed_in": 36,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 35
    }
   ]
  },
  "InTreePluginRBDUnregister": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 27
    },
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "deprecated",
     "to": 30
    }
   ]
  },
  "InTreePluginvSphereUnregister": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 30
    }
   ]
  },
  "IndexedJob": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "InformerResourceVersion": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "IngressClassNamespacedParams": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "Initializers": {
   "removed_in": 15,
   "stages": [
    {
     "default": False,
     "from": 7,
     "locked": False,
     "stage": "alpha",
     "to": 13
    },
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "deprecated",
     "to": 14
    }
   ]
  },
  "JobBackoffLimitPerIndex": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "JobManagedBy": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "beta",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "JobMutableNodeSchedulingDirectives": {
   "removed_in": 29,
   "stages": [
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "stable",
     "to": 28
    }
   ]
  },
  "JobPodFailurePolicy": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "JobPodReplacementPolicy": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "JobReadyPods": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "beta",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "stable",
     "to": 30
    }
   ]
  },
  "JobSuccessPolicy": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "JobTrackingWithFinalizers": {
   "removed_in": 29,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 22
    },
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "beta",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "stable",
     "to": 28
    }
   ]
  },
  "KMSv1": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "deprecated",
     "to": 28
    },
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "KMSv2": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  },
  "KMSv2KDF": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "beta",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  },
  "KubeProxyDrainingTerminatingNodes": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "KubeProxyIPVS": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "KubeProxyNFTablesLocalhostNodePorts": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "KubeletCgroupDriverFromCRI": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": None
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "KubeletConfigFile": {
   "removed_in": 11,
   "stages": [
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "alpha",
     "to": 9
    },
    {
     "default": False,
     "from": 10,
     "locked": False,
     "stage": "deprecated",
     "to": 10
    }
   ]
  },
  "KubeletCrashLoopBackOffMax": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "KubeletCredentialProviders": {
   "removed_in": 29,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "beta",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "stable",
     "to": 28
    }
   ]
  },
  "KubeletEnsureSecretPulledImages": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "KubeletFineGrainedAuthz": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "KubeletInUserNamespace": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "KubeletPSI": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "KubeletPluginsWatcher": {
   "removed_in": 17,
   "stages": [
    {
     "default": False,
     "from": 11,
     "locked": False,
     "stage": "alpha",
     "to": 11
    },
    {
     "default": True,
     "from": 12,
     "locked": False,
     "stage": "beta",
     "to": 12
    },
    {
     "default": True,
     "from": 13,
     "locked": False,
     "stage": "stable",
     "to": 16
    }
   ]
  },
  "KubeletPodResources": {
   "removed_in": 30,
   "stages": [
    {
     "default": False,
     "from": 13,
     "locked": False,
     "stage": "alpha",
     "to": 14
    },
    {
     "default": True,
     "from": 15,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "stable",
     "to": 29
    }
   ]
  },
  "KubeletPodResourcesDynamicResources": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 27,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "KubeletPodResourcesGet": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 27,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "KubeletPodResourcesGetAllocatable": {
   "removed_in": 30,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "stable",
     "to": 29
    }
   ]
  },
  "KubeletSeparateDiskGC": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "KubeletServiceAccountTokenForCredentialProviders": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "KubeletTracing": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "LegacyNodeRoleBehavior": {
   "removed_in": 23,
   "stages": [
    {
     "default": False,
     "from": 16,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 20
    },
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "stable",
     "to": 22
    }
   ]
  },
  "LegacyServiceAccountTokenCleanUp": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  },
  "LegacyServiceAccountTokenNoAutoGeneration": {
   "removed_in": 29,
   "stages": [
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "beta",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "stable",
     "to": 28
    }
   ]
  },
  "LegacyServiceAccountTokenTracking": {
   "removed_in": 30,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "stable",
     "to": 29
    }
   ]
  },
  "ListFromCacheSnapshot": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "LoadBalancerIPMode": {
   "removed_in": 35,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": 34
    }
   ]
  },
  "LocalStorageCapacityIsolation": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 7,
     "locked": False,
     "stage": "alpha",
     "to": 9
    },
    {
     "default": True,
     "from": 10,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "LocalStorageCapacityIsolationFSQuotaMonitoring": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 15,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "LogarithmicScaleDown": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "LoggingAlphaOptions": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 24,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "LoggingBetaOptions": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "ManifestBasedAdmissionControlConfig": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "MatchLabelKeysInPodAffinity": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "MatchLabelKeysInPodTopologySpread": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "MatchLabelKeysInPodTopologySpreadSelectorMerge": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "MaxUnavailableStatefulSet": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 24,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "MemoryManager": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "MemoryQoS": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "MinDomainsInPodTopologySpread": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 24,
     "locked": False,
     "stage": "alpha",
     "to": 24
    },
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "beta",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  },
  "MinimizeIPTablesRestore": {
   "removed_in": 30,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "stable",
     "to": 29
    }
   ]
  },
  "MixedProtocolLBService": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "beta",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "stable",
     "to": 27
    }
   ]
  },
  "MountContainers": {
   "removed_in": 18,
   "stages": [
    {
     "default": False,
     "from": 9,
     "locked": False,
     "stage": "alpha",
     "to": 16
    },
    {
     "default": False,
     "from": 17,
     "locked": False,
     "stage": "deprecated",
     "to": 17
    }
   ]
  },
  "MountPropagation": {
   "removed_in": 15,
   "stages": [
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "alpha",
     "to": 9
    },
    {
     "default": True,
     "from": 10,
     "locked": False,
     "stage": "beta",
     "to": 11
    },
    {
     "default": True,
     "from": 12,
     "locked": False,
     "stage": "stable",
     "to": 14
    }
   ]
  },
  "MultiCIDRRangeAllocator": {
   "removed_in": 29,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 28
    }
   ]
  },
  "MultiCIDRServiceAllocator": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 27,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "MutableCSINodeAllocatableCount": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "MutablePVNodeAffinity": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "MutablePodResourcesForSuspendedJobs": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "MutableSchedulingDirectivesForSuspendedJobs": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "MutatingAdmissionPolicy": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "NFTablesProxyMode": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "NamespaceDefaultLabelName": {
   "removed_in": 24,
   "stages": [
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "stable",
     "to": 23
    }
   ]
  },
  "NativeHistograms": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "NetworkPolicyEndPort": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "NetworkPolicyStatus": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 24,
     "locked": False,
     "stage": "alpha",
     "to": 27
    }
   ]
  },
  "NewVolumeManagerReconstruction": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  },
  "NodeDeclaredFeatures": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "NodeDisruptionExclusion": {
   "removed_in": 23,
   "stages": [
    {
     "default": False,
     "from": 16,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "stable",
     "to": 22
    }
   ]
  },
  "NodeInclusionPolicyInPodTopologySpread": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "NodeLease": {
   "removed_in": 24,
   "stages": [
    {
     "default": False,
     "from": 12,
     "locked": False,
     "stage": "alpha",
     "to": 13
    },
    {
     "default": True,
     "from": 14,
     "locked": False,
     "stage": "beta",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "stable",
     "to": 23
    }
   ]
  },
  "NodeLifecycleConditions": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "NodeLogQuery": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 27,
     "locked": False,
     "stage": "alpha",
     "to": 29
    },
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "NodeOutOfServiceVolumeDetach": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 24,
     "locked": False,
     "stage": "alpha",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  },
  "NodeSwap": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 27
    },
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "beta",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "NominatedNodeNameForExpectation": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "NonPreemptingPriority": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 15,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "OpenAPIEnums": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "OpenAPIV3": {
   "removed_in": 29,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "beta",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "stable",
     "to": 28
    }
   ]
  },
  "OpportunisticBatching": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "OrderedNamespaceDeletion": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "PDBUnhealthyPodEvictionPolicy": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "PVCProtection": {
   "removed_in": 11,
   "stages": [
    {
     "default": False,
     "from": 9,
     "locked": False,
     "stage": "alpha",
     "to": 9
    },
    {
     "default": False,
     "from": 10,
     "locked": False,
     "stage": "deprecated",
     "to": 10
    }
   ]
  },
  "PersistentLocalVolumes": {
   "removed_in": 17,
   "stages": [
    {
     "default": False,
     "from": 7,
     "locked": False,
     "stage": "alpha",
     "to": 9
    },
    {
     "default": True,
     "from": 10,
     "locked": False,
     "stage": "beta",
     "to": 13
    },
    {
     "default": True,
     "from": 14,
     "locked": False,
     "stage": "stable",
     "to": 16
    }
   ]
  },
  "PersistentVolumeClaimUnusedSinceTime": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "PersistentVolumeLastPhaseTransitionTime": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "PodAffinityNamespaceSelector": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "PodAndContainerStatsFromCRI": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 36
    },
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "PodCertificateRequest": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "PodDeletionCost": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "PodDisruptionBudget": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 3,
     "locked": False,
     "stage": "alpha",
     "to": 4
    },
    {
     "default": True,
     "from": 5,
     "locked": False,
     "stage": "beta",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "PodDisruptionConditions": {
   "removed_in": 34,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "stable",
     "to": 33
    }
   ]
  },
  "PodGroupPreemptionPolicy": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "PodHasNetworkCondition": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 27
    }
   ]
  },
  "PodHostIPs": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  },
  "PodIndexLabel": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "PodLevelResourceManagers": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": 36
    },
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "PodLevelResources": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "PodLifecycleSleepAction": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "PodLifecycleSleepActionAllowZero": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "PodLogsQuerySplitStreams": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "PodObservedGenerationTracking": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "PodOverhead": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 16,
     "locked": False,
     "stage": "alpha",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "PodPriority": {
   "removed_in": 19,
   "stages": [
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "alpha",
     "to": 10
    },
    {
     "default": True,
     "from": 11,
     "locked": False,
     "stage": "beta",
     "to": 13
    },
    {
     "default": True,
     "from": 14,
     "locked": False,
     "stage": "stable",
     "to": 18
    }
   ]
  },
  "PodReadinessGates": {
   "removed_in": 17,
   "stages": [
    {
     "default": False,
     "from": 11,
     "locked": False,
     "stage": "alpha",
     "to": 11
    },
    {
     "default": True,
     "from": 12,
     "locked": False,
     "stage": "beta",
     "to": 13
    },
    {
     "default": True,
     "from": 14,
     "locked": False,
     "stage": "stable",
     "to": 16
    }
   ]
  },
  "PodReadyToStartContainersCondition": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "PodSchedulingReadiness": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "PodSecurity": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "stable",
     "to": 27
    }
   ]
  },
  "PodShareProcessNamespace": {
   "removed_in": 20,
   "stages": [
    {
     "default": False,
     "from": 10,
     "locked": False,
     "stage": "alpha",
     "to": 11
    },
    {
     "default": True,
     "from": 12,
     "locked": False,
     "stage": "beta",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "stable",
     "to": 19
    }
   ]
  },
  "PodTopologyLabelsAdmission": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "PodsAPI": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "PortForwardWebsockets": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "PreferNominatedNode": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "PreferSameTrafficDistribution": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "PreventStaticPodAPIReferences": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "ProbeTerminationGracePeriod": {
   "removed_in": 29,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "stable",
     "to": 28
    }
   ]
  },
  "ProcMountType": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 12,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ProxyTerminatingEndpoints": {
   "removed_in": 30,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "stable",
     "to": 29
    }
   ]
  },
  "QOSReserved": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 11,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "ReadOnlyAPIDataVolumes": {
   "removed_in": 11,
   "stages": [
    {
     "default": True,
     "from": 8,
     "locked": False,
     "stage": "beta",
     "to": 9
    },
    {
     "default": False,
     "from": 10,
     "locked": False,
     "stage": "stable",
     "to": 10
    }
   ]
  },
  "ReadWriteOncePod": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "stable",
     "to": 30
    }
   ]
  },
  "RecoverVolumeExpansionFailure": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "RecursiveReadOnlyMounts": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ReduceDefaultCrashLoopBackOffDecay": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "RelaxedDNSSearchValidation": {
   "removed_in": 37,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": 36
    }
   ]
  },
  "RelaxedEnvironmentVariableValidation": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "RelaxedServiceNameValidation": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 34,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ReloadKubeletServerCertificateFile": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "RemainingItemCount": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 15,
     "locked": False,
     "stage": "alpha",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "beta",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "RemoteRequestHeaderUID": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "RemoveSelfLink": {
   "removed_in": 30,
   "stages": [
    {
     "default": False,
     "from": 16,
     "locked": False,
     "stage": "alpha",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 29
    }
   ]
  },
  "RequestManagement": {
   "removed_in": 18,
   "stages": [
    {
     "default": False,
     "from": 15,
     "locked": False,
     "stage": "alpha",
     "to": 16
    },
    {
     "default": False,
     "from": 17,
     "locked": False,
     "stage": "deprecated",
     "to": 17
    }
   ]
  },
  "ResilientWatchCacheInitialization": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ResourceHealthStatus": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "ResourceLimitsPriorityFunction": {
   "removed_in": 20,
   "stages": [
    {
     "default": False,
     "from": 9,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": False,
     "from": 19,
     "locked": False,
     "stage": "deprecated",
     "to": 19
    }
   ]
  },
  "ResourceQuotaScopeSelectors": {
   "removed_in": 19,
   "stages": [
    {
     "default": False,
     "from": 11,
     "locked": False,
     "stage": "alpha",
     "to": 11
    },
    {
     "default": True,
     "from": 12,
     "locked": False,
     "stage": "beta",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "stable",
     "to": 18
    }
   ]
  },
  "RestartAllContainersOnContainerExits": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "RetroactiveDefaultStorageClass": {
   "removed_in": 29,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "stable",
     "to": 28
    }
   ]
  },
  "RetryGenerateName": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "RootCAConfigMap": {
   "removed_in": 23,
   "stages": [
    {
     "default": False,
     "from": 13,
     "locked": False,
     "stage": "alpha",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "beta",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "stable",
     "to": 22
    }
   ]
  },
  "RotateKubeletClientCertificate": {
   "removed_in": 22,
   "stages": [
    {
     "default": True,
     "from": 8,
     "locked": False,
     "stage": "beta",
     "to": 18
    },
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "stable",
     "to": 21
    }
   ]
  },
  "RotateKubeletServerCertificate": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 7,
     "locked": False,
     "stage": "alpha",
     "to": 11
    },
    {
     "default": True,
     "from": 12,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "RunAsGroup": {
   "removed_in": 23,
   "stages": [
    {
     "default": True,
     "from": 14,
     "locked": False,
     "stage": "beta",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "stable",
     "to": 22
    }
   ]
  },
  "RuntimeClass": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 12,
     "locked": False,
     "stage": "alpha",
     "to": 13
    },
    {
     "default": True,
     "from": 14,
     "locked": False,
     "stage": "beta",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "RuntimeClassInImageCriApi": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "SCTPSupport": {
   "removed_in": 23,
   "stages": [
    {
     "default": False,
     "from": 12,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "stable",
     "to": 22
    }
   ]
  },
  "SELinuxChangePolicy": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "SELinuxMount": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "SELinuxMountReadWriteOncePod": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": False,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ScheduleDaemonSetPods": {
   "removed_in": 19,
   "stages": [
    {
     "default": False,
     "from": 11,
     "locked": False,
     "stage": "alpha",
     "to": 11
    },
    {
     "default": True,
     "from": 12,
     "locked": False,
     "stage": "beta",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "stable",
     "to": 18
    }
   ]
  },
  "SchedulerAsyncAPICalls": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "SchedulerAsyncPreemption": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "SchedulerPopFromBackoffQ": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "SchedulerQueueingHints": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "beta",
     "to": 28
    },
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "SeccompDefault": {
   "removed_in": 29,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "beta",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "stable",
     "to": 28
    }
   ]
  },
  "SecurityContextDeny": {
   "removed_in": 30,
   "stages": [
    {
     "default": False,
     "from": 27,
     "locked": False,
     "stage": "alpha",
     "to": 29
    }
   ]
  },
  "SelectorIndex": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 18,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "SeparateCacheWatchRPC": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "SeparateTaintEvictionController": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ServerSideApply": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "alpha",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  },
  "ServerSideFieldValidation": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "beta",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  },
  "ServiceAccountIssuerDiscovery": {
   "removed_in": 24,
   "stages": [
    {
     "default": False,
     "from": 18,
     "locked": False,
     "stage": "alpha",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "beta",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "stable",
     "to": 23
    }
   ]
  },
  "ServiceAccountNodeAudienceRestriction": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "ServiceAccountTokenJTI": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ServiceAccountTokenNodeBinding": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ServiceAccountTokenNodeBindingValidation": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ServiceAccountTokenPodNodeInfo": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ServiceAppProtocol": {
   "removed_in": 23,
   "stages": [
    {
     "default": False,
     "from": 18,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "stable",
     "to": 22
    }
   ]
  },
  "ServiceIPStaticSubrange": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 24,
     "locked": False,
     "stage": "alpha",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "beta",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "stable",
     "to": 27
    }
   ]
  },
  "ServiceInternalTrafficPolicy": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "stable",
     "to": 27
    }
   ]
  },
  "ServiceLBNodePortControl": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "ServiceLoadBalancerClass": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "ServiceLoadBalancerFinalizer": {
   "removed_in": 21,
   "stages": [
    {
     "default": False,
     "from": 15,
     "locked": False,
     "stage": "alpha",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "beta",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "stable",
     "to": 20
    }
   ]
  },
  "ServiceNodeExclusion": {
   "removed_in": 23,
   "stages": [
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "alpha",
     "to": 18
    },
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "stable",
     "to": 22
    }
   ]
  },
  "ServiceNodePortStaticSubrange": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 27,
     "locked": False,
     "stage": "alpha",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "beta",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "stable",
     "to": 30
    }
   ]
  },
  "ServiceTopology": {
   "removed_in": 23,
   "stages": [
    {
     "default": False,
     "from": 17,
     "locked": False,
     "stage": "alpha",
     "to": 19
    },
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "deprecated",
     "to": 22
    }
   ]
  },
  "ServiceTrafficDistribution": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "SetHostnameAsFQDN": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 19,
     "locked": False,
     "stage": "alpha",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "ShardedListAndWatch": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "SidecarContainers": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "SizeBasedListCostEstimate": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "SizeMemoryBackedVolumes": {
   "removed_in": 35,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": True,
     "stage": "stable",
     "to": 34
    }
   ]
  },
  "SkipReadOnlyValidationGCE": {
   "removed_in": 31,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "deprecated",
     "to": 30
    }
   ]
  },
  "StableLoadBalancerNodeSet": {
   "removed_in": 32,
   "stages": [
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  },
  "StaleControllerConsistencyDaemonSet": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "StaleControllerConsistencyJob": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "StaleControllerConsistencyReplicaSet": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "StaleControllerConsistencyStatefulSet": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "StartupProbe": {
   "removed_in": 24,
   "stages": [
    {
     "default": False,
     "from": 16,
     "locked": False,
     "stage": "alpha",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "beta",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "stable",
     "to": 23
    }
   ]
  },
  "StatefulSetAutoDeletePVC": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "StatefulSetMinReadySeconds": {
   "removed_in": 27,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": 24
    },
    {
     "default": True,
     "from": 25,
     "locked": False,
     "stage": "stable",
     "to": 26
    }
   ]
  },
  "StatefulSetRecreateStrategy": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "StatefulSetStartOrdinal": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "beta",
     "to": 30
    },
    {
     "default": True,
     "from": 31,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "StorageCapacityScoring": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "StorageNamespaceIndex": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "StorageObjectInUseProtection": {
   "removed_in": 25,
   "stages": [
    {
     "default": True,
     "from": 10,
     "locked": False,
     "stage": "beta",
     "to": 10
    },
    {
     "default": True,
     "from": 11,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "StorageVersionAPI": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 20,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "StorageVersionHash": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "alpha",
     "to": 14
    },
    {
     "default": True,
     "from": 15,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "StorageVersionMigrator": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "alpha",
     "to": 34
    },
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "StreamingCollectionEncodingToJSON": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "StreamingCollectionEncodingToProtobuf": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "StreamingProxyRedirects": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 5,
     "locked": False,
     "stage": "beta",
     "to": 5
    },
    {
     "default": True,
     "from": 6,
     "locked": False,
     "stage": "beta",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "deprecated",
     "to": 21
    },
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "deprecated",
     "to": 24
    }
   ]
  },
  "StrictCostEnforcementForVAP": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "StrictCostEnforcementForWebhooks": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "StrictIPCIDRValidation": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "StructuredAuthenticationConfiguration": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "StructuredAuthenticationConfigurationEgressSelector": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "StructuredAuthenticationConfigurationJWKSMetrics": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "StructuredAuthorizationConfiguration": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "SupplementalGroupsPolicy": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "SupportIPVSProxyMode": {
   "removed_in": 21,
   "stages": [
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "alpha",
     "to": 8
    },
    {
     "default": False,
     "from": 9,
     "locked": False,
     "stage": "beta",
     "to": 9
    },
    {
     "default": True,
     "from": 10,
     "locked": False,
     "stage": "beta",
     "to": 10
    },
    {
     "default": True,
     "from": 11,
     "locked": False,
     "stage": "stable",
     "to": 20
    }
   ]
  },
  "SupportNodePidsLimit": {
   "removed_in": 24,
   "stages": [
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "alpha",
     "to": 14
    },
    {
     "default": True,
     "from": 15,
     "locked": False,
     "stage": "beta",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "stable",
     "to": 23
    }
   ]
  },
  "SupportPodPidsLimit": {
   "removed_in": 24,
   "stages": [
    {
     "default": False,
     "from": 10,
     "locked": False,
     "stage": "alpha",
     "to": 13
    },
    {
     "default": True,
     "from": 14,
     "locked": False,
     "stage": "beta",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "stable",
     "to": 23
    }
   ]
  },
  "SuspendJob": {
   "removed_in": 26,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "stable",
     "to": 25
    }
   ]
  },
  "Sysctls": {
   "removed_in": 23,
   "stages": [
    {
     "default": True,
     "from": 11,
     "locked": False,
     "stage": "beta",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "stable",
     "to": 22
    }
   ]
  },
  "SystemdWatchdog": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "TTLAfterFinished": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 12,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "beta",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "TaintBasedEvictions": {
   "removed_in": 21,
   "stages": [
    {
     "default": False,
     "from": 6,
     "locked": False,
     "stage": "alpha",
     "to": 12
    },
    {
     "default": True,
     "from": 13,
     "locked": False,
     "stage": "beta",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "stable",
     "to": 20
    }
   ]
  },
  "TaintNodesByCondition": {
   "removed_in": 19,
   "stages": [
    {
     "default": False,
     "from": 8,
     "locked": False,
     "stage": "alpha",
     "to": 11
    },
    {
     "default": True,
     "from": 12,
     "locked": False,
     "stage": "beta",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "stable",
     "to": 18
    }
   ]
  },
  "TaintTolerationComparisonOperators": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "TokenRequest": {
   "removed_in": 22,
   "stages": [
    {
     "default": False,
     "from": 10,
     "locked": False,
     "stage": "alpha",
     "to": 11
    },
    {
     "default": True,
     "from": 12,
     "locked": False,
     "stage": "beta",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "stable",
     "to": 21
    }
   ]
  },
  "TokenRequestProjection": {
   "removed_in": 22,
   "stages": [
    {
     "default": False,
     "from": 11,
     "locked": False,
     "stage": "alpha",
     "to": 11
    },
    {
     "default": True,
     "from": 12,
     "locked": False,
     "stage": "beta",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "stable",
     "to": 21
    }
   ]
  },
  "TokenRequestServiceAccountUIDValidation": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "TopologyAwareHints": {
   "removed_in": 36,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 22
    },
    {
     "default": False,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": 23
    },
    {
     "default": True,
     "from": 24,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": True,
     "stage": "stable",
     "to": 35
    }
   ]
  },
  "TopologyAwareWorkloadScheduling": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "TopologyManager": {
   "removed_in": 29,
   "stages": [
    {
     "default": False,
     "from": 16,
     "locked": False,
     "stage": "alpha",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "beta",
     "to": 26
    },
    {
     "default": True,
     "from": 27,
     "locked": False,
     "stage": "stable",
     "to": 28
    }
   ]
  },
  "TopologyManagerPolicyAlphaOptions": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "TopologyManagerPolicyBetaOptions": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "beta",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "TopologyManagerPolicyOptions": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": 27
    },
    {
     "default": True,
     "from": 28,
     "locked": False,
     "stage": "beta",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "TranslateStreamCloseWebsocketRequests": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "UnauthenticatedHTTP2DOSMitigation": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "beta",
     "to": 28
    },
    {
     "default": True,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "UnknownVersionInteroperabilityProxy": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "UnlockWhileProcessingFIFO": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "UserNamespacesHostNetworkSupport": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "UserNamespacesPodSecurityStandards": {
   "removed_in": 35,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 34
    }
   ]
  },
  "UserNamespacesStatelessPodsSupport": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 25,
     "locked": False,
     "stage": "alpha",
     "to": 27
    }
   ]
  },
  "UserNamespacesSupport": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "alpha",
     "to": 29
    },
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "ValidateProxyRedirects": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 12,
     "locked": False,
     "stage": "alpha",
     "to": 13
    },
    {
     "default": True,
     "from": 14,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "deprecated",
     "to": 24
    }
   ]
  },
  "ValidatingAdmissionPolicy": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": 27
    },
    {
     "default": False,
     "from": 28,
     "locked": False,
     "stage": "beta",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  },
  "VolumeAttributesClass": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "alpha",
     "to": 30
    },
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "stable",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "VolumeBindMountOptions": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 37,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "VolumeCapacityPriority": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 21,
     "locked": False,
     "stage": "alpha",
     "to": 32
    }
   ]
  },
  "VolumeLimitScaling": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 35,
     "locked": False,
     "stage": "alpha",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "VolumePVCDataSource": {
   "removed_in": 22,
   "stages": [
    {
     "default": False,
     "from": 15,
     "locked": False,
     "stage": "alpha",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "beta",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "stable",
     "to": 21
    }
   ]
  },
  "VolumeScheduling": {
   "removed_in": 17,
   "stages": [
    {
     "default": False,
     "from": 9,
     "locked": False,
     "stage": "alpha",
     "to": 9
    },
    {
     "default": True,
     "from": 10,
     "locked": False,
     "stage": "beta",
     "to": 12
    },
    {
     "default": True,
     "from": 13,
     "locked": False,
     "stage": "stable",
     "to": 16
    }
   ]
  },
  "VolumeSnapshotDataSource": {
   "removed_in": 23,
   "stages": [
    {
     "default": False,
     "from": 12,
     "locked": False,
     "stage": "alpha",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "beta",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "stable",
     "to": 22
    }
   ]
  },
  "VolumeSubpath": {
   "removed_in": 25,
   "stages": [
    {
     "default": True,
     "from": 10,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "VolumeSubpathEnvExpansion": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "alpha",
     "to": 14
    },
    {
     "default": True,
     "from": 15,
     "locked": False,
     "stage": "beta",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "WarningHeaders": {
   "removed_in": 25,
   "stages": [
    {
     "default": True,
     "from": 19,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "WatchBookmark": {
   "removed_in": 33,
   "stages": [
    {
     "default": False,
     "from": 15,
     "locked": False,
     "stage": "alpha",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "beta",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "stable",
     "to": 32
    }
   ]
  },
  "WatchCacheInitializationPostStartHook": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 31,
     "locked": False,
     "stage": "beta",
     "to": 35
    },
    {
     "default": True,
     "from": 36,
     "locked": False,
     "stage": "beta",
     "to": 36
    },
    {
     "default": True,
     "from": 37,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "WatchFromStorageWithoutResourceVersion": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "WatchList": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 27,
     "locked": False,
     "stage": "alpha",
     "to": 31
    },
    {
     "default": True,
     "from": 32,
     "locked": False,
     "stage": "beta",
     "to": 32
    },
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "WatchListClient": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 30,
     "locked": False,
     "stage": "beta",
     "to": 34
    },
    {
     "default": True,
     "from": 35,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "WatchListCompression": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 37,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "WinDSR": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": True,
     "from": 33,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "WinOverlay": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "alpha",
     "to": 19
    },
    {
     "default": True,
     "from": 20,
     "locked": False,
     "stage": "beta",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": True,
     "stage": "stable",
     "to": None
    }
   ]
  },
  "WindowsCPUAndMemoryAffinity": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "WindowsEndpointSliceProxying": {
   "removed_in": 25,
   "stages": [
    {
     "default": False,
     "from": 19,
     "locked": False,
     "stage": "alpha",
     "to": 20
    },
    {
     "default": True,
     "from": 21,
     "locked": False,
     "stage": "beta",
     "to": 21
    },
    {
     "default": True,
     "from": 22,
     "locked": False,
     "stage": "stable",
     "to": 24
    }
   ]
  },
  "WindowsGMSA": {
   "removed_in": 19,
   "stages": [
    {
     "default": False,
     "from": 14,
     "locked": False,
     "stage": "alpha",
     "to": 15
    },
    {
     "default": True,
     "from": 16,
     "locked": False,
     "stage": "beta",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "stable",
     "to": 18
    }
   ]
  },
  "WindowsGracefulNodeShutdown": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 32,
     "locked": False,
     "stage": "alpha",
     "to": 33
    },
    {
     "default": True,
     "from": 34,
     "locked": False,
     "stage": "beta",
     "to": None
    }
   ]
  },
  "WindowsHostNetwork": {
   "removed_in": None,
   "stages": [
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "alpha",
     "to": 32
    },
    {
     "default": False,
     "from": 33,
     "locked": False,
     "stage": "deprecated",
     "to": None
    }
   ]
  },
  "WindowsHostProcessContainers": {
   "removed_in": 28,
   "stages": [
    {
     "default": False,
     "from": 22,
     "locked": False,
     "stage": "alpha",
     "to": 22
    },
    {
     "default": True,
     "from": 23,
     "locked": False,
     "stage": "beta",
     "to": 25
    },
    {
     "default": True,
     "from": 26,
     "locked": False,
     "stage": "stable",
     "to": 27
    }
   ]
  },
  "WindowsRunAsUserName": {
   "removed_in": 21,
   "stages": [
    {
     "default": False,
     "from": 16,
     "locked": False,
     "stage": "alpha",
     "to": 16
    },
    {
     "default": True,
     "from": 17,
     "locked": False,
     "stage": "beta",
     "to": 17
    },
    {
     "default": True,
     "from": 18,
     "locked": False,
     "stage": "stable",
     "to": 20
    }
   ]
  },
  "WorkloadAwarePreemption": {
   "removed_in": 37,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": 36
    }
   ]
  },
  "WorkloadWithJob": {
   "removed_in": None,
   "stages": [
    {
     "default": False,
     "from": 36,
     "locked": False,
     "stage": "alpha",
     "to": None
    }
   ]
  },
  "ZeroLimitedNominalConcurrencyShares": {
   "removed_in": 32,
   "stages": [
    {
     "default": False,
     "from": 29,
     "locked": False,
     "stage": "beta",
     "to": 29
    },
    {
     "default": True,
     "from": 30,
     "locked": False,
     "stage": "stable",
     "to": 31
    }
   ]
  }
 },
 "generated": "2026-11-11",
 "latest_minor": 37,
 "releases": {
  "24": {
   "action": [],
   "deprecations": [
    {
     "prs": [
      107235
     ],
     "text": "Deprecated `Service.Spec.LoadBalancerIP`. This field was under-specified and its meaning varies across implementations. As of Kubernetes v1.24, users are encouraged to use implementation-specific annotations when available. This field may be removed in a future API version."
    },
    {
     "prs": [
      108062
     ],
     "text": "Kube-apiserver: the `--master-count` flag and `--endpoint-reconciler-type=master-count` reconciler are deprecated in favor of the lease reconciler"
    },
    {
     "prs": [
      106859
     ],
     "text": "Kube-apiserver: the insecure address flags `--address`, `--insecure-bind-address`, `--port` and `--insecure-port` (inert since 1.20) are removed"
    },
    {
     "prs": [
      108027
     ],
     "text": "Kubeadm: graduated the `UnversionedKubeletConfigMap` feature gate to Beta and enabled the feature by default. This implies that 1) for new clusters kubeadm will start using the `kube-system/kubelet-config` naming scheme for the kubelet ConfigMap and RBAC rules, instead of the legacy `kubelet-config-x.yy` naming. 2) during upgrade, kubeadm will only write the new scheme ConfigMap and RBAC objects. To disable the feature you can pass `UnversionedKubeletConfigMap: False` in the kubeadm config for new clusters. For upgrade on existing clusters you can also override the behavior by patching the ClusterConfiguration object in `kube-system/kubeadm-config`. More details in the associated KEP."
    },
    {
     "prs": [
      108020
     ],
     "text": "Remove `tolerate-unready-endpoints` annotation in Service deprecated from 1.11, use `Service.spec.publishNotReadyAddresses` instead."
    },
    {
     "prs": [
      106830
     ],
     "text": "Remove deprecated feature gates `ValidateProxyRedirects` and `StreamingProxyRedirects`"
    },
    {
     "prs": [
      108953
     ],
     "text": "Remove insecure serving configuration from cloud-provider package, which is consumed by cloud-controller-managers."
    },
    {
     "prs": [
      108045
     ],
     "text": "The `--pod-infra-container-image` kubelet flag is deprecated and will be removed in future releases"
    },
    {
     "prs": [
      108616
     ],
     "text": "The `client.authentication.k8s.io/v1alpha1` ExecCredential has been removed. If you are using a client-go credential plugin that relies on the v1alpha1 API please contact the distributor of your plugin for instructions on how to migrate to the v1 API."
    },
    {
     "prs": [
      103061
     ],
     "text": "The `node.k8s.io/v1alpha1` RuntimeClass API is no longer served. Use the `node.k8s.io/v1` API version, available since v1.20"
    },
    {
     "prs": [
      107481
     ],
     "text": "The cluster addon for dashboard was removed. To install dashboard, see here."
    },
    {
     "prs": [
      107904
     ],
     "text": "The in-tree Azure plugin has been deprecated. The Azure kubelogin plugin serves as an out-of-tree replacement via the kubectl/client-go credential plugin mechanism. Users will now see a warning in the logs regarding this deprecation."
    },
    {
     "prs": [
      106860
     ],
     "text": "The insecure address flags `--address` and `--port` in kube-controller-manager have had no effect since v1.20 and are removed in v1.24."
    },
    {
     "prs": [
      108717
     ],
     "text": "The metadata.clusterName field is deprecated. This field has always been unwritable and always blank, but its presence is confusing, so we will remove it next release. Out of an abundance of caution, this release we have merely changed the name in the go struct to ensure any accidental client uses are found before complete removal."
    },
    {
     "prs": [
      109089
     ],
     "text": "VSphere releases less than 7.0u2 are deprecated as of v1.24. Please consider upgrading vSphere to 7.0u2 or above. vSphere CSI Driver requires minimum vSphere 7.0u2. General Support for vSphere 6.7 will end on October 15, 2022. vSphere 6.7 Update 3 is deprecated in Kubernetes v1.24. Customers are recommended to upgrade vSphere (both ESXi and vCenter) to 7.0u2 or above. vSphere CSI Driver 2.2.3 and higher supports CSI Migration. Support for these deprecations will be available till October 15, 2022."
    }
   ],
   "released": True,
   "removed_flags": [
    {
     "component": "?",
     "flag": "--deserialization-cache-size",
     "prs": [
      108448
     ]
    },
    {
     "component": "?",
     "flag": "--experimental-encryption-provider-config",
     "prs": [
      108423
     ]
    },
    {
     "component": "?",
     "flag": "--really-crash-for-testing",
     "prs": [
      101719
     ]
    },
    {
     "component": "?",
     "flag": "--target-ram-mb",
     "prs": [
      108457
     ]
    },
    {
     "component": "kubectl",
     "flag": "--hostport",
     "prs": [
      108820
     ]
    },
    {
     "component": "kubectl",
     "flag": "--limits",
     "prs": [
      108820
     ]
    },
    {
     "component": "kubectl",
     "flag": "--requests",
     "prs": [
      108820
     ]
    },
    {
     "component": "kubectl",
     "flag": "--serviceaccount",
     "prs": [
      108820
     ]
    },
    {
     "component": "kubelet",
     "flag": "--experimental-check-node-capabilities-before-mount",
     "prs": [
      104732
     ]
    },
    {
     "component": "kubelet",
     "flag": "--non-masquerade-cidr",
     "prs": [
      107096
     ]
    }
   ],
   "urgent": [
    {
     "prs": [
      97252
     ],
     "text": "Docker runtime support using dockershim in the kubelet is now completely removed in 1.24. The kubelet used to have a module called dockershim, which implements CRI support for Docker, and it has seen maintenance issues in the Kubernetes community. From 1.24 onwards, please move to a container runtime that is a full-fledged implementation of CRI (v1alpha1 or v1 compliant) as they become available."
    },
    {
     "prs": [
      101028
     ],
     "text": "Fixed bug with leads to Node goes `Not-ready` state when credentials for vCenter stored in a secret and Zones feature is in use. Zone labels setup moved to KCM component, kubelet skips this step during startup in such case. If credentials stored in cloud-provider config file as plaintext current behaviour does not change and no action required. For proper functioning `kube-system:vsphere-legacy-cloud-provider` should be allowed to update node object if vCenter credentials stored in secret and Zone feature used."
    },
    {
     "prs": [
      108309
     ],
     "text": "The `LegacyServiceAccountTokenNoAutoGeneration` feature gate is beta, and enabled by default. When enabled, Secret API objects containing service account tokens are no longer auto-generated for every ServiceAccount. Use the TokenRequest API to acquire service account tokens, or if a non-expiring token is required, create a Secret API object for the token controller to populate with a service account token by following this guide."
    },
    {
     "prs": [
      107009
     ],
     "text": "The calculations for Pod topology spread skew now exclude nodes that don't match the node affinity/selector. This may lead to unschedulable pods if you previously had pods matching the spreading selector on those excluded nodes (not matching the node affinity/selector), especially when the `topologyKey` is not node-level. Revisit the node affinity and/or pod selector in the topology spread constraints to avoid this scenario."
    },
    {
     "prs": [
      104732
     ],
     "text": "Remove the deprecated flag `--experimental-check-node-capabilities-before-mount`. With CSI now GA, there is a better alternative. Remove any use of `--experimental-check-node-capabilities-before-mount` from your kubelet scripts or manifests."
    },
    {
     "prs": [
      107013
     ],
     "text": "`kubeadm.k8s.io/v1beta2` has been deprecated and will be removed in a future release, possibly in 3 releases (one year). You should start using `kubeadm.k8s.io/v1beta3` for new clusters. To migrate your old configuration files on disk you can use the `kubeadm config migrate` command."
    },
    {
     "prs": [
      107317
     ],
     "text": "Kubeadm: default the kubeadm configuration to the containerd socket (Unix: `unix:///var/run/containerd/containerd.sock`, Windows: `npipe:////./pipe/containerd-containerd`) instead of the one for Docker. If the `Init|JoinConfiguration.nodeRegistration.criSocket` field is empty during cluster creation and multiple sockets are found on the host always throw an error and ask the user to specify which one to use by setting the value in the field. Make sure you update any kubeadm configuration files on disk, to not include the dockershim socket unless you are still using kubelet version < 1.24 with kubeadm >= 1.24. Remove the DockerValidor and ServiceCheck for the `docker` service from kubeadm preflight. Docker is no longer special cased during host validation and ideally this task should be done in the now external cri-dockerd project where the importance of the compatibility matters. Use `crictl` for all communication with CRI sockets for actions like pulling images and obtaining a list of running containers instead of using the docker CLI in the case of Docker."
    },
    {
     "prs": [
      107554
     ],
     "text": "The feature gate was mentioned as `csiMigrationRBD` where it should have been `CSIMigrationRBD` to be in parity with other migration plugins. This release correct the same and keep it as `CSIMigrationRBD`. users who have configured this feature gate as `csiMigrationRBD` has to reconfigure the same to `CSIMigrationRBD` from this release."
    },
    {
     "prs": [
      107207
     ],
     "text": "The experimental dynamic log sanitization feature has been deprecated and removed in the 1.24 release. The feature is no longer available for use."
    },
    {
     "prs": [
      107533
     ],
     "text": "Kubeadm: apply `second stage` of the plan to migrate kubeadm away from the usage of the word `master` in labels and taints. For new clusters, the label `node-role.kubernetes.io/master` will no longer be added to control plane nodes, only the label `node-role.kubernetes.io/control-plane` will be added. For clusters that are being upgraded to 1.24 with `kubeadm upgrade apply`, the command will remove the label `node-role.kubernetes.io/master` from existing control plane nodes. For new clusters, both the old taint `node-role.kubernetes.io/master:NoSchedule` and new taint `node-role.kubernetes.io/control-plane:NoSchedule` will be added to control plane nodes. In release 1.20 (`first stage`), a release note instructed to preemptively tolerate the new taint. For clusters that are being upgraded to 1.24 with `kubeadm upgrade apply`, the command will add the new taint `node-role.kubernetes.io/control-plane:NoSchedule` to existing control plane nodes. Please adapt your infrastructure to these changes. In 1.25 the old taint `node-role.kubernetes.io/master:NoSchedule` will be removed."
    }
   ]
  },
  "25": {
   "action": [],
   "deprecations": [
    {
     "prs": [
      108624
     ],
     "text": "API server's deprecated `--service-account-api-audiences` flag was removed. Use `--api-audiences` instead."
    },
    {
     "prs": [
      111065
     ],
     "text": "Ginkgo.Measure has been deprecated in Ginkgo V2, switch to use gomega/gmeasure instead"
    },
    {
     "prs": [
      109612
     ],
     "text": "Kube-controller-manager: Removed flags `deleting-pods-qps`, `deleting-pods-burst`, and `register-retry-count`."
    },
    {
     "prs": [
      110343
     ],
     "text": "Kubeadm: during \"upgrade apply/diff/node\", in case the `ClusterConfiguration.imageRepository` stored in the \"kubeadm-config\" `ConfigMap` contains the legacy \"k8s.gcr.io\" repository, modify it to the new default \"registry.k8s.io\". Reflect the change in the in-cluster `ConfigMap` only during \"upgrade apply\"."
    },
    {
     "prs": [
      110327
     ],
     "text": "Kubeadm: graduated the kubeadm specific feature gate `UnversionedKubeletConfigMap` to GA and locked it to `true` by default. The kubelet related ConfigMap and RBAC rules are now locked to have a simplified naming `*kubelet-config` instead of the legacy naming `*kubelet-config-x.yy`, where `x.yy` was the version of the control plane. If you have previously used the old naming format with `UnversionedKubeletConfigMap=false`, you must manually copy the config map from `kube-system/kubelet-config-x.yy` to `kube-system/kubelet-config` before upgrading to `v1.25`."
    },
    {
     "prs": [
      110095
     ],
     "text": "Kubeadm: stop applying the `node-role.kubernetes.io/master:NoSchedule` taint to control plane nodes for new clusters. Remove the taint from existing control plane nodes during \"kubeadm upgrade apply\""
    },
    {
     "prs": [
      109819
     ],
     "text": "Support for the alpha seccomp annotations `seccomp.security.alpha.kubernetes.io/pod` and `container.seccomp.security.alpha.kubernetes.io`, deprecated since v1.19, was partially removed. Kubelets no longer support the annotations, use of the annotations in static pods is no longer supported, and the seccomp annotations are no longer auto-populated when pods with seccomp fields are created. Auto-population of the seccomp fields from the annotations is planned to be removed in 1.27. Pods should use the corresponding pod or container `securityContext.seccompProfile` field instead."
    },
    {
     "prs": [
      110013
     ],
     "text": "The `gcp` and `azure` auth plugins have been removed from client-go and kubectl. See https://github.com/Azure/kubelogin and https://cloud.google.com/blog/products/containers-kubernetes/kubectl-auth-changes-in-gke"
    },
    {
     "prs": [
      109798
     ],
     "text": "The beta `PodSecurityPolicy` admission plugin, deprecated since 1.21, is removed. Follow the instructions at https://kubernetes.io/docs/tasks/configure-pod-container/migrate-from-psp/ to migrate to the built-in PodSecurity admission plugin (or to another third-party policy webhook) prior to upgrading to v1.25."
    },
    {
     "prs": [
      111255
     ],
     "text": "VSphere releases less than 7.0u2 are not supported for in-tree vSphere volume as of Kubernetes v1.25. Please consider upgrading vSphere (both ESXi and vCenter) to 7.0u2 or above."
    },
    {
     "prs": [
      110957
     ],
     "text": "Windows winkernel kube-proxy no longer supports Windows HNS v1 APIs."
    },
    {
     "prs": [
      111485
     ],
     "text": "GlusterFS provisioner (`kubernetes.io/glusterfs`) has been deprecated in this release."
    }
   ],
   "released": True,
   "removed_flags": [
    {
     "component": "?",
     "flag": "--experimental-kernel-memcg-notification",
     "prs": [
      109388
     ]
    },
    {
     "component": "?",
     "flag": "--service-account-api-audiences",
     "prs": [
      108624
     ]
    },
    {
     "component": "kube-controller-manager",
     "flag": "--experimental-cluster-signing-duration",
     "prs": [
      108476
     ]
    }
   ],
   "urgent": [
    {
     "prs": [
      108797
     ],
     "text": "Deprecated beta APIs scheduled for removal in 1.25 are no longer served. See https://kubernetes.io/docs/reference/using-api/deprecation-guide/#v1-25 for more information."
    },
    {
     "prs": [
      111119
     ],
     "text": "Encrypted data with DEK using AES-GCM instead of AES-CBC for kms data encryption. No user action required. Reads with AES-GCM and AES-CBC will continue to be allowed."
    },
    {
     "prs": [
      109111
     ],
     "text": "End-to-end testing has been migrated from Ginkgo v1 to v2. When running test/e2e via the Ginkgo CLI, the v2 CLI must be used and `-timeout=24h` (or some other, suitable value) must be passed because the default timeout was reduced from 24h to 1h. When running it via `go test`, the corresponding `-args` parameter is `-ginkgo.timeout=24h`. To build the CLI in the Kubernetes repo, use `make all WHAT=github.com/onsi/ginkgo/v2/ginkgo`. Ginkgo V2 doesn't accept go test's `-parallel` flags to parallelize Ginkgo specs, please switch to use `ginkgo -p` or `ginkgo -procs=N` instead."
    },
    {
     "prs": [
      110333
     ],
     "text": "No action required; No API/CLI changed; Add new Windows Image Support"
    },
    {
     "prs": [
      111618
     ],
     "text": "The intree volume plugin flocker support was completely removed from Kubernetes."
    },
    {
     "prs": [
      111619
     ],
     "text": "The intree volume plugin quobyte support has been completely removed from Kubernetes."
    },
    {
     "prs": [
      111620
     ],
     "text": "The intree volume plugin storageos support has been completely removed from Kubernetes."
    },
    {
     "prs": [
      109938
     ],
     "text": "There is a new OCI image registry (`registry.k8s.io`) that can be used to pull Kubernetes images. The old registry (`k8s.gcr.io`) will continue to be supported for the foreseeable future, but the new name should perform better because it frontends equivalent mirrors in other clouds. Please point your clusters to the new registry going forward. \\n\\nAdmission/Policy integrations that have an allowlist of registries need to include `registry.k8s.io` alongside `k8s.gcr.io`.\\nAir-gapped environments and image garbage-collection configurations will need to update to pre-pull and preserve required images under `registry.k8s.io` as well as `k8s.gcr.io`."
    }
   ]
  },
  "26": {
   "action": [],
   "deprecations": [
    {
     "prs": [
      113710
     ],
     "text": "CLI flag `pod-eviction-timeout` is deprecated and will be removed together with `enable-taint-manager` in v1.27."
    },
    {
     "prs": [
      112797
     ],
     "text": "Kube-apiserver: the unused `--master-service-namespace` flag was deprecated and will be removed in v1.27."
    },
    {
     "prs": [
      112341
     ],
     "text": "The `gcp` and `azure` auth plugins have been removed from `client-go` and `kubectl`. See kubelogin and Kubectl Auth Changes in GKE for details about the cloud-specific replacements."
    }
   ],
   "released": True,
   "removed_flags": [],
   "urgent": [
    {
     "prs": [
      111973
     ],
     "text": "Deprecated beta APIs scheduled for removal in `v1.26` are no longer served. See https://kubernetes.io/docs/reference/using-api/deprecation-guide/#v1-26 for more information."
    },
    {
     "prs": [
      67782
     ],
     "text": "The in-tree cloud provider for OpenStack (and the cinder volume provider) has been removed. Please use the external cloud provider and csi driver from cloud-provider-openstack instead."
    },
    {
     "prs": [
      112015
     ],
     "text": "`GlusterFS` in-tree storage driver which was deprecated in kubernetes 1.25 release is now removed entirely in `v1.26`. Volumes must be migrated to an alternate storage solution before upgrading to `v1.26`."
    }
   ]
  },
  "27": {
   "action": [],
   "deprecations": [
    {
     "prs": [
      115944
     ],
     "text": "Added a warning response when handling requests that set the deprecated `spec.externalID` field for a Node."
    },
    {
     "prs": [
      114505
     ],
     "text": "Added warnings to the Services API. Kubernetes now warns for Services in the case of: - IPv4 addresses with leading zeros - IPv6 address in non-canonical format (RFC 5952)"
    },
    {
     "prs": [
      114947
     ],
     "text": "Support for the alpha seccomp annotations `seccomp.security.alpha.kubernetes.io/pod` and `container.seccomp.security.alpha.kubernetes.io` were deprecated since v1.19, now have been completely removed. The seccomp fields are no longer auto-populated when pods with seccomp annotations are created. Pods should use the corresponding pod or container `securityContext.seccompProfile` field instead."
    },
    {
     "prs": [
      115879
     ],
     "text": "The `SecurityContextDeny` admission plugin is going deprecated and will be removed in future versions."
    }
   ],
   "released": True,
   "removed_flags": [
    {
     "component": "?",
     "flag": "--container-runtime",
     "prs": [
      114017
     ]
    },
    {
     "component": "?",
     "flag": "--enable-taint-manager",
     "prs": [
      115840
     ]
    },
    {
     "component": "?",
     "flag": "--pod-eviction-timeout",
     "prs": [
      115840
     ]
    },
    {
     "component": "kubectl",
     "flag": "--prune",
     "prs": [
      116205
     ]
    }
   ],
   "urgent": [
    {
     "prs": [
      116255
     ],
     "text": "'The `IPv6DualStack` feature gate for external cloud providers was removed. (The feature became GA in 1.23 and the gate was removed for all other components several releases ago.) If you were still manually enabling it you must stop now.'"
    },
    {
     "prs": [
      115331
     ],
     "text": "Give terminal phase correctly to all pods that will not be restarted. In particular, assign Failed phase to pods which are deleted while pending. Also, assign a terminal phase (Succeeded or Failed, depending on the exit statuses of the pod containers) to pods which are deleted while running. This fixes the issue for jobs using pod failure policy (with JobPodFailurePolicy and PodDisruptionConditions feature gates enabled) that their pods could get stuck in the pending phase when deleted. Users who maintain controllers which relied on the fact that pods with RestartPolicy=Always never enter the Succeeded phase may need to adapt their controllers. This is because as a consequence of the change pods which use RestartPolicy=Always may end up in the Succeeded phase in two scenarios: pod deletion and graceful node shutdown."
    },
    {
     "prs": [
      115838
     ],
     "text": "The in-tree cloud provider for AWS (and the EBS storage plugin) has now been removed. Please use the external cloud provider and CSI driver from https://github.com/kubernetes/cloud-provider-aws instead."
    }
   ]
  },
  "28": {
   "action": [],
   "deprecations": [
    {
     "prs": [
      116720
     ],
     "text": "Changed `kubectl version` default output to be identical to what `kubectl version --short` printed, and removed `--short` flag entirely."
    },
    {
     "prs": [
      118128
     ],
     "text": "Kube-controller-manager deprecate `--volume-host-cidr-denylist` and `--volume-host-allow-local-loopback` flags."
    },
    {
     "prs": [
      118596
     ],
     "text": "Kubelet: The `--azure-container-registry-config` flag has been deprecated and will be removed in a future release, please use `--image-credential-provider-config` and `--image-credential-provider-bin-dir` to setup acr credential provider instead."
    },
    {
     "prs": [
      117633
     ],
     "text": "Removed tracking annotation from validation and defaulting."
    },
    {
     "prs": [
      115843
     ],
     "text": "Removed withdrawn feature `NetworkPolicyStatus`."
    },
    {
     "prs": [
      119130
     ],
     "text": "The deprecated flag `--lock-object-namespace` and `--lock-object-name` have been removed from kube-scheduler. Please use `--leader-elect-resource-namespace` and `--leader-elect-resource-name` or ComponentConfig instead to configure those parameters."
    },
    {
     "prs": [
      119007
     ],
     "text": "`KMSv1` is deprecated and will only receive security updates going forward. Use `KMSv2` instead. In a future release, Set `--feature-gates=KMSv1=true` to use the deprecated KMSv1 feature."
    }
   ],
   "released": True,
   "removed_flags": [
    {
     "component": "?",
     "flag": "--feature-gates",
     "prs": [
      118018
     ]
    },
    {
     "component": "?",
     "flag": "--non-blocking-taints",
     "prs": [
      118510
     ]
    },
    {
     "component": "kube-scheduler",
     "flag": "--lock-object-name",
     "prs": [
      119130
     ]
    },
    {
     "component": "kube-scheduler",
     "flag": "--lock-object-namespace",
     "prs": [
      119130
     ]
    }
   ],
   "urgent": [
    {
     "prs": [
      118551
     ],
     "text": "Action required for the custom scheduler plugin developers. Here's the breaking change in `EnqueueExtension` in the scheduling framework. The `EventsToRegister` in `EnqueueExtension` changed the return value from `ClusterEvent` to `ClusterEventWithHint`. `ClusterEventWithHint` allows each plugin to filter out more useless events via the callback function named `QueueingHintFn`. When the scheduling queue receives a cluster event, before moving each Pod from unschedulable pod pool to activeQ/backoffQ, it will call QueueingHintFn of plugins that rejected each Pod in the previous scheduling cycle. Depending on the value returned from QueueingHintFn, the scheduling queue changes how it queues each Pod: - if more than one QueueingHintFn returns QueueImmediately, it queues Pod to activeQ. - If no QueueingHintFn returns QueueImmediately and more than one plugin returns QueueAfterBackoff, it queues Pod to backoffQ if Pod is backing off, or to activeQ if Pod's backoff has already finished. - If all QueueingHintFn return QueueSkip, it puts this pod back to the unschedulable pod pool Having appropriate QueueingHintFn contributes to reducing useless retries and thus improves the overall scheduler's performance. **How can I migrate?** For backward compatibility, nil `QueueingHintFn` is treated as always returning QueueAfterBackoff. So, if you want to just keep the existing behavior, you can register `ClusterEventWithHint` with no `QueueingHintFn` in it. But, registering appropriate `QueueingHintFn` is, of course, better from a scheduling performance perspective."
    },
    {
     "prs": [
      118143
     ],
     "text": "CephFS volume plugin (`kubernetes.io/cephfs`) has been deprecated in this release and will be removed in a subsequent release. The alternative is to use the CephFS CSI driver (https://github.com/ceph/ceph-csi/) in your Kubernetes cluster."
    },
    {
     "prs": [
      118303
     ],
     "text": "Deprecated support for CSI migration of `Ceph RBD volumes`. Users who were relying on Kubernetes' ability to migrate to an out-of-tree storage driver should complete that migration before the support for it is removed."
    },
    {
     "prs": [
      118552
     ],
     "text": "RBD volume plugin (`kubernetes.io/rbd`) has been deprecated in this release and will be removed in a subsequent release. Alternative is to use RBD CSI driver (https://github.com/ceph/ceph-csi/) in your Kubernetes Cluster."
    }
   ]
  },
  "29": {
   "action": [],
   "deprecations": [
    {
     "prs": [
      119495
     ],
     "text": "#### Additional documentation e.g., KEPs (Kubernetes Enhancement Proposals), usage docs, etc.: <!-- This section can be blank if this pull request does not require a release note. When adding links which point to resources within git repositories, like KEPs or supporting documentation, please reference a specific commit and avoid linking directly to the master branch. This ensures that links reference a specific point in time, rather than a document that may change over time. See here for guidance on getting permanent links to files: https://help.github.com/en/articles/getting-permanent-links-to-files Please use the following format for linking documentation: - [KEP]: <link> - [Usage]: <link> - [Other doc]: <link> -->"
    },
    {
     "prs": [
      116252
     ],
     "text": "Creation of new `CronJob` objects containing `TZ` or `CRON_TZ` in `.spec.schedule`, accidentally enabled in `v1.22`, is now disallowed. Use the `.spec.timeZone` field instead, supported in `v1.25+` clusters in default configurations. See https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/#unsupported-timezone-specification for more information."
    },
    {
     "prs": [
      121229
     ],
     "text": "Removed the networking `alpha` API `ClusterCIDR`."
    }
   ],
   "released": True,
   "removed_flags": [],
   "urgent": [
    {
     "prs": [
      120788
     ],
     "text": "Stopped accepting component configuration for `kube-proxy` and `kubelet` during `kubeadm upgrade plan --config`. This was a legacy behavior that was not well supported for upgrades and could be used only at the plan stage to determine if the configuration for these components stored in the cluster needs manual version migration. In the future, `kubeadm` will attempt alternative component config migration approaches."
    },
    {
     "prs": [
      121305
     ],
     "text": "`kubeadm`: a separate \"super-admin.conf\" file is now deployed. The User in `admin.conf` is now bound to a new RBAC Group `kubeadm:cluster-admins` that has `cluster-admin` `ClusterRole` access. The User in `super-admin.conf` is now bound to the `system:masters` built-in super-powers / break-glass Group that can bypass RBAC. Before this change, the default `admin.conf` was bound to `system:masters` Group, which was undesired. Executing `kubeadm init phase kubeconfig all` or just `kubeadm init` will now generate the new `super-admin.conf` file. The cluster admin can then decide to keep the file present on a node host or move it to a safe location. `kubadm certs renew` will renew the certificate in `super-admin.conf` to one year if the file exists; if it does not exist a \"MISSING\" note will be printed. `kubeadm upgrade apply` for this release will migrate this particular node to the two file setup. Subsequent kubeadm releases will continue to optionally renew the certificate in `super-admin.conf` if the file exists on disk and if renew on upgrade is not disabled. `kubeadm join --control-plane` will now generate only an `admin.conf` file that has the less privileged User."
    }
   ]
  },
  "30": {
   "action": [],
   "deprecations": [
    {
     "prs": [
      120246
     ],
     "text": "kubectl: Removed the deprecated flag `prune-whitelist` for apply. Please use the flag `prune-allowlist` instead."
    },
    {
     "prs": [
      122612
     ],
     "text": "The deprecated `SecurityContextDeny` admission plugin, which has been deprecated since `v1.27`, has been removed. It is recommended to use the Pod Security Admission plugin instead, which has been available since v1.25. Refer to the Kubernetes documentation for more information."
    }
   ],
   "released": True,
   "removed_flags": [],
   "urgent": []
  },
  "31": {
   "action": [
    {
     "prs": [
      125163
     ],
     "text": "'ACTION REQUIRED: The Dynamic Resource Allocation (DRA) driver's DaemonSet must be deployed with a service account that enables writing ResourceSlice and reading ResourceClaim objects.'"
    },
    {
     "prs": [
      126113
     ],
     "text": "ACTION REQUIRED for custom scheduler plugin developers: `EventsToRegister` in the `EnqueueExtensions` interface gets `ctx` in the parameters and `error` in the return values. Please change your plugins' implementation accordingly."
    }
   ],
   "deprecations": [
    {
     "prs": [
      124419
     ],
     "text": "'kubeadm: marked the sub-phase of ''init kubelet-finilize'' called ''experimental-cert-rotation'' as deprecated and print a warning if it is used directly; it will be removed in a future release. Add a replacement sub-phase ''enable-client-cert-rotation''.'"
    },
    {
     "prs": [
      124819
     ],
     "text": "Added a warning when creating or updating a PersistentVolume (PV) with the deprecated annotation `volume.beta.kubernetes.io/mount-options`."
    },
    {
     "prs": [
      124544
     ],
     "text": "CephFS volume plugin ( `kubernetes.io/cephfs`) was removed in this release and the `cephfs` volume type became non-functional. Alternative is to use CephFS CSI driver (https://github.com/ceph/ceph-csi/) in your Kubernetes Cluster. A re-deployment of your application is required to use the new driver if you were using `kubernetes.io/cephfs` volume plugin before upgrading cluster version to 1.31+."
    },
    {
     "prs": [
      124546
     ],
     "text": "CephRBD volume plugin ( `kubernetes.io/rbd`) was removed in this release. And its csi migration support was also removed, so the `rbd` volume type became non-functional. Alternative is to use RBD CSI driver (https://github.com/ceph/ceph-csi/) in your Kubernetes Cluster. A re-deployment of your application is required to use the new driver if you were using `kubernetes.io/rbd` volume plugin before upgrading cluster version to 1.31+."
    },
    {
     "prs": [
      124500
     ],
     "text": "Kube-scheduler deprecated all non-csi volumelimit plugins and removed those from defaults plugins. - AzureDiskLimits - CinderLimits - EBSLimits - GCEPDLimits The NodeVolumeLimits plugin can handle the same functionality as the above plugins since the above volume types are migrated to CSI. Please remove those plugins and replace them with the NodeVolumeLimits plugin if you explicitly use those plugins in the scheduler config. Those plugins will be removed in the release 1.32."
    },
    {
     "prs": [
      124997
     ],
     "text": "Kubeadm: deprecated the kubeadm `RootlessControlPlane` feature gate (previously alpha), given that the core K8s `UserNamespacesSupport` feature gate graduated to beta in 1.30. Once core Kubernetes support for user namespaces is generally available and kubeadm has started to support running the control plane in userns pods, the kubeadm `RootlessControlPlane` feature gate will be removed entirely. Until kubeadm supports the userns functionality out of the box, users can continue using the deprecated `RootlessControlPlane` feature gate, or opt-in `UserNamespacesSupport` by using kubeadm patches on the static pod manifests."
    },
    {
     "prs": [
      124767
     ],
     "text": "Removed k8s.io/legacy-cloud-providers from staging."
    },
    {
     "prs": [
      124886
     ],
     "text": "Removed legacy cloud provider integration code (undoing a previous reverted commit)."
    }
   ],
   "released": True,
   "removed_flags": [
    {
     "component": "?",
     "flag": "--iptables-drop-bit",
     "prs": [
      122363
     ]
    },
    {
     "component": "?",
     "flag": "--iptables-masquerade-bit",
     "prs": [
      122363
     ]
    },
    {
     "component": "?",
     "flag": "--keep-terminated-pod-volumes",
     "prs": [
      122082
     ]
    }
   ],
   "urgent": [
    {
     "prs": [
      122234
     ],
     "text": "Added support to the scheduler to start using QueueingHint registered for Pod/Updated event to determine whether unschedulable Pods update make them schedulable, when the feature gate `SchedulerQueueingHints` is enabled. Previously, when unschedulable Pods are updated, the scheduler always put Pods back to activeQ/backoffQ. But, actually not all updates to Pods make Pods schedulable, especially considering many scheduling constraints nowadays are immutable. Now, when unschedulable Pods are updated, the scheduling queue checks with QueueingHint(s) whether the update may make the pods schedulable, and requeues them to activeQ/backoffQ **only when** at least one QueueingHint(s) return Queue. Action required for custom scheduler plugin developers: Plugins **have to** implement a QueueingHint for Pod/Update event if the rejection from them could be resolved by updating unscheduled Pods themselves. Example: suppose you develop a custom plugin that denies Pods that have a `schedulable=false` label. Given Pods with a `schedulable=false` label will be schedulable if the `schedulable=false` label is removed, this plugin would implement QueueingHint for Pod/Update event that returns Queue when such label changes are made in unscheduled Pods."
    },
    {
     "prs": [
      122082
     ],
     "text": "Kubelet flag `--keep-terminated-pod-volumes` was removed. This flag was deprecated in 2017."
    },
    {
     "prs": [
      126108
     ],
     "text": "Reduced state change noise when volume expansion fails. Also mark certain failures as infeasible. ACTION REQUIRED: If you are using the `RecoverVolumeExpansionFailure` alpha feature gate then after upgrading to this release, you need to update some objects. For any existing PersistentVolumeClaimss with `status.allocatedResourceStatus` set to either \"ControllerResizeFailed\" or \"NodeResizeFailed\", clear the `status.allocatedResourceStatus`."
    }
   ]
  },
  "32": {
   "action": [
    {
     "prs": [
      126465
     ],
     "text": "**ACTION REQUIRED** for custom scheduler plugin developers: `PodEligibleToPreemptOthers` in the `preemption` interface now includes `ctx` in the parameters. Please update your plugins' implementation accordingly."
    }
   ],
   "deprecations": [
    {
     "prs": [
      126720
     ],
     "text": "Reverted the `DisableNodeKubeProxyVersion` feature gate to default-off to give a full year from deprecation announcement in 1.29 to clearing the field by default, per the Kubernetes deprecation policy."
    },
    {
     "prs": [
      128396
     ],
     "text": "ServiceAccount metadata.annotations[kubernetes.io/enforce-mountable-secrets]: deprecated since v1.32; no removal deadline. Prefer separate namespaces to isolate access to mounted secrets."
    }
   ],
   "released": True,
   "removed_flags": [
    {
     "component": "kubeadm",
     "flag": "--api-server-manifest",
     "prs": [
      127123
     ]
    },
    {
     "component": "kubeadm",
     "flag": "--controller-manager-manifest",
     "prs": [
      127123
     ]
    },
    {
     "component": "kubeadm",
     "flag": "--experimental-output",
     "prs": [
      126914
     ]
    },
    {
     "component": "kubeadm",
     "flag": "--feature-gates",
     "prs": [
      127123
     ]
    },
    {
     "component": "kubeadm",
     "flag": "--output",
     "prs": [
      126914
     ]
    },
    {
     "component": "kubeadm",
     "flag": "--scheduler-manifest",
     "prs": [
      127123
     ]
    },
    {
     "component": "kubelet",
     "flag": "--runonce",
     "prs": [
      126336
     ]
    }
   ],
   "urgent": []
  },
  "33": {
   "action": [],
   "deprecations": [
    {
     "prs": [
      130742
     ],
     "text": "The EndpointSlice `hints` field has graduated to GA. The beta annotation `service.kubernetes.io/topology-mode` is now considered deprecated and will not graduate to GA. It remains operational for backward compatibility. Users are encouraged to use the `spec.trafficDistribution` field in the Service API for topology-aware routing configuration."
    },
    {
     "prs": [
      128184
     ],
     "text": "The `StorageCapacityScoring` feature gate was added to score nodes by available storage capacity. It's in alpha and disabled by default. The `VolumeCapacityPriority` alpha feature was replaced with this, and the default behavior was changed. The `VolumeCapacityPriority` preferred a node with the least allocatable, but the `StorageCapacityScoring` preferred a node with the maximum allocatable. See KEP-4049 for details."
    },
    {
     "prs": [
      129930
     ],
     "text": "The `WatchFromStorageWithoutResourceVersion` feature was deprecated and can no longer be enabled."
    },
    {
     "prs": [
      130733
     ],
     "text": "The pod `status.resize` field is now deprecated and will no longer be set. The status of a pod resize will be exposed under two new conditions: `PodResizeInProgress` and `PodResizePending` instead."
    },
    {
     "prs": [
      130098
     ],
     "text": "The v1 Endpoints API is now officially deprecated (though still fully supported). The API will not be removed, but all users should use the EndpointSlice API instead."
    }
   ],
   "released": True,
   "removed_flags": [
    {
     "component": "kube-apiserver",
     "flag": "--cloud-config",
     "prs": [
      130162
     ]
    },
    {
     "component": "kube-apiserver",
     "flag": "--cloud-provider",
     "prs": [
      130162
     ]
    }
   ],
   "urgent": [
    {
     "prs": [
      130711
     ],
     "text": "Added the ability to reduce both the initial delay and the maximum delay accrued between container restarts for a node for containers in `CrashLoopBackOff` across the cluster to the recommended values of `1s` initial delay and `60s` maximum delay. To set this for a node, turn on the feature gate `ReduceDefaultCrashLoopBackOffDecay`. If you are also using the feature gate `KubeletCrashLoopBackOffMax` with a configured per-node `CrashLoopBackOff.MaxContainerRestartPeriod`, the effective kubelet configuration will follow the conflict resolution policy described further in the documentation here."
    },
    {
     "prs": [
      129370
     ],
     "text": "[Action Required] CSI drivers that call IsLikelyNotMountPoint should not assume false means that the path is a mount point. Each CSI driver needs to make sure correct usage of return value of IsLikelyNotMountPoint because if the file is an irregular file but not a mount point is acceptable"
    },
    {
     "prs": [
      130401
     ],
     "text": "Fixed the behavior of the `KUBE_PROXY_NFTABLES_SKIP_KERNEL_VERSION_CHECK` environment variable in the nftables proxier. The kernel version check is now skipped only when this variable is explicitly set to a non-empty value. To skip the check, set the `KUBE_PROXY_NFTABLES_SKIP_KERNEL_VERSION_CHECK` environment variable."
    },
    {
     "prs": [
      129023
     ],
     "text": "Renamed `UpdatePodTolerations` action type to `UpdatePodToleration`. Action required for custom plugin developers to update their code to follow the rename."
    }
   ]
  },
  "34": {
   "action": [],
   "deprecations": [
    {
     "prs": [
      132376
     ],
     "text": "Apimachinery: Deprecated `MessageCountMap` and `CreateAggregateFromMessageCountMap`."
    },
    {
     "prs": [
      132700
     ],
     "text": "DRA kubelet: gRPC API graduated to v1, v1beta1 was deprecated starting in 1.34. Updating DRA drivers to the `k8s.io/dynamic-resource-allocation/kubeletplugin` helper from 1.34 added support for both API versions."
    },
    {
     "prs": [
      131741
     ],
     "text": "Deprecated the `preferences` field in kubeconfig in favor of `kuberc`."
    },
    {
     "prs": [
      132080
     ],
     "text": "Kubeadm: Consistently prefixed errors with error: when printing them."
    },
    {
     "prs": [
      131647
     ],
     "text": "Kubeadm: Exposed only the non-deprecated klog flags (-v and -vmodule), in line with KEP https://features.k8s.io/2845."
    },
    {
     "prs": [
      131085
     ],
     "text": "[cloud-provider] Respected the `exclude-from-external-load-balancers=false` label."
    }
   ],
   "released": True,
   "removed_flags": [
    {
     "component": "?",
     "flag": "--cloud-config",
     "prs": [
      130161
     ]
    },
    {
     "component": "?",
     "flag": "--wait-interval",
     "prs": [
      132352
     ]
    },
    {
     "component": "kubeadm",
     "flag": "--container-runtime-endpoint",
     "prs": [
      131981
     ]
    },
    {
     "component": "kubelet",
     "flag": "--register-schedulable",
     "prs": [
      122384
     ]
    }
   ],
   "urgent": [
    {
     "prs": [
      131845
     ],
     "text": "For metrics `apiserver_cache_list_fetched_objects_total`, `apiserver_cache_list_returned_objects_total`, `apiserver_cache_list_total` replace `resource_prefix` label with API `group` and `resource` labels. For metrics `etcd_request_duration_seconds`, `etcd_requests_total` and `etcd_request_errors_total` replace `type` label with API `resource` and `group` label. For metric `apiserver_selfrequest_total` add a API `group` label. For metrics `apiserver_watch_events_sizes` and `apiserver_watch_events_total` replace API `kind` label with `resource` label. For metrics `apiserver_request_body_size_bytes`, `apiserver_storage_events_received_total`, `apiserver_storage_list_evaluated_objects_total`, `apiserver_storage_list_fetched_objects_total`, `apiserver_storage_list_returned_objects_total`, `apiserver_storage_list_total`, `apiserver_watch_cache_events_dispatched_total`, `apiserver_watch_cache_events_received_total`, `apiserver_watch_cache_initializations_total`, `apiserver_watch_cache_resource_version`, `watch_cache_capacity`, `apiserver_init_events_total`, `apiserver_terminated_watchers_total`, `watch_cache_capacity_increase_total`, `watch_cache_capacity_decrease_total`, `apiserver_watch_cache_read_wait_seconds`, `apiserver_watch_cache_consistent_read_total`, `apiserver_storage_consistency_checks_total`, `etcd_bookmark_counts`, `storage_decode_errors_total` extract the API group from `resource` label and put it in new `group` label."
    },
    {
     "prs": [
      130161
     ],
     "text": "Kubelet: removed the deprecated flag `--cloud-config` from the command line."
    },
    {
     "prs": [
      131837
     ],
     "text": "Static pods that reference API objects were denied admission by the kubelet so that static pods would not be silently running even after the mirror pod creation failed."
    },
    {
     "prs": [
      130720
     ],
     "text": "The Scheduling Framework exposed `NodeInfos` to the PreFilter plugins. The PreFilter plugins now accepted the `NodeInfo` list from the arguments."
    }
   ]
  },
  "35": {
   "action": [
    {
     "prs": [
      134784
     ],
     "text": "Added the `StorageVersionMigration` `v1beta1` API and removed the `v1alpha1` API. ACTION REQUIRED: The `v1alpha1` API is no longer supported. Users must remove any `v1alpha1` resources before upgrading."
    }
   ],
   "deprecations": [
    {
     "prs": [
      134298
     ],
     "text": "ACTION REQUIRED: `failCgroupV1` will be set to true from 1.35. This means that nodes will not start on a cgroup v1 by default. This puts cgroup v1 into a deprecated state."
    },
    {
     "prs": [
      134539
     ],
     "text": "Marked `ipvs` mode in kube-proxy as deprecated, which will be removed in a future version of Kubernetes. Users are encouraged to migrate to `nftables`."
    }
   ],
   "released": True,
   "removed_flags": [
    {
     "component": "kubeadm",
     "flag": "--pod-infra-container-image",
     "prs": [
      133779
     ]
    },
    {
     "component": "kubelet",
     "flag": "--pod-infra-container-image",
     "prs": [
      133779
     ]
    }
   ],
   "urgent": [
    {
     "prs": [
      133779
     ],
     "text": "ACTION REQUIRED: Removed the `--pod-infra-container-image` flag from `kubelet` command line. For `non-kubeadm` clusters, users must manually remove this flag from their `kubelet` configuration to prevent startup failures before upgrading `kubelet`. For `kubeadm` clusters, if users pass extra arguments to the `kubelet` like `--pod-infra-container-image`, it will be written to the `kubelet` env file during the `init` phase. `kubeadm` does not remove it during the `init` or `join` phase, so users must manually remove it from `extraArgs` in the `kubelet` configuration file."
    },
    {
     "prs": [
      134744
     ],
     "text": "ACTION REQUIRED: vendor: Updated `k8s.io/system-validators` to `v1.12.1`. The cgroups validator now throws an error instead of a warning if cgroups v1 is detected on the host and the provided KubeletVersion is `v1.35` or newer. kubeadm: Started using `k8s.io/system-validators` `v1.12.1` in `kubeadm` `v1.35`. During `kubeadm init`, `kubeadm join`, and `kubeadm upgrade`, the SystemVerification preflight check throws an error if cgroups v1 is detected and the detected `kubelet` version is `v1.35` or newer. For older versions of `kubelet`, a preflight warning is displayed. To allow cgroups v1 with `kubeadm` and `kubelet` version `v1.35` or newer, you must: - Ignore the error from the SystemVerification preflight check by `kubeadm`. - Edit the `kube-system/kubelet-config` ConfigMap and add the `failCgroupV1: False` field before upgrading."
    }
   ]
  },
  "36": {
   "action": [
    {
     "prs": [
      134947
     ],
     "text": "ACTION REQUIRED: DRA (Dynamic Resource Allocation) drivers and controllers now require granular RBAC permissions to update ResourceClaim statuses when the `DRAResourceClaimGranularStatusAuthorization` feature gate is enabled (beta in `v1.36`). Schedulers and controllers must be granted `update`/`patch` on `resourceclaims/binding`. DRA drivers must be granted `associated-node:update` or `arbitrary-node:update` (or patch equivalents) on `resourceclaims/driver`, restricted by their specific `resourceNames`."
    },
    {
     "prs": [
      136423
     ],
     "text": "ACTION REQUIRED: Removed the integrated support for flex-volumes in kubeadm. Users were advised to migrate away from flex-volumes as recommended by SIG Storage since `v1.22`. If `kubeadm` users wish to continue using the feature, they need a custom image for the KCM that is not based on distroless, pass the KCM flag `--flex-volume-plugin-dir`, and mount the directory `/usr/libexec/kubernetes/kubelet-plugins/volume/exec` in the KCM static pod using `kubeadm`'s `extraVolumes` mechanism before upgrading to `v1.36`. Previously, `kubeadm` automatically did the mounting if the user passed the flag."
    },
    {
     "prs": [
      136483
     ],
     "text": "ACTION REQUIRED: Renamed metric `etcd_bookmark_counts` to `etcd_bookmark_total`. If you are using custom monitoring dashboards or alerting rules based on the `etcd_bookmark_counts` metric, update them to use the new `etcd_bookmark_total` metric."
    }
   ],
   "deprecations": [
    {
     "prs": [
      137293
     ],
     "text": "Added warnings and deprecation for Service `.spec.externalIPs`."
    },
    {
     "prs": [
      137304
     ],
     "text": "Direct access to the `Raw` field of `metav1.FieldsV1` is deprecated. Code that constructs or reads `FieldsV1` should migrate to the new `NewFieldsV1(string)`, `GetRawBytes()`, `GetRawString()`, and `SetRawBytes()` accessor methods."
    },
    {
     "prs": [
      136400
     ],
     "text": "Disabled `git-repo` volume plugin by default, with no option to turn it back on."
    },
    {
     "prs": [
      137272
     ],
     "text": "Renamed `AllowlistEntry.Name` to `AllowlistEntry.Command` in the credential plugin allowlist."
    }
   ],
   "released": True,
   "removed_flags": [
    {
     "component": "?",
     "flag": "--bounding-dirs",
     "prs": [
      137348
     ]
    },
    {
     "component": "kubeadm",
     "flag": "--experimental-initial-corrupt-check",
     "prs": [
      135701
     ]
    },
    {
     "component": "kubeadm",
     "flag": "--experimental-watch-progress-notify-interval",
     "prs": [
      135701
     ]
    },
    {
     "component": "kubeadm",
     "flag": "--pod-infra-container-image",
     "prs": [
      135807
     ]
    },
    {
     "component": "kubeadm",
     "flag": "--watch-progress-notify-interval",
     "prs": [
      135701
     ]
    }
   ],
   "urgent": [
    {
     "prs": [
      136399
     ],
     "text": "ACTION REQUIRED: kube-controller-manager: Renamed metric `volume_operation_total_errors` to `volume_operation_errors_total`. If you are using custom monitoring dashboards or alerting rules based on the `volume_operation_total_errors` metric, update them to use the new `volume_operation_errors_total` metric."
    },
    {
     "prs": [
      135393
     ],
     "text": "Added support for running PreBind plugins in parallel in the scheduler framework to improve binding latency. ACTION REQUIRED: Plugins can opt-in to parallel execution by returning `AllowParallel: True` from the `PreBindPreFlight` method. PreBind plugin implementations need to be updated to return `PreBindPreFlightResult` from the `PreBindPreFlight` method; returning nil retains the existing sequential behavior."
    }
   ]
  },
  "37": {
   "action": [],
   "deprecations": [
    {
     "prs": [
      139777
     ],
     "text": "Changed `kubeadm` to explicitly set `KubeProxyConfiguration.mode` to iptables when `KubeProxyConfiguration` is not provided or when the `mode` field is empty. In `v1.37`, `kube-proxy` will warn if the field is not explicitly set as part of the planned transition to nftables as the default mode in a future release."
    },
    {
     "prs": [
      138671
     ],
     "text": "Deprecated the ignored `--filename`/`-f` flag on `kubectl run`."
    },
    {
     "prs": [
      139212
     ],
     "text": "Locked the deprecated `DeclarativeValidationTakeover` feature gate to its default value; it can no longer be set."
    },
    {
     "prs": [
      139067
     ],
     "text": "`kubeadm`: Added a (delayed) warning that `kube-proxy`'s ipvs mode is deprecated since `v1.35` and users on newer Linux kernels should be using the nftables mode instead, which became GA in `v1.33`. For older kernel versions, users can use iptables, which is still the default."
    }
   ],
   "released": True,
   "removed_flags": [
    {
     "component": "kube-controller-manager",
     "flag": "--concurrent-service-syncs",
     "prs": [
      138002
     ]
    },
    {
     "component": "kubelet",
     "flag": "--application-metrics-count-limit",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--boot-id-file",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--container-hints",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--containerd",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--containerd-namespace",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--enable-load-reader",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--event-storage-age-limit",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--event-storage-event-limit",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--global-housekeeping-interval",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--log-cadvisor-usage",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--machine-id-file",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--storage-driver-buffer-duration",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--storage-driver-db",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--storage-driver-host",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--storage-driver-password",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--storage-driver-secure",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--storage-driver-table",
     "prs": [
      139870
     ]
    },
    {
     "component": "kubelet",
     "flag": "--storage-driver-user",
     "prs": [
      139870
     ]
    }
   ],
   "urgent": [
    {
     "prs": [
      139956
     ],
     "text": "ACTION REQUIRED: Graduated the `SELinuxMount` feature gate to GA. The feature is enabled by default in `v1.37`, which may break existing workloads in clusters with SELinux enabled. Please see the Kubernetes blog post to identify potentially problematic workloads in a `v1.36` cluster and how to fix them or opt out of `SELinuxMount` changes before upgrading to `v1.37`. Admins of clusters without SELinux enabled can ignore this release note."
    },
    {
     "prs": [
      138572
     ],
     "text": "ACTION REQUIRED: Converted the `DisruptionMode` enum field to a struct to support future extensibility. Promoted the `scheduling.k8s.io` API group from `v1alpha2` to `v1alpha3` and dropped `v1alpha2` entirely. Remove all `v1alpha2` objects from the `kube-apiserver` before performing the cluster update."
    },
    {
     "prs": [
      117119
     ],
     "text": "ACTION REQUIRED: Fixed `eventRecordQPS` handling in `kubelet` configuration to treat 0 as unlimited (no rate limit), aligning behavior with the documentation. Users relying on the previous default behavior should explicitly set a non-zero value (for example, 50)."
    },
    {
     "prs": [
      139837
     ],
     "text": "ACTION REQUIRED: Updated the `kubelet` to log its effective configuration at startup. Because these logs can expose configuration details, cluster administrators should restrict the `nodes/logs` ClusterRole to trusted users. This is largely a reminder of an existing best practice, since most effective configuration values can already be inferred from other log messages or `kubelet` behavior."
    }
   ]
  },
  "38": {
   "action": [],
   "deprecations": [],
   "released": False,
   "removed_flags": [],
   "urgent": []
  }
 },
 "removed_apis": [
  [
   16,
   "apps/v1beta1",
   "Deployment",
   "apps/v1"
  ],
  [
   16,
   "apps/v1beta1",
   "ReplicaSet",
   "apps/v1"
  ],
  [
   16,
   "apps/v1beta1",
   "StatefulSet",
   "apps/v1"
  ],
  [
   16,
   "apps/v1beta2",
   "DaemonSet",
   "apps/v1"
  ],
  [
   16,
   "apps/v1beta2",
   "Deployment",
   "apps/v1"
  ],
  [
   16,
   "apps/v1beta2",
   "ReplicaSet",
   "apps/v1"
  ],
  [
   16,
   "apps/v1beta2",
   "StatefulSet",
   "apps/v1"
  ],
  [
   16,
   "extensions/v1beta1",
   "DaemonSet",
   "apps/v1"
  ],
  [
   16,
   "extensions/v1beta1",
   "Deployment",
   "apps/v1"
  ],
  [
   16,
   "extensions/v1beta1",
   "NetworkPolicy",
   "networking.k8s.io/v1"
  ],
  [
   16,
   "extensions/v1beta1",
   "PodSecurityPolicy",
   ""
  ],
  [
   16,
   "extensions/v1beta1",
   "ReplicaSet",
   "apps/v1"
  ],
  [
   22,
   "admissionregistration.k8s.io/v1beta1",
   "MutatingWebhookConfiguration",
   "admissionregistration.k8s.io/v1"
  ],
  [
   22,
   "admissionregistration.k8s.io/v1beta1",
   "ValidatingWebhookConfiguration",
   "admissionregistration.k8s.io/v1"
  ],
  [
   22,
   "apiextensions.k8s.io/v1beta1",
   "CustomResourceDefinition",
   "apiextensions.k8s.io/v1"
  ],
  [
   22,
   "apiregistration.k8s.io/v1beta1",
   "APIService",
   "apiregistration.k8s.io/v1"
  ],
  [
   22,
   "authentication.k8s.io/v1beta1",
   "TokenReview",
   "authentication.k8s.io/v1"
  ],
  [
   22,
   "authorization.k8s.io/v1beta1",
   "LocalSubjectAccessReview",
   "authorization.k8s.io/v1"
  ],
  [
   22,
   "authorization.k8s.io/v1beta1",
   "SelfSubjectAccessReview",
   "authorization.k8s.io/v1"
  ],
  [
   22,
   "authorization.k8s.io/v1beta1",
   "SelfSubjectRulesReview",
   "authorization.k8s.io/v1"
  ],
  [
   22,
   "authorization.k8s.io/v1beta1",
   "SubjectAccessReview",
   "authorization.k8s.io/v1"
  ],
  [
   22,
   "certificates.k8s.io/v1beta1",
   "CertificateSigningRequest",
   "certificates.k8s.io/v1"
  ],
  [
   22,
   "coordination.k8s.io/v1beta1",
   "Lease",
   "coordination.k8s.io/v1"
  ],
  [
   22,
   "extensions/v1beta1",
   "Ingress",
   "networking.k8s.io/v1"
  ],
  [
   22,
   "networking.k8s.io/v1beta1",
   "Ingress",
   "networking.k8s.io/v1"
  ],
  [
   22,
   "networking.k8s.io/v1beta1",
   "IngressClass",
   "networking.k8s.io/v1"
  ],
  [
   22,
   "rbac.authorization.k8s.io/v1beta1",
   "ClusterRole",
   "rbac.authorization.k8s.io/v1"
  ],
  [
   22,
   "rbac.authorization.k8s.io/v1beta1",
   "ClusterRoleBinding",
   "rbac.authorization.k8s.io/v1"
  ],
  [
   22,
   "rbac.authorization.k8s.io/v1beta1",
   "Role",
   "rbac.authorization.k8s.io/v1"
  ],
  [
   22,
   "rbac.authorization.k8s.io/v1beta1",
   "RoleBinding",
   "rbac.authorization.k8s.io/v1"
  ],
  [
   22,
   "scheduling.k8s.io/v1beta1",
   "PriorityClass",
   "scheduling.k8s.io/v1"
  ],
  [
   22,
   "storage.k8s.io/v1beta1",
   "CSIDriver",
   "storage.k8s.io/v1"
  ],
  [
   22,
   "storage.k8s.io/v1beta1",
   "CSINode",
   "storage.k8s.io/v1"
  ],
  [
   22,
   "storage.k8s.io/v1beta1",
   "StorageClass",
   "storage.k8s.io/v1"
  ],
  [
   22,
   "storage.k8s.io/v1beta1",
   "VolumeAttachment",
   "storage.k8s.io/v1"
  ],
  [
   25,
   "autoscaling/v2beta1",
   "HorizontalPodAutoscaler",
   "autoscaling/v2"
  ],
  [
   25,
   "batch/v1beta1",
   "CronJob",
   "batch/v1"
  ],
  [
   25,
   "discovery.k8s.io/v1beta1",
   "EndpointSlice",
   "discovery.k8s.io/v1"
  ],
  [
   25,
   "events.k8s.io/v1beta1",
   "Event",
   "events.k8s.io/v1"
  ],
  [
   25,
   "node.k8s.io/v1beta1",
   "RuntimeClass",
   "node.k8s.io/v1"
  ],
  [
   25,
   "policy/v1beta1",
   "PodDisruptionBudget",
   "policy/v1"
  ],
  [
   25,
   "policy/v1beta1",
   "PodSecurityPolicy",
   ""
  ],
  [
   26,
   "autoscaling/v2beta2",
   "HorizontalPodAutoscaler",
   "autoscaling/v2"
  ],
  [
   26,
   "flowcontrol.apiserver.k8s.io/v1beta1",
   "FlowSchema",
   "flowcontrol.apiserver.k8s.io/v1beta2"
  ],
  [
   26,
   "flowcontrol.apiserver.k8s.io/v1beta1",
   "PriorityLevelConfiguration",
   "flowcontrol.apiserver.k8s.io/v1beta2"
  ],
  [
   27,
   "storage.k8s.io/v1beta1",
   "CSIStorageCapacity",
   "storage.k8s.io/v1"
  ],
  [
   29,
   "flowcontrol.apiserver.k8s.io/v1beta2",
   "FlowSchema",
   "flowcontrol.apiserver.k8s.io/v1"
  ],
  [
   29,
   "flowcontrol.apiserver.k8s.io/v1beta2",
   "PriorityLevelConfiguration",
   "flowcontrol.apiserver.k8s.io/v1"
  ],
  [
   32,
   "flowcontrol.apiserver.k8s.io/v1beta3",
   "FlowSchema",
   "flowcontrol.apiserver.k8s.io/v1"
  ],
  [
   32,
   "flowcontrol.apiserver.k8s.io/v1beta3",
   "PriorityLevelConfiguration",
   "flowcontrol.apiserver.k8s.io/v1"
  ]
 ],
 "rke2": {
  "etcd_bridges": [
   {
    "from": "3.5",
    "min": "3.5.26",
    "to": "3.6"
   }
  ],
  "releases": {
   "v1.24.1+rke2r2": {
    "charts": {},
    "components": {
     "Calico": "v3.23.1",
     "Canal": "Flannel v0.17.0 + Calico v3.22.2",
     "Cilium": "v1.11.5",
     "Containerd": "v1.5.13-k3s1",
     "CoreDNS": "v1.9.1",
     "Etcd": "v3.5.4",
     "Flannel": "v0.17.0",
     "Helm-controller": "v0.12.1",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.24.1",
     "Metrics-server": "v0.5.0",
     "Multus": "v3.8",
     "Runc": "v1.1.2"
    },
    "date": "2022-06-13",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.10+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.24.5",
     "Canal": "Flannel v0.20.2 + Calico v3.24.5",
     "Cilium": "v1.12.4",
     "Containerd": "v1.6.15-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.20.2",
     "Helm-controller": "v0.13.1",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.24.10",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9.3",
     "Runc": "v1.1.4"
    },
    "date": "2023-01-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.11+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.1 + Calico v3.25.0",
     "Cilium": "v1.12.5",
     "Containerd": "v1.6.15-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.21.1",
     "Helm-controller": "v0.13.1",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.24.11",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9.3",
     "Runc": "v1.1.4"
    },
    "date": "2023-03-10",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.12+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.3 + Calico v3.25.0",
     "Cilium": "v1.13.0",
     "Containerd": "v1.6.19-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.21.3",
     "Helm-controller": "v0.13.1",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.24.12",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9.3",
     "Runc": "v1.1.4"
    },
    "date": "2023-03-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.13+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.3 + Calico v3.25.0",
     "Cilium": "v1.13.0",
     "Containerd": "v1.6.19-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.21.3",
     "Helm-controller": "v0.13.3",
     "Ingress-Nginx": "4.5.2",
     "Kubernetes": "v1.24.13",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9.3",
     "Runc": "v1.1.5"
    },
    "date": "2023-04-21",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.14+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.3 + Calico v3.25.1",
     "Cilium": "v1.13.2",
     "Containerd": "v1.7.1-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.21.3",
     "Helm-controller": "v0.14.0",
     "Ingress-Nginx": "4.5.2",
     "Kubernetes": "v1.24.14",
     "Metrics-server": "v0.6.3",
     "Multus": "v3.9.3",
     "Runc": "v1.1.7"
    },
    "date": "2023-05-30",
    "notes": [
     "Many systems have updated their packages with newer version of container-selinux (> v2.191.0) which is incompatible with our rke2-selinux policy and require a change in policy. We have updated our policy; you will notice the rke2-selinux package being upgraded from version v0.11.1 to newer version v0.12.0."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.15+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.22.0 + Calico v3.25.1",
     "Cilium": "v1.13.2",
     "Containerd": "v1.7.1-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.22.0",
     "Helm-controller": "v0.15.0",
     "Ingress-Nginx": "4.5.2",
     "Kubernetes": "v1.24.15",
     "Metrics-server": "v0.6.3",
     "Multus": "v3.9.3",
     "Runc": "v1.1.7"
    },
    "date": "2023-06-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.16+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.0 + Calico v3.25.1",
     "Cilium": "v1.13.2",
     "Containerd": "v1.7.1-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.22.0",
     "Helm-controller": "v0.15.2",
     "Ingress-Nginx": "4.6.1",
     "Kubernetes": "v1.24.16",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.7"
    },
    "date": "2023-07-28",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.17+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.0",
     "Containerd": "v1.7.3-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.6.1",
     "Kubernetes": "v1.24.17",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-09-06",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.2+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.23.1",
     "Canal": "Flannel v0.17.0 + Calico v3.22.2",
     "Cilium": "v1.11.5",
     "Containerd": "v1.6.6-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4",
     "Flannel": "v0.17.0",
     "Helm-controller": "v0.12.3",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.24.2",
     "Metrics-server": "v0.5.0",
     "Multus": "v3.8",
     "Runc": "v1.1.2"
    },
    "date": "2022-07-05",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.3+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.23.1",
     "Canal": "Flannel v0.17.0 + Calico v3.22.2",
     "Cilium": "v1.11.5",
     "Containerd": "v1.6.6-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4",
     "Flannel": "v0.17.0",
     "Helm-controller": "v0.12.3",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.24.3",
     "Metrics-server": "v0.5.0",
     "Multus": "v3.8",
     "Runc": "v1.1.2"
    },
    "date": "2022-07-21",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.4+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.23.1",
     "Canal": "Flannel v0.17.0 + Calico v3.22.2",
     "Cilium": "v1.12.0",
     "Containerd": "v1.6.6-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4",
     "Flannel": "v0.17.0",
     "Helm-controller": "v0.12.3",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.24.4",
     "Metrics-server": "v0.5.0",
     "Multus": "v3.8",
     "Runc": "v1.1.2"
    },
    "date": "2022-08-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.6+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.24.1",
     "Canal": "Flannel v0.19.1 + Calico v3.23.3",
     "Cilium": "v1.12.1",
     "Containerd": "v1.6.8-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4",
     "Flannel": "v0.19.1",
     "Helm-controller": "v0.12.3",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.24.6",
     "Metrics-server": "v0.5.0",
     "Multus": "v3.8",
     "Runc": "v1.1.4"
    },
    "date": "2022-09-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.7+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.24.1",
     "Canal": "Flannel v0.19.1 + Calico v3.24.1",
     "Cilium": "v1.12.1",
     "Containerd": "v1.6.8-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.19.1",
     "Helm-controller": "v0.12.3",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.24.7",
     "Metrics-server": "v0.6.1",
     "Multus": "v3.8",
     "Runc": "v1.1.4"
    },
    "date": "2022-10-20",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.8+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.24.1",
     "Canal": "Flannel v0.19.1 + Calico v3.24.1",
     "Cilium": "v1.12.3",
     "Containerd": "v1.6.8-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.19.1",
     "Helm-controller": "v0.13.0",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.24.8",
     "Metrics-server": "v0.6.1",
     "Multus": "v3.8",
     "Runc": "v1.1.4"
    },
    "date": "2022-11-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.24.9+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.24.5",
     "Canal": "Flannel v0.20.2 + Calico v3.24.5",
     "Cilium": "v1.12.4",
     "Containerd": "v1.6.12-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.20.2",
     "Helm-controller": "v0.13.1",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.24.9",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9",
     "Runc": "v1.1.4"
    },
    "date": "2022-12-20",
    "notes": [
     "This release is affected by https://github.com/containerd/containerd/issues/7843, which causes the kubelet to restart all pods whenever RKE2 is restarted. For this reason, we have removed this RKE2 release from the channel server. Please use v1.24.9+rke2r2 instead."
    ],
    "prime_only": False,
    "pulled": True
   },
   "v1.24.9+rke2r2": {
    "charts": {},
    "components": {
     "Calico": "v3.24.5",
     "Canal": "Flannel v0.20.2 + Calico v3.24.5",
     "Cilium": "v1.12.4",
     "Containerd": "v1.6.14-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.20.2",
     "Helm-controller": "v0.13.1",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.24.9",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9",
     "Runc": "v1.1.4"
    },
    "date": "2023-01-10",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.0+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.24.1",
     "Canal": "Flannel v0.19.1 + Calico v3.24.1",
     "Cilium": "v1.12.1",
     "Containerd": "v1.6.8-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4",
     "Flannel": "v0.19.1",
     "Helm-controller": "v0.12.3",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.25.0",
     "Metrics-server": "v0.5.0",
     "Multus": "v3.8",
     "Runc": "v1.1.4"
    },
    "date": "2022-09-15",
    "notes": [
     "Kubernetes v1.25 removes the beta PodSecurityPolicy admission plugin. Please follow the upstream documentation to migrate from PSP if using the built-in PodSecurity Admission Plugin, prior to upgrading to v1.25.0+rke2r1.",
     "RKE2 now supports version 1.23 of the CIS Benchmark for Kubernetes. The legacy CIS 1.5 and 1.6 profiles (profile: cis-1.5 and profile: cis-1.6) have been removed as they do not apply to Kubernetes 1.25. Servers using one of the legacy profiles must be updated to specify the cis-1.23 profile when upgrading to RKE2 1.25, or RKE2 will fail to start."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.10+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.3 + Calico v3.25.1",
     "Cilium": "v1.13.2",
     "Containerd": "v1.7.1-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.21.3",
     "Helm-controller": "v0.14.0",
     "Ingress-Nginx": "4.5.2",
     "Kubernetes": "v1.25.10",
     "Metrics-server": "v0.6.3",
     "Multus": "v3.9.3",
     "Runc": "v1.1.7"
    },
    "date": "2023-05-30",
    "notes": [
     "Many systems have updated their packages with newer version of container-selinux (> v2.191.0) which is incompatible with our rke2-selinux policy and require a change in policy. We have updated our policy; you will notice the rke2-selinux package being upgraded from version v0.11.1 to newer version v0.12.0."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.11+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.22.0 + Calico v3.25.1",
     "Cilium": "v1.13.2",
     "Containerd": "v1.7.1-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.22.0",
     "Helm-controller": "v0.15.0",
     "Ingress-Nginx": "4.5.2",
     "Kubernetes": "v1.25.11",
     "Metrics-server": "v0.6.3",
     "Multus": "v3.9.3",
     "Runc": "v1.1.7"
    },
    "date": "2023-06-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.12+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.0 + Calico v3.25.1",
     "Cilium": "v1.13.2",
     "Containerd": "v1.7.1-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.22.0",
     "Helm-controller": "v0.15.2",
     "Ingress-Nginx": "4.6.1",
     "Kubernetes": "v1.25.12",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.7"
    },
    "date": "2023-07-28",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.13+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.0",
     "Containerd": "v1.7.3-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.6.1",
     "Kubernetes": "v1.25.13",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-09-06",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.14+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.1",
     "Containerd": "v1.7.3-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.6.1",
     "Kubernetes": "v1.25.14",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-09-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.15+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.2",
     "Containerd": "v1.7.7-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.8.2",
     "Kubernetes": "v1.25.15",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-10-31",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.15+rke2r2": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.2",
     "Containerd": "v1.7.7-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.8.2",
     "Kubernetes": "v1.25.15",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-11-08",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.16+rke2r1": {
    "charts": {
     "rke2-calico": "v3.26.300",
     "rke2-calico-crd": "v3.26.300",
     "rke2-canal": "v3.26.3-build2023110900",
     "rke2-cilium": "1.14.400",
     "rke2-coredns": "1.24.006",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051510",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.26.3",
     "Canal": "Flannel v0.23.0 + Calico v3.26.3",
     "Cilium": "v1.14.4",
     "Containerd": "v1.7.7-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.23.0",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.25.16",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-12-05",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.16+rke2r2": {
    "charts": {
     "rke2-calico": "v3.26.300",
     "rke2-calico-crd": "v3.26.300",
     "rke2-canal": "v3.26.3-build2023110900",
     "rke2-cilium": "1.14.400",
     "rke2-coredns": "1.24.006",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051510",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.26.3",
     "Canal": "Flannel v0.23.0 + Calico v3.26.3",
     "Cilium": "v1.14.4",
     "Containerd": "v1.7.7-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.23.0",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.25.16",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-02-28",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.2+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.24.1",
     "Canal": "Flannel v0.19.1 + Calico v3.23.3",
     "Cilium": "v1.12.1",
     "Containerd": "v1.6.8-k3s2",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4",
     "Flannel": "v0.19.1",
     "Helm-controller": "v0.12.3",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.25.2",
     "Metrics-server": "v0.5.0",
     "Multus": "v3.8",
     "Runc": "v1.1.4"
    },
    "date": "2022-09-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.3+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.24.1",
     "Canal": "Flannel v0.19.1 + Calico v3.24.1",
     "Cilium": "v1.12.1",
     "Containerd": "v1.6.8-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.19.1",
     "Helm-controller": "v0.12.3",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.25.3",
     "Metrics-server": "v0.6.1",
     "Multus": "v3.8",
     "Runc": "v1.1.4"
    },
    "date": "2022-10-20",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.4+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.24.1",
     "Canal": "Flannel v0.19.1 + Calico v3.24.1",
     "Cilium": "v1.12.3",
     "Containerd": "v1.6.8-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.19.1",
     "Helm-controller": "v0.13.0",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.25.4",
     "Metrics-server": "v0.6.1",
     "Multus": "v3.8",
     "Runc": "v1.1.4"
    },
    "date": "2022-11-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.5+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.24.5",
     "Canal": "Flannel v0.20.2 + Calico v3.24.5",
     "Cilium": "v1.12.4",
     "Containerd": "v1.6.12-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.20.2",
     "Helm-controller": "v0.13.1",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.25.5",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9",
     "Runc": "v1.1.4"
    },
    "date": "2022-12-20",
    "notes": [
     "This release is affected by https://github.com/containerd/containerd/issues/7843, which causes the kubelet to restart all pods whenever RKE2 is restarted. For this reason, we have removed this RKE2 release from the channel server. Please use v1.25.5+rke2r2 instead."
    ],
    "prime_only": False,
    "pulled": True
   },
   "v1.25.5+rke2r2": {
    "charts": {},
    "components": {
     "Calico": "v3.24.5",
     "Canal": "Flannel v0.20.2 + Calico v3.24.5",
     "Cilium": "v1.12.4",
     "Containerd": "v1.6.14-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.20.2",
     "Helm-controller": "v0.13.1",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.25.5",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9",
     "Runc": "v1.1.4"
    },
    "date": "2023-01-10",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.6+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.24.5",
     "Canal": "Flannel v0.20.2 + Calico v3.24.5",
     "Cilium": "v1.12.4",
     "Containerd": "v1.6.15-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.20.2",
     "Helm-controller": "v0.13.1",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.25.6",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9.3",
     "Runc": "v1.1.4"
    },
    "date": "2023-01-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.7+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.1 + Calico v3.25.0",
     "Cilium": "v1.12.5",
     "Containerd": "v1.6.15-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.21.1",
     "Helm-controller": "v0.13.2",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.25.7",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9.3",
     "Runc": "v1.1.4"
    },
    "date": "2023-03-10",
    "notes": [
     "The embedded helm-controller job image now correctly handles upgrading charts that contain resource types that no longer exist on the target Kubernetes version. This includes properly handling removal of PodSecurityPolicy resources when upgrading from &lt;= v1.24."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.8+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.3 + Calico v3.25.0",
     "Cilium": "v1.13.0",
     "Containerd": "v1.6.19-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.4-k3s1",
     "Flannel": "v0.21.3",
     "Helm-controller": "v0.13.2",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.25.8",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9.3",
     "Runc": "v1.1.4"
    },
    "date": "2023-03-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.25.9+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.3 + Calico v3.25.0",
     "Cilium": "v1.13.0",
     "Containerd": "v1.6.19-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.21.3",
     "Helm-controller": "v0.13.2",
     "Ingress-Nginx": "4.5.2",
     "Kubernetes": "v1.25.9",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9.3",
     "Runc": "v1.1.5"
    },
    "date": "2023-04-21",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.0+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.24.5",
     "Canal": "Flannel v0.20.2 + Calico v3.24.5",
     "Cilium": "v1.12.4",
     "Containerd": "v1.6.12-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.5",
     "Flannel": "v0.20.2",
     "Helm-controller": "v0.13.1",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.26.0",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9",
     "Runc": "v1.1.4"
    },
    "date": "2022-12-15",
    "notes": [
     "This release is affected by https://github.com/containerd/containerd/issues/7843, which causes the kubelet to restart all pods whenever RKE2 is restarted. For this reason, we have removed this RKE2 release from the channel server. Please use v1.26.0+rke2r2 instead."
    ],
    "prime_only": False,
    "pulled": True
   },
   "v1.26.0+rke2r2": {
    "charts": {},
    "components": {
     "Calico": "v3.24.5",
     "Canal": "Flannel v0.20.2 + Calico v3.24.5",
     "Cilium": "v1.12.4",
     "Containerd": "v1.6.14-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.5",
     "Flannel": "v0.20.2",
     "Helm-controller": "v0.13.1",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.26.0",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9",
     "Runc": "v1.1.4"
    },
    "date": "2023-01-10",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.1+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.24.5",
     "Canal": "Flannel v0.20.2 + Calico v3.24.5",
     "Cilium": "v1.12.4",
     "Containerd": "v1.6.15-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.5-k3s1",
     "Flannel": "v0.20.2",
     "Helm-controller": "v0.13.1",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.26.1",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9.3",
     "Runc": "v1.1.4"
    },
    "date": "2023-01-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.10+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.2",
     "Containerd": "v1.7.7-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.8.2",
     "Kubernetes": "v1.26.10",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-10-31",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.10+rke2r2": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.2",
     "Containerd": "v1.7.7-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.8.2",
     "Kubernetes": "v1.26.10",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-11-08",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.11+rke2r1": {
    "charts": {
     "rke2-calico": "v3.26.300",
     "rke2-calico-crd": "v3.26.300",
     "rke2-canal": "v3.26.3-build2023110900",
     "rke2-cilium": "1.14.400",
     "rke2-coredns": "1.24.006",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051510",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.26.3",
     "Canal": "Flannel v0.23.0 + Calico v3.26.3",
     "Cilium": "v1.14.4",
     "Containerd": "v1.7.7-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.23.0",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.26.11",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-12-05",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.12+rke2r1": {
    "charts": {
     "rke2-calico": "v3.26.300",
     "rke2-calico-crd": "v3.26.300",
     "rke2-canal": "v3.26.3-build2023110900",
     "rke2-cilium": "1.14.400",
     "rke2-coredns": "1.24.006",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051510",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.26.3",
     "Canal": "Flannel v0.23.0 + Calico v3.26.3",
     "Cilium": "v1.14.4",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.23.0",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.26.12",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.10"
    },
    "date": "2023-12-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.13+rke2r1": {
    "charts": {
     "rke2-calico": "v3.26.300",
     "rke2-calico-crd": "v3.26.300",
     "rke2-canal": "v3.26.3-build2023110900",
     "rke2-cilium": "1.14.400",
     "rke2-coredns": "1.24.008",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051511",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.26.3",
     "Canal": "Flannel v0.23.0 + Calico v3.26.3",
     "Cilium": "v1.14.4",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.23.0",
     "Helm-controller": "v0.15.8",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.26.13",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-02-06",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.14+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.002",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.0-build2024020601",
     "rke2-cilium": "1.15.100",
     "rke2-coredns": "1.29.001",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051513",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.0",
     "Canal": "Flannel v0.24.2 + Calico v3.27.0",
     "Cilium": "v1.15.1",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.24.2",
     "Helm-controller": "[](https://github.com/k3s-io/helm-controller/releases/tag/)",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.26.14",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-02-29",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.15+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.200",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.2-build2024030800",
     "rke2-cilium": "1.15.100",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051513",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.2",
     "Canal": "Flannel v0.24.3 + Calico v3.27.2",
     "Cilium": "v1.15.1",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.24.3",
     "Helm-controller": "v0.15.9",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.26.15",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1."
    },
    "date": "2024-03-20",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.2+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.1 + Calico v3.25.0",
     "Cilium": "v1.12.5",
     "Containerd": "v1.6.15-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.5-k3s1",
     "Flannel": "v0.21.1",
     "Helm-controller": "v0.13.2",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.26.2",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9.3",
     "Runc": "v1.1.4"
    },
    "date": "2023-03-10",
    "notes": [
     "The embedded helm-controller job image now correctly handles upgrading charts that contain resource types that no longer exist on the target Kubernetes version. This includes properly handling removal of PodSecurityPolicy resources when upgrading from &lt;= v1.24."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.3+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.3 + Calico v3.25.0",
     "Cilium": "v1.13.0",
     "Containerd": "v1.6.19-k3s1",
     "CoreDNS": "v1.9.3",
     "Etcd": "v3.5.5-k3s1",
     "Flannel": "v0.21.3",
     "Helm-controller": "v0.13.2",
     "Ingress-Nginx": "4.1.0",
     "Kubernetes": "v1.26.3",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9.3",
     "Runc": "v1.1.4"
    },
    "date": "2023-03-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.4+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.3 + Calico v3.25.0",
     "Cilium": "v1.13.0",
     "Containerd": "v1.6.19-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.21.3",
     "Helm-controller": "v0.13.2",
     "Ingress-Nginx": "4.5.2",
     "Kubernetes": "v1.26.4",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9.3",
     "Runc": "v1.1.5"
    },
    "date": "2023-04-21",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.5+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.3 + Calico v3.25.1",
     "Cilium": "v1.13.2",
     "Containerd": "v1.7.1-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.21.3",
     "Helm-controller": "v0.14.0",
     "Ingress-Nginx": "4.5.2",
     "Kubernetes": "v1.26.5",
     "Metrics-server": "v0.6.3",
     "Multus": "v3.9.3",
     "Runc": "v1.1.7"
    },
    "date": "2023-05-30",
    "notes": [
     "Many systems have updated their packages with newer version of container-selinux (> v2.191.0) which is incompatible with our rke2-selinux policy and require a change in policy. We have updated our policy; you will notice the rke2-selinux package being upgraded from version v0.11.1 to newer version v0.12.0."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.6+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.22.0 + Calico v3.25.1",
     "Cilium": "v1.13.2",
     "Containerd": "v1.7.1-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.22.0",
     "Helm-controller": "v0.15.0",
     "Ingress-Nginx": "4.5.2",
     "Kubernetes": "v1.26.6",
     "Metrics-server": "v0.6.3",
     "Multus": "v3.9.3",
     "Runc": "v1.1.7"
    },
    "date": "2023-06-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.7+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.0 + Calico v3.25.1",
     "Cilium": "v1.13.2",
     "Containerd": "v1.7.1-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.22.0",
     "Helm-controller": "v0.15.2",
     "Ingress-Nginx": "4.6.1",
     "Kubernetes": "v1.26.7",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.7"
    },
    "date": "2023-07-28",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.8+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.0",
     "Containerd": "v1.7.3-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.6.1",
     "Kubernetes": "v1.26.8",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-09-06",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.26.9+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.1",
     "Containerd": "v1.7.3-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.6.1",
     "Kubernetes": "v1.26.9",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-09-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.1+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.3 + Calico v3.25.0",
     "Cilium": "v1.13.0",
     "Containerd": "v1.6.19-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.21.3",
     "Helm-controller": "v0.13.2",
     "Ingress-Nginx": "4.5.2",
     "Kubernetes": "v1.27.1",
     "Metrics-server": "v0.6.2",
     "Multus": "v3.9.3",
     "Runc": "v1.1.5"
    },
    "date": "2023-04-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.10+rke2r1": {
    "charts": {
     "rke2-calico": "v3.26.300",
     "rke2-calico-crd": "v3.26.300",
     "rke2-canal": "v3.26.3-build2023110900",
     "rke2-cilium": "1.14.400",
     "rke2-coredns": "1.24.008",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051511",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.26.3",
     "Canal": "Flannel v0.23.0 + Calico v3.26.3",
     "Cilium": "v1.14.4",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.23.0",
     "Helm-controller": "v0.15.8",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.27.10",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-02-06",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.11+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.002",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.0-build2024020601",
     "rke2-cilium": "1.15.100",
     "rke2-coredns": "1.29.001",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051513",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.0",
     "Canal": "Flannel v0.24.2 + Calico v3.27.0",
     "Cilium": "v1.15.1",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.24.2",
     "Helm-controller": "v0.15.8",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.27.11",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-02-29",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.12+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.200",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.2-build2024030800",
     "rke2-cilium": "1.15.100",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051513",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.2",
     "Canal": "Flannel v0.24.3 + Calico v3.27.2",
     "Cilium": "v1.15.1",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.24.3",
     "Helm-controller": "v0.15.9",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.27.12",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-03-20",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.13+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.3-build2024042301",
     "rke2-cilium": "1.15.400",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.9.100",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.1 + Calico v3.27.3",
     "Cilium": "v1.15.4",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.25.1",
     "Helm-controller": "v0.15.9",
     "Ingress-Nginx": "nginx-1.9.6-hardened1",
     "Kubernetes": "v1.27.13",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-04-29",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.14+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.3-build2024042301",
     "rke2-cilium": "1.15.500",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.9.100",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.1 + Calico v3.27.3",
     "Cilium": "v1.15.5",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.25.1",
     "Helm-controller": "v0.15.9",
     "Ingress-Nginx": "nginx-1.9.6-hardened1",
     "Kubernetes": "v1.27.14",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-05-22",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.15+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.28.0-build2024062503",
     "rke2-cilium": "1.15.500",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.10.101",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.4 + Calico v3.28.0",
     "Cilium": "v1.15.5",
     "Containerd": "v1.7.17-k3s1",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.4",
     "Helm-controller": "v0.15.10",
     "Ingress-Nginx": "v1.10.1-hardened1",
     "Kubernetes": "v1.27.15",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-07-01",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.16+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.28.0-build2024062503",
     "rke2-cilium": "1.15.500",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.10.102",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.4 + Calico v3.28.0",
     "Cilium": "v1.15.5",
     "Containerd": "v1.7.17-k3s1",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.4",
     "Helm-controller": "v0.15.10",
     "Ingress-Nginx": "v1.10.1-hardened1",
     "Kubernetes": "v1.27.16",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-08-01",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.16+rke2r2": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.28.1-build2024080600",
     "rke2-cilium": "1.16.000",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.10.401",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.5 + Calico v3.28.1",
     "Cilium": "v1.16.0",
     "Containerd": "v1.7.20-k3s1",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.5",
     "Helm-controller": "v0.15.10",
     "Ingress-Nginx": "v1.10.4-hardened2",
     "Kubernetes": "v1.27.16",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-08-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.2+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.21.3 + Calico v3.25.1",
     "Cilium": "v1.13.2",
     "Containerd": "v1.7.1-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.21.3",
     "Helm-controller": "v0.14.0",
     "Ingress-Nginx": "4.5.2",
     "Kubernetes": "v1.27.2",
     "Metrics-server": "v0.6.3",
     "Multus": "v3.9.3",
     "Runc": "v1.1.7"
    },
    "date": "2023-05-30",
    "notes": [
     "Many systems have updated their packages with newer version of container-selinux (> v2.191.0) which is incompatible with our rke2-selinux policy and require a change in policy. We have updated our policy; you will notice the rke2-selinux package being upgraded from version v0.11.1 to newer version v0.12.0."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.3+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.25.0",
     "Canal": "Flannel v0.22.0 + Calico v3.25.1",
     "Cilium": "v1.13.2",
     "Containerd": "v1.7.1-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.22.0",
     "Helm-controller": "v0.15.0",
     "Ingress-Nginx": "4.5.2",
     "Kubernetes": "v1.27.3",
     "Metrics-server": "v0.6.3",
     "Multus": "v3.9.3",
     "Runc": "v1.1.7"
    },
    "date": "2023-06-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.4+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.0 + Calico v3.25.1",
     "Cilium": "v1.13.2",
     "Containerd": "v1.7.1-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.7-k3s1",
     "Flannel": "v0.22.0",
     "Helm-controller": "v0.15.2",
     "Ingress-Nginx": "4.6.1",
     "Kubernetes": "v1.27.4",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.7"
    },
    "date": "2023-07-28",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.5+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.0",
     "Containerd": "v1.7.3-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.6.1",
     "Kubernetes": "v1.27.5",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-09-06",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.6+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.1",
     "Containerd": "v1.7.3-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.6.1",
     "Kubernetes": "v1.27.6",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-09-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.7+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.2",
     "Containerd": "v1.7.7-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.8.2",
     "Kubernetes": "v1.27.7",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-10-31",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.7+rke2r2": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.2",
     "Containerd": "v1.7.7-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.8.2",
     "Kubernetes": "v1.27.7",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-11-08",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.8+rke2r1": {
    "charts": {
     "rke2-calico": "v3.26.300",
     "rke2-calico-crd": "v3.26.300",
     "rke2-canal": "v3.26.3-build2023110900",
     "rke2-cilium": "1.14.400",
     "rke2-coredns": "1.24.006",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051510",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.26.3",
     "Canal": "Flannel v0.23.0 + Calico v3.26.3",
     "Cilium": "v1.14.4",
     "Containerd": "v1.7.7-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.23.0",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.27.8",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-12-05",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.27.9+rke2r1": {
    "charts": {
     "rke2-calico": "v3.26.300",
     "rke2-calico-crd": "v3.26.300",
     "rke2-canal": "v3.26.3-build2023110900",
     "rke2-cilium": "1.14.400",
     "rke2-coredns": "1.24.006",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051510",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.26.3",
     "Canal": "Flannel v0.23.0 + Calico v3.26.3",
     "Cilium": "v1.14.4",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.23.0",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.27.9",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.10"
    },
    "date": "2023-12-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.10+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.3-build2024042301",
     "rke2-cilium": "1.15.500",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.9.100",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.1 + Calico v3.27.3",
     "Cilium": "v1.15.5",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.25.1",
     "Helm-controller": "v0.15.9",
     "Ingress-Nginx": "nginx-1.9.6-hardened1",
     "Kubernetes": "v1.28.10",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-05-22",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.11+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.28.0-build2024062503",
     "rke2-cilium": "1.15.500",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.10.101",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.4 + Calico v3.28.0",
     "Cilium": "v1.15.5",
     "Containerd": "v1.7.17-k3s1",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.4",
     "Helm-controller": "v0.15.10",
     "Ingress-Nginx": "v1.10.1-hardened1",
     "Kubernetes": "v1.28.11",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-07-01",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.12+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.28.0-build2024062503",
     "rke2-cilium": "1.15.500",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.10.102",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.4 + Calico v3.28.0",
     "Cilium": "v1.15.5",
     "Containerd": "v1.7.17-k3s1",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.4",
     "Helm-controller": "v0.15.10",
     "Ingress-Nginx": "v1.10.1-hardened1",
     "Kubernetes": "v1.28.12",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-08-01",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.13+rke2r1": {
    "charts": {
     "rke2-calico": "v3.28.100",
     "rke2-calico-crd": "v3.28.100",
     "rke2-canal": "v3.28.1-build2024080600",
     "rke2-cilium": "1.16.000",
     "rke2-coredns": "1.29.004",
     "rke2-ingress-nginx": "4.10.401",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.28.1",
     "Canal": "Flannel v0.25.5 + Calico v3.28.1",
     "Cilium": "v1.16.0",
     "Containerd": "v1.7.20-k3s1",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.5",
     "Helm-controller": "v0.15.10",
     "Ingress-Nginx": "v1.10.4-hardened2",
     "Kubernetes": "v1.28.13",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-08-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.14+rke2r1": {
    "charts": {
     "rke2-calico": "v3.28.100",
     "rke2-calico-crd": "v3.28.100",
     "rke2-canal": "v3.28.1-build2024091100",
     "rke2-cilium": "1.16.104",
     "rke2-coredns": "1.29.006",
     "rke2-ingress-nginx": "4.10.402",
     "rke2-metrics-server": "3.12.003",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.28.1",
     "Canal": "Flannel v0.25.6 + Calico v3.28.1",
     "Cilium": "v1.16.1",
     "Containerd": "v1.7.21-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.6",
     "Helm-controller": "v0.15.13",
     "Ingress-Nginx": "v1.10.4-hardened3",
     "Kubernetes": "v1.28.14",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.0",
     "Runc": "v1.1.14"
    },
    "date": "2024-09-23",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.15+rke2r1": {
    "charts": {
     "rke2-calico": "v3.28.200",
     "rke2-calico-crd": "v3.28.200",
     "rke2-canal": "v3.28.2-build2024101601",
     "rke2-cilium": "1.16.201",
     "rke2-coredns": "1.33.002",
     "rke2-ingress-nginx": "4.10.501",
     "rke2-metrics-server": "3.12.004",
     "rke2-snapshot-controller": "3.0.601",
     "rke2-snapshot-controller-crd": "3.0.601",
     "rke2-snapshot-validation-webhook": "1.9.001"
    },
    "components": {
     "Calico": "v3.28.2",
     "Canal": "Flannel v0.25.7 + Calico v3.28.2",
     "Cilium": "v1.16.2",
     "Containerd": "v1.7.22-k3s1",
     "CoreDNS": "v1.11.3",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.7",
     "Helm-controller": "v0.15.15",
     "Ingress-Nginx": "v1.10.5-hardened3",
     "Kubernetes": "v1.28.15",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.2",
     "Runc": "v1.1.14"
    },
    "date": "2024-10-30",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.2+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.1",
     "Containerd": "v1.7.3-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.6.1",
     "Kubernetes": "v1.28.2",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-09-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.3+rke2r1": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.2",
     "Containerd": "v1.7.7-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.8.2",
     "Kubernetes": "v1.28.3",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-10-31",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.3+rke2r2": {
    "charts": {},
    "components": {
     "Calico": "v3.26.1",
     "Canal": "Flannel v0.22.1 + Calico v3.26.1",
     "Cilium": "v1.14.2",
     "Containerd": "v1.7.7-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.22.1",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "4.8.2",
     "Kubernetes": "v1.28.3",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-11-08",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.4+rke2r1": {
    "charts": {
     "rke2-calico": "v3.26.300",
     "rke2-calico-crd": "v3.26.300",
     "rke2-canal": "v3.26.3-build2023110900",
     "rke2-cilium": "1.14.400",
     "rke2-coredns": "1.24.007",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051511",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.26.3",
     "Canal": "Flannel v0.23.0 + Calico v3.26.3",
     "Cilium": "v1.14.4",
     "Containerd": "v1.7.7-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.23.0",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.28.4",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.8"
    },
    "date": "2023-12-05",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.5+rke2r1": {
    "charts": {
     "rke2-calico": "v3.26.300",
     "rke2-calico-crd": "v3.26.300",
     "rke2-canal": "v3.26.3-build2023110900",
     "rke2-cilium": "1.14.400",
     "rke2-coredns": "1.24.007",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051511",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.26.3",
     "Canal": "Flannel v0.23.0 + Calico v3.26.3",
     "Cilium": "v1.14.4",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.23.0",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.28.5",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.10"
    },
    "date": "2023-12-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.6+rke2r1": {
    "charts": {
     "rke2-calico": "v3.26.300",
     "rke2-calico-crd": "v3.26.300",
     "rke2-canal": "v3.26.3-build2023110900",
     "rke2-cilium": "1.14.400",
     "rke2-coredns": "1.24.008",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051511",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.26.3",
     "Canal": "Flannel v0.23.0 + Calico v3.26.3",
     "Cilium": "v1.14.4",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.23.0",
     "Helm-controller": "v0.15.8",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.28.6",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-02-06",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.7+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.002",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.0-build2024020601",
     "rke2-cilium": "1.15.100",
     "rke2-coredns": "1.29.001",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051513",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.0",
     "Canal": "Flannel v0.24.2 + Calico v3.27.0",
     "Cilium": "v1.15.1",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.24.2",
     "Helm-controller": "v0.15.8",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.28.7",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-02-29",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.8+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.200",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.2-build2024030800",
     "rke2-cilium": "1.15.100",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051513",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.2",
     "Canal": "Flannel v0.24.3 + Calico v3.27.2",
     "Cilium": "v1.15.1",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.24.3",
     "Helm-controller": "v0.15.9",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.28.8",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-03-20",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.28.9+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.3-build2024042301",
     "rke2-cilium": "1.15.400",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.9.100",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.1 + Calico v3.27.3",
     "Cilium": "v1.15.4",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.25.1",
     "Helm-controller": "v0.15.9",
     "Ingress-Nginx": "nginx-1.9.6-hardened1",
     "Kubernetes": "v1.28.9",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-04-29",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.0+rke2r1": {
    "charts": {
     "rke2-calico": "v3.26.300",
     "rke2-calico-crd": "v3.26.300",
     "rke2-canal": "v3.26.3-build2023110900",
     "rke2-cilium": "1.14.400",
     "rke2-coredns": "1.24.007",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051511",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.26.3",
     "Canal": "Flannel v0.23.0 + Calico v3.26.3",
     "Cilium": "v1.14.4",
     "Containerd": "v1.7.11-k3s1",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.23.0",
     "Helm-controller": "v0.15.4",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.29.0",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.10"
    },
    "date": "2023-12-22",
    "notes": [
     "The experimental secrets-encrypt rotate-keys command, used to perform an abbreviated rotation of secrets encryptions keys, has been removed from this release due to changes in the upstream implementation of configuration reloading. It will return in a subsequent release; see https://github.com/rancher/rke2/issues/5152 for more information."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.1+rke2r1": {
    "charts": {
     "rke2-calico": "v3.26.300",
     "rke2-calico-crd": "v3.26.300",
     "rke2-canal": "v3.26.3-build2023110900",
     "rke2-cilium": "1.14.400",
     "rke2-coredns": "1.24.008",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051511",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.26.3",
     "Canal": "Flannel v0.23.0 + Calico v3.26.3",
     "Cilium": "v1.14.4",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.10.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.23.0",
     "Helm-controller": "v0.15.8",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.29.1",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-02-06",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.10+rke2r1": {
    "charts": {
     "rke2-calico": "v3.28.200",
     "rke2-calico-crd": "v3.28.200",
     "rke2-canal": "v3.28.2-build2024101601",
     "rke2-cilium": "1.16.201",
     "rke2-coredns": "1.33.002",
     "rke2-ingress-nginx": "4.10.501",
     "rke2-metrics-server": "3.12.004",
     "rke2-snapshot-controller": "3.0.601",
     "rke2-snapshot-controller-crd": "3.0.601",
     "rke2-snapshot-validation-webhook": "1.9.001"
    },
    "components": {
     "Calico": "v3.28.2",
     "Canal": "Flannel v0.25.7 + Calico v3.28.2",
     "Cilium": "v1.16.2",
     "Containerd": "v1.7.22-k3s1",
     "CoreDNS": "v1.11.3",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.7",
     "Helm-controller": "v0.15.15",
     "Ingress-Nginx": "v1.10.5-hardened3",
     "Kubernetes": "v1.29.10",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.2",
     "Runc": "v1.1.14"
    },
    "date": "2024-10-30",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.11+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.000",
     "rke2-calico-crd": "v3.29.000",
     "rke2-canal": "v3.29.0-build2024110400",
     "rke2-cilium": "1.16.303",
     "rke2-coredns": "1.33.005",
     "rke2-ingress-nginx": "4.10.502",
     "rke2-metrics-server": "3.12.004",
     "rke2-snapshot-controller": "3.0.601",
     "rke2-snapshot-controller-crd": "3.0.601",
     "rke2-snapshot-validation-webhook": "1.9.001"
    },
    "components": {
     "Calico": "v3.29.0",
     "Canal": "Flannel v0.26.0 + Calico v3.29.0",
     "Cilium": "v1.16.3",
     "Containerd": "v1.7.23-k3s2",
     "CoreDNS": "v1.11.3",
     "Etcd": "v3.5.16-k3s1",
     "Flannel": "v0.26.0",
     "Helm-controller": "v0.15.15",
     "Ingress-Nginx": "v1.10.5-hardened4",
     "Kubernetes": "v1.29.11",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.3",
     "Runc": "v1.1.14"
    },
    "date": "2024-12-06",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.12+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.100",
     "rke2-calico-crd": "v3.29.100",
     "rke2-canal": "v3.29.1-build2024121100",
     "rke2-cilium": "1.16.400",
     "rke2-coredns": "1.36.102",
     "rke2-ingress-nginx": "4.10.503",
     "rke2-metrics-server": "3.12.004",
     "rke2-snapshot-controller": "3.0.601",
     "rke2-snapshot-controller-crd": "3.0.601",
     "rke2-snapshot-validation-webhook": "1.9.001"
    },
    "components": {
     "Calico": "v3.29.1",
     "Canal": "Flannel v0.26.1 + Calico v3.29.1",
     "Cilium": "v1.16.4",
     "Containerd": "v1.7.23-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.16-k3s1",
     "Flannel": "v0.26.1",
     "Helm-controller": "v0.15.15",
     "Ingress-Nginx": "v1.10.5-hardened6",
     "Kubernetes": "v1.29.12",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.3",
     "Runc": "v1.1.14"
    },
    "date": "2024-12-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.13+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.101",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.1-build2025011000",
     "rke2-cilium": "1.16.501",
     "rke2-coredns": "1.36.102",
     "rke2-ingress-nginx": "4.12.003",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.1",
     "Canal": "Flannel v0.26.3 + Calico v3.29.1",
     "Cilium": "v1.16.5",
     "Containerd": "v1.7.23-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.16-k3s1",
     "Flannel": "v0.26.3",
     "Helm-controller": "v0.15.15",
     "Ingress-Nginx": "v1.12.0-hardened2",
     "Kubernetes": "v1.29.13",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.1.4",
     "Runc": "v1.2.4"
    },
    "date": "2025-01-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.14+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.200",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.2-build2025021800",
     "rke2-cilium": "1.17.000",
     "rke2-coredns": "1.36.102",
     "rke2-ingress-nginx": "4.12.005",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.2",
     "Canal": "Flannel v0.26.4 + Calico v3.29.2",
     "Cilium": "v1.17.0",
     "Containerd": "v1.7.23-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.18-k3s1",
     "Flannel": "v0.26.4",
     "Helm-controller": "v0.15.16",
     "Ingress-Nginx": "v1.12.0-hardened6",
     "Kubernetes": "v1.29.14",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.1.4",
     "Runc": "v1.2.4"
    },
    "date": "2025-02-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.15+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.200",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.2-build2025030601",
     "rke2-cilium": "1.17.100",
     "rke2-coredns": "1.39.100",
     "rke2-ingress-nginx": "4.12.100",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.2",
     "Canal": "Flannel v0.26.5 + Calico v3.29.2",
     "Cilium": "v1.17.1",
     "Containerd": "v1.7.26-k3s1",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.19-k3s1",
     "Flannel": "v0.26.5",
     "Helm-controller": "v0.15.16",
     "Ingress-Nginx": "v1.12.1-hardened1",
     "Kubernetes": "v1.29.15",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.1.4",
     "Runc": "v1.2.5"
    },
    "date": "2025-03-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.2+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.002",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.0-build2024020601",
     "rke2-cilium": "1.15.100",
     "rke2-coredns": "1.29.001",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051513",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.0",
     "Canal": "Flannel v0.24.2 + Calico v3.27.0",
     "Cilium": "v1.15.1",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.24.2",
     "Helm-controller": "v0.15.8",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.29.2",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-02-29",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.3+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.200",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.2-build2024030800",
     "rke2-cilium": "1.15.100",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.8.200",
     "rke2-metrics-server": "2.11.100-build2023051513",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.2",
     "Canal": "Flannel v0.24.3 + Calico v3.27.2",
     "Cilium": "v1.15.1",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.24.3",
     "Helm-controller": "v0.15.9",
     "Ingress-Nginx": "nginx-1.9.3-hardened1",
     "Kubernetes": "v1.29.3",
     "Metrics-server": "v0.6.3",
     "Multus": "v4.0.2",
     "Runc": "v1.1."
    },
    "date": "2024-03-20",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.4+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.3-build2024042301",
     "rke2-cilium": "1.15.400",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.9.100",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.1 + Calico v3.27.3",
     "Cilium": "v1.15.4",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.25.1",
     "Helm-controller": "v0.15.9",
     "Ingress-Nginx": "nginx-1.9.6-hardened1",
     "Kubernetes": "v1.29.4",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-04-29",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.5+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.3-build2024042301",
     "rke2-cilium": "1.15.500",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.9.100",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.1 + Calico v3.27.3",
     "Cilium": "v1.15.5",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.25.1",
     "Helm-controller": "v0.15.9",
     "Ingress-Nginx": "nginx-1.9.6-hardened1",
     "Kubernetes": "v1.29.5",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-05-22",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.6+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.28.0-build2024062503",
     "rke2-cilium": "1.15.500",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.10.101",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.4 + Calico v3.28.0",
     "Cilium": "v1.15.5",
     "Containerd": "v1.7.17-k3s1",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.4",
     "Helm-controller": "v0.15.10",
     "Ingress-Nginx": "v1.10.1-hardened1",
     "Kubernetes": "v1.29.6",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-07-01",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.7+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.28.0-build2024062503",
     "rke2-cilium": "1.15.500",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.10.102",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.4 + Calico v3.28.0",
     "Cilium": "v1.15.5",
     "Containerd": "v1.7.17-k3s1",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.4",
     "Helm-controller": "v0.15.10",
     "Ingress-Nginx": "v1.10.1-hardened1",
     "Kubernetes": "v1.29.7",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-08-01",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.8+rke2r1": {
    "charts": {
     "rke2-calico": "v3.28.100",
     "rke2-calico-crd": "v3.28.100",
     "rke2-canal": "v3.28.1-build2024080600",
     "rke2-cilium": "1.16.000",
     "rke2-coredns": "1.29.004",
     "rke2-ingress-nginx": "4.10.401",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.28.1",
     "Canal": "Flannel v0.25.5 + Calico v3.28.1",
     "Cilium": "v1.16.0",
     "Containerd": "v1.7.20-k3s1",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.5",
     "Helm-controller": "v0.15.10",
     "Ingress-Nginx": "v1.10.4-hardened2",
     "Kubernetes": "v1.29.8",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-08-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.29.9+rke2r1": {
    "charts": {
     "rke2-calico": "v3.28.100",
     "rke2-calico-crd": "v3.28.100",
     "rke2-canal": "v3.28.1-build2024091100",
     "rke2-cilium": "1.16.104",
     "rke2-coredns": "1.29.006",
     "rke2-ingress-nginx": "4.10.402",
     "rke2-metrics-server": "3.12.003",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.28.1",
     "Canal": "Flannel v0.25.6 + Calico v3.28.1",
     "Cilium": "v1.16.1",
     "Containerd": "v1.7.21-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.6",
     "Helm-controller": "v0.15.13",
     "Ingress-Nginx": "v1.10.4-hardened3",
     "Kubernetes": "v1.29.9",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.0",
     "Runc": "v1.1.14"
    },
    "date": "2024-09-23",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.0+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.3-build2024042301",
     "rke2-cilium": "1.15.400",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.9.100",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.1 + Calico v3.27.3",
     "Cilium": "v1.15.4",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.25.1",
     "Helm-controller": "v0.16.1",
     "Ingress-Nginx": "nginx-1.9.6-hardened1",
     "Kubernetes": "v1.30.0",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-05-09",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.1+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.27.3-build2024042301",
     "rke2-cilium": "1.15.500",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.9.100",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.1 + Calico v3.27.3",
     "Cilium": "v1.15.5",
     "Containerd": "v1.7.11-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.9-k3s1",
     "Flannel": "v0.25.1",
     "Helm-controller": "v0.16.1-0.20240502205943-2f32059d43e6",
     "Ingress-Nginx": "nginx-1.9.6-hardened1",
     "Kubernetes": "v1.30.1",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-05-22",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.10+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.200",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.2-build2025021800",
     "rke2-cilium": "1.17.000",
     "rke2-coredns": "1.36.102",
     "rke2-ingress-nginx": "4.12.005",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.2",
     "Canal": "Flannel v0.26.4 + Calico v3.29.2",
     "Cilium": "v1.17.0",
     "Containerd": "v1.7.23-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.18-k3s1",
     "Flannel": "v0.26.4",
     "Helm-controller": "v0.16.6",
     "Ingress-Nginx": "v1.12.0-hardened6",
     "Kubernetes": "v1.30.10",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.1.4",
     "Runc": "v1.2.4"
    },
    "date": "2025-02-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.11+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.200",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.2-build2025030601",
     "rke2-cilium": "1.17.100",
     "rke2-coredns": "1.39.100",
     "rke2-ingress-nginx": "4.12.100",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.2",
     "Canal": "Flannel v0.26.5 + Calico v3.29.2",
     "Cilium": "v1.17.1",
     "Containerd": "v1.7.26-k3s1",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.19-k3s1",
     "Flannel": "v0.26.5",
     "Helm-controller": "v0.16.6",
     "Ingress-Nginx": "v1.12.1-hardened1",
     "Kubernetes": "v1.30.11",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.1.4",
     "Runc": "v1.2.5"
    },
    "date": "2025-03-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.12+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.300",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.3-build2025040801",
     "rke2-cilium": "1.17.300",
     "rke2-coredns": "1.39.201",
     "rke2-ingress-nginx": "4.12.101",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.3",
     "Canal": "Flannel v0.26.6 + Calico v3.29.3",
     "Cilium": "v1.17.3",
     "Containerd": "v1.7.26-k3s1",
     "CoreDNS": "v1.12.1",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.26.6",
     "Helm-controller": "v0.16.10",
     "Ingress-Nginx": "v1.12.1-hardened3",
     "Kubernetes": "v1.30.12",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.2.0",
     "Runc": "v1.2.5"
    },
    "date": "2025-05-01",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.13+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.001",
     "rke2-calico-crd": "v3.30.001",
     "rke2-canal": "v3.30.0-build2025051500",
     "rke2-cilium": "1.17.301",
     "rke2-coredns": "1.42.000",
     "rke2-ingress-nginx": "4.12.103",
     "rke2-metrics-server": "3.12.201",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.0",
     "Canal": "Flannel v0.26.7 + Calico v3.30.0",
     "Cilium": "v1.17.3",
     "Containerd": "v1.7.27-k3s1",
     "CoreDNS": "v1.12.1",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.26.7",
     "Helm-controller": "v0.16.10",
     "Ingress-Nginx": "v1.12.1-hardened6",
     "Kubernetes": "v1.30.13",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.2.0",
     "Runc": "v1.2.6"
    },
    "date": "2025-05-21",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.14+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.100",
     "rke2-calico-crd": "v3.30.100",
     "rke2-canal": "v3.30.1-build2025061101",
     "rke2-cilium": "1.17.401",
     "rke2-coredns": "1.42.302",
     "rke2-ingress-nginx": "4.12.201",
     "rke2-metrics-server": "3.12.202",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.1",
     "Canal": "Flannel v0.27.0 + Calico v3.30.1",
     "Cilium": "v1.17.4",
     "Containerd": "v1.7.27-k3s1",
     "CoreDNS": "v1.12.2",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.0",
     "Helm-controller": "v0.16.11",
     "Ingress-Nginx": "v1.12.2-hardened2",
     "Kubernetes": "v1.30.14",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.2.1",
     "Runc": "v1.2.6"
    },
    "date": "2025-06-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.14+rke2r2": {
    "charts": {
     "rke2-calico": "v3.30.100",
     "rke2-calico-crd": "v3.30.100",
     "rke2-canal": "v3.30.2-build2025071100",
     "rke2-cilium": "1.17.600",
     "rke2-coredns": "1.42.302",
     "rke2-ingress-nginx": "4.12.401",
     "rke2-metrics-server": "3.12.203",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.1",
     "Canal": "Flannel v0.27.1 + Calico v3.30.2",
     "Cilium": "v1.17.6",
     "Containerd": "v1.7.27-k3s1",
     "CoreDNS": "v1.12.2",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.1",
     "Helm-controller": "v0.16.13",
     "Ingress-Nginx": "v1.12.4-hardened2",
     "Kubernetes": "v1.30.14",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.1",
     "Runc": "v1.2.6"
    },
    "date": "2025-07-25",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.14+rke2r4": {
    "charts": {
     "rke2-calico": "v3.30.200",
     "rke2-calico-crd": "v3.30.200",
     "rke2-canal": "v3.30.2-build2025073100",
     "rke2-cilium": "1.18.000",
     "rke2-coredns": "1.43.101",
     "rke2-ingress-nginx": "4.12.404",
     "rke2-metrics-server": "3.13.000",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.2",
     "Canal": "Flannel v0.27.2 + Calico v3.30.2",
     "Cilium": "v1.18.0",
     "Containerd": "v1.7.27-k3s1",
     "CoreDNS": "v1.12.3",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.2",
     "Helm-controller": "v0.16.13",
     "Ingress-Nginx": "v1.12.4-hardened7",
     "Kubernetes": "v1.30.14",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.2",
     "Runc": "v1.2.7"
    },
    "date": "2025-09-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.2+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.28.0-build2024062503",
     "rke2-cilium": "1.15.500",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.10.101",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.4 + Calico v3.28.0",
     "Cilium": "v1.15.5",
     "Containerd": "v1.7.17-k3s1",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.4",
     "Helm-controller": "v0.16.1",
     "Ingress-Nginx": "v1.10.1-hardened1",
     "Kubernetes": "v1.30.2",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-07-01",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.3+rke2r1": {
    "charts": {
     "rke2-calico": "v3.27.300",
     "rke2-calico-crd": "v3.27.002",
     "rke2-canal": "v3.28.0-build2024062503",
     "rke2-cilium": "1.15.500",
     "rke2-coredns": "1.29.002",
     "rke2-ingress-nginx": "4.10.102",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.27.3",
     "Canal": "Flannel v0.25.4 + Calico v3.28.0",
     "Cilium": "v1.15.5",
     "Containerd": "v1.7.17-k3s1",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.4",
     "Helm-controller": "v0.16.1",
     "Ingress-Nginx": "v1.10.1-hardened1",
     "Kubernetes": "v1.30.3",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-08-01",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.4+rke2r1": {
    "charts": {
     "rke2-calico": "v3.28.100",
     "rke2-calico-crd": "v3.28.100",
     "rke2-canal": "v3.28.1-build2024080600",
     "rke2-cilium": "1.16.000",
     "rke2-coredns": "1.29.004",
     "rke2-ingress-nginx": "4.10.401",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.28.1",
     "Canal": "Flannel v0.25.5 + Calico v3.28.1",
     "Cilium": "v1.16.0",
     "Containerd": "v1.7.20-k3s1",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.5",
     "Helm-controller": "v0.16.1",
     "Ingress-Nginx": "v1.10.4-hardened2",
     "Kubernetes": "v1.30.4",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.12"
    },
    "date": "2024-08-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.5+rke2r1": {
    "charts": {
     "rke2-calico": "v3.28.100",
     "rke2-calico-crd": "v3.28.100",
     "rke2-canal": "v3.28.1-build2024091100",
     "rke2-cilium": "1.16.104",
     "rke2-coredns": "1.29.006",
     "rke2-ingress-nginx": "4.10.402",
     "rke2-metrics-server": "3.12.003",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.28.1",
     "Canal": "Flannel v0.25.6 + Calico v3.28.1",
     "Cilium": "v1.16.1",
     "Containerd": "v1.7.21-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.6",
     "Helm-controller": "v0.16.4",
     "Ingress-Nginx": "v1.10.4-hardened3",
     "Kubernetes": "v1.30.5",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.0",
     "Runc": "v1.1.14"
    },
    "date": "2024-09-23",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.6+rke2r1": {
    "charts": {
     "rke2-calico": "v3.28.200",
     "rke2-calico-crd": "v3.28.200",
     "rke2-canal": "v3.28.2-build2024101601",
     "rke2-cilium": "1.16.201",
     "rke2-coredns": "1.33.002",
     "rke2-ingress-nginx": "4.10.501",
     "rke2-metrics-server": "3.12.004",
     "rke2-snapshot-controller": "3.0.601",
     "rke2-snapshot-controller-crd": "3.0.601",
     "rke2-snapshot-validation-webhook": "1.9.001"
    },
    "components": {
     "Calico": "v3.28.2",
     "Canal": "Flannel v0.25.7 + Calico v3.28.2",
     "Cilium": "v1.16.2",
     "Containerd": "v1.7.22-k3s1",
     "CoreDNS": "v1.11.3",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.7",
     "Helm-controller": "v0.16.5",
     "Ingress-Nginx": "v1.10.5-hardened3",
     "Kubernetes": "v1.30.6",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.2",
     "Runc": "v1.1.14"
    },
    "date": "2024-10-30",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.7+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.000",
     "rke2-calico-crd": "v3.29.000",
     "rke2-canal": "v3.29.0-build2024110400",
     "rke2-cilium": "1.16.303",
     "rke2-coredns": "1.33.005",
     "rke2-ingress-nginx": "4.10.502",
     "rke2-metrics-server": "3.12.004",
     "rke2-snapshot-controller": "3.0.601",
     "rke2-snapshot-controller-crd": "3.0.601",
     "rke2-snapshot-validation-webhook": "1.9.001"
    },
    "components": {
     "Calico": "v3.29.0",
     "Canal": "Flannel v0.26.0 + Calico v3.29.0",
     "Cilium": "v1.16.3",
     "Containerd": "v1.7.23-k3s2",
     "CoreDNS": "v1.11.3",
     "Etcd": "v3.5.16-k3s1",
     "Flannel": "v0.26.0",
     "Helm-controller": "v0.16.5",
     "Ingress-Nginx": "v1.10.5-hardened4",
     "Kubernetes": "v1.30.7",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.3",
     "Runc": "v1.1.14"
    },
    "date": "2024-12-06",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.8+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.100",
     "rke2-calico-crd": "v3.29.100",
     "rke2-canal": "v3.29.1-build2024121100",
     "rke2-cilium": "1.16.400",
     "rke2-coredns": "1.36.102",
     "rke2-ingress-nginx": "4.10.503",
     "rke2-metrics-server": "3.12.004",
     "rke2-snapshot-controller": "3.0.601",
     "rke2-snapshot-controller-crd": "3.0.601",
     "rke2-snapshot-validation-webhook": "1.9.001"
    },
    "components": {
     "Calico": "v3.29.1",
     "Canal": "Flannel v0.26.1 + Calico v3.29.1",
     "Cilium": "v1.16.4",
     "Containerd": "v1.7.23-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.16-k3s1",
     "Flannel": "v0.26.1",
     "Helm-controller": "v0.16.5",
     "Ingress-Nginx": "v1.10.5-hardened6",
     "Kubernetes": "v1.30.8",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.3",
     "Runc": "v1.1.14"
    },
    "date": "2024-12-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.30.9+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.101",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.1-build2025011000",
     "rke2-cilium": "1.16.501",
     "rke2-coredns": "1.36.102",
     "rke2-ingress-nginx": "4.12.003",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.1",
     "Canal": "Flannel v0.26.3 + Calico v3.29.1",
     "Cilium": "v1.16.5",
     "Containerd": "v1.7.23-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.16-k3s1",
     "Flannel": "v0.26.3",
     "Helm-controller": "v0.16.5",
     "Ingress-Nginx": "v1.12.0-hardened2",
     "Kubernetes": "v1.30.9",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.1.4",
     "Runc": "v1.2.4"
    },
    "date": "2025-01-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.0+rke2r1": {
    "charts": {
     "rke2-calico": "v3.28.100",
     "rke2-calico-crd": "v3.28.100",
     "rke2-canal": "v3.28.1-build2024082701",
     "rke2-cilium": "1.16.101",
     "rke2-coredns": "1.29.004",
     "rke2-ingress-nginx": "4.10.401",
     "rke2-metrics-server": "3.12.002",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.28.1",
     "Canal": "Flannel v0.25.6 + Calico v3.28.1",
     "Cilium": "v1.16.1",
     "Containerd": "v1.7.20-k3s1",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.6",
     "Helm-controller": "v0.16.3",
     "Ingress-Nginx": "v1.10.4-hardened2",
     "Kubernetes": "v1.31.0",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.0.2",
     "Runc": "v1.1.13"
    },
    "date": "2024-09-04",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.1+rke2r1": {
    "charts": {
     "rke2-calico": "v3.28.100",
     "rke2-calico-crd": "v3.28.100",
     "rke2-canal": "v3.28.1-build2024091100",
     "rke2-cilium": "1.16.104",
     "rke2-coredns": "1.29.006",
     "rke2-ingress-nginx": "4.10.402",
     "rke2-metrics-server": "3.12.003",
     "rke2-snapshot-controller": "1.7.202",
     "rke2-snapshot-controller-crd": "1.7.202",
     "rke2-snapshot-validation-webhook": "1.7.302"
    },
    "components": {
     "Calico": "v3.28.1",
     "Canal": "Flannel v0.25.6 + Calico v3.28.1",
     "Cilium": "v1.16.1",
     "Containerd": "v1.7.21-k3s2",
     "CoreDNS": "v1.11.1",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.6",
     "Helm-controller": "v0.16.4",
     "Ingress-Nginx": "v1.10.4-hardened3",
     "Kubernetes": "v1.31.1",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.0",
     "Runc": "v1.1.14"
    },
    "date": "2024-09-23",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.10+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.100",
     "rke2-calico-crd": "v3.30.100",
     "rke2-canal": "v3.30.1-build2025061101",
     "rke2-cilium": "1.17.401",
     "rke2-coredns": "1.42.302",
     "rke2-ingress-nginx": "4.12.201",
     "rke2-metrics-server": "3.12.202",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.1",
     "Canal": "Flannel v0.27.0 + Calico v3.30.1",
     "Cilium": "v1.17.4",
     "Containerd": "v2.0.5-k3s1",
     "CoreDNS": "v1.12.2",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.0",
     "Helm-controller": "v0.16.11",
     "Ingress-Nginx": "v1.12.2-hardened2",
     "Kubernetes": "v1.31.10",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.2.1",
     "Runc": "v1.2.6"
    },
    "date": "2025-06-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.11+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.100",
     "rke2-calico-crd": "v3.30.100",
     "rke2-canal": "v3.30.2-build2025071100",
     "rke2-cilium": "1.17.600",
     "rke2-coredns": "1.42.302",
     "rke2-ingress-nginx": "4.12.401",
     "rke2-metrics-server": "3.12.203",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.1",
     "Canal": "Flannel v0.27.1 + Calico v3.30.2",
     "Cilium": "v1.17.6",
     "Containerd": "v2.0.5-k3s2",
     "CoreDNS": "v1.12.2",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.1",
     "Helm-controller": "v0.16.13",
     "Ingress-Nginx": "v1.12.4-hardened2",
     "Kubernetes": "v1.31.11",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.1",
     "Runc": "v1.2.6"
    },
    "date": "2025-07-25",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.12+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.200",
     "rke2-calico-crd": "v3.30.200",
     "rke2-canal": "v3.30.2-build2025073100",
     "rke2-cilium": "1.18.000",
     "rke2-coredns": "1.43.101",
     "rke2-ingress-nginx": "4.12.404",
     "rke2-metrics-server": "3.13.000",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.2",
     "Canal": "Flannel v0.27.2 + Calico v3.30.2",
     "Cilium": "v1.18.0",
     "Containerd": "v2.0.5-k3s2",
     "CoreDNS": "v1.12.3",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.2",
     "Helm-controller": "v0.16.13",
     "Ingress-Nginx": "v1.12.4-hardened7",
     "Kubernetes": "v1.31.12",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.2",
     "Runc": "v1.2.6"
    },
    "date": "2025-08-23",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.13+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.300",
     "rke2-calico-crd": "v3.30.300",
     "rke2-canal": "v3.30.3-build2025090900",
     "rke2-cilium": "1.18.103",
     "rke2-coredns": "1.43.302",
     "rke2-ingress-nginx": "4.12.600",
     "rke2-metrics-server": "3.13.001",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.3",
     "Canal": "Flannel v0.27.3 + Calico v3.30.3",
     "Cilium": "v1.18.1",
     "Containerd": "v2.1.4-k3s2",
     "CoreDNS": "v1.12.3",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.3",
     "Helm-controller": "v0.16.13",
     "Ingress-Nginx": "v1.12.6-hardened1",
     "Kubernetes": "v1.31.13",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.2",
     "Runc": "v1.3.1"
    },
    "date": "2025-09-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.14+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.401",
     "rke2-calico-crd": "v3.30.401",
     "rke2-canal": "v3.30.3-build2025101500",
     "rke2-cilium": "1.18.300",
     "rke2-coredns": "1.44.300",
     "rke2-ingress-nginx": "4.13.400",
     "rke2-metrics-server": "3.13.002",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.4",
     "Canal": "Flannel v0.27.4 + Calico v3.30.3",
     "Cilium": "v1.18.3",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.13.1",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.4",
     "Helm-controller": "v0.16.16",
     "Ingress-Nginx": "v1.13.4-hardened1",
     "Kubernetes": "v1.31.14",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.3",
     "Runc": "v1.3.3"
    },
    "date": "2025-11-20",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.14+rke2r2": {
    "charts": {
     "rke2-calico": "v3.31.200",
     "rke2-calico-crd": "v3.31.200",
     "rke2-canal": "v3.31.2-build2025120500",
     "rke2-cilium": "1.18.401",
     "rke2-coredns": "1.45.003",
     "rke2-ingress-nginx": "4.13.500",
     "rke2-metrics-server": "3.13.004",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-traefik": "27.0.204",
     "rke2-traefik-crd": "27.0.204"
    },
    "components": {
     "Calico": "v3.31.2",
     "Canal": "Flannel v0.27.4 + Calico v3.31.2",
     "Cilium": "v1.18.4",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.13.1",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.4",
     "Helm-controller": "v0.16.16",
     "Ingress-Nginx": "v1.13.5-hardened2",
     "Kubernetes": "v1.31.14",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.4",
     "Runc": "v1.3.3"
    },
    "date": "2026-03-18",
    "notes": [],
    "prime_only": True,
    "pulled": False
   },
   "v1.31.2+rke2r1": {
    "charts": {
     "rke2-calico": "v3.28.200",
     "rke2-calico-crd": "v3.28.200",
     "rke2-canal": "v3.28.2-build2024101601",
     "rke2-cilium": "1.16.201",
     "rke2-coredns": "1.33.002",
     "rke2-ingress-nginx": "4.10.501",
     "rke2-metrics-server": "3.12.004",
     "rke2-snapshot-controller": "3.0.601",
     "rke2-snapshot-controller-crd": "3.0.601",
     "rke2-snapshot-validation-webhook": "1.9.001"
    },
    "components": {
     "Calico": "v3.28.2",
     "Canal": "Flannel v0.25.7 + Calico v3.28.2",
     "Cilium": "v1.16.2",
     "Containerd": "v1.7.22-k3s1",
     "CoreDNS": "v1.11.3",
     "Etcd": "v3.5.13-k3s1",
     "Flannel": "v0.25.7",
     "Helm-controller": "v0.16.5",
     "Ingress-Nginx": "v1.10.5-hardened3",
     "Kubernetes": "v1.31.2",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.2",
     "Runc": "v1.1.14"
    },
    "date": "2024-10-30",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.3+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.000",
     "rke2-calico-crd": "v3.29.000",
     "rke2-canal": "v3.29.0-build2024110400",
     "rke2-cilium": "1.16.303",
     "rke2-coredns": "1.33.005",
     "rke2-ingress-nginx": "4.10.502",
     "rke2-metrics-server": "3.12.004",
     "rke2-snapshot-controller": "3.0.601",
     "rke2-snapshot-controller-crd": "3.0.601",
     "rke2-snapshot-validation-webhook": "1.9.001"
    },
    "components": {
     "Calico": "v3.29.0",
     "Canal": "Flannel v0.26.0 + Calico v3.29.0",
     "Cilium": "v1.16.3",
     "Containerd": "v1.7.23-k3s2",
     "CoreDNS": "v1.11.3",
     "Etcd": "v3.5.16-k3s1",
     "Flannel": "v0.26.0",
     "Helm-controller": "v0.16.5",
     "Ingress-Nginx": "v1.10.5-hardened4",
     "Kubernetes": "v1.31.3",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.3",
     "Runc": "v1.1.14"
    },
    "date": "2024-12-06",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.4+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.100",
     "rke2-calico-crd": "v3.29.100",
     "rke2-canal": "v3.29.1-build2024121100",
     "rke2-cilium": "1.16.400",
     "rke2-coredns": "1.36.102",
     "rke2-ingress-nginx": "4.10.503",
     "rke2-metrics-server": "3.12.004",
     "rke2-snapshot-controller": "3.0.601",
     "rke2-snapshot-controller-crd": "3.0.601",
     "rke2-snapshot-validation-webhook": "1.9.001"
    },
    "components": {
     "Calico": "v3.29.1",
     "Canal": "Flannel v0.26.1 + Calico v3.29.1",
     "Cilium": "v1.16.4",
     "Containerd": "v1.7.23-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.16-k3s1",
     "Flannel": "v0.26.1",
     "Helm-controller": "v0.16.5",
     "Ingress-Nginx": "v1.10.5-hardened6",
     "Kubernetes": "v1.31.4",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.3",
     "Runc": "v1.1.14"
    },
    "date": "2024-12-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.5+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.101",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.1-build2025011000",
     "rke2-cilium": "1.16.501",
     "rke2-coredns": "1.36.102",
     "rke2-ingress-nginx": "4.12.003",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.1",
     "Canal": "Flannel v0.26.3 + Calico v3.29.1",
     "Cilium": "v1.16.5",
     "Containerd": "v1.7.23-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.16-k3s1",
     "Flannel": "v0.26.3",
     "Helm-controller": "v0.16.5",
     "Ingress-Nginx": "v1.12.0-hardened2",
     "Kubernetes": "v1.31.5",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.1.4",
     "Runc": "v1.2.4"
    },
    "date": "2025-01-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.6+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.200",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.2-build2025021800",
     "rke2-cilium": "1.17.000",
     "rke2-coredns": "1.36.102",
     "rke2-ingress-nginx": "4.12.005",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.2",
     "Canal": "Flannel v0.26.4 + Calico v3.29.2",
     "Cilium": "v1.17.0",
     "Containerd": "v2.0.2-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.18-k3s1",
     "Flannel": "v0.26.4",
     "Helm-controller": "v0.16.6",
     "Ingress-Nginx": "v1.12.0-hardened6",
     "Kubernetes": "v1.31.6",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.1.4",
     "Runc": "v1.2.4"
    },
    "date": "2025-02-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.7+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.200",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.2-build2025030601",
     "rke2-cilium": "1.17.100",
     "rke2-coredns": "1.39.100",
     "rke2-ingress-nginx": "4.12.100",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.2",
     "Canal": "Flannel v0.26.5 + Calico v3.29.2",
     "Cilium": "v1.17.1",
     "Containerd": "v2.0.4-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.19-k3s1",
     "Flannel": "v0.26.5",
     "Helm-controller": "v0.16.6",
     "Ingress-Nginx": "v1.12.1-hardened1",
     "Kubernetes": "v1.31.7",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.1.4",
     "Runc": "v1.2.5"
    },
    "date": "2025-03-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.8+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.300",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.3-build2025040801",
     "rke2-cilium": "1.17.300",
     "rke2-coredns": "1.39.201",
     "rke2-ingress-nginx": "4.12.101",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.3",
     "Canal": "Flannel v0.26.6 + Calico v3.29.3",
     "Cilium": "v1.17.3",
     "Containerd": "v2.0.4-k3s2",
     "CoreDNS": "v1.12.1",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.26.6",
     "Helm-controller": "v0.16.10",
     "Ingress-Nginx": "v1.12.1-hardened3",
     "Kubernetes": "v1.31.8",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.2.0",
     "Runc": "v1.2.5"
    },
    "date": "2025-05-01",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.31.9+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.001",
     "rke2-calico-crd": "v3.30.001",
     "rke2-canal": "v3.30.0-build2025051500",
     "rke2-cilium": "1.17.301",
     "rke2-coredns": "1.42.000",
     "rke2-ingress-nginx": "4.12.103",
     "rke2-metrics-server": "3.12.201",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.0",
     "Canal": "Flannel v0.26.7 + Calico v3.30.0",
     "Cilium": "v1.17.3",
     "Containerd": "v2.0.5-k3s1",
     "CoreDNS": "v1.12.1",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.26.7",
     "Helm-controller": "v0.16.10",
     "Ingress-Nginx": "v1.12.1-hardened6",
     "Kubernetes": "v1.31.9",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.2.0",
     "Runc": "v1.2.6"
    },
    "date": "2025-05-21",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.0+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.100",
     "rke2-calico-crd": "v3.29.100",
     "rke2-canal": "v3.29.1-build2024121100",
     "rke2-cilium": "1.16.400",
     "rke2-coredns": "1.36.102",
     "rke2-ingress-nginx": "4.10.503",
     "rke2-metrics-server": "3.12.004",
     "rke2-snapshot-controller": "3.0.601",
     "rke2-snapshot-controller-crd": "3.0.601",
     "rke2-snapshot-validation-webhook": "1.9.001"
    },
    "components": {
     "Calico": "v3.29.1",
     "Canal": "Flannel v0.26.1 + Calico v3.29.1",
     "Cilium": "v1.16.4",
     "Containerd": "v1.7.23-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.16-k3s1",
     "Flannel": "v0.26.1",
     "Helm-controller": "v0.16.5",
     "Ingress-Nginx": "v1.10.5-hardened6",
     "Kubernetes": "v1.32.0",
     "Metrics-server": "v0.7.1",
     "Multus": "v4.1.3",
     "Runc": "v1.1.14"
    },
    "date": "2025-01-03",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.1+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.101",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.1-build2025011000",
     "rke2-cilium": "1.16.501",
     "rke2-coredns": "1.36.102",
     "rke2-ingress-nginx": "4.12.003",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.1",
     "Canal": "Flannel v0.26.3 + Calico v3.29.1",
     "Cilium": "v1.16.5",
     "Containerd": "v1.7.23-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.16-k3s1",
     "Flannel": "v0.26.3",
     "Helm-controller": "v0.16.5",
     "Ingress-Nginx": "v1.12.0-hardened2",
     "Kubernetes": "v1.32.1",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.1.4",
     "Runc": "v1.2.4"
    },
    "date": "2025-01-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.10+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.401",
     "rke2-calico-crd": "v3.30.401",
     "rke2-canal": "v3.30.3-build2025101500",
     "rke2-cilium": "1.18.300",
     "rke2-coredns": "1.44.300",
     "rke2-ingress-nginx": "4.13.400",
     "rke2-metrics-server": "3.13.002",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.4",
     "Canal": "Flannel v0.27.4 + Calico v3.30.3",
     "Cilium": "v1.18.3",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.13.1",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.4",
     "Helm-controller": "v0.16.16",
     "Ingress-Nginx": "v1.13.4-hardened1",
     "Kubernetes": "v1.32.10",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.3",
     "Runc": "v1.3.3"
    },
    "date": "2025-11-20",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.11+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.200",
     "rke2-calico-crd": "v3.31.200",
     "rke2-canal": "v3.31.2-build2025120500",
     "rke2-cilium": "1.18.401",
     "rke2-coredns": "1.45.003",
     "rke2-ingress-nginx": "4.13.500",
     "rke2-metrics-server": "3.13.004",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.31.2",
     "Canal": "Flannel v0.27.4 + Calico v3.31.2",
     "Cilium": "v1.18.4",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.13.1",
     "Etcd": "v3.5.25-k3s1",
     "Flannel": "v0.27.4",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.13.5-hardened2",
     "Kubernetes": "v1.32.11",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0"
    },
    "date": "2025-12-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.11+rke2r3": {
    "charts": {
     "rke2-calico": "v3.31.300",
     "rke2-calico-crd": "v3.31.300",
     "rke2-canal": "v3.31.3-build2026011900",
     "rke2-cilium": "1.18.601",
     "rke2-coredns": "1.45.008",
     "rke2-ingress-nginx": "4.14.301",
     "rke2-metrics-server": "3.13.006",
     "rke2-snapshot-controller": "4.2.000",
     "rke2-snapshot-controller-crd": "4.2.000",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "38.0.201",
     "rke2-traefik-crd": "38.0.201"
    },
    "components": {
     "Calico": "v3.31.3",
     "Canal": "Flannel v0.28.0 + Calico v3.31.3",
     "Cilium": "v1.18.6",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.14.1",
     "Etcd": "v3.5.26-k3s1",
     "Flannel": "v0.28.0",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.3-hardened1",
     "Kubernetes": "v1.32.11",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0",
     "Traefik": "v3.6.7"
    },
    "date": "2026-02-04",
    "notes": [
     "This warning targets users who perform upgrades by adding new nodes to the cluster, and removing old ones. If your etcd cluster membership is and has been consistent across versions, you should NOT be affected by this issue.",
     "RKE2 v1.34 and higher include etcd 3.6. Maintainers of the etcd project have indicated that there no safe path from etcd 3.5 to 3.6 except by upgrading to v3.5.26 first.",
     "In mid December, the project released an announcement indicating that there is NO safe path from etcd 3.5 to 3.6 except by upgrading to v3.5.26 first. Failure to do so can cause the cluster to report “zombie members” (etcd nodes that were removed from the cluster some time ago) re-appearing and joining database consensus, ultimately causing the cluster to lose quorum. This updated blog post contradicts previous announcements on this topic, which indicated that it was safe to upgrade from v3.5.20+ as long as nodes had been restarted at least once, to reconcile membership lists across internal s",
     "The January releases of RKE2 v1.32 and v1.33 will include etcd v3.5.26. All users should plan on upgrading to this patch release, prior to upgrading to v1.34 and v1.35."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.12+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.300",
     "rke2-calico-crd": "v3.31.300",
     "rke2-canal": "v3.31.3-build2026020600",
     "rke2-cilium": "1.19.001",
     "rke2-coredns": "1.45.201",
     "rke2-ingress-nginx": "4.14.302",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.001",
     "rke2-snapshot-controller-crd": "4.2.001",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.000",
     "rke2-traefik-crd": "39.0.000"
    },
    "components": {
     "Calico": "v3.31.3",
     "Canal": "Flannel v0.28.1 + Calico v3.31.3",
     "Cilium": "v1.19.0",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.14.1",
     "Etcd": "v3.5.26-k3s1",
     "Flannel": "v0.28.1",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.3-hardened2",
     "Kubernetes": "v1.32.12",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0",
     "Traefik": "v3.6.7"
    },
    "date": "2026-02-13",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.13+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.300",
     "rke2-calico-crd": "v3.31.300",
     "rke2-canal": "v3.31.3-build2026020600",
     "rke2-cilium": "1.19.100",
     "rke2-coredns": "1.45.201",
     "rke2-ingress-nginx": "4.14.303",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.001",
     "rke2-snapshot-controller-crd": "4.2.001",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.002",
     "rke2-traefik-crd": "39.0.002"
    },
    "components": {
     "Calico": "v3.31.3",
     "Canal": "Flannel v0.28.1 + Calico v3.31.3",
     "Cilium": "v1.19.1",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.14.1",
     "Etcd": "v3.5.26-k3s1",
     "Flannel": "v0.28.1",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.3-hardened3",
     "Kubernetes": "v1.32.13",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0",
     "Traefik": "v3.6.9"
    },
    "date": "2026-03-05",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.13+rke2r2": {
    "charts": {
     "rke2-calico": "v3.31.400",
     "rke2-calico-crd": "v3.31.400",
     "rke2-canal": "v3.31.4-build2026032700",
     "rke2-cilium": "1.19.101",
     "rke2-coredns": "1.45.205",
     "rke2-ingress-nginx": "4.14.504",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.002",
     "rke2-snapshot-controller-crd": "4.2.002",
     "rke2-traefik": "39.0.700",
     "rke2-traefik-crd": "39.0.700"
    },
    "components": {
     "Calico": "v3.31.4",
     "Canal": "Flannel v0.28.2 + Calico v3.31.4",
     "Cilium": "v1.19.1",
     "Containerd": "v2.2.2-k3s1",
     "CoreDNS": "v1.14.2",
     "Etcd": "v3.5.26-k3s1",
     "Flannel": "v0.28.2",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.32.13",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.1",
     "Traefik": "v3.6.12"
    },
    "date": "2026-05-27",
    "notes": [],
    "prime_only": True,
    "pulled": False
   },
   "v1.32.2+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.200",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.2-build2025021800",
     "rke2-cilium": "1.17.000",
     "rke2-coredns": "1.36.102",
     "rke2-ingress-nginx": "4.12.005",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.2",
     "Canal": "Flannel v0.26.4 + Calico v3.29.2",
     "Cilium": "v1.17.0",
     "Containerd": "v2.0.2-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.18-k3s1",
     "Flannel": "v0.26.4",
     "Helm-controller": "v0.16.6",
     "Ingress-Nginx": "v1.12.0-hardened6",
     "Kubernetes": "v1.32.2",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.1.4",
     "Runc": "v1.2.4"
    },
    "date": "2025-02-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.3+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.200",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.2-build2025030601",
     "rke2-cilium": "1.17.100",
     "rke2-coredns": "1.39.100",
     "rke2-ingress-nginx": "4.12.100",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.2",
     "Canal": "Flannel v0.26.5 + Calico v3.29.2",
     "Cilium": "v1.17.1",
     "Containerd": "v2.0.4-k3s2",
     "CoreDNS": "v1.12.0",
     "Etcd": "v3.5.19-k3s1",
     "Flannel": "v0.26.5",
     "Helm-controller": "v0.16.6",
     "Ingress-Nginx": "v1.12.1-hardened1",
     "Kubernetes": "v1.32.3",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.1.4",
     "Runc": "v1.2.5"
    },
    "date": "2025-03-26",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.4+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.300",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.3-build2025040801",
     "rke2-cilium": "1.17.300",
     "rke2-coredns": "1.39.201",
     "rke2-ingress-nginx": "4.12.101",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.3",
     "Canal": "Flannel v0.26.6 + Calico v3.29.3",
     "Cilium": "v1.17.3",
     "Containerd": "v2.0.4-k3s2",
     "CoreDNS": "v1.12.1",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.26.6",
     "Helm-controller": "v0.16.10",
     "Ingress-Nginx": "v1.12.1-hardened3",
     "Kubernetes": "v1.32.4",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.2.0",
     "Runc": "v1.2.5"
    },
    "date": "2025-05-01",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.5+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.001",
     "rke2-calico-crd": "v3.30.001",
     "rke2-canal": "v3.30.0-build2025051500",
     "rke2-cilium": "1.17.301",
     "rke2-coredns": "1.42.000",
     "rke2-ingress-nginx": "4.12.103",
     "rke2-metrics-server": "3.12.201",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.0",
     "Canal": "Flannel v0.26.7 + Calico v3.30.0",
     "Cilium": "v1.17.3",
     "Containerd": "v2.0.5-k3s1",
     "CoreDNS": "v1.12.1",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.26.7",
     "Helm-controller": "v0.16.10",
     "Ingress-Nginx": "v1.12.1-hardened6",
     "Kubernetes": "v1.32.5",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.2.0",
     "Runc": "v1.2.6"
    },
    "date": "2025-05-21",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.6+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.100",
     "rke2-calico-crd": "v3.30.100",
     "rke2-canal": "v3.30.1-build2025061101",
     "rke2-cilium": "1.17.401",
     "rke2-coredns": "1.42.302",
     "rke2-ingress-nginx": "4.12.201",
     "rke2-metrics-server": "3.12.202",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.1",
     "Canal": "Flannel v0.27.0 + Calico v3.30.1",
     "Cilium": "v1.17.4",
     "Containerd": "v2.0.5-k3s1",
     "CoreDNS": "v1.12.2",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.0",
     "Helm-controller": "v0.16.11",
     "Ingress-Nginx": "v1.12.2-hardened2",
     "Kubernetes": "v1.32.6",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.2.1",
     "Runc": "v1.2.6"
    },
    "date": "2025-06-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.7+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.100",
     "rke2-calico-crd": "v3.30.100",
     "rke2-canal": "v3.30.2-build2025071100",
     "rke2-cilium": "1.17.600",
     "rke2-coredns": "1.42.302",
     "rke2-ingress-nginx": "4.12.401",
     "rke2-metrics-server": "3.12.203",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.1",
     "Canal": "Flannel v0.27.1 + Calico v3.30.2",
     "Cilium": "v1.17.6",
     "Containerd": "v2.0.5-k3s2",
     "CoreDNS": "v1.12.2",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.1",
     "Helm-controller": "v0.16.13",
     "Ingress-Nginx": "v1.12.4-hardened2",
     "Kubernetes": "v1.32.7",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.1",
     "Runc": "v1.2.6"
    },
    "date": "2025-07-25",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.8+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.200",
     "rke2-calico-crd": "v3.30.200",
     "rke2-canal": "v3.30.2-build2025073100",
     "rke2-cilium": "1.18.000",
     "rke2-coredns": "1.43.101",
     "rke2-ingress-nginx": "4.12.404",
     "rke2-metrics-server": "3.13.000",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.2",
     "Canal": "Flannel v0.27.2 + Calico v3.30.2",
     "Cilium": "v1.18.0",
     "Containerd": "v2.0.5-k3s2",
     "CoreDNS": "v1.12.3",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.2",
     "Helm-controller": "v0.16.13",
     "Ingress-Nginx": "v1.12.4-hardened7",
     "Kubernetes": "v1.32.8",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.2",
     "Runc": "v1.2.6"
    },
    "date": "2025-08-23",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.32.9+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.300",
     "rke2-calico-crd": "v3.30.300",
     "rke2-canal": "v3.30.3-build2025090900",
     "rke2-cilium": "1.18.103",
     "rke2-coredns": "1.43.302",
     "rke2-ingress-nginx": "4.12.600",
     "rke2-metrics-server": "3.13.001",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.3",
     "Canal": "Flannel v0.27.3 + Calico v3.30.3",
     "Cilium": "v1.18.1",
     "Containerd": "v2.1.4-k3s2",
     "CoreDNS": "v1.12.3",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.3",
     "Helm-controller": "v0.16.13",
     "Ingress-Nginx": "v1.12.6-hardened1",
     "Kubernetes": "v1.32.9",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.2",
     "Runc": "v1.3.1"
    },
    "date": "2025-09-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.0+rke2r1": {
    "charts": {
     "rke2-calico": "v3.29.300",
     "rke2-calico-crd": "v3.29.101",
     "rke2-canal": "v3.29.3-build2025040801",
     "rke2-cilium": "1.17.300",
     "rke2-coredns": "1.39.201",
     "rke2-ingress-nginx": "4.12.101",
     "rke2-metrics-server": "3.12.200",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.29.3",
     "Canal": "Flannel v0.26.6 + Calico v3.29.3",
     "Cilium": "v1.17.3",
     "Containerd": "v2.0.4-k3s2",
     "CoreDNS": "v1.12.1",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.26.6",
     "Helm-controller": "v0.16.10",
     "Ingress-Nginx": "v1.12.1-hardened3",
     "Kubernetes": "v1.33.0",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.2.0",
     "Runc": "v1.2.5"
    },
    "date": "2025-05-07",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.1+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.001",
     "rke2-calico-crd": "v3.30.001",
     "rke2-canal": "v3.30.0-build2025051500",
     "rke2-cilium": "1.17.301",
     "rke2-coredns": "1.42.000",
     "rke2-ingress-nginx": "4.12.103",
     "rke2-metrics-server": "3.12.201",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.0",
     "Canal": "Flannel v0.26.7 + Calico v3.30.0",
     "Cilium": "v1.17.3",
     "Containerd": "v2.0.5-k3s1",
     "CoreDNS": "v1.12.1",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.26.7",
     "Helm-controller": "v0.16.10",
     "Ingress-Nginx": "v1.12.1-hardened6",
     "Kubernetes": "v1.33.1",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.2.0",
     "Runc": "v1.2.6"
    },
    "date": "2025-05-21",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.10+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.400",
     "rke2-calico-crd": "v3.31.400",
     "rke2-canal": "v3.31.4-build2026032700",
     "rke2-cilium": "1.19.101",
     "rke2-coredns": "1.45.205",
     "rke2-ingress-nginx": "4.14.501",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.002",
     "rke2-snapshot-controller-crd": "4.2.002",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.502",
     "rke2-traefik-crd": "39.0.502"
    },
    "components": {
     "Calico": "v3.31.4",
     "Canal": "Flannel v0.28.2 + Calico v3.31.4",
     "Cilium": "v1.19.1",
     "Containerd": "v2.2.2-k3s1",
     "CoreDNS": "v1.14.2",
     "Etcd": "v3.5.26-k3s1",
     "Flannel": "v0.28.2",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.5-hardened1",
     "Kubernetes": "v1.33.10",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.1",
     "Traefik": "v3.6.10"
    },
    "date": "2026-03-28",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.10+rke2r3": {
    "charts": {
     "rke2-calico": "v3.31.400",
     "rke2-calico-crd": "v3.31.400",
     "rke2-canal": "v3.31.4-build2026032700",
     "rke2-cilium": "1.19.101",
     "rke2-coredns": "1.45.205",
     "rke2-ingress-nginx": "4.14.503",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.002",
     "rke2-snapshot-controller-crd": "4.2.002",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.502",
     "rke2-traefik-crd": "39.0.502"
    },
    "components": {
     "Calico": "v3.31.4",
     "Canal": "Flannel v0.28.2 + Calico v3.31.4",
     "Cilium": "v1.19.1",
     "Containerd": "v2.2.2-k3s1",
     "CoreDNS": "v1.14.2",
     "Etcd": "v3.5.26-k3s1",
     "Flannel": "v0.28.2",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.5-hardened1",
     "Kubernetes": "v1.33.10",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.1",
     "Traefik": "v3.6.10"
    },
    "date": "2026-04-08",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.11+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.500",
     "rke2-calico-crd": "v3.31.500",
     "rke2-canal": "v3.31.5-build2026041500",
     "rke2-cilium": "1.19.300",
     "rke2-coredns": "1.45.209",
     "rke2-ingress-nginx": "4.14.504",
     "rke2-metrics-server": "3.13.008",
     "rke2-snapshot-controller": "4.2.003",
     "rke2-snapshot-controller-crd": "4.2.003",
     "rke2-traefik": "39.0.701",
     "rke2-traefik-crd": "39.0.701"
    },
    "components": {
     "Calico": "v3.31.5",
     "Canal": "Flannel v0.28.4 + Calico v3.31.5",
     "Cilium": "v1.19.3",
     "Containerd": "v2.2.3-k3s1",
     "CoreDNS": "v1.14.2",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.4",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.33.11",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.6.13"
    },
    "date": "2026-04-24",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.12+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.001",
     "rke2-calico-crd": "v3.32.001",
     "rke2-canal": "v3.32.0-build2026051100",
     "rke2-cilium": "1.19.303",
     "rke2-coredns": "1.45.212",
     "rke2-ingress-nginx": "4.14.508",
     "rke2-metrics-server": "3.13.011",
     "rke2-snapshot-controller": "4.2.005",
     "rke2-snapshot-controller-crd": "4.2.003",
     "rke2-traefik": "39.0.703",
     "rke2-traefik-crd": "39.0.702"
    },
    "components": {
     "Calico": "v3.32.0",
     "Canal": "Flannel v0.28.4 + Calico v3.32.0",
     "Cilium": "v1.19.3",
     "Containerd": "v2.2.3-k3s1",
     "CoreDNS": "v1.14.3",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.4",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.33.12",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.6.16"
    },
    "date": "2026-05-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.12+rke2r2": {
    "charts": {
     "rke2-calico": "v3.32.003",
     "rke2-calico-crd": "v3.32.003",
     "rke2-canal": "v3.32.0-build2026051100",
     "rke2-cilium": "1.19.303",
     "rke2-coredns": "1.45.212",
     "rke2-ingress-nginx": "4.14.509",
     "rke2-metrics-server": "3.13.011",
     "rke2-snapshot-controller": "4.2.005",
     "rke2-snapshot-controller-crd": "4.2.003",
     "rke2-traefik": "39.0.703",
     "rke2-traefik-crd": "39.0.702"
    },
    "components": {
     "Calico": "v3.32.0",
     "Canal": "Flannel v0.28.4 + Calico v3.32.0",
     "Cilium": "v1.19.3",
     "Containerd": "v2.2.3-k3s1",
     "CoreDNS": "v1.14.3",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.4",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.33.12",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.6.16"
    },
    "date": "2026-05-28",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.13+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.003",
     "rke2-calico-crd": "v3.32.003",
     "rke2-canal": "v3.32.0-build2026060401",
     "rke2-cilium": "1.19.402",
     "rke2-coredns": "1.46.002",
     "rke2-ingress-nginx": "4.15.101",
     "rke2-metrics-server": "3.13.100",
     "rke2-multus": "v4.2.418",
     "rke2-snapshot-controller": "4.2.006",
     "rke2-snapshot-controller-crd": "4.2.006",
     "rke2-traefik": "40.1.003",
     "rke2-traefik-crd": "40.1.003"
    },
    "components": {
     "Calico": "v3.32.0",
     "Canal": "Flannel v0.28.5 + Calico v3.32.0",
     "Cilium": "v1.19.4",
     "Containerd": "v2.2.5-k3s1",
     "CoreDNS": "v1.14.4",
     "Etcd": "v3.6.12-k3s1",
     "Flannel": "v0.28.5",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.33.13",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.7.4"
    },
    "date": "2026-06-25",
    "notes": [
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.13+rke2r2": {
    "charts": {
     "rke2-calico": "v3.32.100",
     "rke2-calico-crd": "v3.32.100",
     "rke2-canal": "v3.32.1-build2026072200",
     "rke2-cilium": "1.19.601",
     "rke2-coredns": "1.46.201",
     "rke2-ingress-nginx": "4.15.107",
     "rke2-metrics-server": "3.13.105",
     "rke2-multus": "v4.3.008",
     "rke2-snapshot-controller": "4.2.008",
     "rke2-snapshot-controller-crd": "4.2.008",
     "rke2-traefik": "40.1.009",
     "rke2-traefik-crd": "40.1.009"
    },
    "components": {
     "Calico": "v3.32.1",
     "Canal": "Flannel v0.28.8 + Calico v3.32.1",
     "Cilium": "v1.19.6",
     "Containerd": "v2.2.6-k3s1",
     "CoreDNS": "v1.14.6",
     "Etcd": "v3.6.14-k3s1",
     "Flannel": "v0.28.8",
     "Helm-controller": "v0.16.26",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.33.13",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.0",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.8"
    },
    "date": "2026-08-04",
    "notes": [
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.13+rke2r3": {
    "charts": {
     "rke2-calico": "v3.32.100",
     "rke2-calico-crd": "v3.32.100",
     "rke2-canal": "v3.32.1-build2026072200",
     "rke2-cilium": "1.19.601",
     "rke2-coredns": "1.46.201",
     "rke2-ingress-nginx": "4.15.107",
     "rke2-metrics-server": "3.13.105",
     "rke2-multus": "v4.3.008",
     "rke2-snapshot-controller": "4.2.008",
     "rke2-snapshot-controller-crd": "4.2.008",
     "rke2-traefik": "40.1.009",
     "rke2-traefik-crd": "40.1.009"
    },
    "components": {
     "Calico": "v3.32.1",
     "Canal": "Flannel v0.28.8 + Calico v3.32.1",
     "Cilium": "v1.19.6",
     "Containerd": "v2.2.6-k3s1",
     "CoreDNS": "v1.14.6",
     "Etcd": "v3.6.14-k3s3",
     "Flannel": "v0.28.8",
     "Helm-controller": "v0.16.27",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.33.13",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.0",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.8"
    },
    "date": "2026-10-02",
    "notes": [],
    "prime_only": True,
    "pulled": False
   },
   "v1.33.2+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.100",
     "rke2-calico-crd": "v3.30.100",
     "rke2-canal": "v3.30.1-build2025061101",
     "rke2-cilium": "1.17.401",
     "rke2-coredns": "1.42.302",
     "rke2-ingress-nginx": "4.12.201",
     "rke2-metrics-server": "3.12.202",
     "rke2-snapshot-controller": "4.0.002",
     "rke2-snapshot-controller-crd": "4.0.002",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.1",
     "Canal": "Flannel v0.27.0 + Calico v3.30.1",
     "Cilium": "v1.17.4",
     "Containerd": "v2.0.5-k3s1",
     "CoreDNS": "v1.12.2",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.0",
     "Helm-controller": "v0.16.11",
     "Ingress-Nginx": "v1.12.2-hardened2",
     "Kubernetes": "v1.33.2",
     "Metrics-server": "v0.7.2",
     "Multus": "v4.2.1",
     "Runc": "v1.2.6"
    },
    "date": "2025-06-27",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.3+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.100",
     "rke2-calico-crd": "v3.30.100",
     "rke2-canal": "v3.30.2-build2025071100",
     "rke2-cilium": "1.17.600",
     "rke2-coredns": "1.42.302",
     "rke2-ingress-nginx": "4.12.401",
     "rke2-metrics-server": "3.12.203",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.1",
     "Canal": "Flannel v0.27.1 + Calico v3.30.2",
     "Cilium": "v1.17.6",
     "Containerd": "v2.0.5-k3s2",
     "CoreDNS": "v1.12.2",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.1",
     "Helm-controller": "v0.16.13",
     "Ingress-Nginx": "v1.12.4-hardened2",
     "Kubernetes": "v1.33.3",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.1",
     "Runc": "v1.2.6"
    },
    "date": "2025-07-25",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.4+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.200",
     "rke2-calico-crd": "v3.30.200",
     "rke2-canal": "v3.30.2-build2025073100",
     "rke2-cilium": "1.18.000",
     "rke2-coredns": "1.43.101",
     "rke2-ingress-nginx": "4.12.404",
     "rke2-metrics-server": "3.13.000",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.2",
     "Canal": "Flannel v0.27.2 + Calico v3.30.2",
     "Cilium": "v1.18.0",
     "Containerd": "v2.0.5-k3s2",
     "CoreDNS": "v1.12.3",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.2",
     "Helm-controller": "v0.16.13",
     "Ingress-Nginx": "v1.12.4-hardened7",
     "Kubernetes": "v1.33.4",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.2",
     "Runc": "v1.2.6"
    },
    "date": "2025-08-23",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.5+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.300",
     "rke2-calico-crd": "v3.30.300",
     "rke2-canal": "v3.30.3-build2025090900",
     "rke2-cilium": "1.18.103",
     "rke2-coredns": "1.43.302",
     "rke2-ingress-nginx": "4.12.600",
     "rke2-metrics-server": "3.13.001",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.3",
     "Canal": "Flannel v0.27.3 + Calico v3.30.3",
     "Cilium": "v1.18.1",
     "Containerd": "v2.1.4-k3s2",
     "CoreDNS": "v1.12.3",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.3",
     "Helm-controller": "v0.16.13",
     "Ingress-Nginx": "v1.12.6-hardened1",
     "Kubernetes": "v1.33.5",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.2",
     "Runc": "v1.3.1"
    },
    "date": "2025-09-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.6+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.401",
     "rke2-calico-crd": "v3.30.401",
     "rke2-canal": "v3.30.3-build2025101500",
     "rke2-cilium": "1.18.300",
     "rke2-coredns": "1.44.300",
     "rke2-ingress-nginx": "4.13.400",
     "rke2-metrics-server": "3.13.002",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.4",
     "Canal": "Flannel v0.27.4 + Calico v3.30.3",
     "Cilium": "v1.18.3",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.13.1",
     "Etcd": "v3.5.21-k3s1",
     "Flannel": "v0.27.4",
     "Helm-controller": "v0.16.16",
     "Ingress-Nginx": "v1.13.4-hardened1",
     "Kubernetes": "v1.33.6",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.3",
     "Runc": "v1.3.3"
    },
    "date": "2025-11-20",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.7+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.200",
     "rke2-calico-crd": "v3.31.200",
     "rke2-canal": "v3.31.2-build2025120500",
     "rke2-cilium": "1.18.401",
     "rke2-coredns": "1.45.003",
     "rke2-ingress-nginx": "4.13.500",
     "rke2-metrics-server": "3.13.004",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.31.2",
     "Canal": "Flannel v0.27.4 + Calico v3.31.2",
     "Cilium": "v1.18.4",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.13.1",
     "Etcd": "v3.5.25-k3s1",
     "Flannel": "v0.27.4",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.13.5-hardened2",
     "Kubernetes": "v1.33.7",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0"
    },
    "date": "2025-12-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.7+rke2r3": {
    "charts": {
     "rke2-calico": "v3.31.300",
     "rke2-calico-crd": "v3.31.300",
     "rke2-canal": "v3.31.3-build2026011900",
     "rke2-cilium": "1.18.601",
     "rke2-coredns": "1.45.008",
     "rke2-ingress-nginx": "4.14.301",
     "rke2-metrics-server": "3.13.006",
     "rke2-snapshot-controller": "4.2.000",
     "rke2-snapshot-controller-crd": "4.2.000",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "38.0.201",
     "rke2-traefik-crd": "38.0.201"
    },
    "components": {
     "Calico": "v3.31.3",
     "Canal": "Flannel v0.28.0 + Calico v3.31.3",
     "Cilium": "v1.18.6",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.14.1",
     "Etcd": "v3.5.26-k3s1",
     "Flannel": "v0.28.0",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.3-hardened1",
     "Kubernetes": "v1.33.7",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0",
     "Traefik": "v3.6.7"
    },
    "date": "2026-02-04",
    "notes": [
     "This warning targets users who perform upgrades by adding new nodes to the cluster, and removing old ones. If your etcd cluster membership is and has been consistent across versions, you should NOT be affected by this issue.",
     "RKE2 v1.34 and higher include etcd 3.6. Maintainers of the etcd project have indicated that there no safe path from etcd 3.5 to 3.6 except by upgrading to v3.5.26 first.",
     "In mid December, the project released an announcement indicating that there is NO safe path from etcd 3.5 to 3.6 except by upgrading to v3.5.26 first. Failure to do so can cause the cluster to report “zombie members” (etcd nodes that were removed from the cluster some time ago) re-appearing and joining database consensus, ultimately causing the cluster to lose quorum. This updated blog post contradicts previous announcements on this topic, which indicated that it was safe to upgrade from v3.5.20+ as long as nodes had been restarted at least once, to reconcile membership lists across internal s",
     "The January releases of RKE2 v1.32 and v1.33 will include etcd v3.5.26. All users should plan on upgrading to this patch release, prior to upgrading to v1.34 and v1.35."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.8+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.300",
     "rke2-calico-crd": "v3.31.300",
     "rke2-canal": "v3.31.3-build2026020600",
     "rke2-cilium": "1.19.001",
     "rke2-coredns": "1.45.201",
     "rke2-ingress-nginx": "4.14.302",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.001",
     "rke2-snapshot-controller-crd": "4.2.001",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.000",
     "rke2-traefik-crd": "39.0.000"
    },
    "components": {
     "Calico": "v3.31.3",
     "Canal": "Flannel v0.28.1 + Calico v3.31.3",
     "Cilium": "v1.19.0",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.14.1",
     "Etcd": "v3.5.26-k3s1",
     "Flannel": "v0.28.1",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.3-hardened2",
     "Kubernetes": "v1.33.8",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0",
     "Traefik": "v3.6.7"
    },
    "date": "2026-02-13",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.33.9+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.300",
     "rke2-calico-crd": "v3.31.300",
     "rke2-canal": "v3.31.3-build2026020600",
     "rke2-cilium": "1.19.100",
     "rke2-coredns": "1.45.201",
     "rke2-ingress-nginx": "4.14.303",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.001",
     "rke2-snapshot-controller-crd": "4.2.001",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.002",
     "rke2-traefik-crd": "39.0.002"
    },
    "components": {
     "Calico": "v3.31.3",
     "Canal": "Flannel v0.28.1 + Calico v3.31.3",
     "Cilium": "v1.19.1",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.14.1",
     "Etcd": "v3.5.26-k3s1",
     "Flannel": "v0.28.1",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.3-hardened3",
     "Kubernetes": "v1.33.9",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0",
     "Traefik": "v3.6.9"
    },
    "date": "2026-03-05",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.1+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.300",
     "rke2-calico-crd": "v3.30.300",
     "rke2-canal": "v3.30.3-build2025090900",
     "rke2-cilium": "1.18.103",
     "rke2-coredns": "1.43.302",
     "rke2-ingress-nginx": "4.12.600",
     "rke2-metrics-server": "3.13.001",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.3",
     "Canal": "Flannel v0.27.3 + Calico v3.30.3",
     "Cilium": "v1.18.1",
     "Containerd": "v2.1.4-k3s2",
     "CoreDNS": "v1.12.3",
     "Etcd": "v3.6.4-k3s3",
     "Flannel": "v0.27.3",
     "Helm-controller": "v0.16.13",
     "Ingress-Nginx": "v1.12.6-hardened1",
     "Kubernetes": "v1.34.1",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.2",
     "Runc": "v1.3.1"
    },
    "date": "2025-09-17",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.10+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.100",
     "rke2-calico-crd": "v3.32.100",
     "rke2-canal": "v3.32.1-build2026072200",
     "rke2-cilium": "1.19.601",
     "rke2-coredns": "1.46.201",
     "rke2-ingress-nginx": "4.15.107",
     "rke2-metrics-server": "3.13.105",
     "rke2-multus": "v4.3.008",
     "rke2-snapshot-controller": "4.2.008",
     "rke2-snapshot-controller-crd": "4.2.008",
     "rke2-traefik": "40.1.009",
     "rke2-traefik-crd": "40.1.009"
    },
    "components": {
     "Calico": "v3.32.1",
     "Canal": "Flannel v0.28.8 + Calico v3.32.1",
     "Cilium": "v1.19.6",
     "Containerd": "v2.2.6-k3s1",
     "CoreDNS": "v1.14.6",
     "Etcd": "v3.6.14-k3s1",
     "Flannel": "v0.28.8",
     "Helm-controller": "v0.16.26",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.34.10",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.0",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.8"
    },
    "date": "2026-08-04",
    "notes": [
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.11+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.100",
     "rke2-calico-crd": "v3.32.100",
     "rke2-canal": "v3.32.1-build2026082700",
     "rke2-cilium": "1.19.601",
     "rke2-coredns": "1.47.003",
     "rke2-ingress-nginx": "4.15.109",
     "rke2-metrics-server": "3.14.000",
     "rke2-multus": "v4.3.008",
     "rke2-snapshot-controller": "5.2.003",
     "rke2-snapshot-controller-crd": "5.2.003",
     "rke2-traefik": "40.1.010",
     "rke2-traefik-crd": "40.1.010"
    },
    "components": {
     "Calico": "v3.32.1",
     "Canal": "Flannel v0.28.9 + Calico v3.32.1",
     "Cilium": "v1.19.6",
     "Containerd": "v2.2.7-k3s1",
     "CoreDNS": "v1.14.7",
     "Etcd": "v3.6.14-k3s1",
     "Flannel": "v0.28.9",
     "Helm-controller": "v0.16.26",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.34.11",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.0",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.11"
    },
    "date": "2026-08-28",
    "notes": [
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.12+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.200",
     "rke2-calico-crd": "v3.32.200",
     "rke2-canal": "v3.32.2-build2026090900",
     "rke2-cilium": "1.20.200",
     "rke2-coredns": "1.47.102",
     "rke2-ingress-nginx": "4.15.110",
     "rke2-metrics-server": "3.14.001",
     "rke2-multus": "v4.3.102",
     "rke2-snapshot-controller": "5.2.004",
     "rke2-snapshot-controller-crd": "5.2.004",
     "rke2-traefik": "40.1.013",
     "rke2-traefik-crd": "40.1.013"
    },
    "components": {
     "Calico": "v3.32.2",
     "Canal": "Flannel v0.28.9 + Calico v3.32.2",
     "Cilium": "v1.20.2",
     "Containerd": "v2.2.7-k3s1",
     "CoreDNS": "v1.14.7",
     "Etcd": "v3.6.14-k3s3",
     "Flannel": "v0.28.9",
     "Helm-controller": "v0.16.27",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.34.12",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.1",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.13"
    },
    "date": "2026-09-30",
    "notes": [
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.13+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.200",
     "rke2-calico-crd": "v3.32.200",
     "rke2-canal": "v3.32.2-build2026102200",
     "rke2-cilium": "1.20.400",
     "rke2-coredns": "1.49.002",
     "rke2-ingress-nginx": "4.15.115",
     "rke2-metrics-server": "3.14.004",
     "rke2-multus": "v4.3.118",
     "rke2-snapshot-controller": "5.4.001",
     "rke2-snapshot-controller-crd": "5.4.001",
     "rke2-traefik": "40.1.022",
     "rke2-traefik-crd": "40.1.022"
    },
    "components": {
     "Calico": "v3.32.2",
     "Canal": "Flannel v0.28.10 + Calico v3.32.2",
     "Cilium": "v1.20.4",
     "Containerd": "v2.2.10-k3s1",
     "CoreDNS": "v1.14.7",
     "Etcd": "v3.6.14-k3s3",
     "Flannel": "v0.28.10",
     "Helm-controller": "v0.16.27",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.34.13",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.1",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.16"
    },
    "date": "2026-11-05",
    "notes": [
     "This release upgrades Traefik chart to v40.x which includes a breaking change for the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.2+rke2r1": {
    "charts": {
     "rke2-calico": "v3.30.401",
     "rke2-calico-crd": "v3.30.401",
     "rke2-canal": "v3.30.3-build2025101500",
     "rke2-cilium": "1.18.300",
     "rke2-coredns": "1.44.300",
     "rke2-ingress-nginx": "4.13.400",
     "rke2-metrics-server": "3.13.002",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.30.4",
     "Canal": "Flannel v0.27.4 + Calico v3.30.3",
     "Cilium": "v1.18.3",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.13.1",
     "Etcd": "v3.6.5-k3s1",
     "Flannel": "v0.27.4",
     "Helm-controller": "v0.16.16",
     "Ingress-Nginx": "v1.13.4-hardened1",
     "Kubernetes": "v1.34.2",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.3",
     "Runc": "v1.3.3"
    },
    "date": "2025-11-20",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.3+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.200",
     "rke2-calico-crd": "v3.31.200",
     "rke2-canal": "v3.31.2-build2025120500",
     "rke2-cilium": "1.18.401",
     "rke2-coredns": "1.45.003",
     "rke2-ingress-nginx": "4.13.500",
     "rke2-metrics-server": "3.13.004",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0"
    },
    "components": {
     "Calico": "v3.31.2",
     "Canal": "Flannel v0.27.4 + Calico v3.31.2",
     "Cilium": "v1.18.4",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.13.1",
     "Etcd": "v3.6.6-k3s1",
     "Flannel": "v0.27.4",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.13.5-hardened2",
     "Kubernetes": "v1.34.3",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0"
    },
    "date": "2025-12-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.3+rke2r3": {
    "charts": {
     "rke2-calico": "v3.31.300",
     "rke2-calico-crd": "v3.31.300",
     "rke2-canal": "v3.31.3-build2026011900",
     "rke2-cilium": "1.18.601",
     "rke2-coredns": "1.45.008",
     "rke2-ingress-nginx": "4.14.301",
     "rke2-metrics-server": "3.13.006",
     "rke2-snapshot-controller": "4.2.000",
     "rke2-snapshot-controller-crd": "4.2.000",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "38.0.201",
     "rke2-traefik-crd": "38.0.201"
    },
    "components": {
     "Calico": "v3.31.3",
     "Canal": "Flannel v0.28.0 + Calico v3.31.3",
     "Cilium": "v1.18.6",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.14.1",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.0",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.3-hardened1",
     "Kubernetes": "v1.34.3",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0",
     "Traefik": "v3.6.7"
    },
    "date": "2026-02-04",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.4+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.300",
     "rke2-calico-crd": "v3.31.300",
     "rke2-canal": "v3.31.3-build2026020600",
     "rke2-cilium": "1.19.001",
     "rke2-coredns": "1.45.201",
     "rke2-ingress-nginx": "4.14.302",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.001",
     "rke2-snapshot-controller-crd": "4.2.001",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.000",
     "rke2-traefik-crd": "39.0.000"
    },
    "components": {
     "Calico": "v3.31.3",
     "Canal": "Flannel v0.28.1 + Calico v3.31.3",
     "Cilium": "v1.19.0",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.14.1",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.1",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.3-hardened2",
     "Kubernetes": "v1.34.4",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0",
     "Traefik": "v3.6.7"
    },
    "date": "2026-02-13",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.5+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.300",
     "rke2-calico-crd": "v3.31.300",
     "rke2-canal": "v3.31.3-build2026020600",
     "rke2-cilium": "1.19.100",
     "rke2-coredns": "1.45.201",
     "rke2-ingress-nginx": "4.14.303",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.001",
     "rke2-snapshot-controller-crd": "4.2.001",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.002",
     "rke2-traefik-crd": "39.0.002"
    },
    "components": {
     "Calico": "v3.31.3",
     "Canal": "Flannel v0.28.1 + Calico v3.31.3",
     "Cilium": "v1.19.1",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.14.1",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.1",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.3-hardened3",
     "Kubernetes": "v1.34.5",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0",
     "Traefik": "v3.6.9"
    },
    "date": "2026-03-05",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.6+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.400",
     "rke2-calico-crd": "v3.31.400",
     "rke2-canal": "v3.31.4-build2026032700",
     "rke2-cilium": "1.19.101",
     "rke2-coredns": "1.45.205",
     "rke2-ingress-nginx": "4.14.501",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.002",
     "rke2-snapshot-controller-crd": "4.2.002",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.502",
     "rke2-traefik-crd": "39.0.502"
    },
    "components": {
     "Calico": "v3.31.4",
     "Canal": "Flannel v0.28.2 + Calico v3.31.4",
     "Cilium": "v1.19.1",
     "Containerd": "v2.2.2-k3s1",
     "CoreDNS": "v1.14.2",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.2",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.5-hardened1",
     "Kubernetes": "v1.34.6",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.1",
     "Traefik": "v3.6.10"
    },
    "date": "2026-03-28",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.6+rke2r3": {
    "charts": {
     "rke2-calico": "v3.31.400",
     "rke2-calico-crd": "v3.31.400",
     "rke2-canal": "v3.31.4-build2026032700",
     "rke2-cilium": "1.19.101",
     "rke2-coredns": "1.45.205",
     "rke2-ingress-nginx": "4.14.503",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.002",
     "rke2-snapshot-controller-crd": "4.2.002",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.502",
     "rke2-traefik-crd": "39.0.502"
    },
    "components": {
     "Calico": "v3.31.4",
     "Canal": "Flannel v0.28.2 + Calico v3.31.4",
     "Cilium": "v1.19.1",
     "Containerd": "v2.2.2-k3s1",
     "CoreDNS": "v1.14.2",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.2",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.5-hardened1",
     "Kubernetes": "v1.34.6",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.1",
     "Traefik": "v3.6.10"
    },
    "date": "2026-04-08",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.7+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.500",
     "rke2-calico-crd": "v3.31.500",
     "rke2-canal": "v3.31.5-build2026041500",
     "rke2-cilium": "1.19.300",
     "rke2-coredns": "1.45.209",
     "rke2-ingress-nginx": "4.14.504",
     "rke2-metrics-server": "3.13.008",
     "rke2-snapshot-controller": "4.2.003",
     "rke2-snapshot-controller-crd": "4.2.003",
     "rke2-traefik": "39.0.701",
     "rke2-traefik-crd": "39.0.701"
    },
    "components": {
     "Calico": "v3.31.5",
     "Canal": "Flannel v0.28.4 + Calico v3.31.5",
     "Cilium": "v1.19.3",
     "Containerd": "v2.2.3-k3s1",
     "CoreDNS": "v1.14.2",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.4",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.34.7",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.6.13"
    },
    "date": "2026-04-24",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.8+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.001",
     "rke2-calico-crd": "v3.32.001",
     "rke2-canal": "v3.32.0-build2026051100",
     "rke2-cilium": "1.19.303",
     "rke2-coredns": "1.45.212",
     "rke2-ingress-nginx": "4.14.508",
     "rke2-metrics-server": "3.13.011",
     "rke2-snapshot-controller": "4.2.005",
     "rke2-snapshot-controller-crd": "4.2.003",
     "rke2-traefik": "39.0.703",
     "rke2-traefik-crd": "39.0.702"
    },
    "components": {
     "Calico": "v3.32.0",
     "Canal": "Flannel v0.28.4 + Calico v3.32.0",
     "Cilium": "v1.19.3",
     "Containerd": "v2.2.3-k3s1",
     "CoreDNS": "v1.14.3",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.4",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.34.8",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.6.16"
    },
    "date": "2026-05-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.8+rke2r2": {
    "charts": {
     "rke2-calico": "v3.32.003",
     "rke2-calico-crd": "v3.32.003",
     "rke2-canal": "v3.32.0-build2026051100",
     "rke2-cilium": "1.19.303",
     "rke2-coredns": "1.45.212",
     "rke2-ingress-nginx": "4.14.509",
     "rke2-metrics-server": "3.13.011",
     "rke2-snapshot-controller": "4.2.005",
     "rke2-snapshot-controller-crd": "4.2.003",
     "rke2-traefik": "39.0.703",
     "rke2-traefik-crd": "39.0.702"
    },
    "components": {
     "Calico": "v3.32.0",
     "Canal": "Flannel v0.28.4 + Calico v3.32.0",
     "Cilium": "v1.19.3",
     "Containerd": "v2.2.3-k3s1",
     "CoreDNS": "v1.14.3",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.4",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.34.8",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.6.16"
    },
    "date": "2026-05-28",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.34.9+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.003",
     "rke2-calico-crd": "v3.32.003",
     "rke2-canal": "v3.32.0-build2026060401",
     "rke2-cilium": "1.19.402",
     "rke2-coredns": "1.46.002",
     "rke2-ingress-nginx": "4.15.101",
     "rke2-metrics-server": "3.13.100",
     "rke2-multus": "v4.2.418",
     "rke2-snapshot-controller": "4.2.006",
     "rke2-snapshot-controller-crd": "4.2.006",
     "rke2-traefik": "40.1.003",
     "rke2-traefik-crd": "40.1.003"
    },
    "components": {
     "Calico": "v3.32.0",
     "Canal": "Flannel v0.28.5 + Calico v3.32.0",
     "Cilium": "v1.19.4",
     "Containerd": "v2.2.5-k3s2",
     "CoreDNS": "v1.14.4",
     "Etcd": "v3.6.12-k3s1",
     "Flannel": "v0.28.5",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.34.9",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.7.4"
    },
    "date": "2026-06-25",
    "notes": [
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.0+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.200",
     "rke2-calico-crd": "v3.31.200",
     "rke2-canal": "v3.31.2-build2025120500",
     "rke2-cilium": "1.18.401",
     "rke2-coredns": "1.45.003",
     "rke2-ingress-nginx": "4.13.500",
     "rke2-metrics-server": "3.13.004",
     "rke2-snapshot-controller": "4.0.003",
     "rke2-snapshot-controller-crd": "4.0.003",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "37.4.001",
     "rke2-traefik-crd": "37.4.001"
    },
    "components": {
     "Calico": "v3.31.2",
     "Canal": "Flannel v0.27.4 + Calico v3.31.2",
     "Cilium": "v1.18.4",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.13.1",
     "Etcd": "v3.6.6-k3s1",
     "Flannel": "v0.27.4",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.13.5-hardened2",
     "Kubernetes": "v1.35.0",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0",
     "Traefik": "v3.6.4"
    },
    "date": "2025-12-30",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.0+rke2r3": {
    "charts": {
     "rke2-calico": "v3.31.300",
     "rke2-calico-crd": "v3.31.300",
     "rke2-canal": "v3.31.3-build2026011900",
     "rke2-cilium": "1.18.601",
     "rke2-coredns": "1.45.008",
     "rke2-ingress-nginx": "4.14.301",
     "rke2-metrics-server": "3.13.006",
     "rke2-snapshot-controller": "4.2.000",
     "rke2-snapshot-controller-crd": "4.2.000",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "38.0.201",
     "rke2-traefik-crd": "38.0.201"
    },
    "components": {
     "Calico": "v3.31.3",
     "Canal": "Flannel v0.28.0 + Calico v3.31.3",
     "Cilium": "v1.18.6",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.14.1",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.0",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.3-hardened1",
     "Kubernetes": "v1.35.0",
     "Metrics-server": "v0.8.0",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0",
     "Traefik": "v3.6.7"
    },
    "date": "2026-02-04",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.1+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.300",
     "rke2-calico-crd": "v3.31.300",
     "rke2-canal": "v3.31.3-build2026020600",
     "rke2-cilium": "1.19.001",
     "rke2-coredns": "1.45.201",
     "rke2-ingress-nginx": "4.14.302",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.001",
     "rke2-snapshot-controller-crd": "4.2.001",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.000",
     "rke2-traefik-crd": "39.0.000"
    },
    "components": {
     "Calico": "v3.31.3",
     "Canal": "Flannel v0.28.1 + Calico v3.31.3",
     "Cilium": "v1.19.0",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.14.1",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.1",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.3-hardened2",
     "Kubernetes": "v1.35.1",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0",
     "Traefik": "v3.6.7"
    },
    "date": "2026-02-13",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.10+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.200",
     "rke2-calico-crd": "v3.32.200",
     "rke2-canal": "v3.32.2-build2026102200",
     "rke2-cilium": "1.20.400",
     "rke2-coredns": "1.49.002",
     "rke2-ingress-nginx": "4.15.115",
     "rke2-metrics-server": "3.14.004",
     "rke2-multus": "v4.3.118",
     "rke2-snapshot-controller": "5.4.001",
     "rke2-snapshot-controller-crd": "5.4.001",
     "rke2-traefik": "40.1.022",
     "rke2-traefik-crd": "40.1.022"
    },
    "components": {
     "Calico": "v3.32.2",
     "Canal": "Flannel v0.28.10 + Calico v3.32.2",
     "Cilium": "v1.20.4",
     "Containerd": "v2.2.10-k3s1",
     "CoreDNS": "v1.14.7",
     "Etcd": "v3.6.14-k3s3",
     "Flannel": "v0.28.10",
     "Helm-controller": "v0.17.9",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.35.10",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.1",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.16"
    },
    "date": "2026-11-05",
    "notes": [
     "This release upgrades Traefik chart to v40.x which includes a breaking change for the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.2+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.300",
     "rke2-calico-crd": "v3.31.300",
     "rke2-canal": "v3.31.3-build2026020600",
     "rke2-cilium": "1.19.100",
     "rke2-coredns": "1.45.201",
     "rke2-ingress-nginx": "4.14.303",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.001",
     "rke2-snapshot-controller-crd": "4.2.001",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.002",
     "rke2-traefik-crd": "39.0.002"
    },
    "components": {
     "Calico": "v3.31.3",
     "Canal": "Flannel v0.28.1 + Calico v3.31.3",
     "Cilium": "v1.19.1",
     "Containerd": "v2.1.5-k3s1",
     "CoreDNS": "v1.14.1",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.1",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.3-hardened3",
     "Kubernetes": "v1.35.2",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.3",
     "Runc": "v1.4.0",
     "Traefik": "v3.6.9"
    },
    "date": "2026-03-05",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.3+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.400",
     "rke2-calico-crd": "v3.31.400",
     "rke2-canal": "v3.31.4-build2026032700",
     "rke2-cilium": "1.19.101",
     "rke2-coredns": "1.45.205",
     "rke2-ingress-nginx": "4.14.501",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.002",
     "rke2-snapshot-controller-crd": "4.2.002",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.502",
     "rke2-traefik-crd": "39.0.502"
    },
    "components": {
     "Calico": "v3.31.4",
     "Canal": "Flannel v0.28.2 + Calico v3.31.4",
     "Cilium": "v1.19.1",
     "Containerd": "v2.2.2-k3s1",
     "CoreDNS": "v1.14.2",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.2",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.5-hardened1",
     "Kubernetes": "v1.35.3",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.1",
     "Traefik": "v3.6.10"
    },
    "date": "2026-03-28",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.3+rke2r3": {
    "charts": {
     "rke2-calico": "v3.31.400",
     "rke2-calico-crd": "v3.31.400",
     "rke2-canal": "v3.31.4-build2026032700",
     "rke2-cilium": "1.19.101",
     "rke2-coredns": "1.45.205",
     "rke2-ingress-nginx": "4.14.503",
     "rke2-metrics-server": "3.13.007",
     "rke2-snapshot-controller": "4.2.002",
     "rke2-snapshot-controller-crd": "4.2.002",
     "rke2-snapshot-validation-webhook": "0.0.0",
     "rke2-traefik": "39.0.502",
     "rke2-traefik-crd": "39.0.502"
    },
    "components": {
     "Calico": "v3.31.4",
     "Canal": "Flannel v0.28.2 + Calico v3.31.4",
     "Cilium": "v1.19.1",
     "Containerd": "v2.2.2-k3s1",
     "CoreDNS": "v1.14.2",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.2",
     "Helm-controller": "v0.16.17",
     "Ingress-Nginx": "v1.14.5-hardened1",
     "Kubernetes": "v1.35.3",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.1",
     "Traefik": "v3.6.10"
    },
    "date": "2026-04-08",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.4+rke2r1": {
    "charts": {
     "rke2-calico": "v3.31.500",
     "rke2-calico-crd": "v3.31.500",
     "rke2-canal": "v3.31.5-build2026041500",
     "rke2-cilium": "1.19.300",
     "rke2-coredns": "1.45.209",
     "rke2-ingress-nginx": "4.14.504",
     "rke2-metrics-server": "3.13.008",
     "rke2-snapshot-controller": "4.2.003",
     "rke2-snapshot-controller-crd": "4.2.003",
     "rke2-traefik": "39.0.701",
     "rke2-traefik-crd": "39.0.701"
    },
    "components": {
     "Calico": "v3.31.5",
     "Canal": "Flannel v0.28.4 + Calico v3.31.5",
     "Cilium": "v1.19.3",
     "Containerd": "v2.2.3-k3s1",
     "CoreDNS": "v1.14.2",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.4",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.35.4",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.6.13"
    },
    "date": "2026-04-24",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.5+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.001",
     "rke2-calico-crd": "v3.32.001",
     "rke2-canal": "v3.32.0-build2026051100",
     "rke2-cilium": "1.19.303",
     "rke2-coredns": "1.45.212",
     "rke2-ingress-nginx": "4.14.508",
     "rke2-metrics-server": "3.13.011",
     "rke2-snapshot-controller": "4.2.005",
     "rke2-snapshot-controller-crd": "4.2.003",
     "rke2-traefik": "39.0.703",
     "rke2-traefik-crd": "39.0.702"
    },
    "components": {
     "Calico": "v3.32.0",
     "Canal": "Flannel v0.28.4 + Calico v3.32.0",
     "Cilium": "v1.19.3",
     "Containerd": "v2.2.3-k3s1",
     "CoreDNS": "v1.14.3",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.4",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.35.5",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.6.16"
    },
    "date": "2026-05-18",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.5+rke2r2": {
    "charts": {
     "rke2-calico": "v3.32.003",
     "rke2-calico-crd": "v3.32.003",
     "rke2-canal": "v3.32.0-build2026051100",
     "rke2-cilium": "1.19.303",
     "rke2-coredns": "1.45.212",
     "rke2-ingress-nginx": "4.14.509",
     "rke2-metrics-server": "3.13.011",
     "rke2-snapshot-controller": "4.2.005",
     "rke2-snapshot-controller-crd": "4.2.003",
     "rke2-traefik": "39.0.703",
     "rke2-traefik-crd": "39.0.702"
    },
    "components": {
     "Calico": "v3.32.0",
     "Canal": "Flannel v0.28.4 + Calico v3.32.0",
     "Cilium": "v1.19.3",
     "Containerd": "v2.2.3-k3s1",
     "CoreDNS": "v1.14.3",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.4",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.35.5",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.6.16"
    },
    "date": "2026-05-29",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.6+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.003",
     "rke2-calico-crd": "v3.32.003",
     "rke2-canal": "v3.32.0-build2026060401",
     "rke2-cilium": "1.19.402",
     "rke2-coredns": "1.46.002",
     "rke2-ingress-nginx": "4.15.101",
     "rke2-metrics-server": "3.13.100",
     "rke2-multus": "v4.2.418",
     "rke2-snapshot-controller": "4.2.006",
     "rke2-snapshot-controller-crd": "4.2.006",
     "rke2-traefik": "40.1.003",
     "rke2-traefik-crd": "40.1.003"
    },
    "components": {
     "Calico": "v3.32.0",
     "Canal": "Flannel v0.28.5 + Calico v3.32.0",
     "Cilium": "v1.19.4",
     "Containerd": "v2.2.5-k3s2",
     "CoreDNS": "v1.14.4",
     "Etcd": "v3.6.12-k3s1",
     "Flannel": "v0.28.5",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.35.6",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.7.4"
    },
    "date": "2026-06-25",
    "notes": [
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.7+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.100",
     "rke2-calico-crd": "v3.32.100",
     "rke2-canal": "v3.32.1-build2026072200",
     "rke2-cilium": "1.19.601",
     "rke2-coredns": "1.46.201",
     "rke2-ingress-nginx": "4.15.107",
     "rke2-metrics-server": "3.13.105",
     "rke2-multus": "v4.3.008",
     "rke2-snapshot-controller": "4.2.008",
     "rke2-snapshot-controller-crd": "4.2.008",
     "rke2-traefik": "40.1.009",
     "rke2-traefik-crd": "40.1.009"
    },
    "components": {
     "Calico": "v3.32.1",
     "Canal": "Flannel v0.28.8 + Calico v3.32.1",
     "Cilium": "v1.19.6",
     "Containerd": "v2.2.6-k3s1",
     "CoreDNS": "v1.14.6",
     "Etcd": "v3.6.14-k3s1",
     "Flannel": "v0.28.8",
     "Helm-controller": "v0.17.7",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.35.7",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.0",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.8"
    },
    "date": "2026-08-04",
    "notes": [
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.8+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.100",
     "rke2-calico-crd": "v3.32.100",
     "rke2-canal": "v3.32.1-build2026082700",
     "rke2-cilium": "1.19.601",
     "rke2-coredns": "1.47.003",
     "rke2-ingress-nginx": "4.15.109",
     "rke2-metrics-server": "3.14.000",
     "rke2-multus": "v4.3.008",
     "rke2-snapshot-controller": "5.2.003",
     "rke2-snapshot-controller-crd": "5.2.003",
     "rke2-traefik": "40.1.010",
     "rke2-traefik-crd": "40.1.010"
    },
    "components": {
     "Calico": "v3.32.1",
     "Canal": "Flannel v0.28.9 + Calico v3.32.1",
     "Cilium": "v1.19.6",
     "Containerd": "v2.2.7-k3s1",
     "CoreDNS": "v1.14.7",
     "Etcd": "v3.6.14-k3s1",
     "Flannel": "v0.28.9",
     "Helm-controller": "v0.17.7",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.35.8",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.0",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.11"
    },
    "date": "2026-08-28",
    "notes": [
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.35.9+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.200",
     "rke2-calico-crd": "v3.32.200",
     "rke2-canal": "v3.32.2-build2026090900",
     "rke2-cilium": "1.20.200",
     "rke2-coredns": "1.47.102",
     "rke2-ingress-nginx": "4.15.110",
     "rke2-metrics-server": "3.14.001",
     "rke2-multus": "v4.3.102",
     "rke2-snapshot-controller": "5.2.004",
     "rke2-snapshot-controller-crd": "5.2.004",
     "rke2-traefik": "40.1.013",
     "rke2-traefik-crd": "40.1.013"
    },
    "components": {
     "Calico": "v3.32.2",
     "Canal": "Flannel v0.28.9 + Calico v3.32.2",
     "Cilium": "v1.20.2",
     "Containerd": "v2.2.7-k3s1",
     "CoreDNS": "v1.14.7",
     "Etcd": "v3.6.14-k3s3",
     "Flannel": "v0.28.9",
     "Helm-controller": "v0.17.9",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.35.9",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.1",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.13"
    },
    "date": "2026-09-30",
    "notes": [
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.36.0+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.001",
     "rke2-calico-crd": "v3.32.001",
     "rke2-canal": "v3.32.0-build2026051100",
     "rke2-cilium": "1.19.303",
     "rke2-coredns": "1.45.212",
     "rke2-ingress-nginx": "4.14.506",
     "rke2-metrics-server": "3.13.008",
     "rke2-snapshot-controller": "4.2.003",
     "rke2-snapshot-controller-crd": "4.2.003",
     "rke2-traefik": "39.0.702",
     "rke2-traefik-crd": "39.0.702"
    },
    "components": {
     "Calico": "v3.32.0",
     "Canal": "Flannel v0.28.4 + Calico v3.32.0",
     "Cilium": "v1.19.3",
     "Containerd": "v2.2.3-k3s1",
     "CoreDNS": "v1.14.3",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.4",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.36.0",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.6.16"
    },
    "date": "2026-05-12",
    "notes": [
     "Upstream ingress-nginx Retirement & Transition to Traefik Because ingress-nginx was retired upstream as of March 2026, Traefik is now the default for new clusters starting in v1.36 (existing clusters will keep their current ingress upon upgrade to avoid breakage). This transition brings the following structural changes:",
     "Airgapped Environments: The rke2-images-core tarball now contains Traefik images instead of ingress-nginx. The standalone rke2-images-traefik tarball has been removed. Users who must continue using ingress-nginx will now need to manually provide the rke2-images-ingress-nginx tarball.",
     "Future Removal: The ingress-nginx chart will not receive any additional updates and will be completely removed in v1.37 for community users.",
     "The default ingress-controller is now traefik. Clusters with ingress-nginx installed and set as default will continue to use ingress-nginx by default, unless manually configured to deploy traefik instead.",
     "The rke2-images-core tarball now contains images for traefik, instead of ingress-nginx. Users who will continue to use ingress-nginx in airgapped environments will need to provide images from the rke2-images-ingress-nginx tarball. The standalone rke2-images-traefik tarball has been removed."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.36.1+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.001",
     "rke2-calico-crd": "v3.32.001",
     "rke2-canal": "v3.32.0-build2026051100",
     "rke2-cilium": "1.19.303",
     "rke2-coredns": "1.45.212",
     "rke2-ingress-nginx": "4.14.508",
     "rke2-metrics-server": "3.13.011",
     "rke2-snapshot-controller": "4.2.005",
     "rke2-snapshot-controller-crd": "4.2.003",
     "rke2-traefik": "39.0.703",
     "rke2-traefik-crd": "39.0.702"
    },
    "components": {
     "Calico": "v3.32.0",
     "Canal": "Flannel v0.28.4 + Calico v3.32.0",
     "Cilium": "v1.19.3",
     "Containerd": "v2.2.3-k3s1",
     "CoreDNS": "v1.14.3",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.4",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.36.1",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.6.16"
    },
    "date": "2026-05-18",
    "notes": [
     "Upstream ingress-nginx Retirement & Transition to Traefik Because ingress-nginx was retired upstream as of March 2026, Traefik is now the default for new clusters starting in v1.36 (existing clusters will keep their current ingress upon upgrade to avoid breakage). This transition brings the following structural changes:",
     "Airgapped Environments: The rke2-images-core tarball now contains Traefik images instead of ingress-nginx. The standalone rke2-images-traefik tarball has been removed. Users who must continue using ingress-nginx will now need to manually provide the rke2-images-ingress-nginx tarball.",
     "Future Removal: The ingress-nginx chart will not receive any additional updates and will be completely removed in v1.37 for community users."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.36.1+rke2r2": {
    "charts": {
     "rke2-calico": "v3.32.003",
     "rke2-calico-crd": "v3.32.003",
     "rke2-canal": "v3.32.0-build2026051100",
     "rke2-cilium": "1.19.303",
     "rke2-coredns": "1.45.212",
     "rke2-ingress-nginx": "4.14.509",
     "rke2-metrics-server": "3.13.011",
     "rke2-snapshot-controller": "4.2.005",
     "rke2-snapshot-controller-crd": "4.2.003",
     "rke2-traefik": "39.0.703",
     "rke2-traefik-crd": "39.0.702"
    },
    "components": {
     "Calico": "v3.32.0",
     "Canal": "Flannel v0.28.4 + Calico v3.32.0",
     "Cilium": "v1.19.3",
     "Containerd": "v2.2.3-k3s1",
     "CoreDNS": "v1.14.3",
     "Etcd": "v3.6.7-k3s1",
     "Flannel": "v0.28.4",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.36.1",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.6.16"
    },
    "date": "2026-05-28",
    "notes": [
     "Upstream ingress-nginx Retirement & Transition to Traefik Because ingress-nginx was retired upstream as of March 2026, Traefik is now the default for new clusters starting in v1.36 (existing clusters will keep their current ingress upon upgrade to avoid breakage). This transition brings the following structural changes:",
     "Airgapped Environments: The rke2-images-core tarball now contains Traefik images instead of ingress-nginx. The standalone rke2-images-traefik tarball has been removed. Users who must continue using ingress-nginx will now need to manually provide the rke2-images-ingress-nginx tarball.",
     "Future Removal: The ingress-nginx chart will not receive any additional updates and will be completely removed in v1.37 for community users."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.36.2+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.003",
     "rke2-calico-crd": "v3.32.003",
     "rke2-canal": "v3.32.0-build2026060401",
     "rke2-cilium": "1.19.402",
     "rke2-coredns": "1.46.002",
     "rke2-ingress-nginx": "4.15.101",
     "rke2-metrics-server": "3.13.100",
     "rke2-multus": "v4.2.418",
     "rke2-snapshot-controller": "4.2.006",
     "rke2-snapshot-controller-crd": "4.2.006",
     "rke2-traefik": "40.1.003",
     "rke2-traefik-crd": "40.1.003"
    },
    "components": {
     "Calico": "v3.32.0",
     "Canal": "Flannel v0.28.5 + Calico v3.32.0",
     "Cilium": "v1.19.4",
     "Containerd": "v2.3.2-k3s2",
     "CoreDNS": "v1.14.4",
     "Etcd": "v3.6.12-k3s1",
     "Flannel": "v0.28.5",
     "Helm-controller": "v0.17.1",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.36.2",
     "Metrics-server": "v0.8.1",
     "Multus": "v4.2.4",
     "Runc": "v1.4.2",
     "Traefik": "v3.7.4"
    },
    "date": "2026-06-25",
    "notes": [
     "Upstream ingress-nginx Retirement & Transition to Traefik Because ingress-nginx was retired upstream as of March 2026, Traefik is now the default for new clusters starting in v1.36 (existing clusters will keep their current ingress upon upgrade to avoid breakage). This transition brings the following structural changes:",
     "Airgapped Environments: The rke2-images-core tarball now contains Traefik images instead of ingress-nginx. The standalone rke2-images-traefik tarball has been removed. Users who must continue using ingress-nginx will now need to manually provide the rke2-images-ingress-nginx tarball.",
     "Future Removal: The ingress-nginx chart will not receive any additional updates and will be completely removed in v1.37 for community users.",
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.36.3+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.100",
     "rke2-calico-crd": "v3.32.100",
     "rke2-canal": "v3.32.1-build2026072200",
     "rke2-cilium": "1.19.601",
     "rke2-coredns": "1.46.201",
     "rke2-ingress-nginx": "4.15.107",
     "rke2-metrics-server": "3.13.105",
     "rke2-multus": "v4.3.008",
     "rke2-snapshot-controller": "4.2.008",
     "rke2-snapshot-controller-crd": "4.2.008",
     "rke2-traefik": "40.1.009",
     "rke2-traefik-crd": "40.1.009"
    },
    "components": {
     "Calico": "v3.32.1",
     "Canal": "Flannel v0.28.8 + Calico v3.32.1",
     "Cilium": "v1.19.6",
     "Containerd": "v2.3.3-k3s1",
     "CoreDNS": "v1.14.6",
     "Etcd": "v3.6.14-k3s1",
     "Flannel": "v0.28.8",
     "Helm-controller": "v0.17.7",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.36.3",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.0",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.8"
    },
    "date": "2026-08-04",
    "notes": [
     "Upstream ingress-nginx Retirement & Transition to Traefik Because ingress-nginx was retired upstream as of March 2026, Traefik is now the default for new clusters starting in v1.36 (existing clusters will keep their current ingress upon upgrade to avoid breakage). This transition brings the following structural changes:",
     "Airgapped Environments: The rke2-images-core tarball now contains Traefik images instead of ingress-nginx. The standalone rke2-images-traefik tarball has been removed. Users who must continue using ingress-nginx will now need to manually provide the rke2-images-ingress-nginx tarball.",
     "Future Removal: The ingress-nginx chart will not receive any additional updates and will be completely removed in v1.37 for community users.",
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.36.4+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.100",
     "rke2-calico-crd": "v3.32.100",
     "rke2-canal": "v3.32.1-build2026082700",
     "rke2-cilium": "1.19.601",
     "rke2-coredns": "1.47.003",
     "rke2-ingress-nginx": "4.15.109",
     "rke2-metrics-server": "3.14.000",
     "rke2-multus": "v4.3.008",
     "rke2-snapshot-controller": "5.2.003",
     "rke2-snapshot-controller-crd": "5.2.003",
     "rke2-traefik": "40.1.010",
     "rke2-traefik-crd": "40.1.010"
    },
    "components": {
     "Calico": "v3.32.1",
     "Canal": "Flannel v0.28.9 + Calico v3.32.1",
     "Cilium": "v1.19.6",
     "Containerd": "v2.3.4-k3s1.36",
     "CoreDNS": "v1.14.7",
     "Etcd": "v3.6.14-k3s1",
     "Flannel": "v0.28.9",
     "Helm-controller": "v0.17.7",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.36.4",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.0",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.11"
    },
    "date": "2026-08-28",
    "notes": [
     "Upstream ingress-nginx Retirement & Transition to Traefik Because ingress-nginx was retired upstream as of March 2026, Traefik is now the default for new clusters starting in v1.36 (existing clusters will keep their current ingress upon upgrade to avoid breakage). This transition brings the following structural changes:",
     "Airgapped Environments: The rke2-images-core tarball now contains Traefik images instead of ingress-nginx. The standalone rke2-images-traefik tarball has been removed. Users who must continue using ingress-nginx will now need to manually provide the rke2-images-ingress-nginx tarball.",
     "Future Removal: The ingress-nginx chart will not receive any additional updates and will be completely removed in v1.37 for community users.",
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.36.5+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.200",
     "rke2-calico-crd": "v3.32.200",
     "rke2-canal": "v3.32.2-build2026090900",
     "rke2-cilium": "1.20.200",
     "rke2-coredns": "1.47.102",
     "rke2-ingress-nginx": "4.15.110",
     "rke2-metrics-server": "3.14.001",
     "rke2-multus": "v4.3.102",
     "rke2-snapshot-controller": "5.2.004",
     "rke2-snapshot-controller-crd": "5.2.004",
     "rke2-traefik": "40.1.013",
     "rke2-traefik-crd": "40.1.013"
    },
    "components": {
     "Calico": "v3.32.2",
     "Canal": "Flannel v0.28.9 + Calico v3.32.2",
     "Cilium": "v1.20.2",
     "Containerd": "v2.3.4-k3s1",
     "CoreDNS": "v1.14.7",
     "Etcd": "v3.6.14-k3s3",
     "Flannel": "v0.28.9",
     "Helm-controller": "v0.17.9",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.36.5",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.1",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.13"
    },
    "date": "2026-09-30",
    "notes": [
     "Upstream ingress-nginx Retirement & Transition to Traefik Because ingress-nginx was retired upstream as of March 2026, Traefik is now the default for new clusters starting in v1.36 (existing clusters will keep their current ingress upon upgrade to avoid breakage). This transition brings the following structural changes:",
     "Airgapped Environments: The rke2-images-core tarball now contains Traefik images instead of ingress-nginx. The standalone rke2-images-traefik tarball has been removed. Users who must continue using ingress-nginx will now need to manually provide the rke2-images-ingress-nginx tarball.",
     "Future Removal: The ingress-nginx chart will not receive any additional updates and will be completely removed in v1.37 for community users.",
     "This release upgrades Traefik chart to v40.x which includes two breaking changes. Firstly, the Service spec syntax in values.yaml is now aligned with Kubernetes syntax (e.g. service.type → service.spec.type). Secondly, a breaking change affecting the ingress-nginx migration: the provider name changes from kubernetesIngressNginx to kubernetesIngressNGINX. Check https://github.com/traefik/traefik-helm-chart/releases/tag/v40.0.0 for more details"
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.36.6+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.200",
     "rke2-calico-crd": "v3.32.200",
     "rke2-canal": "v3.32.2-build2026102200",
     "rke2-cilium": "1.20.400",
     "rke2-coredns": "1.49.002",
     "rke2-ingress-nginx": "4.15.115",
     "rke2-metrics-server": "3.14.004",
     "rke2-multus": "v4.3.118",
     "rke2-snapshot-controller": "5.4.001",
     "rke2-snapshot-controller-crd": "5.4.001",
     "rke2-traefik": "40.1.022",
     "rke2-traefik-crd": "40.1.022"
    },
    "components": {
     "Calico": "v3.32.2",
     "Canal": "Flannel v0.28.10 + Calico v3.32.2",
     "Cilium": "v1.20.4",
     "Containerd": "v2.3.7-k3s1",
     "CoreDNS": "v1.14.7",
     "Etcd": "v3.6.14-k3s3",
     "Flannel": "v0.28.10",
     "Helm-controller": "v0.17.9",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.36.6",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.1",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.16"
    },
    "date": "2026-11-05",
    "notes": [
     "Upstream ingress-nginx Retirement & Transition to Traefik Because ingress-nginx was retired upstream as of March 2026, Traefik is now the default for new clusters starting in v1.36 (existing clusters will keep their current ingress upon upgrade to avoid breakage). This transition brings the following structural changes:",
     "Airgapped Environments: The rke2-images-core tarball now contains Traefik images instead of ingress-nginx. The standalone rke2-images-traefik tarball has been removed. Users who must continue using ingress-nginx will now need to manually provide the rke2-images-ingress-nginx tarball.",
     "Future Removal: The ingress-nginx chart will not receive any additional updates and will be completely removed in v1.37 for community users."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.37.0+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.200",
     "rke2-calico-crd": "v3.32.200",
     "rke2-canal": "v3.32.2-build2026090900",
     "rke2-cilium": "1.20.103",
     "rke2-coredns": "1.47.100",
     "rke2-ingress-nginx": "4.15.109",
     "rke2-metrics-server": "3.14.001",
     "rke2-multus": "v4.3.101",
     "rke2-snapshot-controller": "5.2.004",
     "rke2-snapshot-controller-crd": "5.2.004",
     "rke2-traefik": "41.2.003",
     "rke2-traefik-crd": "41.2.003"
    },
    "components": {
     "Calico": "v3.32.2",
     "Canal": "Flannel v0.28.9 + Calico v3.32.2",
     "Cilium": "v1.20.1",
     "Containerd": "v2.3.4-k3s1",
     "CoreDNS": "v1.14.7",
     "Etcd": "v3.7.1-k3s1",
     "Flannel": "v0.28.9",
     "Helm-controller": "v0.17.7",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.37.0",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.1",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.13"
    },
    "date": "2026-09-14",
    "notes": [
     "Users can no longer select ingress-controller: ingress-nginx. Only traefik, ingress-nginx is still supported to allow a last chance for migration."
    ],
    "prime_only": False,
    "pulled": False
   },
   "v1.37.1+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.200",
     "rke2-calico-crd": "v3.32.200",
     "rke2-canal": "v3.32.2-build2026090900",
     "rke2-cilium": "1.20.200",
     "rke2-coredns": "1.47.102",
     "rke2-ingress-nginx": "4.15.110",
     "rke2-metrics-server": "3.14.001",
     "rke2-multus": "v4.3.102",
     "rke2-snapshot-controller": "5.2.004",
     "rke2-snapshot-controller-crd": "5.2.004",
     "rke2-traefik": "41.2.003",
     "rke2-traefik-crd": "41.2.003"
    },
    "components": {
     "Calico": "v3.32.2",
     "Canal": "Flannel v0.28.9 + Calico v3.32.2",
     "Cilium": "v1.20.2",
     "Containerd": "v2.3.4-k3s1",
     "CoreDNS": "v1.14.7",
     "Etcd": "v3.7.1-k3s3",
     "Flannel": "v0.28.9",
     "Helm-controller": "v0.17.9",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.37.1",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.1",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.13"
    },
    "date": "2026-09-30",
    "notes": [],
    "prime_only": False,
    "pulled": False
   },
   "v1.37.2+rke2r1": {
    "charts": {
     "rke2-calico": "v3.32.200",
     "rke2-calico-crd": "v3.32.200",
     "rke2-canal": "v3.32.2-build2026102200",
     "rke2-cilium": "1.20.400",
     "rke2-coredns": "1.49.002",
     "rke2-gateway-api-crd": "1.6.300",
     "rke2-ingress-nginx": "4.15.115",
     "rke2-metrics-server": "3.14.004",
     "rke2-multus": "v4.3.118",
     "rke2-security-responder": "0.1.901",
     "rke2-snapshot-controller": "5.4.001",
     "rke2-snapshot-controller-crd": "5.4.001",
     "rke2-traefik": "42.1.301",
     "rke2-traefik-crd": "42.1.301"
    },
    "components": {
     "Calico": "v3.32.2",
     "Canal": "Flannel v0.28.10 + Calico v3.32.2",
     "Cilium": "v1.20.4",
     "Containerd": "v2.3.7-k3s1",
     "CoreDNS": "v1.14.7",
     "Etcd": "v3.7.1-k3s3",
     "Flannel": "v0.28.10",
     "Helm-controller": "v0.17.9",
     "Ingress-Nginx": "v1.14.5-hardened2",
     "Kubernetes": "v1.37.2",
     "Metrics-server": "v0.9.0",
     "Multus": "v4.3.1",
     "Runc": "v1.4.3",
     "Traefik": "v3.7.16"
    },
    "date": "2026-11-05",
    "notes": [],
    "prime_only": False,
    "pulled": False
   }
  },
  "url": "https://github.com/rancher/rke2/releases"
 },
 "url": {
  "apis": "https://kubernetes.io/docs/reference/using-api/deprecation-guide/",
  "changelog": "https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.{n}.md",
  "gates": "https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/",
  "volumes": "https://kubernetes.io/docs/concepts/storage/persistent-volumes/#types-of-persistent-volumes"
 },
 "volume_types": {
  "awsElasticBlockStore": {
   "since": 23,
   "state": "migrated"
  },
  "azureDisk": {
   "since": 23,
   "state": "migrated"
  },
  "azureFile": {
   "since": 24,
   "state": "migrated"
  },
  "cephfs": {
   "since": 31,
   "state": "removed"
  },
  "cinder": {
   "since": 21,
   "state": "migrated"
  },
  "flocker": {
   "since": 25,
   "state": "removed"
  },
  "gcePersistentDisk": {
   "since": 23,
   "state": "migrated"
  },
  "glusterfs": {
   "since": 26,
   "state": "removed"
  },
  "photonPersistentDisk": {
   "since": 15,
   "state": "removed"
  },
  "portworxVolume": {
   "since": 31,
   "state": "migrated"
  },
  "quobyte": {
   "since": 25,
   "state": "removed"
  },
  "rbd": {
   "since": 31,
   "state": "removed"
  },
  "scaleIO": {
   "since": 21,
   "state": "removed"
  },
  "storageos": {
   "since": 25,
   "state": "removed"
  },
  "vsphereVolume": {
   "since": 25,
   "state": "migrated"
  }
 }
}
