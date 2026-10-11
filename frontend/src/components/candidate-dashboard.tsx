"use client";

import { useEffect, useState } from "react";

type DashboardAttempt = {
  attempt_id: string;
  specialization: string;
  declared_grade: string;
  status: "in_progress" | "submitted";
  score: number | null;
  grade_state: "verified" | "not_confirmed" | null;
  created_at: string;
};

type Dashboard = {
  profile: {
    display_name: string | null;
    headline: string | null;
  };
  current_assessment: {
    attempt_id: string;
    specialization: string;
    declared_grade: string;
    verified_grade: string | null;
    grade_state: "verified" | "not_confirmed";
    score: number;
    assessed_at: string;
  } | null;
  retest_available_at: string | null;
  attempt_history: DashboardAttempt[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function CandidateDashboard({ token, refreshKey = 0 }: { token: string; refreshKey?: number }) {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let active = true;
    setState("loading");
    fetch(`${apiUrl}/api/v1/candidate/dashboard`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("dashboard_unavailable");
        return (await response.json()) as Dashboard;
      })
      .then((value) => {
        if (!active) return;
        setDashboard(value);
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
    return <section className="dashboardPanel muted" aria-busy="true">Загружаем твой Skill Passport…</section>;
  }
  if (state === "error" || !dashboard) {
    return (
      <section className="dashboardPanel error" role="alert">
        Не удалось загрузить данные оценки. Обнови страницу и попробуй ещё раз.
      </section>
    );
  }

  const current = dashboard.current_assessment;
  return (
    <section className="dashboardPanel" aria-labelledby="dashboard-title">
      <div className="dashboardHeading">
        <div>
          <span className="authLabel">ПРОФИЛЬ НАВЫКОВ</span>
          <h2 id="dashboard-title">Твой профессиональный трек</h2>
          <p>Здесь собраны подтверждённая категория и история базовых оценок.</p>
        </div>
        {dashboard.profile.headline && <span className="dashboardHeadline">{dashboard.profile.headline}</span>}
      </div>

      {current ? (
        <div className="dashboardCurrent">
          <div className="dashboardCategory">
            <span>Текущая категория</span>
            <strong>{current.specialization}</strong>
            <small>Оценка от {formatDate(current.assessed_at)}</small>
          </div>
          <div className="dashboardGrade">
            <span>{current.grade_state === "verified" ? "Подтверждённый уровень" : "Заявленный уровень"}</span>
            <strong>{current.verified_grade ?? current.declared_grade}</strong>
            <span className={`dashboardBadge ${current.grade_state}`}>
              {current.grade_state === "verified" ? "УРОВЕНЬ ПОДТВЕРЖДЁН" : "УРОВЕНЬ НЕ ПОДТВЕРЖДЁН"}
            </span>
          </div>
          <div className="dashboardScore">
            <span>Результат</span>
            <strong>{Math.round(current.score)}<small>/100</small></strong>
          </div>
        </div>
      ) : (
        <div className="dashboardEmpty">
          <strong>Подтверждённой оценки пока нет</strong>
          <p>Пройди базовую оценку, чтобы сформировать категорию, которую увидят работодатели.</p>
        </div>
      )}

      <div className="dashboardHistoryHeading">
        <div>
          <h3>История оценок</h3>
          <small>{dashboard.attempt_history.length} попыток · последние сверху</small>
        </div>
        {dashboard.retest_available_at && current && (
          <small className="dashboardCooldown">Следующая попытка доступна с {formatDate(dashboard.retest_available_at)}</small>
        )}
      </div>

      {dashboard.attempt_history.length === 0 ? (
        <p className="dashboardHistoryEmpty">История появится после начала оценки.</p>
      ) : (
        <ul className="dashboardHistory">
          {dashboard.attempt_history.map((attempt) => (
            <li key={attempt.attempt_id}>
              <div>
                <strong>{attempt.specialization} · {attempt.declared_grade}</strong>
                <small>{formatDate(attempt.created_at)}</small>
              </div>
              <span className={`dashboardHistoryState ${attempt.grade_state ?? attempt.status}`}>
                {attempt.status === "in_progress"
                  ? "В процессе"
                  : attempt.grade_state === "verified"
                    ? `${Math.round(attempt.score ?? 0)} · подтверждено`
                    : "Уровень не подтверждён"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
