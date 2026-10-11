"""Idempotently seed public demo companies and vacancies.

This fixture creates only clearly marked synthetic employer data. It does not
touch Keycloak, candidate identities, applications, or existing vacancies.
Run with ``python -m app.seed_demo_vacancies`` from the backend container.
"""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import text

from .db import SessionFactory


COMPANIES = (
    ("Северная Звезда Лабс", "IT / Software Development", "Москва", "https://northstar.example.ru"),
    ("ФинСфера", "FinTech / Financial Services", "Москва", "https://finsfera.example.ru"),
    ("МаркетПоток", "E-commerce / Retail", "Санкт-Петербург", "https://marketpotok.example.ru"),
    ("МедТех Решения", "Healthcare / MedTech", "Новосибирск", "https://medtech.example.ru"),
    ("Открытое Обучение", "Education / EdTech", "Казань", "https://openlearning.example.ru"),
    ("Связь Плюс", "Telecom / Communications", "Москва", "https://svyazplus.example.ru"),
    ("Логистик Про", "Logistics / Transport", "Екатеринбург", "https://logisticpro.example.ru"),
    ("Городские Системы", "Public Sector / GovTech", "Нижний Новгород", "https://citysystems.example.ru"),
    ("Данные Повсюду", "IT / Software Development", "Самара", "https://datavsegda.example.ru"),
    ("Мобильный Контур", "IT / Software Development", "Ростов-на-Дону", "https://mobilekontur.example.ru"),
    ("Облако Восток", "IT / Software Development", "Владивосток", "https://cloudvostok.example.ru"),
    ("Безопасный Контур", "FinTech / Financial Services", "Москва", "https://safecontour.example.ru"),
)

VACANCIES = (
    (1, "Backend-разработчик платёжных сервисов", "backend-engineering", "middle", 280000, 380000, "hybrid", "full_time"),
    (1, "Senior Python Platform Engineer", "backend-engineering", "senior", 420000, 560000, "remote", "full_time"),
    (1, "Инженер автоматизации качества", "qa-test-automation", "middle", 220000, 320000, "hybrid", "full_time"),
    (2, "Backend-разработчик кредитных продуктов", "backend-engineering", "middle", 300000, 430000, "hybrid", "full_time"),
    (2, "Data Engineer риск-моделей", "data-engineering", "senior", 380000, 520000, "remote", "full_time"),
    (2, "QA Automation Engineer", "qa-test-automation", "junior", 150000, 220000, "office", "full_time"),
    (3, "Frontend-разработчик checkout", "frontend-engineering", "middle", 240000, 360000, "hybrid", "full_time"),
    (3, "Full-stack разработчик каталога", "full-stack-engineering", "senior", 360000, 500000, "remote", "full_time"),
    (3, "DevOps-инженер e-commerce", "devops-sre", "middle", 260000, 390000, "hybrid", "full_time"),
    (4, "Backend-разработчик медицинских систем", "backend-engineering", "senior", 340000, 480000, "hybrid", "full_time"),
    (4, "Инженер данных клинических исследований", "data-engineering", "middle", 260000, 380000, "remote", "full_time"),
    (5, "Frontend-разработчик образовательной платформы", "frontend-engineering", "junior", 140000, 210000, "remote", "full_time"),
    (5, "Методист цифровых assessment-продуктов", "full-stack-engineering", "middle", 180000, 260000, "hybrid", "full_time"),
    (6, "DevOps / SRE инженер сети", "devops-sre", "senior", 360000, 520000, "hybrid", "full_time"),
    (6, "Backend-разработчик телеком API", "backend-engineering", "middle", 280000, 400000, "office", "full_time"),
    (7, "Data Engineer маршрутизации", "data-engineering", "middle", 250000, 370000, "hybrid", "full_time"),
    (7, "Mobile-разработчик курьерского приложения", "mobile-engineering", "middle", 240000, 360000, "remote", "full_time"),
    (8, "Full-stack разработчик городских сервисов", "full-stack-engineering", "senior", 330000, 470000, "hybrid", "full_time"),
    (8, "QA Automation инженер интеграций", "qa-test-automation", "middle", 220000, 330000, "office", "full_time"),
    (9, "Data Science / ML инженер рекомендаций", "data-science-ml", "senior", 400000, 600000, "remote", "full_time"),
    (9, "Data Engineer аналитической платформы", "data-engineering", "junior", 160000, 240000, "hybrid", "full_time"),
    (10, "iOS-разработчик мобильного контура", "mobile-engineering", "senior", 360000, 520000, "hybrid", "full_time"),
    (10, "Android-разработчик приложения", "mobile-engineering", "middle", 260000, 390000, "remote", "full_time"),
    (11, "DevOps / SRE инженер облачной платформы", "devops-sre", "senior", 400000, 580000, "remote", "full_time"),
    (11, "Backend-разработчик внутренней платформы", "backend-engineering", "junior", 170000, 250000, "hybrid", "full_time"),
    (12, "Security-minded Backend Engineer", "backend-engineering", "senior", 420000, 620000, "hybrid", "full_time"),
    (12, "QA Automation для платёжного контура", "qa-test-automation", "middle", 240000, 350000, "remote", "full_time"),
    (4, "Frontend-разработчик кабинета врача", "frontend-engineering", "middle", 230000, 340000, "hybrid", "full_time"),
    (6, "Data Science инженер прогнозирования нагрузки", "data-science-ml", "middle", 300000, 450000, "remote", "full_time"),
    (7, "Full-stack разработчик операционного кабинета", "full-stack-engineering", "junior", 180000, 270000, "office", "full_time"),
)


def _id(kind: str, number: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"https://example.invalid/fsp-demo/{kind}/{number}"))


def main() -> None:
    with SessionFactory.begin() as db:
        company_ids: dict[int, str] = {}
        company_locations: dict[int, str] = {}
        for index, (name, industry, location, website) in enumerate(COMPANIES, 1):
            identity_id = _id("identity", index)
            company_id = _id("company", index)
            db.execute(
                text(
                    "INSERT INTO user_identity (id, keycloak_sub, email, role, email_verified) "
                    "VALUES (:id, :sub, :email, 'employer', true) "
                    "ON CONFLICT (keycloak_sub) DO UPDATE SET role = 'employer', email_verified = true"
                ),
                {"id": identity_id, "sub": f"demo-employer-{index:02d}", "email": f"demo-employer-{index:02d}@demo.ru"},
            )
            db.execute(
                text(
                    "INSERT INTO company (id, owner_identity_id, name, description, industry, website, location, public_contact_method) "
                    "VALUES (:id, :owner, :name, :description, :industry, :website, :location, :contact) "
                    "ON CONFLICT (owner_identity_id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, "
                    "industry = EXCLUDED.industry, website = EXCLUDED.website, location = EXCLUDED.location, "
                    "public_contact_method = EXCLUDED.public_contact_method, updated_at = CURRENT_TIMESTAMP"
                ),
                {"id": company_id, "owner": identity_id, "name": name, "description": f"Демо-компания FSP Talent: {industry}.", "industry": industry, "website": website, "location": location, "contact": f"demo-employer-{index:02d}@demo.ru"},
            )
            company_ids[index] = company_id
            company_locations[index] = location

        for index, (company_number, title, specialization, grade, salary_min, salary_max, work_mode, employment_type) in enumerate(VACANCIES, 1):
            specialization_id = db.execute(
                text("SELECT id FROM specialization WHERE slug = :slug AND active = true"),
                {"slug": specialization},
            ).scalar_one()
            grade_id = db.execute(
                text("SELECT id FROM grade WHERE slug = :slug"),
                {"slug": grade},
            ).scalar_one()
            db.execute(
                text(
                    "INSERT INTO vacancy (id, company_id, title, description, location, work_mode, employment_type, "
                    "salary_min_rub, salary_max_rub, specialization_id, grade_id, status, published_at) "
                    "VALUES (:id, :company_id, :title, :description, :location, :work_mode, :employment_type, "
                    ":salary_min, :salary_max, :specialization_id, :grade_id, 'published', CURRENT_TIMESTAMP) "
                    "ON CONFLICT (id) DO UPDATE SET company_id = EXCLUDED.company_id, title = EXCLUDED.title, "
                    "description = EXCLUDED.description, location = EXCLUDED.location, work_mode = EXCLUDED.work_mode, "
                    "employment_type = EXCLUDED.employment_type, salary_min_rub = EXCLUDED.salary_min_rub, "
                    "salary_max_rub = EXCLUDED.salary_max_rub, specialization_id = EXCLUDED.specialization_id, "
                    "grade_id = EXCLUDED.grade_id, status = 'published', published_at = COALESCE(vacancy.published_at, CURRENT_TIMESTAMP), "
                    "updated_at = CURRENT_TIMESTAMP"
                ),
                {"id": _id("vacancy", index), "company_id": company_ids[company_number], "title": title, "description": f"Демо-вакансия для проверки подбора и Talent Radar. {title}: задачи, командная работа и подтверждение навыков.", "location": company_locations[company_number], "work_mode": work_mode, "employment_type": employment_type, "salary_min": salary_min, "salary_max": salary_max, "specialization_id": specialization_id, "grade_id": grade_id},
            )

    print(f"seeded {len(COMPANIES)} demo companies and {len(VACANCIES)} published demo vacancies")


if __name__ == "__main__":
    main()
