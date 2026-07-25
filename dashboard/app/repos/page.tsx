"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "@/lib/i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Repo {
  id: number;
  name: string;
  path: string;
  added_at: string;
}

export default function ReposPage() {
  const { t } = useTranslation();
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [path, setPath] = useState("");
  const [message, setMessage] = useState("");

  const loadRepos = async () => {
    try {
      const res = await fetch(`${API_URL}/repos`, { cache: "no-store" });
      const data = await res.json();
      setRepos(data.repos || []);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRepos();
  }, []);

  const addRepo = async () => {
    if (!name || !path) return;
    try {
      const res = await fetch(`${API_URL}/repos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, path }),
      });
      if (res.ok) {
        setMessage(t("repos_added"));
        setShowForm(false);
        setName("");
        setPath("");
        loadRepos();
      }
    } catch {
      setMessage("Error adding repository.");
    }
  };

  const removeRepo = async (id: number) => {
    try {
      const res = await fetch(`${API_URL}/repos/${id}`, { method: "DELETE" });
      if (res.ok) {
        setMessage(t("repos_removed"));
        loadRepos();
      }
    } catch {
      setMessage("Error removing repository.");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-cyan-500" />
      </div>
    );
  }

  return (
    <div className="space-y-8 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{t("repos_title")}</h1>
          <p className="text-gray-400 text-sm mt-1">{t("repos_subtitle")}</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
        >
          {t("repos_add")}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded-xl p-4 text-red-400">
          {t("error_api")}
        </div>
      )}

      {message && (
        <div className="bg-emerald-900/20 border border-emerald-800 rounded-xl p-4 text-emerald-400">
          {message}
        </div>
      )}

      {showForm && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <input
            type="text"
            placeholder={t("repos_name")}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
          />
          <input
            type="text"
            placeholder={t("repos_path")}
            value={path}
            onChange={(e) => setPath(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
          />
          <div className="flex gap-2">
            <button
              onClick={addRepo}
              className="bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
            >
              {t("repos_add")}
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

      {repos.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center text-gray-500">
          <p className="mb-2">{t("repos_no_data")}</p>
          <p className="text-xs text-gray-600">{t("repos_help")}</p>
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-800 border-b border-gray-700">
                <th className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider">{t("repos_col_name")}</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider">{t("repos_col_path")}</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider">{t("repos_col_added")}</th>
                <th className="text-right px-4 py-3 text-xs text-gray-400 uppercase tracking-wider">{t("repos_col_actions")}</th>
              </tr>
            </thead>
            <tbody>
              {repos.map((repo) => (
                <tr key={repo.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="px-4 py-3 text-sm text-white">{repo.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-400 font-mono">{repo.path}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{repo.added_at?.slice(0, 10)}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => removeRepo(repo.id)}
                      className="text-red-400 hover:text-red-300 text-xs transition-colors"
                    >
                      {t("repos_remove")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
