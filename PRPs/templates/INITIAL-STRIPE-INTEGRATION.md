# FEATURE: Stripe Payment Integration for Agent Tokens

This current agentic application has no payment integration and I want to build that in with Stripe. Changes will need to be made for both the backend and frontend.

## Frontend (frontend/ is the folder)
We will need to implement:
- Page to view purchase options for agent tokens and purchase them
- Integration with a Stripe webhook for when the tokens are purchased (changes will be needed on the frontend but we have to handle the purchase and redirect in the frontend)
- Success and failure pages after purchase completion
- Update to the user profile component to display the tokens available (fetched from the Supabase user record)
- Token usage history page to show past purchases and token consumption (fetched directly from Supabase in the frontend)
- Token balance display in the main chat interface (fetched directly from Supabase in the frontend)
- Display helpful error message when a message is rejected from the backend because no more tokens for the user

## Backend (backend_agent_api/ is the main folder and SQL in sql/)
We will need to implement:
- The user table in Supabase (see sql/) will need to be updated to include a column for the tokens the user currently has
- A transactions table to track all token purchases and usage for audit purposes
- Stripe webhook endpoint to handle when tokens are purchased with proper signature verification and idempotency handling
- The main API endpoint for interacting with the agent needs to check the user token count in Supabase and either reject the interaction or deduct a token

### API Endpoints Required:
- CREATE: `POST /api/create-payment-intent` - Create Stripe payment intent
- CREATE: `POST /api/webhook/stripe` - Handle Stripe webhooks with signature verification
- UPDATE: `POST /api/pydantic-agent` - Modified to check/deduct tokens (check tokens right after authentication with Supabase is verified and rate limiting check)

## Database Schema Updates
- Update user table to include tokens column
- Create transactions table to track:
  - Token purchases (with Stripe payment intent ID)
  - Token consumption (with API call details)
  - Idempotency keys to prevent duplicate processing
- Create Supabase RLS policies for the transaction table so users can view their own transactions (look at existing table RLS setup for examples)

## DOCUMENTATION
- Use the Archon MCP server to search the Graphiti and Pydantic AI documentation
- Search the web (supplemental search) for anything you need with Pydantic AI and/or Graphiti

## EXAMPLES



## OTHER CONSIDERATIONS
- Output a markdown document in planning/stripe-setup.md after the complete implementation that specifies what new environment variables need to be set (and make sure you add those to .env.example) for Stripe (both the backend and the frontend) and what other steps need to be completed for the setup in Stripe, including things like making the webhook
- The purchase page should have three options - 100 tokens, 250 tokens, and 600 tokens ($5, $10, and $20). These will be the purchase options set up in Stripe too
- Update the necessary SQL scripts in sql/ with the new user table column and transactions table, and also create a migration script for those who already have the DB set up
- Tokens do not expire - they are permanent once purchased
- Implement proper Stripe signature verification for webhook security
- Include idempotency handling to prevent duplicate token grants if webhooks are retried
- Keep the implementation simple but effective - we're building for a dev environment initially

## Environment Variables Needed
### Backend
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Frontend
```
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
```