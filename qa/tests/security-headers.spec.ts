import { test, expect } from "@playwright/test";

test("frontend emits baseline browser security headers", async ({ request }) => {
  const response = await request.get("/");

  expect(response.ok()).toBeTruthy();
  expect(response.headers()["x-content-type-options"]).toBe("nosniff");
  expect(response.headers()["x-frame-options"]).toBe("DENY");
  expect(response.headers()["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  expect(response.headers()["permissions-policy"]).toBe(
    "camera=(), microphone=(), geolocation=(), payment=()"
  );
  expect(response.headers()["x-powered-by"]).toBeUndefined();
});

test("backend keeps CORS explicit and supports delete preflight", async ({ request }) => {
  const base = process.env.BACKEND_BASE_URL || "http://backend:8000";
  const origin = process.env.E2E_FRONTEND_ORIGIN || "http://frontend:3000";
  const response = await request.fetch(`${base}/api/v1/candidate/fsp-link`, {
    method: "OPTIONS",
    headers: {
      Origin: origin,
      "Access-Control-Request-Method": "DELETE",
      "Access-Control-Request-Headers": "Authorization"
    }
  });

  expect(response.status()).toBe(200);
  expect(response.headers()["access-control-allow-origin"]).toBe(origin);
  expect(response.headers()["access-control-allow-methods"]).toContain("DELETE");
  expect(response.headers()["x-content-type-options"]).toBe("nosniff");
});
