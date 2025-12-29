
export interface FileAttachment {
  fileName: string;
  content: string; // Base64 encoded content
  mimeType: string;
}

export interface Database {
  public: {
    Tables: {
      conversations: {
        Row: {
          id: string;
          user_id: string;
          session_id: string;
          title: string;
          created_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          session_id: string;
          title: string;
          created_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          session_id?: string;
          title?: string;
          created_at?: string;
        };
      };
      messages: {
        Row: {
          id: string;
          session_id: string;
          computed_session_user_id: string;
          message: {
            type: 'human' | 'ai';
            content: string;
            files?: FileAttachment[];
          };
          created_at: string;
        };
        Insert: {
          id?: string;
          session_id: string;
          computed_session_user_id: string;
          message: {
            type: 'human' | 'ai';
            content: string;
            files?: FileAttachment[];
          };
          created_at?: string;
        };
        Update: {
          id?: string;
          session_id?: string;
          computed_session_user_id?: string;
          message?: {
            type: 'human' | 'ai';
            content: string;
            files?: FileAttachment[];
          };
          created_at?: string;
        };
      };
      profiles: {
        Row: {
          id: string;
          email: string;
          avatar_url: string | null;
          full_name: string | null;
          updated_at: string | null;
        };
        Insert: {
          id: string;
          email: string;
          avatar_url?: string | null;
          full_name?: string | null;
          updated_at?: string | null;
        };
        Update: {
          id?: string;
          email?: string;
          avatar_url?: string | null;
          full_name?: string | null;
          updated_at?: string | null;
        };
      };
    };
  };
}

export type Conversation = Database['public']['Tables']['conversations']['Row'];
export type Message = Database['public']['Tables']['messages']['Row'];
export type Profile = Database['public']['Tables']['profiles']['Row'];
