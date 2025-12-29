import { useEffect, useRef } from 'react';
import { Message } from '@/types/database.types';
import { MessageItem } from './MessageItem';
import { useIsMobile } from '@/hooks/use-mobile';
import { LoadingDots } from '@/components/ui/loading-dots';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  isGeneratingResponse?: boolean; // New prop to distinguish between loading states
  isLoadingMessages?: boolean; // New prop for when switching conversations
  onSendMessage?: (message: string) => void; // Optional callback to send a message
}

export const MessageList = ({ messages, isLoading, isGeneratingResponse = false, isLoadingMessages = false, onSendMessage }: MessageListProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isMobile = useIsMobile();

  const suggestedQuestions = [
    "What is Giuseppe's professional experience with AI agents and RAG systems?",
    "Tell me about Giuseppe's data science and machine learning projects",
    "What certifications does Giuseppe have in ML, cloud, and MLOps?"
  ];

  const handleQuestionClick = (question: string) => {
    if (onSendMessage && !isLoading) {
      onSendMessage(question);
    }
  };

  // Scroll to bottom when messages change or when loading indicator appears/disappears
  useEffect(() => {
    // Use a small timeout to ensure DOM updates are complete before scrolling
    const scrollTimeout = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 50);
    
    return () => clearTimeout(scrollTimeout);
  }, [messages, isGeneratingResponse]);

  // Initial empty state
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 h-full">
        <div className="max-w-md text-center">
          <h3 className="text-xl font-bold mb-2">Welcome to PeppeGPT</h3>
          <p className="text-muted-foreground mb-4">
            Start a conversation by typing a message below.
          </p>
          <div className="grid gap-2 text-sm">
            <p className="font-medium">Try asking:</p>
            {suggestedQuestions.map((question, index) => (
              <button
                key={index}
                onClick={() => handleQuestionClick(question)}
                className="bg-secondary/50 p-3 rounded-md hover:bg-secondary transition-colors text-left cursor-pointer"
              >
                "{question}"
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 overflow-y-auto">
      <div className="py-6 min-h-full mx-auto w-full max-w-4xl">
        {messages.map((message, index) => (
          <div key={message.id} className="mb-6">
            <MessageItem 
              message={message}
              isLastMessage={index === messages.length - 1} 
            />
          </div>
        ))}
        
        {/* Only show loading indicator when generating a response, not when switching conversations */}
        {isGeneratingResponse && (
          <div id="loading-indicator" className="max-w-4xl mx-auto px-4 flex items-start gap-4 animate-fade-in mb-6">
            <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
              AI
            </div>
            <div className="flex items-center bg-chat-assistant py-3 px-4 rounded-lg max-w-[80%]">
              <LoadingDots className="text-current" />
            </div>
          </div>
        )}
        
        {/* Show loading indicator when switching conversations */}
        {isLoadingMessages && (
          <div id="loading-indicator" className="max-w-4xl mx-auto px-4 flex items-start gap-4 animate-fade-in mb-6">
            <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
              AI
            </div>
            <div className="flex items-center bg-chat-assistant py-3 px-4 rounded-lg max-w-[80%]">
              <LoadingDots className="text-current" />
            </div>
          </div>
        )}
        
        {/* This invisible element ensures we can scroll to the very bottom */}
        <div ref={messagesEndRef} className="h-10" />
      </div>
    </div>
  );
};
