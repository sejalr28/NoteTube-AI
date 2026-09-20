/**
 * FlashcardView.jsx
 * ------------------
 * One flashcard at a time. Click the card to flip between question and answer.
 */

import { useState } from "react";
import { formatTimestamp, youtubeLink } from "../utils/time";

function FlashcardView({ cards, videoId }) {
  const [index, setIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);

  const card = cards[index];

  const go = (step) => {
    setIndex((prev) => (prev + step + cards.length) % cards.length);
    setIsFlipped(false);
  };

  return (
    <div className="flashcards">
      <button className="flashcard" onClick={() => setIsFlipped((prev) => !prev)}>
        <span className="flashcard-side">{isFlipped ? "Answer" : "Question"}</span>
        <span className="flashcard-text">{isFlipped ? card.back : card.front}</span>
        <span className="flashcard-hint">Click to flip</span>
      </button>

      <div className="flashcard-nav">
        <button className="panel-action-btn" onClick={() => go(-1)}>
          ← Prev
        </button>
        <span className="flashcard-count">
          {index + 1} / {cards.length}
        </span>
        <button className="panel-action-btn" onClick={() => go(1)}>
          Next →
        </button>
      </div>

      <a
        className="flashcard-review"
        href={youtubeLink(videoId, card.start_time)}
        target="_blank"
        rel="noopener noreferrer"
      >
        Review at {formatTimestamp(card.start_time)}
      </a>
    </div>
  );
}

export default FlashcardView;
