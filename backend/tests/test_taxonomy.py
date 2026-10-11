def test_taxonomy_api_returns_database_catalog_and_composed_categories(auth_context):
    client, _, _ = auth_context

    response = client.get("/api/v1/taxonomy")

    assert response.status_code == 200
    body = response.json()
    assert {item["name"] for item in body["industries"]} == {
        "IT / Software Development",
        "FinTech / Financial Services",
        "E-commerce / Retail",
        "Healthcare / MedTech",
        "Education / EdTech",
        "Telecom / Communications",
        "Logistics / Transport",
        "Public Sector / GovTech",
    }
    assert {item["slug"] for item in body["grades"]} == {"junior", "middle", "senior"}
    assert {item["slug"] for item in body["specializations"]} == {
        "backend-engineering",
        "frontend-engineering",
        "full-stack-engineering",
        "qa-test-automation",
        "devops-sre",
        "data-engineering",
        "data-science-ml",
        "mobile-engineering",
    }

    backend = next(item for item in body["specializations"] if item["slug"] == "backend-engineering")
    assert {skill["slug"] for skill in backend["skills"]} == {
        "python",
        "sql",
        "rest-apis",
        "git",
    }
    assert len(body["categories"]) == 24
    assert {item["key"] for item in body["categories"]} >= {
        "backend-engineering:junior",
        "backend-engineering:middle",
        "backend-engineering:senior",
    }
    assert all(item["label"] for item in body["categories"])


def test_taxonomy_is_read_only_and_does_not_require_auth(auth_context):
    client, _, _ = auth_context

    response = client.get("/api/v1/taxonomy")

    assert response.status_code == 200
    assert "error" not in response.json()
