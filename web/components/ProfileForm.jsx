"use client";

import Form from "./Form";
import GitHubImport from "./GitHubImport";
import Input from "./Input";
import SkillPicker from "./SkillPicker";

function validate(f) {
  const errors = {};
  if (f.years_code === "" || f.years_code < 0 || f.years_code > 60) errors.years_code = "0 – 60";
  if (f.years_pro === "" || f.years_pro < 0 || f.years_pro > 50) errors.years_pro = "0 – 50";
  if (f.years_pro > f.years_code) errors.years_pro = "Can't exceed years coding";
  if (f.hours_per_week === "" || f.hours_per_week < 0 || f.hours_per_week > 80) errors.hours_per_week = "0 – 80";
  if (f.goal_type === "salary" && !(f.goal_salary > 0)) errors.goal_salary = "Enter a target salary";
  if (f.skills.length === 0) errors.skills = "Add at least one skill";
  return errors;
}

/** The developer profile form. All state lives in the parent (page.js); this only renders + validates. */
export default function ProfileForm({ options, form, setForm, onSubmit, loading, error, errors, setErrors }) {
  const set = (name, value) => setForm((f) => ({ ...f, [name]: value }));

  function submit() {
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length === 0) onSubmit();
  }

  return (
    <Form
      title="Your developer profile"
      description="Tell us where you are today. The models compare you with 150k+ developers."
      onSubmit={submit}
      submitLabel="Predict my growth"
      loading={loading}
      error={error}
    >
      <p className="form-section">Experience</p>
      <div className="row-2">
        <Input label="Years coding" name="years_code" type="number" min={0} max={60} step={0.5}
          value={form.years_code} onChange={set} error={errors.years_code} hint="incl. learning" />
        <Input label="Years professional" name="years_pro" type="number" min={0} max={50} step={0.5}
          value={form.years_pro} onChange={set} error={errors.years_pro} hint="paid work" />
      </div>
      <Input label="Main role" name="role" type="select" options={options.roles} value={form.role} onChange={set} />
      <div className="row-2">
        <Input label="Education" name="ed_level" type="select" value={form.ed_level}
          onChange={(n, v) => set(n, Number(v))} options={options.education_levels} />
        <Input label="Country" name="country" type="select" options={options.countries} value={form.country} onChange={set} />
      </div>

      <p className="form-section">Skills</p>
      <SkillPicker allSkills={options.skills} value={form.skills} onChange={(v) => set("skills", v)} />
      {errors.skills && <span className="hint" style={{ color: "var(--critical)" }}>{errors.skills}</span>}
      <GitHubImport
        allSkills={options.skills}
        onSkills={(found) => set("skills", [...new Set([...form.skills, ...found])])}
      />

      <p className="form-section">Goal</p>
      <Input label="Study hours per week" name="hours_per_week" type="number" min={0} max={80}
        value={form.hours_per_week} onChange={set} error={errors.hours_per_week} />
      <div className="field">
        <label>Goal type</label>
        <div className="segmented" role="tablist">
          <button type="button" className={form.goal_type === "level" ? "active" : ""} onClick={() => set("goal_type", "level")}>Reach a level</button>
          <button type="button" className={form.goal_type === "salary" ? "active" : ""} onClick={() => set("goal_type", "salary")}>Reach a salary</button>
        </div>
      </div>
      {form.goal_type === "level" ? (
        <Input label="Target level" name="goal_level" type="select" options={options.levels.slice(1)}
          value={form.goal_level} onChange={set} />
      ) : (
        <Input label="Target salary (USD / year)" name="goal_salary" type="number" min={1000} step={1000}
          value={form.goal_salary} onChange={set} error={errors.goal_salary} />
      )}
    </Form>
  );
}
