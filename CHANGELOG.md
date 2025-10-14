# CHANGELOG

<!-- version list -->

## v1.4.0 (2025-10-14)

### Bug Fixes

- Improve terraform comment handling
  ([`a131f41`](https://github.com/strongio/strong-opx/commit/a131f41df8ee574515e152f9208dd88b1924261b))

### Features

- Add support for selective vars decryption
  ([`b95c7da`](https://github.com/strongio/strong-opx/commit/b95c7dadce5792b30d5d0e3de2bf8f4d58f68bf0))


## v1.3.1 (2025-10-08)

### Bug Fixes

- Don't include env vars in base context
  ([`aefa61e`](https://github.com/strongio/strong-opx/commit/aefa61e86bee8313a3674017559b803f6dabe339))

- Lint
  ([`f58b5bf`](https://github.com/strongio/strong-opx/commit/f58b5bf77f5a4a96097aed39e5255a89442631f4))

- Represent objects as string
  ([`cab5f02`](https://github.com/strongio/strong-opx/commit/cab5f02f0906f18b07b26984758470a6b3b0279f))

### Chores

- Allow manual dispatch of publish workflow
  ([`5ead25d`](https://github.com/strongio/strong-opx/commit/5ead25dc64d34a449325581c6f97f1b4bd890b32))

- Fix version issues [skip ci]
  ([`69c97e3`](https://github.com/strongio/strong-opx/commit/69c97e30bc1a9dbc6d3587ba102232ba50102087))

- Upgrade pydantic requirement
  ([`c5e92d5`](https://github.com/strongio/strong-opx/commit/c5e92d5fc12ecac7492793132e019d7299ead8ac))


## v1.3.0 (2025-09-26)

### Bug Fixes

- `secret` in Project Config is Optional
  ([`4e036fd`](https://github.com/strongio/strong-opx/commit/4e036fd89c84bb6573928a93b60195505a9e3bc8))

- Improve Pydantic error message if value is missing
  ([`ec311d2`](https://github.com/strongio/strong-opx/commit/ec311d2c56b29941e94ce1393641cbaa6d4a8722))

### Chores

- Add provider var to action ([#4](https://github.com/strongio/strong-opx/pull/4),
  [`16b1f16`](https://github.com/strongio/strong-opx/commit/16b1f16e8344a9b32c9d8756d5fda0e55fe07be8))

- Move publishing to PyPI to separate GA workflow
  ([`10c4e88`](https://github.com/strongio/strong-opx/commit/10c4e882e2d1cff70f3f9cdd8e6f2cfd2605481d))

- Tag requires write permission
  ([`96eca5e`](https://github.com/strongio/strong-opx/commit/96eca5e63ef52c5d71662f4e7e54a80f00c6ffcb))

### Features

- Support of Google Cloud
  ([`e740f27`](https://github.com/strongio/strong-opx/commit/e740f272b1654159b5617a31b99b29a50157bf39))

### Refactoring

- Rename ContainerRegistry to DockerRegistry
  ([`040fac8`](https://github.com/strongio/strong-opx/commit/040fac81811c7e0c836a21046c248b5f4fc62a8c))


## v1.2.1 (2025-09-23)

### Bug Fixes

- Explain NoCredentialsError
  ([`2d35df3`](https://github.com/strongio/strong-opx/commit/2d35df3ff07c607af7bc277fb62705d4dc7a4f30))

### Chores

- Add manual version for strong-opx action
  ([`aac780a`](https://github.com/strongio/strong-opx/commit/aac780a196480b8409abcbfd4640507f1475f932))

- Install latest strong-opx only if no version is requested
  ([`e018429`](https://github.com/strongio/strong-opx/commit/e0184290dfd655b79267df837ba9edf1d49e0ff6))

- Install strong-opx from PyPI ([#2](https://github.com/strongio/strong-opx/pull/2),
  [`4eb4de9`](https://github.com/strongio/strong-opx/commit/4eb4de9349cbafe42ffcd938d30affe8fb926acf))

- Update project meta [skip ci]
  ([`1dc50f3`](https://github.com/strongio/strong-opx/commit/1dc50f37c9107a78d786bea17016bb32952c9e20))

- Use Python 3.12 in GA
  ([`a498b88`](https://github.com/strongio/strong-opx/commit/a498b88cb936d5bc99f765c80b3da17a455b39d8))


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
