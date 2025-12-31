import { useEffect, useRef, useState } from 'react';
import { Message } from '@/types/database.types';
import { MessageItem } from './MessageItem';
import { SuggestedQuestions } from './SuggestedQuestions';
import { useIsMobile } from '@/hooks/use-mobile';
import { LoadingDots } from '@/components/ui/loading-dots';
import { getRandomQuestions, getContextualFollowUps } from '@/lib/premadeQA';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  isGeneratingResponse?: boolean; // New prop to distinguish between loading states
  isLoadingMessages?: boolean; // New prop for when switching conversations
  onSendMessage?: (message: string) => void; // Optional callback to send a message
  suggestedQuestions?: string[]; // External suggestions
  showFollowUps?: boolean; // Show follow-up questions after each answer
}

export const MessageList = ({ 
  messages, 
  isLoading, 
  isGeneratingResponse = false, 
  isLoadingMessages = false, 
  onSendMessage,
  suggestedQuestions: externalSuggestions,
  showFollowUps = true
}: MessageListProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isMobile = useIsMobile();
  const [initialQuestions, setInitialQuestions] = useState<string[]>([]);
  const [followUpQuestions, setFollowUpQuestions] = useState<string[]>([]);

  // Permanent question that always appears
  const SCHEDULE_CALL_QUESTION = "Schedule a call with Giuseppe";

  // Generate initial random questions on mount
  useEffect(() => {
    const randomQuestions = getRandomQuestions(10);
    setInitialQuestions(randomQuestions.map(qa => qa.question));
  }, []);

  // Update follow-up questions based on conversation
  useEffect(() => {
    if (messages.length > 0 && showFollowUps) {
      const lastUserMessage = [...messages]
        .reverse()
        .find(m => m.message.type === 'human');
      
      if (lastUserMessage) {
        const conversationHistory = messages
          .filter(m => m.message.type === 'human')
          .map(m => m.message.content);
        
        const followUps = getContextualFollowUps(
          lastUserMessage.message.content,
          conversationHistory
        );
        setFollowUpQuestions(followUps);
      }
    }
  }, [messages, showFollowUps]);

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
  }, [messages, isGeneratingResponse, followUpQuestions]);

  // Determine which questions to show
  const questionsToShow = externalSuggestions || 
    (messages.length === 0 ? initialQuestions : []);

  // Initial empty state
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 h-full">
        <div className="max-w-2xl w-full text-center">
          <h3 className="text-2xl font-bold mb-2">Welcome to PeppeGPT</h3>
          <p className="text-muted-foreground mb-6">
            Ask me anything about Giuseppe's experience, skills, and projects!
          </p>
          
          <SuggestedQuestions
            questions={[...questionsToShow.slice(0, 5), SCHEDULE_CALL_QUESTION]}
            onQuestionClick={handleQuestionClick}
            isLoading={isLoading}
            title="Suggested questions:"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 overflow-y-auto">
      <div className="py-6 min-h-full mx-auto w-full max-w-4xl">
        {messages.map((message, index) => (
          <div key={message.id}>
            <div className="mb-6">
              <MessageItem 
                message={message}
                isLastMessage={index === messages.length - 1} 
              />
            </div>
            
            {/* Show follow-up questions after AI responses */}
            {showFollowUps &&
             message.message.type === 'ai' &&
             index === messages.length - 1 &&
             !isGeneratingResponse &&
             !isLoading && (
              <div className="mb-6 px-4">
                <SuggestedQuestions
                  questions={[...followUpQuestions.slice(0, 2), SCHEDULE_CALL_QUESTION]}
                  onQuestionClick={handleQuestionClick}
                  isLoading={isLoading}
                  title="Continue the conversation:"
                  className="max-w-2xl"
                />
              </div>
            )}
          </div>
        ))}
        
        {/* Only show loading indicator when generating a response, not when switching conversations */}
        {isGeneratingResponse && (
          <div id="loading-indicator" className="max-w-4xl mx-auto px-4 flex items-start gap-4 animate-fade-in mb-6">
            <img
              src="/giuseppe-avatar.jpg"
              alt="Giuseppe"
              className="h-8 w-8 rounded-full object-cover"
            />
            <div className="flex items-center bg-chat-assistant py-3 px-4 rounded-lg max-w-[80%]">
              <LoadingDots className="text-current" />
            </div>
          </div>
        )}
        
        {/* Show loading indicator when switching conversations */}
        {isLoadingMessages && (
          <div id="loading-indicator" className="max-w-4xl mx-auto px-4 flex items-start gap-4 animate-fade-in mb-6">
            <img
              src="/giuseppe-avatar.jpg"
              alt="Giuseppe"
              className="h-8 w-8 rounded-full object-cover"
            />
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
