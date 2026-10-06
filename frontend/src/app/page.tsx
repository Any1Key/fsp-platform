import Image from "next/image";
import { AuthStatus } from "../components/auth-status";

export default function Home() {
  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <Image src="/brand/logo_white1.png" alt="ФСП" width={50} height={72} priority />
          <span>FSP TALENT</span>
        </div>
        <span className="badge">AUTONOMOUS BUILD READY</span>
      </header>

      <section className="hero">
        <div className="heroText">
          <p className="eyebrow">ФЕДЕРАЦИЯ СПОРТИВНОГО ПРОГРАММИРОВАНИЯ</p>
          <h1>Проверенные навыки.<br />Точный подбор.</h1>
          <p className="lead">
            Стартовый каркас готов. Codex превратит его в полноценную reverse-recruitment платформу
            по матрице требований.
          </p>
          <div className="actions">
            <span className="primary">Candidate → verified profile</span>
            <span className="secondary">Employer → talent discovery</span>
          </div>
          <AuthStatus />
        </div>
        <div className="proofCard">
          <p className="cardLabel">VERIFIED PROFILE</p>
          <h2>Backend · Middle</h2>
          <div className="metric"><span>Assessment</span><strong>87</strong></div>
          <div className="bar"><i style={{width: "87%"}} /></div>
          <div className="chips">
            <span>✓ Python</span><span>✓ FastAPI</span><span>✓ PostgreSQL</span>
          </div>
          <div className="fspLine">
            <span className="dot" /> FSP evidence becomes a bounded verified signal
          </div>
        </div>
      </section>

      <section className="principles">
        <article><b>01</b><h3>Assessment</h3><p>Comparable, parameterized, auditable.</p></article>
        <article><b>02</b><h3>Matching</h3><p>Explainable ranking by verified evidence.</p></article>
        <article><b>03</b><h3>Invitation</h3><p>Employer initiates with salary visible upfront.</p></article>
      </section>
    </main>
  );
}
