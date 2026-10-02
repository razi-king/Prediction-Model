"use client";

import { useState } from "react";

// GitHub language names -> skill names used by our model
const GITHUB_TO_SKILL = {
  HTML: "HTML/CSS", CSS: "HTML/CSS", SCSS: "HTML/CSS", Shell: "Bash/Shell", "Jupyter Notebook": "Python",
  Vue: "Vue.js", "C#": "C#", "C++": "C++", "Objective-C": "Objective-C", Dockerfile: "Docker",
  HCL: "Terraform", TSQL: "SQL", PLpgSQL: "PostgreSQL", Svelte: "Svelte",
};

/**
 * Bonus feature: reads the user's public GitHub repositories (GitHub REST API, no login needed)
 * and adds the languages they use to the skill list.
 */
export default function GitHubImport({ allSkills, onSkills }) {
  const [username, setUsername] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  async function fetchSkills() {
    if (!username.trim()) return;
    setBusy(true);
    setStatus("");
    try {
      const res = await fetch(`https://api.github.com/users/${encodeURIComponent(username.trim())}/repos?per_page=100`);
      if (res.status === 404) throw new Error("GitHub user not found");
      if (!res.ok) throw new Error("GitHub API limit reached, try again later");
      const repos = await res.json();
      const found = new Set();
      for (const repo of repos) {
        if (!repo.language) continue;
        const skill = GITHUB_TO_SKILL[repo.language] || repo.language;
        if (allSkills.includes(skill)) found.add(skill);
      }
      onSkills([...found]);
      setStatus(found.size ? `Added ${found.size} skills from ${repos.length} repos` : "No known languages found");
    } catch (err) {
      setStatus(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="field">
      <label htmlFor="gh-user">Fetch skills from GitHub (optional)</label>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          id="gh-user" className="input" placeholder="GitHub username" value={username}
          onChange={(e) => setUsername(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); fetchSkills(); } }}
        />
        <button type="button" className="btn secondary small" onClick={fetchSkills} disabled={busy}>
          {busy ? "…" : "Fetch"}
        </button>
      </div>
      {status && <span className="hint">{status}</span>}
    </div>
  );
}
