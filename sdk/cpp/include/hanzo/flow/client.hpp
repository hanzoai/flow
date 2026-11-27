#pragma once

// hanzo/flow/client.hpp — Native C++20 REST client for the canonical Hanzo Flow
// API (/v1/flow/*), backed by RAII libcurl.

#include <cstddef>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "hanzo/flow/core.hpp"
#include "hanzo/flow/json.hpp"

namespace hanzo::flow {

inline constexpr std::string_view kDefaultBaseUrl = "https://api.hanzo.ai";
inline constexpr std::string_view kGraphSchemaVersion = "hanzo.flow/v1";

struct ApiError {
    int status = 0;
    std::string title;
    std::string detail;
    std::string request_id;

    [[nodiscard]] std::string message() const;
};

template <typename T>
using Result = Expected<T, ApiError>;

struct ClientConfig {
    std::string base_url = std::string(kDefaultBaseUrl);
    std::string token;
    std::string org_id;
    long timeout_ms = 60000;
    long connect_timeout_ms = 10000;
};

struct FlowStatus {
    bool reachable = false;
    std::string version;
};

struct GraphNode {
    std::string id;
    std::string type;
    std::optional<json::Value> data;
};

struct GraphEdge {
    std::string id;
    std::string source;
    std::string source_handle;
    std::string target;
    std::string target_handle;
};

struct WorkflowGraph {
    std::string schema = std::string(kGraphSchemaVersion);
    std::vector<GraphNode> nodes;
    std::vector<GraphEdge> edges;

    [[nodiscard]] json::Value to_json() const;
    [[nodiscard]] static WorkflowGraph from_json(const json::Value& v);
};

struct Workflow {
    std::string id;
    std::string name;
    std::string description;
    std::optional<WorkflowGraph> data;
    bool locked = false;
    std::string folder_id;
    std::string updated_at;
    json::Value raw;
};

struct ListOptions {
    std::optional<int> page;
    std::optional<int> size;
};

struct WorkflowList {
    std::vector<Workflow> workflows;
    std::size_t total = 0;
    std::optional<int> page;
    std::optional<int> size;
    std::optional<int> pages;
    json::Value raw;
};

struct CreateWorkflowRequest {
    std::string name;
    std::string description;
    std::optional<WorkflowGraph> data;
};

struct UpdateWorkflowRequest {
    std::optional<std::string> name;
    std::optional<std::string> description;
    std::optional<WorkflowGraph> data;
    std::optional<bool> locked;
};

struct RunRequest {
    std::string workflow;
    std::string input;
    std::string session;
    std::optional<json::Value> tweaks;
};

struct RunResponse {
    std::string session_id;
    std::vector<json::Value> outputs;
    json::Value raw;
};

struct RunsResponse {
    std::map<std::string, json::Value> vertex_builds;
    std::vector<json::Value> runs;
    json::Value raw;
};

class Client {
public:
    explicit Client(ClientConfig config = {});

    [[nodiscard]] const ClientConfig& config() const noexcept { return config_; }

    [[nodiscard]] Result<FlowStatus> status() const;
    [[nodiscard]] Result<WorkflowList> list_workflows(const ListOptions& opts = {}) const;
    [[nodiscard]] Result<Workflow> get_workflow(std::string_view id) const;
    [[nodiscard]] Result<Workflow> create_workflow(const CreateWorkflowRequest& req) const;
    [[nodiscard]] Result<Workflow> update_workflow(
        std::string_view id, const UpdateWorkflowRequest& req) const;
    [[nodiscard]] Result<void> delete_workflow(std::string_view id) const;
    [[nodiscard]] Result<RunResponse> run(const RunRequest& req) const;
    [[nodiscard]] Result<RunsResponse> list_runs(std::string_view workflow_id) const;

private:
    struct HttpResponse {
        long status = 0;
        std::string body;
        std::string request_id;
    };

    [[nodiscard]] Result<HttpResponse> perform(
        std::string_view method,
        std::string_view path_and_query,
        const std::optional<std::string>& body) const;

    ClientConfig config_;
};

}  // namespace hanzo::flow
