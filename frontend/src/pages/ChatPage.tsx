import { useState, useEffect, useRef, useCallback } from "react";
import {
  fetchConversations,
  fetchMessages,
  fetchAgents,
  fetchLLMConfig,
  fetchModels,
  fetchPersonalities,
  createConversation,
  deleteConversation,
  sendChatMessage,
  streamChatMessage,
} from "../api";
import type {
  AgentInfo,
  ConversationSummary,
  ConversationMessage,
  LLMConfig,
  ModelInfo,
  Personality,
} from "../types";
import { useSpeechRecognition, type MicMode } from "../hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "../hooks/useSpeechSynthesis";

export default function ChatPage() {
  // Sidebar state
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [llmConfig, setLlmConfig] = useState<LLMConfig | null>(null);

  // Chat state
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Settings
  const [selectedAgent, setSelectedAgent] = useState("chat");
  const [selectedModel, setSelectedModel] = useState("");
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [useStreaming, setUseStreaming] = useState(true);
  const [showVoiceSettings, setShowVoiceSettings] = useState(false);

  // Personality state
  const [personalities, setPersonalities] = useState<Personality[]>([]);
  const [selectedPersonality, setSelectedPersonality] = useState<string>("default");
  const [showPersonalities, setShowPersonalities] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const pendingAutoSendRef = useRef<string | null>(null);

  // ── Voice: Text-to-Speech ─────────────────────────────────────
  const tts = useSpeechSynthesis({
    onEnd: () => {
      // In auto mode, resume listening after agent finishes speaking
      if (stt.mode === "paused") {
        stt.resume();
      }
    },
    onStart: () => {
      // Pause mic while agent speaks to avoid feedback
      if (stt.mode === "auto" || stt.mode === "listening") {
        stt.pause();
      }
    },
  });

  // ── Voice: Speech-to-Text ─────────────────────────────────────
  const stt = useSpeechRecognition({
    lang: "en-US",
    silenceTimeout: 1500,
    onResult: (transcript) => {
      setInput(transcript);
    },
    onInterim: (interim) => {
      // Show interim text in input while speaking
    },
    onAutoSend: (transcript) => {
      // In auto mode, auto-send when silence detected
      pendingAutoSendRef.current = transcript;
    },
  });

  // Handle auto-send from voice
  useEffect(() => {
    if (pendingAutoSendRef.current && activeConvId && !sending) {
      const text = pendingAutoSendRef.current;
      pendingAutoSendRef.current = null;
      setInput(text);
      // Trigger send after a tick so input state is set
      setTimeout(() => handleSendText(text), 50);
    }
  }); // intentionally no deps — checks every render

  // Load conversations, agents, config, personalities on mount
  useEffect(() => {
    fetchConversations().then(setConversations).catch(() => {});
    fetchAgents().then(setAgents).catch(() => {});
    fetchPersonalities().then(setPersonalities).catch(() => {});
    fetchLLMConfig()
      .then((cfg) => {
        setLlmConfig(cfg);
        setSelectedModel(
          cfg.active_provider === "ollama" ? cfg.ollama_model : cfg.openai_model
        );
      })
      .catch(() => {});
  }, []);

  // Handle personality change — auto-set recommended TTS voice
  const handlePersonalityChange = useCallback((personalityId: string) => {
    setSelectedPersonality(personalityId);
    const p = personalities.find((x) => x.id === personalityId);
    if (p?.recommended_voice && tts.voices.length > 0) {
      const voiceExists = tts.voices.some((v) => v.name.includes(p.recommended_voice));
      if (voiceExists) {
        const match = tts.voices.find((v) => v.name.includes(p.recommended_voice));
        if (match) tts.setSelectedVoice(match.name);
      }
    }
  }, [personalities, tts.voices, tts.setSelectedVoice]);

  // Get current personality info
  const currentPersonality = personalities.find((p) => p.id === selectedPersonality);

  // Fetch available models when config loads
  useEffect(() => {
    if (!llmConfig) return;
    setLoadingModels(true);
    fetchModels(llmConfig.active_provider)
      .then((models) => setAvailableModels(models))
      .catch(() => setAvailableModels([]))
      .finally(() => setLoadingModels(false));
  }, [llmConfig]);

  // Load messages when active conversation changes
  useEffect(() => {
    if (!activeConvId) {
      setMessages([]);
      return;
    }
    fetchMessages(activeConvId)
      .then(setMessages)
      .catch(() => setError("Failed to load messages"));
  }, [activeConvId]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  const refreshConversations = useCallback(() => {
    fetchConversations().then(setConversations).catch(() => {});
  }, []);

  const handleNewChat = async () => {
    try {
      const conv = await createConversation("New Chat", selectedAgent);
      setActiveConvId(conv.conversation_id);
      setMessages([]);
      setError(null);
      refreshConversations();
      inputRef.current?.focus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create chat");
    }
  };

  const handleDeleteConversation = async (id: string) => {
    try {
      await deleteConversation(id);
      if (activeConvId === id) {
        setActiveConvId(null);
        setMessages([]);
      }
      refreshConversations();
    } catch { /* ignore */ }
  };

  const handleSendText = async (text: string) => {
    if (!text.trim() || sending || !activeConvId) return;

    const userMessage = text.trim();
    setInput("");
    setSending(true);
    setError(null);

    const optimisticMsg: ConversationMessage = {
      message_id: `temp-${Date.now()}`,
      role: "user",
      content: userMessage,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticMsg]);

    try {
      if (useStreaming) {
        setStreamingText("");
        let fullResponse = "";
        const controller = streamChatMessage(
          activeConvId,
          { content: userMessage, agent: selectedAgent, model: selectedModel || undefined, personality: selectedPersonality || undefined },
          (chunk) => {
            fullResponse += chunk;
            setStreamingText((prev) => prev + chunk);
          },
          () => {
            setStreamingText("");
            setSending(false);
            // Auto-speak agent response
            if (tts.autoSpeak && fullResponse.trim()) {
              tts.speak(fullResponse.trim());
            }
            fetchMessages(activeConvId).then(setMessages).catch(() => {});
            refreshConversations();
          },
          (err) => {
            setStreamingText("");
            setSending(false);
            setError(err.message);
          },
        );
        abortRef.current = controller;
      } else {
        await sendChatMessage(activeConvId, {
          content: userMessage,
          agent: selectedAgent,
          model: selectedModel || undefined,
          personality: selectedPersonality || undefined,
        });
        const updated = await fetchMessages(activeConvId);
        setMessages(updated);
        // Auto-speak the last assistant message
        if (tts.autoSpeak && updated.length > 0) {
          const last = updated[updated.length - 1];
          if (last.role === "assistant" && last.content) {
            tts.speak(last.content);
          }
        }
        refreshConversations();
        setSending(false);
      }
    } catch (err) {
      setSending(false);
      setError(err instanceof Error ? err.message : "Send failed");
    }
  };

  const handleSend = () => handleSendText(input);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    if (e.key === "Escape") {
      stt.stop();
      tts.stopSpeaking();
    }
  };

  const handleStop = () => {
    abortRef.current?.abort();
    setStreamingText("");
    setSending(false);
    tts.stopSpeaking();
  };

  // ── Mic button color/label logic ──────────────────────────────
  const micModeStyles: Record<MicMode, { ring: string; bg: string; label: string }> = {
    off: { ring: "", bg: "bg-dash-surface border border-dash-border", label: "🎙️" },
    listening: { ring: "ring-2 ring-red-500 animate-pulse", bg: "bg-red-500/20 border border-red-500", label: "🔴" },
    auto: { ring: "ring-2 ring-green-500 animate-pulse", bg: "bg-green-500/20 border border-green-500", label: "🔄" },
    paused: { ring: "ring-2 ring-blue-500", bg: "bg-blue-500/20 border border-blue-500", label: "⏸️" },
  };
  const micStyle = micModeStyles[stt.mode];

  return (
    <div className="flex h-[calc(100vh-2rem)] gap-4">
      {/* Conversation Sidebar */}
      <div className="w-64 flex-shrink-0 flex flex-col">
        <button
          onClick={handleNewChat}
          className="w-full mb-3 px-4 py-2.5 text-sm font-medium rounded-lg bg-dash-accent text-white hover:bg-dash-accent/80 transition-colors flex items-center justify-center gap-2"
        >
          <span className="text-lg">+</span> New Chat
        </button>

        {/* Agent selector */}
        <div className="mb-2">
          <label className="block text-[10px] text-dash-muted mb-1 px-1">Agent</label>
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className="w-full bg-dash-surface border border-dash-border rounded-lg px-3 py-2 text-xs text-dash-text focus:outline-none focus:border-dash-accent"
          >
            {agents.map((a) => (
              <option key={a.name} value={a.name}>
                {a.name.charAt(0).toUpperCase() + a.name.slice(1)} — {a.description.slice(0, 40)}
              </option>
            ))}
          </select>
        </div>

        {/* Model selector */}
        <div className="mb-3">
          <label className="block text-[10px] text-dash-muted mb-1 px-1">
            Model
            {loadingModels && <span className="ml-1 animate-pulse">detecting…</span>}
            {!loadingModels && availableModels.length > 0 && (
              <span className="ml-1 text-dash-success">({availableModels.length})</span>
            )}
          </label>
          {availableModels.length > 0 ? (
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full bg-dash-surface border border-dash-border rounded-lg px-3 py-2 text-xs text-dash-text focus:outline-none focus:border-dash-accent"
            >
              {availableModels.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name}
                </option>
              ))}
              {selectedModel && !availableModels.some((m) => m.name === selectedModel) && (
                <option value={selectedModel}>{selectedModel} (current)</option>
              )}
            </select>
          ) : (
            <input
              type="text"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              placeholder="e.g. llama3.1:latest"
              className="w-full bg-dash-surface border border-dash-border rounded-lg px-3 py-2 text-xs text-dash-text placeholder:text-dash-muted/50 focus:outline-none focus:border-dash-accent"
            />
          )}
        </div>

        {/* Streaming toggle */}
        <label className="flex items-center gap-2 mb-2 px-2 text-xs text-dash-muted cursor-pointer">
          <input
            type="checkbox"
            checked={useStreaming}
            onChange={(e) => setUseStreaming(e.target.checked)}
            className="rounded border-dash-border"
          />
          Stream responses
        </label>

        {/* Personality Selector */}
        {personalities.length > 0 && (
          <>
            <button
              onClick={() => setShowPersonalities(!showPersonalities)}
              className="flex items-center gap-2 mb-2 px-2 text-xs text-dash-muted hover:text-dash-text transition-colors"
            >
              <span>{showPersonalities ? "▼" : "▶"}</span>
              <span>🎭 Personality</span>
              {currentPersonality && (
                <span className="text-dash-text text-[10px]">
                  {currentPersonality.emoji} {currentPersonality.name}
                </span>
              )}
            </button>

            {showPersonalities && (
              <div className="mb-3 px-1">
                <div className="grid grid-cols-5 gap-1">
                  {personalities.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => handlePersonalityChange(p.id)}
                      title={`${p.name} — ${p.description}`}
                      className={`w-full aspect-square rounded-lg flex items-center justify-center text-lg transition-all hover:scale-110 ${
                        selectedPersonality === p.id
                          ? "bg-dash-accent/30 ring-2 ring-dash-accent shadow-lg"
                          : "bg-dash-surface border border-dash-border/50 hover:border-dash-accent/50"
                      }`}
                    >
                      {p.emoji}
                    </button>
                  ))}
                </div>
                {currentPersonality && (
                  <div className="mt-1.5 px-1">
                    <div className="text-[11px] text-dash-text font-medium">
                      {currentPersonality.emoji} {currentPersonality.name}
                    </div>
                    <div className="text-[10px] text-dash-muted">
                      {currentPersonality.description}
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* Voice Settings Toggle */}
        <button
          onClick={() => setShowVoiceSettings(!showVoiceSettings)}
          className="flex items-center gap-2 mb-2 px-2 text-xs text-dash-muted hover:text-dash-text transition-colors"
        >
          <span>{showVoiceSettings ? "▼" : "▶"}</span>
          <span>🔊 Voice Settings</span>
          {tts.autoSpeak && <span className="text-green-400 text-[10px]">ON</span>}
        </button>

        {showVoiceSettings && (
          <div className="mb-3 px-2 space-y-2 bg-dash-surface/50 rounded-lg p-2 border border-dash-border/50">
            {/* Auto-speak toggle */}
            <label className="flex items-center gap-2 text-xs text-dash-muted cursor-pointer">
              <input
                type="checkbox"
                checked={tts.autoSpeak}
                onChange={(e) => tts.setAutoSpeak(e.target.checked)}
                className="rounded border-dash-border"
              />
              Auto-speak responses
            </label>

            {/* Voice selector */}
            <div>
              <label className="block text-[10px] text-dash-muted mb-1">Voice</label>
              <select
                value={tts.selectedVoice}
                onChange={(e) => tts.setSelectedVoice(e.target.value)}
                className="w-full bg-dash-surface border border-dash-border rounded px-2 py-1 text-[11px] text-dash-text focus:outline-none focus:border-dash-accent"
              >
                {tts.voices.map((v) => (
                  <option key={v.voiceURI} value={v.name}>
                    {v.name} ({v.lang})
                  </option>
                ))}
              </select>
            </div>

            {/* Speech rate */}
            <div>
              <label className="block text-[10px] text-dash-muted mb-1">
                Speed: {tts.rate.toFixed(1)}x
              </label>
              <input
                type="range"
                min="0.5"
                max="2"
                step="0.1"
                value={tts.rate}
                onChange={(e) => tts.setRate(parseFloat(e.target.value))}
                className="w-full h-1 accent-dash-accent"
              />
            </div>

            {/* Test voice */}
            <button
              onClick={() => tts.speak("Hello! I'm your AI assistant. How can I help you today?")}
              className="w-full px-2 py-1 text-[10px] rounded bg-dash-accent/20 text-dash-accent hover:bg-dash-accent/30 transition-colors"
            >
              🔊 Test Voice
            </button>
          </div>
        )}

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto space-y-1">
          {conversations.length === 0 && (
            <p className="text-xs text-dash-muted px-2 py-4 text-center">
              No conversations yet
            </p>
          )}
          {conversations.map((conv) => (
            <div
              key={conv.conversation_id}
              className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors ${
                activeConvId === conv.conversation_id
                  ? "bg-dash-accent/20 text-dash-accent"
                  : "text-dash-text-dim hover:bg-dash-border/30 hover:text-dash-text"
              }`}
              onClick={() => setActiveConvId(conv.conversation_id)}
            >
              <span className="flex-1 truncate">{conv.title}</span>
              <span className="text-[10px] text-dash-muted">{conv.message_count}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteConversation(conv.conversation_id);
                }}
                className="opacity-0 group-hover:opacity-100 text-dash-error text-xs hover:text-dash-error/80 transition-opacity"
                title="Delete"
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        {/* Config info */}
        {llmConfig && (
          <div className="mt-2 pt-2 border-t border-dash-border text-[10px] text-dash-muted space-y-0.5 px-2">
            <div>Provider: <strong className="text-dash-text">{llmConfig.active_provider}</strong></div>
            <div>Model: <strong className="text-dash-text">{llmConfig.ollama_model || llmConfig.openai_model || "default"}</strong></div>
          </div>
        )}
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {!activeConvId ? (
          /* Welcome screen */
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-4">
              <h2 className="text-3xl font-bold text-dash-text">ai-dash Chat</h2>
              <p className="text-dash-muted max-w-md">
                Local ChatGPT replacement powered by your Ollama models.
                Click <strong>"New Chat"</strong> to start a conversation.
              </p>
              <div className="flex flex-wrap gap-2 justify-center pt-2">
                {agents.map((a) => (
                  <button
                    key={a.name}
                    onClick={() => {
                      setSelectedAgent(a.name);
                      handleNewChat();
                    }}
                    className="px-4 py-2 text-sm rounded-lg bg-dash-surface border border-dash-border text-dash-text hover:border-dash-accent transition-colors"
                  >
                    <span className="font-medium capitalize">{a.name}</span>
                    <span className="text-dash-muted ml-1 text-xs">— {a.description.slice(0, 50)}</span>
                  </button>
                ))}
              </div>
              {stt.isSupported && (
                <p className="text-dash-muted text-xs pt-2">
                  🎙️ Voice chat available — click the mic button to talk
                </p>
              )}
            </div>
          </div>
        ) : (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-2 py-4 space-y-4">
              {messages.length === 0 && !streamingText && (
                <p className="text-center text-dash-muted text-sm py-8">
                  Start the conversation by typing a message or clicking 🎙️ to talk.
                </p>
              )}

              {messages.map((msg) => (
                <MessageBubble
                  key={msg.message_id}
                  message={msg}
                  onSpeak={(text) => tts.speak(text)}
                  isSpeaking={tts.isSpeaking}
                  onStopSpeaking={tts.stopSpeaking}
                />
              ))}

              {/* Streaming indicator */}
              {streamingText && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-dash-accent/20 flex items-center justify-center text-xs text-dash-accent flex-shrink-0">
                    AI
                  </div>
                  <div className="flex-1 bg-dash-surface border border-dash-border rounded-xl px-4 py-3 text-sm text-dash-text whitespace-pre-wrap">
                    {streamingText}
                    <span className="inline-block w-1.5 h-4 bg-dash-accent ml-0.5 animate-pulse" />
                  </div>
                </div>
              )}

              {/* Sending indicator (non-streaming) */}
              {sending && !streamingText && !useStreaming && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-dash-accent/20 flex items-center justify-center text-xs text-dash-accent flex-shrink-0">
                    AI
                  </div>
                  <div className="bg-dash-surface border border-dash-border rounded-xl px-4 py-3 text-sm text-dash-muted animate-pulse">
                    Thinking…
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Voice status bar */}
            {stt.mode !== "off" && (
              <div className="mx-2 mb-1 px-3 py-1.5 rounded-lg bg-dash-surface border border-dash-border flex items-center gap-2 text-xs">
                <span className={`inline-block w-2 h-2 rounded-full ${
                  stt.mode === "listening" || stt.mode === "auto" ? "bg-red-500 animate-pulse" :
                  stt.mode === "paused" ? "bg-blue-500" : "bg-gray-500"
                }`} />
                <span className="text-dash-muted">
                  {stt.mode === "listening" && "Listening…"}
                  {stt.mode === "auto" && "🔄 Auto mode — speak naturally"}
                  {stt.mode === "paused" && "⏸️ Agent speaking…"}
                </span>
                {stt.interimTranscript && (
                  <span className="text-dash-text-dim italic truncate flex-1">
                    {stt.interimTranscript}
                  </span>
                )}
                {tts.isSpeaking && (
                  <button
                    onClick={tts.stopSpeaking}
                    className="text-dash-error hover:text-dash-error/80 text-[10px]"
                  >
                    Stop speaking
                  </button>
                )}
              </div>
            )}

            {/* Error banner */}
            {error && (
              <div className="mx-2 mb-2 px-4 py-2 bg-dash-error/10 border border-dash-error/30 rounded-lg text-sm text-dash-error flex items-center justify-between">
                <span>{error}</span>
                <button onClick={() => setError(null)} className="text-xs hover:underline ml-4">
                  dismiss
                </button>
              </div>
            )}

            {/* Input area */}
            <div className="border-t border-dash-border p-3">
              <div className="flex gap-2 items-end">
                {/* Mic button */}
                {stt.isSupported && (
                  <div className="flex flex-col gap-1">
                    <button
                      onClick={stt.toggleListening}
                      title={stt.mode === "off" ? "Click to talk (push-to-talk)" : "Stop listening"}
                      className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg transition-all ${micStyle.bg} ${micStyle.ring} hover:opacity-80`}
                    >
                      {micStyle.label}
                    </button>
                    {/* Auto mode toggle */}
                    <button
                      onClick={stt.toggleAuto}
                      title={stt.mode === "auto" ? "Stop auto mode" : "Start hands-free mode"}
                      className={`w-10 h-5 rounded text-[8px] font-bold transition-all ${
                        stt.mode === "auto"
                          ? "bg-green-500/30 text-green-400 border border-green-500"
                          : "bg-dash-surface border border-dash-border text-dash-muted hover:text-dash-text"
                      }`}
                    >
                      AUTO
                    </button>
                  </div>
                )}

                {/* Text input */}
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    stt.mode !== "off"
                      ? "Listening… (or type here)"
                      : "Type a message… (Enter to send, Shift+Enter for newline)"
                  }
                  disabled={sending}
                  rows={1}
                  className="flex-1 bg-dash-surface border border-dash-border rounded-xl px-4 py-3 text-sm text-dash-text placeholder:text-dash-muted/50 focus:outline-none focus:border-dash-accent resize-none transition-colors disabled:opacity-50"
                  style={{ minHeight: "44px", maxHeight: "120px" }}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement;
                    target.style.height = "auto";
                    target.style.height = Math.min(target.scrollHeight, 120) + "px";
                  }}
                />

                {/* Send / Stop button */}
                {sending ? (
                  <button
                    onClick={handleStop}
                    className="px-4 py-2 text-sm font-medium rounded-xl bg-dash-error text-white hover:bg-dash-error/80 transition-colors self-end"
                  >
                    Stop
                  </button>
                ) : (
                  <button
                    onClick={handleSend}
                    disabled={!input.trim()}
                    className="px-4 py-2 text-sm font-medium rounded-xl bg-dash-accent text-white hover:bg-dash-accent/80 disabled:opacity-30 disabled:cursor-not-allowed transition-colors self-end"
                  >
                    Send
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  onSpeak,
  isSpeaking,
  onStopSpeaking,
}: {
  message: ConversationMessage;
  onSpeak: (text: string) => void;
  isSpeaking: boolean;
  onStopSpeaking: () => void;
}) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${
          isUser
            ? "bg-dash-accent/30 text-dash-accent"
            : "bg-dash-accent/20 text-dash-accent"
        }`}
      >
        {isUser ? "You" : "AI"}
      </div>
      <div
        className={`max-w-[75%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap group relative ${
          isUser
            ? "bg-dash-accent/20 text-dash-text"
            : "bg-dash-surface border border-dash-border text-dash-text"
        }`}
      >
        {message.content}
        {/* Speak button for assistant messages */}
        {!isUser && message.content && (
          <button
            onClick={() => isSpeaking ? onStopSpeaking() : onSpeak(message.content)}
            className="absolute -bottom-1 -right-1 opacity-0 group-hover:opacity-100 w-6 h-6 rounded-full bg-dash-surface border border-dash-border flex items-center justify-center text-[10px] hover:bg-dash-accent/20 transition-all"
            title={isSpeaking ? "Stop speaking" : "Speak this message"}
          >
            {isSpeaking ? "⏹" : "🔊"}
          </button>
        )}
      </div>
    </div>
  );
}
