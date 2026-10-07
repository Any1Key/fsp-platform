"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type TaxonomySpecialization = {
  slug: string;
  name: string;
};

type TaxonomyGrade = {
  slug: string;
  name: string;
};

type Taxonomy = {
  specializations: TaxonomySpecialization[];
  grades: TaxonomyGrade[];
};

type AssessmentItem = {
  item_id: string;
  domain: string;
  difficulty: number;
  prompt: string;
  options: string[];
  progressive: boolean;
};

type IntegrityEvidence = {
  signal: "cross_submission_similarity_review";
  modality: "text" | "code";
  scope: "progressive_response";
  item_id: string;
  similarity: number;
};

type Attempt = {
  attempt_id: string;
  specialization: string;
  declared_grade: string;
  status: "in_progress" | "submitted";
  items: AssessmentItem[];
  score?: number;
  grade_state?: "verified" | "not_confirmed";
  integrity_signals?: string[];
  integrity_evidence?: IntegrityEvidence[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const supportedSpecializations = new Set(["Backend Engineering"]);

async function responseError(response: Response, fallback: string) {
  try {
    const body = (await response.json()) as { error?: { message?: string } };
    return body.error?.message ?? fallback;
  } catch {
    return fallback;
  }
}

export function CandidateAssessment({
  token,
  onSubmitted,
}: {
  token: string;
  onSubmitted: () => void;
}) {
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null);
  const [selectionState, setSelectionState] = useState<"loading" | "ready" | "error">("loading");
  const [specialization, setSpecialization] = useState("Backend Engineering");
  const [grade, setGrade] = useState("Middle");
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [followups, setFollowups] = useState<Record<string, string>>({});
  const [actionState, setActionState] = useState<"idle" | "starting" | "submitting">("idle");
  const [error, setError] = useState<string | null>(null);
  const [pasteChars, setPasteChars] = useState(0);
  const startRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    fetch(`${apiUrl}/api/v1/taxonomy`)
      .then(async (response) => {
        if (!response.ok) throw new Error("taxonomy_unavailable");
        return (await response.json()) as Taxonomy;
      })
      .then((value) => {
        if (!active) return;
        setTaxonomy(value);
        const firstSupported = value.specializations.find((item) => supportedSpecializations.has(item.name));
        if (firstSupported) setSpecialization(firstSupported.name);
        setSelectionState("ready");
      })
      .catch(() => {
        if (active) setSelectionState("error");
      });
    return () => {
      active = false;
    };
  }, []);

  const progressiveItems = useMemo(
    () => (attempt?.items ?? []).filter((item) => item.progressive),
    [attempt],
  );
  const answeredCount = attempt
    ? attempt.items.filter((item) => answers[item.item_id] !== undefined).length
    : 0;
  const canSubmit = Boolean(
    attempt &&
      answeredCount === attempt.items.length &&
      progressiveItems.every((item) => (followups[item.item_id] ?? "").trim()),
  );

  async function startAssessment() {
    setActionState("starting");
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/assessments/attempts`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ specialization, declared_grade: grade }),
      });
      if (!response.ok) throw new Error(await responseError(response, "Не удалось сформировать оценку."));
      const value = (await response.json()) as Attempt;
      setAttempt(value);
      setAnswers({});
      setFollowups({});
      setPasteChars(0);
      requestAnimationFrame(() => startRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось сформировать оценку.");
    } finally {
      setActionState("idle");
    }
  }

  async function submitAssessment() {
    if (!attempt || !canSubmit) return;
    setActionState("submitting");
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/assessments/attempts/${attempt.attempt_id}/submit`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          answers,
          followups,
          telemetry: { paste_chars: pasteChars },
        }),
      });
      if (!response.ok) throw new Error(await responseError(response, "Не удалось отправить ответы."));
      const value = (await response.json()) as Attempt;
      setAttempt(value);
      onSubmitted();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось отправить ответы.");
    } finally {
      setActionState("idle");
    }
  }

  if (selectionState === "loading") {
    return <section className="assessmentPanel muted" aria-busy="true">Готовим варианты специализации…</section>;
  }
  if (selectionState === "error") {
    return <section className="assessmentPanel error" role="alert">Не удалось загрузить каталог оценки. Обнови страницу и попробуй ещё раз.</section>;
  }

  return (
    <section className="assessmentPanel" ref={startRef} aria-labelledby="assessment-title">
      <div className="assessmentHeading">
        <div>
          <span className="authLabel">BASE ASSESSMENT</span>
          <h2 id="assessment-title">Подтверди специализацию</h2>
          <p>Каждая попытка формируется заново: параметры и порядок заданий уникальны для твоей сессии.</p>
        </div>
        {attempt?.status === "in_progress" && <span className="assessmentStatus">В ПРОЦЕССЕ</span>}
      </div>

      {!attempt || attempt.status === "submitted" ? (
        <>
          {attempt?.status === "submitted" && (
            <div className={`assessmentResult ${attempt.grade_state}`}>
              <div>
                <span>Результат системы</span>
                <strong>{Math.round(attempt.score ?? 0)}<small>/100</small></strong>
              </div>
              <p>
                {attempt.grade_state === "verified"
                  ? `Уровень ${attempt.declared_grade} подтверждён и добавлен в Skill Passport.`
                  : `Заявленный уровень ${attempt.declared_grade} пока не подтверждён. Профиль остаётся видимым работодателям.`}
              </p>
              {!!attempt.integrity_evidence?.length && (
                <div className="assessmentReviewSignals" role="status">
                  <strong>Сигналы для ручной проверки</strong>
                  {attempt.integrity_evidence.map((evidence) => (
                    <span key={`${evidence.item_id}-${evidence.signal}`}>
                      {evidence.modality === "code" ? "Структурное сходство кода" : "Лексическое сходство текста"} · {Math.round(evidence.similarity * 100)}%
                    </span>
                  ))}
                  <small>Это не автоматический отказ и не изменение результата.</small>
                </div>
              )}
            </div>
          )}
          <div className="assessmentSelection">
            <label>
              Специализация
              <select value={specialization} onChange={(event) => setSpecialization(event.target.value)}>
                {(taxonomy?.specializations ?? []).map((item) => {
                  const supported = supportedSpecializations.has(item.name);
                  return <option key={item.slug} value={item.name} disabled={!supported}>{item.name}{supported ? "" : " · скоро"}</option>;
                })}
              </select>
            </label>
            <label>
              Заявленный уровень
              <select value={grade} onChange={(event) => setGrade(event.target.value)}>
                {(taxonomy?.grades ?? []).map((item) => <option key={item.slug} value={item.name}>{item.name}</option>)}
              </select>
            </label>
          </div>
          <p className="assessmentHint">Система проверит базовый уровень по выбранной специализации. Неудачный результат не меняет твоё заявление автоматически.</p>
          <button className="authButton primaryButton assessmentButton" disabled={actionState !== "idle"} onClick={startAssessment}>
            {actionState === "starting" ? "Формируем…" : attempt?.status === "submitted" ? "Пройти новую попытку" : "Начать оценку"}
          </button>
        </>
      ) : (
        <form className="assessmentForm" onSubmit={(event) => { event.preventDefault(); void submitAssessment(); }}>
          <div className="assessmentProgress"><span>{specialization} · {grade}</span><strong>{answeredCount}/{attempt.items.length} заданий</strong></div>
          {attempt.items.map((item, index) => (
            <fieldset className="assessmentItem" key={item.item_id}>
              <legend><span>{String(index + 1).padStart(2, "0")}</span>{item.prompt}</legend>
              <div className="assessmentOptions">
                {item.options.map((option, optionIndex) => (
                  <label key={option} className="assessmentOption">
                    <input
                      type="radio"
                      name={item.item_id}
                      checked={answers[item.item_id] === optionIndex}
                      onChange={() => setAnswers((current) => ({ ...current, [item.item_id]: optionIndex }))}
                    />
                    <span>{option}</span>
                  </label>
                ))}
              </div>
              {item.progressive && (
                <label className="assessmentFollowup">
                  Коротко объясни свой выбор
                  <textarea
                    value={followups[item.item_id] ?? ""}
                    onChange={(event) => setFollowups((current) => ({ ...current, [item.item_id]: event.target.value }))}
                    onPaste={(event) => setPasteChars((count) => count + event.clipboardData.getData("text").length)}
                    rows={3}
                    placeholder="Свяжи решение с ограничением из задания"
                  />
                </label>
              )}
            </fieldset>
          ))}
          <div className="assessmentSubmitRow">
            <small>Ответы проверяются системой. Сигналы целостности — только повод для ручного просмотра, не автоматический отказ.</small>
            <button className="authButton primaryButton assessmentButton" type="submit" disabled={!canSubmit || actionState !== "idle"}>
              {actionState === "submitting" ? "Проверяем…" : "Завершить оценку"}
            </button>
          </div>
        </form>
      )}
      {error && <p className="assessmentError" role="alert">{error}</p>}
    </section>
  );
}
