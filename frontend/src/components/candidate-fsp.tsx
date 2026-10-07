"use client";

import { FormEvent, useEffect, useState } from "react";

type Achievement = {
  id: string;
  event_name: string;
  event_date: string;
  discipline: string;
  level: string;
  achievement_type: string;
  placement: string | null;
  result: string | null;
  verification: string;
  mapping_version: string;
  mapped_specialization: string | null;
  mapped_skills: string[];
  result_score: number;
  result_label: string;
  recency_score: number;
  recency_label: string;
};

type FspState = {
  status: "not_linked" | "linked";
  provider: "synthetic" | null;
  participant_id: string | null;
  linked_at: string | null;
  updated_at: string | null;
  history_status: "no_history" | "has_history";
  achievements: Achievement[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function resultLabel(value: string) {
  return ({ winner: "Победа", prize: "Призовое место", finalist: "Финалист", placed: "Место", participant: "Участник", recorded: "Результат" } as Record<string, string>)[value] ?? value;
}

function recencyLabel(value: string) {
  return ({ recent: "свежее", aging: "актуальность снижается", old: "старше года", stale: "устаревшее, не удалено", future: "дата требует проверки" } as Record<string, string>)[value] ?? value;
}

export function CandidateFsp({ token }: { token: string }) {
  const [fsp, setFsp] = useState<FspState | null>(null);
  const [fspId, setFspId] = useState("");
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setState("loading");
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/fsp`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("fsp_unavailable");
      setFsp((await response.json()) as FspState);
      setState("ready");
    } catch {
      setState("error");
    }
  }

  useEffect(() => {
    let active = true;
    fetch(`${apiUrl}/api/v1/candidate/fsp`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("fsp_unavailable");
        return (await response.json()) as FspState;
      })
      .then((value) => {
        if (!active) return;
        setFsp(value);
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => {
      active = false;
    };
  }, [token]);

  async function link(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/fsp-link`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ fsp_id: fspId }),
      });
      if (!response.ok) {
        const error = (await response.json().catch(() => null)) as { error?: { code?: string } } | null;
        const code = error?.error?.code;
        setMessage(code === "PROCESSING_CONSENT_REQUIRED"
          ? "Сначала включи согласие на обработку данных в настройках приватности."
          : code === "FSP_PARTICIPANT_NOT_FOUND"
            ? "Такой демонстрационный FSP ID не найден."
            : "Не удалось привязать FSP ID.");
        return;
      }
      setFsp((await response.json()) as FspState);
      setFspId("");
      setMessage("FSP ID привязан.");
    } catch {
      setMessage("Сервис FSP пока недоступен.");
    } finally {
      setSaving(false);
    }
  }

  async function unlink() {
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/fsp-link`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("unlink_failed");
      await load();
      setMessage("FSP ID отвязан. История не влияет на доступность профиля.");
    } catch {
      setMessage("Не удалось отвязать FSP ID.");
    } finally {
      setSaving(false);
    }
  }

  if (state === "loading") {
    return <section className="fspPanel muted" aria-busy="true">Проверяем FSP evidence…</section>;
  }
  if (state === "error" || !fsp) {
    return <section className="fspPanel error" role="alert">Не удалось загрузить FSP evidence. Обнови страницу и попробуй ещё раз.</section>;
  }

  return (
    <section className="fspPanel" aria-labelledby="fsp-title">
      <div className="fspHeading">
        <div>
          <span className="authLabel">FSP EVIDENCE</span>
          <h2 id="fsp-title">История FSP</h2>
          <p>Дополнительный проверяемый сигнал. Отсутствие истории не ограничивает профиль.</p>
        </div>
        {fsp.provider && <span className="fspProvider">{fsp.provider === "synthetic" ? "DEMO REGISTRY" : fsp.provider}</span>}
      </div>

      {fsp.status === "linked" ? (
        <>
          <div className="fspLinkedRow">
            <div>
              <span>Привязанный ID</span>
              <strong>{fsp.participant_id}</strong>
            </div>
            <button className="textButton" type="button" onClick={unlink} disabled={saving}>Отвязать</button>
          </div>
          {fsp.history_status === "has_history" ? (
            <div className="fspAchievements">
              {fsp.achievements.map((achievement) => (
                <article className="fspAchievement" key={achievement.id}>
                  <div>
                    <strong>{achievement.event_name}</strong>
                    <small>{formatDate(achievement.event_date)} · {achievement.discipline}</small>
                  </div>
                  <span>{achievement.placement ? `Место ${achievement.placement}` : achievement.achievement_type}</span>
                  {achievement.result && <p>{achievement.result}</p>}
                  <div className="fspEvidenceMeta">
                    <span>{resultLabel(achievement.result_label)} · {achievement.result_score}/100</span>
                    <span>{achievement.mapped_skills.length ? `Навыки: ${achievement.mapped_skills.join(", ")}` : "Навыки пока не сопоставлены"}</span>
                    <span>Актуальность: {recencyLabel(achievement.recency_label)}</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="fspNoHistory"><strong>В реестре нет достижений</strong><p>FSP ID подтверждён, но история пока пустая. Профиль остаётся доступным через другие evidence.</p></div>
          )}
        </>
      ) : (
        <div className="fspNoHistory"><strong>FSP ID пока не привязан</strong><p>Это нормальное состояние: оценки платформы и профиль работают независимо от FSP.</p></div>
      )}

      <form className="fspLinkForm" onSubmit={link}>
        <label>FSP ID<input value={fspId} onChange={(event) => setFspId(event.target.value)} placeholder="Например, FSP-DEMO-001" required /></label>
        <button className="authButton secondaryButton" type="submit" disabled={saving}>{saving ? "Проверяем…" : "Привязать ID"}</button>
      </form>
      <small className="fspMessage" aria-live="polite">{message ?? "Демо использует replaceable synthetic adapter; это не production API FSP."}</small>
    </section>
  );
}
