# Design system

## Semantic tokens

```css
--brand-primary: #402FFF;
--brand-accent: #EC1D35;
--brand-light: #EDEDED;
--brand-muted: #C8C9CA;
--brand-ink: #1B1C21;

--surface-page: #F7F7FA;
--surface-card: #FFFFFF;
--surface-inverse: #1B1C21;
--text-primary: #1B1C21;
--text-secondary: #5E6068;
--border-default: #E0E0E6;
--action-primary: #402FFF;
--action-danger: #EC1D35;
```

Derived hover/focus/status colors must pass contrast checks.

## Shape / spacing

- cards: 16–20 px radius;
- controls: 10–14 px radius;
- restrained shadows;
- 4/8-based spacing.

## Layout

Desktop:
- max content width about 1440px;
- employer discovery may use filter sidebar + results + details drawer.

Mobile:
- filters become a sheet/drawer;
- tables become cards or safe responsive layouts;
- no viewport horizontal overflow;
- primary CTA remains reachable.

## Core components

Button, IconButton, Input, Textarea, Select/Combobox, Checkbox/Switch, Badge, VerifiedBadge,
Card, EmptyState, Skeleton, Alert, Dialog, Drawer, Tabs, Progress, ScoreRing/ScoreBar,
SkillEvidence, SalaryRange, MatchBreakdown, Timeline, DataTable, Pagination.

## Candidate UI priorities

1. verified category;
2. assessment result;
3. verified skills/evidence;
4. FSP evidence;
5. freshness;
6. invitations.

Declared and verified skills must look different.

## Employer UI

The main workflow must feel like **talent discovery**, not incoming-resume triage.

Candidate card:
- identity/privacy mode;
- specialization + grade;
- match score;
- top reasons;
- verified skill chips;
- assessment strength;
- FSP badge if applicable;
- freshness;
- View profile;
- Send invitation.

## Salary

High-visibility information. Do not bury it.

## Motion/accessibility

- subtle 120–220 ms transitions;
- honor reduced motion;
- keyboard/focus/semantic status;
- practical WCAG 2.2 AA target.
