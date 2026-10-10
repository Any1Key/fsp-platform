"use client";

import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState, UnconfirmedGradeBadge } from "./ui-state";

type Evidence = {
  id: string;
  source: "platform_assessment" | "fsp" | "profile";
  status: "verified" | "unconfirmed" | "declared";
  title: string;
  skills: string[];
  score: number | null;
  confidence: number;
  measured_at: string | null;
  freshness: "fresh" | "aging" | "stale" | "future" | "not_available";
  provenance: string;
  details: string;
};

type Passport = {
  profile: { display_name: string | null; headline: string | null };
  status: "not_started" | "verified" | "unconfirmed";
  category: {
    specialization: string;
    grade: string | null;
    declared_grade: string;
    grade_state: "verified" | "not_confirmed";
    score: number;
    assessed_at: string;
    freshness: "fresh" | "aging" | "stale";
  } | null;
  fsp: {
    status: "not_linked" | "linked";
    history_status: "no_history" | "has_history";
    achievement_count: number;
  };
  freshness: {
    fresh: number;
    aging: number;
    stale: number;
    future: number;
    not_available: number;
  };
  retest_available_at: string | null;
  evidence: Evidence[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const sourceLabels: Record<Evidence["source"], string> = {
  platform_assessment: "Проверка платформы",
  fsp: "FSP evidence",
  profile: "Заявлено в профиле",
};

const freshnessLabels: Record<Evidence["freshness"], string> = {
  fresh: "свежее",
  aging: "актуальность снижается",
  stale: "устарело, не удалено",
  future: "дата требует проверки",
  not_available: "без даты проверки",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function passportStatus(passport: Passport) {
  if (passport.status === "verified") return "Паспорт подтверждён";
  if (passport.status === "unconfirmed") return "Уровень пока не подтверждён";
  return "Паспорт ещё формируется";
}

export function CandidateSkillPassport({ token, refreshKey = 0 }: { token: string; refreshKey?: number }) {
  const [passport, setPassport] = useState<Passport | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let active = true;
    setState("loading");
    fetch(`${apiUrl}/api/v1/candidate/skill-passport`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("skill_passport_unavailable");
        return (await response.json()) as Passport;
      })
      .then((value) => {
        if (!active) return;
        setPassport(value);
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });

    return () => {
      active = false;
    };
  }, [token, refreshKey]);

  if (state === "loading") {
    return <section className="passportPanel muted"><LoadingState title="Собираем твой Verified Skill Passport…" description="Сверяем assessment, профиль и FSP evidence." /></section>;
  }
  if (state === "error" || !passport) {
    return <section className="passportPanel error"><ErrorState title="Не удалось загрузить Verified Skill Passport" description="Обнови страницу и попробуй ещё раз." /></section>;
  }

  return (
    <section className="passportPanel" aria-labelledby="passport-title">
      <div className="passportHeading">
        <div>
          <span className="authLabel">VERIFIED SKILL PASSPORT</span>
          <h2 id="passport-title">Профиль доказательств</h2>
          <p>Работодатели видят проверяемые сигналы отдельно от твоих заявлений.</p>
        </div>
        <div className={`passportStatus ${passport.status}`}>
          <i aria-hidden="true" />
          {passportStatus(passport)}
        </div>
      </div>

      {passport.category ? (
        <div className="passportCategory">
          <div>
            <span>ТЕКУЩАЯ КАТЕГОРИЯ</span>
            <strong>{passport.category.specialization}</strong>
            <small>Оценка от {formatDate(passport.category.assessed_at)}</small>
          </div>
          <div>
            <span>{passport.category.grade_state === "verified" ? "ПОДТВЕРЖДЁННЫЙ УРОВЕНЬ" : "ЗАЯВЛЕННЫЙ УРОВЕНЬ"}</span>
            <strong>{passport.category.grade ?? passport.category.declared_grade}</strong>
            {passport.category.grade_state === "verified" ? <small className="passportGrade verified">GRADE VERIFIED</small> : <UnconfirmedGradeBadge compact />}
          </div>
          <div>
            <span>РЕЗУЛЬТАТ</span>
            <strong>{Math.round(passport.category.score)}<small>/100</small></strong>
            <small>системная оценка</small>
          </div>
        </div>
      ) : (
        <EmptyState className="passportEmpty" title="Подтверждённой категории пока нет" description="Пройди базовую оценку, чтобы добавить первую платформенную проверку." />
      )}

      <div className="passportFreshness" aria-label="Свежесть доказательств">
        <span className="freshness-fresh"><strong>{passport.freshness.fresh}</strong> свежих</span>
        <span className="freshness-aging"><strong>{passport.freshness.aging}</strong> теряют актуальность</span>
        <span className="freshness-stale"><strong>{passport.freshness.stale}</strong> устаревших</span>
        {passport.fsp.history_status === "no_history" && <span className="passportNoHistory">FSP history отсутствует — это нормально</span>}
      </div>

      {passport.evidence.length === 0 ? (
        <EmptyState className="passportEvidenceEmpty" title="Доказательств пока нет" description="Они появятся после оценки, FSP link или заполнения профиля." />
      ) : (
        <div className="passportEvidence" aria-label="Доказательства навыков">
          {passport.evidence.map((item) => (
            <article className={`passportEvidenceCard ${item.status}`} key={item.id}>
              <div className="passportEvidenceTop">
                <div>
                  <span>{sourceLabels[item.source]}</span>
                  <strong>{item.title}</strong>
                </div>
                <b>{item.status === "verified" ? "VERIFIED" : item.status === "unconfirmed" ? "NOT CONFIRMED" : "DECLARED"}</b>
              </div>
              {item.skills.length > 0 && (
                <div className="passportSkillChips">
                  {item.skills.map((skill) => <span key={skill}>{skill}</span>)}
                </div>
              )}
              <div className="passportEvidenceMeta">
                <span>{item.score === null ? "Без балла" : `${Math.round(item.score)}/100`}</span>
                <span>уверенность {Math.round(item.confidence * 100)}%</span>
                <span>{freshnessLabels[item.freshness]}</span>
              </div>
              <p>{item.details}</p>
              <small>{item.measured_at ? `Измерено ${formatDate(item.measured_at)}` : item.provenance}</small>
            </article>
          ))}
        </div>
      )}

      {passport.retest_available_at && (
        <small className="passportRetest">Следующая базовая оценка доступна с {formatDate(passport.retest_available_at)}.</small>
      )}
    </section>
  );
}
