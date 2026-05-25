/* Polaris 로고 마크 — 골드 8각 별 (북극성) + 후광/광선
   - size 작아도 (16–22px) 골드 글로우가 살아 있도록 디자인
   - 각 인스턴스 unique id (gradient/filter 충돌 방지) */
import React, { useRef } from 'react'

let __polarisMarkSeq = 0

export default function PolarisMark({ size = 22, glow = true }) {
  const idRef = useRef(null)
  if (idRef.current === null) idRef.current = ++__polarisMarkSeq
  const id = idRef.current

  return (
    <svg width={size} height={size} viewBox="-4 -4 48 48" style={{ display: 'block', overflow: 'visible' }}>
      <defs>
        {/* 별의 골드 그라데이션 */}
        <linearGradient id={`pmStar-${id}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#fff5d0" />
          <stop offset="55%" stopColor="#f3c969" />
          <stop offset="100%" stopColor="#a87830" />
        </linearGradient>
        {/* 후광 — 골드 빛이 사방으로 퍼짐 */}
        <radialGradient id={`pmHalo-${id}`} cx="50%" cy="50%" r="50%">
          <stop offset="0%"   stopColor="#ffe9b8" stopOpacity="0.9" />
          <stop offset="40%"  stopColor="#f3c969" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#f3c969" stopOpacity="0" />
        </radialGradient>
        {/* 별빛 광선 — 가로/세로/사선 */}
        <linearGradient id={`pmRayV-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#f3c969" stopOpacity="0" />
          <stop offset="50%"  stopColor="#fff5d0" stopOpacity="1" />
          <stop offset="100%" stopColor="#f3c969" stopOpacity="0" />
        </linearGradient>
        <linearGradient id={`pmRayH-${id}`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%"   stopColor="#f3c969" stopOpacity="0" />
          <stop offset="50%"  stopColor="#fff5d0" stopOpacity="1" />
          <stop offset="100%" stopColor="#f3c969" stopOpacity="0" />
        </linearGradient>
        {/* 별 자체에 약한 블러 글로우 */}
        <filter id={`pmGlow-${id}`} x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="0.9" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* 후광 */}
      {glow && <circle cx="20" cy="20" r="26" fill={`url(#pmHalo-${id})`} />}

      {/* 4축 광선 */}
      {glow && (
        <g>
          <rect x="19.4" y="-4"  width="1.2" height="48" fill={`url(#pmRayV-${id})`} opacity="0.85" />
          <rect x="-4"   y="19.4" width="48"  height="1.2" fill={`url(#pmRayH-${id})`} opacity="0.85" />
          <g transform="rotate(45 20 20)" opacity="0.55">
            <rect x="19.6" y="-4" width="0.8" height="48" fill={`url(#pmRayV-${id})`} />
          </g>
          <g transform="rotate(-45 20 20)" opacity="0.55">
            <rect x="19.6" y="-4" width="0.8" height="48" fill={`url(#pmRayV-${id})`} />
          </g>
        </g>
      )}

      {/* 메인 별 — 8각 컴퍼스 별 (북극성) */}
      <polygon
        points="20,3 23,17 37,20 23,23 20,37 17,23 3,20 17,17"
        fill={`url(#pmStar-${id})`}
        filter={`url(#pmGlow-${id})`}
      />
      {/* 내부 작은 별 — 하이라이트 */}
      <polygon
        points="20,10 21.4,18.6 30,20 21.4,21.4 20,30 18.6,21.4 10,20 18.6,18.6"
        fill="#fff5d6"
        opacity="0.92"
      />
      {/* 중심 점 */}
      <circle cx="20" cy="20" r="1.6" fill="#1a1024" />
    </svg>
  )
}
