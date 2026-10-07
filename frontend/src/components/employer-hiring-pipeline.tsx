"use client";

import { useEffect, useState } from "react";

type StageType = "platform_review" | "employer_task" | "questionnaire" | "portfolio_review" | "interview" | "custom" | "final_decision";
type Stage = { id?: string; position?: number; stage_type: StageType; title: string; required: boolean; estimated_minutes: number };
type Pipeline = { stages: Stage[]; updated_at: string };

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const stageLabels: Record<StageType, string> = {
  platform_review: "Verified Skill Passport",
  employer_task: "Задание работодателя",
  questionnaire: "Анкета",
  portfolio_review: "Проверка портфолио / кода",
  interview: "Интервью",
  custom: "Свой этап",
  final_decision: "Финальное решение",
};
const employerStageTypes: StageType[] = ["employer_task", "questionnaire", "portfolio_review", "interview", "custom"];

async function errorCode(response: Response) {
  try {
    const body = (await response.json()) as { error?: { code?: string } };
    return body.error?.code ?? "HIRING_PIPELINE_REQUEST_FAILED";
  } catch {
    return "HIRING_PIPELINE_REQUEST_FAILED";
  }
}

function stageLabel(type: StageType) {
  return stageLabels[type];
}

export function EmployerHiringPipeline({ token, refreshKey = 0 }: { token: string; refreshKey?: number }) {
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setState("loading");
    fetch(`${apiUrl}/api/v1/employer/hiring-pipeline`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (!response.ok) throw new Error(await errorCode(response));
        return (await response.json()) as Pipeline;
      })
      .then((value) => { if (active) { setPipeline(value); setState("ready"); } })
      .catch((error: Error) => { if (active) { setMessage(error.message); setState("error"); } });
    return () => { active = false; };
  }, [token, refreshKey]);

  function updateStage(index: number, changes: Partial<Stage>) {
    setPipeline((current) => current ? { ...current, stages: current.stages.map((stage, item) => item === index ? { ...stage, ...changes } : stage) } : current);
    setMessage(null);
  }

  function moveStage(index: number, offset: -1 | 1) {
    setPipeline((current) => {
      if (!current) return current;
      const nextIndex = index + offset;
      if (nextIndex < 0 || nextIndex >= current.stages.length) return current;
      const stages = [...current.stages];
      [stages[index], stages[nextIndex]] = [stages[nextIndex], stages[index]];
      return { ...current, stages };
    });
    setMessage(null);
  }

  function removeStage(index: number) {
    if (!pipeline || pipeline.stages[index].stage_type === "platform_review" || pipeline.stages[index].stage_type === "final_decision") return;
    setPipeline({ ...pipeline, stages: pipeline.stages.filter((_, item) => item !== index) });
    setMessage(null);
  }

  function addStage() {
    if (!pipeline || pipeline.stages.length >= 12) return;
    const stageType = employerStageTypes[0];
    const finalIndex = pipeline.stages.findIndex((stage) => stage.stage_type === "final_decision");
    const stages = [...pipeline.stages];
    stages.splice(finalIndex < 0 ? stages.length : finalIndex, 0, {
      stage_type: stageType,
      title: stageLabel(stageType),
      required: false,
      estimated_minutes: 30,
    });
    setPipeline({ ...pipeline, stages });
    setMessage(null);
  }

  async function save() {
    if (!pipeline) return;
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/hiring-pipeline`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ stages: pipeline.stages.map(({ id, position, ...stage }) => stage) }),
      });
      if (!response.ok) {
        const code = await errorCode(response);
        const messages: Record<string, string> = {
          HIRING_PIPELINE_STAGE_COUNT_INVALID: "Добавьте хотя бы два этапа.",
          HIRING_PIPELINE_PLATFORM_REVIEW_REQUIRED: "Проверка Verified Skill Passport обязательна.",
          HIRING_PIPELINE_FINAL_DECISION_REQUIRED: "Финальное решение обязательно.",
        };
        throw new Error(messages[code] ?? code);
      }
      setPipeline((await response.json()) as Pipeline);
      setMessage("Порядок этапов сохранён. Эта версия будет показана в новых приглашениях.");
    } catch (error) {
      setMessage(`Не удалось сохранить: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  if (state === "loading") return <section className="pipelinePanel muted">Загружаем этапы найма…</section>;
  if (state === "error") return <section className="pipelinePanel error">Сначала сохраните hiring need, чтобы настроить этапы найма. <small>{message}</small></section>;
  if (!pipeline) return null;

  return (
    <section className="pipelinePanel" aria-labelledby="hiring-pipeline-title">
      <div className="companyHeading">
        <div>
          <span className="authLabel">HIRING PIPELINE</span>
          <h2 id="hiring-pipeline-title">Этапы после match</h2>
          <p>Соберите прозрачный порядок отбора. Кандидат увидит формат и примерное время до принятия приглашения.</p>
        </div>
        <span className="profileStatus">{pipeline.stages.length} STAGES</span>
      </div>
      <div className="pipelineStages" aria-label="Порядок этапов найма">
        {pipeline.stages.map((stage, index) => {
          const boundary = stage.stage_type === "platform_review" || stage.stage_type === "final_decision";
          return (
            <article className="pipelineStage" key={stage.id ?? `${stage.stage_type}-${index}`}>
              <div className="pipelineStageNumber">{String(index + 1).padStart(2, "0")}</div>
              <div className="pipelineStageBody">
                <div className="pipelineStageTop">
                  <strong>{stageLabel(stage.stage_type)}</strong>
                  <span>{boundary ? "Системный этап" : "Этап работодателя"}</span>
                </div>
                <div className="pipelineStageFields">
                  <label>Название<input maxLength={120} value={stage.title} onChange={(event) => updateStage(index, { title: event.target.value })} /></label>
                  <label>Формат<select value={stage.stage_type} disabled={boundary} onChange={(event) => updateStage(index, { stage_type: event.target.value as StageType, title: stageLabel(event.target.value as StageType) })}>{(boundary ? [stage.stage_type] : employerStageTypes).map((type) => <option key={type} value={type}>{stageLabel(type)}</option>)}</select></label>
                  <label>Минут<input type="number" min={5} max={480} value={stage.estimated_minutes} onChange={(event) => updateStage(index, { estimated_minutes: Number(event.target.value) })} /></label>
                  <label className="pipelineRequired"><input type="checkbox" checked={stage.required} disabled={boundary} onChange={(event) => updateStage(index, { required: event.target.checked })} /> Обязательный</label>
                </div>
              </div>
              <div className="pipelineStageActions">
                <button className="pipelineIconButton" type="button" aria-label={`Поднять этап ${index + 1}`} disabled={index === 0} onClick={() => moveStage(index, -1)}>↑</button>
                <button className="pipelineIconButton" type="button" aria-label={`Опустить этап ${index + 1}`} disabled={index === pipeline.stages.length - 1} onClick={() => moveStage(index, 1)}>↓</button>
                <button className="pipelineIconButton danger" type="button" aria-label={`Удалить этап ${index + 1}`} disabled={boundary} onClick={() => removeStage(index)}>×</button>
              </div>
            </article>
          );
        })}
      </div>
      <div className="pipelineFooter">
        <button className="authButton secondaryButton" type="button" disabled={pipeline.stages.length >= 12} onClick={addStage}>+ Добавить этап</button>
        <small aria-live="polite">{message ?? "Системные границы сохраняют понятный путь от проверки профиля до решения."}</small>
        <button className="authButton primaryButton" type="button" disabled={saving} onClick={() => void save()}>{saving ? "Сохраняем…" : "Сохранить порядок"}</button>
      </div>
    </section>
  );
}
