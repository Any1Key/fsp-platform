"use client";

import Keycloak, { type KeycloakInstance } from "keycloak-js";
import { useEffect, useRef, useState } from "react";
import { PrivacySettings } from "./privacy-settings";
import { CandidateProfile } from "./candidate-profile";
import { CandidateProtectedProfile } from "./candidate-protected-profile";
import { CandidateResume } from "./candidate-resume";
import { CandidateSkillPassport } from "./candidate-skill-passport";
import { CandidateCareerGraph } from "./candidate-career-graph";
import { CandidateAssessment } from "./candidate-assessment";
import { CandidateFsp } from "./candidate-fsp";
import { EmployerCompanyProfile } from "./employer-company-profile";
import { EmployerTrust } from "./employer-trust";
import { EmployerHiringNeed } from "./employer-hiring-need";
import { EmployerVacancies } from "./employer-vacancies";
import { EmployerApplications } from "./employer-applications";
import { EmployerHiringPipeline } from "./employer-hiring-pipeline";
import { EmployerTaskAuthoring } from "./employer-task-authoring";
import { EmployerTaskEvaluations } from "./employer-task-evaluations";
import { EmployerTalentRadar } from "./employer-talent-radar";
import { CandidateInvitations } from "./candidate-invitations";
import { CandidateTaskAssignments } from "./candidate-task-assignments";
import { CandidateVacancies } from "./candidate-vacancies";
import { CandidateChallenges } from "./candidate-challenges";
import { EmployerChallenges } from "./employer-challenges";
import { EmployerInvitations } from "./employer-invitations";
import { InternalChat } from "./internal-chat";
import { ValidationDashboard } from "./validation-dashboard";
import { ErrorState, LoadingState } from "./ui-state";

type Session = {
  identity_id: string | null;
  keycloak_sub: string;
  email: string;
  role: string;
  email_verified: boolean;
  onboarding_required: boolean;
};

type AuthState =
  | { status: "loading" }
  | { status: "signed-out" }
  | { status: "signed-in"; session: Session }
  | { status: "error"; message: string };

type WorkspaceTab = "overview" | "profile" | "assessment" | "opportunities" | "communication" | "matching" | "tasks" | "validation";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function AuthStatus() {
  const keycloak = useRef<KeycloakInstance | null>(null);
  const [auth, setAuth] = useState<AuthState>({ status: "loading" });
  const [roleSaving, setRoleSaving] = useState(false);
  const [roleError, setRoleError] = useState<string | null>(null);
  const [assessmentRefreshKey, setAssessmentRefreshKey] = useState(0);
  const [talentRadarRefreshKey, setTalentRadarRefreshKey] = useState(0);
  const [invitationRefreshKey, setInvitationRefreshKey] = useState(0);
  const [taskRefreshKey, setTaskRefreshKey] = useState(0);
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>("overview");
  const [registrationNotice, setRegistrationNotice] = useState(false);

  useEffect(() => {
    let active = true;
    const client = new Keycloak({
      url: process.env.NEXT_PUBLIC_KEYCLOAK_URL ?? "http://localhost:8081",
      realm: process.env.NEXT_PUBLIC_KEYCLOAK_REALM ?? "fsp",
      clientId: process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "fsp-web",
    });
    keycloak.current = client;

    client
      .init({ onLoad: "check-sso", pkceMethod: "S256", checkLoginIframe: false })
      .then(async (authenticated) => {
        if (!active) return;
        if (!authenticated || !client.token) {
          setAuth({ status: "signed-out" });
          return;
        }

        const response = await fetch(`${apiUrl}/api/v1/auth/me`, {
          headers: { Authorization: `Bearer ${client.token}` },
        });
        if (!response.ok) {
          setAuth({ status: "error", message: "API не принял сессию Keycloak" });
          return;
        }
        const session = (await response.json()) as Session;
        if (active) setAuth({ status: "signed-in", session });
      })
      .catch(() => {
        if (active) setAuth({ status: "error", message: "Keycloak пока недоступен" });
      });

    return () => {
      active = false;
    };
  }, []);

  async function chooseRole(role: "candidate" | "employer") {
    const token = keycloak.current?.token;
    if (!token) return;
    setRoleSaving(true);
    setRoleError(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/auth/onboarding/role`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ role }),
      });
      if (!response.ok) {
        setRoleError("Не удалось закрепить роль. Обновите сессию и повторите.");
        return;
      }
      const session = (await response.json()) as Session;
      setAuth({ status: "signed-in", session });
    } catch {
      setRoleError("Сервис ролей пока недоступен.");
    } finally {
      setRoleSaving(false);
    }
  }

  if (auth.status === "loading") {
    return <div className="authPanel muted"><LoadingState title="Проверяем защищённую сессию…" description="Подключаем защищённое рабочее пространство." /></div>;
  }
  if (auth.status === "error") {
    return <div className="authPanel error"><ErrorState title="Не удалось открыть защищённую сессию" description={auth.message} /></div>;
  }
  if (auth.status === "signed-in") {
    if (auth.session.onboarding_required) {
      return (
        <div className="authPanel onboardingPanel">
          <div>
            <span className="authLabel">НАЧАЛО РАБОТЫ</span>
            <strong>Выберите рабочую роль</strong>
            <small>{auth.session.email} · роль можно выбрать один раз</small>
          </div>
          <div className="authActions">
            <button
              className="authButton primaryButton"
              disabled={roleSaving}
              onClick={() => chooseRole("candidate")}
            >
              Я кандидат
            </button>
            <button
              className="authButton secondaryButton"
              disabled={roleSaving}
              onClick={() => chooseRole("employer")}
            >
              Я работодатель
            </button>
            {roleError && <small className="onboardingError">{roleError}</small>}
          </div>
        </div>
      );
    }
    return (
      <div className="authPanel signedInPanel">
        <div>
          <span className="authLabel">ЛИЧНЫЙ КАБИНЕТ</span>
          <strong>{auth.session.role === "employer" ? "Рабочее пространство работодателя" : "Профиль кандидата"}</strong>
          <small>{auth.session.email}</small>
        </div>
        <button className="authButton secondaryButton" onClick={() => keycloak.current?.logout()}>
          Выйти
        </button>
        <nav className="workspaceTabs" aria-label="Разделы кабинета">
          {auth.session.role === "candidate" ? (
            <>
              <button className={workspaceTab === "overview" ? "workspaceTab active" : "workspaceTab"} onClick={() => setWorkspaceTab("overview")}>Обзор</button>
              <button className={workspaceTab === "profile" ? "workspaceTab active" : "workspaceTab"} onClick={() => setWorkspaceTab("profile")}>Профиль</button>
              <button className={workspaceTab === "assessment" ? "workspaceTab active" : "workspaceTab"} onClick={() => setWorkspaceTab("assessment")}>Проверка навыков</button>
              <button className={workspaceTab === "opportunities" ? "workspaceTab active" : "workspaceTab"} onClick={() => setWorkspaceTab("opportunities")}>Возможности</button>
              <button className={workspaceTab === "communication" ? "workspaceTab active" : "workspaceTab"} onClick={() => setWorkspaceTab("communication")}>Общение</button>
            </>
          ) : (
            <>
              <button className={workspaceTab === "overview" ? "workspaceTab active" : "workspaceTab"} onClick={() => setWorkspaceTab("overview")}>Компания</button>
              <button className={workspaceTab === "matching" ? "workspaceTab active" : "workspaceTab"} onClick={() => setWorkspaceTab("matching")}>Подбор</button>
              <button className={workspaceTab === "tasks" ? "workspaceTab active" : "workspaceTab"} onClick={() => setWorkspaceTab("tasks")}>Задачи</button>
              <button className={workspaceTab === "communication" ? "workspaceTab active" : "workspaceTab"} onClick={() => setWorkspaceTab("communication")}>Общение</button>
              <button className={workspaceTab === "validation" ? "workspaceTab active" : "workspaceTab"} onClick={() => setWorkspaceTab("validation")}>Проверка</button>
            </>
          )}
        </nav>
        <div className="workspaceContent">
        {auth.session.role === "candidate" && (
          <>
            {workspaceTab === "overview" && <>
            <CandidateSkillPassport token={keycloak.current?.token ?? ""} refreshKey={assessmentRefreshKey} />
            <CandidateCareerGraph token={keycloak.current?.token ?? ""} refreshKey={assessmentRefreshKey} />
            <CandidateFsp token={keycloak.current?.token ?? ""} />
            </>}
            {workspaceTab === "profile" && <>
            <CandidateProfile token={keycloak.current?.token ?? ""} />
            <CandidateProtectedProfile token={keycloak.current?.token ?? ""} />
            <CandidateResume token={keycloak.current?.token ?? ""} />
            <PrivacySettings token={keycloak.current?.token ?? ""} />
            </>}
            {workspaceTab === "assessment" && <CandidateAssessment
              token={keycloak.current?.token ?? ""}
              onSubmitted={() => setAssessmentRefreshKey((value) => value + 1)}
            />}
            {workspaceTab === "opportunities" && <>
            <CandidateVacancies token={keycloak.current?.token ?? ""} />
            <CandidateInvitations token={keycloak.current?.token ?? ""} onMatchCreated={() => setTaskRefreshKey((value) => value + 1)} />
            <CandidateTaskAssignments token={keycloak.current?.token ?? ""} refreshKey={taskRefreshKey} />
            <CandidateChallenges token={keycloak.current?.token ?? ""} refreshKey={taskRefreshKey} />
            </>}
            {workspaceTab === "communication" && <InternalChat token={keycloak.current?.token ?? ""} />}
          </>
        )}
        {auth.session.role === "employer" && (
          <>
            {workspaceTab === "overview" && <>
            <EmployerCompanyProfile token={keycloak.current?.token ?? ""} />
            <EmployerTrust token={keycloak.current?.token ?? ""} />
            </>}
            {workspaceTab === "matching" && <>
            <EmployerHiringNeed token={keycloak.current?.token ?? ""} onSaved={() => setTalentRadarRefreshKey((value) => value + 1)} />
            <EmployerVacancies token={keycloak.current?.token ?? ""} />
            <EmployerApplications token={keycloak.current?.token ?? ""} />
            <EmployerHiringPipeline token={keycloak.current?.token ?? ""} refreshKey={talentRadarRefreshKey} />
            <EmployerTalentRadar token={keycloak.current?.token ?? ""} refreshKey={talentRadarRefreshKey} onInvitationCreated={() => setInvitationRefreshKey((value) => value + 1)} />
            <EmployerInvitations token={keycloak.current?.token ?? ""} refreshKey={invitationRefreshKey} />
            </>}
            {workspaceTab === "tasks" && <>
            <EmployerTaskAuthoring token={keycloak.current?.token ?? ""} refreshKey={talentRadarRefreshKey} />
            <EmployerTaskEvaluations token={keycloak.current?.token ?? ""} refreshKey={taskRefreshKey} />
            <EmployerChallenges token={keycloak.current?.token ?? ""} refreshKey={invitationRefreshKey} />
            </>}
            {workspaceTab === "communication" && <InternalChat token={keycloak.current?.token ?? ""} />}
            {workspaceTab === "validation" && <ValidationDashboard token={keycloak.current?.token ?? ""} />}
          </>
        )}
        </div>
      </div>
    );
  }
  return (
    <div className="authPanel">
      <div>
        <span className="authLabel">ДОСТУП К ПЛАТФОРМЕ</span>
        <strong>Войти как кандидат или работодатель</strong>
        <small>Безопасный вход · подтверждённый адрес электронной почты в зоне .ru</small>
      </div>
      <div className="authActions">
        <button className="authButton primaryButton" onClick={() => keycloak.current?.login()}>
          Войти через Keycloak
        </button>
        <button className="authButton secondaryButton" onClick={() => { setRegistrationNotice(true); keycloak.current?.register(); }}>
          Создать аккаунт
        </button>
      </div>
      {registrationNotice && <small className="registrationNotice" role="status">Регистрация доступна только с адресом электронной почты, который заканчивается на .ru</small>}
    </div>
  );
}
