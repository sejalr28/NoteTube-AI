/**
 * StudyPanel.jsx
 * ---------------
 * Study tools for the processed video: a generated quiz, flashcards, and a
 * Markdown notes download that bundles the summary, chapters and anything
 * generated here. Give it key={videoId} so it resets for each new video.
 */

import { useState } from "react";
import LoadingSpinner from "./LoadingSpinner";
import QuizView from "./QuizView";
import FlashcardView from "./FlashcardView";
import { generateQuiz, generateFlashcards } from "../services/api";
import { buildNotesMarkdown, downloadTextFile, notesFilename } from "../utils/notes";

function StudyPanel({ videoId, title, summary, chapters }) {
  const [tab, setTab] = useState("quiz"); // "quiz" | "flashcards"
  const [quiz, setQuiz] = useState(null);
  const [cards, setCards] = useState(null);
  const [round, setRound] = useState(0); // bumps on each generate, so views reset their state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    setIsLoading(true);
    setError("");
    try {
      if (tab === "quiz") {
        setQuiz((await generateQuiz(videoId)).questions);
      } else {
        setCards((await generateFlashcards(videoId)).cards);
      }
      setRound((prev) => prev + 1);
    } catch (err) {
      setError(err?.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    const markdown = buildNotesMarkdown({ videoId, title, summary, chapters, cards, quiz });
    downloadTextFile(notesFilename(title), markdown);
  };

  const items = tab === "quiz" ? quiz : cards;

  return (
    <div className="study-panel">
      <div className="panel-header">
        <span className="panel-eyebrow">Study tools</span>
        <button className="panel-action-btn" onClick={handleDownload} disabled={!summary}>
          Download notes (.md)
        </button>
      </div>

      <div className="study-tabs">
        {[
          ["quiz", "Quiz"],
          ["flashcards", "Flashcards"],
        ].map(([id, label]) => (
          <button
            key={id}
            className={`study-tab${tab === id ? " study-tab--active" : ""}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <div className="alert-card alert-card--error">{error}</div>}

      {isLoading && (
        <LoadingSpinner label={tab === "quiz" ? "Writing quiz questions..." : "Making flashcards..."} />
      )}

      {!isLoading && items && tab === "quiz" && (
        <QuizView key={round} questions={items} videoId={videoId} />
      )}
      {!isLoading && items && tab === "flashcards" && (
        <FlashcardView key={round} cards={items} videoId={videoId} />
      )}

      {!isLoading && !items && (
        <p className="summary-placeholder">
          {tab === "quiz"
            ? "Generate a quiz to test yourself on this video."
            : "Generate flashcards to review the key ideas."}
        </p>
      )}

      {!isLoading && (
        <button className="study-generate" onClick={handleGenerate}>
          {items ? "Regenerate" : tab === "quiz" ? "Generate quiz" : "Generate flashcards"}
        </button>
      )}
    </div>
  );
}

export default StudyPanel;