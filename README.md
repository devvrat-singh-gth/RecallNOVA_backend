# RecallNova Backend

RecallNova Backend is the FastAPI service powering the AI, authentication, guest workspace, document, retrieval, chat, learning, usage, and persistence layers of RecallNova.

It provides the REST API consumed by the RecallNova frontend and manages application state through MongoDB, with optional Redis-backed infrastructure.

---

## Overview

The backend handles the core RecallNova workflow:

```text
Authentication
      ↓
Document ingestion
      ↓
PDF processing
      ↓
Document retrieval
      ↓
AI generation
      ↓
Chat / Flashcards / Quizzes
      ↓
Persistence + Usage Tracking
```

The service is organized into modular routes, services, database collections, authentication dependencies, and configuration layers.

---

## Features

### Authentication

* Google authentication
* Email/password authentication
* Email account registration
* Password hashing with scrypt
* Email verification workflow
* Password reset workflow
* JWT access tokens
* Persistent refresh sessions
* Refresh-token rotation
* Session revocation
* Multiple user sessions
* Account disabling support
* Timezone-aware accounts

### Guest Workspace

* Guest identity generation
* Guest JWT authentication
* Browser-persistent guest identity support
* Guest-specific resource ownership
* Guest usage limits
* Guest rate limiting
* Guest document limits
* Guest chat-session limits
* Guest flashcard limits
* Guest quiz limits
* Guest data retention through MongoDB TTL indexes

Guest resources are identified through guest-prefixed IDs and persisted with:

```text
guest_data: true
```

Current guest data retention is configured for seven days through TTL indexes.

### Document Processing

* PDF upload
* PDF text extraction
* Page-aware document storage
* User-specific document ownership
* Guest-specific document ownership
* Duplicate document detection
* Document size validation
* Page-range retrieval

### AI Chat

* Retrieval-augmented document chat
* Context-aware prompting
* Document-scoped conversations
* Persistent chat sessions
* Chat titles
* Response caching
* Token guarding
* Rate limiting
* Daily/monthly usage enforcement

### Learning System

* Flashcard generation
* Flashcard persistence
* Quiz generation
* Quiz persistence
* Quiz progress tracking
* Configurable learning parameters
* Topic support
* Difficulty support
* Document-grounded generation

### Usage & Plans

* Daily usage tracking
* Monthly usage tracking
* Guest usage tracking
* Plan-based resource limits
* Usage warnings
* Resource guardrails

### Infrastructure

* MongoDB persistence
* MongoDB TTL cleanup
* Redis-ready rate limiting/cache infrastructure
* REST API
* Environment-based configuration
* Docker-compatible deployment architecture

---

## Tech Stack

### Backend

* Python
* FastAPI
* Uvicorn

### Database

* MongoDB
* PyMongo

### AI

* Groq
* Hugging Face embeddings

### Document Processing

* PyMuPDF
* PyPDF2

### Authentication & Security

* JWT
* Google OAuth / Google Identity
* Python `hashlib.scrypt`
* SHA-256 token hashing
* HttpOnly refresh cookies
* Refresh-token rotation

### Email

* Resend

### Infrastructure

* Redis
* Docker
* REST API architecture

---

## Architecture

```text
backend/
│
├── app/
│   ├── config/
│   │   └── plans.py
│   │
│   ├── db/
│   │   └── mongo.py
│   │
│   ├── dependencies/
│   │   └── auth.py
│   │
│   ├── routes/
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── document.py
│   │   ├── dashboard.py
│   │   ├── learning.py
│   │   └── storage.py
│   │
│   ├── schemas/
│   │   └── auth.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── guest_service.py
│   │   ├── jwt_service.py
│   │   ├── session_service.py
│   │   ├── password_service.py
│   │   ├── verification_service.py
│   │   ├── email_service.py
│   │   ├── usage_service.py
│   │   ├── plan_service.py
│   │   ├── learning_service.py
│   │   ├── rag_service.py
│   │   ├── llm_service.py
│   │   ├── cache_service.py
│   │   ├── redis_service.py
│   │   └── guard_service.py
│   │
│   ├── settings.py
│   └── main.py
│
├── requirements.txt
├── Dockerfile
└── .env
```

---

## Authentication Architecture

RecallNova uses its own backend authentication layer while Google acts as an external identity provider.

### Registered users

```text
Google / Email + Password
          ↓
       FastAPI
          ↓
    RecallNova user
          ↓
    Access Token
          +
    Refresh Session
```

### Guest users

```text
Continue as Guest
        ↓
Guest ID
        ↓
Guest JWT
        ↓
Guest API access
```

Guest identities are not stored as registered users in the `users` collection.

Guest ownership is represented through the guest ID used by persisted resources.

---

## Session Architecture

Registered users can have multiple persistent refresh sessions.

```text
User
 ├── Session A
 ├── Session B
 └── Session C
```

Refresh credentials are stored as SHA-256 hashes.

Refresh sessions support:

* Expiration
* Revocation
* Rotation
* Multiple sessions
* Session lookup

Registered access tokens and refresh sessions use separate lifetimes.

Guest sessions use a separate guest JWT lifetime configured through:

```env
GUEST_TOKEN_MINUTES
```

---

## Access Token

Registered access-token lifetime is configured through:

```env
ACCESS_TOKEN_MINUTES
```

Guest-token lifetime is configured independently through:

```env
GUEST_TOKEN_MINUTES
```

The access token contains issuer, audience, subject, session identity, token type, issue time, expiration, and timezone information.

---

## Guest Data Retention

Guest-owned resources are marked using:

```text
guest_data: true
```

MongoDB TTL indexes currently remove guest data after seven days.

TTL cleanup applies to:

```text
documents
chat_sessions
flashcards
quizzes
quiz_progress
```

The guest identifier itself may remain in the browser, but expired MongoDB data cannot be restored after TTL cleanup.

---

## Email Authentication

Native RecallNova accounts support:

```text
Sign up
   ↓
Email + password
   ↓
RecallNova account
   ↓
Authenticated session
```

Passwords are derived using scrypt and are never stored in plaintext.

The backend also supports:

* Email verification tokens
* Password reset tokens
* Token expiration
* Token hashing
* Session invalidation after password reset

---

## Plan & Usage Architecture

Plans are centralized in:

```text
app/config/plans.py
```

Current plans include:

```text
guest
free
pro
```

### Guest limits

```text
Messages
  Daily:       10
  Monthly:     100

Flashcard generations
  Daily:       2
  Monthly:     10

Quiz generations
  Daily:       2
  Monthly:     10

Documents
  Maximum:     2

Chat sessions
  Maximum:     5

Rate limit
  5 requests/minute
```

The backend remains the authoritative enforcement layer.

Usage counters currently track:

```text
messages
flashcard_generations
quiz_generations
```

Both daily and monthly usage are maintained.

---

## API Routes

### Authentication

```text
POST  /auth/google
POST  /auth/email/signup
POST  /auth/email/login
POST  /auth/email/verify
GET   /auth/email/verify
POST  /auth/email/forgot-password
POST  /auth/email/reset-password
POST  /auth/guest
POST  /auth/refresh
POST  /auth/logout
GET   /auth/me
PATCH /auth/timezone
```

### Chat

```text
POST   /chat/
GET    /chat/sessions
GET    /chat/{chat_id}
DELETE /chat/{chat_id}
```

### Documents

```text
POST   /documents/upload
GET    /documents/
DELETE /documents/{doc_id}
```

### Learning

```text
GET  /learning/flashcards
GET  /learning/flashcards/check

GET  /learning/quiz
GET  /learning/quiz/check

POST /learning/quiz/progress/save
GET  /learning/quiz/progress
```

### Dashboard / Usage

Dashboard and usage-related endpoints expose workspace statistics and plan usage information to the frontend.

---

## Environment Variables

Example local configuration:

```env
MONGO_URI=
GROQ_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX_NAME=
HF_API_KEY=
REDIS_URL=

JWT_SECRET=
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=360
GUEST_TOKEN_MINUTES=10080

JWT_ISSUER=recallnova-api
JWT_AUDIENCE=recallnova-web

GOOGLE_CLIENT_ID=
FRONTEND_URL=http://localhost:3000

COOKIE_SECURE=false
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=

REFRESH_SESSION_DAYS=30

EMAIL_TOKEN_MINUTES=30
EMAIL_VERIFY_PATH=/verify-email
PASSWORD_RESET_PATH=/reset-password

RESEND_API_KEY=
RESEND_FROM_EMAIL=
RESEND_FROM_NAME=RecallNova

PASSWORD_SCRYPT_N=16384
PASSWORD_SCRYPT_R=8
PASSWORD_SCRYPT_P=1
```

For production:

```env
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
FRONTEND_URL=https://your-frontend.vercel.app
```

Secrets must never be committed to Git.

---

## Local Installation

```bash
git clone <repository-url>
cd Chatbot_CstmPrmpt
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Run Development Server

```bash
uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

FastAPI documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Production Deployment

### Backend

Recommended platform:

**Render**

Configure all required environment variables in the deployment service.

### Database

Recommended:

**MongoDB Atlas**

### Cache / Rate Limiting

Optional:

**Redis / Upstash Redis**

---

## Security Considerations

* Passwords are never stored directly
* Passwords are derived using scrypt
* Refresh tokens are hashed before database storage
* Refresh credentials are stored in HttpOnly cookies
* Access tokens use issuer and audience validation
* Refresh tokens are rotated
* Expired sessions are rejected
* Revoked sessions cannot be reused
* Registered user documents are scoped by user ID
* Guest resources are scoped by guest ID
* Guest resource cleanup uses MongoDB TTL indexes
* Usage limits protect expensive AI operations
* Redis rate limiting reduces request abuse
* Input length is guarded before LLM processing

Production deployments should use HTTPS and secure cookie configuration.

---

## Data Model

### Users

Stores registered account identity and profile information.

Typical fields:

```text
_id
email
name
picture
auth_provider
password_hash
email_verified
plan
timezone
disabled
created_at
updated_at
last_login_at
```

### Auth Sessions

Stores persistent registered-user refresh-session metadata.

Typical fields:

```text
session_id
user_id
token_hash
created_at
last_used_at
expires_at
revoked
revoked_at
rotated_at
```

### Documents

Stores processed document data, ownership, page information, metadata, and guest-data state where applicable.

### Chat Sessions

Stores persistent conversation sessions and associated messages.

### Learning

Stores generated flashcards, quizzes, and quiz progress.

---

## AI Workflow

The current document-question answering flow is:

```text
PDF upload
    ↓
Text extraction
    ↓
Document storage
    ↓
Document retrieval
    ↓
Relevant context
    ↓
Prompt construction
    ↓
Groq LLM
    ↓
AI response
    ↓
Cache / Persistence
```

Learning generation follows the same document-grounded approach.

---

## Usage Control

Usage is tracked for:

```text
messages
flashcard_generations
quiz_generations
```

Limits are evaluated against:

```text
daily limits
monthly limits
```

Resource limits such as document and chat-session counts are evaluated separately.

---

## MongoDB Indexing

MongoDB indexes are configured for common ownership and retrieval patterns.

Important indexes include:

* User email uniqueness
* Google ID uniqueness
* User/document ownership
* User/chat ordering
* User/document learning lookups
* Daily usage uniqueness
* Monthly usage uniqueness
* Refresh-session uniqueness
* Refresh-session expiration
* Guest resource TTL cleanup

---

## Health & Observability

The application uses standard FastAPI/Uvicorn logging for:

* Startup
* Requests
* Errors
* Authentication failures
* Document-processing failures
* AI workflow errors

Production monitoring should be configured through the deployment platform and infrastructure services.

---

## Roadmap

* Streaming AI responses
* Advanced semantic/vector retrieval
* OCR support
* Background processing queues
* Multi-model routing
* AI memory/context layer
* Advanced learning analytics
* Personalized study planning
* Guest-to-account migration
* Subscription and billing infrastructure
* Team workspaces
* Advanced Doc Atlas data generation
* Advanced document relationship mapping

---

## Deployment Architecture

```text
Vercel Frontend
      ↓
FastAPI Backend
      ↓
MongoDB Atlas
      +
Redis (optional)
      +
Groq / Hugging Face
```

---

## License

MIT License
