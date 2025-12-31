import { useState, useRef, useEffect } from 'react';
import { ChatLayout } from '@/components/chat/ChatLayout';
import { Message } from '@/types/database.types';
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
      let uiResources: Array<{uri: string; mimeType: string; text: string}> = [];

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
            // Capture UI resources from the final chunk
            if (data.ui_resources) {
              uiResources = data.ui_resources;
            }
          } catch {
            // Ignore JSON parse errors for incomplete chunks
          }
        }
      }

      // If we have UI resources, prepend the marker to the content for rendering
      if (uiResources.length > 0 && isMounted.current) {
        const resourceMarkers = uiResources
          .map(r => `__UI_RESOURCE__${JSON.stringify(r)}__END_UI_RESOURCE__`)
          .join('');
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantMessageId
              ? { ...msg, message: { ...msg.message, content: resourceMarkers + '\n\n' + fullText } }
              : msg
          )
        );
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
    <ChatLayout
      messages={messages}
      loading={loading}
      error={error}
      onSendMessage={handleSendMessage}
      isGuest={true}
      onSignIn={handleSignIn}
    />
  );
};

export default GuestChat;
