"use client";

/**
 * Reusable input field: label + control + hint/error, for type "text", "number" or "select".
 *
 * <Input label="Years coding" name="years_code" type="number" value={v} onChange={(name, value) => ...} />
 * <Input label="Role" name="role" type="select" options={[{ value, label }]} ... />
 *
 * onChange receives (name, value) so ONE handler can update any field of a form object.
 * Numbers are converted with Number() so the parent always gets a number for type="number".
 */
export default function Input({
  label, name, type = "text", value, onChange, options = [], hint, error,
  min, max, step, placeholder, required,
}) {
  const id = `field-${name}`;

  function handleChange(event) {
    const raw = event.target.value;
    onChange?.(name, type === "number" ? (raw === "" ? "" : Number(raw)) : raw);
  }

  return (
    <div className="field">
      {label && <label htmlFor={id}>{label}{required && " *"}</label>}
      {type === "select" ? (
        <select id={id} name={name} className={`input${error ? " invalid" : ""}`} value={value} onChange={handleChange}>
          {options.map((opt) => {
            const o = typeof opt === "object" ? opt : { value: opt, label: opt };
            return <option key={o.value} value={o.value}>{o.label}</option>;
          })}
        </select>
      ) : (
        <input
          id={id}
          name={name}
          type={type}
          className={`input${error ? " invalid" : ""}`}
          value={value}
          onChange={handleChange}
          min={min}
          max={max}
          step={step}
          placeholder={placeholder}
          aria-invalid={!!error}
        />
      )}
      {error ? <span className="error">{error}</span> : hint && <span className="hint">{hint}</span>}
    </div>
  );
}
