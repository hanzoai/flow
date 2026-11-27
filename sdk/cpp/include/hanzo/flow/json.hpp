#pragma once

// Minimal zero-dependency RFC 8259 JSON parser and serializer for hanzo::flow.

#include <charconv>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

#include "hanzo/flow/core.hpp"

namespace hanzo::flow::json {

struct ParseError {
    std::string message;
};

class Value {
public:
    using Array = std::vector<Value>;
    using Object = std::map<std::string, Value>;

    Value() : data_(std::monostate{}) {}
    Value(std::nullptr_t) : data_(std::monostate{}) {}
    Value(bool b) : data_(b) {}
    Value(int i) : data_(static_cast<std::int64_t>(i)) {}
    Value(std::int64_t i) : data_(i) {}
    Value(double d) : data_(d) {}
    Value(const char* s) : data_(std::string(s)) {}
    Value(std::string s) : data_(std::move(s)) {}
    Value(Array a) : data_(std::move(a)) {}
    Value(Object o) : data_(std::move(o)) {}

    [[nodiscard]] bool is_null() const noexcept { return std::holds_alternative<std::monostate>(data_); }
    [[nodiscard]] bool is_bool() const noexcept { return std::holds_alternative<bool>(data_); }
    [[nodiscard]] bool is_int() const noexcept { return std::holds_alternative<std::int64_t>(data_); }
    [[nodiscard]] bool is_double() const noexcept { return std::holds_alternative<double>(data_); }
    [[nodiscard]] bool is_number() const noexcept { return is_int() || is_double(); }
    [[nodiscard]] bool is_string() const noexcept { return std::holds_alternative<std::string>(data_); }
    [[nodiscard]] bool is_array() const noexcept { return std::holds_alternative<Array>(data_); }
    [[nodiscard]] bool is_object() const noexcept { return std::holds_alternative<Object>(data_); }

    [[nodiscard]] bool as_bool(bool fallback = false) const noexcept {
        return is_bool() ? std::get<bool>(data_) : fallback;
    }
    [[nodiscard]] std::int64_t as_int(std::int64_t fallback = 0) const noexcept {
        if (is_int()) return std::get<std::int64_t>(data_);
        if (is_double()) return static_cast<std::int64_t>(std::get<double>(data_));
        return fallback;
    }
    [[nodiscard]] double as_double(double fallback = 0.0) const noexcept {
        if (is_double()) return std::get<double>(data_);
        if (is_int()) return static_cast<double>(std::get<std::int64_t>(data_));
        return fallback;
    }
    [[nodiscard]] const std::string& as_string() const { return std::get<std::string>(data_); }
    [[nodiscard]] const Array& as_array() const { return std::get<Array>(data_); }
    [[nodiscard]] const Object& as_object() const { return std::get<Object>(data_); }
    [[nodiscard]] Array& as_array() { return std::get<Array>(data_); }
    [[nodiscard]] Object& as_object() { return std::get<Object>(data_); }

    [[nodiscard]] const Value* find(const std::string& key) const noexcept {
        if (!is_object()) return nullptr;
        const auto& obj = std::get<Object>(data_);
        auto it = obj.find(key);
        return it == obj.end() ? nullptr : &it->second;
    }

    [[nodiscard]] std::string dump() const {
        std::string out;
        dump_into(out);
        return out;
    }

private:
    static void append_escaped(std::string& out, std::string_view s) {
        out.push_back('"');
        for (unsigned char c : s) {
            switch (c) {
                case '"': out += "\\\""; break;
                case '\\': out += "\\\\"; break;
                case '\b': out += "\\b"; break;
                case '\f': out += "\\f"; break;
                case '\n': out += "\\n"; break;
                case '\r': out += "\\r"; break;
                case '\t': out += "\\t"; break;
                default:
                    if (c < 0x20) {
                        char buf[7];
                        std::snprintf(buf, sizeof(buf), "\\u%04x", static_cast<unsigned int>(c));
                        out += buf;
                    } else {
                        out.push_back(static_cast<char>(c));
                    }
                    break;
            }
        }
        out.push_back('"');
    }

    void dump_into(std::string& out) const {
        if (is_null()) {
            out += "null";
        } else if (is_bool()) {
            out += std::get<bool>(data_) ? "true" : "false";
        } else if (is_int()) {
            out += std::to_string(std::get<std::int64_t>(data_));
        } else if (is_double()) {
            double v = std::get<double>(data_);
            if (!std::isfinite(v)) {
                out += "null";
            } else {
                char buf[64];
                std::snprintf(buf, sizeof(buf), "%.17g", v);
                out += buf;
            }
        } else if (is_string()) {
            append_escaped(out, std::get<std::string>(data_));
        } else if (is_array()) {
            out.push_back('[');
            const auto& arr = std::get<Array>(data_);
            for (std::size_t i = 0; i < arr.size(); ++i) {
                if (i > 0) out.push_back(',');
                arr[i].dump_into(out);
            }
            out.push_back(']');
        } else if (is_object()) {
            out.push_back('{');
            const auto& obj = std::get<Object>(data_);
            bool first = true;
            for (const auto& [k, v] : obj) {
                if (!first) out.push_back(',');
                first = false;
                append_escaped(out, k);
                out.push_back(':');
                v.dump_into(out);
            }
            out.push_back('}');
        }
    }

    std::variant<std::monostate, bool, std::int64_t, double, std::string, Array, Object> data_;
};

namespace detail {

class Parser {
public:
    explicit Parser(std::string_view input) : s_(input) {}

    [[nodiscard]] Expected<Value, ParseError> parse() {
        skip_ws();
        auto v = parse_value(0);
        if (!v) return v;
        skip_ws();
        if (pos_ != s_.size()) {
            return ParseError{"trailing characters in JSON"};
        }
        return v;
    }

private:
    static constexpr int kMaxDepth = 128;

    void skip_ws() noexcept {
        while (pos_ < s_.size()) {
            char c = s_[pos_];
            if (c == ' ' || c == '\t' || c == '\r' || c == '\n') {
                ++pos_;
            } else {
                break;
            }
        }
    }

    [[nodiscard]] Expected<Value, ParseError> parse_value(int depth) {
        if (depth > kMaxDepth) return ParseError{"JSON nesting depth exceeded"};
        skip_ws();
        if (pos_ >= s_.size()) return ParseError{"unexpected end of JSON"};
        char c = s_[pos_];
        if (c == 'n') return parse_literal("null", Value(nullptr));
        if (c == 't') return parse_literal("true", Value(true));
        if (c == 'f') return parse_literal("false", Value(false));
        if (c == '"') {
            auto s = parse_string();
            if (!s) return s.error();
            return Value(std::move(s.value()));
        }
        if (c == '[') return parse_array(depth + 1);
        if (c == '{') return parse_object(depth + 1);
        if (c == '-' || (c >= '0' && c <= '9')) return parse_number();
        return ParseError{"unexpected token in JSON"};
    }

    [[nodiscard]] Expected<Value, ParseError> parse_literal(std::string_view lit, Value val) {
        if (s_.substr(pos_, lit.size()) != lit) {
            return ParseError{"invalid JSON literal"};
        }
        pos_ += lit.size();
        return val;
    }

    [[nodiscard]] Expected<std::string, ParseError> parse_string() {
        if (pos_ >= s_.size() || s_[pos_] != '"') return ParseError{"expected '\"'"};
        ++pos_;
        std::string out;
        while (pos_ < s_.size()) {
            char c = s_[pos_++];
            if (c == '"') return out;
            if (c == '\\') {
                if (pos_ >= s_.size()) return ParseError{"unterminated escape"};
                char esc = s_[pos_++];
                switch (esc) {
                    case '"': out.push_back('"'); break;
                    case '\\': out.push_back('\\'); break;
                    case '/': out.push_back('/'); break;
                    case 'b': out.push_back('\b'); break;
                    case 'f': out.push_back('\f'); break;
                    case 'n': out.push_back('\n'); break;
                    case 'r': out.push_back('\r'); break;
                    case 't': out.push_back('\t'); break;
                    case 'u': {
                        if (pos_ + 4 > s_.size()) return ParseError{"invalid unicode escape"};
                        unsigned int code = 0;
                        auto [ptr, ec] = std::from_chars(s_.data() + pos_, s_.data() + pos_ + 4, code, 16);
                        if (ec != std::errc{} || ptr != s_.data() + pos_ + 4) {
                            return ParseError{"invalid hex in unicode escape"};
                        }
                        pos_ += 4;
                        if (code < 0x80) {
                            out.push_back(static_cast<char>(code));
                        } else if (code < 0x800) {
                            out.push_back(static_cast<char>(0xC0 | (code >> 6)));
                            out.push_back(static_cast<char>(0x80 | (code & 0x3F)));
                        } else {
                            out.push_back(static_cast<char>(0xE0 | (code >> 12)));
                            out.push_back(static_cast<char>(0x80 | ((code >> 6) & 0x3F)));
                            out.push_back(static_cast<char>(0x80 | (code & 0x3F)));
                        }
                        break;
                    }
                    default:
                        return ParseError{"invalid escape character"};
                }
            } else {
                out.push_back(c);
            }
        }
        return ParseError{"unterminated JSON string"};
    }

    [[nodiscard]] Expected<Value, ParseError> parse_number() {
        std::size_t start = pos_;
        bool is_float = false;
        if (s_[pos_] == '-') ++pos_;
        while (pos_ < s_.size() && s_[pos_] >= '0' && s_[pos_] <= '9') ++pos_;
        if (pos_ < s_.size() && s_[pos_] == '.') {
            is_float = true;
            ++pos_;
            while (pos_ < s_.size() && s_[pos_] >= '0' && s_[pos_] <= '9') ++pos_;
        }
        if (pos_ < s_.size() && (s_[pos_] == 'e' || s_[pos_] == 'E')) {
            is_float = true;
            ++pos_;
            if (pos_ < s_.size() && (s_[pos_] == '+' || s_[pos_] == '-')) ++pos_;
            while (pos_ < s_.size() && s_[pos_] >= '0' && s_[pos_] <= '9') ++pos_;
        }
        std::string_view token = s_.substr(start, pos_ - start);
        if (!is_float) {
            std::int64_t val = 0;
            auto [ptr, ec] = std::from_chars(token.data(), token.data() + token.size(), val);
            if (ec == std::errc{} && ptr == token.data() + token.size()) {
                return Value(val);
            }
        }
        std::string tmp(token);
        char* end = nullptr;
        double d = std::strtod(tmp.c_str(), &end);
        if (end != tmp.c_str() + tmp.size()) {
            return ParseError{"invalid JSON number"};
        }
        return Value(d);
    }

    [[nodiscard]] Expected<Value, ParseError> parse_array(int depth) {
        ++pos_;  // '['
        Value::Array arr;
        skip_ws();
        if (pos_ < s_.size() && s_[pos_] == ']') {
            ++pos_;
            return Value(std::move(arr));
        }
        while (true) {
            auto item = parse_value(depth);
            if (!item) return item;
            arr.push_back(std::move(item.value()));
            skip_ws();
            if (pos_ >= s_.size()) return ParseError{"unterminated JSON array"};
            if (s_[pos_] == ']') {
                ++pos_;
                return Value(std::move(arr));
            }
            if (s_[pos_] != ',') return ParseError{"expected ',' or ']' in array"};
            ++pos_;
        }
    }

    [[nodiscard]] Expected<Value, ParseError> parse_object(int depth) {
        ++pos_;  // '{'
        Value::Object obj;
        skip_ws();
        if (pos_ < s_.size() && s_[pos_] == '}') {
            ++pos_;
            return Value(std::move(obj));
        }
        while (true) {
            skip_ws();
            auto key = parse_string();
            if (!key) return key.error();
            skip_ws();
            if (pos_ >= s_.size() || s_[pos_] != ':') return ParseError{"expected ':' in object"};
            ++pos_;
            auto val = parse_value(depth);
            if (!val) return val;
            obj.insert_or_assign(std::move(key.value()), std::move(val.value()));
            skip_ws();
            if (pos_ >= s_.size()) return ParseError{"unterminated JSON object"};
            if (s_[pos_] == '}') {
                ++pos_;
                return Value(std::move(obj));
            }
            if (s_[pos_] != ',') return ParseError{"expected ',' or '}' in object"};
            ++pos_;
        }
    }

    std::string_view s_;
    std::size_t pos_ = 0;
};

}  // namespace detail

[[nodiscard]] inline Expected<Value, ParseError> parse(std::string_view input) {
    return detail::Parser(input).parse();
}

}  // namespace hanzo::flow::json
