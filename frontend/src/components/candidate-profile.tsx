"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

type Experience = {
  role: string;
  company: string;
  started_on: string;
  ended_on: string | null;
  description: string | null;
  technologies: string[];
};

type Profile = {
  display_name: string | null;
  headline: string | null;
  location: string | null;
  summary: string | null;
  experience: Experience[];
  skills: string[];
  work_preferences: {
    work_mode?: "office" | "hybrid" | "remote";
    employment_type?: "full_time" | "part_time" | "project";
    availability?: string;
  };
};

type Draft = {
  display_name: string;
  headline: string;
  location: string;
  summary: string;
  skills: string;
  experience: Experience[];
  work_mode: "" | "office" | "hybrid" | "remote";
  employment_type: "" | "full_time" | "part_time" | "project";
  availability: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function emptyExperience(): Experience {
  return {
    role: "",
    company: "",
    started_on: "",
    ended_on: null,
    description: null,
    technologies: [],
  };
}

function toDraft(profile: Profile): Draft {
  return {
    display_name: profile.display_name ?? "",
    headline: profile.headline ?? "",
    location: profile.location ?? "",
    summary: profile.summary ?? "",
    skills: profile.skills.join(", "),
    experience: profile.experience,
    work_mode: profile.work_preferences.work_mode ?? "",
    employment_type: profile.work_preferences.employment_type ?? "",
    availability: profile.work_preferences.availability ?? "",
  };
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { code?: string } };
    return body.error?.code ?? "PROFILE_REQUEST_FAILED";
  } catch {
    return "PROFILE_REQUEST_FAILED";
  }
}

export function CandidateProfile({ token }: { token: string }) {
  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch(`${apiUrl}/api/v1/candidate/profile`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(await readError(response));
        return (await response.json()) as Profile;
      })
      .then((profile) => {
        if (active) setDraft(toDraft(profile));
      })
      .catch((error: Error) => {
        if (active) setMessage(`Профиль недоступен: ${error.message}`);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  function change<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
    setMessage(null);
  }

  function changeExperience(index: number, key: keyof Experience, value: string) {
    setDraft((current) => {
      if (!current) return current;
      const experience = current.experience.map((item, itemIndex) =>
        itemIndex === index
          ? { ...item, [key]: key === "ended_on" && value === "" ? null : value }
          : item,
      );
      return { ...current, experience };
    });
    setMessage(null);
  }

  function removeExperience(index: number) {
    setDraft((current) =>
      current ? { ...current, experience: current.experience.filter((_, i) => i !== index) } : current,
    );
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft) return;
    setSaving(true);
    setMessage(null);
    const experience = draft.experience.map((item) => ({
      ...item,
      description: item.description || null,
      ended_on: item.ended_on || null,
      technologies: item.technologies ?? [],
    }));
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/profile`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          display_name: draft.display_name || null,
          headline: draft.headline || null,
          location: draft.location || null,
          summary: draft.summary || null,
          skills: draft.skills.split(",").map((skill) => skill.trim()).filter(Boolean),
          experience,
          work_preferences: {
            work_mode: draft.work_mode || null,
            employment_type: draft.employment_type || null,
            availability: draft.availability || null,
          },
        }),
      });
      if (!response.ok) {
        const code = await readError(response);
        if (code === "PROCESSING_CONSENT_REQUIRED") {
          throw new Error("Сначала разрешите обработку данных в настройках приватности.");
        }
        throw new Error(code);
      }
      setDraft(toDraft((await response.json()) as Profile));
      setMessage("Профиль сохранен");
    } catch (error) {
      setMessage(`Не удалось сохранить: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <section className="profilePanel muted">Загружаем профиль…</section>;
  if (!draft) return <section className="profilePanel error">{message ?? "Профиль недоступен"}</section>;

  return (
    <section className="profilePanel" aria-label="Профиль кандидата">
      <div className="profileHeading">
        <div>
          <span className="authLabel">CANDIDATE PROFILE</span>
          <strong>Профессиональный профиль</strong>
          <small>Заполните основу — позже добавятся резюме и подтвержденные навыки.</small>
        </div>
        <span className="profileStatus">SELF-SCOPED</span>
      </div>
      <form className="profileForm" onSubmit={save}>
        <div className="profileGrid">
          <label>Имя и фамилия<input value={draft.display_name} maxLength={120} onChange={(event) => change("display_name", event.target.value)} placeholder="Иван Петров" /></label>
          <label>Профессиональный заголовок<input value={draft.headline} maxLength={160} onChange={(event) => change("headline", event.target.value)} placeholder="Backend engineer" /></label>
          <label>Город<input value={draft.location} maxLength={120} onChange={(event) => change("location", event.target.value)} placeholder="Москва" /></label>
          <label>Формат работы<select value={draft.work_mode} onChange={(event) => change("work_mode", event.target.value as Draft["work_mode"])}><option value="">Не указан</option><option value="office">Офис</option><option value="hybrid">Гибрид</option><option value="remote">Удаленно</option></select></label>
        </div>
        <label>О себе<textarea value={draft.summary} maxLength={2000} rows={4} onChange={(event) => change("summary", event.target.value)} placeholder="Коротко о сильных сторонах и типе задач" /></label>
        <label>Навыки <small>через запятую</small><input value={draft.skills} onChange={(event) => change("skills", event.target.value)} placeholder="Python, FastAPI, PostgreSQL" /></label>
        <div className="experienceHeading"><strong>Опыт работы</strong><button type="button" className="textButton" onClick={() => change("experience", [...draft.experience, emptyExperience()])}>+ Добавить</button></div>
        {draft.experience.map((item, index) => (
          <fieldset className="experienceCard" key={`${index}-${item.company}`}>
            <legend>Опыт {index + 1}</legend>
            <button type="button" className="removeButton" onClick={() => removeExperience(index)} aria-label={`Удалить опыт ${index + 1}`}>Удалить</button>
            <div className="profileGrid">
              <label>Роль<input required value={item.role} onChange={(event) => changeExperience(index, "role", event.target.value)} /></label>
              <label>Компания<input required value={item.company} onChange={(event) => changeExperience(index, "company", event.target.value)} /></label>
              <label>Начало<input required type="month" value={item.started_on} onChange={(event) => changeExperience(index, "started_on", event.target.value)} /></label>
              <label>Окончание<input type="month" value={item.ended_on === "present" ? "" : item.ended_on ?? ""} onChange={(event) => changeExperience(index, "ended_on", event.target.value)} /><small>Пусто — текущая работа</small></label>
            </div>
            <label>Что делали<textarea rows={2} maxLength={1000} value={item.description ?? ""} onChange={(event) => changeExperience(index, "description", event.target.value)} /></label>
          </fieldset>
        ))}
        <div className="profileFooter">
          <small aria-live="polite">{message ?? "Профиль виден только вам на этом этапе."}</small>
          <button className="authButton primaryButton" type="submit" disabled={saving}>{saving ? "Сохраняем…" : "Сохранить профиль"}</button>
        </div>
      </form>
    </section>
  );
}
