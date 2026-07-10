/**
 * api.js
 * -------
 * Centralized wrapper for all backend HTTP calls.
 *
 * Why this file exists:
 * Keeping every axios call in one place means components never need to
 * know API URLs or request/response shapes directly -- they just call
 * a clearly-named function like `processVideo(url)`. This makes the
 * codebase easier to maintain and to explain in an interview.
 */

import axios from "axios";

const API_BASE_URL = "http://localhost:8000/api";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

/**
 * Sends a YouTube URL to the backend for full processing:
 * transcript fetch -> chunking -> embedding -> FAISS storage.
 */
export async function processVideo(youtubeUrl) {
  const response = await apiClient.post("/video/process", {
    youtube_url: youtubeUrl,
  });
  // { video_id, title, thumbnail_url, num_chunks, processing_time_seconds, message }
  return response.data;
}

/**
 * Asks a question about a previously-processed video (RAG Q&A).
 */
export async function askQuestion(videoId, question) {
  const response = await apiClient.post("/chat/ask", {
    video_id: videoId,
    question,
  });
  return response.data; // { answer, source_chunks }
}

/**
 * Requests an AI-generated summary of a previously-processed video.
 */
export async function summarizeVideo(videoId) {
  const response = await apiClient.post("/chat/summarize", {
    video_id: videoId,
  });
  return response.data; // { video_id, summary }
}
