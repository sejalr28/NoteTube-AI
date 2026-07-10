/**
 * VideoSuccessCard.jsx
 * ----------------------
 * Shown after a video has been successfully processed: thumbnail, title,
 * chunk count, processing time, and an "Indexed successfully" status
 * badge. Purely presentational -- all data comes from the
 * /api/video/process response via props.
 */

function VideoSuccessCard({ title, thumbnailUrl, numChunks, processingTimeSeconds }) {
  return (
    <div className="video-success-card">
      <img
        className="video-success-thumbnail"
        src={thumbnailUrl}
        alt={title}
        loading="lazy"
      />
      <div className="video-success-info">
        <p className="video-success-title">{title}</p>
        <div className="video-success-meta">
          <span className="status-badge">Indexed successfully</span>
          <span className="meta-chip">{numChunks} chunks</span>
          <span className="meta-chip">{processingTimeSeconds}s</span>
        </div>
      </div>
    </div>
  );
}

export default VideoSuccessCard;
