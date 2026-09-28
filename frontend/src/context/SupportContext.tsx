import React, { createContext, useContext, useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import { api } from "../api/client";
import { useSystem } from "./SystemContext";
import type {
  IncidentInvestigationResponse,
  KbSolutionResponse,
} from "../types";

export interface SupportContextType {
  problemDescription: string;
  setProblemDescription: Dispatch<SetStateAction<string>>;
  uploadMode: "folder" | "files";
  setUploadMode: Dispatch<SetStateAction<"folder" | "files">>;
  selectedFiles: File[];
  setSelectedFiles: Dispatch<SetStateAction<File[]>>;
  folderName: string | null;
  setFolderName: Dispatch<SetStateAction<string | null>>;
  isInvestigating: boolean;
  setIsInvestigating: Dispatch<SetStateAction<boolean>>;
  investigationResult: IncidentInvestigationResponse | null;
  setInvestigationResult: Dispatch<
    SetStateAction<IncidentInvestigationResponse | null>
  >;
  investigationError: string | null;
  setInvestigationError: Dispatch<SetStateAction<string | null>>;
  isSearchingKb: boolean;
  setIsSearchingKb: Dispatch<SetStateAction<boolean>>;
  kbSolution: KbSolutionResponse | null;
  setKbSolution: Dispatch<SetStateAction<KbSolutionResponse | null>>;
  kbError: string | null;
  setKbError: Dispatch<SetStateAction<string | null>>;
  feedbackSubmitted: boolean;
  setFeedbackSubmitted: Dispatch<SetStateAction<boolean>>;
  isCorrectVote: boolean | null;
  setIsCorrectVote: Dispatch<SetStateAction<boolean | null>>;
  feedbackNotes: string;
  setFeedbackNotes: Dispatch<SetStateAction<string>>;
  isSubmittingFeedback: boolean;
  setIsSubmittingFeedback: Dispatch<SetStateAction<boolean>>;
  hasLogFiles: boolean;
  hasEmptyFilesOnly: boolean;
  handleInvestigate: (e?: React.FormEvent) => Promise<void>;
  handleSearchKb: () => Promise<void>;
  handleVote: (isCorrect: boolean) => Promise<void>;
  clearSupportState: () => void;
}

const SupportContext = createContext<SupportContextType | undefined>(undefined);

export function SupportProvider({ children }: { children: ReactNode }) {
  const [problemDescription, setProblemDescription] = useState("");
  const [uploadMode, setUploadMode] = useState<"folder" | "files">("folder");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [folderName, setFolderName] = useState<string | null>(null);

  // Investigation state
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [investigationResult, setInvestigationResult] =
    useState<IncidentInvestigationResponse | null>(null);
  const [investigationError, setInvestigationError] = useState<string | null>(
    null,
  );

  // KB Search state
  const [isSearchingKb, setIsSearchingKb] = useState(false);
  const [kbSolution, setKbSolution] = useState<KbSolutionResponse | null>(null);
  const [kbError, setKbError] = useState<string | null>(null);

  // Feedback state
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<boolean>(false);
  const [isCorrectVote, setIsCorrectVote] = useState<boolean | null>(null);
  const [feedbackNotes, setFeedbackNotes] = useState("");
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);

  const { addActivity } = useSystem();

  const hasLogFiles =
    selectedFiles.length > 0 && selectedFiles.some((f) => f.size > 0);
  const hasEmptyFilesOnly =
    selectedFiles.length > 0 && selectedFiles.every((f) => f.size === 0);

  const clearSupportState = () => {
    setSelectedFiles([]);
    setFolderName(null);
    setProblemDescription("");
    setInvestigationResult(null);
    setInvestigationError(null);
    setKbSolution(null);
    setKbError(null);
    setFeedbackSubmitted(false);
    setIsCorrectVote(null);
    setFeedbackNotes("");
  };

  const handleInvestigate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!hasLogFiles) {
      setInvestigationError(
        hasEmptyFilesOnly
          ? "Uploaded log file(s) are empty (0 bytes). Please upload at least one non-empty log file or select an instrument folder before investigating."
          : "No log file or folder uploaded. You must upload at least one log file or select an instrument folder before investigating.",
      );
      return;
    }
    if (!problemDescription.trim()) return;

    setInvestigationResult(null);
    setInvestigationError(null);
    setKbSolution(null);
    setKbError(null);
    setFeedbackSubmitted(false);
    setIsCorrectVote(null);
    setFeedbackNotes("");
    setIsInvestigating(true);

    addActivity({
      type: "QUERY_SUBMITTED",
      message: "User initiated reactive support log incident investigation",
      user: "Current User",
      severity: "INFO",
      metadata: {
        problem: problemDescription,
        files_count: selectedFiles.length,
        folder: folderName,
      },
    });

    try {
      const startTime = Date.now();
      const response = await api.investigateIncident(
        selectedFiles,
        problemDescription.trim(),
      );
      const durationMs = Date.now() - startTime;

      setInvestigationResult(response);

      addActivity({
        type: "SYSTEM_RESPONSE",
        message: response.found
          ? `Incident located in ${response.log_file} line ${response.line_number}`
          : "Incident investigation completed: issue not detected in logs",
        user: "System",
        severity: response.found ? "SUCCESS" : "WARNING",
        metadata: {
          duration_ms: durationMs,
          found: response.found,
          log_file: response.log_file,
          line_number: response.line_number,
        },
      });
    } catch (err: any) {
      console.error(err);
      setInvestigationError(
        err.message ||
          "Failed to investigate incident logs. Please check backend API connection.",
      );
      addActivity({
        type: "QUERY_ERROR",
        message: "Failed to investigate reactive support incident",
        user: "System",
        severity: "ERROR",
        metadata: { error: String(err) },
      });
    } finally {
      setIsInvestigating(false);
    }
  };

  const handleSearchKb = async () => {
    if (!investigationResult) return;

    setIsSearchingKb(true);
    setKbError(null);

    try {
      const query =
        investigationResult.suggested_search_query || problemDescription;
      const res = await api.searchKbSolution(
        query,
        investigationResult.log_file || undefined,
        investigationResult.line_number || undefined,
        investigationResult.pre_incident_pattern || undefined,
      );
      setKbSolution(res);

      addActivity({
        type: "SYSTEM_RESPONSE",
        message:
          "Retrieved Knowledge Base articles for reactive support incident",
        user: "System",
        severity: "INFO",
        metadata: { articles_count: res.related_articles?.length || 0 },
      });
    } catch (err: any) {
      console.error(err);
      setKbError("Failed to retrieve Knowledge Base articles for this issue.");
    } finally {
      setIsSearchingKb(false);
    }
  };

  const handleVote = async (isCorrect: boolean) => {
    setIsCorrectVote(isCorrect);
    setIsSubmittingFeedback(true);

    try {
      await api.submitSupportFeedback({
        problem_description: problemDescription,
        is_correct: isCorrect,
        log_file: investigationResult?.log_file || undefined,
        line_number: investigationResult?.line_number || undefined,
        detected_pattern:
          investigationResult?.pre_incident_pattern || undefined,
        feedback_notes: feedbackNotes.trim() || undefined,
      });

      setFeedbackSubmitted(true);
      addActivity({
        type: "FEEDBACK_SUBMITTED",
        message: `User confirmed AI response was ${isCorrect ? "CORRECT" : "WRONG"}`,
        user: "Current User",
        severity: isCorrect ? "SUCCESS" : "WARNING",
        metadata: {
          is_correct: isCorrect,
          log_file: investigationResult?.log_file,
        },
      });
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  return (
    <SupportContext.Provider
      value={{
        problemDescription,
        setProblemDescription,
        uploadMode,
        setUploadMode,
        selectedFiles,
        setSelectedFiles,
        folderName,
        setFolderName,
        isInvestigating,
        setIsInvestigating,
        investigationResult,
        setInvestigationResult,
        investigationError,
        setInvestigationError,
        isSearchingKb,
        setIsSearchingKb,
        kbSolution,
        setKbSolution,
        kbError,
        setKbError,
        feedbackSubmitted,
        setFeedbackSubmitted,
        isCorrectVote,
        setIsCorrectVote,
        feedbackNotes,
        setFeedbackNotes,
        isSubmittingFeedback,
        setIsSubmittingFeedback,
        hasLogFiles,
        hasEmptyFilesOnly,
        handleInvestigate,
        handleSearchKb,
        handleVote,
        clearSupportState,
      }}
    >
      {children}
    </SupportContext.Provider>
  );
}

export function useSupport() {
  const context = useContext(SupportContext);
  if (!context) {
    throw new Error("useSupport must be used within a SupportProvider");
  }
  return context;
}

