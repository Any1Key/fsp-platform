"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

type Company = {
  name: string | null;
  description: string | null;
  industry: string | null;
  website: string | null;
  location: string | null;
  public_contact_method: string | null;
};

type Draft = {
  name: string;
  description: string;
  industry: string;
  website: string;
  location: string;
  public_contact_method: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function toDraft(company: Company): Draft {
  return {
    name: company.name ?? "",
    description: company.description ?? "",
    industry: company.industry ?? "",
    website: company.website ?? "",
    location: company.location ?? "",
    public_contact_method: company.public_contact_method ?? "",
  };
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { code?: string } };
    return body.error?.code ?? "COMPANY_PROFILE_REQUEST_FAILED";
  } catch {
    return "COMPANY_PROFILE_REQUEST_FAILED";
  }
}

export function EmployerCompanyProfile({ token }: { token: string }) {
  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch(`${apiUrl}/api/v1/employer/company`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(await readError(response));
        return (await response.json()) as Company;
      })
      .then((company) => {
        if (active) setDraft(toDraft(company));
      })
      .catch((error: Error) => {
        if (active) setMessage(`Профиль компании недоступен: ${error.message}`);
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

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft) return;
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/employer/company`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          name: draft.name || null,
          description: draft.description || null,
          industry: draft.industry || null,
          website: draft.website || null,
          location: draft.location || null,
          public_contact_method: draft.public_contact_method || null,
        }),
      });
      if (!response.ok) {
        const code = await readError(response);
        if (code === "COMPANY_NAME_REQUIRED") throw new Error("Укажите название компании.");
        throw new Error(code);
      }
      setDraft(toDraft((await response.json()) as Company));
      setMessage("Профиль компании сохранен");
    } catch (error) {
      setMessage(`Не удалось сохранить: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <section className="companyPanel muted">Загружаем профиль компании…</section>;
  if (!draft) return <section className="companyPanel error">{message ?? "Профиль компании недоступен"}</section>;

  return (
    <section className="companyPanel" aria-labelledby="company-profile-title">
      <div className="companyHeading">
        <div>
          <span className="authLabel">EMPLOYER PROFILE</span>
          <h2 id="company-profile-title">Профиль компании</h2>
          <p>Заполните основу, которая появится в Talent Radar и приглашениях.</p>
        </div>
        <span className="profileStatus">EMPLOYER-OWNED</span>
      </div>
      <form className="companyForm" onSubmit={save}>
        <div className="profileGrid">
          <label>Название компании<input required maxLength={160} value={draft.name} onChange={(event) => change("name", event.target.value)} placeholder="North Star Labs" /></label>
          <label>Индустрия<input maxLength={120} value={draft.industry} onChange={(event) => change("industry", event.target.value)} placeholder="Разработка ПО" /></label>
          <label>Город / регион<input maxLength={120} value={draft.location} onChange={(event) => change("location", event.target.value)} placeholder="Москва" /></label>
          <label>Сайт<input type="url" maxLength={255} value={draft.website} onChange={(event) => change("website", event.target.value)} placeholder="https://company.ru" /></label>
        </div>
        <label>О компании<textarea maxLength={4000} rows={4} value={draft.description} onChange={(event) => change("description", event.target.value)} placeholder="Какие задачи и продукты создаёт команда" /></label>
        <label>Публичный контакт для найма<input maxLength={160} value={draft.public_contact_method} onChange={(event) => change("public_contact_method", event.target.value)} placeholder="Почта, Telegram или другой согласованный канал" /></label>
        <div className="companyFooter">
          <small aria-live="polite">{message ?? "Контакт публикуется только как явно указанный вами способ связи."}</small>
          <button className="authButton primaryButton" type="submit" disabled={saving}>{saving ? "Сохраняем…" : "Сохранить компанию"}</button>
        </div>
      </form>
    </section>
  );
}
