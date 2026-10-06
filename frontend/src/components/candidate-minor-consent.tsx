"use client";

import { useEffect, useState } from "react";

type MinorConsentDocument = {
  id: string;
  policy_version: string;
  original_filename: string;
  content_type: "application/pdf";
  size_bytes: number;
  status: "submitted" | "approved" | "rejected" | "replaced" | "withdrawn";
  uploaded_at: string;
};

type MinorConsentState = {
  minor_state: "not_set" | "minor" | "adult";
  required: boolean;
  policy_version: string;
  document: MinorConsentDocument | null;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { code?: string } };
    return body.error?.code ?? "MINOR_DOCUMENT_REQUEST_FAILED";
  } catch {
    return "MINOR_DOCUMENT_REQUEST_FAILED";
  }
}

function humanError(code: string): string {
  const messages: Record<string, string> = {
    MINOR_DOCUMENT_PROCESSING_CONSENT_REQUIRED: "Сначала разрешите обработку данных.",
    MINOR_DOCUMENT_INVALID_TYPE: "Нужен PDF-файл.",
    MINOR_DOCUMENT_INVALID_PDF: "Файл не похож на PDF-документ.",
    MINOR_DOCUMENT_TOO_LARGE: "Файл превышает установленный лимит размера.",
  };
  return messages[code] ?? code;
}

function formatSize(bytes: number): string {
  return `${(bytes / 1024 / 1024).toFixed(2)} МБ`;
}

export function CandidateMinorConsent({ token }: { token: string }) {
  const [state, setState] = useState<MinorConsentState | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch(`${apiUrl}/api/v1/candidate/minor-consent-document`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(await readError(response));
        return (await response.json()) as MinorConsentState;
      })
      .then((nextState) => {
        if (active) setState(nextState);
      })
      .catch((error: Error) => {
        if (active) setMessage(`Статус документа недоступен: ${humanError(error.message)}`);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  async function upload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setMessage(null);
    try {
      const form = new FormData();
      form.append("document", file);
      const response = await fetch(`${apiUrl}/api/v1/candidate/minor-consent-document`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!response.ok) throw new Error(await readError(response));
      setState((await response.json()) as MinorConsentState);
      setMessage("Документ загружен в защищённое хранилище.");
    } catch (error) {
      setMessage(`Не удалось загрузить документ: ${humanError((error as Error).message)}`);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  if (loading) return <section className="minorConsentPanel muted">Проверяем статус документа…</section>;
  if (!state) return <section className="minorConsentPanel error">{message ?? "Статус документа недоступен"}</section>;
  if (!state.required) return null;

  return (
    <section className="minorConsentPanel" aria-label="Согласие родителя или законного представителя">
      <div className="profileHeading">
        <div>
          <span className="authLabel">PRIVATE DOCUMENT</span>
          <strong>Согласие родителя или представителя</strong>
          <small>Документ хранится отдельно и не виден работодателям.</small>
        </div>
        <span className="profileStatus">ТРЕБУЕТСЯ</span>
      </div>
      <div className="minorConsentBody">
        {state.document ? (
          <div className="minorConsentStatus">
            <strong>{state.document.original_filename}</strong>
            <small>{formatSize(state.document.size_bytes)} · статус: {state.document.status}</small>
          </div>
        ) : (
          <small>Загрузите PDF с разрешением законного представителя. Точная формулировка остаётся предметом юридической настройки.</small>
        )}
        <label className="uploadButton">
          {uploading ? "Загружаем…" : state.document ? "Заменить PDF" : "Выбрать PDF"}
          <input type="file" accept="application/pdf,.pdf" disabled={uploading} onChange={upload} />
        </label>
      </div>
      {message && <small className="minorConsentMessage" aria-live="polite">{message}</small>}
    </section>
  );
}
