const RETROSPECTIVE_API_BASE = "http://localhost:8000/api/retrospective-kpi";
const RETROSPECTIVE_TIME_JUSTIFICATIONS = new Set([
  "justified",
  "partially_justified",
  "not_justified",
  "insufficient_data",
]);

function isValidScore(value) {
  return typeof value === "number" &&
    Number.isFinite(value) &&
    value >= 0 &&
    value <= 100;
}

function validateQwenKpiOutput(output) {
  const hasMissingTime = output?.timeJustification === "insufficient_data" &&
    output?.timeEfficiencyScore === null;
  const hasValidOverall = output?.overallKpiScore === null || isValidScore(output?.overallKpiScore);
  if (!output ||
      output.available !== true ||
      !isValidScore(output.productivityScore) ||
      (!hasMissingTime && !isValidScore(output.timeEfficiencyScore)) ||
      !isValidScore(output.adHocWorkScore) ||
      !hasValidOverall ||
      !RETROSPECTIVE_TIME_JUSTIFICATIONS.has(output.timeJustification) ||
      typeof output.reasoning !== "string" ||
      !output.reasoning.trim()) {
    throw new Error("Qwen response did not match the required KPI JSON schema.");
  }

  return output;
}

function isEligibleTask(task) {
  const status = String(task?.status || "").trim().toLowerCase();
  return task?.qwenEligible === true &&
    task?.dataOrigin === "jira" &&
    ["done", "completed", "closed", "in progress", "active"].includes(status);
}

function numberOrNull(value) {
  if (value == null || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function round(value, decimals = 2) {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

function positiveNumberOrNull(value) {
  const numeric = numberOrNull(value);
  return numeric != null && numeric > 0 ? numeric : null;
}

function buildDeterministicKpiSummary(subject) {
  const explicit = subject?.retrospectiveDeterministicKpi;
  const trace = subject?.kpiByPeriod?.today?.trace;
  const components = explicit || trace?.components;
  const summary = {
    productivityScore: numberOrNull(components?.productivityScore ?? components?.productivity),
    timeEfficiencyScore: numberOrNull(components?.timeEfficiencyScore ?? components?.timeEfficiency),
    adHocWorkScore: numberOrNull(components?.adHocWorkScore ?? components?.adHoc),
    overallKpiScore: numberOrNull(components?.overallKpiScore ?? trace?.score),
  };
  return summary;
}

function buildRetrospectiveSummary(subject) {
  if (!subject || typeof subject !== "object") {
    throw new Error("A real retrospective subject is required.");
  }

  console.debug("[Qwen retrospective][frontend] Subject used for evaluation", subject);

  const tasks = Array.isArray(subject.tasks)
    ? subject.tasks.filter(isEligibleTask)
    : [];
  if (!tasks.length) {
    throw new Error("No real Jira tasks are eligible for retrospective evaluation.");
  }

  const completedTaskCount = tasks.filter((task) =>
    ["done", "completed", "closed"].includes(String(task.status || "").trim().toLowerCase())
  ).length;
  const inProgressTaskCount = tasks.filter((task) =>
    ["in progress", "active"].includes(String(task.status || "").trim().toLowerCase())
  ).length;
  const loggedEstimateHours = tasks
    .map((task) => numberOrNull(task.estimateHours))
    .filter((value) => value !== null);
  const loggedSpentHours = tasks
    .map((task) => numberOrNull(task.spentHours))
    .filter((value) => value !== null);
  const estimateHoursFromTasks = loggedEstimateHours.length === tasks.length
    ? positiveNumberOrNull(loggedEstimateHours.reduce((sum, value) => sum + value, 0))
    : null;
  const spentHoursFromTasks = loggedSpentHours.length === tasks.length
    ? positiveNumberOrNull(loggedSpentHours.reduce((sum, value) => sum + value, 0))
    : null;
  const mappedEstimateHoursTotal = positiveNumberOrNull(subject.totalEstimate) ?? estimateHoursFromTasks;
  const mappedSpentHoursTotal = positiveNumberOrNull(subject.totalSpent) ?? spentHoursFromTasks;
  const estimateHoursTotal = mappedEstimateHoursTotal == null ? null : round(mappedEstimateHoursTotal);
  const spentHoursTotal = mappedSpentHoursTotal == null ? null : round(mappedSpentHoursTotal);
  const attributedActiveMinutes = round(tasks.reduce(
    (sum, task) => sum + ((numberOrNull(task.activityWatchActiveHours) || 0) * 60),
    0
  ), 1);
  const activityAvailable = subject.activityData?.available === true;
  const mappedActiveMinutes = positiveNumberOrNull(subject.activeHours) == null
    ? null
    : round(positiveNumberOrNull(subject.activeHours) * 60, 1);
  const activeMinutes = attributedActiveMinutes > 0
    ? attributedActiveMinutes
    : numberOrNull(subject.activityData?.active_minutes) ?? mappedActiveMinutes;
  const idleMinutes = activityAvailable
    ? numberOrNull(subject.activityData.idle_minutes)
    : null;

  const uniqueCommits = new Map();
  tasks.forEach((task) => {
    (Array.isArray(task.linkedCommits) ? task.linkedCommits : []).forEach((commit, index) => {
      const key = commit.sha || `${task.id}:${index}:${commit.date || ""}`;
      if (!uniqueCommits.has(key)) uniqueCommits.set(key, commit);
    });
  });
  const commits = [...uniqueCommits.values()];
  const tasksWithCommitEvidence = tasks.filter((task) => Number(task.linkedCommitCount || 0) > 0).length;
  const subjectCommitCount = numberOrNull(subject.totalCommits);

  const summary = {
    taskCount: tasks.length,
    totalTaskCount: tasks.length,
    completedTaskCount,
    inProgressTaskCount,
    activeTaskCount: inProgressTaskCount,
    estimateHoursTotal,
    spentHoursTotal,
    activeMinutes,
    idleMinutes,
    commitCount: subjectCommitCount ?? commits.length,
    additions: commits.reduce((sum, commit) => sum + (numberOrNull(commit.additions) || 0), 0),
    deletions: commits.reduce((sum, commit) => sum + (numberOrNull(commit.deletions) || 0), 0),
    filesChanged: commits.reduce((sum, commit) => {
      if (Array.isArray(commit.files)) return sum + commit.files.length;
      return sum + (numberOrNull(commit.filesChanged) || 0);
    }, 0),
    completedTaskRate: round((completedTaskCount / tasks.length) * 100, 1),
    commitCoverageRate: round((tasksWithCommitEvidence / tasks.length) * 100, 1),
    estimateAccuracyRatio: estimateHoursTotal > 0 && spentHoursTotal !== null
      ? round(spentHoursTotal / estimateHoursTotal)
      : null,
    deterministicKpi: buildDeterministicKpiSummary(subject),
  };
  console.debug("[Qwen retrospective][frontend] Payload sent to backend", summary);
  return summary;
}

async function readJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const details = await response.text();
    throw new Error(`Retrospective request failed (${response.status}): ${details}`);
  }
  return response.json();
}

function statusUrl(subjectType, subjectId) {
  return `${RETROSPECTIVE_API_BASE}/status/${encodeURIComponent(subjectType)}/${encodeURIComponent(subjectId)}`;
}

function getRetrospectiveKpiStatus(subjectType, subjectId) {
  return readJson(statusUrl(subjectType, subjectId)).then((response) => {
    console.debug("[Qwen retrospective][frontend] Status polling response", { subjectType, subjectId, response });
    return response;
  });
}

function startRetrospectiveKpi(subjectType, subjectId, subject) {
  const payload = buildRetrospectiveSummary(subject);
  return readJson(`${RETROSPECTIVE_API_BASE}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      subject_type: subjectType,
      subject_id: subjectId,
      payload,
    }),
  }).then((response) => {
    console.debug("[Qwen retrospective][frontend] Backend start response", { subjectType, subjectId, payload, response });
    return response;
  });
}

window.OllamaQwenKpi = {
  buildRetrospectiveSummary,
  getRetrospectiveKpiStatus,
  startRetrospectiveKpi,
  validateQwenKpiOutput,
};
