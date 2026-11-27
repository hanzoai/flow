# Hanzo Flow C++20 Core & SDK (`hanzo::flow`)

Two clean CMake targets in one portable C++20 package:
1. **`hanzo_flow_core`** (`include/hanzo/flow/core.hpp`): Header-only, zero-dependency 1:1 port of the Hanzo Flow step-DAG engine (`Value`, `Port`, `Step`, `PortRef`, `Edge`, `Mode`, `Graph`, `Scheduler`, zero-copy `std::shared_ptr<const Value>` edge passing, `*` wildcard ports, deterministic Kahn cycle detection).
2. **`hanzo_flow_sdk`** (`include/hanzo/flow/client.hpp`, `src/client.cpp`): Native RAII `libcurl` REST client for the canonical `/v1/flow/*` API (`https://api.hanzo.ai`, `Authorization: Bearer`, `X-Org-Id`) with zero third-party JSON dependencies.

## Build & Test

```bash
cmake -S sdk/cpp -B /tmp/build-flow-cpp
cmake --build /tmp/build-flow-cpp
ctest --test-dir /tmp/build-flow-cpp --output-on-failure
```

## Example — REST Client

```cpp
#include <cstdlib>
#include <iostream>
#include "hanzo/flow/client.hpp"

int main() {
    hanzo::flow::ClientConfig cfg;
    if (const char* key = std::getenv("HANZO_API_KEY")) cfg.token = key;
    cfg.org_id = "hanzo";

    hanzo::flow::Client client(cfg);
    auto st = client.status();
    if (!st) {
        std::cerr << st.error().message() << '\n';
        return 1;
    }
    std::cout << "reachable=" << st.value().reachable
              << " version=" << st.value().version << '\n';
}
```
