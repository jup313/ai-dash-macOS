import { useState, useEffect, useRef, useCallback } from "react";
import {
  fetchConversations,
  fetchMessages,
  fetchAgents,
  fetchLLMConfig,
  fetchModels,
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
} from "../types";

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

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load conversations, agents, config on mount
  useEffect(() => {
    fetchConversations().then(setConversations).catch(() => {});
    fetchAgents().then(setAgents).catch(() => {});
    fetchLLMConfig()
      .then((cfg) => {
        setLlmConfig(cfg);
        setSelectedModel(
          cfg.active_provider === "ollama" ? cfg.ollama_model : cfg.openai_model
        );
      })
      .catch(() => {});
  }, []);

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

  const handleSend = async () => {
    if (!input.trim() || sending || !activeConvId) return;

    const userMessage = input.trim();
    setInput("");
    setSending(true);
    setError(null);

    // Optimistically add user message to UI
    const optimisticMsg: ConversationMessage = {
      message_id: `temp-${Date.now()}`,
      role: "user",
      content: userMessage,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticMsg]);

    try {
      if (useStreaming) {
        // Streaming mode
        setStreamingText("");
        const controller = streamChatMessage(
          activeConvId,
          { content: userMessage, agent: selectedAgent, model: selectedModel || undefined },
          (chunk) => setStreamingText((prev) => prev + chunk),
          () => {
            // On done — reload messages from server to get full state
            setStreamingText("");
            setSending(false);
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
        // Non-streaming mode
        await sendChatMessage(activeConvId, {
          content: userMessage,
          agent: selectedAgent,
          model: selectedModel || undefined,
        });
        // Reload messages
        const updated = await fetchMessages(activeConvId);
        setMessages(updated);
        refreshConversations();
        setSending(false);
      }
    } catch (err) {
      setSending(false);
      setError(err instanceof Error ? err.message : "Send failed");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleStop = () => {
    abortRef.current?.abort();
    setStreamingText("");
    setSending(false);
  };

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
        <label className="flex items-center gap-2 mb-3 px-2 text-xs text-dash-muted cursor-pointer">
          <input
            type="checkbox"
            checked={useStreaming}
            onChange={(e) => setUseStreaming(e.target.checked)}
            className="rounded border-dash-border"
          />
          Stream responses
        </label>

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
            </div>
          </div>
        ) : (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-2 py-4 space-y-4">
              {messages.length === 0 && !streamingText && (
                <p className="text-center text-dash-muted text-sm py-8">
                  Start the conversation by typing a message below.
                </p>
              )}

              {messages.map((msg) => (
                <MessageBubble key={msg.message_id} message={msg} />
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
              <div className="flex gap-2">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
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

function MessageBubble({ message }: { message: ConversationMessage }) {
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
        className={`max-w-[75%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap ${
          isUser
            ? "bg-dash-accent/20 text-dash-text"
            : "bg-dash-surface border border-dash-border text-dash-text"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}
