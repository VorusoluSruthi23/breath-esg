import { useState } from 'react';
import { ingestSAP, ingestUtility, ingestTravel, getBatches } from '../api';
import { useEffect } from 'react';

const SOURCES = [
  {
    id: 'sap',
    label: 'SAP Fuel & Procurement',
    scope: 'Scope 1',
    description: 'Flat-file CSV export from SAP ALV grid (MB52, ME2M or custom Z-report). Handles German headers, decimal formats, and plant codes.',
    accepts: '.csv',
    fn: ingestSAP,
    example: 'sap_fuel_export.csv',
    color: 'var(--green)',
  },
  {
    id: 'utility',
    label: 'Utility Electricity',
    scope: 'Scope 2',
    description: 'Portal CSV download from utility provider. Handles non-calendar billing periods, multiple meters, and region-specific grid factors.',
    accepts: '.csv',
    fn: ingestUtility,
    example: 'utility_electricity.csv',
    color: 'var(--blue)',
  },
  {
    id: 'travel',
    label: 'Corporate Travel',
    scope: 'Scope 3',
    description: 'JSON export from Navan/Concur TMC platforms, or CSV export. Computes flight distances from airport codes (IATA) using haversine formula.',
    accepts: '.json,.csv',
    fn: ingestTravel,
    example: 'corporate_travel.json',
    color: 'var(--amber)',
  },
];

const UploadCard = ({ source, tenant }) => {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);

  const doUpload = async (f) => {
    if (!f) return;
    setLoading(true); setResult(null); setError('');
    try {
      const { data } = await source.fn(f, tenant);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.error || 'Upload failed');
    } finally { setLoading(false); }
  };

  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 8, padding: 24,
      borderTop: `2px solid ${source.color}`,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{source.label}</div>
          <div style={{ fontSize: 11, color: source.color, fontFamily: 'var(--mono)', marginTop: 2 }}>{source.scope}</div>
        </div>
      </div>

      <p style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 16, lineHeight: 1.6 }}>
        {source.description}
      </p>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => {
          e.preventDefault(); setDragging(false);
          const f = e.dataTransfer.files[0];
          if (f) { setFile(f); doUpload(f); }
        }}
        onClick={() => document.getElementById(`file-${source.id}`).click()}
        style={{
          border: `1px dashed ${dragging ? source.color : 'var(--border)'}`,
          borderRadius: 6, padding: '20px', textAlign: 'center', cursor: 'pointer',
          background: dragging ? `${source.color}08` : 'var(--surface2)',
          transition: 'all 0.2s', marginBottom: 12,
        }}
      >
        <input
          id={`file-${source.id}`} type="file" accept={source.accepts} style={{ display: 'none' }}
          onChange={e => { const f = e.target.files[0]; if (f) { setFile(f); doUpload(f); } }}
        />
        <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>
          {file ? (
            <span style={{ color: 'var(--text)' }}>📄 {file.name}</span>
          ) : (
            <span>Drop {source.accepts} file here or <span style={{ color: source.color }}>browse</span></span>
          )}
        </div>
        <div style={{ fontSize: 10, color: 'var(--text-faint)', marginTop: 4, fontFamily: 'var(--mono)' }}>
          e.g. {source.example}
        </div>
      </div>

      {loading && (
        <div style={{ fontSize: 12, color: 'var(--text-dim)', textAlign: 'center', padding: '8px 0' }}>
          Parsing and ingesting…
        </div>
      )}

      {result && (
        <div style={{ background: 'var(--green-muted)', border: '1px solid var(--green)33', borderRadius: 6, padding: 12 }}>
          <div style={{ fontSize: 11, color: 'var(--green)', fontWeight: 600, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>
            ✓ Ingested
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {[
              ['Total rows', result.total],
              ['Parsed OK', result.successful],
              ['Flagged', result.flagged],
              ['Failed', result.failed],
            ].map(([k, v]) => (
              <div key={k} style={{ fontSize: 12 }}>
                <span style={{ color: 'var(--text-dim)' }}>{k}: </span>
                <span style={{ fontFamily: 'var(--mono)', fontWeight: 600 }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div style={{ background: 'var(--red-muted)', border: '1px solid var(--red)33', borderRadius: 6, padding: 12, fontSize: 12, color: 'var(--red)' }}>
          {error}
        </div>
      )}
    </div>
  );
};

export default function Ingest({ tenant }) {
  const [batches, setBatches] = useState([]);

  useEffect(() => {
    getBatches().then(r => setBatches(r.data)).catch(() => {});
  }, []);

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600 }}>Ingest Data</h1>
        <p style={{ color: 'var(--text-dim)', fontSize: 13, marginTop: 4 }}>
          Upload source files — they'll be parsed, normalized, and queued for review
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 32 }}>
        {SOURCES.map(s => <UploadCard key={s.id} source={s} tenant={tenant} />)}
      </div>

      {/* Recent batches */}
      {batches.length > 0 && (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: 24 }}>
          <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: 1 }}>
            Recent Ingestion Batches
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Source', 'File', 'Uploaded', 'Total', 'OK', 'Flagged', 'Failed', 'Status'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '8px 12px', fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {batches.map(b => (
                <tr key={b.id} style={{ borderBottom: '1px solid var(--border)', fontSize: 12 }}>
                  <td style={{ padding: '10px 12px', color: 'var(--text-dim)' }}>{b.source_type?.replace(/_/g, ' ')}</td>
                  <td style={{ padding: '10px 12px', fontFamily: 'var(--mono)', fontSize: 11 }}>{b.original_filename || '—'}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-dim)', fontFamily: 'var(--mono)', fontSize: 11 }}>
                    {new Date(b.uploaded_at).toLocaleDateString()}
                  </td>
                  <td style={{ padding: '10px 12px', fontFamily: 'var(--mono)' }}>{b.total_rows}</td>
                  <td style={{ padding: '10px 12px', fontFamily: 'var(--mono)', color: 'var(--green)' }}>{b.successful_rows}</td>
                  <td style={{ padding: '10px 12px', fontFamily: 'var(--mono)', color: 'var(--amber)' }}>{b.flagged_rows}</td>
                  <td style={{ padding: '10px 12px', fontFamily: 'var(--mono)', color: 'var(--red)' }}>{b.failed_rows}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ fontSize: 10, color: b.status === 'completed' ? 'var(--green)' : 'var(--amber)', fontFamily: 'var(--mono)' }}>
                      {b.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
