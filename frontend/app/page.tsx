const highlights = [
  {
    title: "Frontend template",
    description: "A small Next.js app that can grow once the API layer is ready.",
  },
  {
    title: "Backend pending",
    description: "Endpoints, data fetching, and auth can be wired in later without changing the shell.",
  },
  {
    title: "Clean starting point",
    description: "Light styling, simple structure, and a single landing page for now.",
  },
];

export default function Home() {
  return (
    <main>
      <section className="hero">
        <p className="kicker">Oxbow frontend</p>
        <h1>Simple Next.js starter for the future app.</h1>
        <p className="lead">
          This is a temporary template. It gives the project a working React and
          Next.js frontend now, while the backend contracts are still being
          designed.
        </p>

        <div className="grid">
          {highlights.map((item) => (
            <article className="card" key={item.title}>
              <h2>{item.title}</h2>
              <p>{item.description}</p>
            </article>
          ))}
        </div>

        <div className="actions">
          <a className="button primary" href="#">
            Backend coming soon
          </a>
          <a className="button secondary" href="#">
            Update this template later
          </a>
        </div>

        <p className="note">
          Next step: connect this shell to real data once the backend is ready.
        </p>
      </section>
    </main>
  );
}
