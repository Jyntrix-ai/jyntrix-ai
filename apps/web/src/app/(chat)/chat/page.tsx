'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { ChatInterface } from '@/components/chat/chat-interface';
import { useChatStore } from '@/stores/chat.store';
import { api } from '@/lib/api';

export default function NewChatPage() {
  const router = useRouter();
  const { setCurrentConversationId, clearMessages } = useChatStore();
  const [isCreating, setIsCreating] = useState(false);

  // Clear current conversation on mount for new chat
  useEffect(() => {
    setCurrentConversationId(null);
    clearMessages();
  }, [setCurrentConversationId, clearMessages]);

  const handleFirstMessage = async (message: string): Promise<string> => {
    if (isCreating) {
      throw new Error('Already creating conversation');
    }

    setIsCreating(true);
    try {
      // Create a new conversation
      const conversation = await api.conversations.create({
        title: message.slice(0, 50) + (message.length > 50 ? '...' : ''),
      });

      // Set the conversation ID and navigate
      setCurrentConversationId(conversation.id);
      router.push(`/chat/${conversation.id}`);

      // The chat interface will handle sending the message after navigation
      return conversation.id;
    } catch (error) {
      console.error('Failed to create conversation:', error);
      setIsCreating(false);
      throw error;
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-border dark:border-border-dark">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">
            New Chat
          </h1>
        </div>
      </header>

      {/* Chat Interface */}
      <ChatInterface
        conversationId={null}
        onFirstMessage={handleFirstMessage}
        isNewChat={true}
      />
    </div>
  );
}
