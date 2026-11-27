#include "hanzo/flow/client.hpp"
#include "hanzo/flow/core.hpp"
#include "hanzo/flow/json.hpp"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <atomic>
#include <cctype>
#include <cstring>
#include <functional>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {

using namespace hanzo::flow;

int g_passed = 0;
int g_failed = 0;

void expect(bool cond, const std::string& msg) {
    if (!cond) {
        throw std::runtime_error("assertion failed: " + msg);
    }
}

void run_test(const char* name, const std::function<void()>& fn) {
    try {
        fn();
        ++g_passed;
        std::cout << "[PASS] " << name << '\n';
    } catch (const std::exception& ex) {
        ++g_failed;
        std::cerr << "[FAIL] " << name << ": " << ex.what() << '\n';
    }
}

// ── Core DAG Test Helpers ───────────────────────────────────────────────────

class TextValue final : public Value {
public:
    explicit TextValue(std::string text) : text_(std::move(text)) {}
    [[nodiscard]] std::string_view port_type() const noexcept override { return "text"; }
    [[nodiscard]] const std::string& text() const noexcept { return text_; }

private:
    std::string text_;
};

ValueRef make_text(std::string s) { return std::make_shared<TextValue>(std::move(s)); }

class SourceStep final : public Step {
public:
    SourceStep(std::string id, ValueRef val) : id_(std::move(id)), val_(std::move(val)) {}
    [[nodiscard]] std::string_view id() const noexcept override { return id_; }
    [[nodiscard]] std::vector<Port> ins() const override { return {}; }
    [[nodiscard]] std::vector<Port> outs() const override { return {{"out", "text"}}; }
    [[nodiscard]] Expected<Outputs, CoreError> run(const Inputs&) const override {
        return Outputs{{"out", val_}};
    }

private:
    std::string id_;
    ValueRef val_;
};

class UpperStep final : public Step {
public:
    explicit UpperStep(std::string id) : id_(std::move(id)) {}
    [[nodiscard]] std::string_view id() const noexcept override { return id_; }
    [[nodiscard]] std::vector<Port> ins() const override { return {{"in", "text"}}; }
    [[nodiscard]] std::vector<Port> outs() const override { return {{"out", "text"}}; }
    [[nodiscard]] Expected<Outputs, CoreError> run(const Inputs& in) const override {
        auto it = in.find("in");
        if (it == in.end()) {
            return CoreError{ErrorCode::StepFailed, "missing input"};
        }
        auto tv = value_cast<TextValue>(it->second);
        if (!tv) {
            return CoreError{ErrorCode::StepFailed, "expected TextValue"};
        }
        std::string s = tv->text();
        std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
            return static_cast<char>(std::toupper(c));
        });
        return Outputs{{"out", make_text(std::move(s))}};
    }

private:
    std::string id_;
};

class WantNumberStep final : public Step {
public:
    explicit WantNumberStep(std::string id) : id_(std::move(id)) {}
    [[nodiscard]] std::string_view id() const noexcept override { return id_; }
    [[nodiscard]] std::vector<Port> ins() const override { return {{"in", "number"}}; }
    [[nodiscard]] std::vector<Port> outs() const override { return {}; }
    [[nodiscard]] Expected<Outputs, CoreError> run(const Inputs&) const override { return Outputs{}; }

private:
    std::string id_;
};

class PassthroughStep final : public Step {
public:
    explicit PassthroughStep(std::string id) : id_(std::move(id)) {}
    [[nodiscard]] std::string_view id() const noexcept override { return id_; }
    [[nodiscard]] std::vector<Port> ins() const override { return {{"in", std::string(kAnyType)}}; }
    [[nodiscard]] std::vector<Port> outs() const override { return {{"out", std::string(kAnyType)}}; }
    [[nodiscard]] Expected<Outputs, CoreError> run(const Inputs& in) const override {
        Outputs out;
        if (auto it = in.find("in"); it != in.end()) {
            out.emplace("out", it->second);
        }
        return out;
    }

private:
    std::string id_;
};

class CountingBackend final : public Backend {
public:
    explicit CountingBackend(Mode m) : mode_(m) {}
    [[nodiscard]] Mode mode() const noexcept override { return mode_; }
    [[nodiscard]] Expected<Outputs, CoreError> exec(
        const Step& step, const Inputs& in) const override {
        calls_.fetch_add(1, std::memory_order_seq_cst);
        return step.run(in);
    }
    [[nodiscard]] int calls() const noexcept { return calls_.load(std::memory_order_seq_cst); }

private:
    Mode mode_;
    mutable std::atomic<int> calls_{0};
};

// ── Core DAG Tests ──────────────────────────────────────────────────────────

void test_dag_pipeline_in_process() {
    Graph g;
    expect(g.add(std::make_shared<SourceStep>("src", make_text("hello"))).has_value(), "add src");
    expect(g.add(std::make_shared<UpperStep>("up")).has_value(), "add up");
    expect(g.wire({"src", "out"}, {"up", "in"}).has_value(), "wire src->up");

    Scheduler sched;
    auto res = sched.run(g, Mode::InProcess);
    expect(res.has_value(), "run ok");
    const auto& out = res.value();
    expect(out.find("src.out") == out.end(), "non-terminal port must not leak");
    auto it = out.find("up.out");
    expect(it != out.end(), "terminal port up.out present");
    auto tv = value_cast<TextValue>(it->second);
    expect(tv != nullptr && tv->text() == "HELLO", "up.out == HELLO");
}

void test_zero_copy_value_passing() {
    ValueRef original = make_text("zero-copy-payload");
    const Value* raw_ptr = original.get();

    Graph g;
    expect(g.add(std::make_shared<SourceStep>("src", original)).has_value(), "add src");
    expect(g.add(std::make_shared<PassthroughStep>("pass")).has_value(), "add pass");
    expect(g.wire({"src", "out"}, {"pass", "in"}).has_value(), "wire wildcard");

    Scheduler sched;
    auto res = sched.run(g, Mode::InProcess);
    expect(res.has_value(), "run ok");
    const auto& out_ref = res.value().at("pass.out");
    expect(out_ref.get() == raw_ptr, "shared_ptr pointer identity preserved (zero-copy)");
}

void test_port_type_mismatch_rejected() {
    Graph g;
    expect(g.add(std::make_shared<SourceStep>("src", make_text("x"))).has_value(), "add src");
    expect(g.add(std::make_shared<WantNumberStep>("num")).has_value(), "add num");
    auto w = g.wire({"src", "out"}, {"num", "in"});
    expect(!w.has_value(), "type mismatch must fail");
    expect(w.error().code == ErrorCode::TypeMismatch, "error code TypeMismatch");
}

void test_wildcard_any_type_port() {
    Graph g;
    expect(g.add(std::make_shared<SourceStep>("src", make_text("ok"))).has_value(), "add src");
    expect(g.add(std::make_shared<PassthroughStep>("p")).has_value(), "add p");
    expect(g.add(std::make_shared<UpperStep>("up")).has_value(), "add up");
    expect(g.wire({"src", "out"}, {"p", "in"}).has_value(), "text -> *");
    expect(g.wire({"p", "out"}, {"up", "in"}).has_value(), "* -> text");

    auto res = Scheduler().run(g, Mode::InProcess);
    expect(res.has_value(), "run ok");
    expect(value_cast<TextValue>(res.value().at("up.out"))->text() == "OK", "wildcard chain output");
}

void test_cycle_rejected() {
    Graph g;
    expect(g.add(std::make_shared<PassthroughStep>("a")).has_value(), "add a");
    expect(g.add(std::make_shared<PassthroughStep>("b")).has_value(), "add b");
    expect(g.wire({"a", "out"}, {"b", "in"}).has_value(), "wire a->b");
    expect(g.wire({"b", "out"}, {"a", "in"}).has_value(), "wire b->a");

    auto v = g.validate();
    expect(!v.has_value(), "cycle must fail validate");
    expect(v.error().code == ErrorCode::Cycle, "error code Cycle");

    auto r = Scheduler().run(g, Mode::InProcess);
    expect(!r.has_value() && r.error().code == ErrorCode::Cycle, "run rejects cycle");
}

void test_duplicate_and_empty_step_rejected() {
    Graph g;
    expect(g.add(std::make_shared<PassthroughStep>("")).error().code == ErrorCode::EmptyStepId, "empty id");
    expect(g.add(std::make_shared<PassthroughStep>("dup")).has_value(), "first add");
    auto dup = g.add(std::make_shared<PassthroughStep>("dup"));
    expect(!dup.has_value() && dup.error().code == ErrorCode::DuplicateStep, "duplicate id rejected");
}

void test_missing_port_and_mode_backend() {
    Graph g;
    expect(g.add(std::make_shared<SourceStep>("src", make_text("hi"))).has_value(), "add src");
    auto bad_port = g.wire({"src", "nope"}, {"src", "out"});
    expect(!bad_port.has_value() && bad_port.error().code == ErrorCode::NoPort, "missing port");

    auto durable = std::make_shared<CountingBackend>(Mode::Durable);
    Scheduler sched;
    sched.register_backend(durable);

    auto res = sched.run(g, Mode::Durable);
    expect(res.has_value(), "durable run ok");
    expect(durable->calls() == 1, "durable backend called once");

    auto missing = sched.run(g, Mode::GpuResident);
    expect(!missing.has_value() && missing.error().code == ErrorCode::NoBackend, "unregistered mode rejected");
}

// ── In-Process POSIX Loopback HTTP Test Server ──────────────────────────────

struct HttpReq {
    std::string method;
    std::string target;
    std::map<std::string, std::string> headers;
    std::string body;
};

struct HttpReply {
    int status = 200;
    std::string reason = "OK";
    std::vector<std::pair<std::string, std::string>> headers;
    std::string body;
};

std::string lower_copy(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return s;
}

class LoopbackServer {
public:
    using Handler = std::function<HttpReply(const HttpReq&)>;

    LoopbackServer(int expected_requests, Handler handler)
        : expected_(expected_requests), handler_(std::move(handler)) {
        listen_fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
        expect(listen_fd_ >= 0, "socket()");
        int opt = 1;
        ::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        addr.sin_port = 0;
        expect(::bind(listen_fd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) == 0, "bind()");
        expect(::listen(listen_fd_, 16) == 0, "listen()");

        socklen_t len = sizeof(addr);
        expect(::getsockname(listen_fd_, reinterpret_cast<sockaddr*>(&addr), &len) == 0, "getsockname()");
        port_ = ntohs(addr.sin_port);

        thread_ = std::thread([this]() { serve(); });
    }

    ~LoopbackServer() {
        if (thread_.joinable()) thread_.join();
        if (listen_fd_ >= 0) ::close(listen_fd_);
    }

    [[nodiscard]] std::string base_url() const {
        return "http://127.0.0.1:" + std::to_string(port_);
    }

private:
    void serve() {
        for (int i = 0; i < expected_; ++i) {
            int client_fd = ::accept(listen_fd_, nullptr, nullptr);
            if (client_fd < 0) break;
            handle_client(client_fd);
            ::close(client_fd);
        }
    }

    void handle_client(int fd) {
        std::string raw;
        char buf[4096];
        std::size_t header_end = std::string::npos;
        std::size_t content_len = 0;

        while (true) {
            ssize_t n = ::recv(fd, buf, sizeof(buf), 0);
            if (n <= 0) break;
            raw.append(buf, static_cast<std::size_t>(n));
            if (header_end == std::string::npos) {
                header_end = raw.find("\r\n\r\n");
                if (header_end != std::string::npos) {
                    std::string hdrs = raw.substr(0, header_end);
                    std::size_t pos = 0;
                    while (pos < hdrs.size()) {
                        auto nl = hdrs.find("\r\n", pos);
                        std::string line = hdrs.substr(pos, nl == std::string::npos ? std::string::npos : nl - pos);
                        auto colon = line.find(':');
                        if (colon != std::string::npos) {
                            std::string k = lower_copy(line.substr(0, colon));
                            if (k == "content-length") {
                                content_len = static_cast<std::size_t>(std::stoul(line.substr(colon + 1)));
                            }
                        }
                        if (nl == std::string::npos) break;
                        pos = nl + 2;
                    }
                }
            }
            if (header_end != std::string::npos && raw.size() >= header_end + 4 + content_len) {
                break;
            }
        }

        if (header_end == std::string::npos) return;

        HttpReq req;
        std::string hdrs = raw.substr(0, header_end);
        auto first_nl = hdrs.find("\r\n");
        std::string req_line = hdrs.substr(0, first_nl);
        auto sp1 = req_line.find(' ');
        auto sp2 = req_line.find(' ', sp1 + 1);
        req.method = req_line.substr(0, sp1);
        req.target = req_line.substr(sp1 + 1, sp2 - sp1 - 1);

        std::size_t pos = first_nl + 2;
        while (pos < hdrs.size()) {
            auto nl = hdrs.find("\r\n", pos);
            std::string line = hdrs.substr(pos, nl == std::string::npos ? std::string::npos : nl - pos);
            auto colon = line.find(':');
            if (colon != std::string::npos) {
                std::string k = lower_copy(line.substr(0, colon));
                std::string v = line.substr(colon + 1);
                while (!v.empty() && (v.front() == ' ' || v.front() == '\t')) v.erase(v.begin());
                req.headers[std::move(k)] = std::move(v);
            }
            if (nl == std::string::npos) break;
            pos = nl + 2;
        }
        req.body = raw.substr(header_end + 4, content_len);

        HttpReply reply = handler_(req);
        std::string out = "HTTP/1.1 " + std::to_string(reply.status) + " " + reply.reason + "\r\n";
        out += "Content-Type: application/json\r\n";
        out += "Content-Length: " + std::to_string(reply.body.size()) + "\r\n";
        out += "Connection: close\r\n";
        for (const auto& [k, v] : reply.headers) {
            out += k + ": " + v + "\r\n";
        }
        out += "\r\n";
        out += reply.body;

        std::size_t sent = 0;
        while (sent < out.size()) {
            ssize_t n = ::send(fd, out.data() + sent, out.size() - sent, 0);
            if (n <= 0) break;
            sent += static_cast<std::size_t>(n);
        }
    }

    int listen_fd_ = -1;
    uint16_t port_ = 0;
    int expected_ = 0;
    Handler handler_;
    std::thread thread_;
};

// ── REST Client Integration Tests ───────────────────────────────────────────

void test_client_canonical_endpoints_and_headers() {
    const std::string wf_id = "8f14e45f-ceea-467a-8a3b-111111111111";
    const std::string token = "hz-cpp-token";
    const std::string org = "hanzo";

    LoopbackServer srv(8, [&](const HttpReq& req) -> HttpReply {
        expect(req.headers.at("authorization") == "Bearer " + token, "Authorization header");
        expect(req.headers.at("x-org-id") == org, "X-Org-Id header");

        if (req.method == "GET" && req.target == "/v1/flow/status") {
            return {200, "OK", {}, R"({"reachable":true,"version":"1.8.16"})"};
        }
        if (req.method == "GET" && req.target == "/v1/flow/workflows?page=2&size=25") {
            return {
                200,
                "OK",
                {},
                R"({"flows":[{"id":")" + wf_id + R"(","name":"triage"}],"total":1,"page":2,"size":25,"pages":1})",
            };
        }
        if (req.method == "POST" && req.target == "/v1/flow/workflows") {
            auto parsed = json::parse(req.body);
            expect(parsed.has_value(), "valid create body");
            expect(parsed.value().find("name")->as_string() == "triage", "create name");
            const auto* data = parsed.value().find("data");
            expect(data != nullptr && data->find("schema")->as_string() == "hanzo.flow/v1", "graph schema");
            return {
                200,
                "OK",
                {},
                R"({"id":")" + wf_id +
                    R"(","name":"triage","description":"route","data":{"schema":"hanzo.flow/v1","nodes":[{"id":"n1","type":"input"}],"edges":[]}})",
            };
        }
        if (req.method == "GET" && req.target == "/v1/flow/workflows/" + wf_id) {
            return {200, "OK", {}, R"({"id":")" + wf_id + R"(","name":"triage","locked":false})"};
        }
        if (req.method == "PATCH" && req.target == "/v1/flow/workflows/" + wf_id) {
            auto parsed = json::parse(req.body);
            expect(parsed.has_value(), "valid patch body");
            expect(parsed.value().find("name")->as_string() == "triage-v2", "patch name");
            expect(parsed.value().find("locked")->as_bool() == true, "patch locked");
            expect(parsed.value().find("description") == nullptr, "omitted field absent");
            return {200, "OK", {}, R"({"id":")" + wf_id + R"(","name":"triage-v2","locked":true})"};
        }
        if (req.method == "POST" && req.target == "/v1/flow/runs") {
            auto parsed = json::parse(req.body);
            expect(parsed.has_value(), "valid run body");
            expect(parsed.value().find("workflow")->as_string() == wf_id, "run workflow");
            expect(parsed.value().find("input")->as_string() == "summarize", "run input");
            expect(parsed.value().find("session")->as_string() == "sess-1", "run session");
            return {200, "OK", {}, R"({"session_id":"sess-1","outputs":[{"text":"done"}]})"};
        }
        if (req.method == "GET" && req.target == "/v1/flow/runs?workflow=" + wf_id) {
            return {200, "OK", {}, R"({"vertex_builds":{"n1":[{"status":"ok"}]}})"};
        }
        if (req.method == "DELETE" && req.target == "/v1/flow/workflows/" + wf_id) {
            return {204, "No Content", {}, ""};
        }
        return {404, "Not Found", {}, R"({"detail":"unexpected route"})"};
    });

    ClientConfig cfg;
    cfg.base_url = srv.base_url();
    cfg.token = token;
    cfg.org_id = org;
    Client client(cfg);

    auto st = client.status();
    expect(st.has_value() && st.value().reachable && st.value().version == "1.8.16", "status()");

    auto list = client.list_workflows({2, 25});
    expect(list.has_value() && list.value().total == 1 && list.value().workflows.size() == 1, "list_workflows()");
    expect(list.value().workflows[0].id == wf_id, "listed workflow id");

    WorkflowGraph graph;
    graph.nodes.push_back({"n1", "input", std::nullopt});
    graph.edges.push_back({"e1", "n1", "out", "n2", "in"});
    auto created = client.create_workflow({"triage", "route", graph});
    expect(created.has_value() && created.value().id == wf_id, "create_workflow()");
    expect(created.value().data.has_value() && created.value().data->schema == "hanzo.flow/v1", "graph roundtrip");

    auto got = client.get_workflow(wf_id);
    expect(got.has_value() && !got.value().locked, "get_workflow()");

    UpdateWorkflowRequest patch;
    patch.name = "triage-v2";
    patch.locked = true;
    auto updated = client.update_workflow(wf_id, patch);
    expect(updated.has_value() && updated.value().name == "triage-v2" && updated.value().locked, "update_workflow()");

    RunRequest run_req;
    run_req.workflow = wf_id;
    run_req.input = "summarize";
    run_req.session = "sess-1";
    auto ran = client.run(run_req);
    expect(ran.has_value() && ran.value().session_id == "sess-1" && ran.value().outputs.size() == 1, "run()");

    auto runs = client.list_runs(wf_id);
    expect(runs.has_value() && runs.value().vertex_builds.count("n1") == 1, "list_runs()");

    auto del = client.delete_workflow(wf_id);
    expect(del.has_value(), "delete_workflow()");
}

void test_client_error_handling_and_validation() {
    const std::string wf_id = "8f14e45f-ceea-467a-8a3b-111111111111";
    LoopbackServer srv(1, [&](const HttpReq&) -> HttpReply {
        return {
            404,
            "Not Found",
            {{"X-Request-Id", "req-cpp-404"}},
            R"({"title":"Not Found","status":404,"detail":"workflow not found"})",
        };
    });

    ClientConfig cfg;
    cfg.base_url = srv.base_url();
    Client client(cfg);

    auto res = client.get_workflow(wf_id);
    expect(!res.has_value(), "404 must return ApiError");
    expect(res.error().status == 404, "error status 404");
    expect(res.error().title == "Not Found", "error title");
    expect(res.error().detail == "workflow not found", "error detail");
    expect(res.error().request_id == "req-cpp-404", "error request_id");
    expect(res.error().message().find("req-cpp-404") != std::string::npos, "error message contains request_id");

    // Local input validation (no network call)
    expect(!client.get_workflow(" ").has_value(), "empty id rejected");
    expect(!client.create_workflow({"", "", std::nullopt}).has_value(), "empty name rejected");
    expect(!client.run({"", "hi", "", std::nullopt}).has_value(), "empty workflow rejected");
    expect(!client.list_runs("").has_value(), "empty list_runs workflow rejected");
}

}  // namespace

int main() {
    run_test("core/dag_pipeline_in_process", test_dag_pipeline_in_process);
    run_test("core/zero_copy_value_passing", test_zero_copy_value_passing);
    run_test("core/port_type_mismatch_rejected", test_port_type_mismatch_rejected);
    run_test("core/wildcard_any_type_port", test_wildcard_any_type_port);
    run_test("core/cycle_rejected", test_cycle_rejected);
    run_test("core/duplicate_and_empty_step_rejected", test_duplicate_and_empty_step_rejected);
    run_test("core/missing_port_and_mode_backend", test_missing_port_and_mode_backend);
    run_test("client/canonical_endpoints_and_headers", test_client_canonical_endpoints_and_headers);
    run_test("client/error_handling_and_validation", test_client_error_handling_and_validation);

    std::cout << "\nTotal: " << g_passed << " passed, " << g_failed << " failed\n";
    return g_failed == 0 ? 0 : 1;
}
