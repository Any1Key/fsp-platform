"use client";

import { useEffect, useState } from "react";

type TrustSignal = {
  key: string;
  label: string;
  category: "verified" | "heuristic";
  status: "pass" | "attention" | "not_available";
  explanation: string;
};

type TrustProfile = {
  state: "normal" | "review";
  badge: "verified_email" | "none";
  badge_label: string;
  review_queue: boolean;
  open_report_count: number;
  outbound_used: number;
  outbound_limit: number;
  review_reasons: string[];
  signals: TrustSignal[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function signalLabel(signal: TrustSignal) {
  if (signal.status === "pass") return "ПРОВЕРЕНО";
  if (signal.status === "attention") return "ТРЕБУЕТ ВНИМАНИЯ";
  return "НЕ ПРОВЕРЕНО";
}

export function EmployerTrust({ token }: { token: string }) {
  const [profile, setProfile] = useState<TrustProfile | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let active = true;
    fetch(`${apiUrl}/api/v1/employer/trust`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (!response.ok) throw new Error("trust_unavailable");
        return (await response.json()) as TrustProfile;
      })
      .then((next) => {
        if (!active) return;
        setProfile(next);
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => {
      active = false;
    };
  }, [token]);

  if (state === "loading") return <section className="trustPanel muted">Проверяем trust-сигналы работодателя…</section>;
  if (state === "error" || !profile) return <section className="trustPanel error">Trust-профиль пока недоступен.</section>;

  return (
    <section className="trustPanel" aria-labelledby="employer-trust-title">
      <div className="trustHeading">
        <div>
          <span className="authLabel">ПРОВЕРКА КОМПАНИИ</span>
          <h2 id="employer-trust-title">Доверие и защита исходящих приглашений</h2>
          <p>Отметка компании основана на подтверждённом email. Остальные сигналы помогают принять решение и не являются автоматическим обвинением.</p>
        </div>
        <span className={`trustBadge ${profile.badge === "verified_email" ? "verified" : ""}`}>{profile.badge_label}</span>
      </div>
      <div className="trustMeta">
        <span className={profile.state === "review" ? "trustState review" : "trustState"}>{profile.state === "review" ? "НА ПРОВЕРКЕ" : "ОБЫЧНЫЙ РЕЖИМ"}</span>
        <span>{profile.outbound_used} / {profile.outbound_limit} приглашений за 24 часа</span>
        {profile.open_report_count > 0 && <span>{profile.open_report_count} открытый report</span>}
      </div>
      <div className="trustSignals">
        {profile.signals.map((signal) => (
          <article className="trustSignal" key={signal.key}>
            <div><strong>{signal.label}</strong><small>{signal.category === "verified" ? "EXPLICIT" : "HEURISTIC"}</small></div>
            <span className={`trustSignalStatus ${signal.status}`}>{signalLabel(signal)}</span>
            <p>{signal.explanation}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
