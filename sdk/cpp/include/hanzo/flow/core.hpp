#pragma once

// hanzo/flow/core.hpp — 1:1 C++20 port of the Hanzo Flow step-DAG engine
// (mirrors Go `core/` and Rust `core-rs/`).
//
// Zero external dependencies. Values travel along edges as
// `std::shared_ptr<const Value>` so hand-off between steps is a zero-copy
// refcount bump. Execution locality/durability (`Mode`) is a parameter to
// `Scheduler::run`, selecting a registered `Backend` over the same topological
// walk.

#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <variant>
#include <vector>

namespace hanzo::flow {

// Wildcard port type tag that disables wire-time type checking on that edge.
inline constexpr std::string_view kAnyType = "*";

// ── Expected<T, E> (portable C++20 result type) ─────────────────────────────

template <typename T, typename E>
class Expected {
public:
    Expected(T value) : storage_(std::in_place_index<0>, std::move(value)) {}
    Expected(E error) : storage_(std::in_place_index<1>, std::move(error)) {}

    [[nodiscard]] bool has_value() const noexcept { return storage_.index() == 0; }
    [[nodiscard]] explicit operator bool() const noexcept { return has_value(); }

    [[nodiscard]] T& value() & {
        if (!has_value()) {
            throw std::logic_error("Expected has no value");
        }
        return std::get<0>(storage_);
    }
    [[nodiscard]] const T& value() const& {
        if (!has_value()) {
            throw std::logic_error("Expected has no value");
        }
        return std::get<0>(storage_);
    }
    [[nodiscard]] T&& value() && {
        if (!has_value()) {
            throw std::logic_error("Expected has no value");
        }
        return std::get<0>(std::move(storage_));
    }

    [[nodiscard]] E& error() & {
        if (has_value()) {
            throw std::logic_error("Expected has no error");
        }
        return std::get<1>(storage_);
    }
    [[nodiscard]] const E& error() const& {
        if (has_value()) {
            throw std::logic_error("Expected has no error");
        }
        return std::get<1>(storage_);
    }

private:
    std::variant<T, E> storage_;
};

template <typename E>
class Expected<void, E> {
public:
    Expected() : storage_(std::in_place_index<0>, std::monostate{}) {}
    Expected(E error) : storage_(std::in_place_index<1>, std::move(error)) {}

    [[nodiscard]] static Expected ok() noexcept { return Expected(); }

    [[nodiscard]] bool has_value() const noexcept { return storage_.index() == 0; }
    [[nodiscard]] explicit operator bool() const noexcept { return has_value(); }

    [[nodiscard]] E& error() & {
        if (has_value()) {
            throw std::logic_error("Expected<void> has no error");
        }
        return std::get<1>(storage_);
    }
    [[nodiscard]] const E& error() const& {
        if (has_value()) {
            throw std::logic_error("Expected<void> has no error");
        }
        return std::get<1>(storage_);
    }

private:
    std::variant<std::monostate, E> storage_;
};

// ── Errors ──────────────────────────────────────────────────────────────────

enum class ErrorCode {
    EmptyStepId,
    DuplicateStep,
    NoStep,
    NoPort,
    TypeMismatch,
    Cycle,
    NoBackend,
    StepFailed,
};

struct CoreError {
    ErrorCode code;
    std::string message;
};

// ── Value + Port ────────────────────────────────────────────────────────────

// Opaque typed value flowing along an edge. Held behind std::shared_ptr<const Value>
// so edge hand-off is zero-copy.
class Value {
public:
    virtual ~Value() = default;
    [[nodiscard]] virtual std::string_view port_type() const noexcept = 0;
};

using ValueRef = std::shared_ptr<const Value>;

template <typename T>
[[nodiscard]] inline std::shared_ptr<const T> value_cast(const ValueRef& ref) noexcept {
    return std::dynamic_pointer_cast<const T>(ref);
}

struct Port {
    std::string name;
    std::string type;
};

[[nodiscard]] inline bool types_match(std::string_view a, std::string_view b) noexcept {
    return a == b || a == kAnyType || b == kAnyType;
}

using Inputs = std::unordered_map<std::string, ValueRef>;
using Outputs = std::unordered_map<std::string, ValueRef>;

// ── Step + PortRef + Edge ───────────────────────────────────────────────────

class Step {
public:
    virtual ~Step() = default;
    [[nodiscard]] virtual std::string_view id() const noexcept = 0;
    [[nodiscard]] virtual std::vector<Port> ins() const = 0;
    [[nodiscard]] virtual std::vector<Port> outs() const = 0;
    [[nodiscard]] virtual Expected<Outputs, CoreError> run(const Inputs& in) const = 0;
};

struct PortRef {
    std::string step;
    std::string port;

    [[nodiscard]] std::string key() const { return step + "." + port; }
    [[nodiscard]] bool operator==(const PortRef& other) const noexcept = default;
};

struct Edge {
    PortRef from;
    PortRef to;
};

// ── Mode + Backend ──────────────────────────────────────────────────────────

enum class Mode {
    InProcess,
    GpuResident,
    Durable,
};

[[nodiscard]] inline std::string_view to_string(Mode m) noexcept {
    switch (m) {
        case Mode::InProcess:
            return "in-process";
        case Mode::GpuResident:
            return "gpu-resident";
        case Mode::Durable:
            return "durable";
    }
    return "mode(?)";
}

class Backend {
public:
    virtual ~Backend() = default;
    [[nodiscard]] virtual Mode mode() const noexcept = 0;
    [[nodiscard]] virtual Expected<Outputs, CoreError> exec(
        const Step& step, const Inputs& in) const = 0;
};

class InProcessBackend final : public Backend {
public:
    [[nodiscard]] Mode mode() const noexcept override { return Mode::InProcess; }
    [[nodiscard]] Expected<Outputs, CoreError> exec(
        const Step& step, const Inputs& in) const override {
        return step.run(in);
    }
};

// ── Graph ───────────────────────────────────────────────────────────────────

class Graph {
public:
    [[nodiscard]] Expected<void, CoreError> add(std::shared_ptr<Step> step) {
        if (!step || step->id().empty()) {
            return CoreError{ErrorCode::EmptyStepId, "flow: step has empty id"};
        }
        std::string id(step->id());
        if (steps_.find(id) != steps_.end()) {
            return CoreError{ErrorCode::DuplicateStep, "flow: duplicate step id \"" + id + "\""};
        }
        steps_.emplace(std::move(id), std::move(step));
        return Expected<void, CoreError>::ok();
    }

    [[nodiscard]] Expected<void, CoreError> wire(PortRef from, PortRef to) {
        auto out = find_port(from, false);
        if (!out) {
            return out.error();
        }
        auto in = find_port(to, true);
        if (!in) {
            return in.error();
        }
        if (!types_match(out.value().type, in.value().type)) {
            return CoreError{
                ErrorCode::TypeMismatch,
                "flow: type mismatch wiring " + from.key() + " (" + out.value().type + ") -> " +
                    to.key() + " (" + in.value().type + ")",
            };
        }
        edges_.push_back(Edge{std::move(from), std::move(to)});
        return Expected<void, CoreError>::ok();
    }

    [[nodiscard]] Expected<void, CoreError> validate() const {
        for (const auto& e : edges_) {
            auto out = find_port(e.from, false);
            if (!out) {
                return out.error();
            }
            auto in = find_port(e.to, true);
            if (!in) {
                return in.error();
            }
        }
        auto order = topo_order();
        if (!order) {
            return order.error();
        }
        return Expected<void, CoreError>::ok();
    }

    // Kahn's algorithm with a sorted ready set so scheduling order is deterministic.
    [[nodiscard]] Expected<std::vector<std::string>, CoreError> topo_order() const {
        std::unordered_map<std::string, std::size_t> indeg;
        indeg.reserve(steps_.size());
        for (const auto& [id, _] : steps_) {
            indeg.emplace(id, 0);
        }

        std::unordered_map<std::string, std::vector<std::string>> succ;
        for (const auto& e : edges_) {
            succ[e.from.step].push_back(e.to.step);
            auto it = indeg.find(e.to.step);
            if (it != indeg.end()) {
                it->second += 1;
            }
        }

        std::set<std::string> ready;
        for (const auto& [id, deg] : indeg) {
            if (deg == 0) {
                ready.insert(id);
            }
        }

        std::vector<std::string> order;
        order.reserve(steps_.size());
        while (!ready.empty()) {
            auto it = ready.begin();
            std::string id = *it;
            ready.erase(it);
            order.push_back(id);

            auto sit = succ.find(id);
            if (sit != succ.end()) {
                for (const auto& next : sit->second) {
                    auto dit = indeg.find(next);
                    if (dit != indeg.end()) {
                        dit->second -= 1;
                        if (dit->second == 0) {
                            ready.insert(next);
                        }
                    }
                }
            }
        }

        if (order.size() != steps_.size()) {
            return CoreError{
                ErrorCode::Cycle,
                "flow: graph has a cycle (" + std::to_string(order.size()) + " of " +
                    std::to_string(steps_.size()) + " steps scheduled)",
            };
        }
        return order;
    }

    [[nodiscard]] const std::unordered_map<std::string, std::shared_ptr<Step>>& steps() const noexcept {
        return steps_;
    }

    [[nodiscard]] const std::vector<Edge>& edges() const noexcept { return edges_; }

private:
    [[nodiscard]] Expected<Port, CoreError> find_port(const PortRef& ref, bool input) const {
        auto it = steps_.find(ref.step);
        if (it == steps_.end()) {
            return CoreError{ErrorCode::NoStep, "flow: no step \"" + ref.step + "\""};
        }
        const auto ports = input ? it->second->ins() : it->second->outs();
        for (const auto& p : ports) {
            if (p.name == ref.port) {
                return p;
            }
        }
        const std::string side = input ? "input" : "output";
        return CoreError{
            ErrorCode::NoPort,
            "flow: step \"" + ref.step + "\" has no " + side + " port \"" + ref.port + "\"",
        };
    }

    std::unordered_map<std::string, std::shared_ptr<Step>> steps_;
    std::vector<Edge> edges_;
};

// ── Scheduler ───────────────────────────────────────────────────────────────

class Scheduler {
public:
    Scheduler() { register_backend(std::make_shared<InProcessBackend>()); }

    void register_backend(std::shared_ptr<Backend> backend) {
        if (backend) {
            backends_[backend->mode()] = std::move(backend);
        }
    }

    [[nodiscard]] Expected<Outputs, CoreError> run(
        const Graph& g, Mode mode, const Inputs& source = {}) const {
        auto bit = backends_.find(mode);
        if (bit == backends_.end()) {
            return CoreError{
                ErrorCode::NoBackend,
                std::string("flow: no backend for ") + std::string(to_string(mode)),
            };
        }
        auto valid = g.validate();
        if (!valid) {
            return valid.error();
        }
        auto order_res = g.topo_order();
        if (!order_res) {
            return order_res.error();
        }
        const auto& order = order_res.value();

        std::unordered_map<std::string, PortRef> wires;
        std::unordered_set<std::string> fed;
        for (const auto& e : g.edges()) {
            wires.insert_or_assign(e.to.key(), e.from);
            fed.insert(e.from.key());
        }

        std::unordered_map<std::string, ValueRef> produced;
        const auto& steps = g.steps();

        for (const auto& id : order) {
            const auto& step = steps.at(id);
            Inputs step_in;
            for (const auto& p : step->ins()) {
                PortRef ref{id, p.name};
                const std::string ref_key = ref.key();
                auto wit = wires.find(ref_key);
                if (wit != wires.end()) {
                    auto pit = produced.find(wit->second.key());
                    if (pit != produced.end()) {
                        step_in.emplace(p.name, pit->second);
                    }
                } else {
                    auto sit = source.find(ref_key);
                    if (sit != source.end()) {
                        step_in.emplace(p.name, sit->second);
                    }
                }
            }

            auto out_res = bit->second->exec(*step, step_in);
            if (!out_res) {
                return CoreError{
                    ErrorCode::StepFailed,
                    "flow: step \"" + id + "\": " + out_res.error().message,
                };
            }
            const auto& out = out_res.value();
            for (const auto& p : step->outs()) {
                auto oit = out.find(p.name);
                if (oit != out.end()) {
                    produced.insert_or_assign(PortRef{id, p.name}.key(), oit->second);
                }
            }
        }

        Outputs leaves;
        for (const auto& id : order) {
            for (const auto& p : steps.at(id)->outs()) {
                PortRef ref{id, p.name};
                const std::string ref_key = ref.key();
                if (fed.find(ref_key) == fed.end()) {
                    auto pit = produced.find(ref_key);
                    if (pit != produced.end()) {
                        leaves.emplace(ref_key, pit->second);
                    }
                }
            }
        }
        return leaves;
    }

private:
    std::unordered_map<Mode, std::shared_ptr<Backend>> backends_;
};

}  // namespace hanzo::flow
