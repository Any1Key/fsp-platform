"use client";

import { useEffect, useState } from "react";

type Status = "submitted" | "reviewing" | "shortlisted" | "accepted" | "rejected" | "withdrawn";
type Application = {
  id: string;
  status: Status;
  match_id: string | null;
  applied_at: string;
  candidate: { id: string; display_name: string };
  vacancy: { title: string; company_name: string; salary_min_rub: number; salary_max_rub: number };
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const labels: Record<Status, string> = {
  submitted: "Новый отклик",
  reviewing: "На рассмотрении",
  shortlisted: "Следующий этап",
  accepted: "Совпадение найдено",
  rejected: "Отклонён",
  withdrawn: "Отозван",
};

async function readError(response: Response) {
  try {
    const body = (await response.json()) as { error?: { code?: string } };
    return body.error?.code ?? "APPLICATION_REQUEST_FAILED";
  } catch {
    return "APPLICATION_REQUEST_FAILED";
  }
}

export function EmployerApplications({ token, refreshKey = 0 }: { token: string; refreshKey?: number }) {
  const [applications, setApplications] = useState<Application[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setState("loading");
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/applications`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error(await readError(response));
      setApplications((await response.json()) as Application[]);
      setState("ready");
    } catch (error) {
      setMessage((error as Error).message);
      setState("error");
    }
  }

  useEffect(() => {
    void load();
    // refreshKey is the explicit cross-panel invalidation signal.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, refreshKey]);

  async function update(applicationId: string, nextStatus: "reviewing" | "shortlisted" | "rejected" | "accepted") {
    setBusyId(applicationId);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/applications/${applicationId}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      });
      if (!response.ok) throw new Error(await readError(response));
      setMessage(nextStatus === "accepted" ? "Отклик принят — рабочий контакт и внутренний чат созданы." : "Статус отклика обновлён.");
      await load();
    } catch (error) {
      setMessage(`Не удалось обновить отклик: ${(error as Error).message}`);
    } finally {
      setBusyId(null);
    }
  }

  if (state === "loading") return <section className="applicationReviewPanel muted">Загружаем входящие отклики…</section>;
  if (state === "error") return <section className="applicationReviewPanel error">Не удалось загрузить входящие отклики.</section>;

  return (
    <section className="applicationReviewPanel" aria-labelledby="employer-applications-title">
      <div className="applicationReviewHeading">
        <div>
          <span className="authLabel">ОТКЛИКИ КАНДИДАТОВ</span>
          <h2 id="employer-applications-title">Отклики на вакансии</h2>
          <p>Примите подходящего кандидата — рабочий контакт создастся сразу, а контакты откроются только внутри рабочего чата.</p>
        </div>
        <span className="profileStatus">{applications.length} APPLICATIONS</span>
      </div>
      {applications.length === 0 ? (
        <div className="applicationReviewEmpty"><strong>Входящих откликов пока нет</strong><span>Опубликуйте вакансию — подходящие кандидаты увидят её в разделе вакансий.</span></div>
      ) : (
        <div className="applicationReviewList">
          {applications.map((application) => (
            <article className="applicationReviewCard" key={application.id}>
              <div className="applicationReviewCardTop">
                <div><span className="candidateVacancyCompany">{application.candidate.display_name}</span><h3>{application.vacancy.title}</h3></div>
                <span className={`candidateApplicationStatus ${application.status}`}>{labels[application.status]}</span>
              </div>
              <small>Отклик от {new Date(application.applied_at).toLocaleDateString("ru-RU")} · ₽{application.vacancy.salary_min_rub.toLocaleString("ru-RU")}–{application.vacancy.salary_max_rub.toLocaleString("ru-RU")}</small>
              {application.status === "accepted" ? <p className="candidateMatchNotice">✓ Контакт создан · кандидат может открыть рабочий чат</p> : application.status === "rejected" || application.status === "withdrawn" ? null : (
                <div className="applicationReviewActions">
                  <button className="authButton secondaryButton" disabled={busyId === application.id} onClick={() => void update(application.id, "reviewing")}>На рассмотрение</button>
                  <button className="authButton secondaryButton" disabled={busyId === application.id} onClick={() => void update(application.id, "shortlisted")}>Следующий этап</button>
                  <button className="authButton primaryButton" disabled={busyId === application.id} onClick={() => void update(application.id, "accepted")}>Принять отклик</button>
                  <button className="authButton dangerButton" disabled={busyId === application.id} onClick={() => void update(application.id, "rejected")}>Отклонить</button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
      {message && <small className="candidateVacanciesMessage" aria-live="polite">{message}</small>}
    </section>
  );
}
