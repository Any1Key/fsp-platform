"use client";

import { useEffect, useState, type FormEvent } from "react";

type Cycle = { id: string; cycle_number: number; status: string; match_id: string; candidate_display_name: string; challenge: { title: string; target_skill: string; cadence_days: number }; rubric: { name: string; points: number }[]; submission: { response_text: string } | null; result: { score: number; status: string; evidence_fresh_until: string | null; freshness: { status: "fresh" | "expiring" | "stale"; days_remaining: number; evidence_fresh_until: string } | null; rubric_scores?: { name: string; points_awarded: number }[] } | null };
type Match = { match_id: string; candidate: { id: string; display_name: string }; status: "accepted" };

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function EmployerChallenges({ token, refreshKey = 0 }: { token: string; refreshKey?: number }) {
  const [cycles, setCycles] = useState<Cycle[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [matchId, setMatchId] = useState("");
  const [title, setTitle] = useState("Weekly reliability pulse");
  const [instructions, setInstructions] = useState("Describe one production failure and the smallest safe mitigation.");
  const [skill, setSkill] = useState("python");
  const [cadence, setCadence] = useState("7");
  const [scores, setScores] = useState<Record<string, Record<string, number>>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setState("loading");
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [challengeResponse, invitationResponse] = await Promise.all([
        fetch(`${apiUrl}/api/v1/employer/challenges`, { headers }),
        fetch(`${apiUrl}/api/v1/employer/invitations`, { headers }),
      ]);
      if (!challengeResponse.ok || !invitationResponse.ok) throw new Error("challenges_unavailable");
      setCycles((await challengeResponse.json()) as Cycle[]);
      const invitations = (await invitationResponse.json()) as Match[];
      const accepted = invitations.filter((item) => item.status === "accepted" && item.match_id).map((item) => ({ match_id: item.match_id, candidate: item.candidate, status: item.status }));
      setMatches(accepted);
      if (!matchId && accepted[0]) setMatchId(accepted[0].match_id);
      setState("ready");
    } catch { setState("error"); }
  }

  useEffect(() => { void load(); }, [token, refreshKey]);

  async function create(event: FormEvent) {
    event.preventDefault(); setBusy("create"); setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/challenges`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ match_id: matchId, title, instructions, target_skill: skill, estimated_minutes: 10, cadence_days: Number(cadence), rubric: [{ name: "Diagnosis", points: 60 }, { name: "Mitigation", points: 40 }] }) });
      if (!response.ok) throw new Error("challenge_create_failed");
      setMessage("Задание запущено. После публикации результата следующий цикл запланируется автоматически.");
      await load();
    } catch { setMessage("Не удалось запустить задание. Нужны действующий контакт и корректная периодичность."); }
    finally { setBusy(null); }
  }

  async function grade(item: Cycle) {
    if (!item.submission || item.result) return;
    setBusy(item.id); setMessage(null);
    const rubricScores = item.rubric.map((rubric) => ({ name: rubric.name, points_awarded: scores[item.id]?.[rubric.name] ?? 0 }));
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/challenges/${item.id}/result`, { method: "PUT", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ rubric_scores: rubricScores, release_to_candidate: true, feedback: "Результат проверен по короткой challenge-рубрике." }) });
      if (!response.ok) throw new Error("challenge_grade_failed");
      setMessage("Результат опубликован в профиле кандидата; следующий цикл запланирован.");
      await load();
    } catch { setMessage("Не удалось сохранить результат. Проверьте баллы по рубрике."); }
    finally { setBusy(null); }
  }

  if (state === "loading") return <section className="taskPanel muted">Загружаем периодические задания…</section>;
  if (state === "error") return <section className="taskPanel error">Не удалось загрузить периодические задания.</section>;

  return <section className="taskPanel" aria-labelledby="employer-challenges-title">
    <div className="companyHeading"><div><span className="authLabel">ПОВТОРНАЯ ПРОВЕРКА НАВЫКОВ</span><h2 id="employer-challenges-title">Периодические задания</h2><p>Короткие задания после совпадения помогают поддерживать актуальность оценки компании и не меняют общий уровень кандидата.</p></div><button className="authButton secondaryButton" type="button" onClick={() => void load()}>Обновить</button></div>
    <form className="inviteForm" onSubmit={(event) => void create(event)}><strong>Создать задание для кандидата</strong><label>Кандидат<select required value={matchId} onChange={(event) => setMatchId(event.target.value)}><option value="">Выберите контакт</option>{matches.map((match) => <option key={match.match_id} value={match.match_id}>{match.candidate.display_name}</option>)}</select></label><label>Название<input required value={title} onChange={(event) => setTitle(event.target.value)} maxLength={160} /></label><label>Инструкция<textarea required value={instructions} onChange={(event) => setInstructions(event.target.value)} maxLength={12000} rows={3} /></label><div className="inviteFields"><label>Навык<input required value={skill} onChange={(event) => setSkill(event.target.value)} maxLength={80} /></label><label>Повтор, дней<input required type="number" min="1" max="90" value={cadence} onChange={(event) => setCadence(event.target.value)} /></label></div><button className="authButton primaryButton" disabled={busy === "create" || !matchId}>{busy === "create" ? "Запускаем…" : "Запустить задание"}</button></form>
    {message && <p className="candidateTasksMessage" aria-live="polite">{message}</p>}
    {cycles.length === 0 ? <div className="invitationEmpty"><strong>Периодических заданий пока нет</strong><span>После принятия приглашения кандидатом запустите короткий цикл.</span></div> : <div className="candidateTaskList">{cycles.map((item) => <article className="candidateTaskCard" key={item.id}><div className="candidateTaskTop"><div><span className="invitationState">{item.candidate_display_name} · цикл {item.cycle_number}</span><h3>{item.challenge.title}</h3><small>{item.challenge.target_skill} · каждые {item.challenge.cadence_days} дн.</small></div><strong className="candidateTaskDeadline">{item.result ? `${item.result.score}/100` : item.status === "scheduled" ? "ЗАПЛАНИРОВАНО" : "НЕ ОЦЕНЕНО"}</strong></div>{item.result?.freshness && <div className={`candidateTaskFreshness freshness-${item.result.freshness.status}`}>{item.result.freshness.status === "fresh" ? `Результат актуален ещё ${item.result.freshness.days_remaining} дн.` : item.result.freshness.status === "expiring" ? `Результат скоро потребуется обновить · ${item.result.freshness.days_remaining} дн.` : "Результат устарел · нужен новый цикл"}</div>}{item.submission && <div className="candidateTaskHistory"><strong>Ответ кандидата</strong><p>{item.submission.response_text}</p></div>}{!item.result && item.submission && <div className="taskRubric"><strong>Критерии оценки</strong>{item.rubric.map((rubric) => <label className="evaluationRow" key={rubric.name}><span>{rubric.name} · максимум {rubric.points}</span><input type="number" min={0} max={rubric.points} value={scores[item.id]?.[rubric.name] ?? 0} onChange={(event) => setScores((current) => ({ ...current, [item.id]: { ...current[item.id], [rubric.name]: Number(event.target.value) } }))} /></label>)}<button className="authButton primaryButton" disabled={busy === item.id} onClick={() => void grade(item)}>{busy === item.id ? "Публикуем…" : "Опубликовать результат"}</button></div>}</article>)}</div>}
  </section>;
}
