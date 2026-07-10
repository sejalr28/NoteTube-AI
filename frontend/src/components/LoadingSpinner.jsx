/**
 * LoadingSpinner.jsx
 * -------------------
 * Small reusable loading indicator, styled like a video buffering ring
 * to stay on-theme. Accepts an optional label so callers can describe
 * what's happening (e.g. "Fetching transcript...").
 */

function LoadingSpinner({ label = "Loading..." }) {
  return (
    <div className="spinner-wrap">
      <div className="spinner-ring" />
      <span className="spinner-label">{label}</span>
    </div>
  );
}

export default LoadingSpinner;
