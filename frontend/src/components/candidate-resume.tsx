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

type ExtractedExperience = {
  role: string;
  company: string;
  started_on: string;
  ended_on: string | null;
  description: string | null;
  confidence?: number;
  source?: string;
};

type ResumeExtraction = {
  id: string;
  status: "needs_review" | "accepted" | "rejected" | "unsupported";
  parser_version: string;
  text_available: boolean;
  fields: {
    full_name?: { value: string | null; confidence: number; source: string };
    headline?: { value: string | null; confidence: number; source: string };
    contacts?: { emails: string[]; phones: string[]; links: string[] };
    skills?: { value: string; confidence: number; source: string }[];
    experience?: ExtractedExperience[];
  };
  extracted_at: string;
  reviewed_at: string | null;
};

type ResumeResponse = { document: ResumeDocument | null; extraction: ResumeExtraction | null };

type ReviewDraft = {
  display_name: string;
  headline: string;
  summary: string;
  skills: string;
  experience: ExtractedExperience[];
};

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

function toReviewDraft(extraction: ResumeExtraction): ReviewDraft {
  return {
    display_name: extraction.fields.full_name?.value ?? "",
    headline: extraction.fields.headline?.value ?? "",
    summary: "",
    skills: (extraction.fields.skills ?? []).map((skill) => skill.value).join(", "),
    experience: extraction.fields.experience ?? [],
  };
}

export function CandidateResume({ token }: { token: string }) {
  const [resume, setResume] = useState<ResumeDocument | null>(null);
  const [extraction, setExtraction] = useState<ResumeExtraction | null>(null);
  const [reviewDraft, setReviewDraft] = useState<ReviewDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [reviewing, setReviewing] = useState(false);
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
        if (active) {
          setResume(result.document);
          setExtraction(result.extraction);
          if (result.extraction?.status === "needs_review") setReviewDraft(toReviewDraft(result.extraction));
        }
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
      setExtraction(result.extraction);
      setReviewDraft(result.extraction?.status === "needs_review" ? toReviewDraft(result.extraction) : null);
      setMessage(result.extraction?.status === "needs_review" ? "PDF обработан. Проверьте поля перед сохранением." : "PDF загружен, но текстовые поля не распознаны.");
    } catch (error) {
      setMessage(`Не удалось загрузить PDF: ${messageFor((error as Error).message)}`);
    } finally {
      setUploading(false);
    }
  }

  function changeDraft(key: keyof ReviewDraft, value: string) {
    setReviewDraft((current) => (current ? { ...current, [key]: value } : current));
  }

  async function review(accepted: boolean) {
    if (!resume || !reviewDraft) return;
    setReviewing(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/resume/${resume.id}/review`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          accepted,
          display_name: reviewDraft.display_name || null,
          headline: reviewDraft.headline || null,
          summary: reviewDraft.summary || null,
          skills: reviewDraft.skills.split(",").map((skill) => skill.trim()).filter(Boolean),
          experience: reviewDraft.experience.map(({ confidence, source, ...item }) => item),
        }),
      });
      if (!response.ok) throw new Error(await readError(response));
      const result = (await response.json()) as ResumeResponse;
      setExtraction(result.extraction);
      setReviewDraft(null);
      setMessage(accepted ? "Поля проверены и сохранены в профиле." : "Распознанные поля отклонены; профиль не изменен.");
    } catch (error) {
      setMessage(`Не удалось завершить проверку: ${messageFor((error as Error).message)}`);
    } finally {
      setReviewing(false);
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
      {extraction?.status === "unsupported" && (
        <div className="resumeReview unsupported">
          <strong>Текст не распознан</strong>
          <small>Скан или изображение можно добавить вручную в профиль. Парсер не публикует неподтвержденные поля.</small>
        </div>
      )}
      {extraction?.status === "needs_review" && reviewDraft && (
        <div className="resumeReview" aria-label="Проверка распознанных полей">
          <div className="resumeReviewHeading">
            <div><strong>Проверьте распознанные поля</strong><small>Это заявленные данные из резюме, не подтвержденная категория.</small></div>
            <span className="profileStatus">NEEDS REVIEW</span>
          </div>
          <div className="resumeReviewGrid">
            <label>Имя и фамилия<input value={reviewDraft.display_name} onChange={(event) => changeDraft("display_name", event.target.value)} /></label>
            <label>Заголовок<input value={reviewDraft.headline} onChange={(event) => changeDraft("headline", event.target.value)} /></label>
          </div>
          <label>Навыки <small>через запятую</small><input value={reviewDraft.skills} onChange={(event) => changeDraft("skills", event.target.value)} /></label>
          {reviewDraft.experience.length > 0 && (
            <div className="resumeExperience"><strong>Опыт из резюме</strong>{reviewDraft.experience.map((item, index) => <small key={`${item.company}-${index}`}>{item.role} · {item.company} · {item.started_on} — {item.ended_on ?? "не указано"}</small>)}</div>
          )}
          {extraction.fields.contacts && (extraction.fields.contacts.emails.length > 0 || extraction.fields.contacts.phones.length > 0) && (
            <small className="resumeContactNote">Контакты распознаны для проверки, но автоматически в публичный профиль не переносятся.</small>
          )}
          <div className="resumeReviewActions">
            <button className="authButton secondaryButton" type="button" disabled={reviewing} onClick={() => review(false)}>Отклонить поля</button>
            <button className="authButton primaryButton" type="button" disabled={reviewing} onClick={() => review(true)}>{reviewing ? "Сохраняем…" : "Проверил — сохранить"}</button>
          </div>
        </div>
      )}
    </section>
  );
}
