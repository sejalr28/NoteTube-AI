/**
 * SummaryPanel.jsx
 * -----------------
 * Displays the AI-generated summary for the processed video, styled as
 * a premium card (soft gradient background, subtle shadow). Purely
 * presentational -- receives summary text and loading state as props.
 */

import LoadingSpinner from "./LoadingSpinner";

function SummaryPanel({ summary, isLoading }) {
  return (
    <div className="summary-panel">
      <div className="panel-header">
        <span className="panel-eyebrow">AI summary</span>
      </div>

      {isLoading && <LoadingSpinner label="Generating summary..." />}

      {!isLoading && summary && (
        <p className="summary-text">{summary}</p>
      )}

      {!isLoading && !summary && (
        <p className="summary-placeholder">
          Process a video to see its summary here.
        </p>
      )}
    </div>
  );
}

export default SummaryPanel;
