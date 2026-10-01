# Port Blueprints & Infrastructure

Version-controlled Port infrastructure definitions for the Agentic SDLC POC.

## Structure

```
blueprints/
├── service.json          # Service blueprint definition
├── entities/
│   ├── auth-service.json
│   ├── notification-service.json
│   └── payment-service.json
└── README.md (this file)
```

## Setup

### Prerequisites

Set your Port API token:
```bash
export PORT_API_TOKEN="your-jwt-token-from-port"
```

### 1. Create Service Blueprint

Import `service.json` into Port:

**Via Port API:**
```bash
curl -X POST https://api.us.getport.io/v1/blueprints \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @service.json
```

**Via Port UI:**
- Settings → Data Model → Create Blueprint
- Use `service.json` as reference

### 2. Create Service Entities

Once blueprint is created, create entities for each service:

```bash
# Create auth-service entity
curl -X POST https://api.us.getport.io/v1/blueprints/service/entities \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @entities/auth-service.json

# Create notification-service entity
curl -X POST https://api.us.getport.io/v1/blueprints/service/entities \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @entities/notification-service.json

# Create payment-service entity
curl -X POST https://api.us.getport.io/v1/blueprints/service/entities \
  -H "Authorization: Bearer $PORT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @entities/payment-service.json
```

Or manually in Port UI:
- New Entity → Service → Fill in details for each service

## Blueprints

### Service
Represents a microservice in the catalog.

**Properties:**
- `name` - Service identifier (e.g., "auth-service")
- `description` - What the service does
- `language` - Programming language
- `owner` - Team/person who owns it
- `repository_url` - GitHub repo
- `port` - Service port number
- `health_check_url` - Health endpoint
- `dependencies` - Services it depends on (array)
- `tech_stack` - Technologies used (array)

## Entities

### Auth Service
- Name: `auth-service`
- Language: Python
- Owner: `platform-team`
- Dependencies: None

### Notification Service
- Name: `notification-service`
- Language: Python
- Owner: `platform-team`
- Dependencies: None (called by others)

### Payment Service
- Name: `payment-service`
- Language: Python
- Owner: `platform-team`
- Dependencies: [`notification-service`]

## Next Steps

1. Create Service blueprint in Port
2. Create entities for the 3 existing services
3. Agents will query these when designing new services
4. User Profile Service (agent-created) will be added as 4th entity

## Keeping in Sync

When Port structure changes, export and commit back to version control:

```bash
# Export blueprint from Port
curl https://api.us.getport.io/v1/blueprints/service \
  -H "Authorization: Bearer $PORT_API_TOKEN" | jq '.blueprint' > service.json

# Export entities
curl https://api.us.getport.io/v1/blueprints/service/entities \
  -H "Authorization: Bearer $PORT_API_TOKEN" | jq '.entities[]' > entities/all.json
```

Then commit changes to track Port infrastructure history in Git:
```bash
git add blueprints/
git commit -m "Update Port blueprints and entities"
git push
```
