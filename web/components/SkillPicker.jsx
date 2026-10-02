"use client";

import { useMemo, useState } from "react";

/**
 * Multi-select for skills: selected skills are chips (click × to remove),
 * type to search, click a suggestion to add.
 */
export default function SkillPicker({ allSkills, value, onChange }) {
  const [query, setQuery] = useState("");

  const suggestions = useMemo(() => {
    const q = query.trim().toLowerCase();
    return allSkills
      .filter((s) => !value.includes(s))
      .filter((s) => !q || s.toLowerCase().includes(q))
      .slice(0, q ? 14 : 10);
  }, [allSkills, value, query]);

  const add = (skill) => { onChange([...value, skill]); setQuery(""); };
  const remove = (skill) => onChange(value.filter((s) => s !== skill));

  return (
    <div className="field">
      <label htmlFor="skill-search">Languages &amp; tools you know ({value.length})</label>
      {value.length > 0 && (
        <div className="chips">
          {value.map((s) => (
            <span className="chip" key={s}>
              {s}
              <button type="button" onClick={() => remove(s)} aria-label={`Remove ${s}`}>×</button>
            </span>
          ))}
        </div>
      )}
      <input
        id="skill-search"
        className="input"
        placeholder="Search skills… (e.g. Docker)"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") { e.preventDefault(); if (suggestions[0]) add(suggestions[0]); }
        }}
      />
      <div className="suggestions">
        {suggestions.map((s) => (
          <button type="button" className="suggestion" key={s} onClick={() => add(s)}>+ {s}</button>
        ))}
      </div>
    </div>
  );
}
