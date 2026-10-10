"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { EmptyState, ErrorState, LoadingState, UnconfirmedGradeBadge } from "./ui-state";

type SkillEvidence = { skill: string; present: boolean; edges: { source: string }[] };
type RadarCandidate = {
  candidate_id: string;
  display_name: string;
  headline: string | null;
  location: string | null;
  eligibility: "verified" | "unconfirmed";
  match_score: number;
  fit_band: "ready_now" | "strong_fit" | "potential_fit" | "explore";
  score_breakdown: Record<string, number>;
  category: {
    label: string | null;
    specialization: string | null;
    grade: string | null;
    grade_name: string | null;
    state: string;
  };
  confidence: { overall: number; grade: number; evidence: number; freshness: number };
  assessment: { score: number | null; status: string; assessed_at?: string | null };
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
    specialization_name?: string | null;
    grade_name?: string | null;
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

const fitBandLabels: Record<RadarCandidate["fit_band"], string> = {
  ready_now: "Ready now",
  strong_fit: "Strong fit",
  potential_fit: "Potential fit",
  explore: "Explore",
};

const scoreLabels: Record<string, string> = {
  specialization_fit: "Specialization fit",
  grade_fit: "Grade fit",
  required_skill_coverage: "Required skills",
  preferred_skill_coverage: "Preferred skills",
  assessment_strength: "Assessment strength",
  evidence_confidence_freshness: "Evidence confidence + freshness",
  fsp_bonus: "FSP evidence bonus",
};

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
  const [selectedCandidate, setSelectedCandidate] = useState<RadarCandidate | null>(null);

  useEffect(() => {
    if (!selectedCandidate) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setSelectedCandidate(null);
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [selectedCandidate]);

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
    setSelectedCandidate(null);
    setInvitingCandidate(candidate);
    setOffer(`Приглашаем присоединиться к команде как ${candidate.category.label ?? "специалист"}.`);
    setInviteMessage(null);
  }

  function resetFilters() {
    setDraft(initialFilters);
    void load(initialFilters);
  }

  const activeFilterCount = [
    filters.query,
    filters.specialization,
    filters.grade,
    filters.skill,
    filters.fsp !== "all" ? filters.fsp : "",
    !filters.include_unconfirmed ? "verified" : "",
    filters.blind ? "blind" : "",
  ].filter(Boolean).length;

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

  if (loading && !radar) return <section className="radarPanel muted"><LoadingState title="Строим Talent Radar по проверенным свидетельствам…" description="Собираем explainable ProofMatch snapshot." /></section>;
  if (!radar) {
    return (
      <section className="radarPanel error">
        <ErrorState title="Talent Radar пока не готов" description={message ?? "Сохраните hiring need, чтобы открыть подбор."}>
          <button className="authButton secondaryButton" type="button" onClick={() => void load()}>Обновить</button>
        </ErrorState>
      </section>
    );
  }

  return (
    <section className="radarPanel" aria-labelledby="talent-radar-title" aria-busy={loading}>
      <div className="radarHeading">
        <div>
          <span className="authLabel">PROOFMATCH · EVIDENCE GRAPH</span>
          <h2 id="talent-radar-title">Talent Radar</h2>
          <p>{radar.need.role} · {radar.need.specialization.name} · {radar.need.grade.name}</p>
        </div>
        <div className="radarHeadingMeta">
          <span className="profileStatus">{radar.total_candidates} CANDIDATES</span>
          {loading && <span className="radarRefreshing" role="status">Обновляем snapshot…</span>}
        </div>
      </div>

      <form className="radarFilters" onSubmit={(event) => { event.preventDefault(); void load(draft); }}>
        <label>Поиск<input value={draft.query} onChange={(event) => update("query", event.target.value)} placeholder="Имя, роль или категория" /></label>
        <label>Специализация<input value={draft.specialization} onChange={(event) => update("specialization", event.target.value)} placeholder="Например, backend-engineering" /></label>
        <label>Грейд<input value={draft.grade} onChange={(event) => update("grade", event.target.value)} placeholder="middle" /></label>
        <label>Навык<select value={draft.skill} onChange={(event) => update("skill", event.target.value)}><option value="">Все навыки</option>{skills.map((skill) => <option key={skill.slug} value={skill.slug}>{skill.name}</option>)}</select></label>
        <label>FSP evidence<select value={draft.fsp} onChange={(event) => update("fsp", event.target.value as Filters["fsp"])}><option value="all">Все кандидаты</option><option value="with_history">Только с историей</option><option value="without_history">Без истории тоже</option></select></label>
        <label className="radarCheckbox"><input type="checkbox" checked={draft.include_unconfirmed} onChange={(event) => update("include_unconfirmed", event.target.checked)} /> Показывать grade not confirmed</label>
        <label className="radarCheckbox"><input type="checkbox" checked={draft.blind} onChange={(event) => update("blind", event.target.checked)} /> Blind Discovery: скрывать identity до match</label>
        <div className="radarFilterActions">
          <button className="authButton primaryButton" type="submit" disabled={loading}>{loading ? "Обновляем…" : "Применить фильтры"}</button>
          <button className="authButton secondaryButton" type="button" disabled={loading || activeFilterCount === 0} onClick={resetFilters}>Сбросить{activeFilterCount > 0 ? ` (${activeFilterCount})` : ""}</button>
        </div>
      </form>

      {radar.blind_discovery && <div className="radarBlindNote"><strong>BLIND DISCOVERY</strong><span>Видны только category, ProofMatch и verified evidence. Salary-bearing invitation можно отправить анонимно; identity откроется работодателю только после acceptance кандидатом.</span></div>}

      <div className="radarSummary">
        <div><span>SNAPSHOT</span><strong>{radar.snapshot.id}</strong></div>
        <div><span>КАТЕГОРИИ</span><strong>{radar.categories.length}</strong></div>
        <div><span>СОСТОЯНИЕ</span><strong>{radar.snapshot.filters.include_unconfirmed ? "Verified + unconfirmed" : "Verified only"}</strong></div>
      </div>

      <div className="radarSupply" aria-label="Candidate supply by category">
        <div className="radarSupplyHeading">
          <div><span className="radarSectionKicker">CATEGORY SUPPLY</span><strong>Кого видно в этом snapshot</strong></div>
          <small>{radar.categories.length} {radar.categories.length === 1 ? "категория" : "категории"}</small>
        </div>
        <div className="radarSupplyGrid">
          {radar.categories.map((category) => (
            <div className="radarSupplyCard" key={category.key}>
              <strong>{category.key}</strong>
              <span>{category.candidate_count} {category.candidate_count === 1 ? "candidate" : "candidates"}</span>
              <small><i className="radarVerifiedDot" /> {category.verified_count} verified · <i className="radarUnconfirmedDot" /> {category.unconfirmed_count} not confirmed</small>
            </div>
          ))}
        </div>
      </div>

      {radar.candidates.length === 0 ? (
        <EmptyState className="radarEmpty" title="Подходящих кандидатов пока нет" description="Измените фильтр или сохраните больше подтверждённых свидетельств." />
      ) : (
        <div className="radarCandidates">
          {radar.candidates.map((candidate) => (
            <article className="radarCandidate" key={candidate.candidate_id}>
              <div className="radarCandidateTop">
                <div>{candidate.eligibility === "verified" ? <span className="radarCandidateState verified">✓ VERIFIED</span> : <UnconfirmedGradeBadge />}<h3>{candidate.display_name}</h3><p>{candidate.headline ?? "Профессиональный профиль"}{candidate.location ? ` · ${candidate.location}` : ""}</p></div>
                <div className="radarScore"><strong>{Math.round(candidate.match_score)}</strong><span>ProofMatch</span><em className={`fitBand ${candidate.fit_band}`}>{fitBandLabels[candidate.fit_band]}</em></div>
              </div>
              <div className="radarCategory"><span>{candidate.category.label ?? "Категория ещё не подтверждена"}</span><small>Уверенность {percent(candidate.confidence.overall)} · свежесть {percent(candidate.confidence.freshness)}</small></div>
              <div className="radarEvidenceChips">{candidate.evidence.required.filter((item) => item.present).map((item) => <span key={item.skill}>✓ {item.skill}</span>)}{candidate.fsp.score > 0 && <span>FSP +{candidate.fsp.score}</span>}</div>
              <ul className="radarReasons">{candidate.reasons.slice(0, 3).map((reason) => <li key={reason}>{reason}</li>)}</ul>
              <div className="radarFooter"><span>{candidate.gaps[0]}</span><div className="radarCardActions"><button className="authButton secondaryButton" type="button" onClick={() => setSelectedCandidate(candidate)}>View proof</button><button className="authButton primaryButton" type="button" disabled={candidate.eligibility !== "verified"} title={candidate.eligibility === "verified" ? "Send a salary-bearing invitation" : "A confirmed platform grade is required"} onClick={() => openInvitation(candidate)}>{candidate.eligibility === "verified" ? "Пригласить" : "Нужен verified grade"}</button></div></div>
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

      {selectedCandidate && (
        <div className="radarDialogBackdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedCandidate(null); }}>
          <section className="radarDialog" role="dialog" aria-modal="true" aria-labelledby="radar-dialog-title">
            <div className="radarDialogHeading">
              <div><span className="authLabel">PROOFMATCH EXPLANATION</span><h3 id="radar-dialog-title">{selectedCandidate.display_name}</h3><p>{selectedCandidate.category.label ?? "Категория ещё не подтверждена"} · {fitBandLabels[selectedCandidate.fit_band]}</p></div>
              <button className="radarCloseButton" type="button" aria-label="Закрыть объяснение" onClick={() => setSelectedCandidate(null)}>×</button>
            </div>
            <div className="radarDialogScore"><strong>{Math.round(selectedCandidate.match_score)}</strong><span>из 100 · ProofMatch</span><small>{selectedCandidate.eligibility === "verified" ? "Категория подтверждена assessment-результатом." : "Grade ещё не подтверждён; кандидат остаётся доступен для исследования."}</small></div>
            <div className="radarBreakdown"><h4>Score breakdown</h4>{Object.entries(selectedCandidate.score_breakdown).map(([key, value]) => <div className="radarBreakdownRow" key={key}><span>{scoreLabels[key] ?? key}</span><strong>{value.toFixed(1)}</strong><div className="radarBreakdownTrack"><i style={{ width: `${Math.min(100, (value / (key === "fsp_bonus" ? 10 : key === "specialization_fit" ? 20 : key === "grade_fit" ? 15 : key === "required_skill_coverage" ? 25 : key === "preferred_skill_coverage" ? 10 : key === "assessment_strength" ? 15 : 5)) * 100)}%` }} /></div></div>)}</div>
            <div className="radarDialogGrid"><div><h4>Confidence</h4><p>Grade <strong>{percent(selectedCandidate.confidence.grade)}</strong></p><p>Evidence <strong>{percent(selectedCandidate.confidence.evidence)}</strong></p><p>Freshness <strong>{percent(selectedCandidate.confidence.freshness)}</strong></p></div><div><h4>Evidence gaps</h4><ul>{selectedCandidate.gaps.map((gap) => <li key={gap}>{gap}</li>)}</ul></div></div>
            <div className="radarDialogEvidence"><h4>Verified evidence</h4><div className="radarEvidenceList">{[...selectedCandidate.evidence.required, ...selectedCandidate.evidence.preferred].filter((item) => item.present).map((item) => <span key={item.skill}>✓ {item.skill}<small>{item.edges.some((edge) => edge.source === "fsp_achievement") ? "FSP registry" : "Candidate profile"}</small></span>)}{selectedCandidate.evidence.required.every((item) => !item.present) && selectedCandidate.evidence.preferred.every((item) => !item.present) && <small>Пока нет совпавших skill evidence.</small>}</div></div>
            <div className="radarDialogActions"><button className="authButton secondaryButton" type="button" onClick={() => setSelectedCandidate(null)}>Закрыть</button><button className="authButton primaryButton" type="button" disabled={selectedCandidate.eligibility !== "verified"} onClick={() => openInvitation(selectedCandidate)}>{selectedCandidate.eligibility === "verified" ? "Пригласить с зарплатой" : "Нужен verified grade"}</button></div>
          </section>
        </div>
      )}
    </section>
  );
}
