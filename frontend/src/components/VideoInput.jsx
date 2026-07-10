/**
 * VideoInput.jsx
 * ---------------
 * Lets the user paste a YouTube URL and triggers backend processing.
 * Parent (App.jsx) owns the actual API call + state; this component
 * only handles the form UI and local input value.
 */

import { useState } from "react";
import ProcessingSteps from "./ProcessingSteps";

function VideoInput({ onProcessVideo, isProcessing, currentStepIndex }) {
  const [url, setUrl] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    onProcessVideo(url.trim());
  };

  return (
    <form className="video-input-form" onSubmit={handleSubmit}>
      <label className="video-input-label" htmlFor="youtube-url">
        YouTube video URL
      </label>
      <div className="video-input-row">
        <input
          id="youtube-url"
          type="text"
          placeholder="https://www.youtube.com/watch?v=..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={isProcessing}
          className="video-input-field"
        />
        <button
          type="submit"
          className="video-input-button"
          disabled={isProcessing || !url.trim()}
        >
          {isProcessing ? "Processing..." : "Process video"}
        </button>
      </div>

      {isProcessing && <ProcessingSteps currentStepIndex={currentStepIndex} />}
    </form>
  );
}

export default VideoInput;
