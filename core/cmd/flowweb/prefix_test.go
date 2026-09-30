package main

import (
	"bufio"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"testing"
)

// firstParty matches a path literal on flow's own API that names the retired
// /api/ namespace or the folded /v2/ surface: "/api/…", 'api/v1…', `/v2/files`.
var firstParty = regexp.MustCompile("[\"'`(]/?api/|[\"'`(]/v2/(files|mcp|workflows|registration)")

// thirdParty names the files and hosts that call someone else's API, whose
// paths are theirs: Ollama's /api/tags, LangWatch's /api/evaluations, Zep's
// api/v1 base path, OpenRouter's /api/v1.
var thirdParty = []string{
	"openrouter.ai", "pokeapi.co", "components/langwatch/", "components/zep/",
	"components/ollama/", "base/models/model_utils.py",
}

// TestNoFirstPartyAPIPrefix fails when flow's own source calls or serves a path
// under /api/ or /v2/. The API is /v1 and nothing else.
func TestNoFirstPartyAPIPrefix(t *testing.T) {
	root := filepath.Join("..", "..", "..", "src")
	dirs := []string{"frontend/src", "backend/base/flow", "lfx/src/lfx", "sdk/src"}
	exts := map[string]bool{".py": true, ".ts": true, ".tsx": true, ".js": true, ".jsx": true}
	var hits []string
	for _, d := range dirs {
		err := filepath.WalkDir(filepath.Join(root, d), func(p string, e fs.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if e.IsDir() {
				switch e.Name() {
				case "node_modules", "__tests__", "tests", "_assets":
					return filepath.SkipDir
				}
				return nil
			}
			if !exts[filepath.Ext(p)] {
				return nil
			}
			f, err := os.Open(p)
			if err != nil {
				return err
			}
			defer f.Close()
			s := bufio.NewScanner(f)
			s.Buffer(make([]byte, 1<<20), 1<<24)
			for n := 1; s.Scan(); n++ {
				line := s.Text()
				if !firstParty.MatchString(line) || mentions(filepath.ToSlash(p)+" "+line, thirdParty) {
					continue
				}
				hits = append(hits, p+":"+strconv.Itoa(n)+": "+strings.TrimSpace(line))
			}
			return s.Err()
		})
		if err != nil {
			t.Fatalf("walk %s: %v", d, err)
		}
	}
	for _, h := range hits {
		t.Error(h)
	}
}

func mentions(line string, words []string) bool {
	l := strings.ToLower(line)
	for _, w := range words {
		if strings.Contains(l, w) {
			return true
		}
	}
	return false
}
