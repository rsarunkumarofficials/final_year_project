export default function QuoteFooter() {
  return (
    <>
      <section id="quote" className="section" aria-labelledby="quote-title">
        <div className="inner">
          <div className="section-head">
            <h2 className="section-title" id="quote-title">About</h2>
          </div>
          <blockquote className="quote" data-reveal>
            <p>A number you can reproduce beats a number you can only admire.</p>
            <footer>URL CHECKER</footer>
          </blockquote>
        </div>
      </section>

      <footer id="footer" className="footer">
        <div className="footer-inner">
          <div className="footer-grid">
            <div>
              <p className="footer-head">Sections</p>
              <nav className="footer-links" aria-label="Footer">
                <a href="#hero">Overview</a>
                <a href="#how-to">How it works</a>
                <a href="#scan">Check a URL</a>
                <a href="#output">Report</a>
                <a href="#quote">About</a>
              </nav>
            </div>
          </div>
          <p className="footer-base">Developer RS ARUNKUMAR</p>
        </div>
      </footer>
    </>
  );
}
