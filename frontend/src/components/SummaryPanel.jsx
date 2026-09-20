/**
 * SummaryPanel.jsx
 * -----------------
 * Displays the AI-generated summary for the processed video, styled as
 * a premium card (soft gradient background, subtle shadow). For long
 * videos it also lists timestamped chapters that link to that moment.
 * Purely presentational -- receives data and loading state as props.
 */

import LoadingSpinner from "./LoadingSpinner";
import { formatTimestamp, youtubeLink } from "../utils/time";

function SummaryPanel({ videoId, summary, chapters = [], isLoading }) {
  return (
    <div className="summary-panel">
      <div className="panel-header">
        <span className="panel-eyebrow">AI summary</span>
      </div>

      {isLoading && <LoadingSpinner label="Generating summary..." />}

      {!isLoading && summary && (
        <p className="summary-text">{summary}</p>
      )}

      {!isLoading && chapters.length > 0 && (
        <div className="chapters">
          <span className="chapters-label">Chapters</span>
          <ul className="chapter-list">
            {chapters.map((chapter) => (
              <li key={chapter.start_time} className="chapter-item">
                <a
                  className="chapter-time"
                  href={youtubeLink(videoId, chapter.start_time)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {formatTimestamp(chapter.start_time)}
                </a>
                <div>
                  <p className="chapter-title">{chapter.title}</p>
                  <p className="chapter-summary">{chapter.summary}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
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