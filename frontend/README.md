# PeppeGPT Frontend

A modern React application built with Vite, TypeScript, and Shadcn UI that provides a polished interface for interacting with the AI agent. This frontend transforms the powerful backend agent into an accessible, user-friendly application with real-time streaming responses, conversation management, and a beautiful UI.

## Features

- **Real-time Streaming**: Watch AI responses appear as they're generated
- **Conversation Management**: Create, switch between, and delete conversations
- **Modern UI**: Built with Shadcn UI components for a polished look
- **Code Syntax Highlighting**: Beautiful code rendering in responses
- **Markdown Support**: Full markdown rendering for formatted responses
- **Responsive Design**: Works seamlessly on desktop and mobile
- **Admin Dashboard**: Manage conversations and users (admin features)

## Tech Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite for lightning-fast development
- **UI Components**: Shadcn UI (built on Radix UI)
- **Styling**: Tailwind CSS
- **State Management**: React hooks and context
- **Database**: Supabase for real-time data and auth

## Prerequisites

- Node.js 18+ and npm (recommended)
- Supabase project (same one used by the backend)
- Backend agent API running (either Python or n8n)

## Setup Instructions

### NPM Setup (Recommended)

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env`:
   ```env
   # Supabase credentials (from your Supabase project)
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=your-anon-key
   
   # Agent API endpoint
   VITE_AGENT_ENDPOINT=http://localhost:8001/api/pydantic-agent
   
   # Enable streaming for Python agents (set to false for n8n)
   VITE_ENABLE_STREAMING=true
   
   # LangFuse integration (optional)
   VITE_LANGFUSE_HOST_WITH_PROJECT=http://localhost:3000/project/your-project-id
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

   The application will be available at `http://localhost:8081`

### Docker Setup (Alternative)

1. **Build with explicit values:**
   ```bash
   docker build -t frontend \
     --build-arg VITE_SUPABASE_URL=https://your-project.supabase.co \
     --build-arg VITE_SUPABASE_ANON_KEY=your-anon-key \
     --build-arg VITE_AGENT_ENDPOINT=http://localhost:8001/api/pydantic-agent \
     --build-arg VITE_ENABLE_STREAMING=true \
     .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name frontend \
     -p 8082:8080 \
     frontend
   ```

3. **Access the application** at http://localhost:8082

## Development

### Docker Development

When running with Docker, the frontend is served by nginx in production mode. For development with hot reload:

```bash
# Stop the Docker container
docker stop frontend

# Run in development mode locally
cd frontend
npm install
npm run dev
```

### Available Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

### Project Structure

```
frontend/
├── src/
│   ├── components/        # React components
│   │   ├── ui/           # Shadcn UI components
│   │   ├── admin/        # Admin dashboard components
│   │   ├── auth/         # Authentication components
│   │   ├── chat/         # Chat interface components
│   │   ├── sidebar/      # Sidebar navigation components
│   │   └── util/         # Utility components
│   ├── pages/            # Page components
│   ├── hooks/            # Custom React hooks
│   ├── lib/              # Utility functions and helpers
│   ├── types/            # TypeScript type definitions
│   ├── App.tsx           # Main application component
│   └── main.tsx          # Application entry point
├── public/               # Static assets
├── .env.example          # Example environment variables
├── vite.config.ts        # Vite configuration
├── tailwind.config.js    # Tailwind CSS configuration
└── package.json          # Dependencies and scripts
```

## Building for Production

### With Docker (Recommended)

Docker automatically builds the production version:

```bash
# Build with production optimizations
docker build -t frontend \
  --build-arg VITE_SUPABASE_URL=your_production_url \
  --build-arg VITE_SUPABASE_ANON_KEY=your_production_key \
  --build-arg VITE_AGENT_ENDPOINT=https://your-api.com/api/pydantic-agent \
  .

# Run the production container
docker run -d \
  --name frontend-prod \
  -p 80:8080 \
  frontend
```

The Docker image:
- Builds the React app with production optimizations
- Serves it with nginx for best performance
- Includes health checks and proper signal handling
- Runs as a non-root user for security

### Manual Build (Alternative)

1. **Build the application:**
   ```bash
   npm run build
   ```

   This creates an optimized production build in the `dist` directory.

2. **Test the production build locally:**
   ```bash
   npm run preview
   ```

3. **Deploy the `dist` directory** to your hosting service:
   - **Vercel**: Connect GitHub repo and deploy automatically
   - **Netlify**: Drag and drop the `dist` folder
   - **Render**: Deploy as a static site
   - **Cloud Storage**: Upload to S3, Google Cloud Storage, etc.

## Deployment Configuration

### Environment Variables for Production

When deploying, ensure you set the production environment variables:

```env
VITE_SUPABASE_URL=https://your-production-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-production-anon-key
VITE_AGENT_ENDPOINT=https://your-production-api.com/api/pydantic-agent
VITE_ENABLE_STREAMING=true

# Optional: LangFuse integration
VITE_LANGFUSE_HOST_WITH_PROJECT=https://your-langfuse-host.com/project/your-project-id
```

### Build Settings for Deployment Platforms

**Vercel/Netlify/Render:**
- Build Command: `npm run build`
- Output Directory: `dist`
- Node Version: 18.x or higher

## How It Works

1. **Authentication**: Uses Supabase Auth for user management
2. **Real-time Updates**: Leverages Supabase real-time subscriptions
3. **API Communication**: Sends requests to the agent backend
4. **Streaming Responses**: Uses Server-Sent Events (SSE) for real-time streaming
5. **State Management**: React hooks manage conversation state
6. **Data Persistence**: All conversations stored in Supabase

## Troubleshooting

### Common Issues

1. **"Cannot connect to agent"**
   - Verify the backend is running
   - Check `VITE_AGENT_ENDPOINT` is correct
   - Ensure no CORS issues (backend should allow frontend origin)

2. **"Invalid Supabase credentials"**
   - Double-check `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
   - Ensure you're using the anon key, not the service key

3. **Streaming not working**
   - Verify `VITE_ENABLE_STREAMING` matches your backend capability
   - Check browser console for SSE errors
   - Ensure backend supports streaming responses

4. **Build errors**
   - Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`
   - Check Node.js version (18+ required)
   - Run `npm run type-check` to find TypeScript issues