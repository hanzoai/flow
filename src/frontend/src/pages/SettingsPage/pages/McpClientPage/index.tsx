import { useCallback, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Button } from "@/components/ui/button";
import { customGetHostProtocol } from "@/customization/utils/custom-get-host-protocol";
import { cn } from "@/utils/utils";

type AgentTab = "hanzo-dev" | "claude-code" | "cursor";

const agents: { id: AgentTab; title: string; icon: string }[] = [
  { id: "hanzo-dev", title: "Hanzo Dev / CLI", icon: "Hanzo" },
  { id: "claude-code", title: "Claude Code", icon: "Terminal" },
  { id: "cursor", title: "Cursor", icon: "Cursor" },
];

function buildMcpJson(serverUrl: string): string {
  return JSON.stringify(
    {
      mcpServers: {
        hanzo: {
          command: "npx",
          args: ["-y", "hanzo", "mcp"],
          env: {
            FLOW_SERVER_URL: serverUrl,
            FLOW_API_KEY: "YOUR_API_KEY", // pragma: allowlist secret
          },
        },
      },
    },
    null,
    2,
  );
}

function getAgentInstructions(agent: AgentTab): {
  configPath: string;
  steps: string[];
} {
  switch (agent) {
    case "hanzo-dev":
      return {
        configPath: "~/.hanzo/mcp.json",
        steps: [
          "Run the Hanzo MCP server directly with npx or install globally with npm i -g hanzo:",
          "Or add the JSON config below to ~/.hanzo/mcp.json (hanzo dev loads it automatically)",
        ],
      };
    case "claude-code":
      return {
        configPath: "~/.claude.json",
        steps: [
          "Run the command below in your terminal:",
          "Or add the JSON config below to ~/.claude.json manually",
        ],
      };
    case "cursor":
      return {
        configPath: "~/.cursor/mcp.json",
        steps: [
          "Open Cursor and go to Settings > MCP",
          "Click \"Add new global MCP server\" (or add .cursor/mcp.json in your project)",
          "Paste the JSON config below and save",
        ],
      };
  }
}

function getCliCommand(agent: AgentTab, serverUrl: string): string | null {
  switch (agent) {
    case "hanzo-dev":
      return `FLOW_SERVER_URL=${serverUrl} FLOW_API_KEY=YOUR_API_KEY npx -y hanzo mcp`;
    case "claude-code":
      return `claude mcp add hanzo -- npx -y hanzo mcp \\
  -e FLOW_SERVER_URL=${serverUrl} \\
  -e FLOW_API_KEY=YOUR_API_KEY`;
    case "cursor":
      return null;
  }
}

export default function McpClientPage() {
  const [selectedAgent, setSelectedAgent] = useState<AgentTab>("hanzo-dev");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const { host, protocol } = customGetHostProtocol();
  const serverUrl = `${protocol}//${host}`;

  const mcpJson = useMemo(() => buildMcpJson(serverUrl), [serverUrl]);
  const instructions = getAgentInstructions(selectedAgent);
  const cliCommand = useMemo(
    () => getCliCommand(selectedAgent, serverUrl),
    [selectedAgent, serverUrl],
  );

  const copyToClipboard = useCallback((text: string, key: string) => {
    if (!navigator.clipboard) return;
    navigator.clipboard.writeText(text).then(() => {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 1000);
    });
  }, []);

  return (
    <div className="flex h-full w-full flex-col gap-6">
      <div className="flex w-full items-start justify-between gap-6">
        <div className="flex flex-col">
          <h2 className="flex items-center text-lg font-semibold tracking-tight">
            Flow MCP Client
            <ForwardedIconComponent
              name="Mcp"
              className="ml-2 h-5 w-5 text-primary"
            />
          </h2>
          <p className="text-sm text-muted-foreground">
            Connect coding agents to build and run flows on this Hanzo Flow
            instance.
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <div
          className="flex flex-row justify-start border-b border-border"
          role="tablist"
        >
          {agents.map((agent) => (
            <Button
              unstyled
              key={agent.id}
              role="tab"
              aria-selected={selectedAgent === agent.id}
              data-testid={`mcp-client-tab-${agent.id}`}
              className={cn(
                "flex h-8 flex-row items-center gap-2 text-nowrap border-b-2 border-b-transparent px-3 py-2 text-[13px] font-medium transition-colors",
                selectedAgent === agent.id
                  ? "border-b-foreground text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
              onClick={() => {
                setSelectedAgent(agent.id);
                setCopiedKey(null);
              }}
            >
              <ForwardedIconComponent
                name={agent.icon}
                className="h-4 w-4"
                aria-hidden="true"
              />
              <span>{agent.title}</span>
            </Button>
          ))}
        </div>

        <div className="flex flex-col gap-3">
          <ol className="list-decimal pl-5 text-sm text-muted-foreground space-y-1">
            {instructions.steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>

          {cliCommand && (
            <div className="relative overflow-hidden rounded-lg border border-border bg-background">
              <div className="absolute right-3 top-3">
                <Button
                  unstyled
                  size="icon"
                  className="h-4 w-4 text-muted-foreground hover:text-foreground"
                  onClick={() => copyToClipboard(cliCommand, "command")}
                >
                  <ForwardedIconComponent
                    name={copiedKey === "command" ? "Check" : "Copy"}
                    className="h-4 w-4"
                    aria-hidden="true"
                  />
                </Button>
              </div>
              <pre
                className="overflow-x-auto p-4 text-[13px]"
                data-testid="mcp-client-cli-command"
              >
                <code>{cliCommand}</code>
              </pre>
            </div>
          )}

          {instructions.configPath && (
            <p className="text-sm text-muted-foreground">
              Config file:{" "}
              <code className="rounded bg-muted px-1.5 py-0.5 text-[13px]">
                {instructions.configPath}
              </code>
            </p>
          )}

          <div className="relative overflow-hidden rounded-lg border border-border bg-background">
            <div className="absolute right-3 top-3">
              <Button
                unstyled
                size="icon"
                className="h-4 w-4 text-muted-foreground hover:text-foreground"
                onClick={() => copyToClipboard(mcpJson, "json")}
              >
                <ForwardedIconComponent
                  name={copiedKey === "json" ? "Check" : "Copy"}
                  className="h-4 w-4"
                  aria-hidden="true"
                />
              </Button>
            </div>
            <pre
              className="overflow-x-auto p-4 text-[13px]"
              data-testid="mcp-client-json-config"
            >
              <code>{mcpJson}</code>
            </pre>
          </div>

          <div className="flex items-start gap-2 rounded-md border border-border bg-muted/50 px-3 py-2 text-sm text-muted-foreground">
            <ForwardedIconComponent
              name="Info"
              className="mt-0.5 h-4 w-4 shrink-0 text-foreground"
            />
            <span>
              Authenticate with{" "}
              <code className="font-mono text-foreground">hanzo auth login</code>{" "}
              or generate an API key in{" "}
              <Link
                to="/settings/api-keys"
                className="text-foreground underline hover:opacity-80"
              >
                API Keys settings
              </Link>
              .
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
