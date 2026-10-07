"use client";

import { useEffect, useState } from "react";

type Invitation = {
  id: string;
  status: "pending" | "accepted" | "declined";
  salary_min_rub: number;
  salary_max_rub: number;
  company: { name: string };
  candidate: { display_name: string };
  created_at: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function EmployerInvitations({ token, refreshKey = 0 }: { token: string; refreshKey?: number }) {
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let active = true;
    setState("loading");
    fetch(`${apiUrl}/api/v1/employer/invitations`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (!response.ok) throw new Error("employer_invitations_unavailable");
        return (await response.json()) as Invitation[];
      })
      .then((value) => { if (active) { setInvitations(value); setState("ready"); } })
      .catch(() => { if (active) setState("error"); });
    return () => { active = false; };
  }, [token, refreshKey]);

  if (state === "loading") return <section className="invitationPanel muted">Загружаем историю приглашений…</section>;
  if (state === "error") return <section className="invitationPanel error">Не удалось загрузить историю приглашений.</section>;

  return (
    <section className="invitationPanel" aria-labelledby="employer-invitations-title">
      <div className="invitationHeading"><div><span className="authLabel">OUTREACH PIPELINE</span><h2 id="employer-invitations-title">Мои приглашения</h2><p>Статус обновляется после решения кандидата. Контакты доступны только в matched flow.</p></div><span className="profileStatus">{invitations.length} SENT</span></div>
      {invitations.length === 0 ? <div className="invitationEmpty"><strong>Приглашений пока нет</strong><span>Открой Talent Radar и выбери кандидата для salary-bearing offer.</span></div> : (
        <div className="employerInvitationRows">
          {invitations.map((invitation) => <div className="employerInvitationRow" key={invitation.id}><div><strong>{invitation.candidate.display_name}</strong><small>{invitation.company.name} · {invitation.salary_min_rub.toLocaleString("ru-RU")}–{invitation.salary_max_rub.toLocaleString("ru-RU")} ₽</small></div><span className={`invitationState ${invitation.status}`}>{invitation.status === "pending" ? "Ждёт ответа" : invitation.status === "accepted" ? "MATCH CREATED" : "Отклонено"}</span></div>)}
        </div>
      )}
    </section>
  );
}
