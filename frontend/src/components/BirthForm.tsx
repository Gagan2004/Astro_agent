import React, { useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

interface BirthDetails {
  name: string;
  date: string; // YYYY-MM-DD
  time: string; // HH:MM
  place: string;
  latitude: number;
  longitude: number;
  timezone: string;
  display_name: string;
  sidereal: boolean;
}

interface BirthFormProps {
  onSave: (details: BirthDetails) => void;
  initialDetails?: BirthDetails | null;
}

export const BirthForm: React.FC<BirthFormProps> = ({ onSave, initialDetails }) => {
  const [name, setName] = useState(initialDetails?.name || '');
  const [date, setDate] = useState(initialDetails?.date || '');
  const [time, setTime] = useState(initialDetails?.time || '');
  const [place, setPlace] = useState(initialDetails?.place || '');
  const [sidereal, setSidereal] = useState(initialDetails?.sidereal || false);

  const [geocoded, setGeocoded] = useState<any>(
    initialDetails
      ? {
        lat: initialDetails.latitude,
        lng: initialDetails.longitude,
        timezone: initialDetails.timezone,
        display_name: initialDetails.display_name,
      }
      : null
  );

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [suggestions, setSuggestions] = useState<any[]>([]);

  const handleGeocode = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (!place.trim()) {
      setError('Please enter a place name first.');
      return;
    }

    setLoading(true);
    setError('');
    setGeocoded(null);
    setSuggestions([]);

    try {
      // Call backend geocoder
      const response = await fetch(`${API_BASE_URL}api/geocode?place_name=${encodeURIComponent(place)}`);
      if (!response.ok) {
        throw new Error('Location could not be found. Please try a major nearby city.');
      }
      const data = await response.json();

      if (data.results && data.results.length > 1) {
        setSuggestions(data.results);
      } else {
        setSuggestions([]);
      }

      setGeocoded(data);
      // Automatically prefill place with display_name
      setPlace(data.display_name);
    } catch (err: any) {
      setError(err.message || 'Geocoding failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!name.trim()) {
      setError('Please enter your name.');
      return;
    }
    if (!date) {
      setError('Please select your date of birth.');
      return;
    }
    if (!time) {
      setError('Please enter your time of birth.');
      return;
    }
    if (!geocoded) {
      setError('Please resolve your birth place coordinates first by clicking "Find Coordinates".');
      return;
    }

    // Date validations
    const birthDate = new Date(`${date}T${time}`);
    if (birthDate > new Date()) {
      setError('Birth date and time cannot be in the future.');
      return;
    }

    onSave({
      name: name.trim(),
      date,
      time,
      place,
      latitude: geocoded.lat,
      longitude: geocoded.lng,
      timezone: geocoded.timezone,
      display_name: geocoded.display_name,
      sidereal,
    });
  };

  return (
    <div className="glass-panel form-card" style={{ padding: '2rem', maxWidth: '500px', margin: '0 auto' }}>
      <h3 className="gold-glow" style={{ color: 'var(--color-gold)', marginBottom: '1.5rem', textAlign: 'center', fontSize: '1.5rem' }}>
        Create Natal Chart
      </h3>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>First Name / Identifier</label>
          <input
            type="text"
            className="gold-border-glow"
            placeholder="e.g. Aradhya"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{
              padding: '0.75rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-card-border)',
              background: 'rgba(5, 6, 20, 0.6)',
              color: 'var(--color-text-main)',
              fontSize: '1rem',
            }}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            <label style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Date of Birth</label>
            <input
              type="date"
              className="gold-border-glow"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              style={{
                padding: '0.75rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-card-border)',
                background: 'rgba(5, 6, 20, 0.6)',
                color: 'var(--color-text-main)',
                fontSize: '1rem',
              }}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            <label style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Time of Birth</label>
            <input
              type="time"
              className="gold-border-glow"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              style={{
                padding: '0.75rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-card-border)',
                background: 'rgba(5, 6, 20, 0.6)',
                color: 'var(--color-text-main)',
                fontSize: '1rem',
              }}
            />
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Place of Birth</label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              className="gold-border-glow"
              placeholder="e.g. New Delhi, London, Tokyo"
              value={place}
              onChange={(e) => {
                setPlace(e.target.value);
                setSuggestions([]);
              }}
              style={{
                flex: 1,
                padding: '0.75rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-card-border)',
                background: 'rgba(5, 6, 20, 0.6)',
                color: 'var(--color-text-main)',
                fontSize: '1rem',
              }}
            />
            <button
              onClick={handleGeocode}
              disabled={loading}
              style={{
                padding: '0 1rem',
                background: 'rgba(212, 175, 55, 0.15)',
                border: '1px solid var(--color-gold)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-gold-light)',
                cursor: 'pointer',
                fontWeight: 500,
                fontSize: '0.9rem',
                transition: 'all 0.2s',
              }}
              onMouseOver={(e) => (e.currentTarget.style.background = 'rgba(212, 175, 55, 0.3)')}
              onMouseOut={(e) => (e.currentTarget.style.background = 'rgba(212, 175, 55, 0.15)')}
            >
              {loading ? 'Finding...' : 'Resolve'}
            </button>
          </div>
          {geocoded && (
            <div style={{ fontSize: '0.8rem', color: 'var(--color-gold-light)', marginTop: '0.2rem' }}>
              ✓ Lat: {geocoded.lat.toFixed(4)}, Lng: {geocoded.lng.toFixed(4)} | Timezone: {geocoded.timezone}
            </div>
          )}

          {suggestions.length > 1 && (
            <div
              style={{
                marginTop: '0.75rem',
                background: 'rgba(5, 6, 20, 0.85)',
                border: '1px solid var(--color-card-border)',
                borderRadius: 'var(--radius-md)',
                padding: '0.6rem',
                maxHeight: '160px',
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.4rem',
                boxShadow: 'inset 0 0 10px rgba(0, 0, 0, 0.5)'
              }}
            >
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: '0.2rem', paddingLeft: '0.4rem', fontWeight: 500 }}>
                Multiple matches found. Select location:
              </div>
              {suggestions.map((item, idx) => {
                const isSelected = geocoded?.lat === item.lat && geocoded?.lng === item.lng;
                return (
                  <button
                    key={idx}
                    onClick={(e) => {
                      e.preventDefault();
                      setGeocoded(item);
                      setPlace(item.display_name);
                    }}
                    style={{
                      textAlign: 'left',
                      padding: '0.45rem 0.6rem',
                      background: isSelected ? 'rgba(212, 175, 55, 0.18)' : 'transparent',
                      border: isSelected ? '1px solid var(--color-gold)' : '1px solid transparent',
                      borderRadius: 'var(--radius-sm)',
                      color: isSelected ? 'var(--color-gold-light)' : 'var(--color-text-main)',
                      fontSize: '0.8rem',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      outline: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.3rem'
                    }}
                    onMouseOver={(e) => {
                      if (!isSelected) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                    }}
                    onMouseOut={(e) => {
                      if (!isSelected) e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <span>📍</span>
                    <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                      {item.display_name} (Lat: {item.lat.toFixed(2)}, Lng: {item.lng.toFixed(2)})
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: '0.25rem 0' }}>
          <input
            type="checkbox"
            id="sidereal"
            checked={sidereal}
            onChange={(e) => setSidereal(e.target.checked)}
            style={{
              width: '18px',
              height: '18px',
              cursor: 'pointer',
              accentColor: 'var(--color-gold)',
            }}
          />
          <label htmlFor="sidereal" style={{ fontSize: '0.9rem', color: 'var(--color-text-main)', cursor: 'pointer' }}>
            Use Vedic Sidereal Calculations (Lahiri Ayanamsa)
          </label>
        </div>

        {error && (
          <div style={{ color: '#ff6b6b', fontSize: '0.85rem', textAlign: 'center', background: 'rgba(255, 107, 107, 0.1)', padding: '0.5rem', borderRadius: 'var(--radius-md)' }}>
            ⚠️ {error}
          </div>
        )}

        <button
          type="submit"
          className="pulse-indicator"
          style={{
            padding: '0.9rem',
            background: 'var(--color-gold)',
            color: 'var(--bg-deep)',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            fontSize: '1rem',
            fontWeight: '600',
            cursor: 'pointer',
            marginTop: '0.5rem',
            transition: 'all 0.3s',
            boxShadow: '0 0 15px var(--color-gold-glow)',
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.background = 'var(--color-gold-light)';
            e.currentTarget.style.boxShadow = '0 0 25px var(--color-gold)';
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.background = 'var(--color-gold)';
            e.currentTarget.style.boxShadow = '0 0 15px var(--color-gold-glow)';
          }}
        >
          Generate Chart & Start Companion
        </button>
      </form>
    </div>
  );
};
