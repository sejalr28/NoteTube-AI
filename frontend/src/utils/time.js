// 75 -> "1:15", 3725 -> "1:02:05"
export function formatTimestamp(totalSeconds) {
  const s = Math.floor(totalSeconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(s % 60).padStart(2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
}

// Link that opens the video at the given second.
export function youtubeLink(videoId, seconds) {
  return `https://youtu.be/${videoId}?t=${Math.floor(seconds)}`;
}