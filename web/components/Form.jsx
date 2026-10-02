"use client";

/**
 * Reusable form wrapper.
 * Handles: title/description, preventing page reload on submit, and a submit button with loading state.
 *
 * <Form title="..." onSubmit={fn} submitLabel="Analyze" loading={bool}> ...fields... </Form>
 */
export default function Form({ title, description, onSubmit, submitLabel = "Submit", loading = false, error, children }) {
  function handleSubmit(event) {
    event.preventDefault(); // stop the browser from reloading the page
    onSubmit?.();
  }

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      {title && <h2 className="form-title">{title}</h2>}
      {description && <p className="form-desc">{description}</p>}
      {children}
      {error && <div className="alert error" role="alert">{error}</div>}
      <button type="submit" className="btn" disabled={loading}>
        {loading && <span className="spinner" aria-hidden />}
        {loading ? "Predicting…" : submitLabel}
      </button>
    </form>
  );
}
