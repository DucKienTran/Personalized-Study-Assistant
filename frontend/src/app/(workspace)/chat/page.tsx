"use client";

import React from "react";
import { useChat } from "@/hooks/useChat";
import { useConversations } from "@/hooks/useConversations";
import { ChatHistory } from "@/components/chat/chat-history";
import { ChatInput } from "@/components/chat/chat-input";
import { ConversationSidebar } from "@/components/chat/conversation-sidebar";
import { CitationSource } from "@/types/chat";
import { Trash2, BotMessageSquare } from "lucide-react";

export default function ChatPage() {
  const { conversations, isLoading: conversationsLoading, refresh, rename, remove } = useConversations();
  const {
    messages,
    isLoading,
    error,
    conversationId,
    sendMessage,
    clearMessages,
    loadConversation,
  } = useChat({ onConversationUpdated: refresh });

  const handleCitationClick = (source: CitationSource) => {
    console.log("Navigating to source:", source);
  };


  return (
    <div className="flex h-full">
      <ConversationSidebar
        conversations={conversations}
        isLoading={conversationsLoading}
        activeConversationId={conversationId}
        onSelect={(id) => id !== conversationId && loadConversation(id)}
        onNewChat={clearMessages}
        onRename={rename}
        onDelete={async (id: number) => {
          await remove(id);

          if (id === conversationId) {
            clearMessages();
          }
        }}
      />

      <div className="flex flex-col h-full flex-1 bg-[#F8FAF8] border-l border-gray-100">
        <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200 shrink-0">
          <div className="flex items-center gap-2 text-[#111827]">
            <BotMessageSquare size={20} className="text-[#69B989]" />
            <h1 className="text-base font-semibold">AI Learning Assistant</h1>
          </div>

          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-500 bg-white border border-gray-200 rounded-lg hover:text-red-600 hover:border-red-200 hover:bg-red-50 transition-all disabled:opacity-50"
              title="Clear conversation"
            >
              <Trash2 size={14} />
              <span>Clear Chat</span>
            </button>
          )}
        </header>

        {error && (
          <div className="bg-red-50 px-4 py-2 text-sm text-red-600 border-b border-red-100 text-center shrink-0 flex items-center justify-center gap-2">
            <span className="font-medium">Error:</span> {error}
          </div>
        )}

        <div className="flex-1 overflow-hidden flex flex-col">
          <ChatHistory messages={messages} isLoading={isLoading} onCitationClick={handleCitationClick} />
        </div>

        <div className="p-4 bg-white border-t border-gray-200 shrink-0">
          <ChatInput
            onSend={sendMessage}
            isLoading={isLoading}
            placeholder="Ask a question about your documents (e.g. Summarize Chapter 1...)"
          />
        </div>
      </div>
    </div>
  );
}