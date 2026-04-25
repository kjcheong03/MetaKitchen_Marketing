import React, { useEffect, useState } from "react";
import { getJob, startAuto, startManual, videoUrl } from "./api.js";

const STAGE_LABELS = {
  queued: "Queued",
  picking_topic: "Sourcing trending topic",
  writing_script: "Writing script",
  uploading_avatar: "Preparing avatar",
  generating_video: "Rendering video",
  done: "Complete",
  error: "Error",
};

export default function App() {
  const [mode, setMode] = useState("auto");
  const [jobId, setJobId] = useState(null);
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    let missCount = 0;
    const tick = async () => {
      try {
        const j = await getJob(jobId);
        if (!cancelled) {
          missCount = 0;
          setJob(j);
          if (j.status !== "running") return;
          setTimeout(tick, 2500);
        }
      } catch (e) {
        if (!cancelled) {
          missCount += 1;
          if (missCount >= 3) {
            setError(
              "Lost track of this job — the backend likely restarted. Please generate again."
            );
            return;
          }
          setTimeout(tick, 5000);
        }
      }
    };
    tick();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  const busy = job && job.status === "running";

  return (
    <div className="min-h-screen bg-ink-950 text-ink-100">
      <Header />
      <main className="max-w-6xl mx-auto px-10 py-16">
        <Hero />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 mt-14">
          <section className="lg:col-span-7 space-y-8">
            <ModeTabs mode={mode} setMode={setMode} disabled={busy} />
            {mode === "auto" ? (
              <AutoPanel
                disabled={busy}
                onStart={async () => {
                  setError(null);
                  setJob(null);
                  try {
                    const { job_id } = await startAuto();
                    setJobId(job_id);
                  } catch (e) {
                    setError(e.message);
                  }
                }}
              />
            ) : (
              <ManualPanel
                disabled={busy}
                onStart={async (payload) => {
                  setError(null);
                  setJob(null);
                  try {
                    const { job_id } = await startManual(payload);
                    setJobId(job_id);
                  } catch (e) {
                    setError(e.message);
                  }
                }}
              />
            )}
            {error && (
              <div className="border border-red-900/60 bg-red-950/20 text-red-200 px-5 py-4 text-sm">
                {error}
              </div>
            )}
          </section>

          <section className="lg:col-span-5">
            <ResultPanel job={job} jobId={jobId} />
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function Header() {
  return (
    <header className="border-b border-ink-700/60">
      <div className="max-w-6xl mx-auto px-10 h-16 flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-[22px] tracking-tight">Aara</span>
          <span className="text-[10px] uppercase tracking-widest text-ink-400">
            Studio
          </span>
        </div>
        <nav className="flex items-center gap-8 text-xs text-ink-300">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="hover:text-ink-100 transition"
          >
            API
          </a>
          <span className="text-ink-500">v0.1</span>
        </nav>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <div className="max-w-2xl">
      <div className="text-[10px] uppercase tracking-widest text-accent mb-5">
        Automated Reel Generation
      </div>
      <h1 className="font-display text-5xl md:text-[56px] leading-[1.05] tracking-tight text-ink-50">
        A studio for <em className="italic">Dr Aara</em>.
      </h1>
      <p className="mt-6 text-ink-300 text-[15px] leading-relaxed max-w-xl">
        Sourcing Indian social trends, writing FSSAI-compliant scripts, and
        producing vertical video with a trained avatar. One clean workflow,
        rendered end to end.
      </p>
    </div>
  );
}

function ModeTabs({ mode, setMode, disabled }) {
  const tabs = [
    { id: "auto", label: "Automatic" },
    { id: "manual", label: "Manual" },
  ];
  return (
    <div className="flex items-center gap-8 border-b border-ink-700/60">
      {tabs.map((t) => {
        const active = mode === t.id;
        return (
          <button
            key={t.id}
            disabled={disabled}
            onClick={() => setMode(t.id)}
            className={`relative -mb-px py-4 text-[13px] tracking-wide transition ${
              active ? "text-ink-50" : "text-ink-400 hover:text-ink-200"
            } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            {t.label}
            {active && (
              <span className="absolute left-0 right-0 -bottom-px h-px bg-accent" />
            )}
          </button>
        );
      })}
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <div className="text-[10px] uppercase tracking-widest text-ink-400 mb-3">
      {children}
    </div>
  );
}

function AutoPanel({ onStart, disabled }) {
  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <SectionLabel>Workflow</SectionLabel>
        <ol className="text-[14px] text-ink-200 space-y-3">
          <Step n="01" title="Research">
            Gemini searches Indian Instagram and Facebook for metabolic-health
            topics trending in the past 14 days.
          </Step>
          <Step n="02" title="Write">
            A script is composed in Dr Aara's voice with the signature opener,
            a dry hook, and FSSAI-compliant claims.
          </Step>
          <Step n="03" title="Render">
            HeyGen renders the vertical 9:16 video using the trained avatar and
            a randomly-selected scene.
          </Step>
        </ol>
      </div>

      <button
        disabled={disabled}
        onClick={onStart}
        className={`group w-full border border-ink-100 bg-ink-100 text-ink-950 hover:bg-transparent hover:text-ink-100 transition-colors py-4 text-[13px] tracking-wider uppercase ${
          disabled ? "opacity-50 cursor-not-allowed" : ""
        }`}
      >
        {disabled ? "Rendering…" : "Generate Reel"}
      </button>
    </div>
  );
}

function Step({ n, title, children }) {
  return (
    <li className="flex gap-5">
      <span className="font-mono text-[11px] tracking-widest text-accent pt-0.5 w-8">
        {n}
      </span>
      <div>
        <div className="text-ink-50 text-[14px]">{title}</div>
        <div className="text-ink-300 text-[13px] leading-relaxed mt-1">
          {children}
        </div>
      </div>
    </li>
  );
}

function ManualPanel({ onStart, disabled }) {
  const [script, setScript] = useState(
    "Aara here! Let me guess: roti for breakfast, a sweet chai, and now it's eleven AM and you want a nap. That's not your body failing. That's a glucose spike crashing three hours later. Swap the order — ten grams of protein and five grams of fiber before the roti. Spoonful of curd. A few almonds. The crash disappears. Measured on glucose monitors in Indian adults. Follow @draara for more."
  );
  const [scenePrompt, setScenePrompt] = useState("");

  const canSubmit = script.trim().length > 10 && !disabled;

  return (
    <div className="space-y-8">
      <div>
        <SectionLabel>Script</SectionLabel>
        <textarea
          rows={8}
          className="w-full bg-ink-900 border border-ink-700 focus:border-accent focus:outline-none text-[14px] leading-relaxed text-ink-100 px-4 py-3"
          value={script}
          onChange={(e) => setScript(e.target.value)}
        />
        <p className="text-[11px] text-ink-400 mt-2 tracking-wide">
          Read aloud verbatim by the avatar. Seventy-five words is roughly thirty seconds.
        </p>
      </div>

      <div>
        <SectionLabel>Scene prompt (optional)</SectionLabel>
        <input
          type="text"
          placeholder="Leave blank to use a randomly selected scene"
          className="w-full bg-ink-900 border border-ink-700 focus:border-accent focus:outline-none text-[14px] text-ink-100 px-4 py-3"
          value={scenePrompt}
          onChange={(e) => setScenePrompt(e.target.value)}
        />
        <p className="text-[11px] text-ink-400 mt-2 tracking-wide">
          Overrides the random scene for this render only.
        </p>
      </div>

      <button
        disabled={!canSubmit}
        onClick={() => onStart({ script: script.trim(), scenePrompt: scenePrompt.trim() })}
        className={`w-full border border-ink-100 bg-ink-100 text-ink-950 hover:bg-transparent hover:text-ink-100 transition-colors py-4 text-[13px] tracking-wider uppercase ${
          !canSubmit ? "opacity-50 cursor-not-allowed" : ""
        }`}
      >
        {disabled ? "Rendering…" : "Render Video"}
      </button>
    </div>
  );
}

function ResultPanel({ job, jobId }) {
  if (!jobId) {
    return (
      <aside className="border border-ink-700/60 min-h-[480px] flex flex-col">
        <div className="px-6 py-4 border-b border-ink-700/60">
          <div className="text-[10px] uppercase tracking-widest text-ink-400">
            Output
          </div>
        </div>
        <div className="flex-1 grid place-items-center text-center px-8">
          <div>
            <div className="font-display italic text-2xl text-ink-300">
              Nothing rendered yet.
            </div>
            <div className="text-[12px] text-ink-400 mt-3 tracking-wide">
              Generate a Reel to see the output here.
            </div>
          </div>
        </div>
      </aside>
    );
  }

  if (!job) return <OutputShell title="Initialising">Creating job…</OutputShell>;

  if (job.status === "failed") {
    return (
      <OutputShell title="Failed">
        <pre className="text-red-300 text-[12px] whitespace-pre-wrap font-mono leading-relaxed">
          {job.error || "Unknown error"}
        </pre>
      </OutputShell>
    );
  }

  if (job.status === "running") {
    return (
      <OutputShell title={STAGE_LABELS[job.stage] || job.stage}>
        <div className="space-y-5">
          <ProgressBar value={job.progress || 0} />
          <dl className="space-y-3 text-[12px]">
            {job.topic?.topic && (
              <Row label="Topic">{job.topic.topic}</Row>
            )}
            {job.heygen_status && (
              <Row label="HeyGen">{job.heygen_status}</Row>
            )}
            {job.scene_prompt && (
              <Row label="Scene">{truncate(job.scene_prompt, 120)}</Row>
            )}
          </dl>
        </div>
      </OutputShell>
    );
  }

  // succeeded
  return (
    <aside className="space-y-6">
      <div className="border border-ink-700/60 overflow-hidden">
        <video
          src={videoUrl(jobId)}
          controls
          className="w-full aspect-[9/16] bg-black object-contain"
        />
      </div>
      <a
        href={videoUrl(jobId)}
        download
        className="block text-center border border-ink-100 bg-ink-100 text-ink-950 hover:bg-transparent hover:text-ink-100 transition-colors py-4 text-[13px] tracking-wider uppercase"
      >
        Download
      </a>
      {job.post && <PostCard post={job.post} sceneUsed={job.scene_prompt} />}
    </aside>
  );
}

function OutputShell({ title, children }) {
  return (
    <aside className="border border-ink-700/60">
      <div className="px-6 py-4 border-b border-ink-700/60 flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-widest text-ink-400">
          Output
        </div>
        <div className="text-[11px] text-ink-300 tracking-wide">{title}</div>
      </div>
      <div className="px-6 py-6">{children}</div>
    </aside>
  );
}

function Row({ label, children }) {
  return (
    <div className="flex gap-5">
      <dt className="w-20 text-[10px] uppercase tracking-widest text-ink-400 pt-0.5">
        {label}
      </dt>
      <dd className="flex-1 text-ink-200 text-[13px] leading-relaxed">
        {children}
      </dd>
    </div>
  );
}

function ProgressBar({ value }) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div>
      <div className="w-full bg-ink-800 h-px relative overflow-hidden">
        <div
          className="absolute top-0 left-0 h-full bg-accent transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-2 text-[10px] tracking-widest text-ink-400 uppercase">
        {pct}%
      </div>
    </div>
  );
}

function PostCard({ post, sceneUsed }) {
  return (
    <div className="border border-ink-700/60">
      <div className="px-6 py-4 border-b border-ink-700/60">
        <div className="text-[10px] uppercase tracking-widest text-ink-400">
          Post
        </div>
      </div>
      <div className="px-6 py-5 space-y-5 text-[13px]">
        {post.topic && <Row label="Topic">{post.topic}</Row>}
        {post.hook && <Row label="Hook"><em className="font-display text-[15px] text-ink-100">"{post.hook}"</em></Row>}
        {post.script && (
          <Row label="Script">
            <p className="whitespace-pre-wrap leading-relaxed text-ink-200">
              {post.script}
            </p>
          </Row>
        )}
        {post.caption && <Row label="Caption">{post.caption}</Row>}
        {post.hashtags && post.hashtags.length > 0 && (
          <Row label="Tags">
            <div className="flex flex-wrap gap-x-2 gap-y-1 text-ink-300">
              {post.hashtags.map((h) => (
                <span key={h}>#{h}</span>
              ))}
            </div>
          </Row>
        )}
        {sceneUsed && (
          <Row label="Scene">
            <span className="text-ink-300 text-[12px] leading-relaxed">
              {sceneUsed}
            </span>
          </Row>
        )}
        <button
          onClick={() => navigator.clipboard.writeText(buildShareText(post))}
          className="w-full mt-3 border border-ink-700 hover:border-ink-100 hover:text-ink-100 text-ink-300 py-3 text-[11px] uppercase tracking-widest transition-colors"
        >
          Copy caption &amp; tags
        </button>
      </div>
    </div>
  );
}

function Footer() {
  return (
    <footer className="border-t border-ink-700/60 mt-20">
      <div className="max-w-6xl mx-auto px-10 h-14 flex items-center justify-between text-[11px] text-ink-400 tracking-wide">
        <span>Aara Studio</span>
        <span>FSSAI-compliant · Human-in-the-loop</span>
      </div>
    </footer>
  );
}

function buildShareText(post) {
  const tags = (post.hashtags || []).map((h) => `#${h}`).join(" ");
  return [post.caption, "", tags].filter(Boolean).join("\n");
}

function truncate(text, max) {
  if (!text) return "";
  return text.length > max ? text.slice(0, max - 1).trimEnd() + "…" : text;
}
