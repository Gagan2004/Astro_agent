import React, { useState } from 'react';

interface PlanetInfo {
  sign_name: string;
  sign_sanskrit: string;
  sign_symbol: string;
  degrees: number;
  minutes: number;
  formatted: string;
  house?: number;
  raw_longitude?: number;
}

interface ChartData {
  ascendant: PlanetInfo;
  mc: PlanetInfo;
  planets: Record<string, PlanetInfo>;
  ayanamsa?: number;
  cusps?: number[];
}

interface PlanetPositionsProps {
  chartData: ChartData;
  sidereal: boolean;
}

// Major aspect configurations for the aspect lines in the center of the wheel
const ASPECTS = [
  { name: 'Conjunction', angle: 0, orb: 8, color: '#FFD700', dash: 'none' },   // Gold
  { name: 'Sextile', angle: 60, orb: 6, color: '#32CD32', dash: '3,3' },     // Green
  { name: 'Square', angle: 90, orb: 8, color: '#FF4500', dash: 'none' },      // Orange-Red
  { name: 'Trine', angle: 120, orb: 8, color: '#1E90FF', dash: 'none' },     // Blue
  { name: 'Opposition', angle: 180, orb: 8, color: '#BA55D3', dash: '4,4' }  // Purple
];

interface Aspect {
  p1: string;
  p2: string;
  type: string;
  color: string;
  dash: string;
}

// Polar to Cartesian conversion helper for circular coordinates
const polarToCartesian = (centerX: number, centerY: number, radius: number, angleInDegrees: number) => {
  const angleInRadians = (angleInDegrees * Math.PI) / 180.0;
  return {
    x: centerX + radius * Math.cos(angleInRadians),
    y: centerY - radius * Math.sin(angleInRadians)
  };
};

export const PlanetPositions: React.FC<PlanetPositionsProps> = ({ chartData, sidereal }) => {
  const { ascendant, planets } = chartData;
  const [viewMode, setViewMode] = useState<'visual' | 'list'>('visual');

  const ascLongitude = ascendant.raw_longitude ?? 0;
  const signsList = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
  ];

  // Helper to safely get raw longitude if missing
  const getRawLongitude = (_name: string, info: PlanetInfo): number => {
    if (info.raw_longitude !== undefined) return info.raw_longitude;
    const idx = signsList.indexOf(info.sign_name);
    return (idx >= 0 ? idx * 30 : 0) + info.degrees + info.minutes / 60.0;
  };

  // 1. Calculate natal aspects on the fly
  const getNatalAspects = (): Aspect[] => {
    const planetEntries = Object.entries(planets);
    const list: Aspect[] = [];
    for (let i = 0; i < planetEntries.length; i++) {
      for (let j = i + 1; j < planetEntries.length; j++) {
        const [name1, p1] = planetEntries[i];
        const [name2, p2] = planetEntries[j];
        const long1 = getRawLongitude(name1, p1);
        const long2 = getRawLongitude(name2, p2);
        
        let diff = Math.abs(long1 - long2);
        diff = Math.min(diff, 360 - diff);
        
        for (const aspect of ASPECTS) {
          if (Math.abs(diff - aspect.angle) <= aspect.orb) {
            list.push({
              p1: name1,
              p2: name2,
              type: aspect.name,
              color: aspect.color,
              dash: aspect.dash
            });
          }
        }
      }
    }
    return list;
  };

  // Helper to resolve 2-letter planet abbreviation for Vedic square chart
  const getPlanetAbbrev = (name: string): string => {
    switch (name) {
      case 'Sun': return 'Su';
      case 'Moon': return 'Mo';
      case 'Mercury': return 'Me';
      case 'Venus': return 'Ve';
      case 'Mars': return 'Ma';
      case 'Jupiter': return 'Ju';
      case 'Saturn': return 'Sa';
      case 'Rahu': return 'Ra';
      case 'Ketu': return 'Ke';
      case 'Uranus': return 'Ur';
      case 'Neptune': return 'Ne';
      case 'Pluto': return 'Pl';
      default: return name.substring(0, 2);
    }
  };

  // Render 1: Western Circular Chart Wheel
  const renderWesternWheel = () => {
    const center = 200;
    const houseCusps = chartData.cusps || Array.from({ length: 12 }, (_, i) => (ascLongitude + i * 30) % 360);
    const aspects = getNatalAspects();

    // Map sign element to colors
    const getSignColor = (signName: string) => {
      const idx = signsList.indexOf(signName);
      const elements = ['fire', 'earth', 'air', 'water'];
      const elem = elements[idx % 4];
      switch (elem) {
        case 'fire': return { bg: 'rgba(255, 99, 132, 0.08)', border: 'rgba(255, 99, 132, 0.35)' };
        case 'earth': return { bg: 'rgba(75, 192, 192, 0.08)', border: 'rgba(75, 192, 192, 0.35)' };
        case 'air': return { bg: 'rgba(255, 205, 86, 0.08)', border: 'rgba(255, 205, 86, 0.35)' };
        case 'water': return { bg: 'rgba(54, 162, 235, 0.08)', border: 'rgba(54, 162, 235, 0.35)' };
        default: return { bg: 'rgba(255, 255, 255, 0.05)', border: 'var(--color-card-border)' };
      }
    };

    return (
      <svg width="100%" height="100%" viewBox="0 0 400 400" style={{ maxWidth: '400px', margin: '0 auto', display: 'block' }}>
        {/* Background Grids */}
        <circle cx={center} cy={center} r="185" fill="rgba(5, 6, 20, 0.4)" stroke="var(--color-card-border)" strokeWidth="1" />
        <circle cx={center} cy={center} r="160" fill="none" stroke="var(--color-card-border)" strokeWidth="1" />
        <circle cx={center} cy={center} r="100" fill="none" stroke="var(--color-card-border)" strokeWidth="1" />
        <circle cx={center} cy={center} r="50" fill="none" stroke="var(--color-card-border)" strokeWidth="0.5" />

        {/* 1. Draw Zodiac signs outer dividers and symbols */}
        {signsList.map((sign, i) => {
          const startAngle = 180 + (i * 30 - ascLongitude);
          const midAngle = startAngle + 15;
          const signInfo = getSignColor(sign);

          // Divider lines
          const innerPt = polarToCartesian(center, center, 160, startAngle);
          const outerPt = polarToCartesian(center, center, 185, startAngle);
          
          // Symbol position
          const symPt = polarToCartesian(center, center, 172.5, midAngle);
          const signSymbol = getZodiacSymbol(sign);

          return (
            <g key={sign}>
              {/* Radial divider */}
              <line x1={innerPt.x} y1={innerPt.y} x2={outerPt.x} y2={outerPt.y} stroke={signInfo.border} strokeWidth="1" />
              {/* Sign label */}
              <text
                x={symPt.x}
                y={symPt.y}
                fill="var(--color-text-main)"
                fontSize="0.9rem"
                fontWeight="bold"
                textAnchor="middle"
                dominantBaseline="central"
                style={{ cursor: 'help' }}
              >
                <title>{sign}</title>
                {signSymbol}
              </text>
            </g>
          );
        })}

        {/* 2. Draw House dividing lines */}
        {houseCusps.map((cusp, idx) => {
          const houseNum = idx + 1;
          const relativeAngle = 180 + (cusp - ascLongitude);
          const innerPt = polarToCartesian(center, center, 50, relativeAngle);
          const outerPt = polarToCartesian(center, center, 160, relativeAngle);

          // Highlight Ascendant (1st House) and Midheaven (10th House) cusp lines
          const isAsc = houseNum === 1;
          const isMC = houseNum === 10;
          const strokeColor = isAsc || isMC ? 'var(--color-gold)' : 'rgba(212, 175, 55, 0.25)';
          const strokeWidth = isAsc || isMC ? '2.5' : '1';

          // Calculate house center for label placing
          const nextCusp = houseCusps[idx % 12];
          let nextAngle = 180 + (nextCusp - ascLongitude);
          if (nextAngle < relativeAngle) nextAngle += 360;
          const midAngle = relativeAngle + (nextAngle - relativeAngle) / 2;
          const labelPt = polarToCartesian(center, center, 75, midAngle);

          return (
            <g key={houseNum}>
              <line x1={innerPt.x} y1={innerPt.y} x2={outerPt.x} y2={outerPt.y} stroke={strokeColor} strokeWidth={strokeWidth} />
              {/* House Number inside */}
              <text
                x={labelPt.x}
                y={labelPt.y}
                fill="var(--color-text-muted)"
                fontSize="0.7rem"
                textAnchor="middle"
                dominantBaseline="central"
              >
                {houseNum}
              </text>
            </g>
          );
        })}

        {/* 3. Draw Aspect lines in the center */}
        {aspects.map((asp, idx) => {
          const p1Long = getRawLongitude(asp.p1, planets[asp.p1]);
          const p2Long = getRawLongitude(asp.p2, planets[asp.p2]);
          const ang1 = 180 + (p1Long - ascLongitude);
          const ang2 = 180 + (p2Long - ascLongitude);

          const pt1 = polarToCartesian(center, center, 95, ang1);
          const pt2 = polarToCartesian(center, center, 95, ang2);

          return (
            <line
              key={idx}
              x1={pt1.x}
              y1={pt1.y}
              x2={pt2.x}
              y2={pt2.y}
              stroke={asp.color}
              strokeWidth="1.5"
              strokeOpacity="0.45"
              strokeDasharray={asp.dash !== 'none' ? asp.dash : undefined}
            >
              <title>{`${asp.p1} ${asp.type} ${asp.p2}`}</title>
            </line>
          );
        })}

        {/* 4. Draw Planets on the wheel ring */}
        {Object.entries(planets).map(([planetName, info]) => {
          const rawLong = getRawLongitude(planetName, info);
          const relativeAngle = 180 + (rawLong - ascLongitude);
          
          // Tick from inner to text
          const tickStart = polarToCartesian(center, center, 100, relativeAngle);
          const tickEnd = polarToCartesian(center, center, 112, relativeAngle);
          const textPt = polarToCartesian(center, center, 130, relativeAngle);

          return (
            <g key={planetName} className="planet-node">
              {/* Small indicator tick line */}
              <line x1={tickStart.x} y1={tickStart.y} x2={tickEnd.x} y2={tickEnd.y} stroke="var(--color-gold)" strokeWidth="1" />
              {/* Planet icon and abbreviation tooltip */}
              <text
                x={textPt.x}
                y={textPt.y}
                fill="var(--color-gold-light)"
                fontSize="1.1rem"
                textAnchor="middle"
                dominantBaseline="central"
                style={{ cursor: 'pointer', filter: 'drop-shadow(0 0 2px var(--color-gold-glow))' }}
              >
                <title>{`${planetName}: ${info.formatted} (House ${info.house})`}</title>
                {getPlanetEmoji(planetName)}
              </text>
            </g>
          );
        })}

        {/* Center spiritual circle marker */}
        <circle cx={center} cy={center} r="16" fill="var(--bg-deep)" stroke="var(--color-gold)" strokeWidth="1.5" />
        <text x={center} y={center} fill="var(--color-gold)" fontSize="0.75rem" textAnchor="middle" dominantBaseline="central" className="pulse-indicator">
          ✨
        </text>
      </svg>
    );
  };

  // Render 2: Vedic North Indian Diamond Style Chart (Kundali)
  const renderVedicChart = () => {
    const ascSignIndex = signsList.indexOf(ascendant.sign_name);
    
    // Group planets by their house numbers (1 to 12)
    const planetsByHouse: Record<number, string[]> = {};
    for (let h = 1; h <= 12; h++) {
      planetsByHouse[h] = [];
    }
    
    // Put Ascendant (Lagna) as As in House 1
    planetsByHouse[1].push('As');
    
    Object.entries(planets).forEach(([planetName, info]) => {
      if (info.house) {
        planetsByHouse[info.house].push(getPlanetAbbrev(planetName));
      }
    });

    // Vedic House coordinate mapping ( centerX, centerY for planets list; signX, signY for Sign number )
    const VEDIC_HOUSE_POSITIONS: Record<number, { centerX: number; centerY: number; signX: number; signY: number }> = {
      1: { centerX: 160, centerY: 110, signX: 160, signY: 55 },
      2: { centerX: 95, centerY: 65, signX: 125, signY: 45 },
      3: { centerX: 65, centerY: 95, signX: 45, signY: 125 },
      4: { centerX: 115, centerY: 160, signX: 55, signY: 160 },
      5: { centerX: 65, centerY: 225, signX: 45, signY: 195 },
      6: { centerX: 95, centerY: 255, signX: 125, signY: 275 },
      7: { centerX: 160, centerY: 210, signX: 160, signY: 265 },
      8: { centerX: 225, centerY: 255, signX: 195, signY: 275 },
      9: { centerX: 255, centerY: 225, signX: 275, signY: 195 },
      10: { centerX: 205, centerY: 160, signX: 265, signY: 160 },
      11: { centerX: 255, centerY: 95, signX: 275, signY: 125 },
      12: { centerX: 225, centerY: 65, signX: 195, signY: 45 }
    };

    return (
      <svg width="100%" viewBox="0 0 320 320" style={{ maxWidth: '320px', margin: '0 auto', display: 'block' }}>
        {/* Border Box */}
        <rect x="10" y="10" width="300" height="300" fill="rgba(5, 6, 20, 0.4)" stroke="var(--color-card-border)" strokeWidth="2" />
        
        {/* Diagonals */}
        <line x1="10" y1="10" x2="310" y2="310" stroke="var(--color-card-border)" strokeWidth="1.5" />
        <line x1="310" y1="10" x2="10" y2="310" stroke="var(--color-card-border)" strokeWidth="1.5" />
        
        {/* Diamond lines */}
        <line x1="160" y1="10" x2="10" y2="160" stroke="var(--color-card-border)" strokeWidth="1.5" />
        <line x1="10" y1="160" x2="160" y2="310" stroke="var(--color-card-border)" strokeWidth="1.5" />
        <line x1="160" y1="310" x2="310" y2="160" stroke="var(--color-card-border)" strokeWidth="1.5" />
        <line x1="310" y1="160" x2="160" y2="10" stroke="var(--color-card-border)" strokeWidth="1.5" />

        {/* 12 House Placements rendering */}
        {Array.from({ length: 12 }, (_, idx) => {
          const houseNum = idx + 1;
          const pos = VEDIC_HOUSE_POSITIONS[houseNum];
          // Sign number is calculated starting from Ascendant sign index
          const signIndex = (ascSignIndex + houseNum - 1) % 12;
          const signNum = signIndex + 1;
          const signName = signsList[signIndex];
          const signSanskrit = chartData.planets[signName]?.sign_sanskrit || '';

          const housePlanets = planetsByHouse[houseNum];

          return (
            <g key={houseNum}>
              {/* Sign Number */}
              <text
                x={pos.signX}
                y={pos.signY}
                fill="var(--color-gold-light)"
                fontSize="0.75rem"
                fontWeight="700"
                textAnchor="middle"
                dominantBaseline="central"
                style={{ cursor: 'help' }}
              >
                <title>{`${signName} (${signSanskrit})`}</title>
                {signNum}
              </text>
              {/* Planet symbols */}
              {housePlanets.length > 0 && (
                <text
                  x={pos.centerX}
                  y={pos.centerY}
                  fill="var(--color-text-main)"
                  fontSize="0.85rem"
                  fontWeight="bold"
                  textAnchor="middle"
                  dominantBaseline="central"
                >
                  {housePlanets.join(' ')}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    );
  };

  return (
    <div className="glass-panel chart-display-panel" style={{ padding: '1.25rem', marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid var(--color-card-border)', paddingBottom: '0.6rem' }}>
        <h4 style={{ color: 'var(--color-gold)', fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }} className="gold-glow">
          🪐 {sidereal ? 'Kundali Chart (Vedic)' : 'Birth Wheel (Western)'}
        </h4>
        <div style={{ display: 'flex', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '30px', padding: '2px' }}>
          <button
            onClick={() => setViewMode('visual')}
            style={{
              background: viewMode === 'visual' ? 'var(--color-gold)' : 'transparent',
              color: viewMode === 'visual' ? '#000' : 'var(--color-text-muted)',
              border: 'none',
              padding: '0.2rem 0.6rem',
              borderRadius: '20px',
              fontSize: '0.75rem',
              cursor: 'pointer',
              fontWeight: 600,
              transition: 'background 0.2s, color 0.2s',
            }}
          >
            Visual
          </button>
          <button
            onClick={() => setViewMode('list')}
            style={{
              background: viewMode === 'list' ? 'var(--color-gold)' : 'transparent',
              color: viewMode === 'list' ? '#000' : 'var(--color-text-muted)',
              border: 'none',
              padding: '0.2rem 0.6rem',
              borderRadius: '20px',
              fontSize: '0.75rem',
              cursor: 'pointer',
              fontWeight: 600,
              transition: 'background 0.2s, color 0.2s',
            }}
          >
            Placements
          </button>
        </div>
      </div>

      {viewMode === 'visual' ? (
        <div style={{ padding: '0.5rem 0' }}>
          {sidereal ? renderVedicChart() : renderWesternWheel()}
          <div style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.8rem' }}>
            {sidereal 
              ? 'North Indian style square chart. Center numbers indicate Zodiac signs.' 
              : 'Western style circular wheel. Outer perimeter shows Zodiac; inner lines represent houses.'}
          </div>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))',
            gap: '0.5rem',
            maxHeight: '320px',
            overflowY: 'auto',
            paddingRight: '4px'
          }}
        >
          {/* Render Ascendant first */}
          <div
            style={{
              background: 'rgba(212, 175, 55, 0.08)',
              border: '1px solid rgba(212, 175, 55, 0.3)',
              borderRadius: 'var(--radius-md)',
              padding: '0.5rem',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '0.7rem', color: 'var(--color-gold-light)', textTransform: 'uppercase', letterSpacing: '0.3px', fontWeight: 600 }}>Ascendant</div>
            <div style={{ fontSize: '1.4rem', margin: '0.1rem 0' }}>🌅</div>
            <div style={{ fontWeight: '600', fontSize: '0.85rem' }}>{ascendant.sign_symbol} {ascendant.sign_name}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{ascendant.degrees}° {ascendant.minutes}'</div>
            <div style={{ fontSize: '0.7rem', marginTop: '0.15rem', background: 'rgba(255, 255, 255, 0.05)', padding: '1px 3px', borderRadius: '3px', display: 'inline-block' }}>House 1</div>
          </div>

          {/* Render Planets */}
          {Object.entries(planets).map(([planetName, data]) => (
            <div
              key={planetName}
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--color-card-border)',
                borderRadius: 'var(--radius-md)',
                padding: '0.5rem',
                textAlign: 'center',
                transition: 'transform 0.2s',
              }}
              onMouseOver={(e) => (e.currentTarget.style.transform = 'translateY(-2px)')}
              onMouseOut={(e) => (e.currentTarget.style.transform = 'translateY(0)')}
            >
              <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', fontWeight: 600 }}>{planetName}</div>
              <div style={{ fontSize: '1.4rem', margin: '0.1rem 0', filter: 'drop-shadow(0 0 3px var(--color-gold-glow))' }}>
                {getPlanetEmoji(planetName)}
              </div>
              <div style={{ fontWeight: '600', fontSize: '0.85rem' }}>{data.sign_symbol} {data.sign_name}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{data.degrees}° {data.minutes}'</div>
              {data.house && (
                <div style={{ fontSize: '0.7rem', marginTop: '0.15rem', background: 'rgba(255, 255, 255, 0.05)', padding: '1px 3px', borderRadius: '3px', display: 'inline-block' }}>
                  House {data.house}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Helper to get nice emoji representations for planets
function getPlanetEmoji(name: string): string {
  switch (name) {
    case 'Sun': return '☀️';
    case 'Moon': return '🌙';
    case 'Mercury': return '☿️';
    case 'Venus': return '♀️';
    case 'Mars': return '♂️';
    case 'Jupiter': return '♃';
    case 'Saturn': return '♄';
    case 'Uranus': return '♅';
    case 'Neptune': return '♆';
    case 'Pluto': return '♇';
    case 'Rahu': return '🐉'; // Dragon Head (North Node)
    case 'Ketu': return '⚗️'; // Tail of the Dragon (South Node)
    default: return '🪐';
  }
}

// Get standard unicode symbol characters for zodiac signs
function getZodiacSymbol(name: string): string {
  switch (name) {
    case 'Aries': return '♈';
    case 'Taurus': return '♉';
    case 'Gemini': return '♊';
    case 'Cancer': return '♋';
    case 'Leo': return '♌';
    case 'Virgo': return '♍';
    case 'Libra': return '♎';
    case 'Scorpio': return '♏';
    case 'Sagittarius': return '♐';
    case 'Capricorn': return '♑';
    case 'Aquarius': return '♒';
    case 'Pisces': return '♓';
    default: return '🌌';
  }
}
