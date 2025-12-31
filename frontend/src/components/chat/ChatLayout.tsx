
import React, { useState } from 'react';
import { MessageList } from '@/components/chat/MessageList';
import { ChatInput } from '@/components/chat/ChatInput';
import { ChatSidebar } from '@/components/sidebar/ChatSidebar';
import { ProjectInfoPanel } from '@/components/chat/ProjectInfoPanel';
import { AlertCircle, Menu, LogIn } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Message, Conversation } from '@/types/database.types';
import { useIsMobile } from '@/hooks/use-mobile';
import { Sheet, SheetContent, SheetTrigger, SheetClose } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';

interface ChatLayoutProps {
  conversations?: Conversation[];
  messages: Message[];
  selectedConversation?: Conversation | null;
  loading: boolean;
  error: string | null;
  isSidebarCollapsed?: boolean;
  onSendMessage: (message: string) => void;
  onNewChat?: () => void;
  onSelectConversation?: (conversation: Conversation) => void;
  onToggleSidebar?: () => void;
  newConversationId?: string | null;
  isGuest?: boolean;
  onSignIn?: () => void;
}

export const ChatLayout: React.FC<ChatLayoutProps> = ({
  conversations = [],
  messages,
  selectedConversation,
  loading,
  error,
  isSidebarCollapsed = false,
  onSendMessage,
  onNewChat = () => {},
  onSelectConversation = () => {},
  onToggleSidebar = () => {},
  newConversationId,
  isGuest = false,
  onSignIn
}) => {
  const isMobile = useIsMobile();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [isGeneratingResponse, setIsGeneratingResponse] = useState(false);
  
  // Track when a response is being generated vs. just loading messages
  React.useEffect(() => {
    // Only set isGeneratingResponse to true when loading is true AND we have messages
    // This ensures we only show the loading indicator when generating a response, not when switching conversations
    if (loading && messages.length > 0) {
      // Check if the last message is from AI
      const lastMessage = messages[messages.length - 1];
      const isLastMessageAI = lastMessage.message.type === 'ai';
      
      // If the last message is from AI (whether empty/loading or streaming text),
      // we don't need the bottom loading indicator because the message itself 
      // provides the visual feedback (dots if empty, streaming text if not).
      if (isLastMessageAI) {
        setIsGeneratingResponse(false);
      } else {
        // If the last message is from the user, we show the loading dots 
        // to indicate the AI is "thinking" before the first token arrives.
        setIsGeneratingResponse(true);
      }
    } else {
      setIsGeneratingResponse(false);
    }
  }, [loading, messages]);
  
  // Wrapper for mobile conversation selection that also closes the sheet
  const handleSelectConversation = (conversation: Conversation) => {
    onSelectConversation(conversation);
    if (isMobile) {
      setSheetOpen(false);
    }
  };
  
  // Wrapper for new chat that also closes the sheet on mobile
  const handleNewChat = () => {
    onNewChat();
    if (isMobile) {
      setSheetOpen(false);
    }
  };

  // Custom onToggleSidebar for mobile that closes the sheet
  const handleToggleSidebar = () => {
    if (isMobile) {
      setSheetOpen(false);
    } else {
      onToggleSidebar();
    }
  };
  
  const renderSidebar = () => (
    <ChatSidebar
      conversations={conversations}
      isCollapsed={isMobile ? false : isSidebarCollapsed} // For desktop, use the collapse state
      onNewChat={handleNewChat}
      onSelectConversation={handleSelectConversation}
      selectedConversationId={selectedConversation?.session_id || null}
      onToggleSidebar={handleToggleSidebar}
      newConversationId={newConversationId}
    />
  );

  const renderChatContent = () => (
    <div className="flex-1 flex flex-col overflow-hidden w-full">
      <main className="flex-1 flex flex-col overflow-hidden">
        {error && (
          <Alert variant="destructive" className="m-4">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        
        <div className="flex-1 overflow-hidden relative">
          <MessageList 
            messages={messages} 
            isLoading={loading} 
            isGeneratingResponse={isGeneratingResponse}
            onSendMessage={onSendMessage}
          />
        </div>
        
        <div className="border-t">
          <div className="p-2 sm:p-4 max-w-4xl mx-auto w-full">
            <ChatInput 
              onSendMessage={onSendMessage} 
              isLoading={loading}
            />
            <div className="mt-2 text-xs text-center text-muted-foreground">
              {isGuest ? (
                <>
                  Guest mode - conversations are not saved. <button onClick={onSignIn} className="underline hover:text-foreground">Sign in</button> for full features.
                </>
              ) : (
                "AI responses are generated based on your input. The AI agent may produce inaccurate information."
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );

  // Guest Mode Layout
  if (isGuest) {
    return (
      <div className="flex h-screen bg-background flex-col overflow-hidden">
        {/* Guest Header */}
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
            <Button variant="outline" size="sm" onClick={onSignIn}>
              <LogIn className="h-4 w-4 mr-2" />
              Sign In
            </Button>
          </div>
        </div>
        {renderChatContent()}
      </div>
    );
  }

  // For mobile view (Authenticated)
  if (isMobile) {
    return (
      <div className="flex h-screen bg-background flex-col overflow-hidden">
        <div className="flex items-center justify-between h-14 border-b px-4">
          <div className="flex items-center">
            <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="mr-2">
                  <Menu className="h-5 w-5" />
                  <span className="sr-only">Open sidebar</span>
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="p-0 w-[280px]" showCloseButton={false}>
                {renderSidebar()}
              </SheetContent>
            </Sheet>
            <div className="font-semibold">
              {selectedConversation?.title || "New Chat"}
            </div>
          </div>
          <ProjectInfoPanel />
        </div>
        {renderChatContent()}
      </div>
    );
  }

  // For desktop view (Authenticated)
  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {renderSidebar()}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Desktop header with info button */}
        <div className="flex items-center justify-between h-12 border-b px-4">
          <div className="font-semibold text-sm text-muted-foreground">
            {selectedConversation?.title || "New Chat"}
          </div>
          <ProjectInfoPanel />
        </div>
        {renderChatContent()}
      </div>
    </div>
  );
};
