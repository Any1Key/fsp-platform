"use client";

import { useEffect, useMemo, useState } from "react";

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
};
type RadarResponse = {
  need: {
    role: string;
    specialization: { name: string };
    grade: { name: string };
    required_skills: { slug: string; name: string }[];
    preferred_skills: { slug: string; name: string }[];
  };
  snapshot: { id: string; created_at: string; filters: { include_unconfirmed: boolean } };
  categories: {
    key: string;
    candidate_count: number;
    verified_count: number;
    unconfirmed_count: number;
  }[];
  candidates: RadarCandidate[];
  total_candidates: number;
};

type Filters = { query: string; specialization: string; grade: string; skill: string; fsp: "all" | "with_history" | "without_history"; include_unconfirmed: boolean };
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const initialFilters: Filters = { query: "", specialization: "", grade: "", skill: "", fsp: "all", include_unconfirmed: true };

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

export function EmployerTalentRadar({ token, refreshKey = 0 }: { token: string; refreshKey?: number }) {
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [draft, setDraft] = useState<Filters>(initialFilters);
  const [radar, setRadar] = useState<RadarResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

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
        <button className="authButton primaryButton" type="submit" disabled={loading}>{loading ? "Обновляем…" : "Применить фильтры"}</button>
      </form>

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
              <div className="radarFooter"><span>{candidate.gaps[0]}</span><button className="authButton secondaryButton" type="button" disabled title="Salary-bearing invitations arrive in the next hiring-pipeline milestone">Пригласить — скоро</button></div>
            </article>
          ))}
        </div>
      )}
      <small className="radarPrivacyNote">Контакты, дата рождения и документы кандидата скрыты до действительного match.</small>
    </section>
  );
}
