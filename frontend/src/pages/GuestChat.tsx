import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { MessageList } from '@/components/chat/MessageList';
import { ChatInput } from '@/components/chat/ChatInput';
import { ProjectInfoPanel } from '@/components/chat/ProjectInfoPanel';
import { LogIn, AlertCircle } from 'lucide-react';
import { Message } from '@/types/database.types';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useNavigate } from 'react-router-dom';
import { findQA, simulateStreaming } from '@/lib/premadeQA';

const AGENT_BASE_URL = import.meta.env.VITE_AGENT_ENDPOINT?.replace('/api/pydantic-agent', '') || 'http://localhost:8001';

export const GuestChat = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);  // True while waiting for first response
  const [error, setError] = useState<string | null>(null);
  const isMounted = useRef(true);

  useEffect(() => {
    return () => {
      isMounted.current = false;
    };
  }, []);

  const handleSignIn = () => {
    navigate('/login');
  };

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || loading) return;

    // Add user message immediately
    const userMessage: Message = {
      id: `guest-user-${Date.now()}`,
      session_id: 'guest-session',
      computed_session_user_id: 'guest',
      message: {
        type: 'human',
        content,
      },
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    setError(null);

    // Check if this is a pre-made question
    const premadeQA = findQA(content);
    
    if (premadeQA) {
      // Handle pre-made answer with simulated streaming
      const assistantMessageId = `guest-assistant-${Date.now()}`;
      const assistantMessage: Message = {
        id: assistantMessageId,
        session_id: 'guest-session',
        computed_session_user_id: 'guest',
        message: {
          type: 'ai',
          content: '',
        },
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMessage]);
      
      // Simulate streaming with 2-3 second initial delay
      const initialDelay = 2000 + Math.random() * 1000; // 2-3 seconds
      
      try {
        await simulateStreaming(
          premadeQA.answer,
          (chunk) => {
            if (!isMounted.current) return;
            
            setMessages((prev) => {
              const updatedMessages = [...prev];
              const aiMessageIndex = updatedMessages.findIndex(msg => msg.id === assistantMessageId);
              
              if (aiMessageIndex !== -1) {
                updatedMessages[aiMessageIndex] = {
                  ...updatedMessages[aiMessageIndex],
                  message: {
                    ...updatedMessages[aiMessageIndex].message,
                    content: chunk,
                  },
                };
              }
              
              return updatedMessages;
            });
          },
          initialDelay,
          30 // 30ms delay between words
        );
        
        if (isMounted.current) {
          setLoading(false);
          setIsStreaming(false);
        }
      } catch (err) {
        console.error('Error during simulated streaming:', err);
        if (isMounted.current) {
          setError('An error occurred while generating the response');
          setLoading(false);
          setIsStreaming(false);
        }
      }
      
      return; // Exit early for pre-made answers
    }

    // Create placeholder for assistant message (shows loading dots) for non-premade questions
    const assistantMessageId = `guest-assistant-${Date.now()}`;
    const assistantMessage: Message = {
      id: assistantMessageId,
      session_id: 'guest-session',
      computed_session_user_id: 'guest',
      message: {
        type: 'ai',
        content: '',  // Empty content will show loading dots
      },
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, assistantMessage]);

    try {
      // Build conversation history for short-term memory (exclude empty placeholder)
      const history = messages.map(msg => ({
        role: msg.message.type === 'human' ? 'user' : 'assistant',
        content: msg.message.content
      }));

      const response = await fetch(`${AGENT_BASE_URL}/api/public/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: content, history }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n').filter(line => line.trim());

        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            if (data.text) {
              fullText = data.text;
              if (isMounted.current) {
                // Update existing placeholder message with new content
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === assistantMessageId
                      ? { ...msg, message: { ...msg.message, content: fullText } }
                      : msg
                  )
                );
              }
            }
          } catch {
            // Ignore JSON parse errors for incomplete chunks
          }
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
      setError(errorMessage);
      // Remove the empty assistant message on error
      setMessages(prev => prev.filter(msg => msg.id !== assistantMessageId));
    } finally {
      if (isMounted.current) {
        setLoading(false);
        setIsStreaming(false);
      }
    }
  };

  return (
    <div className="flex h-screen bg-background flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between h-14 border-b px-4 bg-secondary/30">
        <div className="flex items-center gap-3">
          <img src="/giuseppe-avatar.jpg" alt="Giuseppe" className="h-8 w-8 rounded-full object-cover" />
          <span className="font-semibold">PeppeGPT</span>
          <span className="text-xs text-muted-foreground bg-secondary px-2 py-0.5 rounded">
            Guest Mode
          </span>
        </div>
        <div className="flex items-center gap-2">
          <ProjectInfoPanel />
          <Button variant="outline" size="sm" onClick={handleSignIn}>
            <LogIn className="h-4 w-4 mr-2" />
            Sign In
          </Button>
        </div>
      </div>

      {/* Chat content */}
      <div className="flex-1 flex flex-col overflow-hidden w-full">
        <main className="flex-1 flex flex-col overflow-hidden">
          {error && (
            <Alert variant="destructive" className="m-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="flex-1 overflow-hidden relative">
            <MessageList
              messages={messages}
              isLoading={loading}
              isGeneratingResponse={false}
              onSendMessage={handleSendMessage}
            />
          </div>

          <div className="border-t">
            <div className="p-4 max-w-4xl mx-auto w-full">
              <ChatInput
                onSendMessage={handleSendMessage}
                isLoading={loading}
              />
              <div className="mt-2 text-xs text-center text-muted-foreground">
                Guest mode - conversations are not saved. <button onClick={handleSignIn} className="underline hover:text-foreground">Sign in</button> for full features.
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default GuestChat;
