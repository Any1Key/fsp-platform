"use client";

import { useEffect, useMemo, useState } from "react";

type ApplicationStatus = "submitted" | "reviewing" | "shortlisted" | "accepted" | "rejected" | "withdrawn";
type Taxonomy = { slug: string; name: string } | null;
type Vacancy = {
  id: string;
  title: string;
  description: string;
  company_name: string;
  location: string | null;
  work_mode: "office" | "hybrid" | "remote" | null;
  employment_type: "full_time" | "part_time" | "project" | null;
  salary_min_rub: number;
  salary_max_rub: number;
  specialization: Taxonomy;
  grade: Taxonomy;
  application_id: string | null;
  application_status: ApplicationStatus | null;
  applied_at: string | null;
};
type Application = {
  id: string;
  status: ApplicationStatus;
  applied_at: string;
  updated_at: string;
  match_id: string | null;
  vacancy: Vacancy & { vacancy_status: "draft" | "published" | "closed" };
  status_history: { status: ApplicationStatus; changed_at: string }[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const statusLabels: Record<ApplicationStatus, string> = {
  submitted: "Отклик отправлен",
  reviewing: "На рассмотрении",
  shortlisted: "Следующий этап",
  accepted: "Принято · match создан",
  rejected: "Не подошло",
  withdrawn: "Отозван",
};
const workModeLabels = { office: "Офис", hybrid: "Гибрид", remote: "Удалённо" };

async function errorCode(response: Response) {
  try {
    const body = (await response.json()) as { error?: { code?: string } };
    return body.error?.code ?? "VACANCY_REQUEST_FAILED";
  } catch {
    return "VACANCY_REQUEST_FAILED";
  }
}

function salary(vacancy: Vacancy) {
  return `₽${vacancy.salary_min_rub.toLocaleString("ru-RU")}–${vacancy.salary_max_rub.toLocaleString("ru-RU")}`;
}

function statusText(status: ApplicationStatus) {
  return statusLabels[status];
}

export function CandidateVacancies({ token }: { token: string }) {
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [applyingId, setApplyingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [specializationFilter, setSpecializationFilter] = useState("all");

  async function load() {
    setLoading(true);
    setMessage(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [vacanciesResponse, applicationsResponse] = await Promise.all([
        fetch(`${apiUrl}/api/v1/candidate/vacancies`, { headers }),
        fetch(`${apiUrl}/api/v1/candidate/applications`, { headers }),
      ]);
      if (!vacanciesResponse.ok) throw new Error(await errorCode(vacanciesResponse));
      if (!applicationsResponse.ok) throw new Error(await errorCode(applicationsResponse));
      setVacancies((await vacanciesResponse.json()) as Vacancy[]);
      setApplications((await applicationsResponse.json()) as Application[]);
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // The candidate token is the only external identity dependency for this panel.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function apply(vacancyId: string) {
    setApplyingId(vacancyId);
    setMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/candidate/vacancies/${vacancyId}/applications`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const code = await errorCode(response);
        const messages: Record<string, string> = {
          PROCESSING_CONSENT_REQUIRED: "Сначала подтвердите согласие на обработку данных в настройках приватности.",
          APPLICATION_EXISTS: "Вы уже откликались на эту вакансию.",
          VACANCY_NOT_PUBLISHED: "Вакансия больше не принимает отклики.",
        };
        throw new Error(messages[code] ?? code);
      }
      setMessage("Отклик отправлен. Его статус появится в истории справа.");
      await load();
    } catch (error) {
      setMessage(`Не удалось отправить отклик: ${(error as Error).message}`);
    } finally {
      setApplyingId(null);
    }
  }

  const specializations = useMemo(
    () => Array.from(new Set(vacancies.map((vacancy) => vacancy.specialization?.name).filter(Boolean))).sort(),
    [vacancies],
  );
  const filteredVacancies = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("ru-RU");
    return vacancies.filter((vacancy) => {
      const searchable = `${vacancy.title} ${vacancy.company_name} ${vacancy.location ?? ""}`.toLocaleLowerCase("ru-RU");
      return (!normalizedQuery || searchable.includes(normalizedQuery)) &&
        (specializationFilter === "all" || vacancy.specialization?.name === specializationFilter);
    });
  }, [query, specializationFilter, vacancies]);

  if (loading) return <section className="candidateVacanciesPanel muted">Загружаем вакансии и отклики…</section>;

  return (
    <section className="candidateVacanciesPanel" aria-labelledby="candidate-vacancies-title">
      <div className="candidateVacanciesHeading">
        <div>
          <span className="authLabel">ПОДХОДЯЩИЕ ВАКАНСИИ</span>
          <h2 id="candidate-vacancies-title">Вакансии и мои отклики</h2>
          <p>Открытые предложения с зарплатой — отдельный путь к матчу, без раскрытия контактов до принятия.</p>
        </div>
        <span className="profileStatus">{filteredVacancies.length} из {vacancies.length}</span>
      </div>
      <div className="candidateVacancyFilters" aria-label="Фильтры вакансий">
        <label>
          <span>Поиск</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Название или компания" />
        </label>
        <label>
          <span>Специализация</span>
          <select value={specializationFilter} onChange={(event) => setSpecializationFilter(event.target.value)}>
            <option value="all">Все специализации</option>
            {specializations.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
      </div>
      <div className="candidateVacanciesLayout">
        <div className="candidateVacancyList" aria-label="Опубликованные вакансии">
          {filteredVacancies.length === 0 ? (
            <div className="candidateVacancyEmpty"><strong>Пока нет опубликованных вакансий</strong><span>Работодатели добавят новые предложения — они появятся здесь с обязательной зарплатой.</span></div>
          ) : filteredVacancies.map((vacancy) => (
            <article className="candidateVacancyCard" key={vacancy.id}>
              <div className="candidateVacancyCardTop">
                <div>
                  <span className="candidateVacancyCompany">{vacancy.company_name}</span>
                  <h3>{vacancy.title}</h3>
                </div>
                <strong className="candidateVacancySalary">{salary(vacancy)}</strong>
              </div>
              <div className="candidateVacancyMeta">
                {vacancy.specialization && <span>{vacancy.specialization.name}</span>}
                {vacancy.grade && <span>{vacancy.grade.name}</span>}
                {vacancy.location && <span>{vacancy.location}</span>}
                {vacancy.work_mode && <span>{workModeLabels[vacancy.work_mode]}</span>}
              </div>
              <details className="candidateVacancyDetails">
                <summary>Подробнее о вакансии</summary>
                <p>{vacancy.description}</p>
              </details>
              <div className="candidateVacancyFooter">
                {vacancy.application_status ? (
                  <span className={`candidateApplicationStatus ${vacancy.application_status}`}>{statusText(vacancy.application_status)}</span>
                ) : <span className="candidateVacancyHint">Отклик отправится работодателю на рассмотрение.</span>}
                <button
                  className="authButton primaryButton"
                  type="button"
                  disabled={Boolean(vacancy.application_id) || applyingId === vacancy.id}
                  onClick={() => void apply(vacancy.id)}
                >
                  {applyingId === vacancy.id ? "Отправляем…" : vacancy.application_id ? "Отклик отправлен" : "Откликнуться"}
                </button>
              </div>
            </article>
          ))}
        </div>
        <aside className="candidateApplicationsPanel" aria-labelledby="candidate-applications-title">
          <div className="candidateApplicationsHeading">
            <div>
            <span className="authLabel">СТАТУС ОТКЛИКОВ</span>
              <h3 id="candidate-applications-title">История откликов</h3>
            </div>
            <span className="profileStatus">{applications.length}</span>
          </div>
          {applications.length === 0 ? (
            <div className="candidateVacancyEmpty"><strong>История пока пуста</strong><span>Ваши отклики и следующие статусы появятся здесь.</span></div>
          ) : applications.map((application) => (
            <div className="candidateApplicationCard" key={application.id}>
              <div>
                <span className="candidateVacancyCompany">{application.vacancy.company_name}</span>
                <strong>{application.vacancy.title}</strong>
              </div>
              <span className={`candidateApplicationStatus ${application.status}`}>{statusText(application.status)}</span>
              {application.match_id && <small className="candidateMatchNotice">✓ Рабочий чат разблокирован</small>}
              <small>Отправлен {new Date(application.applied_at).toLocaleDateString("ru-RU")}</small>
              <div className="candidateApplicationTimeline">
                {application.status_history.map((item) => (
                  <span key={`${item.status}-${item.changed_at}`}><i />{statusText(item.status)}</span>
                ))}
              </div>
            </div>
          ))}
        </aside>
      </div>
      {message && <small className="candidateVacanciesMessage" aria-live="polite">{message}</small>}
    </section>
  );
}
