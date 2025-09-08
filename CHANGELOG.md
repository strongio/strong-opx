# CHANGELOG

<!-- version list -->

## v1.1.0 (2025-09-08)

### Bug Fixes

- If end_lineno is available, pass that to TemplateError
  ([`053abdd`](https://github.com/strongio/strong-opx/commit/053abdd99d38bc186a3907bd6c1d6e2776fcd8f5))

### Features

- Include template tag with auto indentation
  ([`4b82222`](https://github.com/strongio/strong-opx/commit/4b82222ced2dcf2b54e8c49779cf022115191a81))

### Refactoring

- Disallowed & syntax_error will return instead of raise
  ([`0ada862`](https://github.com/strongio/strong-opx/commit/0ada86246895e775aed35f9ab0c313b4cc9f06e4))

- Improve tokenization to properly handle raw block
  ([`f98bee4`](https://github.com/strongio/strong-opx/commit/f98bee4726845c1790022fc5409cf635e854ff9e))

- Remove usage of legacy template syntax in unittests
  ([`efff900`](https://github.com/strongio/strong-opx/commit/efff900e79d8ce3915b413135091edb0987bde3f))


## v1.0.0 (2025-09-02)

- Initial Release
