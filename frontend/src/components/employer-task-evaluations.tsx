"use client";

import { useEffect, useState } from "react";

type Submission = { id: string; attempt_number: number; response_text: string; submitted_at: string };
type Rubric = { name: string; points: number; description: string | null };
type Evaluation = {
  score: number;
  feedback: string | null;
  status: "draft" | "released";
  rubric_scores: { name: string; points_awarded: number }[];
};
type Assignment = {
  id: string;
  candidate_display_name: string;
  stage_title: string;
  status: "assigned" | "submitted" | "expired";
  submitted_at: string | null;
  task: { title: string; version_number: number; rubric: Rubric[] };
  submissions: Submission[];
  evaluation: Evaluation | null;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function EmployerTaskEvaluations({ token, refreshKey = 0 }: { token: string; refreshKey?: number }) {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [scores, setScores] = useState<Record<string, Record<string, number>>>({});
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [release, setRelease] = useState<Record<string, boolean>>({});
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setState("loading");
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/task-assignments`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("assignments_unavailable");
      const next = (await response.json()) as Assignment[];
      setAssignments(next);
      setScores(Object.fromEntries(next.map((assignment) => [
        assignment.id,
        Object.fromEntries(assignment.task.rubric.map((item) => [
          item.name,
          assignment.evaluation?.rubric_scores.find((score) => score.name === item.name)?.points_awarded ?? 0,
        ])),
      ])));
      setFeedback(Object.fromEntries(next.map((assignment) => [assignment.id, assignment.evaluation?.feedback ?? ""])));
      setRelease(Object.fromEntries(next.map((assignment) => [assignment.id, assignment.evaluation?.status === "released"])));
      setState("ready");
    } catch {
      setState("error");
    }
  }

  useEffect(() => { void load(); }, [token, refreshKey]);

  async function save(assignment: Assignment) {
    const rubricScores = assignment.task.rubric.map((item) => ({
      name: item.name,
      points_awarded: scores[assignment.id]?.[item.name] ?? 0,
    }));
    setBusyId(assignment.id);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/task-assignments/${assignment.id}/evaluation`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          rubric_scores: rubricScores,
          feedback: feedback[assignment.id]?.trim() || null,
          release_to_candidate: release[assignment.id] ?? false,
        }),
      });
      if (!response.ok) throw new Error("evaluation_failed");
      const updated = (await response.json()) as Assignment;
      setAssignments((current) => current.map((item) => item.id === updated.id ? updated : item));
      setMessage("Оценка сохранена в истории задания работодателя.");
    } catch {
      setMessage("Не удалось сохранить оценку. Проверьте баллы по рубрике.");
    } finally {
      setBusyId(null);
    }
  }

  if (state === "loading") return <section className="taskPanel muted">Загружаем ответы кандидатов…</section>;
  if (state === "error") return <section className="taskPanel error">Не удалось загрузить задания на проверку.</section>;

  return (
    <section className="taskPanel" aria-labelledby="employer-evaluations-title">
      <div className="companyHeading">
        <div>
          <span className="authLabel">ОЦЕНКА ЗАДАНИЙ КОМПАНИЕЙ</span>
          <h2 id="employer-evaluations-title">Ответы кандидатов</h2>
          <p>Вы проверяете задания, созданные вашей компанией. Результат относится к конкретной вакансии и кандидату.</p>
        </div>
        <span className="profileStatus">{assignments.length} SUBMISSIONS</span>
      </div>
      {message && <p className="candidateTasksMessage" aria-live="polite">{message}</p>}
      {assignments.length === 0 ? (
        <div className="invitationEmpty"><strong>Ответов пока нет</strong><span>Здесь появятся задания после взаимного согласия и отправки ответа кандидатом.</span></div>
      ) : (
        <div className="candidateTaskList">
          {assignments.map((assignment) => {
            const hasSubmission = assignment.submissions.length > 0;
            return (
              <article className="candidateTaskCard" key={assignment.id}>
                <div className="candidateTaskTop">
                  <div><span className="invitationState">{assignment.candidate_display_name}</span><h3>{assignment.task.title}</h3><small>{assignment.stage_title} · версия v{assignment.task.version_number}</small></div>
                  <strong className="candidateTaskDeadline">{assignment.evaluation ? `${assignment.evaluation.score}/100` : "НЕ ОЦЕНЕНО"}</strong>
                </div>
                {assignment.submissions.length > 0 && <div className="candidateTaskHistory"><strong>Последний ответ</strong><p>{assignment.submissions[assignment.submissions.length - 1].response_text}</p></div>}
                <div className="taskRubric"><strong>Оценка по рубрике</strong>{assignment.task.rubric.map((item) => <label className="evaluationRow" key={item.name}><span>{item.name} · максимум {item.points}</span><input type="number" min={0} max={item.points} value={scores[assignment.id]?.[item.name] ?? 0} onChange={(event) => setScores((current) => ({ ...current, [assignment.id]: { ...current[assignment.id], [item.name]: Number(event.target.value) } }))} /></label>)}</div>
                <label className="candidateTaskComposer">Комментарий кандидату<textarea value={feedback[assignment.id] ?? ""} maxLength={5000} rows={3} onChange={(event) => setFeedback((current) => ({ ...current, [assignment.id]: event.target.value }))} placeholder="Что получилось и что важно улучшить…" /></label>
                <div className="taskFooter"><label className="evaluationRelease"><input type="checkbox" checked={release[assignment.id] ?? false} onChange={(event) => setRelease((current) => ({ ...current, [assignment.id]: event.target.checked }))} /> Показать score и feedback кандидату</label><button className="authButton primaryButton" disabled={busyId === assignment.id || !hasSubmission} onClick={() => void save(assignment)}>{busyId === assignment.id ? "Сохраняем…" : "Сохранить оценку"}</button></div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
