"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";

type SkillEvidence = { skill: string; present: boolean; edges: { source: string }[] };
type RadarCandidate = {
  candidate_id: string;
  display_name: string;
  headline: string | null;
  location: string | null;
  eligibility: "verified" | "unconfirmed";
  match_score: number;
  category: {
    label: string | null;
    specialization: string | null;
    grade: string | null;
    grade_name: string | null;
    state: string;
  };
  confidence: { overall: number; grade: number; evidence: number; freshness: number };
  assessment: { score: number | null; status: string };
  evidence: { required: SkillEvidence[]; preferred: SkillEvidence[] };
  fsp: { score: number; history_status: string };
  reasons: string[];
  gaps: string[];
  blind_discovery?: boolean;
  identity_revealed?: boolean;
};
type RadarResponse = {
  need: {
    role: string;
    specialization: { name: string };
    grade: { name: string };
    required_skills: { slug: string; name: string }[];
    preferred_skills: { slug: string; name: string }[];
  };
  snapshot: { id: string; created_at: string; filters: { include_unconfirmed: boolean; blind: boolean } };
  blind_discovery: boolean;
  categories: {
    key: string;
    candidate_count: number;
    verified_count: number;
    unconfirmed_count: number;
  }[];
  candidates: RadarCandidate[];
  total_candidates: number;
};

type Filters = { query: string; specialization: string; grade: string; skill: string; fsp: "all" | "with_history" | "without_history"; include_unconfirmed: boolean; blind: boolean };
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const initialFilters: Filters = { query: "", specialization: "", grade: "", skill: "", fsp: "all", include_unconfirmed: true, blind: false };

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { code?: string } };
    return body.error?.code ?? "TALENT_RADAR_REQUEST_FAILED";
  } catch {
    return "TALENT_RADAR_REQUEST_FAILED";
  }
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function EmployerTalentRadar({ token, refreshKey = 0, onInvitationCreated }: { token: string; refreshKey?: number; onInvitationCreated?: () => void }) {
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [draft, setDraft] = useState<Filters>(initialFilters);
  const [radar, setRadar] = useState<RadarResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [invitingCandidate, setInvitingCandidate] = useState<RadarCandidate | null>(null);
  const [salaryMin, setSalaryMin] = useState("180000");
  const [salaryMax, setSalaryMax] = useState("260000");
  const [offer, setOffer] = useState("");
  const [inviteBusy, setInviteBusy] = useState(false);
  const [inviteMessage, setInviteMessage] = useState<string | null>(null);

  async function load(nextFilters: Filters = filters) {
    setLoading(true);
    setMessage(null);
    const params = new URLSearchParams();
    if (nextFilters.query) params.set("q", nextFilters.query);
    if (nextFilters.specialization) params.set("specialization", nextFilters.specialization);
    if (nextFilters.grade) params.set("grade", nextFilters.grade);
    if (nextFilters.skill) params.set("skill", nextFilters.skill);
    params.set("fsp", nextFilters.fsp);
    params.set("include_unconfirmed", String(nextFilters.include_unconfirmed));
    params.set("blind", String(nextFilters.blind));
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/talent-radar?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const code = await readError(response);
        if (code === "HIRING_NEED_REQUIRED_FOR_TALENT_RADAR") {
          throw new Error("Сначала сохраните hiring need — она задаёт контекст Talent Radar.");
        }
        throw new Error(code);
      }
      setRadar((await response.json()) as RadarResponse);
      setFilters(nextFilters);
    } catch (error) {
      setRadar(null);
      setMessage((error as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(initialFilters);
    // The employer need save callback intentionally refreshes this projection.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, refreshKey]);

  const skills = useMemo(() => {
    if (!radar) return [];
    return [...radar.need.required_skills, ...radar.need.preferred_skills].filter(
      (skill, index, all) => all.findIndex((item) => item.slug === skill.slug) === index,
    );
  }, [radar]);

  function update<K extends keyof Filters>(key: K, value: Filters[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function openInvitation(candidate: RadarCandidate) {
    setInvitingCandidate(candidate);
    setOffer(`Приглашаем присоединиться к команде как ${candidate.category.label ?? "специалист"}.`);
    setInviteMessage(null);
  }

  async function sendInvitation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!invitingCandidate) return;
    setInviteBusy(true);
    setInviteMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/invitations`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_profile_id: invitingCandidate.candidate_id,
          salary_min_rub: Number(salaryMin),
          salary_max_rub: Number(salaryMax),
          offer_description: offer,
          blind_discovery: radar?.blind_discovery ?? false,
        }),
      });
      if (!response.ok) throw new Error(await readError(response));
      setInvitingCandidate(null);
      setMessage("Приглашение отправлено: кандидат увидит зарплату и offer во входящих.");
      onInvitationCreated?.();
    } catch (error) {
      const code = (error as Error).message;
      setInviteMessage(code === "INVITATION_COMPANY_CONTACT_REQUIRED" ? "Сначала заполните название компании и публичный способ связи." : code === "INVITATION_ALREADY_PENDING" ? "Для этого кандидата уже есть pending invitation." : "Не удалось отправить приглашение.");
    } finally {
      setInviteBusy(false);
    }
  }

  if (loading && !radar) return <section className="radarPanel muted">Строим Talent Radar по проверенным свидетельствам…</section>;
  if (!radar) {
    return (
      <section className="radarPanel error" aria-live="polite">
        <div className="radarHeading"><div><span className="authLabel">TALENT RADAR</span><h2>Talent Radar пока не готов</h2></div><button className="authButton secondaryButton" type="button" onClick={() => void load()}>Обновить</button></div>
        <p>{message ?? "Сохраните hiring need, чтобы открыть подбор."}</p>
      </section>
    );
  }

  return (
    <section className="radarPanel" aria-labelledby="talent-radar-title">
      <div className="radarHeading">
        <div>
          <span className="authLabel">PROOFMATCH · EVIDENCE GRAPH</span>
          <h2 id="talent-radar-title">Talent Radar</h2>
          <p>{radar.need.role} · {radar.need.specialization.name} · {radar.need.grade.name}</p>
        </div>
        <span className="profileStatus">{radar.total_candidates} CANDIDATES</span>
      </div>

      <form className="radarFilters" onSubmit={(event) => { event.preventDefault(); void load(draft); }}>
        <label>Поиск<input value={draft.query} onChange={(event) => update("query", event.target.value)} placeholder="Имя, роль или категория" /></label>
        <label>Специализация<input value={draft.specialization} onChange={(event) => update("specialization", event.target.value)} placeholder="Например, backend-engineering" /></label>
        <label>Грейд<input value={draft.grade} onChange={(event) => update("grade", event.target.value)} placeholder="middle" /></label>
        <label>Навык<select value={draft.skill} onChange={(event) => update("skill", event.target.value)}><option value="">Все навыки</option>{skills.map((skill) => <option key={skill.slug} value={skill.slug}>{skill.name}</option>)}</select></label>
        <label>FSP evidence<select value={draft.fsp} onChange={(event) => update("fsp", event.target.value as Filters["fsp"])}><option value="all">Все кандидаты</option><option value="with_history">Только с историей</option><option value="without_history">Без истории тоже</option></select></label>
        <label className="radarCheckbox"><input type="checkbox" checked={draft.include_unconfirmed} onChange={(event) => update("include_unconfirmed", event.target.checked)} /> Показывать grade not confirmed</label>
        <label className="radarCheckbox"><input type="checkbox" checked={draft.blind} onChange={(event) => update("blind", event.target.checked)} /> Blind Discovery: скрывать identity до match</label>
        <button className="authButton primaryButton" type="submit" disabled={loading}>{loading ? "Обновляем…" : "Применить фильтры"}</button>
      </form>

      {radar.blind_discovery && <div className="radarBlindNote"><strong>BLIND DISCOVERY</strong><span>Видны только category, ProofMatch и verified evidence. Salary-bearing invitation можно отправить анонимно; identity откроется работодателю только после acceptance кандидатом.</span></div>}

      <div className="radarSummary">
        <div><span>SNAPSHOT</span><strong>{radar.snapshot.id}</strong></div>
        <div><span>КАТЕГОРИИ</span><strong>{radar.categories.length}</strong></div>
        <div><span>СОСТОЯНИЕ</span><strong>{radar.snapshot.filters.include_unconfirmed ? "Verified + unconfirmed" : "Verified only"}</strong></div>
      </div>

      {radar.candidates.length === 0 ? (
        <div className="radarEmpty"><strong>Подходящих кандидатов пока нет</strong><span>Измените фильтр или сохраните больше подтверждённых свидетельств.</span></div>
      ) : (
        <div className="radarCandidates">
          {radar.candidates.map((candidate) => (
            <article className="radarCandidate" key={candidate.candidate_id}>
              <div className="radarCandidateTop">
                <div><span className="radarCandidateState">{candidate.eligibility === "verified" ? "✓ VERIFIED" : "! GRADE NOT CONFIRMED"}</span><h3>{candidate.display_name}</h3><p>{candidate.headline ?? "Профессиональный профиль"}{candidate.location ? ` · ${candidate.location}` : ""}</p></div>
                <div className="radarScore"><strong>{Math.round(candidate.match_score)}</strong><span>ProofMatch</span></div>
              </div>
              <div className="radarCategory"><span>{candidate.category.label ?? "Категория ещё не подтверждена"}</span><small>Уверенность {percent(candidate.confidence.overall)} · свежесть {percent(candidate.confidence.freshness)}</small></div>
              <div className="radarEvidenceChips">{candidate.evidence.required.filter((item) => item.present).map((item) => <span key={item.skill}>✓ {item.skill}</span>)}{candidate.fsp.score > 0 && <span>FSP +{candidate.fsp.score}</span>}</div>
              <ul className="radarReasons">{candidate.reasons.slice(0, 3).map((reason) => <li key={reason}>{reason}</li>)}</ul>
              <div className="radarFooter"><span>{candidate.gaps[0]}</span><button className="authButton secondaryButton" type="button" disabled={candidate.eligibility !== "verified"} title={candidate.eligibility === "verified" ? "Send a salary-bearing invitation" : "A confirmed platform grade is required"} onClick={() => openInvitation(candidate)}>{candidate.eligibility === "verified" ? "Пригласить" : "Нужен verified grade"}</button></div>
              {invitingCandidate?.candidate_id === candidate.candidate_id && (
                <form className="inviteForm" onSubmit={(event) => void sendInvitation(event)}>
                  <strong>Salary-bearing invitation</strong>
                  <div className="inviteFields"><label>От, ₽<input required min="1" type="number" value={salaryMin} onChange={(event) => setSalaryMin(event.target.value)} /></label><label>До, ₽<input required min="1" type="number" value={salaryMax} onChange={(event) => setSalaryMax(event.target.value)} /></label></div>
                  <label>Offer<textarea required maxLength={4000} rows={3} value={offer} onChange={(event) => setOffer(event.target.value)} /></label>
                  <div className="inviteActions"><button className="authButton primaryButton" type="submit" disabled={inviteBusy}>{inviteBusy ? "Отправляем…" : "Отправить invitation"}</button><button className="authButton secondaryButton" type="button" onClick={() => setInvitingCandidate(null)}>Отмена</button></div>
                  {inviteMessage && <small className="inviteError">{inviteMessage}</small>}
                </form>
              )}
            </article>
          ))}
        </div>
      )}
      <small className="radarPrivacyNote">Контакты, дата рождения и документы кандидата скрыты до действительного match.</small>
    </section>
  );
}
