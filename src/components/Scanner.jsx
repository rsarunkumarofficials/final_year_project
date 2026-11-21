import Icons from './Icons.jsx';
import { QUICK_TESTS } from '../data/facts.js';

export default function Scanner({
  input,
  onInput,
  status,
  error,
  onSubmit,
  onQuickTest,
}) {
  const busy = status === 'loading';

  return (
    <section id="scan" className="section">
      <div className="inner">
        <form className="console" onSubmit={onSubmit} aria-busy={busy} data-reveal>
          <div className="console-body">
            <div className="scan-field">
              <Icons name="link" size={17} />
              <input
                id="url-input"
                className="url-input"
                type="text"
                inputMode="url"
                autoComplete="off"
                spellCheck="false"
                placeholder="Paste a URL — https://example.com"
                aria-label="URL to check"
                value={input}
                onChange={(event) => onInput(event.target.value)}
              />
              {input && !busy && (
                <button
                  className="clear-btn"
                  type="button"
                  onClick={() => onInput('')}
                  aria-label="Clear URL"
                >
                  <Icons name="close" size={11} />
                </button>
              )}
            </div>

            {error && (
              <p className="field-error" role="alert">{error}</p>
            )}

            <div className="scan-actions">
              <button className="btn btn-primary" type="submit" disabled={busy}>
                {busy ? (
                  <span className="spinner" aria-hidden="true" />
                ) : (
                  <Icons name="check" size={16} />
                )}
                <span>{busy ? 'Checking…' : 'Check link'}</span>
              </button>

              <div className="samples">
                {QUICK_TESTS.map((test) => (
                  <button
                    key={test.url}
                    className={`chip ${test.tone === 'safe' ? 'is-safe' : 'is-risk'}`}
                    type="button"
                    onClick={() => onQuickTest(test.url)}
                    disabled={busy}
                  >
                    <i aria-hidden="true" />
                    {test.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </form>
      </div>
    </section>
  );
}
