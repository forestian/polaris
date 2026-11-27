import React, { useRef } from 'react'

/* PolarisInstallStar — 설치 창 좌측 브랜드 패널용 별 일러스트 (목업 그대로 이식).
   intensity: 0(미니멀) → 1(후광+광선+별클러스터+점선가이드) */
let __pisSeq = 0

export default function PolarisInstallStar({ size = 360, intensity = 0.7 }) {
  const idRef = useRef(null)
  if (idRef.current === null) idRef.current = ++__pisSeq
  const id = idRef.current

  const clamp = (v) => Math.max(0, Math.min(1, v))
  const I = clamp(intensity)
  const dustOp = clamp((I - 0.1) / 0.5) * 0.5
  const ringOp = clamp((I - 0.25) / 0.4)
  const rayOp = clamp((I - 0.15) / 0.45)
  const diagRayOp = clamp((I - 0.45) / 0.45) * 0.35
  const haloOp = clamp((I - 0.2) / 0.5)
  const clusterOp = clamp((I - 0.5) / 0.45)
  const cx = 200, cy = 200

  return (
    <svg width={size} height={size} viewBox="0 0 400 400"
      style={{ display: 'block', overflow: 'visible' }} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id={`pisRayV-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#f3c969" stopOpacity="0"/>
          <stop offset="50%" stopColor="#f3c969" stopOpacity="0.9"/>
          <stop offset="100%" stopColor="#f3c969" stopOpacity="0"/>
        </linearGradient>
        <linearGradient id={`pisRayH-${id}`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#f3c969" stopOpacity="0"/>
          <stop offset="50%" stopColor="#f3c969" stopOpacity="0.9"/>
          <stop offset="100%" stopColor="#f3c969" stopOpacity="0"/>
        </linearGradient>
        <radialGradient id={`pisHalo-${id}`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fff5d6" stopOpacity="1"/>
          <stop offset="32%" stopColor="#f3c969" stopOpacity="0.85"/>
          <stop offset="100%" stopColor="#f3c969" stopOpacity="0"/>
        </radialGradient>
        <linearGradient id={`pisStar-${id}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#fff5d0"/>
          <stop offset="55%" stopColor="#f3c969"/>
          <stop offset="100%" stopColor="#c89a3e"/>
        </linearGradient>
      </defs>

      <g fill="#ffffff" opacity={dustOp}>
        <circle cx="60" cy="60" r="0.9"/><circle cx="120" cy="120" r="1.2"/>
        <circle cx="240" cy="40" r="0.7"/><circle cx="340" cy="100" r="1"/>
        <circle cx="40" cy="220" r="0.9"/><circle cx="160" cy="280" r="0.7"/>
        <circle cx="360" cy="240" r="1.2"/><circle cx="300" cy="340" r="0.9"/>
        <circle cx="80" cy="360" r="1"/><circle cx="220" cy="380" r="0.7"/>
        <circle cx="380" cy="60" r="0.9"/><circle cx="200" cy="190" r="0.6"/>
        <circle cx="280" cy="160" r="0.7"/><circle cx="40" cy="320" r="0.7"/>
        <circle cx="320" cy="290" r="0.7"/><circle cx="150" cy="60" r="0.8"/>
      </g>

      <g fill="none" stroke="#7dd3fc">
        <circle cx={cx} cy={cy} r="170" strokeWidth="1" opacity={ringOp * 0.1}/>
        <circle cx={cx} cy={cy} r="125" strokeWidth="1" opacity={ringOp * 0.16}/>
        <circle cx={cx} cy={cy} r="86" stroke="#f3c969" strokeWidth="1" opacity={ringOp * 0.26}/>
        <circle cx={cx} cy={cy} r="54" stroke="#f3c969" strokeWidth="1" opacity={ringOp * 0.4}/>
      </g>

      <g opacity={rayOp}>
        <rect x="198" y="0" width="4" height="400" fill={`url(#pisRayV-${id})`}/>
        <rect x="0" y="198" width="400" height="4" fill={`url(#pisRayH-${id})`}/>
      </g>
      <g opacity={diagRayOp}>
        <g transform={`rotate(45 ${cx} ${cy})`}><rect x="199" y="20" width="2" height="360" fill="#7dd3fc"/></g>
        <g transform={`rotate(-45 ${cx} ${cy})`}><rect x="199" y="20" width="2" height="360" fill="#7dd3fc"/></g>
      </g>

      <circle cx={cx} cy={cy} r="64" fill={`url(#pisHalo-${id})`} opacity={haloOp}/>

      <g opacity={clusterOp}>
        <g stroke="#7dd3fc" strokeWidth="0.6" opacity="0.3" strokeDasharray="2 3">
          <line x1="80" y1="80" x2={cx} y2={cy}/><line x1="340" y1="100" x2={cx} y2={cy}/>
          <line x1="100" y1="320" x2={cx} y2={cy}/><line x1="340" y1="320" x2={cx} y2={cy}/>
        </g>
        <g fill="#7dd3fc">
          <circle cx="80" cy="80" r="2.6"/><circle cx="340" cy="100" r="2.2"/>
          <circle cx="100" cy="320" r="2.6"/><circle cx="340" cy="320" r="2.2"/>
          <circle cx="40" cy="200" r="1.8"/><circle cx="280" cy="360" r="1.8"/>
        </g>
      </g>

      <polygon points="200,144 210,192 258,200 210,208 200,256 190,208 142,200 190,192" fill={`url(#pisStar-${id})`}/>
      <polygon points="200,168 206,196 234,200 206,204 200,232 194,204 166,200 194,196" fill="#fff5d6"/>
      <circle cx={cx} cy={cy} r="4" fill="#14163d"/>
    </svg>
  )
}
