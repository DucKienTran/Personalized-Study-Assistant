"use client";

import React from "react";
import { Bot } from "lucide-react";

export const TypingIndicator: React.FC = () => {
  return (
    <div className="flex items-start gap-3 my-5">
      <div className="w-8 h-8 rounded-lg bg-[#8FCFA9]/20 text-[#69B989] flex items-center justify-center shrink-0">
        <Bot size={18} />
      </div>
      <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm max-w-[720px] flex items-center gap-2">
        <span className="text-xs font-medium text-gray-500">AI is thinking</span>
        <div className="flex items-center gap-1 ml-1">
          <span className="w-1.5 h-1.5 bg-[#8FCFA9] rounded-full animate-pulse"></span>
          <span className="w-1.5 h-1.5 bg-[#8FCFA9] rounded-full animate-pulse [animation-delay:200ms]"></span>
          <span className="w-1.5 h-1.5 bg-[#8FCFA9] rounded-full animate-pulse [animation-delay:400ms]"></span>
        </div>
      </div>
    </div>
  );
};