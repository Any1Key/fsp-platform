"use client";

import { useEffect, useState } from "react";

type MetricGroup = {
  matching_metrics_version: string;
  keyword_baseline_version: string;
  matching_validation_version: string;
  precision_at_5: number;
  ndcg_at_5: number;
  recall_at_10: number;
  ranking_count: number;
};

type AssessmentGroup = {
  validation_version: string;
  specialization: string;
  candidates_per_grade: number;
  sample_size: number;
  macro_f1: number;
  grade_agreement: number;
  confusion_matrix: Record<string, Record<string, number>>;
  predicted_distribution: Record<string, number>;
  grade_collapse: boolean;
  grade_collapse_threshold: number;
  grade_collapse_dominant_grade: string | null;
  grade_collapse_share: number;
  equivalent_form_score_difference: number;
  retest_agreement: number;
  mean_item_discrimination: number;
  positive_item_discrimination_rate: number;
  critical_domain_reliability: Record<string, number>;
  form_uniqueness_rate: number;
  item_metrics: Record<string, { discrimination: number; difficulty: number; observations: number; pass_rate: number }>;
};

type ValidationDashboardData = {
  dashboard_version: string;
  dataset: { version: string; seed: string; candidate_count: number; need_count: number };
  matching: MetricGroup;
  assessment: AssessmentGroup;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const grades = ["Junior", "Middle", "Senior"];

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function ValidationDashboard({ token }: { token: string }) {
  const [dashboard, setDashboard] = useState<ValidationDashboardData | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let active = true;
    setState("loading");
    fetch(`${apiUrl}/api/v1/validation/dashboard`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("validation_dashboard_unavailable");
        return (await response.json()) as ValidationDashboardData;
      })
      .then((value) => {
        if (!active) return;
        setDashboard(value);
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });

    return () => {
      active = false;
    };
  }, [token]);

  if (state === "loading") {
    return <section className="validationPanel muted" aria-busy="true">Загружаем Validation Dashboard…</section>;
  }
  if (state === "error" || !dashboard) {
    return <section className="validationPanel error" role="alert">Не удалось загрузить Validation Dashboard. Проверь права доступа и обнови страницу.</section>;
  }

  const { matching, assessment } = dashboard;
  const itemMetrics = Object.entries(assessment.item_metrics);

  return (
    <section className="validationPanel" aria-labelledby="validation-dashboard-title">
      <div className="validationHeading">
        <div>
          <span className="authLabel">VALIDATION DASHBOARD · {dashboard.dashboard_version}</span>
          <h2 id="validation-dashboard-title">Доказательная база подбора</h2>
          <p>Синтетическая калибровка matching и assessment в одном проверяемом срезе.</p>
        </div>
        <span className="validationBadge">DEMO EVIDENCE</span>
      </div>

      <div className="validationNotice">
        <strong>Важно для интерпретации</strong>
        <span>Это воспроизводимые synthetic-результаты, а не production-решение о найме и не внешняя верификация.</span>
      </div>

      <div className="validationMeta">
        <span><b>{dashboard.dataset.candidate_count}</b> candidates</span>
        <span><b>{dashboard.dataset.need_count}</b> hiring needs</span>
        <span>dataset <b>{dashboard.dataset.version}</b></span>
        <span>seed <b>{dashboard.dataset.seed}</b></span>
      </div>

      <div className="validationSection">
        <div className="validationSectionHeading">
          <div><span className="authLabel">PROOFMATCH BASELINE</span><h3>Ranking quality</h3></div>
          <small>{matching.ranking_count} complete need rankings</small>
        </div>
        <div className="validationMetricGrid">
          <div className="validationMetric"><span>Precision@5</span><strong>{percent(matching.precision_at_5)}</strong><small>relevant + adjacent</small></div>
          <div className="validationMetric"><span>nDCG@5</span><strong>{percent(matching.ndcg_at_5)}</strong><small>graded relevance gain</small></div>
          <div className="validationMetric"><span>Recall@10</span><strong>{percent(matching.recall_at_10)}</strong><small>positive labels found</small></div>
        </div>
      </div>

      <div className="validationSection">
        <div className="validationSectionHeading">
          <div><span className="authLabel">ASSESSMENT CALIBRATION</span><h3>{assessment.specialization}</h3></div>
          <small>{assessment.sample_size} labeled attempts · {assessment.validation_version}</small>
        </div>
        <div className="validationMetricGrid">
          <div className="validationMetric"><span>Macro-F1</span><strong>{percent(assessment.macro_f1)}</strong><small>grade discrimination</small></div>
          <div className="validationMetric"><span>Grade agreement</span><strong>{percent(assessment.grade_agreement)}</strong><small>target vs predicted</small></div>
          <div className="validationMetric"><span>Unique forms</span><strong>{percent(assessment.form_uniqueness_rate)}</strong><small>session-specific variants</small></div>
          <div className="validationMetric"><span>Retest agreement</span><strong>{percent(assessment.retest_agreement)}</strong><small>same synthetic ability</small></div>
        </div>

        <div className="validationEvidenceGrid">
          <div className="validationTableCard">
            <div className="validationCardHeading"><h4>Confusion matrix</h4><small>actual × predicted</small></div>
            <div className="validationTableWrap">
              <table className="validationTable">
                <thead><tr><th scope="col">Actual</th>{grades.map((grade) => <th scope="col" key={grade}>{grade}</th>)}</tr></thead>
                <tbody>{grades.map((actual) => <tr key={actual}><th scope="row">{actual}</th>{grades.map((predicted) => <td key={predicted}>{assessment.confusion_matrix[actual]?.[predicted] ?? 0}</td>)}</tr>)}</tbody>
              </table>
            </div>
          </div>
          <div className="validationTableCard">
            <div className="validationCardHeading"><h4>Item discrimination</h4><small>family-level signal</small></div>
            <div className="validationItemList">{itemMetrics.map(([itemId, metric]) => (
              <div className="validationItemRow" key={itemId}>
                <span>{itemId}</span><i><b style={{ width: `${Math.max(0, Math.min(100, metric.discrimination * 100))}%` }} /></i><strong className={metric.discrimination > 0 ? "positive" : "attention"}>{metric.discrimination.toFixed(2)}</strong>
              </div>
            ))}</div>
          </div>
        </div>

        <div className={`validationCollapse ${assessment.grade_collapse ? "attention" : "pass"}`}>
          <strong>{assessment.grade_collapse ? "Grade-collapse signal detected" : "Grade-collapse check passed"}</strong>
          <span>{assessment.grade_collapse ? `${assessment.grade_collapse_dominant_grade} = ${percent(assessment.grade_collapse_share)} of predictions` : `dominant grade share ${percent(assessment.grade_collapse_share)} · threshold ${percent(assessment.grade_collapse_threshold)}`}</span>
        </div>
      </div>

      <small className="validationFooter">Source versions: matching {matching.matching_metrics_version} · baseline {matching.keyword_baseline_version} · assessment {assessment.validation_version}. Negative item signals remain visible for calibration follow-up.</small>
    </section>
  );
}
