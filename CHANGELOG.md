# CHANGELOG

<!-- version list -->

## v1.2.0 (2025-09-19)

### Chores

- Only release from master branch
  ([`0576355`](https://github.com/strongio/strong-opx/commit/0576355b163e52c41c2974a109435d092650c345))

### Documentation

- Improve docs [skip ci]
  ([`503fc6e`](https://github.com/strongio/strong-opx/commit/503fc6e00532bd7f544dafe5af73129a59eeba14))

### Features

- Azure Secret Provider ([#1](https://github.com/strongio/strong-opx/pull/1),
  [`d7a467c`](https://github.com/strongio/strong-opx/commit/d7a467c4a76d973906744384ba802ff2cdfbd76e))

### Refactoring

- Remove aws dependencies to optional dependencies [skip ci]
  ([`4d2ba2f`](https://github.com/strongio/strong-opx/commit/4d2ba2f744063ff0852780460971f2867d3e3ee7))


## v1.1.2 (2025-09-16)

### Bug Fixes

- Use environment to render FileTemplate using jinja2
  ([`d6e024a`](https://github.com/strongio/strong-opx/commit/d6e024ae66dd017886db9a141953aed7100713b0))


## v1.1.1 (2025-09-09)

### Bug Fixes

- Remove hardcoded tfbackend path and look for *.tfbackend
  ([`73f28e0`](https://github.com/strongio/strong-opx/commit/73f28e00f36e547c938131e55ed56076439d8a9f))


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
