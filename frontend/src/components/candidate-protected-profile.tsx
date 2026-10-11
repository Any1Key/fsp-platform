"use client";

import { useEffect, useState } from "react";
import { CandidateMinorConsent } from "./candidate-minor-consent";

type ProtectedProfile = {
  date_of_birth: string | null;
  minor_state: "not_set" | "minor" | "adult";
  adult_age_years: number;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { code?: string } };
    return body.error?.code ?? "PROTECTED_PROFILE_REQUEST_FAILED";
  } catch {
    return "PROTECTED_PROFILE_REQUEST_FAILED";
  }
}

const stateLabels: Record<ProtectedProfile["minor_state"], string> = {
  not_set: "Не указано",
  minor: "Несовершеннолетний статус",
  adult: "Совершеннолетний статус",
};

export function CandidateProtectedProfile({ token }: { token: string }) {
  const [profile, setProfile] = useState<ProtectedProfile | null>(null);
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch(`${apiUrl}/api/v1/candidate/protected-profile`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(await readError(response));
        return (await response.json()) as ProtectedProfile;
      })
      .then((nextProfile) => {
        if (!active) return;
        setProfile(nextProfile);
        setDateOfBirth(nextProfile.date_of_birth ?? "");
      })
      .catch((error: Error) => {
        if (active) setMessage(`Данные недоступны: ${error.message}`);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  async function save() {
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/protected-profile`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ date_of_birth: dateOfBirth || null }),
      });
      if (!response.ok) {
        const code = await readError(response);
        if (code === "PROCESSING_CONSENT_REQUIRED") {
          throw new Error("Сначала разрешите обработку данных в настройках приватности.");
        }
        if (code === "DATE_OF_BIRTH_IN_FUTURE") {
          throw new Error("Дата рождения не может быть в будущем.");
        }
        throw new Error(code);
      }
      const nextProfile = (await response.json()) as ProtectedProfile;
      setProfile(nextProfile);
      setDateOfBirth(nextProfile.date_of_birth ?? "");
      setMessage("Приватные данные сохранены");
    } catch (error) {
      setMessage(`Не удалось сохранить: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <section className="protectedPanel muted">Загружаем приватные данные…</section>;
  if (!profile) return <section className="protectedPanel error">{message ?? "Приватные данные недоступны"}</section>;

  return (
    <>
      <section className="protectedPanel" aria-label="Приватные данные кандидата">
        <div className="profileHeading">
          <div>
          <span className="authLabel">ЛИЧНЫЕ ДАННЫЕ</span>
            <strong>Дата рождения</strong>
            <small>Нужна только для приватных возрастных процессов и не участвует в подборе.</small>
          </div>
          <span className="profileStatus">{stateLabels[profile.minor_state]}</span>
        </div>
        <div className="protectedForm">
          <label>
            Дата рождения
            <input
              type="date"
              value={dateOfBirth}
              max={new Date().toISOString().slice(0, 10)}
              onChange={(event) => {
                setDateOfBirth(event.target.value);
                setMessage(null);
              }}
            />
          </label>
          <div className="protectedHint">
            <span>Состояние: {stateLabels[profile.minor_state]}</span>
            <small>Возрастной порог сервиса: {profile.adult_age_years} лет. Документы представителя — отдельный защищенный процесс.</small>
          </div>
          <div className="profileFooter">
            <small aria-live="polite">{message ?? "Эти сведения не видны работодателям."}</small>
            <button className="authButton primaryButton" type="button" disabled={saving} onClick={save}>
              {saving ? "Сохраняем…" : "Сохранить"}
            </button>
          </div>
        </div>
      </section>
      {profile.minor_state === "minor" && <CandidateMinorConsent token={token} />}
    </>
  );
}
