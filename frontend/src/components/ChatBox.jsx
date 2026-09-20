/**
 * ChatBox.jsx
 * ------------
 * Chat interface for asking questions about the processed video.
 * Renders message history, suggested question chips, and a text input;
 * delegates the actual "ask question" API call to the parent via
 * onAskQuestion.
 *
 * Small UX features:
 *   - Enter key submits (native <form> behavior -- no extra handler needed)
 *   - Copy button on each assistant answer
 *   - Clear chat button
 *   - Suggested question chips shown once a video is processed but no
 *     question has been asked yet
 *   - Auto-scrolls to the latest message
 *   - Answers list timestamped sources that jump to that moment on YouTube
 */

import { useState, useRef, useEffect } from "react";
import LoadingSpinner from "./LoadingSpinner";

const SUGGESTED_QUESTIONS = [
  "Summarize this video",
  "Key takeaways",
  "Explain like I'm 10",
  "Important concepts",
];

// 75 -> "1:15", 3725 -> "1:02:05"
function formatTimestamp(totalSeconds) {
  const s = Math.floor(totalSeconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(s % 60).padStart(2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
}

function ChatBox({ videoId, messages, onAskQuestion, onClearChat, isAsking, disabled }) {
  const [question, setQuestion] = useState("");
  const [copiedIndex, setCopiedIndex] = useState(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to the latest message whenever the conversation grows.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAsking]);

  const submitQuestion = (text) => {
    if (!text.trim() || disabled || isAsking) return;
    onAskQuestion(text.trim());
    setQuestion("");
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    submitQuestion(question);
  };

  const handleCopy = async (text, index) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1500);
    } catch {
      // Clipboard API can fail (e.g. insecure context) -- fail silently,
      // copying is a convenience feature, not critical functionality.
    }
  };

  const showSuggestions = !disabled && messages.length === 0;

  return (
    <div className="chat-box">
      <div className="panel-header">
        <span className="panel-eyebrow">Ask about this video</span>
        {messages.length > 0 && (
          <button
            type="button"
            className="panel-action-btn"
            onClick={onClearChat}
            disabled={isAsking}
          >
            Clear chat
          </button>
        )}
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <p className="chat-placeholder">
            {disabled
              ? "Once a video is processed, ask anything covered in it -- answers are grounded only in the transcript."
              : "Ask a question below, or try one of the suggestions."}
          </p>
        )}

        {showSuggestions && (
          <div className="suggested-questions">
            {SUGGESTED_QUESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="suggested-question-chip"
                onClick={() => submitQuestion(suggestion)}
                disabled={isAsking}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`chat-message-group chat-message-group--${msg.role}`}>
            <span className="chat-message-role">
              {msg.role === "user" ? "You" : "NoteTube AI"}
            </span>
            <div className={`chat-message chat-message--${msg.role}`}>
              <p className="chat-message-text">{msg.text}</p>
            </div>
            {msg.role === "assistant" && msg.sources?.length > 0 && (
              <div className="chat-sources">
                <span className="chat-sources-label">Sources</span>
                {[...msg.sources]
                  .sort((a, b) => a.start_time - b.start_time)
                  .map((source, i) => (
                    <a
                      key={i}
                      className="chat-source-link"
                      href={`https://youtu.be/${videoId}?t=${Math.floor(source.start_time)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={source.text}
                    >
                      {formatTimestamp(source.start_time)}
                    </a>
                  ))}
              </div>
            )}
            {msg.role === "assistant" && (
              <button
                type="button"
                className="chat-message-copy-btn"
                onClick={() => handleCopy(msg.text, idx)}
              >
                {copiedIndex === idx ? "Copied!" : "Copy answer"}
              </button>
            )}
          </div>
        ))}

        {isAsking && <LoadingSpinner label="Thinking..." />}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-row" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder={
            disabled
              ? "Process a video first..."
              : "Ask a question about the video..."
          }
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={disabled || isAsking}
          className="chat-input-field"
        />
        <button
          type="submit"
          className="chat-input-button"
          disabled={disabled || isAsking || !question.trim()}
        >
          Ask
        </button>
      </form>
    </div>
  );
}

export default ChatBox;
