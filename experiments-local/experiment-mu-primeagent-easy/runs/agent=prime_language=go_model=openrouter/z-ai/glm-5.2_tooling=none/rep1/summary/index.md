# Architecture summary

Small, idiomatic Go REST service (stdlib `net/http` with Go 1.22 method+path
routing) over an embedded pure-Go SQLite DB (`modernc.org/sqlite`, no CGO).

| File | Role |
|------|------|
| `main.go` | Entry point: parses `-addr`/`-db` flags (env fallbacks), opens `Store`, wires `Handler`, runs `http.Server`. |
| `model.go` | `Book`, `BookInput`, `BookInput.Validate()` (title+author required), `validationError`. |
| `store.go` | `Store` over `*sql.DB`; schema DDL; `Create/List/Get/Update/DeleteBook`. `:memory:` supported for tests. |
| `handler.go` | `Handler.Routes()` builds the `ServeMux`; per-route handlers; `parseID`, `decodeBookInput` (DisallowUnknownFields), `writeJSON`/`writeError`. |
| `handler_test.go` | 4 table/flow tests over an in-memory store. |

## Request flow

`main` → `NewStore(dbPath)` (opens SQLite, `CREATE TABLE IF NOT EXISTS books`)
→ `NewHandler(store)` → `Routes()` registers `GET/POST/PUT/DELETE` on `/books`,
`/books/{id}`, `/health` → each handler decodes/validates, calls a `Store`
method, and serializes JSON with an appropriate status code.

## Notes

- Clean layering: model / store / handler separation, no globals.
- Update is a full replace and re-validates title+author (spec-consistent).
- Extra rigor beyond spec: unknown JSON fields rejected; empty request body → 400.
