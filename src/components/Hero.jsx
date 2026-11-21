import Icons from './Icons.jsx';

export default function Hero() {
  const scrollTo = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <section id="hero" className="section" aria-labelledby="hero-title">
      <div className="inner">
        <div className="hero-copy" data-reveal>
          <p className="hero-kicker">URL phishing checker</p>
          <h1 className="hero-title" id="hero-title">
            Know the link
            <span>before you open it.</span>
          </h1>
          <div className="hero-actions">
            <button className="btn btn-primary" type="button" onClick={() => scrollTo('scan')}>
              <Icons name="arrow" size={16} />
              Check a URL
            </button>
            <button className="btn btn-quiet" type="button" onClick={() => scrollTo('how-to')}>
              How it works
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
