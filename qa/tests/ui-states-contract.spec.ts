import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd(), "../");

function source(name: string) {
  return fs.readFileSync(path.join(root, "frontend/src/components", name), "utf8");
}

test("shared data-surface state vocabulary is adopted by core journeys", () => {
  const stateSource = source("ui-state.tsx");
  for (const state of ["loading", "empty", "error", "unconfirmed-grade"]) {
    expect(stateSource).toContain(`data-ui-state=\"${state}\"`);
  }

  expect(source("candidate-skill-passport.tsx")).toContain("<UnconfirmedGradeBadge compact />");
  expect(source("employer-talent-radar.tsx")).toContain("<UnconfirmedGradeBadge />");
  expect(source("employer-talent-radar.tsx")).toContain("<EmptyState className=\"radarEmpty\"");
  expect(source("validation-dashboard.tsx")).toContain("<LoadingState");
  expect(source("auth-status.tsx")).toContain("<ErrorState");
});
