"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

type TaxonomySkill = { slug: string; name: string };
type Specialization = { slug: string; name: string; skills: TaxonomySkill[] };
type Taxonomy = { specializations: Specialization[]; grades: { slug: string; name: string }[] };
type HiringNeed = {
  team: string;
  role: string;
  specialization: { slug: string; name: string };
  grade: { slug: string; name: string };
  required_skills: TaxonomySkill[];
  preferred_skills: TaxonomySkill[];
};
type Draft = {
  team: string;
  role: string;
  specialization: string;
  grade: string;
  required_skills: string[];
  preferred_skills: string[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function draftFromNeed(need: HiringNeed | null, taxonomy: Taxonomy): Draft {
  return {
    team: need?.team ?? "",
    role: need?.role ?? "",
    specialization: need?.specialization.slug ?? taxonomy.specializations[0]?.slug ?? "",
    grade: need?.grade.slug ?? taxonomy.grades[0]?.slug ?? "",
    required_skills: need?.required_skills.map((skill) => skill.slug) ?? [],
    preferred_skills: need?.preferred_skills.map((skill) => skill.slug) ?? [],
  };
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { code?: string } };
    return body.error?.code ?? "HIRING_NEED_REQUEST_FAILED";
  } catch {
    return "HIRING_NEED_REQUEST_FAILED";
  }
}

export function EmployerHiringNeed({ token, onSaved }: { token: string; onSaved?: () => void }) {
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [exists, setExists] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      fetch(`${apiUrl}/api/v1/taxonomy`).then(async (response) => {
        if (!response.ok) throw new Error(await readError(response));
        return (await response.json()) as Taxonomy;
      }),
      fetch(`${apiUrl}/api/v1/employer/hiring-need`, { headers: { Authorization: `Bearer ${token}` } }).then(async (response) => {
        if (!response.ok) throw new Error(await readError(response));
        return (await response.json()) as HiringNeed | null;
      }),
    ])
      .then(([catalog, need]) => {
        if (!active) return;
        setTaxonomy(catalog);
        setExists(Boolean(need));
        setDraft(draftFromNeed(need, catalog));
      })
      .catch((error: Error) => {
        if (active) setMessage(`Потребность недоступна: ${error.message}`);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  const skills = useMemo(() => {
    const unique = new Map<string, TaxonomySkill>();
    taxonomy?.specializations.forEach((specialization) => specialization.skills.forEach((skill) => unique.set(skill.slug, skill)));
    return Array.from(unique.values()).sort((left, right) => left.name.localeCompare(right.name));
  }, [taxonomy]);

  function setField<K extends keyof Draft>(field: K, value: Draft[K]) {
    setDraft((current) => (current ? { ...current, [field]: value } : current));
    setMessage(null);
  }

  function setSkill(slug: string, preference: "required_skills" | "preferred_skills", selected: boolean) {
    if (!draft) return;
    const other = preference === "required_skills" ? "preferred_skills" : "required_skills";
    const next = new Set(draft[preference]);
    if (selected) next.add(slug); else next.delete(slug);
    setDraft({ ...draft, [preference]: Array.from(next), [other]: draft[other].filter((item) => item !== slug) });
    setMessage(null);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft) return;
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/hiring-need`, {
        method: exists ? "PATCH" : "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      if (!response.ok) {
        const code = await readError(response);
        const messages: Record<string, string> = {
          HIRING_NEED_FIELDS_REQUIRED: "Заполните команду, роль, специализацию и грейд.",
          HIRING_NEED_SKILLS_REQUIRED: "Выберите хотя бы один навык.",
          HIRING_NEED_SKILL_NOT_AVAILABLE: "Один из навыков больше недоступен в каталоге.",
        };
        throw new Error(messages[code] ?? code);
      }
      const saved = (await response.json()) as HiringNeed;
      setDraft(draftFromNeed(saved, taxonomy as Taxonomy));
      setExists(true);
      setMessage("Параметры поиска сохранены — можно подбирать кандидатов.");
      onSaved?.();
    } catch (error) {
      setMessage(`Не удалось сохранить: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <section className="hiringNeedPanel muted">Загружаем каталог и параметры поиска…</section>;
  if (!taxonomy || !draft) return <section className="hiringNeedPanel error">{message ?? "Потребность недоступна"}</section>;

  return (
    <section className="hiringNeedPanel" aria-labelledby="hiring-need-title">
      <div className="companyHeading">
        <div>
          <span className="authLabel">ПАРАМЕТРЫ ПОИСКА</span>
          <h2 id="hiring-need-title">Параметры поиска</h2>
          <p>Опишите контекст найма и отделите обязательные навыки от желательных.</p>
        </div>
        <span className="profileStatus">ГОТОВО К ПОИСКУ</span>
      </div>
      <form className="hiringNeedForm" onSubmit={save}>
        <div className="profileGrid">
          <label>Команда<input required maxLength={160} value={draft.team} onChange={(event) => setField("team", event.target.value)} placeholder="Platform engineering" /></label>
          <label>Роль<input required maxLength={160} value={draft.role} onChange={(event) => setField("role", event.target.value)} placeholder="Backend engineer" /></label>
          <label>Специализация<select required value={draft.specialization} onChange={(event) => setField("specialization", event.target.value)}>{taxonomy.specializations.map((item) => <option key={item.slug} value={item.slug}>{item.name}</option>)}</select></label>
          <label>Целевой грейд<select required value={draft.grade} onChange={(event) => setField("grade", event.target.value)}>{taxonomy.grades.map((item) => <option key={item.slug} value={item.slug}>{item.name}</option>)}</select></label>
        </div>
        <div className="skillPreferenceGrid">
          {(["required_skills", "preferred_skills"] as const).map((preference) => (
            <fieldset className="skillPreference" key={preference}>
              <legend>{preference === "required_skills" ? "Обязательные навыки" : "Желательные навыки"}</legend>
              {skills.map((skill) => (
                <label key={`${preference}-${skill.slug}`} className="skillChoice">
                  <input type="checkbox" checked={draft[preference].includes(skill.slug)} onChange={(event) => setSkill(skill.slug, preference, event.target.checked)} />
                  <span>{skill.name}</span>
                </label>
              ))}
            </fieldset>
          ))}
        </div>
        <div className="companyFooter">
          <small aria-live="polite">{message ?? "Навыки сохраняются как структурированная потребность работодателя."}</small>
          <button className="authButton primaryButton" type="submit" disabled={saving}>{saving ? "Сохраняем…" : exists ? "Обновить потребность" : "Сохранить потребность"}</button>
        </div>
      </form>
    </section>
  );
}
