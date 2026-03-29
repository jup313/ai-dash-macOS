/**
 * Custom hook for browser Text-to-Speech using the Web Speech API.
 * Provides voice selection, speed control, and auto-speak functionality.
 */
import { useState, useRef, useCallback, useEffect } from "react";

export interface VoiceOption {
  name: string;
  lang: string;
  localService: boolean;
  voiceURI: string;
}

interface UseSpeechSynthesisOptions {
  /** Called when speech finishes */
  onEnd?: () => void;
  /** Called when speech starts */
  onStart?: () => void;
}

interface UseSpeechSynthesisReturn {
  voices: VoiceOption[];
  selectedVoice: string;
  setSelectedVoice: (name: string) => void;
  rate: number;
  setRate: (rate: number) => void;
  isSpeaking: boolean;
  autoSpeak: boolean;
  setAutoSpeak: (v: boolean) => void;
  isSupported: boolean;
  /** Speak the given text */
  speak: (text: string) => void;
  /** Stop current speech */
  stopSpeaking: () => void;
}

export function useSpeechSynthesis(
  opts: UseSpeechSynthesisOptions = {}
): UseSpeechSynthesisReturn {
  const { onEnd, onStart } = opts;

  const [voices, setVoices] = useState<VoiceOption[]>([]);
  const [selectedVoice, setSelectedVoice] = useState("");
  const [rate, setRate] = useState(1.0);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(false);

  const synthRef = useRef<SpeechSynthesis | null>(null);
  const isSupported = typeof window !== "undefined" && "speechSynthesis" in window;

  // Load available voices
  useEffect(() => {
    if (!isSupported) return;

    const synth = window.speechSynthesis;
    synthRef.current = synth;

    const loadVoices = () => {
      const available = synth.getVoices();
      const mapped: VoiceOption[] = available.map((v) => ({
        name: v.name,
        lang: v.lang,
        localService: v.localService,
        voiceURI: v.voiceURI,
      }));

      // Sort: English first, then by name
      mapped.sort((a, b) => {
        const aEn = a.lang.startsWith("en") ? 0 : 1;
        const bEn = b.lang.startsWith("en") ? 0 : 1;
        if (aEn !== bEn) return aEn - bEn;
        return a.name.localeCompare(b.name);
      });

      setVoices(mapped);

      // Pick a good default voice
      if (!selectedVoice && mapped.length > 0) {
        const preferred = ["Samantha", "Alex", "Karen", "Daniel", "Ava", "Zoe"];
        const found = mapped.find((v) =>
          preferred.some((p) => v.name.includes(p))
        );
        setSelectedVoice(found?.name || mapped[0].name);
      }
    };

    loadVoices();
    synth.addEventListener("voiceschanged", loadVoices);
    return () => synth.removeEventListener("voiceschanged", loadVoices);
  }, [isSupported]); // eslint-disable-line react-hooks/exhaustive-deps

  const speak = useCallback(
    (text: string) => {
      if (!synthRef.current || !text.trim()) return;

      // Cancel any ongoing speech
      synthRef.current.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = rate;
      utterance.pitch = 1;

      // Find selected voice object
      const allVoices = synthRef.current.getVoices();
      const voice = allVoices.find((v) => v.name === selectedVoice);
      if (voice) utterance.voice = voice;

      utterance.onstart = () => {
        setIsSpeaking(true);
        onStart?.();
      };

      utterance.onend = () => {
        setIsSpeaking(false);
        onEnd?.();
      };

      utterance.onerror = () => {
        setIsSpeaking(false);
        onEnd?.();
      };

      synthRef.current.speak(utterance);
    },
    [selectedVoice, rate, onEnd, onStart]
  );

  const stopSpeaking = useCallback(() => {
    if (synthRef.current) {
      synthRef.current.cancel();
      setIsSpeaking(false);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (synthRef.current) {
        synthRef.current.cancel();
      }
    };
  }, []);

  return {
    voices,
    selectedVoice,
    setSelectedVoice,
    rate,
    setRate,
    isSpeaking,
    autoSpeak,
    setAutoSpeak,
    isSupported,
    speak,
    stopSpeaking,
  };
}
