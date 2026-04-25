const BASE = "";

export async function startAuto() {
  const r = await fetch(`${BASE}/api/generate/auto`, { method: "POST" });
  if (!r.ok) throw new Error(`Auto start failed: ${r.status}`);
  return r.json();
}

export async function startManual({ script, scenePrompt }) {
  const fd = new FormData();
  fd.append("script", script);
  if (scenePrompt) fd.append("scene_prompt", scenePrompt);
  const r = await fetch(`${BASE}/api/generate/manual`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(`Manual start failed: ${r.status}`);
  return r.json();
}

export async function getJob(jobId) {
  const r = await fetch(`${BASE}/api/jobs/${jobId}`);
  if (!r.ok) throw new Error(`Job fetch failed: ${r.status}`);
  return r.json();
}

export function videoUrl(jobId) {
  return `${BASE}/api/jobs/${jobId}/video`;
}
