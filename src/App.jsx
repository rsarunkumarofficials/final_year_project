import { useCallback, useEffect, useRef, useState } from 'react';
import Hero from './components/Hero.jsx';
import HowTo from './components/HowTo.jsx';
import Scanner from './components/Scanner.jsx';
import ResultCard from './components/ResultCard.jsx';
import QuoteFooter from './components/QuoteFooter.jsx';
import { createSessionId, normalizeUrl, predictUrl } from './lib/api.js';
import { useReducedMotion } from './hooks/useReducedMotion.js';
import { useReveal } from './hooks/useReveal.js';

const NAV = [
  { id: 'hero', label: 'Overview', short: 'Home' },
  { id: 'how-to', label: 'Method', short: 'Method' },
  { id: 'scan', label: 'Check a URL', short: 'Check' },
  { id: 'output', label: 'Report', short: 'Report' },
  { id: 'quote', label: 'About', short: 'About' },
];

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <span className="brand-slashes">//</span>
    </span>
  );
}

export default function App() {
  const reduced = useReducedMotion();
  const [active, setActive] = useState('hero');
  const [input, setInput] = useState('');
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [scannedUrl, setScannedUrl] = useState('');
  const abortRef = useRef(null);
  const sessionId = useRef(createSessionId()).current;

  useReveal(reduced);

  useEffect(() => () => abortRef.current?.abort(), []);

  useEffect(() => {
    if (!result) return undefined;
    const frame = requestAnimationFrame(() => {
      document.getElementById('output')?.scrollIntoView({
        behavior: 'auto',
        block: 'start',
      });
      document.getElementById('output-heading')?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [result]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActive(visible.target.id);
      },
      { rootMargin: '-40% 0px -40% 0px', threshold: [0, 0.1, 0.5] },
    );

    NAV.forEach(({ id }) => {
      const node = document.getElementById(id);
      if (node) observer.observe(node);
    });
    return () => observer.disconnect();
  }, []);

  const scrollTo = useCallback(
    (id) => {
      document.getElementById(id)?.scrollIntoView({
        behavior: reduced ? 'auto' : 'smooth',
        block: 'start',
      });
    },
    [reduced],
  );

  const runScan = useCallback(
    async (rawValue) => {
      // Cancel any in-flight scan first: a stale success must never overwrite
      // a newer validation error or a newer result.
      abortRef.current?.abort();
      const controller = new AbortController();

      const url = normalizeUrl(rawValue);
      if (!url) {
        setError('Enter a valid http(s) URL or a bare domain such as example.com.');
        setStatus('error');
        return;
      }

      setInput(url);
      setError('');
      setStatus('loading');
      abortRef.current = controller;

      try {
        const payload = await predictUrl(url, sessionId, controller.signal);
        if (controller.signal.aborted) return;
        setStatus('success');
        setResult(payload);
        setScannedUrl(url);
      } catch (requestError) {
        if (controller.signal.aborted || requestError.name === 'AbortError') return;
        setError(requestError.message || 'The scan could not be completed.');
        setStatus('error');
      }
    },
    [sessionId],
  );

  return (
    <div className="app">
      <a className="skip-link" href="#scan">
        Skip to scanner
      </a>

      <aside className="rail" aria-label="Sections">
        <div className="rail-inner">
          <button className="brand" type="button" onClick={() => scrollTo('hero')}>
            <BrandMark />
            <span className="brand-name">URL CHECKER</span>
          </button>

          <nav className="rail-nav">
            {NAV.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`rail-link ${active === item.id ? 'is-active' : ''}`}
                onClick={() => scrollTo(item.id)}
                aria-current={active === item.id ? 'true' : undefined}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      </aside>

      <div className="mobile-bar">
        <button className="mobile-brand" type="button" onClick={() => scrollTo('hero')}>
          <BrandMark />
          <span className="brand-name">URL CHECKER</span>
        </button>
        <nav className="mobile-links" aria-label="Sections">
          {NAV.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className={active === item.id ? 'is-active' : ''}
              onClick={(event) => {
                event.preventDefault();
                scrollTo(item.id);
              }}
            >
              {item.short}
            </a>
          ))}
        </nav>
      </div>

      <div className="workspace">
        <main id="main">
          <Hero />

          <HowTo />

          <Scanner
            input={input}
            onInput={setInput}
            status={status}
            error={error}
            onSubmit={(event) => {
              event.preventDefault();
              runScan(input);
            }}
            onQuickTest={runScan}
          />

          <section id="output" className="section" aria-labelledby="output-title">
            <div className="inner">
              <div className="section-head">
                <h2 className="section-title" id="output-title">Analysis report</h2>
              </div>
              <div aria-live="polite">
                <ResultCard result={result} scannedUrl={scannedUrl} />
              </div>
            </div>
          </section>

          <QuoteFooter />
        </main>
      </div>
    </div>
  );
}
