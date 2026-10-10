import Image from "next/image";
import { AuthStatus } from "../components/auth-status";

export default function Home() {
  return (
    <main className="shell" data-brand="fsp-talent">
      <header className="topbar">
        <div className="brand">
          <Image className="brandLogo" src="/brand/logo_white1.png" alt="ФСП" width={50} height={72} priority />
          <span className="brandName">FSP <b>TALENT</b></span>
        </div>
        <span className="badge">EVIDENCE-FIRST DISCOVERY</span>
      </header>

      <section className="hero">
        <div className="heroText">
          <p className="eyebrow">ФСП TALENT · VERIFIED ENGINEERING EVIDENCE</p>
          <h1>Проверенные навыки.<br />Точный подбор.</h1>
          <p className="lead">
            Работодатель находит специалистов по подтверждённым навыкам и сразу видит объяснимое
            соответствие задаче. Кандидат управляет профилем, доказательствами и каждым приглашением.
          </p>
          <nav className="actions" aria-label="Основные разделы">
            <a className="primary" href="#principles">Как работает FSP Talent</a>
            <a className="secondary" href="#proof">Пример доказательств</a>
          </nav>
          <AuthStatus />
        </div>
        <div className="proofCard" id="proof" aria-label="Пример подтверждённого профиля">
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

      <section className="principles" id="principles" aria-label="Принципы FSP Talent">
        <article><b>01</b><h3>Assessment</h3><p>Comparable, parameterized, auditable.</p></article>
        <article><b>02</b><h3>Matching</h3><p>Explainable ranking by verified evidence.</p></article>
        <article><b>03</b><h3>Invitation</h3><p>Employer initiates with salary visible upfront.</p></article>
      </section>
    </main>
  );
}
