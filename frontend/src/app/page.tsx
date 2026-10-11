import Image from "next/image";
import { AuthStatus } from "../components/auth-status";

export default function Home() {
  return (
    <main className="shell" data-brand="fsp-talent">
      <a className="skipLink" href="#main-content">Перейти к содержимому</a>
      <header className="topbar">
        <div className="brand">
          <Image className="brandLogo" src="/brand/logo_white1.png" alt="ФСП" width={50} height={72} priority />
          <span className="brandName">FSP <b>TALENT</b></span>
        </div>
        <span className="badge">ПОДБОР ПО ПОДТВЕРЖДЁННЫМ НАВЫКАМ</span>
      </header>

      <section className="hero" id="main-content" tabIndex={-1}>
        <div className="heroBrandVisual" aria-hidden="true">
          <Image className="heroBrandFace" src="/brand/official/face1.png" alt="" width={420} height={420} priority />
          <Image className="heroBrandLine" src="/brand/official/lineline1.png" alt="" width={360} height={250} priority />
        </div>
        <div className="heroText">
          <p className="eyebrow">FSP TALENT · ПЛАТФОРМА ПРОФЕССИОНАЛЬНОГО ПОДБОРА</p>
          <h1>Проверенные навыки.<br />Точный подбор.</h1>
          <p className="lead">
            Работодатель находит специалистов по подтверждённым навыкам и сразу видит объяснимое
            соответствие задаче. Кандидат управляет профилем навыков и каждым приглашением.
          </p>
          <nav className="actions" aria-label="Основные разделы">
            <a className="primary" href="#principles">Как работает FSP Talent</a>
            <a className="secondary" href="#proof">Пример профиля навыков</a>
          </nav>
          <AuthStatus />
        </div>
        <div className="proofCard" id="proof" aria-label="Пример подтверждённого профиля">
          <p className="cardLabel">ПОДТВЕРЖДЁННЫЙ ПРОФИЛЬ</p>
          <h2>Backend · Middle</h2>
          <div className="metric"><span>Оценка навыков</span><strong>87</strong></div>
          <div className="bar"><i style={{width: "87%"}} /></div>
          <div className="chips">
            <span>✓ Python</span><span>✓ FastAPI</span><span>✓ PostgreSQL</span>
          </div>
          <div className="fspLine">
            <span className="dot" /> Подтверждённые данные помогают принимать решения
          </div>
        </div>
      </section>

      <section className="principles" id="principles" aria-label="Как работает FSP Talent">
        <article><b>01</b><h3>Оценка навыков</h3><p>Сравнимые задания и понятный результат.</p></article>
        <article><b>02</b><h3>Подбор</h3><p>Рейтинг кандидатов на основе подтверждённых данных.</p></article>
        <article><b>03</b><h3>Приглашение</h3><p>Работодатель сразу указывает условия предложения.</p></article>
      </section>
    </main>
  );
}
