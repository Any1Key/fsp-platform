"use client";

import Image from "next/image";
import { FormEvent, useEffect, useState } from "react";

type Achievement = {
  id: string;
  event_name: string;
  event_date: string;
  discipline: string;
  level: string;
  achievement_type: string;
  placement: string | null;
  result: string | null;
  verification: string;
  mapping_version: string;
  mapped_specialization: string | null;
  mapped_skills: string[];
  result_score: number;
  result_label: string;
  recency_score: number;
  recency_label: string;
};

type FspState = {
  status: "not_linked" | "linked";
  provider: "synthetic" | null;
  participant_id: string | null;
  linked_at: string | null;
  updated_at: string | null;
  history_status: "no_history" | "has_history";
  achievements: Achievement[];
};

type FspIdentityBridge = {
  bridge_version: string;
  binding_mode: "explicit_candidate_link";
  keycloak: {
    provider: "keycloak";
    issuer: string;
    subject_fingerprint: string;
  };
  fsp: {
    provider: string | null;
    participant_id: string | null;
    status: "not_linked" | "linked";
    history_status: "no_history" | "has_history";
  };
  registry_adapter: "FspRegistryPort";
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function resultLabel(value: string) {
  return ({ winner: "Победа", prize: "Призовое место", finalist: "Финалист", placed: "Место", participant: "Участник", recorded: "Результат" } as Record<string, string>)[value] ?? value;
}

function recencyLabel(value: string) {
  return ({ recent: "свежее", aging: "актуальность снижается", old: "старше года", stale: "устаревшее, не удалено", future: "дата требует проверки" } as Record<string, string>)[value] ?? value;
}

export function CandidateFsp({ token }: { token: string }) {
  const [fsp, setFsp] = useState<FspState | null>(null);
  const [integration, setIntegration] = useState<FspIdentityBridge | null>(null);
  const [fspId, setFspId] = useState("");
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setState("loading");
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/fsp`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("fsp_unavailable");
      setFsp((await response.json()) as FspState);
      setState("ready");
    } catch {
      setState("error");
    }
  }

  async function loadIntegration() {
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/fsp/integration`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("fsp_integration_unavailable");
      setIntegration((await response.json()) as FspIdentityBridge);
    } catch {
      setIntegration(null);
    }
  }

  useEffect(() => {
    let active = true;
    fetch(`${apiUrl}/api/v1/candidate/fsp`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("fsp_unavailable");
        return (await response.json()) as FspState;
      })
      .then((value) => {
        if (!active) return;
        setFsp(value);
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    void loadIntegration();
    return () => {
      active = false;
    };
  }, [token]);

  async function link(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/fsp-link`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ fsp_id: fspId }),
      });
      if (!response.ok) {
        const error = (await response.json().catch(() => null)) as { error?: { code?: string } } | null;
        const code = error?.error?.code;
        setMessage(code === "PROCESSING_CONSENT_REQUIRED"
          ? "Сначала включи согласие на обработку данных в настройках приватности."
          : code === "FSP_PARTICIPANT_NOT_FOUND"
            ? "Такой идентификатор участника ФСП не найден."
            : "Не удалось подключить профиль участника ФСП.");
        return;
      }
      setFsp((await response.json()) as FspState);
      await loadIntegration();
      setFspId("");
      setMessage("Профиль участника ФСП подключён.");
    } catch {
      setMessage("Сервис FSP пока недоступен.");
    } finally {
      setSaving(false);
    }
  }

  async function unlink() {
    setSaving(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/fsp-link`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("unlink_failed");
      await load();
      await loadIntegration();
      setMessage("Профиль участника ФСП отключён. Это не влияет на доступность основного профиля.");
    } catch {
      setMessage("Не удалось отключить профиль участника ФСП.");
    } finally {
      setSaving(false);
    }
  }

  if (state === "loading") {
    return <section className="fspPanel muted" aria-busy="true">Проверяем внешние подтверждения…</section>;
  }
  if (state === "error" || !fsp) {
    return <section className="fspPanel error" role="alert">Не удалось загрузить внешние подтверждения. Обновите страницу и попробуйте ещё раз.</section>;
  }

  return (
    <section className="fspPanel" aria-labelledby="fsp-title">
      <div className="fspBrandBar">
        <div className="fspIdentity">
          <span className="fspLogoFrame" aria-hidden="true">
            <Image src="/brand/logo_white1.png" alt="" width={22} height={31} />
          </span>
          <div className="fspHeading">
            <span className="authLabel">ВНЕШНИЕ ПОДТВЕРЖДЕНИЯ · СВЯЗЬ ПРОВЕРЕНА</span>
            <h2 id="fsp-title">История FSP</h2>
            <p>Дополнительный проверяемый сигнал. Отсутствие истории не ограничивает профиль.</p>
          </div>
        </div>
        {fsp.provider && (
          <span className="fspProvider">
            <i aria-hidden="true" />
            {fsp.provider === "synthetic" ? "РЕЕСТР FSP" : fsp.provider}
          </span>
        )}
      </div>

      {integration && (
        <div className="fspIdentityBridge" aria-label="Связка Keycloak и FSP">
          <div className="fspBridgeHeading">
            <div>
              <span className="fspSectionKicker">СВЯЗЬ С ПРОФИЛЕМ · ПРОВЕРЕННЫЕ ДАННЫЕ</span>
          <strong>Учётная запись и профиль навыков связаны безопасно</strong>
            </div>
            <span>{integration.binding_mode === "explicit_candidate_link" ? "Явная связь" : integration.binding_mode}</span>
          </div>
          <div className="fspBridgeGrid">
            <div>
              <span>УЧЁТНАЯ ЗАПИСЬ</span>
              <strong>{integration.keycloak.provider}</strong>
              <small>fingerprint · {integration.keycloak.subject_fingerprint}</small>
            </div>
            <div>
              <span>СВЯЗЬ С РЕЕСТРОМ</span>
              <strong>{integration.fsp.participant_id ?? "Не привязан"}</strong>
              <small>{integration.registry_adapter} · {integration.fsp.status === "linked" ? "подтверждён" : "ожидает link"}</small>
            </div>
          </div>
          <small className="fspBridgeNote">Профиль ФСП подключается отдельно от учётной записи платформы. Личные данные и технические идентификаторы не раскрываются работодателю.</small>
        </div>
      )}

      {fsp.status === "linked" ? (
        <>
          <div className="fspLinkedRow">
            <div>
              <span className="fspFieldLabel">ПРОФИЛЬ УЧАСТНИКА ФСП</span>
              <strong>{fsp.participant_id}</strong>
            </div>
            <span className="fspLinkState"><i aria-hidden="true" />{fsp.history_status === "has_history" ? "Связь подтверждена" : "ID подтверждён"}</span>
            <button className="textButton" type="button" onClick={unlink} disabled={saving}>Отвязать</button>
          </div>
          {fsp.history_status === "has_history" ? (
            <div className="fspEvidenceBlock">
              <div className="fspSectionHeading">
                <div>
                  <span className="fspSectionKicker">ПОДТВЕРЖДЕНИЯ</span>
                  <strong>Достижения и сопоставленные навыки</strong>
                </div>
                <span>{fsp.achievements.length} записи</span>
              </div>
              <div className="fspAchievements">
                {fsp.achievements.map((achievement, index) => (
                  <article className="fspAchievement" key={achievement.id}>
                    <div className="fspAchievementHeading">
                      <div>
                        <span className="fspAchievementIndex">ДОСТИЖЕНИЕ {String(index + 1).padStart(2, "0")}</span>
                        <strong>{achievement.event_name}</strong>
                        <small>{formatDate(achievement.event_date)} · {achievement.discipline}</small>
                      </div>
                      <span className="fspResultBadge">{achievement.placement ? `Место ${achievement.placement}` : achievement.achievement_type}</span>
                    </div>
                    {achievement.result && <p>{achievement.result}</p>}
                    <div className="fspEvidenceMeta">
                      <span>{resultLabel(achievement.result_label)} · {achievement.result_score}/100</span>
                      <span>{achievement.mapped_skills.length ? `Навыки: ${achievement.mapped_skills.join(", ")}` : "Навыки пока не сопоставлены"}</span>
                      <span>Актуальность: {recencyLabel(achievement.recency_label)}</span>
                    </div>
                    <small className="fspProvenance">Источник: {achievement.verification} · mapping {achievement.mapping_version}</small>
                  </article>
                ))}
              </div>
            </div>
          ) : (
            <div className="fspNoHistory" role="status">
              <span className="fspStateKicker">ИСТОРИЯ ПОКА НЕ ДОБАВЛЕНА</span>
              <strong>В реестре нет достижений</strong>
          <p>Идентификатор подтверждён, но история пока пустая. Профиль остаётся доступным через оценки и другие подтверждения.</p>
            </div>
          )}
        </>
      ) : (
        <div className="fspNoHistory" role="status">
          <span className="fspStateKicker">ДОПОЛНИТЕЛЬНОЕ ПОДТВЕРЖДЕНИЕ</span>
          <strong>Профиль участника ФСП пока не подключён</strong>
          <p>Это нормальное состояние: оценки платформы и профиль работают независимо от FSP.</p>
        </div>
      )}

      <form className="fspLinkForm" onSubmit={link} aria-describedby="fsp-link-help">
        <label htmlFor="fsp-link-id">Идентификатор профиля<input id="fsp-link-id" value={fspId} onChange={(event) => setFspId(event.target.value)} placeholder="Например, FSP-001" required autoComplete="off" /></label>
        <button className="authButton secondaryButton" type="submit" disabled={saving}>{saving ? "Проверяем…" : "Привязать ID"}</button>
      </form>
      <small id="fsp-link-help" className="fspMessage" aria-live="polite">{message ?? "Подключите внешний профиль, чтобы дополнить подтверждения навыков."}</small>
    </section>
  );
}
