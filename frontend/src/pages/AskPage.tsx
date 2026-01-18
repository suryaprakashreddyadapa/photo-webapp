import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { searchApi } from '@/services/api';
import { AskResponse, Media } from '@/types';
import PhotoGrid from '@/components/media/PhotoGrid';
import {
  PaperAirplaneIcon,
  SparklesIcon,
  PhotoIcon,
  FolderPlusIcon,
  MagnifyingGlassIcon,
  BookmarkIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  media?: Media[];
  action?: string;
  timestamp: Date;
}

const EXAMPLE_QUERIES = [
  { icon: PhotoIcon, text: 'Show photos from last summer' },
  { icon: MagnifyingGlassIcon, text: 'Find photos with dogs' },
  { icon: FolderPlusIcon, text: 'Create album "Vacation 2024"' },
  { icon: BookmarkIcon, text: 'Save search as smart album' },
];

export default function AskPage() {
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState(initialQuery);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Ask mutation
  const askMutation = useMutation({
    mutationFn: async (query: string) => {
      const response = await searchApi.ask(query);
      return response.data as AskResponse;
    },
    onSuccess: (data, query) => {
      // Add assistant response
      const assistantMessage: Message = {
        id: Date.now().toString(),
        type: 'assistant',
        content: data.response,
        media: data.media || undefined,
        action: data.action || undefined,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    },
    onError: () => {
      const errorMessage: Message = {
        id: Date.now().toString(),
        type: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    },
  });
  
  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Handle initial query from URL
  useEffect(() => {
    if (initialQuery && messages.length === 0) {
      handleSubmit(new Event('submit') as any, initialQuery);
    }
  }, []);
  
  const handleSubmit = (e: React.FormEvent, overrideQuery?: string) => {
    e.preventDefault();
    const query = overrideQuery || input.trim();
    if (!query) return;
    
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: query,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    
    // Send to API
    askMutation.mutate(query);
  };
  
  const handleExampleClick = (text: string) => {
    setInput(text);
  };
  
  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <SparklesIcon className="w-7 h-7 text-primary-500" />
          Ask PhotoVault
        </h1>
        <p className="text-dark-500 dark:text-dark-400">
          Search your photos using natural language or give commands
        </p>
      </div>
      
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center">
            <SparklesIcon className="w-16 h-16 text-primary-200 dark:text-primary-800 mb-6" />
            <h2 className="text-xl font-semibold mb-2">How can I help you?</h2>
            <p className="text-dark-500 mb-8 text-center max-w-md">
              Ask me to find photos, create albums, or search using natural language.
            </p>
            
            {/* Example queries */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl">
              {EXAMPLE_QUERIES.map((example, index) => (
                <button
                  key={index}
                  onClick={() => handleExampleClick(example.text)}
                  className="card p-4 text-left hover:border-primary-300 dark:hover:border-primary-700 transition-colors flex items-center gap-3"
                >
                  <example.icon className="w-5 h-5 text-primary-500" />
                  <span>{example.text}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={clsx(
                'max-w-3xl',
                message.type === 'user' ? 'ml-auto' : ''
              )}
            >
              <div
                className={clsx(
                  'rounded-2xl px-4 py-3',
                  message.type === 'user'
                    ? 'bg-primary-500 text-white ml-auto'
                    : 'bg-dark-100 dark:bg-dark-800'
                )}
              >
                <p>{message.content}</p>
                
                {/* Action badge */}
                {message.action && (
                  <div className="mt-2 inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full text-sm">
                    <SparklesIcon className="w-4 h-4" />
                    {message.action}
                  </div>
                )}
              </div>
              
              {/* Media results */}
              {message.media && message.media.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm text-dark-500 mb-2">
                    Found {message.media.length} result(s)
                  </p>
                  <PhotoGrid media={message.media.slice(0, 12)} selectable={false} />
                  {message.media.length > 12 && (
                    <p className="text-sm text-dark-500 mt-2 text-center">
                      And {message.media.length - 12} more...
                    </p>
                  )}
                </div>
              )}
            </div>
          ))
        )}
        
        {/* Loading indicator */}
        {askMutation.isPending && (
          <div className="flex items-center gap-2 text-dark-500">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-500"></div>
            <span>Thinking...</span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input area */}
      <form onSubmit={handleSubmit} className="mt-4">
        <div className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about your photos..."
            className="input pr-12 py-4 text-lg"
            disabled={askMutation.isPending}
          />
          <button
            type="submit"
            disabled={!input.trim() || askMutation.isPending}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <PaperAirplaneIcon className="w-5 h-5" />
          </button>
        </div>
        <p className="text-xs text-dark-400 mt-2 text-center">
          Try: "Show me photos from Paris" • "Create album Summer 2024" • "Find photos with cats"
        </p>
      </form>
    </div>
  );
}
