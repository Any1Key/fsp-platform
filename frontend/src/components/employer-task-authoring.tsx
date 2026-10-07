"use client";

import { useEffect, useMemo, useState } from "react";

type Stage = { id?: string; stage_type: string; title: string };
type Pipeline = { stages: Stage[] };
type Rubric = { name: string; points: number; description: string };
type Content = {
  title: string;
  instructions: string;
  target_skills: string[];
  expected_grade: "junior" | "middle" | "senior";
  estimated_minutes: number;
  deadline_hours: number;
  rubric: Rubric[];
};
type Version = Content & { version_number: number; status: "draft" | "published" | "retired" };
type Task = {
  id: string;
  pipeline_stage_id: string | null;
  status: "draft" | "published" | "retired";
  current_version: Version;
  versions: { version_number: number; status: string }[];
};
type LocalAiStatus = "loading" | "disabled" | "available" | "error";
type ApprovedExample = {
  task_version_id: string;
  title: string;
  specialization: string;
  grade: string;
  target_skills: string[];
  relevance_score: number;
};
type GeneratedDraft = Content & { difficulty_rationale: string };
type DraftFeedback = {
  id: string;
  decision: "approved" | "edited" | "rejected";
  reviewed_draft: GeneratedDraft | null;
  feedback_note: string | null;
  created_at: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const emptyRubric = (): Rubric[] => [
  { name: "Correctness", points: 70, description: "" },
  { name: "Explanation", points: 30, description: "" },
];

function blankContent(): Content {
  return {
    title: "",
    instructions: "",
    target_skills: ["python"],
    expected_grade: "middle",
    estimated_minutes: 30,
    deadline_hours: 72,
    rubric: emptyRubric(),
  };
}

async function readError(response: Response) {
  try {
    const body = (await response.json()) as { error?: { message?: string } };
    return body.error?.message ?? "Не удалось сохранить задание.";
  } catch {
    return "Не удалось сохранить задание.";
  }
}

function toForm(version: Version): Content {
  return {
    title: version.title,
    instructions: version.instructions,
    target_skills: version.target_skills,
    expected_grade: version.expected_grade,
    estimated_minutes: version.estimated_minutes,
    deadline_hours: version.deadline_hours,
    rubric: version.rubric.map((item) => ({ ...item, description: item.description ?? "" })),
  };
}

export function EmployerTaskAuthoring({ token, refreshKey = 0 }: { token: string; refreshKey?: number }) {
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [stageId, setStageId] = useState("");
  const [form, setForm] = useState<Content>(blankContent());
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [localAiStatus, setLocalAiStatus] = useState<LocalAiStatus>("loading");
  const [approvedExamples, setApprovedExamples] = useState<ApprovedExample[]>([]);
  const [suggestedDraft, setSuggestedDraft] = useState<GeneratedDraft | null>(null);
  const [suggestedDraftApplied, setSuggestedDraftApplied] = useState(false);
  const [feedbackHistory, setFeedbackHistory] = useState<DraftFeedback[]>([]);
  const [feedbackNote, setFeedbackNote] = useState("");
  const [feedbackBusy, setFeedbackBusy] = useState(false);

  const employerStages = useMemo(
    () => (pipeline?.stages ?? []).filter((stage) => stage.stage_type === "employer_task" && stage.id),
    [pipeline],
  );
  const selectedTask = tasks.find((task) => task.id === selectedId) ?? null;

  async function load() {
    setState("loading");
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [pipelineResponse, tasksResponse] = await Promise.all([
        fetch(`${apiUrl}/api/v1/employer/hiring-pipeline`, { headers }),
        fetch(`${apiUrl}/api/v1/employer/tasks`, { headers }),
      ]);
      if (!pipelineResponse.ok) throw new Error(await readError(pipelineResponse));
      if (!tasksResponse.ok) throw new Error(await readError(tasksResponse));
      const nextPipeline = (await pipelineResponse.json()) as Pipeline;
      const nextTasks = (await tasksResponse.json()) as Task[];
      setPipeline(nextPipeline);
      setTasks(nextTasks);
      if (nextTasks.length > 0) {
        setSelectedId(nextTasks[0].id);
        setStageId(nextTasks[0].pipeline_stage_id ?? nextPipeline.stages.find((stage) => stage.stage_type === "employer_task")?.id ?? "");
        setForm(toForm(nextTasks[0].current_version));
      } else {
        setSelectedId(null);
        setStageId(nextPipeline.stages.find((stage) => stage.stage_type === "employer_task")?.id ?? "");
        setForm(blankContent());
      }
      setState("ready");
      void probeLocalAi();
    } catch (error) {
      setMessage((error as Error).message);
      setState("error");
    }
  }

  useEffect(() => { void load(); }, [token, refreshKey]);

  async function probeLocalAi() {
    setLocalAiStatus("loading");
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/tasks/draft-suggestion`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("local_ai_unavailable");
      const result = (await response.json()) as {
        status: "disabled" | "completed" | "failed";
        approved_examples: ApprovedExample[];
        draft: GeneratedDraft | null;
        feedback_history: DraftFeedback[];
      };
      setApprovedExamples(result.approved_examples ?? []);
      setSuggestedDraft(result.status === "completed" ? result.draft : null);
      setSuggestedDraftApplied(false);
      setFeedbackHistory(result.feedback_history ?? []);
      setLocalAiStatus(result.status === "disabled" ? "disabled" : result.status === "completed" ? "available" : "error");
    } catch {
      // AI is optional: a probe failure must never disable manual authoring.
      setApprovedExamples([]);
      setSuggestedDraft(null);
      setLocalAiStatus("error");
    }
  }

  function applySuggestedDraft() {
    if (!suggestedDraft) return;
    const { difficulty_rationale: rationale, ...content } = suggestedDraft;
    setForm({
      ...content,
      rubric: content.rubric.map((item) => ({ ...item, description: item.description ?? "" })),
    });
    setSuggestedDraftApplied(true);
    setMessage(`Черновик применён для проверки. Обоснование сложности: ${rationale}`);
  }

  async function submitFeedback(decision: DraftFeedback["decision"]) {
    if (decision !== "rejected" && !suggestedDraft) return;
    setFeedbackBusy(true);
    setMessage(null);
    const draft = decision === "rejected" ? null : decision === "approved" ? suggestedDraft : {
      ...form,
      difficulty_rationale: suggestedDraft?.difficulty_rationale ?? "Отредактировано работодателем после проверки.",
    };
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/tasks/draft-suggestion/feedback`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ decision, draft, feedback_note: feedbackNote.trim() || null }),
      });
      if (!response.ok) throw new Error(await readError(response));
      const feedback = (await response.json()) as DraftFeedback;
      setFeedbackHistory((current) => [feedback, ...current].slice(0, 10));
      setFeedbackNote("");
      setMessage(decision === "rejected" ? "Подсказка отклонена. Это не меняет задание и не блокирует ручное создание." : "Решение сохранено. Сохраните и опубликуйте задание отдельно, если оно готово.");
      if (decision === "rejected") setSuggestedDraft(null);
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setFeedbackBusy(false);
    }
  }

  function selectTask(task: Task) {
    setSelectedId(task.id);
    setStageId(task.pipeline_stage_id ?? employerStages[0]?.id ?? "");
    setForm(toForm(task.current_version));
    setSuggestedDraftApplied(false);
    setMessage(null);
  }

  function newTask() {
    setSelectedId(null);
    setStageId(employerStages[0]?.id ?? "");
    setForm(blankContent());
    setSuggestedDraftApplied(false);
    setMessage(null);
  }

  function update<K extends keyof Content>(field: K, value: Content[K]) {
    setForm((current) => ({ ...current, [field]: value }));
    setMessage(null);
  }

  function updateRubric(index: number, changes: Partial<Rubric>) {
    setForm((current) => ({
      ...current,
      rubric: current.rubric.map((item, itemIndex) => itemIndex === index ? { ...item, ...changes } : item),
    }));
  }

  async function saveDraft() {
    if (!stageId || !form.title.trim() || !form.instructions.trim()) {
      setMessage("Выберите этап и заполните название с инструкцией.");
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
      const response = await fetch(
        selectedId ? `${apiUrl}/api/v1/employer/tasks/${selectedId}/draft` : `${apiUrl}/api/v1/employer/tasks`,
        {
          method: selectedId ? "PATCH" : "POST",
          headers,
          body: JSON.stringify(selectedId ? form : { ...form, pipeline_stage_id: stageId }),
        },
      );
      if (!response.ok) throw new Error(await readError(response));
      const task = (await response.json()) as Task;
      setTasks((current) => current.some((item) => item.id === task.id) ? current.map((item) => item.id === task.id ? task : item) : [...current, task]);
      setSelectedId(task.id);
      setStageId(task.pipeline_stage_id ?? stageId);
      setForm(toForm(task.current_version));
      setMessage("Черновик сохранён. Он ещё не показывается кандидатам.");
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function publish() {
    if (!selectedId) return;
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/tasks/${selectedId}/publish`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error(await readError(response));
      const task = (await response.json()) as Task;
      setTasks((current) => current.map((item) => item.id === task.id ? task : item));
      setForm(toForm(task.current_version));
      setMessage("Версия опубликована. Изменения после этого создадут новую версию.");
      void probeLocalAi();
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (state === "loading") return <section className="taskPanel muted">Загружаем редактор заданий…</section>;
  if (state === "error") return <section className="taskPanel error">Не удалось загрузить задания. <small>{message}</small></section>;
  if (employerStages.length === 0) return <section className="taskPanel muted">Добавьте этап «Задание работодателя» в Hiring Pipeline, чтобы создать задание.</section>;

  return (
    <section className="taskPanel" aria-labelledby="employer-task-title">
      <div className="companyHeading">
        <div>
          <span className="authLabel">EMPLOYER-OWNED EVIDENCE</span>
          <h2 id="employer-task-title">Задания для pipeline</h2>
          <p>Создайте черновик и опубликуйте его явно. Это задание не меняет глобальный Verified Grade.</p>
        </div>
        <span className="profileStatus">{tasks.length} TASKS</span>
      </div>
      <div className={`localAiStatus ${localAiStatus}`} aria-live="polite">
        <span>{localAiStatus === "disabled" ? "LOCAL AI OFF" : localAiStatus === "available" ? "LOCAL AI READY" : localAiStatus === "loading" ? "CHECKING LOCAL AI…" : "LOCAL AI UNAVAILABLE"}</span>
        <small>{localAiStatus === "disabled" ? "Создайте задание вручную — это не блокирует hiring pipeline." : "Подсказки не публикуются автоматически; работодатель всегда редактирует и публикует задание."}</small>
        {localAiStatus !== "disabled" && (
          <div className="taskAiActions">
            <button className="authButton secondaryButton" type="button" disabled={localAiStatus === "loading"} onClick={() => void probeLocalAi()}>
              {suggestedDraft ? "Обновить черновик" : "Сгенерировать черновик"}
            </button>
            {suggestedDraft && <button className="authButton primaryButton" type="button" onClick={applySuggestedDraft}>Применить для проверки</button>}
          </div>
        )}
      </div>
      {approvedExamples.length > 0 && (
        <div className="approvedTaskMemory" aria-label="Одобренные примеры заданий">
          <strong>{approvedExamples.length} одобренных примера доступны для подсказки</strong>
          <small>Подобраны по текущей специализации, грейду и навыкам. Содержимое остаётся в контуре вашей компании.</small>
          <ul>
            {approvedExamples.map((example) => (
              <li key={example.task_version_id}>
                <span>{example.title}</span>
                <small>{example.specialization} · {example.grade} · {example.target_skills.join(", ")}</small>
              </li>
            ))}
          </ul>
        </div>
      )}
      {suggestedDraft && (
        <div className="draftFeedback" aria-label="Проверка подсказки">
          <strong>Решение по текущему черновику</strong>
          <small>Одобрение сохраняет feedback для этой компании, но само по себе не публикует задание.</small>
          <input maxLength={1000} value={feedbackNote} onChange={(event) => setFeedbackNote(event.target.value)} placeholder="Необязательный комментарий для команды" />
          <div className="taskAiActions">
            <button className="authButton secondaryButton" type="button" disabled={feedbackBusy} onClick={() => void submitFeedback("rejected")}>Отклонить</button>
            <button className="authButton secondaryButton" type="button" disabled={feedbackBusy || !suggestedDraftApplied} onClick={() => void submitFeedback("edited")}>Сохранить как изменённый</button>
            <button className="authButton primaryButton" type="button" disabled={feedbackBusy} onClick={() => void submitFeedback("approved")}>Одобрить</button>
          </div>
        </div>
      )}
      {feedbackHistory.length > 0 && (
        <div className="draftFeedbackHistory" aria-label="История решений по подсказкам">
          <strong>Последние решения</strong>
          <ul>
            {feedbackHistory.map((feedback) => (
              <li key={feedback.id}>
                <span>{feedback.decision === "approved" ? "Одобрено" : feedback.decision === "edited" ? "Изменено" : "Отклонено"}</span>
                <small>{new Date(feedback.created_at).toLocaleString("ru-RU")}{feedback.feedback_note ? ` · ${feedback.feedback_note}` : ""}</small>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="taskToolbar">
        <div className="taskList" aria-label="Задания работодателя">
          {tasks.map((task) => (
            <button key={task.id} className={`taskListItem ${task.id === selectedId ? "active" : ""}`} type="button" onClick={() => selectTask(task)}>
              <strong>{task.current_version.title || "Без названия"}</strong>
              <small>v{task.current_version.version_number} · {task.status === "published" ? "Опубликовано" : "Черновик"}</small>
            </button>
          ))}
          <button className="taskNewButton" type="button" onClick={newTask}>+ Новое задание</button>
        </div>
        <div className="taskForm">
          <label>Этап<select value={stageId} onChange={(event) => setStageId(event.target.value)}>{employerStages.map((stage) => <option key={stage.id} value={stage.id}>{stage.title}</option>)}</select></label>
          <label>Название<input maxLength={160} value={form.title} onChange={(event) => update("title", event.target.value)} placeholder="Например, bounded retry policy" /></label>
          <label>Инструкция<textarea maxLength={12000} rows={5} value={form.instructions} onChange={(event) => update("instructions", event.target.value)} placeholder="Опишите контекст, результат и ограничения…" /></label>
          <div className="taskFields">
            <label>Навыки<input value={form.target_skills.join(", ")} onChange={(event) => update("target_skills", event.target.value.split(",").map((skill) => skill.trim()).filter(Boolean))} /></label>
            <label>Ожидаемый грейд<select value={form.expected_grade} onChange={(event) => update("expected_grade", event.target.value as Content["expected_grade"])}><option value="junior">Junior</option><option value="middle">Middle</option><option value="senior">Senior</option></select></label>
            <label>Минут<input type="number" min={5} max={480} value={form.estimated_minutes} onChange={(event) => update("estimated_minutes", Number(event.target.value))} /></label>
            <label>Дедлайн, часов<input type="number" min={1} max={720} value={form.deadline_hours} onChange={(event) => update("deadline_hours", Number(event.target.value))} /></label>
          </div>
          <div className="taskRubric"><strong>Рубрика и баллы</strong>{form.rubric.map((item, index) => <div className="taskRubricRow" key={index}><input aria-label={`Название критерия ${index + 1}`} value={item.name} onChange={(event) => updateRubric(index, { name: event.target.value })} /><input aria-label={`Баллы критерия ${index + 1}`} type="number" min={1} max={1000} value={item.points} onChange={(event) => updateRubric(index, { points: Number(event.target.value) })} /><input aria-label={`Описание критерия ${index + 1}`} value={item.description} onChange={(event) => updateRubric(index, { description: event.target.value })} placeholder="Что проверяем" /></div>)}</div>
          <div className="taskFooter"><small aria-live="polite">{message ?? (selectedTask?.status === "published" ? "Редактирование создаст следующую версию." : "Черновик доступен только вашей команде.")}</small><button className="authButton secondaryButton" type="button" disabled={saving} onClick={() => void saveDraft()}>{saving ? "Сохраняем…" : "Сохранить черновик"}</button><button className="authButton primaryButton" type="button" disabled={saving || !selectedId || selectedTask?.status !== "draft"} onClick={() => void publish()}>Опубликовать версию</button></div>
        </div>
      </div>
    </section>
  );
}
