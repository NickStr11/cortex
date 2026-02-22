# Node/TypeScript MCP Server Implementation Guide

## Quick Reference

### Key Imports
```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import express from "express";
import { z } from "zod";
```

### Server Initialization
```typescript
const server = new McpServer({
  name: "service-mcp-server",
  version: "1.0.0"
});
```

### Tool Registration Pattern
```typescript
server.registerTool(
  "tool_name",
  {
    title: "Tool Display Name",
    description: "What the tool does",
    inputSchema: { param: z.string() },
    outputSchema: { result: z.string() }
  },
  async ({ param }) => {
    const output = { result: `Processed: ${param}` };
    return {
      content: [{ type: "text", text: JSON.stringify(output) }],
      structuredContent: output
    };
  }
);
```

## Server Naming Convention

- **Format**: `{service}-mcp-server` (lowercase with hyphens)
- **Examples**: `github-mcp-server`, `jira-mcp-server`, `stripe-mcp-server`

## Project Structure

```
{service}-mcp-server/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts          # Main entry point
│   ├── types.ts           # Type definitions
│   ├── tools/             # Tool implementations
│   ├── services/          # API clients and utilities
│   ├── schemas/           # Zod validation schemas
│   └── constants.ts       # Shared constants
└── dist/                  # Built JavaScript files
```

## IMPORTANT - Use Modern APIs Only

- **DO use**: `server.registerTool()`, `server.registerResource()`, `server.registerPrompt()`
- **DO NOT use**: `server.tool()`, `server.setRequestHandler(ListToolsRequestSchema, ...)`

## Tool Implementation

Use Zod schemas for runtime input validation:

```typescript
const UserSearchInputSchema = z.object({
  query: z.string().min(2).max(200).describe("Search string"),
  limit: z.number().int().min(1).max(100).default(20).describe("Max results"),
  offset: z.number().int().min(0).default(0).describe("Pagination offset"),
}).strict();

server.registerTool(
  "example_search_users",
  {
    title: "Search Users",
    description: "Search for users by name or email",
    inputSchema: UserSearchInputSchema,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: true
    }
  },
  async (params) => {
    // implementation
  }
);
```

## Error Handling

```typescript
function handleApiError(error: unknown): string {
  if (error instanceof AxiosError) {
    if (error.response) {
      switch (error.response.status) {
        case 404: return "Error: Resource not found.";
        case 403: return "Error: Permission denied.";
        case 429: return "Error: Rate limit exceeded.";
        default: return `Error: API request failed with status ${error.response.status}`;
      }
    }
  }
  return `Error: ${error instanceof Error ? error.message : String(error)}`;
}
```

## Transport Options

### Streamable HTTP (Remote)
```typescript
const app = express();
app.use(express.json());
app.post('/mcp', async (req, res) => {
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true
  });
  res.on('close', () => transport.close());
  await server.connect(transport);
  await transport.handleRequest(req, res, req.body);
});
app.listen(3000);
```

### stdio (Local)
```typescript
const transport = new StdioServerTransport();
await server.connect(transport);
```

## Package Configuration

### package.json
```json
{
  "name": "{service}-mcp-server",
  "version": "1.0.0",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "start": "node dist/index.js",
    "dev": "tsx watch src/index.ts",
    "build": "tsc"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.6.1",
    "axios": "^1.7.9",
    "zod": "^3.23.8"
  },
  "devDependencies": {
    "@types/node": "^22.10.0",
    "tsx": "^4.19.2",
    "typescript": "^5.7.2"
  }
}
```

### tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "declaration": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

## Quality Checklist

- [ ] Tools registered with `registerTool` and complete configuration
- [ ] All tools include `title`, `description`, `inputSchema`, `annotations`
- [ ] Zod schemas with `.strict()` enforcement
- [ ] No use of `any` type
- [ ] All async functions have explicit return types
- [ ] `npm run build` completes without errors
- [ ] Server name follows `{service}-mcp-server` format
