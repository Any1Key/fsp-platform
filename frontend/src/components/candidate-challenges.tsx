"use client";

import { useEffect, useState } from "react";

type Challenge = {
  id: string;
  cycle_number: number;
  status: "assigned" | "scheduled" | "submitted" | "graded" | "expired";
  assigned_at: string;
  due_at: string;
  challenge: { title: string; instructions: string; target_skill: string; estimated_minutes: number; cadence_days: number };
  submission: { response_text: string; submitted_at: string } | null;
  result: {
    score: number;
    feedback: string | null;
    evidence_fresh_until: string | null;
    freshness: { status: "fresh" | "expiring" | "stale"; days_remaining: number; evidence_fresh_until: string } | null;
  } | null;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function dateLabel(value: string) {
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

export function CandidateChallenges({ token, refreshKey = 0 }: { token: string; refreshKey?: number }) {
  const [items, setItems] = useState<Challenge[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setState("loading");
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/challenges`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("challenges_unavailable");
      setItems((await response.json()) as Challenge[]);
      setState("ready");
    } catch {
      setState("error");
    }
  }

  useEffect(() => { void load(); }, [token, refreshKey]);

  async function submit(item: Challenge) {
    const responseText = drafts[item.id]?.trim() ?? "";
    if (!responseText) { setMessage("Добавьте ответ перед отправкой."); return; }
    setBusy(item.id); setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/challenges/${item.id}/submissions`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ response_text: responseText }),
      });
      if (!response.ok) throw new Error("challenge_submission_failed");
      const updated = (await response.json()) as Challenge;
      setItems((current) => current.map((entry) => entry.id === updated.id ? updated : entry));
      setDrafts((current) => ({ ...current, [item.id]: "" }));
      setMessage("Ответ отправлен работодателю на проверку.");
    } catch {
      setMessage("Не удалось отправить ответ. Проверьте цикл и дедлайн.");
    } finally { setBusy(null); }
  }

  if (state === "loading") return <section className="candidateTasksPanel muted">Проверяем короткие challenge-циклы…</section>;
  if (state === "error") return <section className="candidateTasksPanel error">Не удалось загрузить challenge-циклы.</section>;

  const freshness = items.reduce((summary, item) => {
    const status = item.result?.freshness?.status;
    if (status) summary[status] += 1;
    return summary;
  }, { fresh: 0, expiring: 0, stale: 0 });

  return (
    <section className="candidateTasksPanel" aria-labelledby="candidate-challenges-title">
      <div className="candidateTasksHeading"><div><span className="authLabel">ПРАКТИЧЕСКИЕ ЗАДАЧИ</span><h2 id="candidate-challenges-title">Короткие задания работодателя</h2><p>5–20 минут на задание. Результат относится к конкретной компании и не меняет общий подтверждённый уровень.</p></div><span className="profileStatus">{items.length} заданий</span></div>
      {message && <p className="candidateTasksMessage" aria-live="polite">{message}</p>}
      {items.length > 0 && <div className="candidateFreshnessSummary" aria-label="Сводка свежести employer evidence"><span className="fresh"><strong>{freshness.fresh}</strong> актуально</span><span className="expiring"><strong>{freshness.expiring}</strong> скоро обновить</span><span className="stale"><strong>{freshness.stale}</strong> устарело</span></div>}
      {items.length === 0 ? <div className="invitationEmpty"><strong>Активных challenge пока нет</strong><span>После match работодатель может включить короткий повторяющийся цикл.</span></div> : (
        <div className="candidateTaskList">{items.map((item) => (
          <article className="candidateTaskCard" key={item.id}>
            <div className="candidateTaskTop"><div><span className={`invitationState ${item.status === "expired" ? "declined" : item.status === "graded" ? "accepted" : ""}`}>{item.status === "scheduled" ? "ЗАПЛАНИРОВАНО" : item.status === "assigned" ? "ЖДЁТ ОТВЕТА" : item.status === "submitted" ? "НА ПРОВЕРКЕ" : item.status === "graded" ? "ПРОВЕРЕНО" : "ДЕДЛАЙН ПРОШЁЛ"}</span><h3>{item.challenge.title}</h3><small>Цикл {item.cycle_number} · {item.challenge.target_skill} · около {item.challenge.estimated_minutes} мин.</small></div><strong className="candidateTaskDeadline">до {dateLabel(item.due_at)}</strong></div>
            <p className="candidateTaskInstructions">{item.challenge.instructions}</p>
            {item.result && <div className={`candidateTaskEvaluation freshness-${item.result.freshness?.status ?? "stale"}`}><strong>{item.result.score}/100 · employer evidence</strong><p>{item.result.feedback || "Результат опубликован без комментария."}</p>{item.result.freshness?.status === "fresh" && <small>Свидетельство актуально ещё {item.result.freshness.days_remaining} дн. · до {dateLabel(item.result.evidence_fresh_until ?? item.result.freshness.evidence_fresh_until)}</small>}{item.result.freshness?.status === "expiring" && <small>Свидетельство скоро обновить · осталось {item.result.freshness.days_remaining} дн.</small>}{item.result.freshness?.status === "stale" && <small>Свидетельство устарело. Следующий цикл поможет обновить evidence.</small>}</div>}
            {item.status === "assigned" && <div className="candidateTaskComposer"><label>Ответ<textarea value={drafts[item.id] ?? ""} onChange={(event) => setDrafts((current) => ({ ...current, [item.id]: event.target.value }))} maxLength={20000} rows={4} placeholder="Опишите решение, наблюдение и ограничение…" /></label><button className="authButton primaryButton" disabled={busy === item.id} onClick={() => void submit(item)}>{busy === item.id ? "Отправляем…" : "Отправить ответ"}</button></div>}
          </article>
        ))}</div>
      )}
    </section>
  );
}
