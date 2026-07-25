"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "@/lib/i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface FeedbackEntry {
  id: number;
  timestamp: string;
  file_path: string;
  commit_hash: string;
  ai_probability: number;
  user_rating: string;
  user_note: string;
}

export default function FeedbackPage() {
  const { t } = useTranslation();
  const [feedback, setFeedback] = useState<FeedbackEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [filePath, setFilePath] = useState("");
  const [commitHash, setCommitHash] = useState("");
  const [aiProb, setAiProb] = useState("0.5");
  const [rating, setRating] = useState("correct");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");

  const loadFeedback = async () => {
    try {
      const res = await fetch(`${API_URL}/feedback`, { cache: "no-store" });
      const data = await res.json();
      setFeedback((data.feedback || []).reverse());
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFeedback();
  }, []);

  const submitFeedback = async () => {
    try {
      const res = await fetch(`${API_URL}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_path: filePath,
          commit_hash: commitHash,
          ai_probability: parseFloat(aiProb),
          rating,
          note,
        }),
      });
      if (res.ok) {
        setMessage(t("feedback_submitted"));
        setShowForm(false);
        setFilePath("");
        setCommitHash("");
        setAiProb("0.5");
        setRating("correct");
        setNote("");
        loadFeedback();
      }
    } catch {
      setMessage("Error submitting feedback.");
    }
  };

  return (
    <div className="space-y-8 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{t("feedback_title")}</h1>
          <p className="text-gray-400 text-sm mt-1">{t("feedback_subtitle")}</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
        >
          {t("feedback_submit")}
        </button>
      </div>

      {message && (
        <div className="bg-emerald-900/20 border border-emerald-800 rounded-xl p-4 text-emerald-400">
          {message}
        </div>
      )}

      {showForm && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <input
            type="text"
            placeholder="File path"
            value={filePath}
            onChange={(e) => setFilePath(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
          />
          <input
            type="text"
            placeholder="Commit hash"
            value={commitHash}
            onChange={(e) => setCommitHash(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
          />
          <input
            type="number"
            step="0.1"
            min="0"
            max="1"
            placeholder="AI probability (0-1)"
            value={aiProb}
            onChange={(e) => setAiProb(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
          />
          <div className="flex gap-2">
            {["correct", "incorrect", "unsure"].map((r) => (
              <button
                key={r}
                onClick={() => setRating(r)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  rating === r
                    ? r === "correct"
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500"
                      : r === "incorrect"
                      ? "bg-red-500/20 text-red-400 border border-red-500"
                      : "bg-yellow-500/20 text-yellow-400 border border-yellow-500"
                    : "bg-gray-800 text-gray-400 border border-gray-700 hover:border-gray-600"
                }`}
              >
                {r === "correct" ? t("feedback_rating_correct") : r === "incorrect" ? t("feedback_rating_incorrect") : t("feedback_rating_unsure")}
              </button>
            ))}
          </div>
          <textarea
            placeholder={t("feedback_note_placeholder")}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-cyan-500 h-20 resize-none"
          />
          <div className="flex gap-2">
            <button
              onClick={submitFeedback}
              className="bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
            >
              {t("feedback_submit")}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="text-gray-400 hover:text-white text-sm px-4 py-2 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-cyan-500" />
        </div>
      ) : feedback.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center text-gray-500">
          {t("feedback_no_data")}
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-800 border-b border-gray-700">
                <th className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider">{t("feedback_col_file")}</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider">{t("feedback_col_rating")}</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider">{t("feedback_col_note")}</th>
                <th className="text-right px-4 py-3 text-xs text-gray-400 uppercase tracking-wider">{t("feedback_col_date")}</th>
              </tr>
            </thead>
            <tbody>
              {feedback.map((entry) => (
                <tr key={entry.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="px-4 py-3 text-sm text-white font-mono">{entry.file_path || "—"}</td>
                  <td className="px-4 py-3 text-sm">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                        entry.user_rating === "correct"
                          ? "bg-emerald-500/20 text-emerald-400"
                          : entry.user_rating === "incorrect"
                          ? "bg-red-500/20 text-red-400"
                          : "bg-yellow-500/20 text-yellow-400"
                      }`}
                    >
                      {entry.user_rating}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-400 max-w-xs truncate">{entry.user_note || "—"}</td>
                  <td className="px-4 py-3 text-sm text-gray-500 text-right">{entry.timestamp?.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
