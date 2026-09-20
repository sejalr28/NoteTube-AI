/**
 * App.jsx
 * --------
 * Root component. Owns all shared state (video metadata, summary, chat
 * history) and coordinates calls to the backend via services/api.js.
 *
 * Keeping state here (instead of scattering it across children) is a
 * simple, beginner-friendly form of "lifting state up" -- a core React
 * pattern worth being able to explain in an interview.
 */

import { useState, useRef } from "react";
import VideoInput from "./components/VideoInput";
import VideoSuccessCard from "./components/VideoSuccessCard";
import SummaryPanel from "./components/SummaryPanel";
import ChatBox from "./components/ChatBox";
import { processVideo, askQuestion, summarizeVideo } from "./services/api";

// Index of the "Generating summary..." step in ProcessingSteps' step list.
// Kept in sync with components/ProcessingSteps.jsx's STEPS array.
const SUMMARY_STEP_INDEX = 3;

function App() {
  const [videoMeta, setVideoMeta] = useState(null); // { videoId, title, thumbnailUrl, numChunks, processingTimeSeconds }

  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [processError, setProcessError] = useState("");
  const stepIntervalRef = useRef(null);

  const [summary, setSummary] = useState("");
  const [isSummarizing, setIsSummarizing] = useState(false);

  const [messages, setMessages] = useState([]);
  const [isAsking, setIsAsking] = useState(false);

  /**
   * Full "process video" flow:
   *   1. Call backend to fetch transcript, chunk, embed, store in FAISS
   *   2. On success, immediately kick off summary generation
   *
   * The backend does step 1 as a single synchronous call, so we simulate
   * progress through its sub-stages on a timer purely for UX -- see
   * ProcessingSteps.jsx for details on why.
   */
  const handleProcessVideo = async (youtubeUrl) => {
    setIsProcessing(true);
    setProcessError("");
    setSummary("");
    setMessages([]);
    setVideoMeta(null);
    setCurrentStepIndex(0);

    // Cycle through the first 3 step labels while the request is in
    // flight. Capped at index 2 so it never races ahead of the real
    // "Generating summary..." step, which is triggered for real below.
    stepIntervalRef.current = setInterval(() => {
      setCurrentStepIndex((prev) => (prev < 2 ? prev + 1 : prev));
    }, 900);

    try {
      const result = await processVideo(youtubeUrl);
      clearInterval(stepIntervalRef.current);

      setVideoMeta({
        videoId: result.video_id,
        title: result.title,
        thumbnailUrl: result.thumbnail_url,
        numChunks: result.num_chunks,
        processingTimeSeconds: result.processing_time_seconds,
      });

      // Real step now -- the summarize call is actually in flight.
      setCurrentStepIndex(SUMMARY_STEP_INDEX);
      setIsSummarizing(true);
      const summaryResult = await summarizeVideo(result.video_id);
      setSummary(summaryResult.summary);
    } catch (err) {
      clearInterval(stepIntervalRef.current);
      const detail = err?.response?.data?.detail || "Something went wrong. Please try again.";
      setProcessError(detail);
    } finally {
      setIsProcessing(false);
      setIsSummarizing(false);
    }
  };

  /**
   * Handles a user question: appends it to chat history, calls the RAG
   * endpoint, then appends the AI's answer.
   */
  const handleAskQuestion = async (question) => {
    // Earlier turns (excluding failed ones) give the backend context for follow-ups.
    const history = messages.filter((m) => !m.isError);

    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setIsAsking(true);

    try {
      const result = await askQuestion(videoMeta.videoId, question, history);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: result.answer, sources: result.sources },
      ]);
    } catch (err) {
      const detail = err?.response?.data?.detail || "Failed to get an answer.";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `Error: ${detail}`, isError: true },
      ]);
    } finally {
      setIsAsking(false);
    }
  };

  const handleClearChat = () => setMessages([]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-mark">▶</div>
        <div>
          <h1 className="app-title">NoteTube AI</h1>
          <p className="app-subtitle">YouTube Learning Assistant</p>
        </div>
      </header>

      <main className="app-main">
        <section className="app-column">
          <VideoInput
            onProcessVideo={handleProcessVideo}
            isProcessing={isProcessing}
            currentStepIndex={currentStepIndex}
          />

          {processError && (
            <div className="alert-card alert-card--error">{processError}</div>
          )}

          {videoMeta && !processError && (
            <VideoSuccessCard
              title={videoMeta.title}
              thumbnailUrl={videoMeta.thumbnailUrl}
              numChunks={videoMeta.numChunks}
              processingTimeSeconds={videoMeta.processingTimeSeconds}
            />
          )}

          <SummaryPanel summary={summary} isLoading={isSummarizing} />
        </section>

        <section className="app-column">
          <ChatBox
            videoId={videoMeta?.videoId}
            messages={messages}
            onAskQuestion={handleAskQuestion}
            onClearChat={handleClearChat}
            isAsking={isAsking}
            disabled={!videoMeta}
          />
        </section>
      </main>

      <footer className="app-footer">
        <p className="app-footer-text">Powered by FAISS + Sentence Transformers + Groq</p>
      </footer>
    </div>
  );
}

export default App;
