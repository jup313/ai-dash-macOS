/**
 * Custom hook for browser Speech-to-Text using the Web Speech API.
 * Supports push-to-talk and continuous (auto) listening modes.
 */
import { useState, useRef, useCallback, useEffect } from "react";

export type MicMode = "off" | "listening" | "auto" | "paused";

interface UseSpeechRecognitionOptions {
  /** Language for recognition */
  lang?: string;
  /** Silence timeout in ms before auto-sending (auto mode) */
  silenceTimeout?: number;
  /** Called with final transcript when user stops speaking */
  onResult?: (transcript: string) => void;
  /** Called with interim (partial) transcript while speaking */
  onInterim?: (transcript: string) => void;
  /** Called when auto-mode detects end of speech */
  onAutoSend?: (transcript: string) => void;
}

interface UseSpeechRecognitionReturn {
  mode: MicMode;
  transcript: string;
  interimTranscript: string;
  isSupported: boolean;
  /** Single press: start/stop listening. */
  toggleListening: () => void;
  /** Toggle auto (hands-free) mode */
  toggleAuto: () => void;
  /** Pause listening (e.g., while agent speaks) */
  pause: () => void;
  /** Resume listening (after agent finishes speaking) */
  resume: () => void;
  /** Stop everything */
  stop: () => void;
}

const SpeechRecognition =
  typeof window !== "undefined"
    ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    : null;

export function useSpeechRecognition(
  opts: UseSpeechRecognitionOptions = {}
): UseSpeechRecognitionReturn {
  const {
    lang = "en-US",
    silenceTimeout = 1500,
    onResult,
    onInterim,
    onAutoSend,
  } = opts;

  const [mode, setMode] = useState<MicMode>("off");
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");

  const recognitionRef = useRef<any>(null);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const autoModeRef = useRef(false);
  const accumulatedRef = useRef("");

  const isSupported = !!SpeechRecognition;

  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  const startRecognition = useCallback(() => {
    if (!SpeechRecognition) return;

    // Clean up old instance
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
    }

    const recognition = new SpeechRecognition();
    recognition.lang = lang;
    recognition.interimResults = true;
    recognition.continuous = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: any) => {
      let interim = "";
      let final = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          final += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      if (final) {
        accumulatedRef.current += (accumulatedRef.current ? " " : "") + final.trim();
        setTranscript(accumulatedRef.current);
        onResult?.(accumulatedRef.current);

        // Reset silence timer — auto-send when user stops speaking
        // Works in BOTH push-to-talk and auto modes
        clearSilenceTimer();
        silenceTimerRef.current = setTimeout(() => {
          const text = accumulatedRef.current.trim();
          if (text) {
            onAutoSend?.(text);
            accumulatedRef.current = "";
            setTranscript("");
            setInterimTranscript("");

            // In push-to-talk mode, stop listening after auto-send
            if (!autoModeRef.current) {
              if (recognitionRef.current) {
                try { recognitionRef.current.stop(); } catch {}
                recognitionRef.current = null;
              }
              setMode("off");
            }
          }
        }, silenceTimeout);
      }

      if (interim) {
        setInterimTranscript(interim);
        onInterim?.(interim);
      } else {
        setInterimTranscript("");
      }
    };

    recognition.onerror = (event: any) => {
      console.warn("Speech recognition error:", event.error);
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        setMode("off");
        autoModeRef.current = false;
      }
      // For "no-speech" in auto mode, just restart
      if (event.error === "no-speech" && autoModeRef.current) {
        setTimeout(() => {
          if (autoModeRef.current) startRecognition();
        }, 300);
      }
    };

    recognition.onend = () => {
      // Auto-restart in auto/listening mode (browser stops after a while)
      if (autoModeRef.current) {
        setTimeout(() => {
          if (autoModeRef.current) startRecognition();
        }, 200);
      } else {
        // Push-to-talk ended — finalize
        const text = accumulatedRef.current.trim();
        if (text) {
          onResult?.(text);
        }
        setMode("off");
      }
    };

    recognitionRef.current = recognition;

    try {
      recognition.start();
    } catch (e) {
      console.warn("Failed to start recognition:", e);
    }
  }, [lang, silenceTimeout, onResult, onInterim, onAutoSend, clearSilenceTimer]);

  const stopRecognition = useCallback(() => {
    clearSilenceTimer();
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
      recognitionRef.current = null;
    }
  }, [clearSilenceTimer]);

  const toggleListening = useCallback(() => {
    if (mode === "listening") {
      // Stop listening, finalize
      autoModeRef.current = false;
      stopRecognition();
      setMode("off");
      const text = accumulatedRef.current.trim();
      if (text) onResult?.(text);
    } else if (mode === "auto") {
      // Turn off auto mode
      autoModeRef.current = false;
      stopRecognition();
      setMode("off");
      accumulatedRef.current = "";
      setTranscript("");
      setInterimTranscript("");
    } else {
      // Start push-to-talk
      autoModeRef.current = false;
      accumulatedRef.current = "";
      setTranscript("");
      setInterimTranscript("");
      setMode("listening");
      startRecognition();
    }
  }, [mode, startRecognition, stopRecognition, onResult]);

  const toggleAuto = useCallback(() => {
    if (mode === "auto") {
      autoModeRef.current = false;
      stopRecognition();
      setMode("off");
      accumulatedRef.current = "";
      setTranscript("");
      setInterimTranscript("");
    } else {
      autoModeRef.current = true;
      accumulatedRef.current = "";
      setTranscript("");
      setInterimTranscript("");
      setMode("auto");
      startRecognition();
    }
  }, [mode, startRecognition, stopRecognition]);

  const pause = useCallback(() => {
    if (mode === "auto" || mode === "listening") {
      stopRecognition();
      setMode("paused");
    }
  }, [mode, stopRecognition]);

  const resume = useCallback(() => {
    if (mode === "paused") {
      accumulatedRef.current = "";
      setTranscript("");
      setInterimTranscript("");
      if (autoModeRef.current) {
        setMode("auto");
      } else {
        setMode("listening");
      }
      startRecognition();
    }
  }, [mode, startRecognition]);

  const stop = useCallback(() => {
    autoModeRef.current = false;
    stopRecognition();
    setMode("off");
    accumulatedRef.current = "";
    setTranscript("");
    setInterimTranscript("");
  }, [stopRecognition]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      autoModeRef.current = false;
      clearSilenceTimer();
      if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch {}
      }
    };
  }, [clearSilenceTimer]);

  return {
    mode,
    transcript,
    interimTranscript,
    isSupported,
    toggleListening,
    toggleAuto,
    pause,
    resume,
    stop,
  };
}
