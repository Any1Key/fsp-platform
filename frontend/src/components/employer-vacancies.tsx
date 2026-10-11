"use client";

import { useEffect, useState, type FormEvent } from "react";

type VacancyStatus = "draft" | "published" | "closed";
type Vacancy = {
  id: string;
  title: string;
  description: string;
  location: string | null;
  work_mode: "office" | "hybrid" | "remote" | null;
  employment_type: "full_time" | "part_time" | "project" | null;
  salary_min_rub: number;
  salary_max_rub: number;
  status: VacancyStatus;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};
type Draft = Omit<Vacancy, "id" | "status" | "published_at" | "created_at" | "updated_at">;

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const emptyDraft: Draft = {
  title: "",
  description: "",
  location: "",
  work_mode: "hybrid",
  employment_type: "full_time",
  salary_min_rub: 180000,
  salary_max_rub: 260000,
};

async function errorCode(response: Response) {
  try {
    const body = (await response.json()) as { error?: { code?: string } };
    return body.error?.code ?? "VACANCY_REQUEST_FAILED";
  } catch {
    return "VACANCY_REQUEST_FAILED";
  }
}

function draftFromVacancy(vacancy: Vacancy): Draft {
  return {
    title: vacancy.title,
    description: vacancy.description,
    location: vacancy.location ?? "",
    work_mode: vacancy.work_mode,
    employment_type: vacancy.employment_type,
    salary_min_rub: vacancy.salary_min_rub,
    salary_max_rub: vacancy.salary_max_rub,
  };
}

function statusLabel(status: VacancyStatus) {
  return status === "published" ? "PUBLISHED" : status === "closed" ? "CLOSED" : "DRAFT";
}

export function EmployerVacancies({ token }: { token: string }) {
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/vacancies`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error(await errorCode(response));
      const items = (await response.json()) as Vacancy[];
      setVacancies(items);
      if (selectedId) {
        const selected = items.find((item) => item.id === selectedId);
        if (selected) setDraft(draftFromVacancy(selected));
      }
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // The employer token is the only external identity dependency for this panel.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  function select(vacancy: Vacancy) {
    setSelectedId(vacancy.id);
    setDraft(draftFromVacancy(vacancy));
    setMessage(null);
  }

  function startNew() {
    setSelectedId(null);
    setDraft({ ...emptyDraft });
    setMessage(null);
  }

  function change<K extends keyof Draft>(field: K, value: Draft[K]) {
    setDraft((current) => ({ ...current, [field]: value }));
    setMessage(null);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(
        `${apiUrl}/api/v1/employer/vacancies${selectedId ? `/${selectedId}` : ""}`,
        {
          method: selectedId ? "PATCH" : "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ ...draft, location: draft.location || null }),
        },
      );
      if (!response.ok) {
        const code = await errorCode(response);
        const messages: Record<string, string> = {
          VACANCY_SALARY_INVALID: "Проверьте диапазон зарплаты: минимум не выше максимума.",
          VACANCY_FIELDS_REQUIRED: "Укажите название и описание вакансии.",
        };
        throw new Error(messages[code] ?? code);
      }
      const saved = (await response.json()) as Vacancy;
      setSelectedId(saved.id);
      setDraft(draftFromVacancy(saved));
      setMessage("Вакансия сохранена как черновик.");
      await load();
    } catch (error) {
      setMessage(`Не удалось сохранить: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  async function transition(path: "publish" | "close") {
    if (!selectedId) return;
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/vacancies/${selectedId}/${path}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error(await errorCode(response));
      const changed = (await response.json()) as Vacancy;
      setDraft(draftFromVacancy(changed));
      setMessage(path === "publish" ? "Вакансия опубликована." : "Вакансия закрыта, история сохранена.");
      await load();
    } catch (error) {
      setMessage(`Не удалось изменить статус: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <section className="vacancyPanel muted">Загружаем вакансии…</section>;

  const selected = vacancies.find((vacancy) => vacancy.id === selectedId) ?? null;
  const closed = selected?.status === "closed";

  return (
    <section className="vacancyPanel" aria-labelledby="vacancies-title">
      <div className="companyHeading">
        <div>
          <span className="authLabel">ВАКАНСИИ КОМПАНИИ</span>
          <h2 id="vacancies-title">Публикации с зарплатой</h2>
          <p>Создайте понятное предложение для кандидата. Зарплата обязательна до публикации.</p>
        </div>
        <span className="profileStatus">{vacancies.length} VACANCIES</span>
      </div>
      <div className="vacancyToolbar">
        <div className="vacancyList" aria-label="Вакансии работодателя">
          {vacancies.length === 0 ? (
            <div className="vacancyEmpty"><strong>Пока нет вакансий</strong><span>Начните с черновика — его можно проверить перед публикацией.</span></div>
          ) : vacancies.map((vacancy) => (
            <button className={`vacancyListItem${selectedId === vacancy.id ? " active" : ""}`} key={vacancy.id} type="button" onClick={() => select(vacancy)}>
              <strong>{vacancy.title}</strong>
              <small>{statusLabel(vacancy.status)} · ₽{vacancy.salary_min_rub.toLocaleString("ru-RU")}–{vacancy.salary_max_rub.toLocaleString("ru-RU")}</small>
            </button>
          ))}
          <button className="vacancyNewButton" type="button" onClick={startNew}>+ Новая вакансия</button>
        </div>
        <form className="vacancyForm" onSubmit={(event) => void save(event)}>
          <div className="vacancyFormTop">
            <strong>{selected ? selected.title : "Новый черновик"}</strong>
            {selected && <span className={`vacancyStatus ${selected.status}`}>{statusLabel(selected.status)}</span>}
          </div>
          <label>Название<input required maxLength={160} disabled={closed} value={draft.title} onChange={(event) => change("title", event.target.value)} placeholder="Backend engineer" /></label>
          <label>Описание задачи<textarea required maxLength={12000} rows={5} disabled={closed} value={draft.description} onChange={(event) => change("description", event.target.value)} placeholder="Что предстоит создавать и за что отвечает команда" /></label>
          <div className="vacancyFields">
            <label>Зарплата от, ₽<input required min={1} type="number" disabled={closed} value={draft.salary_min_rub} onChange={(event) => change("salary_min_rub", Number(event.target.value))} /></label>
            <label>Зарплата до, ₽<input required min={1} type="number" disabled={closed} value={draft.salary_max_rub} onChange={(event) => change("salary_max_rub", Number(event.target.value))} /></label>
            <label>Город / регион<input maxLength={120} disabled={closed} value={draft.location ?? ""} onChange={(event) => change("location", event.target.value)} placeholder="Москва" /></label>
            <label>Формат<select disabled={closed} value={draft.work_mode ?? ""} onChange={(event) => change("work_mode", (event.target.value || null) as Draft["work_mode"])}><option value="">Не указан</option><option value="office">Офис</option><option value="hybrid">Гибрид</option><option value="remote">Удалённо</option></select></label>
          </div>
          <div className="vacancyFooter">
            <small aria-live="polite">{message ?? "После публикации ваканция появится в общем списке кандидатов в следующем M11 шаге."}</small>
            <div className="vacancyActions">
              <button className="authButton primaryButton" type="submit" disabled={saving || closed}>{saving ? "Сохраняем…" : selected ? "Сохранить изменения" : "Сохранить черновик"}</button>
              {selected?.status === "draft" && <button className="authButton secondaryButton" type="button" disabled={saving} onClick={() => void transition("publish")}>Опубликовать</button>}
              {selected?.status === "published" && <button className="authButton secondaryButton" type="button" disabled={saving} onClick={() => void transition("close")}>Закрыть</button>}
            </div>
          </div>
        </form>
      </div>
    </section>
  );
}
