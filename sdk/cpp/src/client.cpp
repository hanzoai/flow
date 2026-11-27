#include "hanzo/flow/client.hpp"

#include <curl/curl.h>

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <mutex>
#include <sstream>

namespace hanzo::flow {

namespace {

std::once_flag g_curl_init_once;

void ensure_curl_init() {
    std::call_once(g_curl_init_once, []() { curl_global_init(CURL_GLOBAL_DEFAULT); });
}

class CurlEasy {
public:
    CurlEasy() : handle_(curl_easy_init()) {}
    ~CurlEasy() {
        if (handle_) curl_easy_cleanup(handle_);
    }
    CurlEasy(const CurlEasy&) = delete;
    CurlEasy& operator=(const CurlEasy&) = delete;

    [[nodiscard]] CURL* get() const noexcept { return handle_; }
    [[nodiscard]] explicit operator bool() const noexcept { return handle_ != nullptr; }

private:
    CURL* handle_ = nullptr;
};

class CurlSlist {
public:
    CurlSlist() = default;
    ~CurlSlist() {
        if (list_) curl_slist_free_all(list_);
    }
    CurlSlist(const CurlSlist&) = delete;
    CurlSlist& operator=(const CurlSlist&) = delete;

    void append(const std::string& header) {
        list_ = curl_slist_append(list_, header.c_str());
    }
    [[nodiscard]] curl_slist* get() const noexcept { return list_; }

private:
    curl_slist* list_ = nullptr;
};

std::string trim(std::string_view s) {
    std::size_t start = 0;
    while (start < s.size() && std::isspace(static_cast<unsigned char>(s[start])) != 0) ++start;
    std::size_t end = s.size();
    while (end > start && std::isspace(static_cast<unsigned char>(s[end - 1])) != 0) --end;
    return std::string(s.substr(start, end - start));
}

std::string url_encode(std::string_view s) {
    std::string out;
    out.reserve(s.size());
    for (unsigned char c : s) {
        bool unreserved = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
                          (c >= '0' && c <= '9') || c == '-' || c == '_' || c == '.' || c == '~';
        if (unreserved) {
            out.push_back(static_cast<char>(c));
        } else {
            char buf[4];
            std::snprintf(buf, sizeof(buf), "%%%02X", static_cast<unsigned int>(c));
            out += buf;
        }
    }
    return out;
}

std::string to_lower(std::string_view s) {
    std::string out(s);
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return out;
}

std::size_t write_body_cb(char* ptr, std::size_t size, std::size_t nmemb, void* userdata) {
    const std::size_t bytes = size * nmemb;
    auto* out = static_cast<std::string*>(userdata);
    out->append(ptr, bytes);
    return bytes;
}

std::size_t header_cb(char* ptr, std::size_t size, std::size_t nmemb, void* userdata) {
    const std::size_t bytes = size * nmemb;
    auto* req_id = static_cast<std::string*>(userdata);
    std::string_view line(ptr, bytes);
    auto colon = line.find(':');
    if (colon != std::string_view::npos) {
        if (to_lower(trim(line.substr(0, colon))) == "x-request-id") {
            *req_id = trim(line.substr(colon + 1));
        }
    }
    return bytes;
}

std::string status_title(int code) {
    switch (code) {
        case 400: return "Bad Request";
        case 401: return "Unauthorized";
        case 403: return "Forbidden";
        case 404: return "Not Found";
        case 409: return "Conflict";
        case 422: return "Unprocessable Entity";
        case 429: return "Too Many Requests";
        case 500: return "Internal Server Error";
        case 502: return "Bad Gateway";
        case 503: return "Service Unavailable";
        case 504: return "Gateway Timeout";
        default: return "HTTP " + std::to_string(code);
    }
}

ApiError decode_api_error(int status, const std::string& body, const std::string& header_req_id) {
    ApiError err;
    err.status = status;
    err.title = status_title(status);
    err.request_id = header_req_id;

    auto parsed = json::parse(body);
    if (parsed && parsed.value().is_object()) {
        const auto& obj = parsed.value();
        if (const auto* st = obj.find("status"); st != nullptr && st->is_number()) {
            err.status = static_cast<int>(st->as_int(status));
        }
        if (const auto* t = obj.find("title"); t != nullptr && t->is_string() && !t->as_string().empty()) {
            err.title = t->as_string();
        }
        if (err.request_id.empty()) {
            if (const auto* r = obj.find("request_id"); r != nullptr && r->is_string()) {
                err.request_id = r->as_string();
            }
        }
        for (const char* key : {"detail", "message", "error"}) {
            if (const auto* v = obj.find(key); v != nullptr && !v->is_null()) {
                err.detail = v->is_string() ? v->as_string() : v->dump();
                if (!err.detail.empty()) break;
            }
        }
    }
    if (err.detail.empty()) {
        err.detail = trim(body);
    }
    return err;
}

Workflow decode_workflow(const json::Value& v) {
    Workflow wf;
    wf.raw = v;
    if (!v.is_object()) return wf;
    if (const auto* f = v.find("id"); f && f->is_string()) wf.id = f->as_string();
    if (const auto* f = v.find("name"); f && f->is_string()) wf.name = f->as_string();
    if (const auto* f = v.find("description"); f && f->is_string()) wf.description = f->as_string();
    if (const auto* f = v.find("locked"); f && f->is_bool()) wf.locked = f->as_bool();
    if (const auto* f = v.find("folder_id"); f && f->is_string()) wf.folder_id = f->as_string();
    if (const auto* f = v.find("updated_at"); f && f->is_string()) wf.updated_at = f->as_string();
    if (const auto* f = v.find("data"); f && f->is_object()) wf.data = WorkflowGraph::from_json(*f);
    return wf;
}

}  // namespace

std::string ApiError::message() const {
    std::ostringstream oss;
    oss << "flow api " << status;
    if (!title.empty()) oss << ' ' << title;
    if (!detail.empty()) oss << ": " << detail;
    if (!request_id.empty()) oss << " (request_id=" << request_id << ')';
    return oss.str();
}

json::Value WorkflowGraph::to_json() const {
    json::Value::Object obj;
    obj["schema"] = schema.empty() ? std::string(kGraphSchemaVersion) : schema;

    json::Value::Array nodes_arr;
    nodes_arr.reserve(nodes.size());
    for (const auto& n : nodes) {
        json::Value::Object no;
        no["id"] = n.id;
        if (!n.type.empty()) no["type"] = n.type;
        if (n.data.has_value()) no["data"] = *n.data;
        nodes_arr.emplace_back(std::move(no));
    }
    obj["nodes"] = std::move(nodes_arr);

    json::Value::Array edges_arr;
    edges_arr.reserve(edges.size());
    for (const auto& e : edges) {
        json::Value::Object eo;
        if (!e.id.empty()) eo["id"] = e.id;
        eo["source"] = e.source;
        if (!e.source_handle.empty()) eo["sourceHandle"] = e.source_handle;
        eo["target"] = e.target;
        if (!e.target_handle.empty()) eo["targetHandle"] = e.target_handle;
        edges_arr.emplace_back(std::move(eo));
    }
    obj["edges"] = std::move(edges_arr);
    return json::Value(std::move(obj));
}

WorkflowGraph WorkflowGraph::from_json(const json::Value& v) {
    WorkflowGraph g;
    if (!v.is_object()) return g;
    if (const auto* s = v.find("schema"); s && s->is_string() && !s->as_string().empty()) {
        g.schema = s->as_string();
    }
    if (const auto* ns = v.find("nodes"); ns && ns->is_array()) {
        for (const auto& item : ns->as_array()) {
            if (!item.is_object()) continue;
            GraphNode node;
            if (const auto* f = item.find("id"); f && f->is_string()) node.id = f->as_string();
            if (const auto* f = item.find("type"); f && f->is_string()) node.type = f->as_string();
            if (const auto* f = item.find("data"); f && !f->is_null()) node.data = *f;
            g.nodes.push_back(std::move(node));
        }
    }
    if (const auto* es = v.find("edges"); es && es->is_array()) {
        for (const auto& item : es->as_array()) {
            if (!item.is_object()) continue;
            GraphEdge edge;
            if (const auto* f = item.find("id"); f && f->is_string()) edge.id = f->as_string();
            if (const auto* f = item.find("source"); f && f->is_string()) edge.source = f->as_string();
            if (const auto* f = item.find("sourceHandle"); f && f->is_string()) edge.source_handle = f->as_string();
            if (const auto* f = item.find("target"); f && f->is_string()) edge.target = f->as_string();
            if (const auto* f = item.find("targetHandle"); f && f->is_string()) edge.target_handle = f->as_string();
            g.edges.push_back(std::move(edge));
        }
    }
    return g;
}

Client::Client(ClientConfig config) : config_(std::move(config)) {
    ensure_curl_init();
    while (!config_.base_url.empty() && config_.base_url.back() == '/') {
        config_.base_url.pop_back();
    }
    if (config_.base_url.empty()) {
        config_.base_url = std::string(kDefaultBaseUrl);
    }
}

Result<Client::HttpResponse> Client::perform(
    std::string_view method,
    std::string_view path_and_query,
    const std::optional<std::string>& body) const {
    CurlEasy curl;
    if (!curl) {
        return ApiError{0, "Transport Error", "failed to initialize libcurl handle", ""};
    }

    const std::string url = config_.base_url + std::string(path_and_query);
    HttpResponse resp;

    CurlSlist headers;
    headers.append("Accept: application/json");
    if (body.has_value()) {
        headers.append("Content-Type: application/json");
    }
    if (!config_.token.empty()) {
        headers.append("Authorization: Bearer " + config_.token);
    }
    if (!config_.org_id.empty()) {
        headers.append("X-Org-Id: " + config_.org_id);
    }

    curl_easy_setopt(curl.get(), CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl.get(), CURLOPT_HTTPHEADER, headers.get());
    curl_easy_setopt(curl.get(), CURLOPT_NOSIGNAL, 1L);
    curl_easy_setopt(curl.get(), CURLOPT_TIMEOUT_MS, config_.timeout_ms);
    curl_easy_setopt(curl.get(), CURLOPT_CONNECTTIMEOUT_MS, config_.connect_timeout_ms);
    curl_easy_setopt(curl.get(), CURLOPT_WRITEFUNCTION, write_body_cb);
    curl_easy_setopt(curl.get(), CURLOPT_WRITEDATA, &resp.body);
    curl_easy_setopt(curl.get(), CURLOPT_HEADERFUNCTION, header_cb);
    curl_easy_setopt(curl.get(), CURLOPT_HEADERDATA, &resp.request_id);

    const std::string method_str(method);
    if (method_str == "POST") {
        curl_easy_setopt(curl.get(), CURLOPT_POST, 1L);
    } else if (method_str != "GET") {
        curl_easy_setopt(curl.get(), CURLOPT_CUSTOMREQUEST, method_str.c_str());
    }

    if (body.has_value()) {
        curl_easy_setopt(curl.get(), CURLOPT_POSTFIELDS, body->data());
        curl_easy_setopt(curl.get(), CURLOPT_POSTFIELDSIZE_LARGE, static_cast<curl_off_t>(body->size()));
    } else if (method_str == "POST") {
        curl_easy_setopt(curl.get(), CURLOPT_POSTFIELDS, "");
        curl_easy_setopt(curl.get(), CURLOPT_POSTFIELDSIZE, 0L);
    }

    const CURLcode rc = curl_easy_perform(curl.get());
    if (rc != CURLE_OK) {
        return ApiError{0, "Transport Error", curl_easy_strerror(rc), ""};
    }

    curl_easy_getinfo(curl.get(), CURLINFO_RESPONSE_CODE, &resp.status);
    if (resp.status < 200 || resp.status >= 300) {
        return decode_api_error(static_cast<int>(resp.status), resp.body, resp.request_id);
    }
    return resp;
}

Result<FlowStatus> Client::status() const {
    auto res = perform("GET", "/v1/flow/status", std::nullopt);
    if (!res) return res.error();
    auto parsed = json::parse(res.value().body);
    if (!parsed || !parsed.value().is_object()) {
        return ApiError{static_cast<int>(res.value().status), "Decode Error", "invalid status JSON", res.value().request_id};
    }
    FlowStatus out;
    if (const auto* r = parsed.value().find("reachable"); r && r->is_bool()) out.reachable = r->as_bool();
    if (const auto* v = parsed.value().find("version"); v && v->is_string()) out.version = v->as_string();
    return out;
}

Result<WorkflowList> Client::list_workflows(const ListOptions& opts) const {
    std::string path = "/v1/flow/workflows";
    char sep = '?';
    if (opts.page.has_value() && *opts.page > 0) {
        path += sep;
        sep = '&';
        path += "page=" + std::to_string(*opts.page);
    }
    if (opts.size.has_value() && *opts.size > 0) {
        path += sep;
        path += "size=" + std::to_string(*opts.size);
    }
    auto res = perform("GET", path, std::nullopt);
    if (!res) return res.error();
    auto parsed = json::parse(res.value().body);
    if (!parsed) {
        return ApiError{static_cast<int>(res.value().status), "Decode Error", parsed.error().message, res.value().request_id};
    }

    WorkflowList out;
    out.raw = parsed.value();
    if (parsed.value().is_array()) {
        for (const auto& item : parsed.value().as_array()) {
            out.workflows.push_back(decode_workflow(item));
        }
        out.total = out.workflows.size();
        return out;
    }
    if (parsed.value().is_object()) {
        const auto& obj = parsed.value();
        const auto* arr = obj.find("flows");
        if (!arr || !arr->is_array()) arr = obj.find("items");
        if (arr && arr->is_array()) {
            for (const auto& item : arr->as_array()) {
                out.workflows.push_back(decode_workflow(item));
            }
        }
        if (const auto* t = obj.find("total"); t && t->is_number()) {
            out.total = static_cast<std::size_t>(t->as_int());
        } else {
            out.total = out.workflows.size();
        }
        if (const auto* p = obj.find("page"); p && p->is_number()) out.page = static_cast<int>(p->as_int());
        if (const auto* s = obj.find("size"); s && s->is_number()) out.size = static_cast<int>(s->as_int());
        if (const auto* ps = obj.find("pages"); ps && ps->is_number()) out.pages = static_cast<int>(ps->as_int());
    }
    return out;
}

Result<Workflow> Client::get_workflow(std::string_view id) const {
    const std::string trimmed = trim(id);
    if (trimmed.empty()) {
        return ApiError{0, "Invalid Input", "workflow id is required", ""};
    }
    auto res = perform("GET", "/v1/flow/workflows/" + url_encode(trimmed), std::nullopt);
    if (!res) return res.error();
    auto parsed = json::parse(res.value().body);
    if (!parsed) {
        return ApiError{static_cast<int>(res.value().status), "Decode Error", parsed.error().message, res.value().request_id};
    }
    return decode_workflow(parsed.value());
}

Result<Workflow> Client::create_workflow(const CreateWorkflowRequest& req) const {
    if (trim(req.name).empty()) {
        return ApiError{0, "Invalid Input", "workflow name is required", ""};
    }
    json::Value::Object payload;
    payload["name"] = req.name;
    if (!req.description.empty()) payload["description"] = req.description;
    if (req.data.has_value()) payload["data"] = req.data->to_json();

    auto res = perform("POST", "/v1/flow/workflows", json::Value(std::move(payload)).dump());
    if (!res) return res.error();
    auto parsed = json::parse(res.value().body);
    if (!parsed) {
        return ApiError{static_cast<int>(res.value().status), "Decode Error", parsed.error().message, res.value().request_id};
    }
    return decode_workflow(parsed.value());
}

Result<Workflow> Client::update_workflow(
    std::string_view id, const UpdateWorkflowRequest& req) const {
    const std::string trimmed = trim(id);
    if (trimmed.empty()) {
        return ApiError{0, "Invalid Input", "workflow id is required", ""};
    }
    json::Value::Object payload;
    if (req.name.has_value()) payload["name"] = *req.name;
    if (req.description.has_value()) payload["description"] = *req.description;
    if (req.data.has_value()) payload["data"] = req.data->to_json();
    if (req.locked.has_value()) payload["locked"] = *req.locked;

    auto res = perform(
        "PATCH",
        "/v1/flow/workflows/" + url_encode(trimmed),
        json::Value(std::move(payload)).dump());
    if (!res) return res.error();
    auto parsed = json::parse(res.value().body);
    if (!parsed) {
        return ApiError{static_cast<int>(res.value().status), "Decode Error", parsed.error().message, res.value().request_id};
    }
    return decode_workflow(parsed.value());
}

Result<void> Client::delete_workflow(std::string_view id) const {
    const std::string trimmed = trim(id);
    if (trimmed.empty()) {
        return ApiError{0, "Invalid Input", "workflow id is required", ""};
    }
    auto res = perform("DELETE", "/v1/flow/workflows/" + url_encode(trimmed), std::nullopt);
    if (!res) return res.error();
    return Result<void>::ok();
}

Result<RunResponse> Client::run(const RunRequest& req) const {
    if (trim(req.workflow).empty()) {
        return ApiError{0, "Invalid Input", "workflow id is required", ""};
    }
    json::Value::Object payload;
    payload["workflow"] = req.workflow;
    if (!req.input.empty()) payload["input"] = req.input;
    if (!req.session.empty()) payload["session"] = req.session;
    if (req.tweaks.has_value()) payload["tweaks"] = *req.tweaks;

    auto res = perform("POST", "/v1/flow/runs", json::Value(std::move(payload)).dump());
    if (!res) return res.error();
    auto parsed = json::parse(res.value().body);
    if (!parsed) {
        return ApiError{static_cast<int>(res.value().status), "Decode Error", parsed.error().message, res.value().request_id};
    }

    RunResponse out;
    out.raw = parsed.value();
    if (parsed.value().is_object()) {
        if (const auto* s = parsed.value().find("session_id"); s && s->is_string()) {
            out.session_id = s->as_string();
        }
        if (const auto* o = parsed.value().find("outputs"); o && o->is_array()) {
            out.outputs = o->as_array();
        }
    }
    return out;
}

Result<RunsResponse> Client::list_runs(std::string_view workflow_id) const {
    const std::string trimmed = trim(workflow_id);
    if (trimmed.empty()) {
        return ApiError{0, "Invalid Input", "workflow id is required", ""};
    }
    auto res = perform("GET", "/v1/flow/runs?workflow=" + url_encode(trimmed), std::nullopt);
    if (!res) return res.error();
    auto parsed = json::parse(res.value().body);
    if (!parsed) {
        return ApiError{static_cast<int>(res.value().status), "Decode Error", parsed.error().message, res.value().request_id};
    }

    RunsResponse out;
    out.raw = parsed.value();
    if (parsed.value().is_array()) {
        out.runs = parsed.value().as_array();
    } else if (parsed.value().is_object()) {
        if (const auto* vb = parsed.value().find("vertex_builds"); vb && vb->is_object()) {
            out.vertex_builds = vb->as_object();
        }
        if (const auto* rs = parsed.value().find("runs"); rs && rs->is_array()) {
            out.runs = rs->as_array();
        }
    }
    return out;
}

}  // namespace hanzo::flow
