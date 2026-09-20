/**
 * QuizView.jsx
 * -------------
 * Multiple-choice quiz. Picking an option locks the question, marks the right
 * answer, and shows the explanation with a link to that moment in the video.
 */

import { useState } from "react";
import { formatTimestamp, youtubeLink } from "../utils/time";

function QuizView({ questions, videoId }) {
  const [picked, setPicked] = useState({}); // question index -> chosen option index

  const answered = Object.keys(picked).length;
  const score = questions.filter((q, i) => picked[i] === q.answer_index).length;

  return (
    <div className="quiz">
      {questions.map((q, i) => {
        const chosen = picked[i];
        const isDone = chosen !== undefined;

        return (
          <div key={i} className="quiz-question">
            <p className="quiz-prompt">
              {i + 1}. {q.question}
            </p>
            <div className="quiz-options">
              {q.options.map((option, j) => {
                let className = "quiz-option";
                if (isDone && j === q.answer_index) className += " quiz-option--correct";
                else if (isDone && j === chosen) className += " quiz-option--wrong";

                return (
                  <button
                    key={j}
                    className={className}
                    disabled={isDone}
                    onClick={() => setPicked((prev) => ({ ...prev, [i]: j }))}
                  >
                    {option}
                  </button>
                );
              })}
            </div>
            {isDone && (
              <p className="quiz-explanation">
                {q.explanation}{" "}
                <a
                  href={youtubeLink(videoId, q.start_time)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Review at {formatTimestamp(q.start_time)}
                </a>
              </p>
            )}
          </div>
        );
      })}

      {answered === questions.length && (
        <p className="quiz-score">
          Score: {score} / {questions.length}
        </p>
      )}
    </div>
  );
}

export default QuizView;