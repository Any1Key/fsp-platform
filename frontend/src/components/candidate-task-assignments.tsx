"use client";

import { useEffect, useState } from "react";

type Submission = {
  id: string;
  attempt_number: number;
  response_text: string;
  submitted_at: string;
};

type Assignment = {
  id: string;
  stage_title: string;
  status: "assigned" | "submitted" | "expired";
  assigned_at: string;
  due_at: string;
  submitted_at: string | null;
  task: {
    version_number: number;
    title: string;
    instructions: string;
    target_skills: string[];
    expected_grade: "junior" | "middle" | "senior";
    estimated_minutes: number;
  };
  submissions: Submission[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function dateLabel(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function statusLabel(status: Assignment["status"]) {
  if (status === "submitted") return "ОТВЕТ ОТПРАВЛЕН";
  if (status === "expired") return "ДЕДЛАЙН ПРОШЁЛ";
  return "ОЖИДАЕТ ОТВЕТА";
}

export function CandidateTaskAssignments({ token, refreshKey = 0 }: { token: string; refreshKey?: number }) {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setState("loading");
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/task-assignments`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("tasks_unavailable");
      setAssignments((await response.json()) as Assignment[]);
      setState("ready");
    } catch {
      setState("error");
    }
  }

  useEffect(() => {
    void load();
  }, [token, refreshKey]);

  async function submit(assignment: Assignment) {
    const responseText = drafts[assignment.id]?.trim() ?? "";
    if (!responseText) {
      setMessage("Добавьте ответ перед отправкой.");
      return;
    }
    setBusyId(assignment.id);
    setMessage(null);
    try {
      const response = await fetch(
        `${apiUrl}/api/v1/candidate/task-assignments/${assignment.id}/submissions`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ response_text: responseText }),
        },
      );
      if (!response.ok) throw new Error("submission_failed");
      const updated = (await response.json()) as Assignment;
      setAssignments((current) => current.map((item) => item.id === updated.id ? updated : item));
      setDrafts((current) => ({ ...current, [assignment.id]: "" }));
      setMessage("Ответ сохранён. При необходимости можно отправить новую версию до дедлайна.");
    } catch {
      setMessage("Не удалось отправить ответ. Проверьте дедлайн и попробуйте ещё раз.");
    } finally {
      setBusyId(null);
    }
  }

  if (state === "loading") return <section className="candidateTasksPanel muted">Проверяем задания после match…</section>;
  if (state === "error") return <section className="candidateTasksPanel error">Не удалось загрузить задания работодателя.</section>;

  return (
    <section className="candidateTasksPanel" aria-labelledby="candidate-tasks-title">
      <div className="candidateTasksHeading">
        <div>
          <span className="authLabel">EMPLOYER-OWNED STAGE</span>
          <h2 id="candidate-tasks-title">Задания после match</h2>
          <p>Это задания конкретного работодателя. Они не меняют глобальный Verified Grade.</p>
        </div>
        <span className="profileStatus">{assignments.length} TASK{assignments.length === 1 ? "" : "S"}</span>
      </div>
      {message && <p className="candidateTasksMessage" aria-live="polite">{message}</p>}
      {assignments.length === 0 ? (
        <div className="invitationEmpty"><strong>Назначенных заданий пока нет</strong><span>Они появятся после принятия приглашения и создания match.</span></div>
      ) : (
        <div className="candidateTaskList">
          {assignments.map((assignment) => (
            <article className="candidateTaskCard" key={assignment.id}>
              <div className="candidateTaskTop">
                <div><span className={`invitationState ${assignment.status === "expired" ? "declined" : assignment.status === "submitted" ? "accepted" : ""}`}>{statusLabel(assignment.status)}</span><h3>{assignment.task.title}</h3><small>{assignment.stage_title} · версия v{assignment.task.version_number}</small></div>
                <strong className="candidateTaskDeadline">до {dateLabel(assignment.due_at)}</strong>
              </div>
              <div className="candidateTaskMeta"><span>{assignment.task.expected_grade} · около {assignment.task.estimated_minutes} мин.</span><span>{assignment.task.target_skills.join(" · ")}</span></div>
              <p className="candidateTaskInstructions">{assignment.task.instructions}</p>
              {assignment.submissions.length > 0 && <div className="candidateTaskHistory"><strong>История ответов</strong>{assignment.submissions.map((submission) => <div key={submission.id}><span>Версия {submission.attempt_number} · {dateLabel(submission.submitted_at)}</span><p>{submission.response_text}</p></div>)}</div>}
              {assignment.status !== "expired" && <div className="candidateTaskComposer"><label>Новая версия ответа<textarea value={drafts[assignment.id] ?? ""} onChange={(event) => setDrafts((current) => ({ ...current, [assignment.id]: event.target.value }))} maxLength={20000} rows={5} placeholder="Опишите решение, ход мыслей и результат…" /></label><button className="authButton primaryButton" disabled={busyId === assignment.id} onClick={() => void submit(assignment)}>{busyId === assignment.id ? "Отправляем…" : assignment.status === "submitted" ? "Отправить новую версию" : "Отправить ответ"}</button></div>}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
