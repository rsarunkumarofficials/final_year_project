import Icons from './Icons.jsx';
import { MODEL_FACTS } from '../data/facts.js';

function parseSignal(signal) {
  const text = String(signal ?? '').trim();
  const match = text.match(/^'([^']+)'\s*\(([+-]\d+(?:\.\d+)?)\)$/);
  if (!match) return { term: text, value: null };
  return { term: match[1], value: Number(match[2]) };
}

function deriveAddressFacts(raw) {
  const value = String(raw || '').trim();
  try {
    const parsed = new URL(value);
    const host = parsed.hostname;
    const labels = host.split('.');
    const keys = [...parsed.searchParams.keys()].map((key) => key.toLowerCase());
    return {
      scheme: parsed.protocol.replace(':', '') || '—',
      host,
      path: parsed.pathname || '/',
      query: parsed.search ? 'present' : 'none',
      port: parsed.port || 'default',
      length: value.length,
      labels: labels.length,
      subdomains: Math.max(0, labels.length - 2),
      hyphens: (host.match(/-/g) || []).length,
      digits: (host.match(/\d/g) || []).length,
      ipHost: /^(\d{1,3}\.){3}\d{1,3}$/.test(host) || host.includes(':') ? 'yes' : 'no',
      punycode: labels.some((label) => label.startsWith('xn--')) ? 'yes' : 'no',
      redirectHint: keys.some((key) =>
        ['redirect', 'url', 'target', 'to', 'next', 'goto', 'dest'].includes(key),
      )
        ? 'yes'
        : 'no',
      credentials: parsed.username || parsed.password ? 'yes' : 'no',
    };
  } catch {
    return null;
  }
}

function FactRows({ rows }) {
  return (
    <dl className="detail-rows">
      {rows.map(([label, value]) => (
        <div className="detail-row" key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function EmptyResult() {
  return (
    <div className="empty">
      <div className="empty-glyph" aria-hidden="true">
        <Icons name="link" size={26} />
      </div>
      <h3>No report yet</h3>
      <a className="btn btn-quiet" href="#scan">Check a link</a>
    </div>
  );
}

export default function ResultCard({ result, scannedUrl }) {
  if (!result) return <EmptyResult />;

  const ml = result.ml || {};
  const model = result.model || {};
  const isPhishing = ml.is_phishing === true || ml.verdict === 'PHISHING';
  const verdict = isPhishing ? 'PHISHING' : 'SAFE';
  const probability = Number(ml.phishing_probability ?? 0);
  const riskPercent = Math.max(0, Math.min(100, probability * 100));
  const confidence = Number(
    ml.confidence ?? Math.max(probability, 1 - probability) * 100,
  );
  const threshold = typeof ml.threshold === 'number' ? ml.threshold.toFixed(2) : '—';
  const signals = Array.isArray(ml.signals) ? ml.signals : [];
  const facts = deriveAddressFacts(scannedUrl);
  const weights = model.weights || ml.ensemble_weights || {};
  const weightText = Object.keys(weights).length
    ? Object.entries(weights)
        .map(([name, value]) => `${Number(value).toFixed(2)} ${name}`)
        .join(' + ')
    : MODEL_FACTS.weights;
  const accuracy =
    typeof model.accuracy === 'number' ? model.accuracy : MODEL_FACTS.accuracy;
  const modelName = model.model || MODEL_FACTS.model;
  const tone = isPhishing ? 'risk' : 'safe';

  return (
    <article className={`report is-${tone}`} aria-label="Analysis report">
      <div className="report-status">
        <b>Verdict</b>
        <span>{modelName}</span>
      </div>

      <div className={`verdict is-${tone}`}>
        <div className="verdict-main">
          <h3 id="output-heading" className="verdict-word" tabIndex={-1}>
            {verdict}
          </h3>
          <div className="verdict-url">{scannedUrl || 'Scanned address'}</div>
        </div>
        <div className="verdict-score">
          <b>{riskPercent.toFixed(2)}%</b>
          <span>phishing probability</span>
        </div>
      </div>

      <div className="risk-strip">
        <div className="risk-bar" aria-hidden="true">
          <span style={{ width: `${riskPercent}%` }} />
        </div>
        <div className="risk-values">
          <div>
            <span>Probability</span>
            <b>{riskPercent.toFixed(2)}%</b>
          </div>
          <div>
            <span>Confidence</span>
            <b>{Number.isFinite(confidence) ? confidence.toFixed(1) : '—'}%</b>
          </div>
          <div>
            <span>Decision threshold</span>
            <b>{threshold}</b>
          </div>
        </div>
      </div>

      {facts && (
        <>
          <div className="detail-grid">
            <section className="detail-card">
              <h4>Address structure</h4>
              <FactRows
                rows={[
                  ['Scheme', facts.scheme],
                  ['Host', facts.host],
                  ['Path', facts.path],
                  ['Query', facts.query],
                  ['Port', facts.port],
                  ['Length', `${facts.length} chars`],
                ]}
              />
            </section>

            <section className="detail-card">
              <h4>Domain features</h4>
              <FactRows
                rows={[
                  ['Host labels', facts.labels],
                  ['Subdomains', facts.subdomains],
                  ['Hyphens', facts.hyphens],
                  ['Digits', facts.digits],
                  ['IP host', facts.ipHost],
                  ['Punycode', facts.punycode],
                ]}
              />
            </section>

            <section className="detail-card">
              <h4>Heuristics</h4>
              <FactRows
                rows={[
                  ['Redirect-style key', facts.redirectHint],
                  ['Credentials in URL', facts.credentials],
                  ['Transport', facts.scheme === 'https' ? 'HTTPS requested' : 'HTTP requested'],
                  ['Long address', facts.length > 75 ? 'yes' : 'no'],
                  ['Signals found', signals.length],
                ]}
              />
            </section>
          </div>
          <p className="detail-note">
            Address facts are read from the submitted URL. Certificate validity and
            live redirects are not verified here.
          </p>
        </>
      )}

      <div className="report-block">
        <div className="block-head">
          <b>Character signals</b>
          <span>n-gram contribution to the score</span>
        </div>
        {signals.length ? (
          <ul className="signal-list">
            {signals.map((signal, index) => {
              const { term, value } = parseSignal(signal);
              const weightClass =
                value === null ? 'is-neutral' : value > 0 ? 'is-risk' : 'is-guard';
              return (
                <li key={`${term}-${index}`}>
                  <span className="signal-no">{String(index + 1).padStart(2, '0')}</span>
                  <span className="signal-term">{term}</span>
                  <b className={`signal-weight ${weightClass}`}>
                    {value === null
                      ? '—'
                      : `${value > 0 ? '+' : ''}${value.toFixed(2)}`}
                  </b>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="signal-empty">No dominant character n-gram was extracted for this address.</p>
        )}
      </div>

      <div className="report-block">
        <details className="context">
          <summary>
            <span>Supporting context</span>
            <small>scraper / language model · not authoritative</small>
          </summary>
          <p>
            {result.response || 'No supporting context was returned for this address.'}
          </p>
        </details>
      </div>

      <dl className="provenance">
        <div>
          <dt>Model</dt>
          <dd>{modelName}</dd>
        </div>
        <div>
          <dt>Weights</dt>
          <dd>{weightText}</dd>
        </div>
        <div>
          <dt>Held-out accuracy</dt>
          <dd>{accuracy.toFixed(2)}%</dd>
        </div>
        <div>
          <dt>Training rows</dt>
          <dd>{MODEL_FACTS.trainingRows.toLocaleString('en-US')}</dd>
        </div>
        <div>
          <dt>Test rows</dt>
          <dd>{MODEL_FACTS.testRows.toLocaleString('en-US')}</dd>
        </div>
        <div>
          <dt>Method</dt>
          <dd>classical ML · not deep learning</dd>
        </div>
      </dl>
    </article>
  );
}
