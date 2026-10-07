"use client";

import { useEffect, useState } from "react";

type Invitation = {
  id: string;
  status: "pending" | "accepted" | "declined";
  salary_min_rub: number;
  salary_max_rub: number;
  offer_description: string;
  company: { name: string; contact_method: string };
  created_at: string;
  matched_at: string | null;
  pipeline_stages: { stage_type: string; title: string; required: boolean; estimated_minutes: number }[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short" }).format(new Date(value));
}

function statusLabel(status: Invitation["status"]) {
  return status === "pending" ? "Ждёт ответа" : status === "accepted" ? "MATCH CREATED" : "Отклонено";
}

export function CandidateInvitations({ token }: { token: string }) {
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setState("loading");
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/invitations`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("invitations_unavailable");
      setInvitations((await response.json()) as Invitation[]);
      setState("ready");
    } catch {
      setState("error");
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  async function respond(id: string, action: "accepted" | "declined") {
    setBusyId(id);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/invitations/${id}/respond`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      if (!response.ok) throw new Error("invitation_response_failed");
      await load();
      setMessage(action === "accepted" ? "Match создан: теперь можно продолжить общение внутри платформы." : "Приглашение отклонено.");
    } catch {
      setMessage("Не удалось обновить приглашение. Обнови список и попробуй ещё раз.");
    } finally {
      setBusyId(null);
    }
  }

  if (state === "loading") return <section className="invitationPanel muted">Проверяем входящие приглашения…</section>;
  if (state === "error") return <section className="invitationPanel error">Не удалось загрузить входящие приглашения.</section>;

  return (
    <section className="invitationPanel" aria-labelledby="candidate-invitations-title">
      <div className="invitationHeading">
        <div>
          <span className="authLabel">REVERSE RECRUITMENT</span>
          <h2 id="candidate-invitations-title">Приглашения от работодателей</h2>
          <p>Зарплата и способ связи видны до ответа. Прямые контакты открываются только после match.</p>
        </div>
        <span className="profileStatus">{invitations.length} OFFER{invitations.length === 1 ? "" : "S"}</span>
      </div>
      {message && <p className="invitationMessage" aria-live="polite">{message}</p>}
      {invitations.length === 0 ? (
        <div className="invitationEmpty"><strong>Новых приглашений пока нет</strong><span>Работодатель увидит только опубликованные тобой профессиональные свидетельства.</span></div>
      ) : (
        <div className="invitationList">
          {invitations.map((invitation) => (
            <article className="invitationCard" key={invitation.id}>
              <div className="invitationCardTop">
                <div><span className={`invitationState ${invitation.status}`}>{statusLabel(invitation.status)}</span><h3>{invitation.company.name}</h3><small>{formatDate(invitation.created_at)} · {invitation.company.contact_method}</small></div>
                <strong className="invitationSalary">{invitation.salary_min_rub.toLocaleString("ru-RU")}–{invitation.salary_max_rub.toLocaleString("ru-RU")} ₽</strong>
              </div>
              <p className="invitationOffer">{invitation.offer_description}</p>
              {invitation.pipeline_stages.length > 0 && (
                <div className="invitationPipeline">
                  <strong>Что будет после match</strong>
                  <ol>
                    {invitation.pipeline_stages.map((stage, index) => <li key={`${invitation.id}-${index}`}><span>{stage.title}</span><small>{stage.required ? "Обязательный" : "Опциональный"} · около {stage.estimated_minutes} мин.</small></li>)}
                  </ol>
                </div>
              )}
              {invitation.status === "pending" && (
                <div className="invitationActions">
                  <button className="authButton primaryButton" disabled={busyId === invitation.id} onClick={() => void respond(invitation.id, "accepted")}>Принять · создать match</button>
                  <button className="authButton secondaryButton" disabled={busyId === invitation.id} onClick={() => void respond(invitation.id, "declined")}>Отклонить</button>
                </div>
              )}
              {invitation.status === "accepted" && <small className="invitationUnlocked">✓ Match создан · внутреннее общение разблокировано</small>}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
