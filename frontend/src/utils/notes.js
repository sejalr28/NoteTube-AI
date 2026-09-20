import { formatTimestamp, youtubeLink } from "./time";

/**
 * Builds a Markdown study-notes document from whatever has been generated so
 * far: summary, chapters, flashcards and quiz. Empty sections are left out.
 */
export function buildNotesMarkdown({ videoId, title, summary, chapters = [], cards, quiz }) {
  const at = (seconds) => `[${formatTimestamp(seconds)}](${youtubeLink(videoId, seconds)})`;
  const lines = [`# ${title || "Video notes"}`, "", `Source: https://youtu.be/${videoId}`, ""];

  if (summary) {
    lines.push("## Summary", "", summary, "");
  }

  if (chapters.length > 0) {
    lines.push("## Chapters", "");
    chapters.forEach((c) => lines.push(`- ${at(c.start_time)} **${c.title}**: ${c.summary}`));
    lines.push("");
  }

  if (cards?.length > 0) {
    lines.push("## Flashcards", "");
    cards.forEach((card) => {
      lines.push(`**Q:** ${card.front}`, "", `**A:** ${card.back} (${at(card.start_time)})`, "");
    });
  }

  if (quiz?.length > 0) {
    lines.push("## Quiz", "");
    quiz.forEach((q, i) => {
      lines.push(`${i + 1}. ${q.question}`);
      q.options.forEach((option, j) => lines.push(`   - ${String.fromCharCode(65 + j)}. ${option}`));
      lines.push(
        "",
        `   **Answer:** ${String.fromCharCode(65 + q.answer_index)}. ${q.explanation} (${at(q.start_time)})`,
        ""
      );
    });
  }

  return lines.join("\n");
}

export function notesFilename(title) {
  const slug = (title || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60);
  return `${slug || "video"}-notes.md`;
}

/** Saves text as a file download in the browser. */
export function downloadTextFile(filename, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/markdown;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}