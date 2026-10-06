"use client";

import { ChangeEvent, useEffect, useState } from "react";

type ResumeDocument = {
  id: string;
  original_filename: string;
  content_type: "application/pdf";
  size_bytes: number;
  status: "uploaded";
  uploaded_at: string;
};

type ResumeResponse = { document: ResumeDocument | null };

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { code?: string } };
    return body.error?.code ?? "RESUME_REQUEST_FAILED";
  } catch {
    return "RESUME_REQUEST_FAILED";
  }
}

function messageFor(code: string): string {
  const messages: Record<string, string> = {
    PROCESSING_CONSENT_REQUIRED: "Сначала разрешите обработку данных в настройках приватности.",
    RESUME_INVALID_FILENAME: "Выберите файл с расширением .pdf.",
    RESUME_INVALID_TYPE: "Файл должен быть PDF-документом.",
    RESUME_INVALID_PDF: "Файл не похож на корректный PDF-документ.",
    RESUME_TOO_LARGE: "Размер PDF превышает допустимый лимит.",
  };
  return messages[code] ?? code;
}

function formatSize(size: number): string {
  if (size < 1024) return `${size} Б`;
  return `${(size / 1024 / 1024).toFixed(1)} МБ`;
}

export function CandidateResume({ token }: { token: string }) {
  const [resume, setResume] = useState<ResumeDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch(`${apiUrl}/api/v1/candidate/resume`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(await readError(response));
        return (await response.json()) as ResumeResponse;
      })
      .then((result) => {
        if (active) setResume(result.document);
      })
      .catch((error: Error) => {
        if (active) setMessage(`Резюме недоступно: ${messageFor(error.message)}`);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setUploading(true);
    setMessage(null);
    const form = new FormData();
    form.append("resume", file);
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/resume`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!response.ok) throw new Error(await readError(response));
      const result = (await response.json()) as ResumeResponse;
      setResume(result.document);
      setMessage("PDF загружен. Следующий шаг — проверить распознанные поля.");
    } catch (error) {
      setMessage(`Не удалось загрузить PDF: ${messageFor((error as Error).message)}`);
    } finally {
      setUploading(false);
    }
  }

  if (loading) return <section className="resumePanel muted">Проверяем загруженное резюме…</section>;
  if (message && !resume) {
    return (
      <section className="resumePanel error" aria-label="Резюме кандидата">
        {message}
        <label className="uploadButton">
          Повторить загрузку
          <input type="file" accept="application/pdf,.pdf" disabled={uploading} onChange={upload} />
        </label>
      </section>
    );
  }

  return (
    <section className="resumePanel" aria-label="Резюме кандидата">
      <div className="resumeHeading">
        <div>
          <span className="authLabel">PRIVATE RESUME</span>
          <strong>PDF-резюме</strong>
          <small>Файл хранится приватно и не определяет подтвержденную категорию.</small>
        </div>
        <span className="profileStatus">CANDIDATE ONLY</span>
      </div>
      {resume ? (
        <div className="resumeStatus">
          <div>
            <strong>{resume.original_filename}</strong>
            <small>{formatSize(resume.size_bytes)} · загружено и ожидает проверки полей</small>
          </div>
          <span>{resume.status === "uploaded" ? "UPLOADED" : resume.status}</span>
        </div>
      ) : (
        <p className="resumeEmpty">Резюме еще не загружено.</p>
      )}
      <label className="uploadButton">
        {uploading ? "Загружаем…" : resume ? "Заменить PDF" : "Загрузить PDF"}
        <input type="file" accept="application/pdf,.pdf" disabled={uploading} onChange={upload} />
      </label>
      {message && <small className="resumeMessage" aria-live="polite">{message}</small>}
    </section>
  );
}
