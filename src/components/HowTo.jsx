const STEPS = ['Paste', 'Scan', 'Verify'];

export default function HowTo() {
  return (
    <section id="how-to" className="section" aria-labelledby="how-to-title">
      <div className="inner">
        <div className="section-head" data-reveal>
          <h2 className="section-title" id="how-to-title">How it works</h2>
        </div>

        <div className="steps" data-reveal>
          {STEPS.map((word) => (
            <article className="step" key={word}>
              <h3>{word}</h3>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
