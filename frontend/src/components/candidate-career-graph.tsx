"use client";

import { useEffect, useState } from "react";

type GraphNode = {
  id: string;
  kind: "position" | "skill";
  label: string;
  status: "verified" | "unconfirmed" | "declared";
  confidence: number;
  evidence_count: number;
  freshness: "fresh" | "aging" | "stale" | "future" | "not_available";
  sources: string[];
  details: string;
};

type GraphPath = {
  id: string;
  specialization: { slug: string; name: string };
  grade: { slug: string; name: string; rank: number };
  relation: "current" | "next" | "adjacent";
  readiness: "current" | "explore";
  match_score: number;
  matched_skills: string[];
  gap_skills: string[];
  reasons: string[];
  evidence_basis: "verified_and_unconfirmed" | "no_mapped_evidence";
};

type CareerGraph = {
  version: string;
  profile: { display_name: string | null; headline: string | null };
  status: "not_started" | "active" | "unconfirmed";
  current_position: {
    specialization: { slug: string; name: string };
    grade: { slug: string; name: string; rank: number };
    grade_state: "verified" | "not_confirmed";
    score: number;
    assessed_at: string;
  } | null;
  nodes: GraphNode[];
  paths: GraphPath[];
  summary: {
    verified_skills: number;
    unconfirmed_skills: number;
    declared_skills: number;
    evidence_nodes: number;
    path_count: number;
    gap_count: number;
  };
  next_step: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const statusLabels: Record<GraphNode["status"], string> = {
  verified: "VERIFIED",
  unconfirmed: "NOT CONFIRMED",
  declared: "DECLARED",
};

const relationLabels: Record<GraphPath["relation"], string> = {
  current: "ТЕКУЩАЯ ПОЗИЦИЯ",
  next: "СЛЕДУЮЩИЙ ШАГ",
  adjacent: "СМЕЖНЫЙ ТРЕК",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function CandidateCareerGraph({ token, refreshKey = 0 }: { token: string; refreshKey?: number }) {
  const [graph, setGraph] = useState<CareerGraph | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let active = true;
    setState("loading");
    fetch(`${apiUrl}/api/v1/candidate/career-graph`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("career_graph_unavailable");
        return (await response.json()) as CareerGraph;
      })
      .then((value) => {
        if (!active) return;
        setGraph(value);
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });

    return () => {
      active = false;
    };
  }, [token, refreshKey]);

  if (state === "loading") {
    return <section className="careerGraphPanel muted" aria-busy="true">Строим твою Career Graph…</section>;
  }
  if (state === "error" || !graph) {
    return <section className="careerGraphPanel error" role="alert">Не удалось загрузить Career Graph. Обнови страницу и попробуй ещё раз.</section>;
  }

  const skillNodes = graph.nodes.filter((node) => node.kind === "skill");
  return (
    <section className="careerGraphPanel" aria-labelledby="career-graph-title">
      <div className="careerGraphHeading">
        <div>
          <span className="authLabel">CAREER GRAPH · EVIDENCE MAP</span>
          <h2 id="career-graph-title">Куда растёт твой профиль</h2>
          <p>Связываем проверенные сигналы с соседними профессиональными треками.</p>
        </div>
        <span className={`careerGraphStatus ${graph.status}`}>
          {graph.status === "active" ? "TRACK ACTIVE" : graph.status === "unconfirmed" ? "GRADE NOT CONFIRMED" : "STARTING POINT"}
        </span>
      </div>

      {graph.current_position ? (
        <div className="careerGraphCurrent">
          <div>
            <span>СЕЙЧАС</span>
            <strong>{graph.current_position.specialization.name}</strong>
            <small>{graph.current_position.grade.name} · оценка {formatDate(graph.current_position.assessed_at)}</small>
          </div>
          <div>
            <span>{graph.current_position.grade_state === "verified" ? "GRADE VERIFIED" : "GRADE NOT CONFIRMED"}</span>
            <strong>{Math.round(graph.current_position.score)}<small>/100</small></strong>
            <small>системный результат</small>
          </div>
        </div>
      ) : (
        <div className="careerGraphEmpty">
          <strong>Точка старта ещё не определена</strong>
          <p>{graph.next_step}</p>
        </div>
      )}

      {graph.current_position && (
        <div className="careerGraphFlow" aria-label="Карьерные пути">
          <div className="careerGraphColumn">
            <div className="careerGraphColumnHeading"><span>01</span><strong>ТВОИ СИГНАЛЫ</strong><small>{skillNodes.length} nodes</small></div>
            <div className="careerGraphNodes">
              {skillNodes.map((node) => (
                <article className={`careerGraphNode ${node.status}`} key={node.id}>
                  <div>
                    <strong>{node.label}</strong>
                    <span>{statusLabels[node.status]}</span>
                  </div>
                  <small>{node.details}</small>
                </article>
              ))}
            </div>
          </div>
          <div className="careerGraphConnector" aria-hidden="true">→</div>
          <div className="careerGraphColumn careerGraphPaths">
            <div className="careerGraphColumnHeading"><span>02</span><strong>ВОЗМОЖНЫЕ ТРЕКИ</strong><small>{graph.paths.length} paths</small></div>
            {graph.paths.map((path) => (
              <article className={`careerGraphPath ${path.relation}`} key={path.id}>
                <div className="careerGraphPathTop">
                  <div><span>{relationLabels[path.relation]}</span><strong>{path.specialization.name} · {path.grade.name}</strong></div>
                  <b>{path.match_score}%</b>
                </div>
                {path.gap_skills.length > 0 && <p><i>GAP</i> {path.gap_skills.join(" · ")}</p>}
                <small>{path.reasons[0]}</small>
              </article>
            ))}
          </div>
        </div>
      )}

      <div className="careerGraphSummary" aria-label="Сводка графа">
        <span><strong>{graph.summary.verified_skills}</strong> verified</span>
        <span><strong>{graph.summary.declared_skills}</strong> declared</span>
        <span><strong>{graph.summary.gap_count}</strong> gaps to explore</span>
        <small>{graph.next_step}</small>
      </div>
    </section>
  );
}
