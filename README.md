[![Build Status](https://github.com/davidbrochart/anychange/workflows/test/badge.svg)](https://github.com/davidbrochart/anychange/actions)
[![Code Coverage](https://img.shields.io/badge/coverage-100%25-green)](https://img.shields.io/badge/coverage-100%25-green)

# anychange

`anychange` is a fork of [watchfiles](https://github.com/samuelcolvin/watchfiles) before it switched to the Rust backend,
i.e. when it was still called `watchgod` (at [this commit](https://github.com/samuelcolvin/watchfiles/tree/59c5eb3067761c2bfe346682784221cfca452b63)). The goal is to have it running in WASM,
so OS builtin file change notifications are not an option. Also, `watchgod` was
using threads which are not available in WASM, but file polling can be done without threads,
so `anychange` doesn't use them anymore.
