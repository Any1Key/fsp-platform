"use client";

import { useEffect, useState } from "react";

type PrivacyState = {
  processing_consent: boolean;
  processing_consent_version: string | null;
  processing_consent_at: string | null;
  publication_consent: boolean;
  publication_consent_version: string | null;
  publication_consent_at: string | null;
  discoverable: boolean;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { code?: string } };
    return body.error?.code ?? "PRIVACY_REQUEST_FAILED";
  } catch {
    return "PRIVACY_REQUEST_FAILED";
  }
}

export function PrivacySettings({ token }: { token: string }) {
  const [privacy, setPrivacy] = useState<PrivacyState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [exportStatus, setExportStatus] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch(`${apiUrl}/api/v1/candidate/privacy`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(await readError(response));
        return (await response.json()) as PrivacyState;
      })
      .then((state) => {
        if (active) setPrivacy(state);
      })
      .catch((error: Error) => {
        if (active) setMessage(`Не удалось загрузить настройки: ${error.message}`);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  async function change(setting: "processing_consent" | "publication_consent" | "discoverable", value: boolean) {
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/privacy`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ [setting]: value }),
      });
      if (!response.ok) throw new Error(await readError(response));
      setPrivacy((await response.json()) as PrivacyState);
      setMessage("Настройки сохранены");
    } catch (error) {
      setMessage(`Изменение не сохранено: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  async function requestExport() {
    setExportStatus("Отправляем запрос…");
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/privacy/export`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error(await readError(response));
      const result = (await response.json()) as { status: string };
      setExportStatus(`Запрос зарегистрирован: ${result.status}`);
    } catch (error) {
      setExportStatus(`Не удалось отправить запрос: ${(error as Error).message}`);
    }
  }

  if (loading) return <div className="privacyPanel muted">Загружаем настройки приватности…</div>;
  if (!privacy) return <div className="privacyPanel error">{message ?? "Настройки недоступны"}</div>;

  return (
    <section className="privacyPanel" aria-label="Настройки приватности">
      <div className="privacyHeading">
        <div>
          <span className="authLabel">PRIVACY CONTROL</span>
          <strong>Приватность и доступность профиля</strong>
        </div>
        <small>Политика {privacy.processing_consent_version ?? "не принята"}</small>
      </div>
      <label className="privacyOption">
        <input
          type="checkbox"
          checked={privacy.processing_consent}
          disabled={saving}
          onChange={(event) => change("processing_consent", event.target.checked)}
        />
        <span>Разрешаю обработку данных для работы платформы</span>
      </label>
      <label className="privacyOption">
        <input
          type="checkbox"
          checked={privacy.publication_consent}
          disabled={saving || !privacy.processing_consent}
          onChange={(event) => change("publication_consent", event.target.checked)}
        />
        <span>Разрешаю показывать профессиональный профиль работодателям</span>
      </label>
      <label className="privacyOption">
        <input
          type="checkbox"
          checked={privacy.discoverable}
          disabled={saving || !privacy.publication_consent}
          onChange={(event) => change("discoverable", event.target.checked)}
        />
        <span>Сделать профиль доступным для Talent Radar</span>
      </label>
      {message && <small className="privacyMessage">{message}</small>}
      <button className="authButton secondaryButton" disabled={saving} onClick={requestExport}>
        Запросить экспорт моих данных
      </button>
      {exportStatus && <small className="privacyMessage">{exportStatus}</small>}
    </section>
  );
}
