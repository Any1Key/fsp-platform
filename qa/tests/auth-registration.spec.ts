import { test, expect, type APIRequestContext } from "@playwright/test";
import { createHash, randomBytes } from "node:crypto";

const enabled = process.env.AUTH_E2E_ENABLED === "true";
const keycloakBaseUrl = process.env.KEYCLOAK_E2E_BASE_URL || "http://keycloak:8080";
const keycloakPublicBaseUrl = process.env.KEYCLOAK_PUBLIC_E2E_BASE_URL || keycloakBaseUrl;
const mailpitBaseUrl = process.env.MAILPIT_BASE_URL || "http://mailpit:8025";
const realm = "fsp";

type KeycloakUser = {
  id: string;
  email: string;
  emailVerified: boolean;
};

async function adminToken(request: APIRequestContext): Promise<string> {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try {
      const response = await request.post(
        `${keycloakBaseUrl}/realms/master/protocol/openid-connect/token`,
        {
          form: {
            client_id: "admin-cli",
            grant_type: "password",
            username: process.env.KEYCLOAK_ADMIN_USERNAME || "admin",
            password: process.env.KEYCLOAK_ADMIN_PASSWORD || "",
          },
        },
      );
      if (response.ok()) {
        return ((await response.json()) as { access_token: string }).access_token;
      }
    } catch {
      // Compose starts QA after the API/frontend, while Keycloak may still be booting.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("Timed out waiting for the Keycloak admin endpoint");
}

async function findUser(
  request: APIRequestContext,
  token: string,
  email: string,
): Promise<KeycloakUser | undefined> {
  const response = await request.get(`${keycloakBaseUrl}/admin/realms/${realm}/users`, {
    headers: { Authorization: `Bearer ${token}` },
    params: { email, exact: "true" },
  });
  expect(response.ok()).toBeTruthy();
  const users = (await response.json()) as KeycloakUser[];
  return users.find((user) => user.email.toLowerCase() === email.toLowerCase());
}

async function waitFor<T>(loader: () => Promise<T | undefined>): Promise<T> {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const result = await loader();
    if (result !== undefined) return result;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("Timed out waiting for the Keycloak/Mailpit state");
}

function verificationLink(message: Record<string, unknown>): string {
  const html = String(message.HTML || message.Html || "");
  const text = String(message.Text || message.text || "");
  const candidate =
    html.match(/href=["']([^"']*\/login-actions\/action-token[^"']*)["']/i)?.[1] ||
    text.match(/https?:\/\/[^\s<]+\/login-actions\/action-token[^\s<]*/i)?.[0];
  if (!candidate) throw new Error("Mailpit message did not contain a Keycloak verification link");

  const decoded = candidate.replaceAll("&amp;", "&");
  const link = new URL(decoded);
  // Keycloak may build the email link from the public host. The test browser
  // reaches the service over the Compose network, so keep the path/token but
  // use the internal service address.
  if (link.hostname === "localhost" || link.hostname === "127.0.0.1") {
    link.hostname = "keycloak";
    link.port = "8080";
  }
  return link.toString();
}

async function findVerificationMessage(
  request: APIRequestContext,
  email: string,
): Promise<Record<string, unknown> | undefined> {
  const listResponse = await request.get(`${mailpitBaseUrl}/api/v1/messages`, {
    params: { limit: "50" },
  });
  expect(listResponse.ok()).toBeTruthy();
  const list = (await listResponse.json()) as { messages?: Array<{ ID?: string; Id?: string }> };
  for (const item of list.messages || []) {
    const id = item.ID || item.Id;
    if (!id) continue;
    const messageResponse = await request.get(`${mailpitBaseUrl}/api/v1/message/${id}`);
    expect(messageResponse.ok()).toBeTruthy();
    const message = (await messageResponse.json()) as Record<string, unknown>;
    if (JSON.stringify(message).toLowerCase().includes(email.toLowerCase())) return message;
  }
  return undefined;
}

test.describe("Keycloak email verification", () => {
  test.skip(!enabled, "Compose auth E2E is enabled only in the test profile");

  test("registers a .ru user and verifies it through Mailpit", async ({ page, request }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-1920", "Run the external auth journey once, not per responsive viewport");
    test.setTimeout(90_000);
    const projectSlug = testInfo.project.name.replace(/[^a-z0-9]+/gi, "-").toLowerCase();
    const email = `qa-${projectSlug}-${Date.now()}@demo.ru`;
    const password = "Fsp-QA-Verification-2026!";
    const token = await adminToken(request);
    let user: KeycloakUser | undefined;

    try {
      const registrationUrl = new URL(`${keycloakPublicBaseUrl}/realms/${realm}/protocol/openid-connect/registrations`);
      registrationUrl.searchParams.set("client_id", "fsp-web");
      registrationUrl.searchParams.set("response_type", "code");
      registrationUrl.searchParams.set("scope", "openid");
      registrationUrl.searchParams.set("redirect_uri", "http://frontend:3000/");
      const verifier = randomBytes(32).toString("base64url");
      const challenge = createHash("sha256").update(verifier).digest("base64url");
      registrationUrl.searchParams.set("code_challenge_method", "S256");
      registrationUrl.searchParams.set("code_challenge", challenge);
      await page.goto(registrationUrl.toString());

      await expect(page.locator('input[name="username"]')).toBeVisible();
      await page.locator('input[name="username"]').fill(email);
      await page.locator('input[name="email"]').fill(email);
      await page.locator('input[name="firstName"]').fill("QA");
      await page.locator('input[name="lastName"]').fill("Verification");
      // Password is normally rendered by Keycloak's registration flow. Keep
      // the probe compatible with realms that delegate first-login credential
      // setup to a later onboarding action.
      if (await page.locator('input[name="password"]').count()) {
        await page.locator('input[name="password"]').fill(password);
        await page.locator('input[name="password-confirm"]').fill(password);
      }
      await page.getByRole("button", { name: /register|зарегистрировать/i }).click();

      user = await waitFor(() => findUser(request, token, email));
      expect(user.emailVerified).toBe(false);

      const message = await waitFor(() => findVerificationMessage(request, email));
      await page.goto(verificationLink(message));

      const verifiedUser = await waitFor(async () => {
        const current = await findUser(request, token, email);
        return current?.emailVerified ? current : undefined;
      });
      expect(verifiedUser.emailVerified).toBe(true);
    } finally {
      const cleanupUser = user || (await findUser(request, token, email));
      if (cleanupUser) {
        const response = await request.delete(`${keycloakBaseUrl}/admin/realms/${realm}/users/${cleanupUser.id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        expect(response.ok()).toBeTruthy();
      }
    }
  });
});
