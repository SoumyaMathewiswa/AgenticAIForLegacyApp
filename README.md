# Bedrock Agent Legacy Integration

A production-ready example demonstrating how to layer AI intelligence on top of legacy systems using Amazon Bedrock AgentCore, Strands SDK, and MCP (Model-Controller-Protocol).

## Architecture Overview

```
┌────────────────────────────────────┐
│        End User                    │
│  (Chat / API Client)               │
└────────────────┬────────────────────┘
                 │
                 ▼
┌────────────────────────────────────┐
│   AI Agent (Strands SDK)           │
│  - Reasoning (Claude)              │
│  - Tool Selection                  │
│  - Agentic Loop                    │
└────────────────┬────────────────────┘
                 │
                 ▼
┌────────────────────────────────────┐
│  Bedrock AgentCore Runtime         │
│  - Session Management              │
│  - Memory & Context                │
│  - Multi-user Support              │
└────────────────┬────────────────────┘
                 │
                 ▼
┌────────────────────────────────────┐
│   MCP Gateway (Bridge)             │
│  - Tool Conversion                 │
│  - Auth & Authorization            │
│  - OpenAPI Integration             │
└────────────────┬────────────────────┘
                 │
                 ▼
┌────────────────────────────────────┐
│   Legacy Application               │
│ (ECS / Java / Database)            │
│  - NO CODE CHANGES                 │
└────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- AWS Credentials (for Bedrock)

### Setup

```bash
# Clone the repository
git clone https://github.com/SoumyaMathewiswa/AgenticAIForLegacyApp.git
cd AgenticAIForLegacyApp

# Configure environment
cp .env.example .env
# Edit .env with your AWS credentials and settings

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

### Test the Integration

```bash
# 1. Check health
curl http://localhost:8000/health
curl http://localhost:8002/health
curl http://localhost:8001/health

# 2. Get available tools from MCP Gateway
curl -X GET http://localhost:8002/tools \
  -H "Authorization: Bearer test-token-12345"

# 3. Invoke the agent
curl -X POST http://localhost:8001/invocations \
  -H "Authorization: Bearer test-token-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user-alice",
    "message": "Show me all laptops"
  }'

# 4. Run integration tests
docker-compose exec agent-runtime pytest tests/test_integration.py -v

# 5. Run the demo
python demo.py
```

## Service Endpoints

### Legacy System (Port 8000)
- `GET /health` - Health check
- `GET /api/products` - List products
- `POST /api/products` - Create product
- `GET /api/users` - List users
- `POST /api/users` - Create user
- `POST /api/cart/add` - Add to cart
- `GET /api/cart/{user_id}` - Get cart

### Bedrock AgentCore Runtime (Port 8001)
- `POST /invocations` - Invoke agent with user message
- `GET /sessions/{session_id}` - Get session state
- `DELETE /sessions/{session_id}` - Clear session
- `GET /health` - Health check

### MCP Gateway (Port 8002)
- `GET /tools` - List available tools
- `POST /invoke-tool` - Execute tool
- `GET /health` - Health check

## Key Components

### 1. Strands SDK Agent (`agent/`)
- Implements agentic loop: Think → Act → Observe → Plan
- Processes user intent
- Selects appropriate tools
- Maintains conversation context

### 2. MCP Gateway (`gateway/`)
- Converts REST APIs to MCP tools
- Handles authentication (JWT Bearer tokens)
- Enables dynamic tool discovery
- Manages OpenAPI spec ingestion

### 3. Bedrock Runtime (`bedrock_runtime/`)
- Manages user sessions
- Persists memory in Redis
- Scales horizontally
- Provides session isolation

### 4. Legacy System (`legacy_system/`)
- Simulated e-commerce backend
- NO MODIFICATIONS - demonstrates zero-change integration
- PostgreSQL for persistence
- Standard REST API

## Example Agent Workflows

### Workflow 1: Product Browsing
```
User: "Show me laptops under $2000"
  ↓
Agent: Interprets intent → searches products
  ↓
Agent: Calls MCP tool: list_products(category="laptops", max_price=2000)
  ↓
MCP Gateway: Converts to API call: GET /api/products?category=laptops&max_price=2000
  ↓
Legacy System: Returns matching products
  ↓
Agent: Formats response for user
```

### Workflow 2: Multi-step Transaction
```
User: "Create an account and add a laptop to my cart"
  ↓
Agent: Plans 3 steps:
  1. Create user account
  2. Get laptop products
  3. Add to cart
  ↓
Agent: Executes steps sequentially with tool calls
  ↓
MCP Gateway: Routes each call to appropriate legacy API
  ↓
Agent: Maintains context across all steps
  ↓
User: Gets unified response with account details
```

## Authentication

The MCP Gateway and AgentCore Runtime use JWT Bearer tokens:

```bash
# Token format
Authorization: Bearer <JWT_TOKEN>

# Example test token
Bearer test-token-12345
```

For production:
1. Integrate with your identity provider (Auth0, AWS Cognito, etc.)
2. Validate JWT signatures
3. Enforce scope-based authorization

## Monitoring & Observability

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f agent-runtime
docker-compose logs -f mcp-gateway
docker-compose logs -f legacy-system
```

### Health Metrics
Each service exposes `/health` endpoint:
- Status: up/down
- Dependencies: database, cache, etc.
- Response time

## Database

### PostgreSQL (Port 5432)
```bash
# Connect to database
docker-compose exec postgres psql -U postgres -d bedrock_legacy

# View tables
\dt

# Example queries
SELECT * FROM products;
SELECT * FROM users;
SELECT * FROM shopping_carts;
```

### Redis (Port 6379)
```bash
# Connect to Redis
docker-compose exec redis redis-cli

# View sessions
KEYS session:*

# View session data
GET session:user-alice
```

## Running Tests

```bash
# Run all tests
docker-compose exec agent-runtime pytest tests/ -v

# Run specific test file
docker-compose exec agent-runtime pytest tests/test_integration.py -v

# Run with coverage
docker-compose exec agent-runtime pytest tests/ --cov=. --cov-report=html
```

## Demo Script

The `demo.py` script demonstrates real agent workflows:

```bash
python demo.py
```

This will run through several scenarios:
1. Product browsing with filters
2. User account creation
3. Multi-step cart operations

## Development

### Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start only database and cache
docker-compose up postgres redis -d

# Run services locally
python -m uvicorn legacy_system.app:app --port 8000
python -m uvicorn gateway.app:app --port 8002
python -m uvicorn bedrock_runtime.app:app --port 8001
```

### Adding New Tools

1. Add API endpoint to legacy system
2. Register tool in `gateway/app.py` TOOL_REGISTRY
3. Update agent prompts if needed
4. Add tests

### Environment Variables

See `.env.example` for all configuration options. Key variables:

- `AWS_REGION`: AWS region for Bedrock
- `BEDROCK_MODEL_ID`: Claude model to use
- `JWT_SECRET`: Authentication secret
- `DATABASE_URL`: PostgreSQL connection
- `REDIS_URL`: Redis connection

## Production Deployment

### AWS Deployment

1. **ECS Fargate**: Containerized deployment
2. **RDS PostgreSQL**: Managed database
3. **ElastiCache Redis**: Managed cache
4. **API Gateway**: Expose agent endpoints
5. **CloudWatch**: Monitoring and logging

### Security Considerations

- Use proper JWT validation
- Implement rate limiting
- Add input validation and sanitization
- Use VPC and security groups
- Enable encryption in transit and at rest

## Troubleshooting

### Common Issues

1. **Bedrock Access Denied**
   - Check AWS credentials
   - Verify IAM permissions for Bedrock
   - Ensure correct region

2. **Database Connection Failed**
   - Check PostgreSQL container is running
   - Verify connection string
   - Check network connectivity

3. **Tool Execution Errors**
   - Verify MCP Gateway is accessible
   - Check JWT token
   - Review legacy API responses

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
docker-compose up
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Development

### Add New Tools

1. **Create API endpoint in legacy system** (`legacy_system/api.py`)
2. **Add OpenAPI spec** in MCP Gateway
3. **Register with MCP Gateway** - automatic discovery
4. **Agent uses it immediately** - no deployment needed

### Run Tests

```bash
# Unit tests
docker-compose exec agent-runtime pytest tests/test_agent.py -v

# Integration tests
docker-compose exec agent-runtime pytest tests/test_integration.py -v

# All tests with coverage
docker-compose exec agent-runtime pytest --cov=app tests/ -v
```

## Production Deployment

### AWS ECS Deployment

1. **Build images**
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t bedrock-agent-runtime .
docker tag bedrock-agent-runtime:latest <account>.dkr.ecr.us-east-1.amazonaws.com/bedrock-agent-runtime:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/bedrock-agent-runtime:latest
```

2. **Deploy via CloudFormation** (see `infrastructure/` folder)

3. **Enable auto-scaling**
```yaml
DesiredCount: 3
MinimumHealthyPercent: 100
MaximumPercent: 200
TargetTrackingScalingPolicyConfiguration:
  TargetValue: 70.0
  PredefinedMetricSpecification:
    PredefinedMetricType: ECSServiceAverageCPUUtilization
```

## Troubleshooting

### Agent not responding
```bash
# Check AgentCore Runtime
curl http://localhost:8001/health

# Check MCP Gateway
curl http://localhost:8002/health

# Check Legacy System
curl http://localhost:8000/health

# View logs
docker-compose logs agent-runtime
```

### Tools not available
```bash
# List available tools
curl -X GET http://localhost:8002/tools \
  -H "Authorization: Bearer test-token-12345"

# Verify OpenAPI specs are registered
docker-compose exec mcp-gateway curl http://localhost:5000/openapi/specs
```

### Session issues
```bash
# Check Redis
docker-compose exec redis redis-cli
KEYS session:*
GET session:user-alice

# Clear sessions
FLUSHDB
```

## Project Structure

```
AgenticAIForLegacyApp/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── docker-compose.yml                 # Service orchestration
├── .env.example                       # Environment template
├── .gitignore                         # Git ignore rules
├── agent/                             # Strands SDK Agent
│   ├── __init__.py
│   ├── main.py                        # Agent entry point
│   ├── models.py                      # Data models
│   ├── prompts.py                     # Agent prompts
│   └── tools.py                       # Tool definitions
├── bedrock_runtime/                   # AgentCore Runtime
│   ├── __init__.py
│   ├── main.py                        # Runtime entry point
│   ├── session_manager.py             # Session handling
│   ├── memory.py                      # Memory management
│   ├── models.py                      # Runtime models
│   └── Dockerfile
├── gateway/                           # MCP Gateway
│   ├── __init__.py
│   ├── main.py                        # Gateway entry point
│   ├── openapi_converter.py           # OpenAPI → MCP
│   ├── auth.py                        # Authentication
│   ├── models.py                      # Gateway models
│   └── Dockerfile
├── legacy_system/                     # Legacy E-commerce System
│   ├── __init__.py
│   ├── main.py                        # API entry point
│   ├── api.py                         # REST endpoints
│   ├── db.py                          # Database models
│   ├── models.py                      # Business models
│   └── Dockerfile
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── test_agent.py                  # Agent tests
│   ├── test_gateway.py                # Gateway tests
│   ├── test_runtime.py                # Runtime tests
│   └── test_integration.py            # E2E tests
└── infrastructure/                    # Deployment configs
    ├── Dockerfile.agent
    ├── Dockerfile.gateway
    ├── Dockerfile.legacy
    └── docker-compose.yml
```

## Why This Approach Works

✅ **No Rewrite Required** - Legacy systems remain untouched

✅ **Scalable by Design** - AgentCore handles infrastructure

✅ **Secure Integration** - MCP enforces controlled access

✅ **Intelligent Automation** - Agents adapt instead of rigid workflows

✅ **Production Ready** - Enterprise-grade monitoring & reliability

## Next Steps

1. **Customize for your system** - Update OpenAPI specs
2. **Add real AWS Bedrock integration** - Use actual LLM
3. **Deploy to production** - Use ECS/Kubernetes
4. **Monitor & scale** - CloudWatch + auto-scaling
5. **Add more tools** - Extend MCP Gateway

## Support

For issues, questions, or contributions:
- Open GitHub Issues
- Submit Pull Requests
- Check existing documentation

## License

MIT License - see LICENSE file for details

---

**Last Updated:** 2026-05-04
